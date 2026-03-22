from storage.db import get_connection
from collections import defaultdict

def get_sent_hashes() -> set[str]:
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("select article_hash from sent_digest_items")
    rows= cursor.fetchall()
    conn.close()
    return {row[0] for row in rows}
def save_sent_articles(article_hashes: list[str],sent_date:str)-> None:
    conn=get_connection()
    cursor=conn.cursor()
    cursor.executemany(
        "insert into sent_digest_items (article_hash, sent_date) values (?,?)",
        [(article_hash, sent_date) for article_hash in article_hashes]
    )
    conn.commit()
    conn.close()
def get_active_topic_rules()->dict[str,list[str]]:
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute(
        """
        select topic_name, keyword
        from topics
        where is_active=1
    """)
    rows=cursor.fetchall()
    conn.close()

    topic_rules=defaultdict(list)
    for topic_name,keyword in rows:
        topic_rules[topic_name].append(keyword)
    return dict(topic_rules)

def seed_topics(topic_rows:list[tuple[str,str]])-> None:
    conn=get_connection()
    cursor=conn.cursor()

    cursor.executemany(
        """
        Insert into topics (topic_name, keyword, is_active)
        values(?,?,1)
    """, topic_rows
    )
    conn.commit()
    conn.close()
def get_source_weights() -> dict[str, float]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT source_name, weight
        FROM source_weights
    """)
    rows = cursor.fetchall()
    conn.close()

    return {source_name: weight for source_name, weight in rows}
from datetime import datetime



def save_articles(articles: list[dict]) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    rows = []
    for article in articles:
        rows.append((
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
        ))

    cursor.executemany("""
        INSERT OR IGNORE INTO articles (
            article_hash,
            title,
            url,
            source,
            published_at,
            topic,
            topic_score,
            summary,
            score,
            fetched_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

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
    """Log a pipeline run to the pipeline_runs table."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO pipeline_runs
            (run_started_at, run_finished_at, articles_ingested, articles_sent, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_started_at, run_finished_at, articles_ingested, articles_sent, status, error_message),
    )
    conn.commit()
    conn.close()
