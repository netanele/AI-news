---
title: 'AI News Dashboard — YouTube Aggregator with AI Summaries'
slug: 'ai-news-dashboard'
created: '2026-02-27'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python 3.11+ (data pipeline)'
  - 'youtube-transcript-api 1.2.x (transcript extraction)'
  - 'feedparser 6.x (RSS parsing)'
  - 'google-genai (Gemini Flash SDK — replaces archived google-generativeai)'
  - 'requests (HTTP for channel URL resolution)'
  - 'HTML/CSS/JS (static frontend — no framework)'
  - 'GitHub Actions (CI/CD cron)'
  - 'GitHub Pages (hosting)'
files_to_modify:
  - 'pipeline/main.py'
  - 'pipeline/config_loader.py'
  - 'pipeline/channel_resolver.py'
  - 'pipeline/rss_fetcher.py'
  - 'pipeline/transcript_fetcher.py'
  - 'pipeline/summarizer.py'
  - 'pipeline/data_manager.py'
  - 'pipeline/writer.py'
  - 'config.json'
  - 'index.html'
  - 'css/style.css'
  - 'js/app.js'
  - 'js/settings.js'
  - 'settings.html'
  - '.github/workflows/pipeline.yml'
  - 'requirements.txt'
  - 'tests/test_channel_resolver.py'
  - 'tests/test_rss_fetcher.py'
  - 'tests/test_data_manager.py'
  - 'tests/test_summarizer.py'
code_patterns:
  - 'Modular pipeline — each stage is a separate module with a single-purpose function'
  - 'Config-driven — all runtime values from config.json, secrets from env vars'
  - 'Atomic output — data.json only written at final stage'
  - 'Incremental processing — diff new vs existing, skip already-processed videos'
  - 'Graceful degradation — individual failures never halt the pipeline'
  - 'Layered summarization — video summaries first, daily digests from summaries'
test_patterns:
  - 'pytest for unit tests'
  - 'Mocked HTTP responses for RSS, transcript, and AI API calls'
  - 'Fixture-based test data (sample RSS XML, sample transcripts, sample config)'
  - 'Manual E2E test with real channels for final validation'
---

# Tech-Spec: AI News Dashboard — YouTube Aggregator with AI Summaries

**Created:** 2026-02-27

## Overview

### Problem Statement

There is no free, automated way to get a daily digest of AI news from YouTube channels — with AI-generated summaries — without manually watching hours of video. Existing tools either cost money, require manual curation, or don't provide summaries.

### Solution

A zero-cost static pipeline that runs on GitHub Actions (Sun–Thu, 3x daily), fetches YouTube videos via RSS, extracts transcripts using `youtube-transcript-api`, generates AI summaries via Gemini Flash free tier, and writes a `data.json` file consumed by a dark-mode static HTML dashboard hosted on GitHub Pages. The pipeline is incremental — it only processes new videos and reuses existing summaries.

### Scope

**In Scope:**

- Python data pipeline (8-stage incremental processing)
- RSS-based video discovery (no API key needed)
- Transcript extraction via `youtube-transcript-api`
- AI summarization via Gemini Flash free tier (video summaries + daily digests)
- Static HTML/CSS/JS dashboard with dark mode (default) and light mode toggle
- Days-first layout with channel groupings, collapsible day sections
- Inline embedded YouTube player
- GitHub Actions workflow (Sun–Thu, 3x daily at 10:00/13:00/18:00 Israel time)
- Universal retry logic (3x, 5-min intervals) for transcript fetches and AI calls
- Error fallback states in frontend (no data, failed summaries, unavailable transcripts)
- `config.json` for channels/AI settings, `data.json` for pipeline output
- Settings page with localStorage for display preferences
- GitHub Pages deployment
- End-to-end test with real channels

**Out of Scope:**

- User authentication or multi-user support
- Database or server-side backend
- Video upload or content creation
- Paid API tiers or non-free hosting
- Mobile native app
- Comments or social features
- Custom transcript generation (relies on YouTube auto-captions only)

## Context for Development

### Codebase Patterns

- **Greenfield project (Confirmed Clean Slate)** — no existing code; all files created from scratch
- **Decoupled architecture** — pipeline (Python) and frontend (HTML/JS) communicate only via `data.json`
- **Modular pipeline** — each of the 8 stages lives in its own Python module with a clear single-purpose function
- **Config-driven** — all channel lists, AI settings, and display settings live in `config.json`; secrets come from environment variables
- **Atomic writes** — `data.json` is only written at the final pipeline stage; partial runs leave existing data intact
- **Incremental processing** — pipeline reads existing `data.json`, diffs against RSS results, only processes new videos
- **Layered summarization** — individual video summaries first, then daily digests built from those summaries (not raw transcripts)
- **Graceful degradation** — individual video/channel failures never halt the pipeline; errors recorded in data with fallback states

### Project File Structure

```
AI-news/
├── pipeline/                  # Python data pipeline
│   ├── main.py                # 8-stage orchestrator entry point
│   ├── config_loader.py       # Load & validate config.json
│   ├── channel_resolver.py    # Resolve @handle URLs → channel IDs
│   ├── rss_fetcher.py         # Fetch & parse YouTube RSS feeds
│   ├── transcript_fetcher.py  # Fetch transcripts with retry
│   ├── summarizer.py          # Gemini Flash API calls
│   ├── data_manager.py        # Merge, window, group by day/channel
│   └── writer.py              # Write final data.json
├── tests/                     # pytest unit tests
│   ├── test_channel_resolver.py
│   ├── test_rss_fetcher.py
│   ├── test_data_manager.py
│   └── test_summarizer.py
├── js/                        # Frontend JavaScript
│   ├── app.js                 # Load data.json, render dashboard
│   └── settings.js            # localStorage preferences
├── css/
│   └── style.css              # Dark/light mode styles
├── .github/
│   └── workflows/
│       └── pipeline.yml       # GitHub Actions cron workflow
├── index.html                 # Main dashboard page
├── settings.html              # Settings page
├── config.json                # Pipeline configuration
├── data.json                  # Pipeline output (git-committed)
└── requirements.txt           # Python dependencies
```

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `_bmad-output/brainstorming/brainstorming-session-2026-02-25.md` | Full brainstorming session with architecture decisions, data model, UX layout, failure scenarios |

### Technical Decisions

1. **`google-genai` SDK (NOT `google-generativeai`)** — the old package was archived Dec 2025. New API: `from google import genai; client = genai.Client(api_key=...); response = client.models.generate_content(model='gemini-2.0-flash', contents='...')`
2. **Gemini Flash free tier limits** — ~20 RPM, ~250 RPD. Incremental processing keeps us well within limits (most runs = few new videos). If limits tighten further, the config supports swapping providers.
3. **RSS feeds** for video discovery — zero API keys, returns ~15 recent videos per channel, sufficient for 7-day window
4. **youtube-transcript-api** for transcript extraction — v1.2.x. API: `YouTubeTranscriptApi().fetch(video_id)`. Key exceptions: `TranscriptsDisabled`, `NoTranscriptFound`, `RequestBlocked`, `IpBlocked`, `VideoUnavailable`
5. **Cloud IP blocking risk** — YouTube blocks cloud provider IPs for transcript fetching. GitHub Actions runners may hit `RequestBlocked`. Mitigation: retry logic (3x) + graceful fallback ("transcript not available") + re-attempt on next run. This is accepted risk — most transcripts should succeed over multiple runs.
6. **Channel URL resolution via HTML scrape** — fetch the YouTube channel page, extract channel ID from meta tags or canonical URL. No YouTube Data API key needed. Handles `@handle`, `/c/custom`, and `/channel/ID` URL formats.
7. **Single rolling `data.json`** — overwritten each run, contains only last N days (default 7), no data accumulation
8. **GitHub Actions cron** — Sun–Thu at 07:00/10:00/15:00 UTC (10:00/13:00/18:00 Israel time). No Friday/Saturday runs (Shabbat).
9. **Secrets in GitHub Secrets** — `config.json` references env var names (e.g., `GEMINI_API_KEY`), not actual keys
10. **feedparser field mapping** — `entry.id` format is `yt:video:VIDEO_ID` (extract after last `:`); `entry.published_parsed` for structured datetime; `entry.title`, `entry.link`, `entry.author` for metadata

### Key API Patterns

**Gemini Flash (google-genai):**
```python
from google import genai
client = genai.Client(api_key=os.environ[config["ai"]["apiKeyEnvVar"]])
response = client.models.generate_content(
    model=config["ai"]["model"],  # "gemini-2.0-flash"
    contents="Summarize this transcript in bullet points:\n\n" + transcript_text
)
summary = response.text
```

**YouTube Transcript API:**
```python
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
transcript = api.fetch(video_id)
full_text = " ".join([snippet.text for snippet in transcript.snippets])
```

**YouTube RSS Feed:**
```python
import feedparser
feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
feed = feedparser.parse(feed_url)
for entry in feed.entries:
    video_id = entry.id.split(":")[-1]  # "yt:video:ABC123" → "ABC123"
```

## Implementation Plan

### Tasks

#### Phase 1: Project Setup & Core Pipeline

- [x] Task 1: Initialize project structure and dependencies
  - File: `requirements.txt`
  - Action: Create file with pinned dependencies: `feedparser>=6.0`, `youtube-transcript-api>=1.2`, `google-genai>=1.0`, `requests>=2.31`, `pytest>=7.0`
  - File: `config.json`
  - Action: Create with default config — 2 starter channels (TwoMinutePapers, AIExplained-official), Gemini Flash settings, 7-day display window. See Config Model section for exact structure.
  - File: `pipeline/__init__.py`
  - Action: Create empty `__init__.py` for package imports
  - File: `tests/__init__.py`
  - Action: Create empty `__init__.py` for test discovery

- [x] Task 2: Build config loader module
  - File: `pipeline/config_loader.py`
  - Action: Create `load_config(config_path="config.json") -> dict` function. Read and parse JSON file. Validate required keys exist: `ai.provider`, `ai.model`, `ai.apiKeyEnvVar`, `display.daysToShow`, `channels` (non-empty list). Raise `ValueError` with descriptive message on missing/invalid keys. Return parsed config dict.

- [x] Task 3: Build channel resolver module
  - File: `pipeline/channel_resolver.py`
  - Action: Create `resolve_channels(channel_urls: list[str]) -> list[dict]` function. For each URL: (1) If URL contains `/channel/`, extract channel ID directly. (2) Otherwise, HTTP GET the URL, parse HTML response to find `<meta property="og:url" content="...">` or `<link rel="canonical" href="...">` which contains the `/channel/CHANNEL_ID` path. (3) Return list of dicts: `{"url": original_url, "channel_id": resolved_id, "channel_name": parsed_name}`. (4) On failure (HTTP error, parse error), log warning, skip channel, continue with remaining.
  - File: `tests/test_channel_resolver.py`
  - Action: Test with mocked HTML responses for `@handle`, `/c/custom`, and `/channel/ID` URL formats. Test that invalid URLs are skipped gracefully without halting.

- [x] Task 4: Build RSS fetcher module
  - File: `pipeline/rss_fetcher.py`
  - Action: Create `fetch_videos(channels: list[dict], days_to_show: int) -> list[dict]` function. For each channel: (1) Build RSS URL from channel_id. (2) Parse with `feedparser.parse()`. (3) For each entry, extract: `video_id` (from `entry.id.split(":")[-1]`), `title` (`entry.title`), `published_at` (`entry.published`), `video_url` (`entry.link`), `channel_name`, `channel_url`. (4) Build `thumbnail_url` as `https://i.ytimg.com/vi/{video_id}/hqdefault.jpg`. (5) Filter to entries within last `days_to_show` days based on `published_at`. (6) Return flat list of video dicts. On feed parse failure, log warning, skip channel, continue.
  - File: `tests/test_rss_fetcher.py`
  - Action: Test with mocked feedparser responses containing sample YouTube Atom XML. Verify field extraction, date filtering, and graceful channel-skip on error.

- [x] Task 5: Build transcript fetcher module with retry logic
  - File: `pipeline/transcript_fetcher.py`
  - Action: Create `fetch_transcripts(videos: list[dict], max_retries=3, retry_delay=300) -> list[dict]` function. For each video: (1) Call `YouTubeTranscriptApi().fetch(video_id)`. (2) Concatenate all snippet texts with spaces into `full_text`. (3) On success, set `video["transcript"] = full_text` and `video["transcriptAvailable"] = True`. (4) On exception (`TranscriptsDisabled`, `NoTranscriptFound`, `RequestBlocked`, `IpBlocked`, `VideoUnavailable`): retry up to `max_retries` times with `retry_delay` seconds between attempts. (5) On final failure, set `video["transcript"] = None` and `video["transcriptAvailable"] = False`. (6) Never halt — always continue to next video. Return updated video list.
  - Notes: Import all exception types from `youtube_transcript_api`. Use `time.sleep(retry_delay)` between retries. Log each retry attempt and final failure with video ID.

- [x] Task 6: Build summarizer module
  - File: `pipeline/summarizer.py`
  - Action: Create two functions:
    - `summarize_video(client, model: str, transcript: str) -> str`: Send prompt "Summarize this YouTube video transcript as 3-5 bullet points of key takeaways. Use • as bullet character. Be concise.\n\nTranscript:\n{transcript}" to Gemini. Return `response.text`. On API error, retry up to 3 times with exponential backoff (5s, 10s, 20s). On final failure, return `"Summary generation failed — will retry next run."`.
    - `generate_daily_digest(client, model: str, day_date: str, video_summaries: list[str]) -> str`: Send prompt "Write a brief 2-3 sentence news roundup for {day_date} based on these AI video summaries:\n\n{joined_summaries}" to Gemini. Return `response.text`. Same retry/fallback logic.
    - `init_client(config: dict) -> genai.Client`: Create and return `genai.Client(api_key=os.environ[config["ai"]["apiKeyEnvVar"]])`.
  - File: `tests/test_summarizer.py`
  - Action: Mock `genai.Client` and `generate_content` responses. Test prompt construction, retry logic on API errors, fallback message on final failure.

- [x] Task 7: Build data manager module
  - File: `pipeline/data_manager.py`
  - Action: Create these functions:
    - `load_existing_data(data_path="data.json") -> dict`: Read and parse existing data.json. Return empty structure `{"lastUpdated": None, "config": {}, "days": []}` if file doesn't exist or is invalid JSON.
    - `get_existing_video_ids(existing_data: dict) -> set[str]`: Extract all video IDs from existing data to enable incremental diffing.
    - `filter_new_videos(all_videos: list[dict], existing_ids: set[str]) -> list[dict]`: Return only videos whose ID is not in `existing_ids`.
    - `merge_and_group(existing_data: dict, new_videos: list[dict], days_to_show: int) -> dict`: (1) Combine existing videos with new videos. (2) Group by date (YYYY-MM-DD from `publishedAt`). (3) Within each date, group by channel. (4) Drop days older than `days_to_show`. (5) Sort days newest-first. (6) Return full data structure matching the Data Model.
    - `get_changed_days(existing_data: dict, merged_data: dict) -> list[str]`: Compare day-by-day video counts. Return list of date strings for days that have new content (need digest regeneration).
  - File: `tests/test_data_manager.py`
  - Action: Test merging new videos into empty data, merging into existing data without duplicates, day windowing (dropping old days), correct grouping by date then channel, and changed-day detection.

- [x] Task 8: Build writer module
  - File: `pipeline/writer.py`
  - Action: Create `write_data(data: dict, output_path="data.json")` function. Set `data["lastUpdated"]` to current UTC ISO timestamp. Write JSON with `json.dump(data, f, indent=2, ensure_ascii=False)`. This is the atomic write point — only called at pipeline end.

- [x] Task 9: Build pipeline orchestrator
  - File: `pipeline/main.py`
  - Action: Create `run_pipeline(config_path="config.json", data_path="data.json")` function that executes all 8 stages in sequence:
    1. `config = config_loader.load_config(config_path)`
    2. `existing_data = data_manager.load_existing_data(data_path)`
    3. `existing_ids = data_manager.get_existing_video_ids(existing_data)`
    4. `channels = channel_resolver.resolve_channels(config["channels"])`
    5. `all_videos = rss_fetcher.fetch_videos(channels, config["display"]["daysToShow"])`
    6. `new_videos = data_manager.filter_new_videos(all_videos, existing_ids)`
    7. If `new_videos` is empty, log "No new videos found" and exit early (keep existing data.json unchanged).
    8. `new_videos = transcript_fetcher.fetch_transcripts(new_videos)`
    9. `client = summarizer.init_client(config)`
    10. For each new video with `transcriptAvailable == True`: `video["summary"] = summarizer.summarize_video(client, config["ai"]["model"], video["transcript"])`
    11. For each new video with `transcriptAvailable == False`: `video["summary"] = "Transcript not available for this video."`
    12. `merged_data = data_manager.merge_and_group(existing_data, new_videos, config["display"]["daysToShow"])`
    13. `changed_days = data_manager.get_changed_days(existing_data, merged_data)`
    14. For each changed day: regenerate daily digest via `summarizer.generate_daily_digest()`
    15. `writer.write_data(merged_data, data_path)`
    16. Log summary: "Pipeline complete. Processed {n} new videos across {d} days."
  - Add `if __name__ == "__main__": run_pipeline()` for direct execution.
  - Notes: Wrap the entire pipeline in try/except at the top level. On unhandled error, log the error but do NOT write data.json (preserves existing data — atomic safety). Use Python `logging` module throughout with INFO level for progress and WARNING for failures.

#### Phase 2: Full Dashboard Frontend

- [x] Task 10: Build main dashboard HTML structure
  - File: `index.html`
  - Action: Create semantic HTML page with: (1) `<header>` — site title "AI News Dashboard", "Last updated: X" timestamp, dark/light mode toggle button, link to settings.html. (2) `<main id="dashboard">` — container for dynamically rendered day sections. (3) `<footer>` — "Powered by Gemini Flash" attribution. Link `css/style.css` and `js/app.js`. Include viewport meta tag for responsive display.

- [x] Task 11: Build dashboard JavaScript (app.js)
  - File: `js/app.js`
  - Action: Create `app.js` with the following functions:
    - `async loadData()`: Fetch `data.json`, parse JSON. On fetch error, show "Data unavailable, check back later" fallback message in `#dashboard`.
    - `renderDashboard(data)`: (1) Set "Last updated" header from `data.lastUpdated` as relative time ("2 hours ago"). (2) For each day in `data.days`: create a `<section class="day-section">` with date heading (formatted as "Wednesday, Feb 26"), daily digest paragraph, and channel groups. (3) Today's section starts expanded (`open` attribute on `<details>`), older days collapsed.
    - `renderChannel(channel)`: For each channel, render channel name header and video cards.
    - `renderVideoCard(video)`: Render card with: thumbnail image, title, channel name, duration badge, summary text (or "Transcript not available" / "Summary generation failed" fallback), and "Watch" button. Clicking the card or "Watch" toggles an inline `<iframe>` YouTube embed (`https://www.youtube.com/embed/{video.id}`).
    - `togglePlayer(videoId, containerEl)`: Insert/remove YouTube iframe embed in the card.
    - `initTheme()`: Read `localStorage.getItem("theme")` — default to "dark". Apply `data-theme` attribute to `<html>`. Wire toggle button to switch and persist.
    - `formatRelativeTime(isoString)`: Convert ISO timestamp to "X hours ago" / "X days ago" format.
    - Call `loadData()` on `DOMContentLoaded`.

- [x] Task 12: Build CSS styles with dark/light mode
  - File: `css/style.css`
  - Action: Create stylesheet with:
    - CSS custom properties on `[data-theme="dark"]` (default): `--bg: #0d1117`, `--surface: #161b22`, `--text: #e6edf3`, `--text-muted: #8b949e`, `--accent: #58a6ff`, `--border: #30363d`
    - `[data-theme="light"]` overrides: `--bg: #ffffff`, `--surface: #f6f8fa`, `--text: #1f2328`, etc.
    - Layout: max-width 900px, centered, responsive padding
    - Header: flexbox row, title left, controls right (toggle + settings link)
    - Day sections: `<details>` element styling, date as heading, digest as italic paragraph
    - Video cards: flexbox row (thumbnail left, content right), border-bottom separator, hover highlight
    - Thumbnail: 168×94px (YouTube default), border-radius
    - Duration badge: absolute positioned on thumbnail, dark bg, small white text
    - Summary text: pre-wrap for bullet points, muted color
    - Inline player: 16:9 aspect ratio container, full-width iframe
    - Fallback states: centered muted text for "Data unavailable" and "Transcript not available"
    - Responsive: stack video cards vertically below 600px width

- [x] Task 13: Build settings page
  - File: `settings.html`
  - Action: Create settings page with: (1) Back link to index.html. (2) Display settings section — "Days to show" number selector (reads/writes `localStorage.getItem("daysFilter")`). (3) Theme toggle (same as main page). (4) "About" section explaining what the dashboard does and linking to the GitHub repo. Link `css/style.css` and `js/settings.js`.
  - File: `js/settings.js`
  - Action: Create script that: (1) Reads `localStorage` values for `theme` and `daysFilter` on load. (2) Populates form fields with current values. (3) On change, writes to `localStorage`. (4) `daysFilter` is used client-side only — `app.js` reads it to filter which days to display (the full `data.json` always has `config.daysToShow` days from the pipeline).

#### Phase 3: Production Hardening

- [x] Task 14: Add retry logic wrapper utility
  - File: `pipeline/transcript_fetcher.py` (update)
  - Action: Verify retry logic is implemented per Task 5. If `retry_delay=300` (5 min) is too slow for local development, add an optional `retry_delay` parameter so it can be overridden in tests and local runs. The default 300s is for GitHub Actions where we want to space out retries.
  - File: `pipeline/summarizer.py` (update)
  - Action: Verify retry logic is implemented per Task 6 with exponential backoff. Catch `google.genai.errors.ClientError` (429 rate limits) and `google.genai.errors.ServerError` (5xx). Log each retry.

- [x] Task 15: Build GitHub Actions workflow
  - File: `.github/workflows/pipeline.yml`
  - Action: Create workflow with:
    - `name: AI News Pipeline`
    - Triggers: `schedule` with 3 cron entries for Sun–Thu at 07:00, 10:00, 15:00 UTC. Cron expressions: `0 7 * * 0-4`, `0 10 * * 0-4`, `0 15 * * 0-4` (note: cron uses 0=Sun, 4=Thu). Also `workflow_dispatch` for manual runs.
    - Job `run-pipeline`:
      - `runs-on: ubuntu-latest`
      - Steps: (1) Checkout repo. (2) Set up Python 3.11. (3) `pip install -r requirements.txt`. (4) `python -m pipeline.main` with env `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`. (5) Check if `data.json` changed via `git diff --name-only`. (6) If changed: `git config user.name "github-actions"`, `git config user.email "github-actions@github.com"`, `git add data.json`, `git commit -m "Update data.json"`, `git push`.
    - Notes: The `git push` triggers GitHub Pages deployment automatically. Only commit if data.json actually changed (no empty commits).

- [x] Task 16: Add frontend error fallback states
  - File: `js/app.js` (update)
  - Action: Ensure these fallback states are rendered:
    - **No data.json / fetch error**: Show full-page message "Data unavailable — check back later" with muted styling.
    - **Empty days array**: Show "No videos found in the last N days."
    - **Video with `transcriptAvailable: false`**: Show "Transcript not available for this video." in muted italic in place of summary.
    - **Video with summary starting with "Summary generation failed"**: Show the message in muted italic with a subtle warning indicator.
    - **`daysFilter` from localStorage**: If user set a filter smaller than data.config.daysToShow, only render that many days. If filter is larger or unset, render all available days.

#### Phase 4: Deploy & Validate

- [x] Task 17: Configure GitHub Pages
  - File: Repository Settings (manual)
  - Action: Enable GitHub Pages in repo settings → Source: "Deploy from a branch" → Branch: `main`, folder: `/ (root)`. This serves `index.html`, `settings.html`, `css/`, `js/`, and `data.json` directly.
  - Notes: No build step needed — the site is pure static files. `data.json` is committed to the repo and served as-is. The `pipeline/` and `tests/` directories are served too but that's harmless.

- [x] Task 18: End-to-end test with real channels
  - Action: Run `python -m pipeline.main` locally with `GEMINI_API_KEY` env var set. Verify:
    1. `config.json` loads correctly
    2. Channel URLs resolve to channel IDs
    3. RSS feeds return recent videos
    4. Transcripts are fetched (at least some succeed)
    5. Summaries are generated via Gemini Flash
    6. `data.json` is written with correct structure
    7. Open `index.html` in browser — verify data renders, dark mode works, day sections collapse/expand, inline player works
  - Notes: This is a manual validation step. Run locally first — GitHub Actions may have transcript issues due to IP blocking.

- [x] Task 19: Create sample data.json for offline frontend development
  - File: `data.json`
  - Action: Create a realistic sample `data.json` with 3 days of data, 2 channels per day, 2-3 videos per channel. Use real-looking but fake data. This allows frontend development and testing without running the pipeline. It will be overwritten by the first real pipeline run.

### Acceptance Criteria

#### Pipeline Core

- [x] AC 1: Given a valid `config.json` with 2 channel URLs, when the pipeline runs, then `data.json` is created with the correct schema (has `lastUpdated`, `config`, `days` array).
- [x] AC 2: Given a channel URL like `https://www.youtube.com/@TwoMinutePapers`, when channel resolution runs, then the correct channel ID is extracted and used for RSS fetching.
- [x] AC 3: Given an RSS feed with 10 videos and `daysToShow: 7`, when the RSS fetcher runs, then only videos from the last 7 days are included.
- [x] AC 4: Given a video with an available transcript, when transcript fetching runs, then the full transcript text is captured and `transcriptAvailable` is set to `true`.
- [x] AC 5: Given a video where transcript fetch fails after 3 retries, when transcript fetching runs, then `transcriptAvailable` is set to `false` and the pipeline continues to the next video.
- [x] AC 6: Given a video transcript, when summarization runs, then a bullet-point summary (3-5 bullets using • character) is returned.
- [x] AC 7: Given a day with 3 video summaries, when daily digest generation runs, then a 2-3 sentence narrative summary of the day is returned.

#### Incremental Processing

- [x] AC 8: Given an existing `data.json` with 5 videos and an RSS feed that returns those same 5 plus 2 new videos, when the pipeline runs, then only the 2 new videos are processed (transcripts fetched + summarized) and all 7 appear in the output.
- [x] AC 9: Given an existing `data.json` with days from Feb 20–26 and `daysToShow: 7`, when the pipeline runs on Feb 27, then Feb 20 is dropped and Feb 27 is added.
- [x] AC 10: Given no new videos discovered in an RSS fetch, when the pipeline runs, then `data.json` is left unchanged and the pipeline exits early.

#### Error Handling

- [x] AC 11: Given an invalid channel URL in `config.json`, when channel resolution runs, then the invalid channel is skipped with a warning log and remaining channels are processed normally.
- [x] AC 12: Given the Gemini API returns a 429 rate limit error, when summarization runs, then the request is retried with exponential backoff up to 3 times before recording a failure message.
- [x] AC 13: Given the pipeline crashes mid-execution (e.g., unhandled exception in stage 5), when the error is caught, then `data.json` is NOT written (preserving the previous valid data).

#### Frontend Dashboard

- [x] AC 14: Given a valid `data.json`, when `index.html` loads, then all days are rendered with correct dates, daily digests, channel groupings, and video cards.
- [x] AC 15: Given today's date matches a day in `data.json`, when the dashboard loads, then today's section is expanded and older days are collapsed.
- [x] AC 16: Given a video card is clicked, when the click event fires, then an inline YouTube iframe embed appears/disappears below the card.
- [x] AC 17: Given the dashboard is in dark mode (default), when the theme toggle is clicked, then the theme switches to light mode and the preference is saved to `localStorage`.
- [x] AC 18: Given `data.json` fails to load (network error or missing file), when the dashboard loads, then a "Data unavailable, check back later" message is displayed.
- [x] AC 19: Given the browser window is 500px wide, when the dashboard renders, then video cards stack vertically (thumbnail above content) for readability.

#### GitHub Actions & Deployment

- [x] AC 20: Given the GitHub Actions workflow is configured, when cron triggers at 07:00 UTC on a Tuesday, then the pipeline runs and commits updated `data.json` if new content was found.
- [x] AC 21: Given the cron schedule, when evaluated on a Friday or Saturday, then no pipeline runs are triggered (Sun–Thu only, cron `0-4`).
- [x] AC 22: Given GitHub Pages is enabled on the repo, when a user visits the Pages URL, then `index.html` loads and renders the dashboard from `data.json`.

## Additional Context

### Dependencies

| Package | Purpose | Install |
| ------- | ------- | ------- |
| `feedparser` | Parse YouTube RSS feeds | `pip install feedparser` |
| `youtube-transcript-api` | Fetch YouTube auto-generated transcripts | `pip install youtube-transcript-api` |
| `google-genai` | Google Gemini Flash SDK (new package, replaces archived `google-generativeai`) | `pip install google-genai` |
| `requests` | HTTP requests for channel URL resolution (HTML scrape) | `pip install requests` |
| `pytest` | Unit testing framework | `pip install pytest` |

### Data Model

```json
{
  "lastUpdated": "2026-02-26T08:00:00Z",
  "config": { "daysToShow": 7 },
  "days": [
    {
      "date": "2026-02-26",
      "dailyDigest": "Today's biggest AI stories...",
      "channels": [
        {
          "channelName": "AI Explained",
          "channelUrl": "https://www.youtube.com/@AIExplained",
          "videos": [
            {
              "id": "abc123",
              "title": "BREAKING: GPT-5 Released",
              "publishedAt": "2026-02-26T14:30:00Z",
              "duration": "45:12",
              "thumbnailUrl": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
              "videoUrl": "https://www.youtube.com/watch?v=abc123",
              "summary": "• GPT-5 features native multimodal\n• Pricing 2x cheaper\n• Available next week",
              "transcriptAvailable": true
            }
          ]
        }
      ]
    }
  ]
}
```

### Config Model

```json
{
  "ai": {
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "apiKeyEnvVar": "GEMINI_API_KEY"
  },
  "display": {
    "daysToShow": 7
  },
  "channels": [
    "https://www.youtube.com/@TwoMinutePapers",
    "https://www.youtube.com/@AIExplained-official"
  ]
}
```

### Testing Strategy

- **Unit tests (pytest)** — channel URL resolution, RSS parsing, data merging, day windowing, summarizer prompt construction
- **Mocked external calls** — mock HTTP responses for RSS feeds, transcript API, and Gemini API to avoid real network calls in tests
- **End-to-end pipeline test** — run with 2 real channels (TwoMinutePapers, AIExplained-official) to validate full flow
- **Frontend manual test** — verify data.json renders correctly, dark/light mode toggle, collapsible days, inline player
- **Failure simulation** — test with invalid channel URL, unavailable transcript, missing data.json

### Known Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| YouTube blocks transcript fetching from GitHub Actions IPs | Videos show "transcript not available" | Retry 3x + fallback state + re-attempt next run. Most transcripts succeed over multiple runs. |
| Gemini free tier rate limits reduced further | Summarization fails for some videos | Incremental processing keeps call count low. Config supports provider swap. |
| YouTube RSS feed changes format | Video discovery breaks | feedparser handles most Atom/RSS variations. Monitor for breakage. |
| Channel URL resolution scrape breaks | New channels can't be added | Fallback: users can provide direct `/channel/ID` URLs in config. |

### Notes

- **Schedule:** Runs 3x daily Sun–Thu. No runs on Friday/Saturday (Shabbat).
- **Retry policy:** 3 retries with 5-minute intervals (transcript) or exponential backoff 5s/10s/20s (AI). On final failure, record failure state and retry next pipeline run.
- **Atomic safety:** `data.json` only written at Stage 8. If pipeline crashes mid-run, old data stays intact.
- **Duration field:** YouTube RSS does not include video duration. The `duration` field in the data model will be set to `null` unless we add a secondary lookup. This is a known limitation — the UI should handle missing duration gracefully (hide the badge).
- **Recommended implementation order:** Tasks 1–9 (pipeline) → Task 19 (sample data) → Tasks 10–13 (frontend) → Tasks 14–16 (hardening) → Tasks 17–18 (deploy). Task 19 enables frontend development in parallel with pipeline work.

## Review Notes
- Adversarial review completed with 15 findings (all real)
- All 15 findings auto-fixed:
  - F1: Atomic write via temp file + os.replace()
  - F2: CI uses `git status --porcelain` for untracked file detection
  - F3: Added concurrency guard + 30-min job timeout
  - F4: Added User-Agent header + request delay to channel resolver
  - F5: Narrowed retry exceptions, non-retriable errors break immediately
  - F6: Channel dedup in config loader
  - F7: Descriptive ValueError on missing API key
  - F8: Null check for entry.id in RSS fetcher
  - F9: Change detection uses video ID fingerprints, not counts
  - F10: iframe sandbox attribute + videoId regex validation
  - F11: CSP meta tags on both HTML pages
  - F12: Added tests for config_loader, writer, transcript_fetcher (50 total)
  - F13: Added git pull --rebase before push
  - F14: Rate limiting (1s delay) between RSS and channel HTTP requests
  - F15: O(1) channel URL lookup via pre-built map
- Resolution approach: auto-fix
- Final test count: 50/50 passing
