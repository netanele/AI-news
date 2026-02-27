"""Fetch and parse YouTube RSS feeds for video discovery."""

import logging
import time
from datetime import datetime, timedelta, timezone

import feedparser

logger = logging.getLogger(__name__)

RSS_URL_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
THUMBNAIL_URL_TEMPLATE = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
_REQUEST_DELAY = 1  # seconds between RSS fetches


def fetch_videos(channels, days_to_show):
    """Fetch recent videos from YouTube RSS feeds for all channels.

    Returns a flat list of video dicts within the date window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_show)
    all_videos = []

    for i, channel in enumerate(channels):
        try:
            if i > 0:
                time.sleep(_REQUEST_DELAY)
            feed_url = RSS_URL_TEMPLATE.format(channel_id=channel["channel_id"])
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning("Feed parse error for %s: %s", channel["channel_name"], feed.bozo_exception)
                continue

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
                all_videos.append({
                    "id": video_id,
                    "title": entry.get("title", "Untitled"),
                    "publishedAt": published_str,
                    "duration": None,  # YouTube RSS doesn't include duration
                    "thumbnailUrl": THUMBNAIL_URL_TEMPLATE.format(video_id=video_id),
                    "videoUrl": entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                    "channelName": channel["channel_name"],
                    "channelUrl": channel["url"],
                })

            logger.info("Fetched %d videos from %s (within %d-day window)",
                        sum(1 for v in all_videos if v["channelName"] == channel["channel_name"]),
                        channel["channel_name"], days_to_show)

        except Exception as e:
            logger.warning("Failed to fetch RSS for %s: %s", channel["channel_name"], e)

    return all_videos
