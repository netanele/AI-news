"""Manage pipeline data: load, merge, group, and window video data."""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _empty_data():
    """Return the empty data structure."""
    return {"lastUpdated": None, "config": {}, "days": []}


def load_existing_data(data_path="data.json"):
    """Load existing data.json. Returns empty structure if missing or invalid."""
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "days" not in data:
            return _empty_data()
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return _empty_data()


def get_existing_video_ids(existing_data):
    """Extract all video IDs from existing data for incremental diffing."""
    ids = set()
    for day in existing_data.get("days", []):
        for channel in day.get("channels", []):
            for video in channel.get("videos", []):
                ids.add(video["id"])
    return ids


def filter_new_videos(all_videos, existing_ids):
    """Return only videos whose ID is not in existing_ids."""
    return [v for v in all_videos if v["id"] not in existing_ids]


def merge_and_group(existing_data, new_videos, days_to_show):
    """Merge existing + new videos, group by date/channel, window to days_to_show.

    Returns the full data structure matching the Data Model spec.
    """
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_to_show)).strftime("%Y-%m-%d")

    # Collect all existing videos into a flat list
    all_videos = []
    for day in existing_data.get("days", []):
        for channel in day.get("channels", []):
            for video in channel.get("videos", []):
                all_videos.append({
                    **video,
                    "channelName": channel.get("channelName", ""),
                    "channelUrl": channel.get("channelUrl", ""),
                })

    # Add new videos
    all_videos.extend(new_videos)

    # Group by date -> channel
    days_dict = defaultdict(lambda: defaultdict(list))
    for video in all_videos:
        date_str = video.get("publishedAt", "")[:10]  # YYYY-MM-DD
        if date_str < cutoff_date:
            continue

        channel_key = video.get("channelName", "Unknown")
        # Store video without redundant channel fields at video level
        video_entry = {
            "id": video["id"],
            "title": video.get("title", "Untitled"),
            "publishedAt": video.get("publishedAt", ""),
            "duration": video.get("duration"),
            "thumbnailUrl": video.get("thumbnailUrl", ""),
            "videoUrl": video.get("videoUrl", ""),
            "summary": video.get("summary", ""),
            "transcriptAvailable": video.get("transcriptAvailable", False),
        }
        days_dict[date_str][channel_key].append(video_entry)

    # Build channel name -> URL lookup (O(1) per channel)
    channel_url_map = {}
    for v in all_videos:
        name = v.get("channelName", "")
        if name and name not in channel_url_map:
            channel_url_map[name] = v.get("channelUrl", "")

    # Build structured days array
    days = []
    existing_digests = {}
    for day in existing_data.get("days", []):
        existing_digests[day["date"]] = day.get("dailyDigest", "")

    for date_str in sorted(days_dict.keys(), reverse=True):
        channels = []
        channel_groups = days_dict[date_str]
        for channel_name in sorted(channel_groups.keys()):
            videos = channel_groups[channel_name]

            channels.append({
                "channelName": channel_name,
                "channelUrl": channel_url_map.get(channel_name, ""),
                "videos": sorted(videos, key=lambda v: v.get("publishedAt", ""), reverse=True),
            })

        days.append({
            "date": date_str,
            "dailyDigest": existing_digests.get(date_str, ""),
            "channels": channels,
        })

    return {
        "lastUpdated": existing_data.get("lastUpdated"),
        "config": {"daysToShow": days_to_show},
        "days": days,
    }


def _day_fingerprint(day):
    """Build a fingerprint for a day based on video IDs and summary presence."""
    parts = []
    for ch in day.get("channels", []):
        for v in ch.get("videos", []):
            summary = v.get("summary", "")
            has_real_summary = bool(summary) and not summary.startswith("Summary generation failed")
            parts.append(f"{v['id']}:{has_real_summary}")
    return frozenset(parts)


def get_changed_days(existing_data, merged_data):
    """Return list of date strings for days that have new or updated content."""
    existing_fingerprints = {}
    for day in existing_data.get("days", []):
        existing_fingerprints[day["date"]] = _day_fingerprint(day)

    changed = []
    for day in merged_data.get("days", []):
        fp = _day_fingerprint(day)
        if day["date"] not in existing_fingerprints or existing_fingerprints[day["date"]] != fp:
            changed.append(day["date"])

    return changed
