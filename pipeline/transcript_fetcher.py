"""Fetch YouTube video transcripts with retry logic."""

import logging
import time

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

# Only retry on transient/known YouTube errors, not programming bugs
RETRIABLE_EXCEPTIONS = (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    ConnectionError,
    TimeoutError,
    OSError,
)


def fetch_transcripts(videos, max_retries=3, retry_delay=300):
    """Fetch transcripts for a list of videos with retry logic.

    Args:
        videos: List of video dicts (must have 'id' key).
        max_retries: Number of retry attempts per video.
        retry_delay: Seconds between retries (default 300s for GitHub Actions).

    Returns:
        Updated video list with 'transcript' and 'transcriptAvailable' fields.
    """
    api = YouTubeTranscriptApi()

    for video in videos:
        video_id = video["id"]
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
            logger.warning("Transcript unavailable for %s after %d attempts", video_id, max_retries)

    return videos
