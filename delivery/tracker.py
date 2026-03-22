"""
Click Tracking Server — delivery/tracker.py

A tiny Flask server that:
1. Receives click events from links in the digest email
2. Records them in the clicks table
3. Redirects the user to the real article URL

Run alongside the scheduler:
    cd news_digest_agent
    python3 -m delivery.tracker

Runs on http://localhost:5001
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote

from flask import Flask, request, redirect, jsonify

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from storage.db import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TRACKER_PORT = 5001


def record_click(article_hash: str, source: str, topic: str, sent_date: str) -> None:
    """Write a click event to the clicks table."""
    try:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO clicks (article_hash, source, topic, clicked_at, sent_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (article_hash, source, topic, datetime.utcnow().isoformat(), sent_date)
        )
        conn.commit()
        conn.close()
        logger.info("Click recorded — hash=%s source=%s topic=%s", article_hash, source, topic)
    except Exception as e:
        logger.error("Failed to record click: %s", e)


@app.route("/click")
def click():
    """
    Tracking endpoint.
    Expects: /click?hash=...&url=...&source=...&topic=...&date=...
    Records the click and redirects to the real article URL.
    """
    article_hash = request.args.get("hash", "")
    url = unquote(request.args.get("url", ""))
    source = request.args.get("source", "")
    topic = request.args.get("topic", "")
    sent_date = request.args.get("date", "")

    if article_hash and url:
        record_click(article_hash, source, topic, sent_date)

    if url:
        return redirect(url)
    else:
        return "Missing URL parameter.", 400


@app.route("/stats")
def stats():
    """Quick JSON endpoint showing click stats — useful for the Streamlit dashboard."""
    try:
        conn = get_connection()

        # Top clicked sources
        cur = conn.cursor()
        cur.execute("""
            SELECT source, COUNT(*) as clicks
            FROM clicks
            WHERE source IS NOT NULL AND source != ''
            GROUP BY source
            ORDER BY clicks DESC
            LIMIT 10
        """)
        top_sources = [{"source": r[0], "clicks": r[1]} for r in cur.fetchall()]

        # Top clicked topics
        cur.execute("""
            SELECT topic, COUNT(*) as clicks
            FROM clicks
            WHERE topic IS NOT NULL AND topic != ''
            GROUP BY topic
            ORDER BY clicks DESC
        """)
        top_topics = [{"topic": r[0], "clicks": r[1]} for r in cur.fetchall()]

        # Total clicks
        cur.execute("SELECT COUNT(*) FROM clicks")
        total = cur.fetchone()[0]

        conn.close()
        return jsonify({
            "total_clicks": total,
            "top_sources": top_sources,
            "top_topics": top_topics,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    logger.info("Click tracker running on http://localhost:%d", TRACKER_PORT)
    app.run(host="0.0.0.0", port=TRACKER_PORT, debug=False)
