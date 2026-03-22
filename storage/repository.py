from collections import defaultdict
from datetime import datetime
from storage.db import get_connection, is_postgres


def _placeholder() -> str:
    """Returns the correct SQL placeholder for the current database."""
    return "%s" if is_postgres() else "?"


def get_sent_hashes() -> set[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT article_hash FROM sent_digest_items")
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows}


def save_sent_articles(article_hashes: list[str], sent_date: str) -> None:
    if not article_hashes:
        return
    p = _placeholder()
    conn = get_connection()
    cursor = conn.cursor()
    for article_hash in article_hashes:
        try:
            cursor.execute(
                f"INSERT INTO sent_digest_items (article_hash, sent_date) VALUES ({p}, {p})",
                (article_hash, sent_date)
            )
        except Exception:
            pass
    conn.commit()
    conn.close()


def get_active_topic_rules() -> dict[str, list[str]]:
    DEFAULT_TOPICS = {
        "AI": ["artificial intelligence", "llm", "openai", "chatgpt", "machine learning"],
        "Politics": ["trump", "election", "congress", "senate", "white house"],
        "World": ["war", "diplomacy", "india", "europe", "middle east", "ukraine"],
        "Technology": ["software", "startup", "chip", "apple", "google", "microsoft"],
        "Business": ["economy", "stock market", "inflation", "fed", "earnings"],
        "Science": ["nasa", "space", "climate", "research", "discovery"],
        "Health": ["health", "medicine", "fda", "disease", "mental health"],
        "Sports": ["nba", "nfl", "cricket", "football", "tennis"],
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name, keyword FROM topics WHERE is_active=1")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return DEFAULT_TOPICS

        topic_rules = defaultdict(list)
        for topic_name, keyword in rows:
            topic_rules[topic_name].append(keyword)
        return dict(topic_rules)

    except Exception:
        return DEFAULT_TOPICS


def seed_topics(topic_rows: list[tuple[str, str]]) -> None:
    p = _placeholder()
    conn = get_connection()
    cursor = conn.cursor()
    for topic_name, keyword in topic_rows:
        try:
            cursor.execute(
                f"INSERT INTO topics (topic_name, keyword, is_active) VALUES ({p}, {p}, 1)",
                (topic_name, keyword)
            )
        except Exception:
            pass
    conn.commit()
    conn.close()


def get_source_weights() -> dict[str, float]:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT source_name, weight FROM source_weights")
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}


def save_articles(articles: list[dict]) -> None:
    if not articles:
        return
    p = _placeholder()
    conn = get_connection()
    cursor = conn.cursor()

    for article in articles:
        try:
            cursor.execute(
                f"""
                INSERT INTO articles
                    (article_hash, title, url, source, published_at,
                     topic, topic_score, summary, score, fetched_at)
                VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
                ON CONFLICT (article_hash) DO NOTHING
                """,
                (
                    article.get("article_hash"),
                    article.get("title"),
                    article.get("url"),
                    article.get("source"),
                    article.get("published_at"),
                    article.get("topic"),
                    article.get("topic_score"),
                    article.get("summary"),
                    article.get("score"),
                    datetime.utcnow().isoformat()
                )
            )
        except Exception as e:
            pass

    conn.commit()
    conn.close()


def log_pipeline_run(
    run_started_at: str,
    run_finished_at: str,
    articles_ingested: int,
    articles_sent: int,
    status: str,
    error_message: str = None,
) -> None:
    p = _placeholder()
    try:
        conn = get_connection()
        conn.cursor().execute(
            f"""
            INSERT INTO pipeline_runs
                (run_started_at, run_finished_at, articles_ingested,
                 articles_sent, status, error_message)
            VALUES ({p},{p},{p},{p},{p},{p})
            """,
            (run_started_at, run_finished_at, articles_ingested,
             articles_sent, status, error_message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        pass


def get_click_weights() -> dict:
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT source, COUNT(*) as clicks
            FROM clicks
            WHERE source IS NOT NULL
              AND clicked_at >= NOW() - INTERVAL '30 days'
            GROUP BY source
        """ if is_postgres() else """
            SELECT source, COUNT(*) as clicks
            FROM clicks
            WHERE source IS NOT NULL
              AND clicked_at >= date('now', '-30 days')
            GROUP BY source
        """)
        source_clicks = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("""
            SELECT topic, COUNT(*) as clicks
            FROM clicks
            WHERE topic IS NOT NULL
              AND clicked_at >= NOW() - INTERVAL '30 days'
            GROUP BY topic
        """ if is_postgres() else """
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
        return {"sources": {}, "topics": {}}
