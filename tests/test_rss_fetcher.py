"""Tests for rss_fetcher module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, call

from pipeline.rss_fetcher import fetch_videos, _fetch_channel_feed


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


def _mock_response(status_code=200):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b"<xml>mock</xml>"
    return resp


def _mock_feed(entries):
    feed = MagicMock()
    feed.bozo = False
    feed.entries = entries
    return feed


class TestFetchChannelFeed:
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_returns_videos_on_success(self, mock_get, mock_parse):
        mock_get.return_value = _mock_response(200)
        now = datetime.now(timezone.utc)
        mock_parse.return_value = _mock_feed([
            _make_entry("vid1", "Video 1", now),
        ])
        cutoff = now - timedelta(days=7)
        result = _fetch_channel_feed(_make_channel(), cutoff)
        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "vid1"

    @patch("pipeline.rss_fetcher.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_get.return_value = _mock_response(404)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = _fetch_channel_feed(_make_channel(), cutoff)
        assert result is None

    @patch("pipeline.rss_fetcher.requests.get")
    def test_returns_none_on_exception(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = _fetch_channel_feed(_make_channel(), cutoff)
        assert result is None


class TestFetchVideos:
    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_returns_recent_videos(self, mock_get, mock_parse, mock_sleep):
        mock_get.return_value = _mock_response(200)
        now = datetime.now(timezone.utc)
        mock_parse.return_value = _mock_feed([
            _make_entry("vid1", "Recent Video", now - timedelta(hours=2)),
            _make_entry("vid2", "Yesterday Video", now - timedelta(days=1)),
        ])

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 2
        assert result[0]["id"] == "vid1"
        assert result[0]["title"] == "Recent Video"
        assert result[0]["thumbnailUrl"] == "https://i.ytimg.com/vi/vid1/hqdefault.jpg"

    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_filters_old_videos(self, mock_get, mock_parse, mock_sleep):
        mock_get.return_value = _mock_response(200)
        now = datetime.now(timezone.utc)
        mock_parse.return_value = _mock_feed([
            _make_entry("new", "New", now - timedelta(days=1)),
            _make_entry("old", "Old", now - timedelta(days=10)),
        ])

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 1
        assert result[0]["id"] == "new"

    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_channel_error_retries_then_fails(self, mock_get, mock_sleep):
        """A channel that always errors should be retried 3 times then skipped."""
        mock_get.side_effect = Exception("Network error")
        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 0
        # 1 initial + 3 retries = 4 total calls
        assert mock_get.call_count == 4

    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_retry_succeeds_on_second_attempt(self, mock_get, mock_parse, mock_sleep):
        """A channel that fails initially but succeeds on retry."""
        now = datetime.now(timezone.utc)
        good_resp = _mock_response(200)
        bad_resp = _mock_response(500)

        # First call fails, second succeeds
        mock_get.side_effect = [bad_resp, good_resp]
        mock_parse.return_value = _mock_feed([
            _make_entry("v1", "Video 1", now),
        ])

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 1
        assert result[0]["id"] == "v1"

    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_video_metadata_fields(self, mock_get, mock_parse, mock_sleep):
        mock_get.return_value = _mock_response(200)
        now = datetime.now(timezone.utc)
        mock_parse.return_value = _mock_feed([_make_entry("xyz", "Test Title", now)])

        channel = _make_channel("MyChannel")
        result = fetch_videos([channel], days_to_show=7)
        assert len(result) == 1
        video = result[0]
        assert video["id"] == "xyz"
        assert video["channelName"] == "MyChannel"
        assert video["channelUrl"] == "https://www.youtube.com/@MyChannel"
        assert video["duration"] is None
        assert video["videoUrl"] == "https://www.youtube.com/watch?v=xyz"

    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.feedparser.parse")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_multiple_channels(self, mock_get, mock_parse, mock_sleep):
        mock_get.return_value = _mock_response(200)
        now = datetime.now(timezone.utc)
        mock_parse.return_value = _mock_feed([_make_entry("v1", "Video 1", now)])

        channels = [_make_channel("Ch1", "UC_ch1_id_00000000000000"), _make_channel("Ch2", "UC_ch2_id_00000000000000")]
        result = fetch_videos(channels, days_to_show=7)
        assert len(result) == 2

    @patch("pipeline.rss_fetcher.time.sleep")
    @patch("pipeline.rss_fetcher.requests.get")
    def test_http_error_retried(self, mock_get, mock_sleep):
        """When RSS returns non-200, the channel should be retried."""
        mock_get.return_value = _mock_response(404)

        result = fetch_videos([_make_channel()], days_to_show=7)
        assert len(result) == 0
        # 1 initial + 3 retries = 4 total calls
        assert mock_get.call_count == 4
