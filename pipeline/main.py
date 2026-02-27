"""Pipeline orchestrator — 8-stage sequential execution."""

import logging
import sys

from pipeline import (
    config_loader,
    channel_resolver,
    rss_fetcher,
    # transcript_fetcher,
    # summarizer,
    data_manager,
    writer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class PipelineStatus:
    """Track warnings and errors during pipeline execution."""

    def __init__(self):
        self.issues = []

    def warn(self, msg):
        self.issues.append(msg)

    def to_dict(self):
        if not self.issues:
            return {"status": "ok", "issues": []}
        return {"status": "partial", "issues": self.issues}


def run_pipeline(config_path="config.json", data_path="data.json"):
    """Execute the full 8-stage pipeline."""
    try:
        status = PipelineStatus()

        # Stage 1: Load config
        logger.info("Stage 1: Loading config from %s", config_path)
        config = config_loader.load_config(config_path)

        # Stage 2: Load existing data
        logger.info("Stage 2: Loading existing data from %s", data_path)
        existing_data = data_manager.load_existing_data(data_path)
        existing_ids = data_manager.get_existing_video_ids(existing_data)
        logger.info("Found %d existing videos", len(existing_ids))

        # Stage 3: Resolve channels
        logger.info("Stage 3: Resolving %d channel URLs", len(config["channels"]))
        channels = channel_resolver.resolve_channels(config["channels"])
        if not channels:
            logger.warning("No channels resolved — exiting")
            return

        failed_channels = len(config["channels"]) - len(channels)
        if failed_channels > 0:
            status.warn(f"{failed_channels} channel(s) could not be resolved")

        # Stage 4: Fetch RSS feeds
        logger.info("Stage 4: Fetching RSS feeds")
        all_videos = rss_fetcher.fetch_videos(channels, config["display"]["daysToShow"])
        logger.info("Found %d total videos in RSS feeds", len(all_videos))

        rss_channels = set(v["channelName"] for v in all_videos)
        rss_failed = [c["channel_name"] for c in channels if c["channel_name"] not in rss_channels]
        if rss_failed:
            status.warn(f"RSS unavailable for: {', '.join(rss_failed)}")

        # Stage 5: Filter to new videos only
        new_videos = data_manager.filter_new_videos(all_videos, existing_ids)
        if not new_videos:
            logger.info("No new videos found — keeping existing data.json unchanged")
            # Still update status in existing data
            existing_data["pipelineStatus"] = status.to_dict()
            writer.write_data(existing_data, data_path)
            return
        logger.info("Stage 5: %d new videos to process", len(new_videos))

        # Stage 6: Fetch transcripts (disabled — re-enable when proxy is configured)
        # logger.info("Stage 6: Fetching transcripts for %d videos", len(new_videos))
        # new_videos = transcript_fetcher.fetch_transcripts(new_videos)
        #
        # transcripts_ok = sum(1 for v in new_videos if v.get("transcriptAvailable"))
        # if transcripts_ok == 0:
        #     status.warn("Transcripts blocked (cloud IP) — set YOUTUBE_PROXY secret for transcripts")
        # elif transcripts_ok < len(new_videos):
        #     status.warn(f"Transcripts fetched for {transcripts_ok}/{len(new_videos)} videos")

        # Stage 7: Generate summaries (disabled — re-enable when transcripts are available)
        # logger.info("Stage 7: Generating summaries")
        # summary_errors = 0
        # try:
        #     client = summarizer.init_client(config)
        #     model = config["ai"]["model"]
        #
        #     for video in new_videos:
        #         if video["transcriptAvailable"]:
        #             video["summary"] = summarizer.summarize_video(client, model, video["transcript"])
        #             if video["summary"].startswith("Summary generation failed"):
        #                 summary_errors += 1
        #         else:
        #             video["summary"] = "Transcript not available for this video."
        #         # Remove raw transcript from output (not needed in data.json)
        #         video.pop("transcript", None)
        # except Exception as e:
        #     logger.warning("Summarizer init failed: %s", e)
        #     summary_errors = len(new_videos)
        #     for video in new_videos:
        #         if "summary" not in video:
        #             video["summary"] = "Transcript not available for this video."
        #         video.pop("transcript", None)
        #
        # if summary_errors > 0:
        #     status.warn(f"AI summaries failed for {summary_errors} video(s) — check Gemini API quota")

        # Set defaults while transcripts/summaries are disabled
        for video in new_videos:
            video["transcriptAvailable"] = False
            video["summary"] = ""

        # Stage 8: Merge, group, and write
        logger.info("Stage 8: Merging data and writing output")
        merged_data = data_manager.merge_and_group(existing_data, new_videos, config["display"]["daysToShow"])

        # Daily digest generation (disabled — re-enable with summaries)
        # changed_days = data_manager.get_changed_days(existing_data, merged_data)
        # if changed_days and summary_errors == 0:
        #     logger.info("Regenerating daily digests for %d days: %s", len(changed_days), changed_days)
        #     for day in merged_data["days"]:
        #         if day["date"] in changed_days:
        #             video_summaries = []
        #             for ch in day["channels"]:
        #                 for v in ch["videos"]:
        #                     if v.get("summary") and not v["summary"].startswith("Transcript not available"):
        #                         video_summaries.append(v["summary"])
        #             if video_summaries:
        #                 day["dailyDigest"] = summarizer.generate_daily_digest(
        #                     client, model, day["date"], video_summaries
        #                 )

        merged_data["pipelineStatus"] = status.to_dict()
        writer.write_data(merged_data, data_path)

        total_days = len(merged_data["days"])
        logger.info("Pipeline complete. Processed %d new videos across %d days.", len(new_videos), total_days)
        if status.issues:
            logger.info("Pipeline issues: %s", "; ".join(status.issues))

    except Exception as e:
        logger.error("Pipeline failed: %s — data.json NOT written (preserving existing data)", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
