"""Resolve YouTube channel URLs to channel IDs via HTML scraping."""

import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

CHANNEL_ID_PATTERN = re.compile(r"/channel/(UC[\w-]{22})")
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-News-Bot/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}
_REQUEST_DELAY = 1  # seconds between HTTP requests


def _extract_channel_id_from_html(html):
    """Extract channel ID from YouTube page HTML meta tags or canonical URL."""
    # Try meta og:url
    match = re.search(r'<meta\s+property="og:url"\s+content="([^"]*)"', html)
    if match:
        id_match = CHANNEL_ID_PATTERN.search(match.group(1))
        if id_match:
            return id_match.group(1)

    # Try link canonical
    match = re.search(r'<link\s+rel="canonical"\s+href="([^"]*)"', html)
    if match:
        id_match = CHANNEL_ID_PATTERN.search(match.group(1))
        if id_match:
            return id_match.group(1)

    # Try any /channel/ reference in page
    id_match = CHANNEL_ID_PATTERN.search(html)
    if id_match:
        return id_match.group(1)

    return None


def _extract_channel_name(url):
    """Extract a readable channel name from the URL."""
    # @handle format
    match = re.search(r"@([\w-]+)", url)
    if match:
        return match.group(1)
    # /c/custom format
    match = re.search(r"/c/([\w-]+)", url)
    if match:
        return match.group(1)
    # /channel/ID format
    match = re.search(r"/channel/([\w-]+)", url)
    if match:
        return match.group(1)
    return url


def resolve_channels(channel_urls):
    """Resolve channel URLs to channel IDs. Returns list of dicts with url, channel_id, channel_name."""
    resolved = []
    for url in channel_urls:
        try:
            # Direct /channel/ URL — extract ID without HTTP request
            direct_match = CHANNEL_ID_PATTERN.search(url)
            if direct_match:
                resolved.append({
                    "url": url,
                    "channel_id": direct_match.group(1),
                    "channel_name": _extract_channel_name(url),
                })
                logger.info("Resolved %s (direct) -> %s", url, direct_match.group(1))
                continue

            # Fetch page HTML and extract channel ID
            time.sleep(_REQUEST_DELAY)
            response = requests.get(url, headers=_HEADERS, timeout=15)
            response.raise_for_status()
            channel_id = _extract_channel_id_from_html(response.text)
            if channel_id:
                resolved.append({
                    "url": url,
                    "channel_id": channel_id,
                    "channel_name": _extract_channel_name(url),
                })
                logger.info("Resolved %s -> %s", url, channel_id)
            else:
                logger.warning("Could not extract channel ID from %s", url)
        except Exception as e:
            logger.warning("Failed to resolve channel %s: %s", url, e)

    return resolved
