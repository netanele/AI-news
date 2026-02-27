"""Tests for rss_fetcher module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from pipeline.rss_fetcher import fetch_videos


def _make_entry(video_id, title, published_dt):
    """Helper to create a mock feedparser entry."""
    entry = MagicMock()
    entry.id = f"yt:video:{video_id}"
    entry.title = title
    entry.published = published_dt.isoformat()
    entry.link = f"https://www.youtube.com/watch?v={video_id}"
    entry.get = lambda key, default=None: {
        "title": title,
        "published": published_dt.isoformat(),
        "link": f"https://www.youtube.com/watch?v={video_id}",
    }.get(key, default)
    return entry


def _make_channel(name="TestChannel", channel_id="UC_test123456789012345"):
    return {
        "url": f"https://www.youtube.com/@{name}",
        "channel_id": channel_id,
        "channel_name": name,
    }


def _mock_response_ok():
    """Create a mock requests.Response with status 200."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"<xml>mock</xml>"
    return resp


class TestFetchVideos:
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_returns_recent_videos(self, mock_get, mock_parse):
        mock_get.return_value = _mock_response_ok()
        now = datetime.now(timezone.utc)
        feed = MagicMock()
        feed.bozo = False
        feed.entries = [
            _make_entry("vid1", "Recent Video", now - timedelta(hours=2)),
            _make_entry("vid2", "Yesterday Video", now - timedelta(days=1)),
        ]
        mock_parse.return_value = feed

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 2
        assert result[0]["id"] == "vid1"
        assert result[0]["title"] == "Recent Video"
        assert result[0]["thumbnailUrl"] == "https://i.ytimg.com/vi/vid1/hqdefault.jpg"

    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_filters_old_videos(self, mock_get, mock_parse):
        mock_get.return_value = _mock_response_ok()
        now = datetime.now(timezone.utc)
        feed = MagicMock()
        feed.bozo = False
        feed.entries = [
            _make_entry("new", "New", now - timedelta(days=1)),
            _make_entry("old", "Old", now - timedelta(days=10)),
        ]
        mock_parse.return_value = feed

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 1
        assert result[0]["id"] == "new"

    @patch("pipeline.rss_fetcher.requests.get")
    def test_channel_error_skipped(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 0

    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_video_metadata_fields(self, mock_get, mock_parse):
        mock_get.return_value = _mock_response_ok()
        now = datetime.now(timezone.utc)
        feed = MagicMock()
        feed.bozo = False
        feed.entries = [_make_entry("xyz", "Test Title", now)]
        mock_parse.return_value = feed

        channel = _make_channel("MyChannel")
        result = fetch_videos([channel], days_to_show=7)
        assert len(result) == 1
        video = result[0]
        assert video["id"] == "xyz"
        assert video["channelName"] == "MyChannel"
        assert video["channelUrl"] == "https://www.youtube.com/@MyChannel"
        assert video["duration"] is None
        assert video["videoUrl"] == "https://www.youtube.com/watch?v=xyz"

    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_multiple_channels(self, mock_get, mock_parse):
        mock_get.return_value = _mock_response_ok()
        now = datetime.now(timezone.utc)
        feed = MagicMock()
        feed.bozo = False
        feed.entries = [_make_entry("v1", "Video 1", now)]
        mock_parse.return_value = feed

        channels = [_make_channel("Ch1", "UC_ch1_id_00000000000000"), _make_channel("Ch2", "UC_ch2_id_00000000000000")]
        result = fetch_videos(channels, days_to_show=7)
        assert len(result) == 2

    @patch("pipeline.rss_fetcher.requests.get")
    def test_http_error_skips_channel(self, mock_get):
        """When RSS returns non-200, the channel should be skipped."""
        resp = MagicMock()
        resp.status_code = 404
        mock_get.return_value = resp

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 0
