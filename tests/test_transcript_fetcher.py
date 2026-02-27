"""Tests for transcript_fetcher module."""

from unittest.mock import patch, MagicMock, Mock

from youtube_transcript_api._errors import RequestBlocked

from pipeline.transcript_fetcher import fetch_transcripts


def _make_video(video_id):
    return {"id": video_id, "title": f"Video {video_id}"}


class TestFetchTranscripts:
    @patch("pipeline.transcript_fetcher._build_api")
    def test_successful_fetch(self, mock_build):
        api_instance = MagicMock()
        mock_build.return_value = api_instance

        snippet1 = Mock()
        snippet1.text = "Hello world"
        snippet2 = Mock()
        snippet2.text = "This is a test"
        transcript = Mock()
        transcript.snippets = [snippet1, snippet2]
        api_instance.fetch.return_value = transcript

        videos = [_make_video("abc123")]
        result = fetch_transcripts(videos, max_retries=1, retry_delay=0)

        assert result[0]["transcriptAvailable"] is True
        assert result[0]["transcript"] == "Hello world This is a test"

    @patch("pipeline.transcript_fetcher._build_api")
    def test_failure_marks_unavailable(self, mock_build):
        api_instance = MagicMock()
        mock_build.return_value = api_instance
        api_instance.fetch.side_effect = ConnectionError("Blocked")

        videos = [_make_video("fail123")]
        result = fetch_transcripts(videos, max_retries=2, retry_delay=0)

        assert result[0]["transcriptAvailable"] is False
        assert result[0]["transcript"] is None

    @patch("pipeline.transcript_fetcher.time.sleep")
    @patch("pipeline.transcript_fetcher._build_api")
    def test_retries_on_transient_error(self, mock_build, mock_sleep):
        api_instance = MagicMock()
        mock_build.return_value = api_instance

        snippet = Mock()
        snippet.text = "Success"
        transcript = Mock()
        transcript.snippets = [snippet]
        api_instance.fetch.side_effect = [ConnectionError("Temp"), transcript]

        videos = [_make_video("retry123")]
        result = fetch_transcripts(videos, max_retries=3, retry_delay=1)

        assert result[0]["transcriptAvailable"] is True
        assert mock_sleep.call_count == 1

    @patch("pipeline.transcript_fetcher._build_api")
    def test_non_retriable_error_breaks_immediately(self, mock_build):
        api_instance = MagicMock()
        mock_build.return_value = api_instance
        api_instance.fetch.side_effect = TypeError("Unexpected API change")

        videos = [_make_video("bug123")]
        result = fetch_transcripts(videos, max_retries=3, retry_delay=0)

        assert result[0]["transcriptAvailable"] is False
        assert api_instance.fetch.call_count == 1

    @patch("pipeline.transcript_fetcher._build_api")
    def test_continues_to_next_video_on_failure(self, mock_build):
        api_instance = MagicMock()
        mock_build.return_value = api_instance

        snippet = Mock()
        snippet.text = "OK"
        transcript = Mock()
        transcript.snippets = [snippet]

        api_instance.fetch.side_effect = [ConnectionError("Fail"), transcript]

        videos = [_make_video("fail1"), _make_video("ok1")]
        result = fetch_transcripts(videos, max_retries=1, retry_delay=0)

        assert result[0]["transcriptAvailable"] is False
        assert result[1]["transcriptAvailable"] is True

    @patch("pipeline.transcript_fetcher._build_api")
    def test_ip_blocked_skips_remaining_videos(self, mock_build):
        """When YouTube blocks the IP, skip all remaining videos immediately."""
        api_instance = MagicMock()
        mock_build.return_value = api_instance
        api_instance.fetch.side_effect = RequestBlocked("vid1")

        videos = [_make_video("v1"), _make_video("v2"), _make_video("v3")]
        result = fetch_transcripts(videos, max_retries=3, retry_delay=0)

        # All marked unavailable
        assert all(v["transcriptAvailable"] is False for v in result)
        # Only tried fetching the first video (then skipped the rest)
        assert api_instance.fetch.call_count == 1

    @patch("pipeline.transcript_fetcher.os.environ", {"YOUTUBE_PROXY": "http://proxy:8080"})
    @patch("pipeline.transcript_fetcher.GenericProxyConfig")
    @patch("pipeline.transcript_fetcher.YouTubeTranscriptApi")
    def test_proxy_configured_from_env(self, mock_api_cls, mock_proxy_cls):
        """When YOUTUBE_PROXY is set, the API should use proxy config."""
        from pipeline.transcript_fetcher import _build_api
        _build_api()

        mock_proxy_cls.assert_called_once_with(
            http_url="http://proxy:8080",
            https_url="http://proxy:8080",
        )
        mock_api_cls.assert_called_once()
