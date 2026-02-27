"""Tests for transcript_fetcher module."""

from unittest.mock import patch, MagicMock, Mock

from pipeline.transcript_fetcher import fetch_transcripts


def _make_video(video_id):
    return {"id": video_id, "title": f"Video {video_id}"}


class TestFetchTranscripts:
    @patch("pipeline.transcript_fetcher.YouTubeTranscriptApi")
    def test_successful_fetch(self, mock_api_cls):
        api_instance = MagicMock()
        mock_api_cls.return_value = api_instance

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

    @patch("pipeline.transcript_fetcher.YouTubeTranscriptApi")
    def test_failure_marks_unavailable(self, mock_api_cls):
        api_instance = MagicMock()
        mock_api_cls.return_value = api_instance
        api_instance.fetch.side_effect = ConnectionError("Blocked")

        videos = [_make_video("fail123")]
        result = fetch_transcripts(videos, max_retries=2, retry_delay=0)

        assert result[0]["transcriptAvailable"] is False
        assert result[0]["transcript"] is None

    @patch("pipeline.transcript_fetcher.time.sleep")
    @patch("pipeline.transcript_fetcher.YouTubeTranscriptApi")
    def test_retries_on_transient_error(self, mock_api_cls, mock_sleep):
        api_instance = MagicMock()
        mock_api_cls.return_value = api_instance

        snippet = Mock()
        snippet.text = "Success"
        transcript = Mock()
        transcript.snippets = [snippet]
        api_instance.fetch.side_effect = [ConnectionError("Temp"), transcript]

        videos = [_make_video("retry123")]
        result = fetch_transcripts(videos, max_retries=3, retry_delay=1)

        assert result[0]["transcriptAvailable"] is True
        assert mock_sleep.call_count == 1

    @patch("pipeline.transcript_fetcher.YouTubeTranscriptApi")
    def test_non_retriable_error_breaks_immediately(self, mock_api_cls):
        api_instance = MagicMock()
        mock_api_cls.return_value = api_instance
        api_instance.fetch.side_effect = TypeError("Unexpected API change")

        videos = [_make_video("bug123")]
        result = fetch_transcripts(videos, max_retries=3, retry_delay=0)

        assert result[0]["transcriptAvailable"] is False
        # Should only try once (non-retriable breaks immediately)
        assert api_instance.fetch.call_count == 1

    @patch("pipeline.transcript_fetcher.YouTubeTranscriptApi")
    def test_continues_to_next_video_on_failure(self, mock_api_cls):
        api_instance = MagicMock()
        mock_api_cls.return_value = api_instance

        snippet = Mock()
        snippet.text = "OK"
        transcript = Mock()
        transcript.snippets = [snippet]

        api_instance.fetch.side_effect = [ConnectionError("Fail"), transcript]

        videos = [_make_video("fail1"), _make_video("ok1")]
        result = fetch_transcripts(videos, max_retries=1, retry_delay=0)

        assert result[0]["transcriptAvailable"] is False
        assert result[1]["transcriptAvailable"] is True
