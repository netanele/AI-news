"""Fetch and parse YouTube RSS feeds for video discovery."""

import logging
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

logger = logging.getLogger(__name__)

RSS_URL_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
THUMBNAIL_URL_TEMPLATE = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
_REQUEST_DELAY = 1  # seconds between RSS fetches
_MAX_RETRIES = 3
_RETRY_INTERVAL = 180  # seconds between retries (3 minutes)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, application/atom+xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_videos(channels, days_to_show):
    """Fetch recent videos from YouTube RSS feeds for all channels.

    Returns a flat list of video dicts within the date window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_show)
    all_videos = []

    failed_channels = []

    for i, channel in enumerate(channels):
        if i > 0:
            time.sleep(_REQUEST_DELAY)
        videos = _fetch_channel_feed(channel, cutoff)
        if videos is not None:
            all_videos.extend(videos)
            logger.info("Fetched %d videos from %s (within %d-day window)",
                        len(videos), channel["channel_name"], days_to_show)
        else:
            failed_channels.append(channel)

    # Retry failed channels up to _MAX_RETRIES times
    for attempt in range(1, _MAX_RETRIES + 1):
        if not failed_channels:
            break
        names = ", ".join(c["channel_name"] for c in failed_channels)
        logger.info("Retry %d/%d for %d channel(s) in %ds: %s",
                     attempt, _MAX_RETRIES, len(failed_channels), _RETRY_INTERVAL, names)
        time.sleep(_RETRY_INTERVAL)

        still_failed = []
        for channel in failed_channels:
            videos = _fetch_channel_feed(channel, cutoff)
            if videos is not None:
                all_videos.extend(videos)
                logger.info("Retry succeeded for %s — %d videos", channel["channel_name"], len(videos))
            else:
                still_failed.append(channel)
        failed_channels = still_failed

    if failed_channels:
        names = ", ".join(c["channel_name"] for c in failed_channels)
        logger.warning("RSS permanently failed for: %s", names)

    return all_videos


def _fetch_channel_feed(channel, cutoff):
    """Fetch a single channel's RSS feed. Returns list of videos or None on failure."""
    try:
        feed_url = RSS_URL_TEMPLATE.format(channel_id=channel["channel_id"])
        response = requests.get(feed_url, headers=_HEADERS, timeout=15)

        if response.status_code != 200:
            logger.warning("RSS feed HTTP %d for %s", response.status_code, channel["channel_name"])
            return None

        feed = feedparser.parse(response.content)

        if feed.bozo and not feed.entries:
            logger.warning("Feed parse error for %s: %s", channel["channel_name"], feed.bozo_exception)
            return None

        videos = []
        for entry in feed.entries:
            published_str = entry.get("published", "")
            try:
                published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning("Skipping entry with unparseable date: %s", published_str)
                continue

            if published_dt < cutoff:
                continue

            entry_id = getattr(entry, "id", None) or ""
            if not entry_id or ":" not in entry_id:
                logger.warning("Skipping entry with missing/malformed id: %s", entry_id)
                continue
            video_id = entry_id.split(":")[-1]
            if not video_id:
                continue
            videos.append({
                "id": video_id,
                "title": entry.get("title", "Untitled"),
                "publishedAt": published_str,
                "duration": None,  # YouTube RSS doesn't include duration
                "thumbnailUrl": THUMBNAIL_URL_TEMPLATE.format(video_id=video_id),
                "videoUrl": entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                "channelName": channel["channel_name"],
                "channelUrl": channel["url"],
            })

        return videos

    except Exception as e:
        logger.warning("Failed to fetch RSS for %s: %s", channel["channel_name"], e)
        return None
