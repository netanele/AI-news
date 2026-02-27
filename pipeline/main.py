"""Pipeline orchestrator — 8-stage sequential execution."""

import logging
import sys

from pipeline import (
    config_loader,
    channel_resolver,
    rss_fetcher,
    transcript_fetcher,
    summarizer,
    data_manager,
    writer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline(config_path="config.json", data_path="data.json"):
    """Execute the full 8-stage pipeline."""
    try:
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

        # Stage 4: Fetch RSS feeds
        logger.info("Stage 4: Fetching RSS feeds")
        all_videos = rss_fetcher.fetch_videos(channels, config["display"]["daysToShow"])
        logger.info("Found %d total videos in RSS feeds", len(all_videos))

        # Stage 5: Filter to new videos only
        new_videos = data_manager.filter_new_videos(all_videos, existing_ids)
        if not new_videos:
            logger.info("No new videos found — keeping existing data.json unchanged")
            return
        logger.info("Stage 5: %d new videos to process", len(new_videos))

        # Stage 6: Fetch transcripts
        logger.info("Stage 6: Fetching transcripts for %d videos", len(new_videos))
        new_videos = transcript_fetcher.fetch_transcripts(new_videos)

        # Stage 7: Generate summaries
        logger.info("Stage 7: Generating summaries")
        client = summarizer.init_client(config)
        model = config["ai"]["model"]

        for video in new_videos:
            if video["transcriptAvailable"]:
                video["summary"] = summarizer.summarize_video(client, model, video["transcript"])
            else:
                video["summary"] = "Transcript not available for this video."
            # Remove raw transcript from output (not needed in data.json)
            video.pop("transcript", None)

        # Stage 8: Merge, group, regenerate digests, and write
        logger.info("Stage 8: Merging data and writing output")
        merged_data = data_manager.merge_and_group(existing_data, new_videos, config["display"]["daysToShow"])

        changed_days = data_manager.get_changed_days(existing_data, merged_data)
        if changed_days:
            logger.info("Regenerating daily digests for %d days: %s", len(changed_days), changed_days)
            for day in merged_data["days"]:
                if day["date"] in changed_days:
                    video_summaries = []
                    for ch in day["channels"]:
                        for v in ch["videos"]:
                            if v.get("summary") and not v["summary"].startswith("Transcript not available"):
                                video_summaries.append(v["summary"])
                    if video_summaries:
                        day["dailyDigest"] = summarizer.generate_daily_digest(
                            client, model, day["date"], video_summaries
                        )

        writer.write_data(merged_data, data_path)

        total_days = len(merged_data["days"])
        logger.info("Pipeline complete. Processed %d new videos across %d days.", len(new_videos), total_days)

    except Exception as e:
        logger.error("Pipeline failed: %s — data.json NOT written (preserving existing data)", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
