# Daily News Digest Agent

An agentic AI pipeline that sends a personalized daily email digest every morning. Curated, summarized, and ranked by AI.

## Features

- Fetches 100+ articles daily from RSS feeds and NewsAPI across 8 topic categories
- Claude-powered article selection — picks the most important, diverse, non-repetitive stories
- Claude-powered summarization — 2-sentence factual summary per article
- Adaptive retry loop — detects undercovered topics and fetches targeted articles
- Feedback loop — click tracking boosts sources and topics you engage with
- Persistent storage via Supabase (PostgreSQL) — no duplicate articles across runs
- Streamlit admin dashboard — monitor pipeline runs, article scores, click trends
- Scheduled delivery via APScheduler

## Tech stack: Python 3.12, Claude API (Anthropic), Supabase (PostgreSQL)
