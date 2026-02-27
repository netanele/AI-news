"""Tests for data_manager module."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

from pipeline.data_manager import (
    load_existing_data,
    get_existing_video_ids,
    filter_new_videos,
    merge_and_group,
    get_changed_days,
)


def _make_video(video_id, channel_name, days_ago=0):
    """Helper to create a video dict."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "id": video_id,
        "title": f"Video {video_id}",
        "publishedAt": dt.isoformat(),
        "duration": None,
        "thumbnailUrl": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
        "channelName": channel_name,
        "channelUrl": f"https://www.youtube.com/@{channel_name}",
        "summary": f"Summary for {video_id}",
        "transcriptAvailable": True,
    }


def _make_existing_data(videos_by_day):
    """Helper to create an existing data structure."""
    days = []
    for date_str, channel_videos in videos_by_day.items():
        channels = []
        for ch_name, videos in channel_videos.items():
            channels.append({
                "channelName": ch_name,
                "channelUrl": f"https://www.youtube.com/@{ch_name}",
                "videos": videos,
            })
        days.append({
            "date": date_str,
            "dailyDigest": f"Digest for {date_str}",
            "channels": channels,
        })
    return {"lastUpdated": "2026-02-26T08:00:00Z", "config": {"daysToShow": 7}, "days": days}


class TestLoadExistingData:
    def test_returns_empty_when_file_missing(self):
        result = load_existing_data("/nonexistent/path.json")
        assert result["days"] == []
        assert result["lastUpdated"] is None

    def test_returns_empty_on_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            path = f.name
        try:
            result = load_existing_data(path)
            assert result["days"] == []
        finally:
            os.unlink(path)

    def test_loads_valid_data(self):
        data = {"lastUpdated": "2026-02-26T08:00:00Z", "config": {}, "days": [{"date": "2026-02-26"}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_existing_data(path)
            assert len(result["days"]) == 1
        finally:
            os.unlink(path)


class TestGetExistingVideoIds:
    def test_extracts_ids(self):
        data = _make_existing_data({
            "2026-02-26": {"Ch1": [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]},
        })
        ids = get_existing_video_ids(data)
        assert ids == {"a", "b"}

    def test_empty_data(self):
        ids = get_existing_video_ids({"days": []})
        assert ids == set()


class TestFilterNewVideos:
    def test_filters_existing(self):
        videos = [_make_video("a", "Ch"), _make_video("b", "Ch"), _make_video("c", "Ch")]
        result = filter_new_videos(videos, {"a", "b"})
        assert len(result) == 1
        assert result[0]["id"] == "c"

    def test_no_existing(self):
        videos = [_make_video("a", "Ch")]
        result = filter_new_videos(videos, set())
        assert len(result) == 1


class TestMergeAndGroup:
    def test_merge_new_into_empty(self):
        new_videos = [_make_video("v1", "Ch1", days_ago=0), _make_video("v2", "Ch2", days_ago=1)]
        result = merge_and_group({"days": []}, new_videos, days_to_show=7)
        assert len(result["days"]) == 2
        assert result["config"]["daysToShow"] == 7

    def test_no_duplicates(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing = _make_existing_data({
            today: {"Ch1": [{"id": "v1", "title": "V1", "publishedAt": datetime.now(timezone.utc).isoformat(),
                             "summary": "existing", "transcriptAvailable": True, "duration": None,
                             "thumbnailUrl": "", "videoUrl": ""}]},
        })
        new_videos = [_make_video("v2", "Ch1", days_ago=0)]
        result = merge_and_group(existing, new_videos, days_to_show=7)

        # Find today's day
        today_day = next(d for d in result["days"] if d["date"] == today)
        ch1_videos = next(ch for ch in today_day["channels"] if ch["channelName"] == "Ch1")
        assert len(ch1_videos["videos"]) == 2

    def test_drops_old_days(self):
        new_videos = [_make_video("old", "Ch1", days_ago=10), _make_video("new", "Ch1", days_ago=1)]
        result = merge_and_group({"days": []}, new_videos, days_to_show=7)
        all_ids = [v["id"] for d in result["days"] for ch in d["channels"] for v in ch["videos"]]
        assert "new" in all_ids
        assert "old" not in all_ids

    def test_days_sorted_newest_first(self):
        new_videos = [
            _make_video("v1", "Ch1", days_ago=3),
            _make_video("v2", "Ch1", days_ago=1),
            _make_video("v3", "Ch1", days_ago=0),
        ]
        result = merge_and_group({"days": []}, new_videos, days_to_show=7)
        dates = [d["date"] for d in result["days"]]
        assert dates == sorted(dates, reverse=True)


class TestGetChangedDays:
    def test_detects_new_day(self):
        existing = {"days": []}
        merged = {"days": [{"date": "2026-02-26", "channels": [{"videos": [{"id": "v1"}]}]}]}
        changed = get_changed_days(existing, merged)
        assert "2026-02-26" in changed

    def test_detects_new_video_in_existing_day(self):
        existing = {"days": [{"date": "2026-02-26", "channels": [{"videos": [{"id": "v1"}]}]}]}
        merged = {"days": [{"date": "2026-02-26", "channels": [{"videos": [{"id": "v1"}, {"id": "v2"}]}]}]}
        changed = get_changed_days(existing, merged)
        assert "2026-02-26" in changed

    def test_unchanged_day_not_returned(self):
        existing = {"days": [{"date": "2026-02-26", "channels": [{"videos": [{"id": "v1"}]}]}]}
        merged = {"days": [{"date": "2026-02-26", "channels": [{"videos": [{"id": "v1"}]}]}]}
        changed = get_changed_days(existing, merged)
        assert changed == []
