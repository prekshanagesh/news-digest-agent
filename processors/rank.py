from datetime import datetime, timezone
from storage.db import get_connection
from dotenv import load_dotenv
load_dotenv()


def get_click_weights() -> dict:
    """
    Read click history from the database and return
    boost scores per source and per topic.

    Sources/topics you click more get a higher boost,
    making them rank higher in future digests.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Source click counts (last 30 days)
        cur.execute("""
            SELECT source, COUNT(*) as clicks
            FROM clicks
            WHERE source IS NOT NULL
              AND clicked_at >= date('now', '-30 days')
            GROUP BY source
        """)
        source_clicks = {row[0]: row[1] for row in cur.fetchall()}

        # Topic click counts (last 30 days)
        cur.execute("""
            SELECT topic, COUNT(*) as clicks
            FROM clicks
            WHERE topic IS NOT NULL
              AND clicked_at >= date('now', '-30 days')
            GROUP BY topic
        """)
        topic_clicks = {row[0]: row[1] for row in cur.fetchall()}

        conn.close()
        return {"sources": source_clicks, "topics": topic_clicks}

    except Exception:
        # If clicks table doesn't exist yet, return empty weights
        return {"sources": {}, "topics": {}}


def calculate_recency_score(article: dict) -> float:
    published_at = article.get("published_at")
    if not published_at:
        return 0.5

    try:
        published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours_old = (now - published_dt).total_seconds() / 3600

        if hours_old <= 6:
            return 1.5
        elif hours_old <= 24:
            return 1.2
        elif hours_old <= 72:
            return 0.9
        else:
            return 0.5
    except Exception:
        return 0.5


def calculate_click_boost(article: dict, click_weights: dict) -> float:
    """
    Returns a boost score based on how often you've clicked
    articles from this source and topic in the last 30 days.

    Max boost is capped at 1.0 to avoid one source dominating.
    """
    source = article.get("source", "")
    topic = article.get("topic", "")

    source_clicks = click_weights["sources"].get(source, 0)
    topic_clicks = click_weights["topics"].get(topic, 0)

    # Normalize: each click adds 0.1, capped at 0.5 per dimension
    source_boost = min(source_clicks * 0.1, 0.5)
    topic_boost = min(topic_clicks * 0.1, 0.5)

    return round(source_boost + topic_boost, 3)


def calculate_final_score(
    article: dict,
    source_weights: dict[str, float],
    click_weights: dict,
) -> dict:
    enriched = article.copy()

    topic_score = article.get("topic_score", 0)
    source_weight = source_weights.get(article.get("source", ""), 1.0)
    recency_score = calculate_recency_score(article)
    click_boost = calculate_click_boost(article, click_weights)

    # Scoring formula:
    # 40% topic relevance
    # 25% source trust weight
    # 20% recency
    # 15% personal click history (feedback loop)
    final_score = (
        topic_score   * 0.40 +
        source_weight * 0.25 +
        recency_score * 0.20 +
        click_boost   * 0.15
    )

    enriched["score"] = round(final_score, 3)
    enriched["click_boost"] = click_boost
    return enriched


def rank_articles(
    articles: list[dict],
    source_weights: dict[str, float],
) -> list[dict]:
    # Load click history once for the whole batch
    click_weights = get_click_weights()

    scored = [
        calculate_final_score(article, source_weights, click_weights)
        for article in articles
    ]
    return sorted(scored, key=lambda x: x["score"], reverse=True)
