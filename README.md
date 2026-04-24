# Daily News Digest Agent

An agentic AI pipeline that sends a personalized daily email digest every morning — curated, summarized, and ranked by AI.

Instead of scrolling through news apps for 30 minutes, you get 5 high-quality stories delivered to your inbox, selected by Claude and personalized based on what you actually click.

---

## How it works

```
RSS Feeds + NewsAPI
        ↓
Normalize → Dedupe → Filter already-sent
        ↓
Tag by topic → Rank by score + click history
        ↓
Claude picks the best 5 stories
        ↓
Claude summarizes each in 2 sentences
        ↓
Email sent → clicks recorded → ranking improves tomorrow
```

The system is agentic because it doesn't follow a fixed script. A planner decides which topics to target, an evaluator checks coverage gaps, and if certain topics are underrepresented it fetches more articles and re-ranks before selecting. Claude makes the final editorial decisions.

---

## Features

- Fetches 100+ articles daily from RSS feeds and NewsAPI across 8 topic categories
- Claude-powered article selection — picks the most important, diverse, non-repetitive stories
- Claude-powered summarization — 2-sentence factual summary per article
- Adaptive retry loop — detects undercovered topics and fetches targeted articles
- Feedback loop — click tracking boosts sources and topics you engage with
- Persistent storage via Supabase (PostgreSQL) — no duplicate articles across runs
- Streamlit admin dashboard — monitor pipeline runs, article scores, click trends
- Scheduled delivery via APScheduler

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| AI | Claude API (Anthropic) — Haiku model |
| News sources | NewsAPI, RSS (BBC, NYT, TechCrunch, The Verge) |
| Database | Supabase (PostgreSQL) / SQLite locally |
| Email delivery | Gmail API (OAuth2) |
| Click tracking | Flask |
| Dashboard | Streamlit |
| Scheduler | APScheduler |
| Version control | Git / GitHub |

---

## Project structure

```
news_digest_agent/
├── agents/
│   ├── planner.py          # decides target topics and fallback queries
│   ├── evaluator.py        # detects undercovered topics
│   └── selector.py         # Claude-powered article selection
├── app/
│   ├── main.py             # pipeline entry point
│   └── config.py           # loads env vars
├── collector/
│   ├── newsapi_collector.py
│   ├── rss_collector.py
│   └── normalize.py
├── processors/
│   ├── dedupe.py           # deduplication + sent history filter
│   ├── filter.py           # topic tagging
│   ├── rank.py             # scoring with click feedback
│   └── summarize.py        # Claude-powered summarization
├── delivery/
│   ├── gmail_auth.py
│   ├── gmail_sender.py
│   ├── html_builder.py     # builds email HTML with tracking links
│   └── tracker.py          # Flask click tracking server
├── storage/
│   ├── db.py               # SQLite / PostgreSQL connection
│   ├── repository.py       # all database queries
│   └── schema.sql          # database schema
├── admin/
│   └── streamlit_app.py    # monitoring dashboard
├── scheduler/
│   └── jobs.py             # APScheduler cron job
├── .env.example
└── requirements.txt
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/prekshanagesh/news-digest-agent.git
cd news_digest_agent
```

### 2. Create a conda environment

```bash
conda create -n news_digest python=3.12
conda activate news_digest
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
NEWSAPI_KEY=your_newsapi_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GMAIL_SENDER=your_gmail@gmail.com
DIGEST_RECIPIENT=your_gmail@gmail.com
DATABASE_URL=postgresql://...  # Supabase connection string
DATABASE_PATH=data/news_digest.db  # only needed locally without Supabase
```

### 4. Get API keys

- NewsAPI — [newsapi.org](https://newsapi.org) (free tier)
- Anthropic — [console.anthropic.com](https://console.anthropic.com)
- Gmail OAuth — [Google Cloud Console](https://console.cloud.google.com) → create OAuth 2.0 credentials → download as `credentials.json`

### 5. Initialize the database

```bash
python3 -m storage.db
```

### 6. Authorize Gmail (first run only)

```bash
python3 -m app.main
```

A browser window will open asking you to authorize Gmail access. After approving, `token.json` is saved and future runs won't need the browser.

---

## Running the project

### Send a digest now

```bash
python3 -m app.main
```

### Run with click tracking (feedback loop)

Open two terminals:

```bash
# Terminal 1 — click tracker
python3 -m delivery.tracker

# Terminal 2 — pipeline
python3 -m app.main
```

### Run on a daily schedule (7 AM)

```bash
python3 -m scheduler.jobs
```

### Open the dashboard

```bash
streamlit run admin/streamlit_app.py
```

---

## How the feedback loop works

Every link in the digest email is wrapped through a local tracking URL. When you click a link:

1. The tracker records the click (source, topic, timestamp) to Supabase
2. Next time the pipeline runs, `rank.py` reads your click history
3. Sources and topics you clicked get a score boost (up to +1.0)
4. More relevant articles surface to the top over time

The ranking formula:

```
final_score = topic_relevance  * 0.40
            + source_weight    * 0.25
            + recency          * 0.20
            + click_boost      * 0.15
```

---

## Environment variables reference

| Variable | Description |
|---|---|
| `NEWSAPI_KEY` | NewsAPI key for fetching articles |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `GMAIL_SENDER` | Gmail address to send from |
| `DIGEST_RECIPIENT` | Email address to receive the digest |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `DATABASE_PATH` | Local SQLite path (fallback if no DATABASE_URL) |

---

## Why AI

Keywords and filters miss context. "Fed rate decision" and "interest rates rise" are the same story — a keyword filter treats them as different. Claude understands relevance, importance, and diversity the way a human editor would. The result is a digest that feels curated, not just filtered.

---
