import logging
import os
import re
import anthropic

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"  # fastest + cheapest Claude model


def _clean_summary(text: str) -> str:
    """Strip any markdown the model sneaks in."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", " ", text)
    return text.strip()


def summarize_article(article: dict) -> str:
    """
    Summarize a single article using Claude Haiku.
    Falls back to the source summary if the API call fails.
    """
    title = article.get("title") or ""
    source_summary = article.get("summary") or ""
    source = article.get("source") or ""
    topic = article.get("topic") or ""

    if not title and not source_summary:
        return ""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=120,
            system=(
                "You are a news editor writing digest summaries. "
                "Always respond in exactly 2 concise sentences. "
                "Plain prose only — no markdown, no bullet points, no bold text."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Title: {title}\n"
                        f"Description: {source_summary}\n"
                        f"Source: {source}\n"
                        f"Topic: {topic}"
                    ),
                }
            ],
        )
        raw = message.content[0].text or ""
        cleaned = _clean_summary(raw)

        if not cleaned:
            raise ValueError("Empty response from Claude")

        logger.debug("Summarized: %s", title[:60])
        return cleaned

    except Exception as e:
        logger.warning(
            "Claude summarization failed for '%s': %s. Using source summary.",
            title[:60], e
        )
        return _clean_summary(source_summary) or title


def summarize_articles(articles: list[dict], limit: int = 30) -> list[dict]:
    """
    Summarize up to `limit` articles using Claude Haiku.
    Articles beyond the limit get their source summary promoted to llm_summary
    so every article always has an llm_summary field.
    """
    if not articles:
        return []

    summarized = []
    total = min(limit, len(articles))
    logger.info("Summarizing %d articles with Claude Haiku...", total)

    for idx, article in enumerate(articles):
        enriched = article.copy()

        if idx < limit:
            enriched["llm_summary"] = summarize_article(article)
            logger.info("  [%d/%d] done", idx + 1, total)
        else:
            fallback = (article.get("summary") or article.get("title") or "").strip()
            enriched["llm_summary"] = _clean_summary(fallback)

        summarized.append(enriched)

    logger.info("Summarization complete.")
    return summarized