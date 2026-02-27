"""Tests for channel_resolver module."""

from unittest.mock import patch, Mock

from pipeline.channel_resolver import resolve_channels, _extract_channel_id_from_html


class TestExtractChannelIdFromHtml:
    def test_extracts_from_og_url(self):
        html = '<meta property="og:url" content="https://www.youtube.com/channel/UCbfYPyITQ-7l4upoX8nvctg">'
        assert _extract_channel_id_from_html(html) == "UCbfYPyITQ-7l4upoX8nvctg"

    def test_extracts_from_canonical(self):
        html = '<link rel="canonical" href="https://www.youtube.com/channel/UCZHmQk67mSJgfCCTn7xBfew">'
        assert _extract_channel_id_from_html(html) == "UCZHmQk67mSJgfCCTn7xBfew"

    def test_extracts_from_page_body(self):
        html = '<script>var url = "/channel/UCbfYPyITQ-7l4upoX8nvctg/featured";</script>'
        assert _extract_channel_id_from_html(html) == "UCbfYPyITQ-7l4upoX8nvctg"

    def test_returns_none_when_not_found(self):
        html = "<html><body>No channel here</body></html>"
        assert _extract_channel_id_from_html(html) is None


class TestResolveChannels:
    def test_direct_channel_url(self):
        urls = ["https://www.youtube.com/channel/UCbfYPyITQ-7l4upoX8nvctg"]
        result = resolve_channels(urls)
        assert len(result) == 1
        assert result[0]["channel_id"] == "UCbfYPyITQ-7l4upoX8nvctg"

    @patch("pipeline.channel_resolver.requests.get")
    def test_handle_url_resolved(self, mock_get):
        mock_response = Mock()
        mock_response.text = '<meta property="og:url" content="https://www.youtube.com/channel/UCbfYPyITQ-7l4upoX8nvctg">'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = resolve_channels(["https://www.youtube.com/@TwoMinutePapers"])
        assert len(result) == 1
        assert result[0]["channel_id"] == "UCbfYPyITQ-7l4upoX8nvctg"
        assert result[0]["channel_name"] == "TwoMinutePapers"

    @patch("pipeline.channel_resolver.requests.get")
    def test_invalid_url_skipped(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = resolve_channels(["https://www.youtube.com/@InvalidChannel123"])
        assert len(result) == 0

    @patch("pipeline.channel_resolver.requests.get")
    def test_no_channel_id_in_html_skipped(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html><body>No channel ID</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = resolve_channels(["https://www.youtube.com/@SomeChannel"])
        assert len(result) == 0

    @patch("pipeline.channel_resolver.requests.get")
    def test_mixed_urls(self, mock_get):
        mock_response = Mock()
        mock_response.text = '<link rel="canonical" href="https://www.youtube.com/channel/UCZHmQk67mSJgfCCTn7xBfew">'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        urls = [
            "https://www.youtube.com/channel/UCbfYPyITQ-7l4upoX8nvctg",
            "https://www.youtube.com/@AIExplained-official",
        ]
        result = resolve_channels(urls)
        assert len(result) == 2
        assert result[0]["channel_id"] == "UCbfYPyITQ-7l4upoX8nvctg"
        assert result[1]["channel_id"] == "UCZHmQk67mSJgfCCTn7xBfew"
