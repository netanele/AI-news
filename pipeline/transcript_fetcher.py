"""Fetch YouTube video transcripts with retry logic and proxy support."""

import logging
import os
import time

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
)
from youtube_transcript_api.proxies import GenericProxyConfig

logger = logging.getLogger(__name__)

# Transient errors worth retrying from the same IP
RETRIABLE_EXCEPTIONS = (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    ConnectionError,
    TimeoutError,
    OSError,
)

# IP-level blocks — retrying from same IP won't help
IP_BLOCKED_EXCEPTIONS = (RequestBlocked,)


def _build_api():
    """Build YouTubeTranscriptApi with optional proxy from env."""
    proxy_url = os.environ.get("YOUTUBE_PROXY")
    if proxy_url:
        logger.info("Using proxy for transcript fetching")
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(
                http_url=proxy_url,
                https_url=proxy_url,
            )
        )
    return YouTubeTranscriptApi()


def fetch_transcripts(videos, max_retries=3, retry_delay=2):
    """Fetch transcripts for a list of videos with retry logic.

    Args:
        videos: List of video dicts (must have 'id' key).
        max_retries: Number of retry attempts per video.
        retry_delay: Seconds between retries.

    Returns:
        Updated video list with 'transcript' and 'transcriptAvailable' fields.
    """
    api = _build_api()
    ip_blocked = False

    for video in videos:
        video_id = video["id"]

        # If already IP-blocked, skip remaining transcript fetches
        if ip_blocked:
            video["transcript"] = None
            video["transcriptAvailable"] = False
            continue

        success = False

        for attempt in range(1, max_retries + 1):
            try:
                transcript = api.fetch(video_id)
                full_text = " ".join([snippet.text for snippet in transcript.snippets])
                video["transcript"] = full_text
                video["transcriptAvailable"] = True
                success = True
                logger.info("Transcript fetched for %s", video_id)
                break
            except IP_BLOCKED_EXCEPTIONS as e:
                logger.warning(
                    "YouTube IP blocked — skipping all remaining transcripts. "
                    "Set YOUTUBE_PROXY env var to use a proxy. Error: %s", type(e).__name__
                )
                ip_blocked = True
                break
            except RETRIABLE_EXCEPTIONS as e:
                logger.warning(
                    "Transcript fetch attempt %d/%d failed for %s: %s",
                    attempt, max_retries, video_id, e
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)
            except Exception as e:
                # Non-retriable error (programming bug, unexpected API change)
                logger.error("Non-retriable transcript error for %s: %s", video_id, e)
                break

        if not success:
            video["transcript"] = None
            video["transcriptAvailable"] = False
            logger.warning("Transcript unavailable for %s", video_id)

    fetched = sum(1 for v in videos if v.get("transcriptAvailable"))
    logger.info("Transcripts: %d/%d fetched successfully", fetched, len(videos))

    return videos
