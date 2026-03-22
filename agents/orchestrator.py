"""
Agentic Orchestrator — agents/orchestrator.py

Replaces the hardcoded pipeline in app/main.py with a Claude-powered
agent loop that decides what tools to call and in what order.

Usage — replace the body of app/main.py with:
    from agents.orchestrator import run_agent
    run_agent()
"""

import json
import logging
import os
from datetime import date, timedelta

import anthropic

from collector.newsapi_collector import fetch_newsapi_articles
from collector.rss_collector import fetch_rss_articles
from collector.normalize import normalize_article
from processors.dedupe import dedupe_articles, filter_already_sent
from processors.filter import filter_and_tag_articles_by_topic
from processors.rank import rank_articles
from processors.summarize import summarize_articles
from delivery.html_builder import build_digest_html
from delivery.gmail_auth import get_gmail_credentials
from delivery.gmail_sender import send_html_email
from storage.repository import (
    get_active_topic_rules,
    get_source_weights,
    get_sent_hashes,
    save_articles,
    save_sent_articles,
)
from app.config import GMAIL_SENDER, DIGEST_RECIPIENT

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
]

# ── Tool definitions (what the agent can do) ──────────────────────────────────
TOOLS = [
    {
        "name": "fetch_articles",
        "description": (
            "Fetch fresh news articles from RSS feeds and NewsAPI. "
            "Call this first to get raw articles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "NewsAPI search query e.g. 'AI OR politics OR technology'"
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of articles to fetch from NewsAPI (max 20)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "process_articles",
        "description": (
            "Normalize, deduplicate, filter already-sent articles, "
            "tag by topic, and rank by score. "
            "Call this after fetch_articles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {
                    "type": "integer",
                    "description": "Maximum number of articles to return after processing",
                    "default": 5
                }
            },
            "required": []
        }
    },
    {
        "name": "evaluate_coverage",
        "description": (
            "Check which topics have enough articles. "
            "Returns a list of undercovered topics that need more articles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Topics that should be covered e.g. ['AI', 'Politics', 'World']"
                },
                "min_per_topic": {
                    "type": "integer",
                    "description": "Minimum articles needed per topic",
                    "default": 1
                }
            },
            "required": ["target_topics"]
        }
    },
    {
        "name": "summarize_and_send",
        "description": (
            "Summarize the selected articles and send the digest email. "
            "Call this as the final step when you are happy with the article selection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Email subject and digest title",
                    "default": "Your Daily News Digest"
                }
            },
            "required": []
        }
    }
]


# ── Tool implementations ───────────────────────────────────────────────────────
class AgentState:
    """Holds state across tool calls within a single agent run."""
    def __init__(self):
        self.raw_articles: list[dict] = []
        self.processed_articles: list[dict] = []
        self.sent_hashes: set[str] = set()
        self.topic_rules: dict = {}
        self.source_weights: dict = {}


_state = AgentState()


def tool_fetch_articles(query: str, page_size: int = 10) -> dict:
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    logger.info("Fetching RSS articles...")
    rss = fetch_rss_articles(RSS_FEEDS)

    logger.info("Fetching NewsAPI articles for query: %s", query)
    news = fetch_newsapi_articles(query=query, from_date=yesterday, page_size=page_size)

    _state.raw_articles = rss + news
    _state.sent_hashes = get_sent_hashes()
    _state.topic_rules = get_active_topic_rules()
    _state.source_weights = get_source_weights()

    return {
        "rss_count": len(rss),
        "newsapi_count": len(news),
        "total": len(_state.raw_articles),
        "message": f"Fetched {len(_state.raw_articles)} total articles."
    }


def tool_process_articles(max_articles: int = 5) -> dict:
    if not _state.raw_articles:
        return {"error": "No articles to process. Call fetch_articles first."}

    normalized = [normalize_article(a) for a in _state.raw_articles]
    unique = dedupe_articles(normalized)
    unsent = filter_already_sent(unique, _state.sent_hashes)
    tagged = filter_and_tag_articles_by_topic(unsent, _state.topic_rules)
    ranked = rank_articles(tagged, _state.source_weights)

    _state.processed_articles = ranked[:max_articles]

    topic_counts = {}
    for a in _state.processed_articles:
        t = a.get("topic", "Unknown")
        topic_counts[t] = topic_counts.get(t, 0) + 1

    return {
        "after_dedupe": len(unique),
        "after_sent_filter": len(unsent),
        "after_topic_filter": len(tagged),
        "final_count": len(_state.processed_articles),
        "topic_breakdown": topic_counts,
        "message": f"Processed down to {len(_state.processed_articles)} articles."
    }


def tool_evaluate_coverage(target_topics: list[str], min_per_topic: int = 1) -> dict:
    if not _state.processed_articles:
        return {"error": "No processed articles. Call process_articles first."}

    topic_counts = {}
    for a in _state.processed_articles:
        t = a.get("topic", "Unknown")
        topic_counts[t] = topic_counts.get(t, 0) + 1

    undercovered = [
        t for t in target_topics
        if topic_counts.get(t, 0) < min_per_topic
    ]

    return {
        "topic_counts": topic_counts,
        "undercovered_topics": undercovered,
        "coverage_ok": len(undercovered) == 0,
        "message": (
            "Coverage looks good!" if not undercovered
            else f"These topics need more articles: {undercovered}"
        )
    }


def tool_summarize_and_send(title: str = "Your Daily News Digest") -> dict:
    if not _state.processed_articles:
        return {"error": "No articles to send. Run process_articles first."}

    logger.info("Summarizing %d articles...", len(_state.processed_articles))
    summarized = summarize_articles(_state.processed_articles, limit=len(_state.processed_articles))

    html = build_digest_html(summarized, title=title)

    logger.info("Sending email to %s...", DIGEST_RECIPIENT)
    creds = get_gmail_credentials()
    send_html_email(
        creds=creds,
        sender=GMAIL_SENDER,
        recipient=DIGEST_RECIPIENT,
        subject=title,
        html_body=html,
    )

    save_articles(summarized)
    hashes = [a["article_hash"] for a in summarized if a.get("article_hash")]
    save_sent_articles(hashes, str(date.today()))

    return {
        "articles_sent": len(summarized),
        "recipient": DIGEST_RECIPIENT,
        "message": f"Successfully sent {len(summarized)} articles to {DIGEST_RECIPIENT}."
    }


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Route a tool call to the correct function."""
    logger.info("Executing tool: %s with input: %s", tool_name, tool_input)

    if tool_name == "fetch_articles":
        result = tool_fetch_articles(**tool_input)
    elif tool_name == "process_articles":
        result = tool_process_articles(**tool_input)
    elif tool_name == "evaluate_coverage":
        result = tool_evaluate_coverage(**tool_input)
    elif tool_name == "summarize_and_send":
        result = tool_summarize_and_send(**tool_input)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    logger.info("Tool result: %s", result)
    return json.dumps(result)


# ── Main agent loop ────────────────────────────────────────────────────────────
def run_agent():
    """
    Run the agentic news digest pipeline.
    Claude decides which tools to call and in what order.
    """
    today = date.today().strftime("%A, %B %d %Y")

    system_prompt = """You are an autonomous news digest agent. Your job is to:
1. Fetch fresh news articles
2. Process and filter them
3. Evaluate topic coverage
4. Send a well-rounded daily digest email

You have access to tools to accomplish this. Use them in a logical order.
Be efficient — don't call the same tool twice unless necessary.
When coverage is good and you have enough articles, send the digest.
Always end by calling summarize_and_send."""

    user_message = f"""Today is {today}.

Please build and send the daily news digest. 
- Target topics: AI, Politics, World, Technology
- Target: 5 high quality diverse articles
- Fetch articles covering today's most important news
- Make sure topics are well covered before sending"""

    messages = [{"role": "user", "content": user_message}]

    logger.info("Starting agentic pipeline for %s", today)
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.info("Agent iteration %d/%d", iteration, max_iterations)

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Add assistant response to message history
        messages.append({"role": "assistant", "content": response.content})

        # Check if agent is done
        if response.stop_reason == "end_turn":
            logger.info("Agent finished.")
            # Print final message
            for block in response.content:
                if hasattr(block, "text"):
                    logger.info("Agent summary: %s", block.text)
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Add tool results back to conversation
            messages.append({"role": "user", "content": tool_results})

    else:
        logger.warning("Agent hit max iterations (%d) without finishing.", max_iterations)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_agent()
