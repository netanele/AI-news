"""Tests for summarizer module."""

from unittest.mock import patch, Mock, MagicMock

from pipeline.summarizer import (
    summarize_video,
    generate_daily_digest,
    init_client,
    FAILURE_MESSAGE,
)


class TestInitClient:
    @patch("pipeline.summarizer.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"})
    def test_creates_client_with_env_key(self, mock_client_cls):
        config = {"ai": {"apiKeyEnvVar": "GEMINI_API_KEY"}}
        init_client(config)
        mock_client_cls.assert_called_once_with(api_key="test-key-123")


class TestSummarizeVideo:
    def test_returns_summary_on_success(self):
        client = MagicMock()
        response = Mock()
        response.text = "\u2022 Point 1\n\u2022 Point 2\n\u2022 Point 3"
        client.models.generate_content.return_value = response

        result = summarize_video(client, "gemini-2.0-flash", "Some transcript text")
        assert "\u2022 Point 1" in result
        client.models.generate_content.assert_called_once()

    def test_prompt_includes_transcript(self):
        client = MagicMock()
        response = Mock()
        response.text = "summary"
        client.models.generate_content.return_value = response

        summarize_video(client, "gemini-2.0-flash", "My specific transcript content")
        call_args = client.models.generate_content.call_args
        assert "My specific transcript content" in call_args.kwargs["contents"]

    @patch("pipeline.summarizer.time.sleep")
    def test_retries_on_failure(self, mock_sleep):
        client = MagicMock()
        client.models.generate_content.side_effect = [
            Exception("Rate limited"),
            Exception("Server error"),
            Mock(text="Final success"),
        ]

        result = summarize_video(client, "gemini-2.0-flash", "transcript")
        assert result == "Final success"
        assert client.models.generate_content.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("pipeline.summarizer.time.sleep")
    def test_returns_fallback_after_all_retries(self, mock_sleep):
        client = MagicMock()
        client.models.generate_content.side_effect = Exception("Always fails")

        result = summarize_video(client, "gemini-2.0-flash", "transcript")
        assert result == FAILURE_MESSAGE
        assert client.models.generate_content.call_count == 3


class TestGenerateDailyDigest:
    def test_returns_digest_on_success(self):
        client = MagicMock()
        response = Mock()
        response.text = "Today's AI news covered breakthroughs in LLMs and robotics."
        client.models.generate_content.return_value = response

        result = generate_daily_digest(client, "gemini-2.0-flash", "2026-02-26", ["\u2022 Point 1", "\u2022 Point 2"])
        assert "breakthroughs" in result

    def test_prompt_includes_day_and_summaries(self):
        client = MagicMock()
        response = Mock()
        response.text = "digest"
        client.models.generate_content.return_value = response

        generate_daily_digest(client, "gemini-2.0-flash", "2026-02-26", ["Summary A", "Summary B"])
        call_args = client.models.generate_content.call_args
        prompt = call_args.kwargs["contents"]
        assert "2026-02-26" in prompt
        assert "Summary A" in prompt
        assert "Summary B" in prompt
