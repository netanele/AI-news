"""AI summarization via Gemini Flash for video transcripts and daily digests."""

import logging
import os
import time

from google import genai

logger = logging.getLogger(__name__)

VIDEO_SUMMARY_PROMPT = (
    "Summarize this YouTube video transcript as 3-5 bullet points of key takeaways. "
    "Use \u2022 as bullet character. Be concise.\n\nTranscript:\n{transcript}"
)

DAILY_DIGEST_PROMPT = (
    "Write a brief 2-3 sentence news roundup for {day_date} based on these AI video summaries:\n\n{summaries}"
)

FAILURE_MESSAGE = "Summary generation failed \u2014 will retry next run."


def init_client(config):
    """Create and return a Gemini API client."""
    env_var = config["ai"]["apiKeyEnvVar"]
    api_key = os.environ.get(env_var)
    if not api_key:
        raise ValueError(
            f"Environment variable '{env_var}' is not set. "
            f"Set it with: export {env_var}=your-api-key"
        )
    return genai.Client(api_key=api_key)


def summarize_video(client, model, transcript):
    """Generate a bullet-point summary of a video transcript.

    Retries up to 3 times with exponential backoff (5s, 10s, 20s).
    Returns fallback message on final failure.
    """
    prompt = VIDEO_SUMMARY_PROMPT.format(transcript=transcript)
    return _call_with_retry(client, model, prompt)


def generate_daily_digest(client, model, day_date, video_summaries):
    """Generate a brief daily news roundup from video summaries.

    Retries up to 3 times with exponential backoff.
    Returns fallback message on final failure.
    """
    joined = "\n\n".join(video_summaries)
    prompt = DAILY_DIGEST_PROMPT.format(day_date=day_date, summaries=joined)
    return _call_with_retry(client, model, prompt)


def _call_with_retry(client, model, prompt, max_retries=3):
    """Call Gemini API with exponential backoff retry."""
    delays = [5, 10, 20]

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as e:
            logger.warning("Gemini API attempt %d/%d failed: %s", attempt, max_retries, e)
            if attempt < max_retries:
                delay = delays[attempt - 1] if attempt - 1 < len(delays) else delays[-1]
                time.sleep(delay)

    logger.error("Gemini API call failed after %d retries", max_retries)
    return FAILURE_MESSAGE
