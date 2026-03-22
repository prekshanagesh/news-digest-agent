"""
News Digest Agent — Admin Dashboard
Run with:
    cd news_digest_agent
    streamlit run admin/streamlit_app.py
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
from collections import defaultdict

import streamlit as st
import pandas as pd

if "DATABASE_URL" in st.secrets:
    os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]

# ── Path setup so imports work when run from admin/ ──────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from storage.db import get_connection

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="News Digest Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helper: safe SQL query → DataFrame ───────────────────────────────────────
def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    try:
        conn = get_connection()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


def query_scalar(sql: str, params: tuple = (), default=0):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.close()
        return row[0] if row and row[0] is not None else default
    except Exception:
        return default


# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.title("📰 News Digest")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Pipeline Runs", "Articles", "Topics & Sources", "Sent History"],
    index=0,
)
st.sidebar.markdown("---")
st.sidebar.caption(f"DB: `{os.getenv('DATABASE_PATH', 'data/news_digest.db')}`")
if st.sidebar.button("🔄 Refresh"):
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("📊 Pipeline Overview")

    # ── KPI row ──────────────────────────────────────────────────────────────
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    total_articles    = query_scalar("SELECT COUNT(*) FROM articles")
    articles_today    = query_scalar("SELECT COUNT(*) FROM sent_digest_items WHERE sent_date = ?", (today,))
    articles_7d       = query_scalar("SELECT COUNT(*) FROM sent_digest_items WHERE sent_date >= ?", (week_ago,))
    total_runs        = query_scalar("SELECT COUNT(*) FROM pipeline_runs")
    successful_runs   = query_scalar("SELECT COUNT(*) FROM pipeline_runs WHERE status = 'success'")
    failed_runs       = query_scalar("SELECT COUNT(*) FROM pipeline_runs WHERE status = 'failed'")
    success_rate      = round((successful_runs / total_runs * 100) if total_runs > 0 else 0, 1)
    unique_sources    = query_scalar("SELECT COUNT(DISTINCT source) FROM articles")
    unique_topics     = query_scalar("SELECT COUNT(DISTINCT topic) FROM articles WHERE topic IS NOT NULL")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Articles Stored", f"{total_articles:,}")
    col2.metric("Sent Today", articles_today)
    col3.metric("Sent This Week", articles_7d)
    col4.metric("Pipeline Success Rate", f"{success_rate}%",
                delta=f"{successful_runs} ok / {failed_runs} failed")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total Pipeline Runs", total_runs)
    col6.metric("Unique Sources", unique_sources)
    col7.metric("Active Topics", unique_topics)
    last_run = query_scalar("SELECT run_started_at FROM pipeline_runs ORDER BY id DESC LIMIT 1", default="Never")
    col8.metric("Last Run", str(last_run)[:16] if last_run != "Never" else "Never")

    st.markdown("---")

    # ── Articles sent per day (bar chart) ────────────────────────────────────
    st.subheader("📬 Articles Sent Per Day (Last 14 Days)")
    df_daily = query_df("""
        SELECT sent_date, COUNT(*) as articles_sent
        FROM sent_digest_items
        WHERE sent_date >= ?
        GROUP BY sent_date
        ORDER BY sent_date ASC
    """, ((date.today() - timedelta(days=14)).isoformat(),))

    if not df_daily.empty:
        st.bar_chart(df_daily.set_index("sent_date")["articles_sent"])
    else:
        st.info("No sent digest data yet. Run the pipeline to populate this chart.")

    st.markdown("---")

    # ── Topic distribution (last 7 days) ─────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🏷️ Topic Distribution (Last 7 Days)")
        df_topics = query_df("""
            SELECT a.topic, COUNT(*) as count
            FROM articles a
            JOIN sent_digest_items s ON a.article_hash = s.article_hash
            WHERE s.sent_date >= ? AND a.topic IS NOT NULL
            GROUP BY a.topic
            ORDER BY count DESC
        """, (week_ago,))
        if not df_topics.empty:
            st.bar_chart(df_topics.set_index("topic")["count"])
        else:
            st.info("No topic data yet.")

    with col_right:
        st.subheader("📡 Top Sources (Last 7 Days)")
        df_sources = query_df("""
            SELECT a.source, COUNT(*) as count
            FROM articles a
            JOIN sent_digest_items s ON a.article_hash = s.article_hash
            WHERE s.sent_date >= ? AND a.source IS NOT NULL
            GROUP BY a.source
            ORDER BY count DESC
            LIMIT 10
        """, (week_ago,))
        if not df_sources.empty:
            st.bar_chart(df_sources.set_index("source")["count"])
        else:
            st.info("No source data yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE RUNS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline Runs":
    st.title("⚙️ Pipeline Run History")

    df_runs = query_df("""
        SELECT
            id,
            run_started_at,
            run_finished_at,
            articles_ingested,
            articles_sent,
            status,
            error_message
        FROM pipeline_runs
        ORDER BY id DESC
        LIMIT 50
    """)

    if df_runs.empty:
        st.info("""
        No pipeline runs recorded yet.

        To enable run tracking, wrap your `main()` in `app/main.py` with logging:

        ```python
        from storage.repository import log_pipeline_run
        from datetime import datetime

        def main():
            run_start = datetime.utcnow().isoformat()
            try:
                # ... pipeline steps ...
                log_pipeline_run(run_start, datetime.utcnow().isoformat(),
                                 articles_ingested=len(all_articles),
                                 articles_sent=len(summarized_articles),
                                 status="success")
            except Exception as e:
                log_pipeline_run(run_start, datetime.utcnow().isoformat(),
                                 articles_ingested=0, articles_sent=0,
                                 status="failed", error_message=str(e))
                raise
        ```
        """)
    else:
        # Color status column
        def color_status(val):
            if val == "success":
                return "background-color: #d4edda; color: #155724"
            elif val == "failed":
                return "background-color: #f8d7da; color: #721c24"
            return ""

        styled = df_runs.style.applymap(color_status, subset=["status"])
        st.dataframe(styled, use_container_width=True)

        st.markdown("---")
        st.subheader("📈 Articles Ingested vs Sent Per Run")
        if "articles_ingested" in df_runs.columns:
            chart_df = df_runs[["id", "articles_ingested", "articles_sent"]].dropna()
            chart_df = chart_df.set_index("id").sort_index()
            st.line_chart(chart_df)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ARTICLES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Articles":
    st.title("📰 Article Browser")

    # ── Filters ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    all_topics = query_df("SELECT DISTINCT topic FROM articles WHERE topic IS NOT NULL ORDER BY topic")
    topic_options = ["All"] + all_topics["topic"].tolist() if not all_topics.empty else ["All"]
    selected_topic = col1.selectbox("Filter by Topic", topic_options)

    all_sources = query_df("SELECT DISTINCT source FROM articles WHERE source IS NOT NULL ORDER BY source")
    source_options = ["All"] + all_sources["source"].tolist() if not all_sources.empty else ["All"]
    selected_source = col2.selectbox("Filter by Source", source_options)

    search_term = col3.text_input("Search title", placeholder="e.g. OpenAI")

    # ── Build query dynamically ───────────────────────────────────────────────
    conditions = []
    params = []

    if selected_topic != "All":
        conditions.append("topic = ?")
        params.append(selected_topic)
    if selected_source != "All":
        conditions.append("source = ?")
        params.append(selected_source)
    if search_term:
        conditions.append("title LIKE ?")
        params.append(f"%{search_term}%")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    df_articles = query_df(f"""
        SELECT
            title,
            source,
            topic,
            score,
            published_at,
            url,
            fetched_at
        FROM articles
        {where_clause}
        ORDER BY fetched_at DESC
        LIMIT 200
    """, tuple(params))

    st.markdown(f"**{len(df_articles)} articles** found")

    if not df_articles.empty:
        # Make URLs clickable
        df_display = df_articles.copy()
        df_display["url"] = df_display["url"].apply(
            lambda u: f'<a href="{u}" target="_blank">🔗 open</a>' if u else ""
        )
        st.write(
            df_display.to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
    else:
        st.info("No articles match your filters.")

    st.markdown("---")

    # ── Score distribution ────────────────────────────────────────────────────
    st.subheader("📊 Score Distribution")
    df_scores = query_df("SELECT score FROM articles WHERE score IS NOT NULL")
    if not df_scores.empty:
        st.bar_chart(df_scores["score"].value_counts(bins=10).sort_index())


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TOPICS & SOURCES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Topics & Sources":
    st.title("🏷️ Topics & Sources Management")

    tab1, tab2 = st.tabs(["Topics", "Source Weights"])

    # ── Topics tab ───────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Active Topic Keywords")
        df_topics = query_df("""
            SELECT topic_name, GROUP_CONCAT(keyword, ', ') as keywords,
                   COUNT(*) as keyword_count,
                   is_active
            FROM topics
            GROUP BY topic_name, is_active
            ORDER BY topic_name
        """)

        if df_topics.empty:
            st.info("""
            No topics configured yet. Seed your database with topics first:

            ```python
            from storage.repository import seed_topics
            seed_topics([
                ("AI", "artificial intelligence"),
                ("AI", "llm"),
                ("AI", "openai"),
                ("Politics", "trump"),
                ("Politics", "election"),
                ("Technology", "software"),
                ("Technology", "startup"),
            ])
            ```
            """)
        else:
            st.dataframe(df_topics, use_container_width=True)

        st.markdown("---")
        st.subheader("➕ Add New Keyword")
        col1, col2, col3 = st.columns([2, 2, 1])
        new_topic = col1.text_input("Topic name", placeholder="e.g. Health")
        new_keyword = col2.text_input("Keyword", placeholder="e.g. FDA")
        if col3.button("Add", use_container_width=True):
            if new_topic and new_keyword:
                try:
                    conn = get_connection()
                    conn.execute(
                        "INSERT INTO topics (topic_name, keyword, is_active) VALUES (?, ?, 1)",
                        (new_topic.strip(), new_keyword.strip().lower())
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Added keyword '{new_keyword}' to topic '{new_topic}'")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.warning("That keyword already exists for this topic.")
            else:
                st.warning("Please fill in both fields.")

    # ── Source weights tab ───────────────────────────────────────────────────
    with tab2:
        st.subheader("Source Trust Weights")
        st.caption("Higher weight = articles from this source rank higher. Default is 1.0.")

        df_weights = query_df("""
            SELECT source_name, weight
            FROM source_weights
            ORDER BY weight DESC
        """)

        if df_weights.empty:
            st.info("No source weights configured yet. They will appear here after your first pipeline run.")
        else:
            st.dataframe(df_weights, use_container_width=True)

        st.markdown("---")
        st.subheader("➕ Set Source Weight")
        col1, col2, col3 = st.columns([2, 2, 1])
        source_name = col1.text_input("Source name", placeholder="e.g. BBC News")
        source_weight = col2.slider("Weight", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
        if col3.button("Save", use_container_width=True):
            if source_name:
                try:
                    conn = get_connection()
                    conn.execute("""
                        INSERT INTO source_weights (source_name, weight)
                        VALUES (?, ?)
                        ON CONFLICT(source_name) DO UPDATE SET weight = excluded.weight
                    """, (source_name.strip(), source_weight))
                    conn.commit()
                    conn.close()
                    st.success(f"Set weight {source_weight} for '{source_name}'")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a source name.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SENT HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Sent History":
    st.title("📬 Sent Digest History")

    # ── Date picker ──────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 3])
    selected_date = col1.date_input("Select date", value=date.today())

    df_sent = query_df("""
        SELECT
            a.title,
            a.source,
            a.topic,
            a.score,
            a.url,
            s.sent_date
        FROM sent_digest_items s
        JOIN articles a ON s.article_hash = a.article_hash
        WHERE s.sent_date = ?
        ORDER BY a.score DESC
    """, (selected_date.isoformat(),))

    if df_sent.empty:
        st.info(f"No digest was sent on {selected_date}.")
    else:
        st.markdown(f"**{len(df_sent)} articles** sent on {selected_date}")

        for _, row in df_sent.iterrows():
            with st.expander(f"📄 {row['title'] or 'Untitled'}"):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**Source:** {row['source'] or '—'}")
                col2.markdown(f"**Topic:** {row['topic'] or '—'}")
                col3.markdown(f"**Score:** {round(row['score'], 3) if row['score'] else '—'}")
                if row["url"]:
                    st.markdown(f"[🔗 Read article]({row['url']})")

    st.markdown("---")

    # ── All-time sent summary ─────────────────────────────────────────────────
    st.subheader("📅 All-Time Sent Summary")
    df_summary = query_df("""
        SELECT sent_date, COUNT(*) as articles_sent
        FROM sent_digest_items
        GROUP BY sent_date
        ORDER BY sent_date DESC
        LIMIT 30
    """)

    if not df_summary.empty:
        st.dataframe(df_summary, use_container_width=True)
        total_sent = df_summary["articles_sent"].sum()
        st.metric("Total Articles Ever Sent", int(total_sent))
    else:
        st.info("No sent history yet.")