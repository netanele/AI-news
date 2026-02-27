---
stepsCompleted: [1, 2, 3, 4]
session_active: false
workflow_completed: true
inputDocuments: []
session_topic: 'AI News Dashboard - YouTube video aggregator with AI summaries, organized by day, hosted on GitHub Pages'
session_goals: 'Design a zero-cost AI news consumption workflow; explore static-site architecture for dynamic content; solve transcript-to-summary pipeline; create scannable daily news digest UX'
selected_approach: 'ai-recommended'
techniques_used: ['constraint-mapping', 'morphological-analysis', 'chaos-engineering']
ideas_generated:
  - 'Architecture #1: Decoupled Static Pipeline — GitHub Action writes JSON, static HTML consumes it'
  - 'Architecture #2: Single Rolling JSON — one data.json overwritten each run, last N days only'
  - 'Architecture #3: Configurable AI Engine — settings.json for model/provider swap'
  - 'Architecture #4: User-Friendly Channel Config — paste YouTube URLs, auto-resolve to channel IDs'
  - 'Constraint #1: Transcripts are HARD constraint — youtube-transcript-api fetches YouTube auto-transcripts'
  - 'Constraint #2: Transcript availability mostly solved — fallback shows "not available" message'
  - 'Constraint #3: AI cost solved at $0 — Gemini Flash free tier, configurable'
  - 'Constraint #4: Video discovery — RSS feeds, no API key needed'
  - 'Constraint #5: No-transcript fallback — display "not available" in summary area'
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Netanel
**Date:** 2026-02-25

## Session Overview

**Topic:** AI News Dashboard — a YouTube video aggregator with AI summaries, organized by day, potentially hosted as a static site on GitHub Pages
**Goals:** Design a zero-cost (or near-zero) AI news consumption workflow; explore static-site architecture for dynamic content; solve the transcript-to-summary pipeline; create a clean, scannable daily news digest UX

### Session Setup

The user wants to build an HTML-based AI news dashboard that:
- Aggregates latest YouTube videos from a configurable list of AI-focused channels
- Displays videos organized by day (default 7 days)
- Provides AI-generated summaries for each video and each day
- Allows embedded video playback directly on the page
- Includes a settings page for managing channels and day count
- Ideally hosted for free on GitHub Pages with GitHub Actions automation

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** AI News Dashboard with focus on zero-cost architecture, feasibility exploration, and UX design

**Recommended Techniques:**

- **Constraint Mapping (deep):** Map all real vs imagined constraints — GitHub Pages, YouTube API, AI costs, transcripts
- **Morphological Analysis (deep):** Systematically explore all architectural dimensions and option combinations
- **Chaos Engineering (wild):** Stress-test candidate architectures against failure scenarios and edge cases

**AI Rationale:** The challenge combines constrained architecture (static hosting for dynamic data) with product design (UX, summarization, automation). This sequence maps the solution space, systematically explores it, then pressure-tests what emerges.

## Technique 1: Constraint Mapping Results

### Constraint Map (All Resolved)

| Constraint | Resolution |
|---|---|
| Hosting | GitHub Pages serves static HTML/JSON; GitHub Actions runs the data pipeline on a cron schedule |
| Data Structure | Single `data.json` file, overwritten each run, contains only last N days (default 7) |
| Transcript Access | `youtube-transcript-api` Python library fetches YouTube's auto-generated transcripts for free |
| No-Transcript Fallback | Display "transcript not available" message in place of AI summary |
| AI Summarization | Gemini Flash free tier; model/provider configurable via `config.json` |
| Secrets Management | API keys stored in GitHub Secrets; `config.json` references env var names, not actual keys |
| Video Discovery | YouTube RSS feeds (free, no API key); channel URLs auto-resolved to channel IDs each run |
| Configuration | Single `config.json` — YouTube channel URLs, AI model settings, display settings (days to show) |

### Key Architecture Decisions

1. **Decoupled Static Pipeline** — GitHub Action is the "backend," JSON file is the "API response," HTML/JS client renders dynamically from static data
2. **Single Rolling JSON** — No data accumulation, no cleanup, bounded and predictable
3. **Configurable AI Engine** — `config.json` stores model name + env var reference for API key; swap models with one line change
4. **User-Friendly Channel Config** — Paste any YouTube channel URL format; pipeline resolves to channel ID automatically each run
5. **RSS for Discovery** — Zero API keys for video discovery; RSS returns ~15 recent videos per channel, sufficient for 7-day window

## Technique 2: Morphological Analysis Results

### Complete Architecture Matrix

| Dimension | Decision |
|---|---|
| Pipeline | 8-stage incremental: config → load existing data → discover videos (RSS) → fetch transcripts (new only) → generate video summaries (new only) → merge data → regenerate daily digests (changed days only) → commit & deploy |
| Data Model | Single `data.json`, days-first structure with channel groupings within each day, includes video duration, explicit fallback message for missing transcripts |
| Summaries | Video summaries = bullet-point key takeaways; Daily digest = news roundup narrative; digest generated from individual video summaries (not raw transcripts) |
| UX/Layout | Days-first with channels grouped within each day; today expanded, older days collapsed; dark mode default with light toggle; inline embedded YouTube player |
| Settings | `localStorage` for display preferences (dark mode, days filter); `config.json` in repo for pipeline config (channels, AI model, schedule) |
| Schedule | 3x daily at 10:00, 13:00, 18:00 Israel time (converted to UTC in GitHub Actions cron) |

### Pipeline Flow (Final)

```
Stage 1: LOAD CONFIG
  └── Read config.json (channels, AI settings, daysToShow)

Stage 2: LOAD EXISTING DATA
  └── Read current data.json (if exists)
  └── Extract set of already-processed video IDs

Stage 3: RESOLVE CHANNELS + DISCOVER VIDEOS
  └── Resolve channel URLs → channel IDs (every run)
  └── Fetch RSS feeds → parse video entries
  └── Filter to last N days
  └── Diff against existing: identify NEW videos only

Stage 4: FETCH TRANSCRIPTS (new videos only)
  └── youtube-transcript-api for each new video
  └── Mark "not available" on failure

Stage 5: GENERATE VIDEO SUMMARIES (new videos only)
  └── Send each transcript to Gemini Flash
  └── Get bullet-point key takeaways

Stage 6: MERGE & BUILD
  └── Merge new video data into existing data
  └── Drop days older than N-day window
  └── Group videos by day, then by channel within each day

Stage 7: GENERATE DAILY DIGESTS (changed days only)
  └── For changed days, feed all video summaries to Gemini
  └── Generate news roundup narrative

Stage 8: WRITE & DEPLOY
  └── Write final data.json
  └── Git commit + push → GitHub Pages auto-deploys
```

### Data Model (Final)

```json
{
  "lastUpdated": "2026-02-26T08:00:00Z",
  "config": {
    "daysToShow": 7
  },
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

### Config File (Final)

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

### UX Layout

- **Page structure:** Days first (newest on top), channels grouped within each day
- **Day sections:** Today expanded by default, older days collapsed (click to expand)
- **Daily digest:** News roundup paragraph at top of each day section
- **Video cards:** Thumbnail + title + channel + duration + bullet-point summary + Watch button
- **Video playback:** Inline embedded YouTube player
- **Dark mode:** Default, with light mode toggle
- **Settings page:** Display-only, localStorage for user preferences
- **Schedule display:** "Last updated: X hours ago" in header

## Technique 3: Chaos Engineering Results

### Failure Scenarios & Defenses

| Scenario | What Breaks | Defense |
|---|---|---|
| YouTube blocks transcript fetch | All videos get "not available" | Retry 3x at 5-minute intervals before marking unavailable |
| Gemini API down / rate-limited | Summaries can't be generated | Same retry (3x, 5-min intervals). Failed videos appear with "Summary generation failed", retried next run |
| Channel posts 30+ videos in a day | Long run, potential rate limits | No cap — process all videos. Incremental processing means most are handled across runs |
| Action crashes mid-pipeline | Partial processing lost | Safe by design — data.json only written at Stage 8. Old data stays intact. Next run picks up new videos |
| Channel URL becomes invalid | Channel resolution fails | Skip invalid channel, continue with remaining channels, log warning |
| data.json corrupted/missing | Frontend can't parse data | HTML displays "Data unavailable, check back later" fallback state |

### Schedule Adjustments

- **No runs on Friday and Saturday** (Shabbat)
- Schedule: Sunday–Thursday at 10:00, 13:00, 18:00 Israel time

### Retry Policy (Universal)

- **Max retries:** 3 per operation (transcript fetch, AI summarization)
- **Retry interval:** 5 minutes between attempts
- **On final failure:** Record failure state in data, retry on next pipeline run
- **Pipeline continues:** Individual failures never halt the full pipeline

## Idea Organization and Prioritization

### Thematic Organization

**Theme 1: Data Pipeline Architecture**
- Decoupled Static Pipeline — GitHub Action as "backend", JSON as "API", HTML as client
- 8-Stage Incremental Pipeline — Only processes new content, reuses existing summaries
- Smart Daily Digest Regeneration — Only regenerates digests for days with new content
- Layered Summarization — Individual summaries first, daily digest built from those

**Theme 2: Zero-Cost Infrastructure**
- GitHub Pages + Actions — Free hosting, free compute
- RSS for Discovery — No API key needed for video discovery
- youtube-transcript-api — Free transcript access via YouTube's auto-generated captions
- Gemini Flash Free Tier — $0 AI summarization with configurable provider swap

**Theme 3: Configuration & Flexibility**
- Single config.json — Channels (paste URLs), AI model settings, display settings all in one file
- Auto-resolve channel URLs — Paste any YouTube URL format, pipeline handles the rest
- Configurable AI engine — Swap Gemini for OpenAI/Claude with one line change
- Secrets separation — API keys in GitHub Secrets, config references env var names

**Theme 4: User Experience**
- Days-first, channels-within-day layout
- Bullet-point video summaries for fast scanning
- News roundup daily digests for day's narrative
- Dark mode default with light toggle
- Collapsed older days, today expanded
- Inline embedded YouTube player

**Theme 5: Resilience & Error Handling**
- Universal retry policy (3x, 5-min intervals)
- Atomic writes — data.json only written at end of pipeline
- Graceful fallbacks for all failure states
- Skip invalid channels, continue with rest
- Failed summaries retried next run

### Implementation Roadmap

**Phase 1: Core Pipeline (MVP)**
1. Python script with config loading + RSS fetching + transcript extraction
2. Gemini Flash summarization (video summaries)
3. Write `data.json` output
4. Basic HTML page that loads and renders the JSON

**Phase 2: Full Features**
5. Incremental processing (read existing data, only process new)
6. Daily digest generation
7. Dark mode UI with day sections, channel groupings, collapsible days
8. Inline YouTube player

**Phase 3: Production Hardening**
9. GitHub Action workflow with cron schedule (Sun–Thu, 10/13/18 Israel time)
10. Retry logic (3x, 5-min intervals)
11. Error fallback states in frontend
12. Settings page with localStorage preferences

**Phase 4: Deploy**
13. GitHub Pages setup
14. End-to-end test with real channels

## Session Summary and Insights

### Key Achievements

- Designed a complete, implementation-ready architecture for a zero-cost AI News Dashboard
- Proved feasibility of every major technical component (GitHub Pages, RSS, transcripts, Gemini Flash)
- Created a resilient, self-healing pipeline that gracefully handles all identified failure scenarios
- Defined a clear 4-phase implementation roadmap from MVP to production

### Technology Stack (Final)

| Component | Technology | Cost |
|---|---|---|
| Hosting | GitHub Pages | Free |
| Compute/CI | GitHub Actions | Free (well within 2,000 min/month) |
| Video Discovery | YouTube RSS Feeds | Free, no API key |
| Transcripts | youtube-transcript-api (Python) | Free |
| AI Summarization | Google Gemini Flash (free tier) | Free |
| Frontend | Static HTML/CSS/JS | Free |
| Data Storage | data.json in repo | Free |
| Configuration | config.json in repo | Free |
| **Total Monthly Cost** | | **$0** |

### Architecture in One Sentence

> A GitHub Action runs 3x daily (Sun–Thu), fetches YouTube RSS feeds, grabs transcripts, generates AI summaries via Gemini Flash, and writes a `data.json` that a dark-mode static HTML dashboard renders — all hosted free on GitHub Pages.
