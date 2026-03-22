from datetime import date, timedelta
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

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
    log_pipeline_run,
)
from agents.planner import build_digest_plan
from agents.evaluator import find_undercovered_topics
from agents.selector import llm_select_final_articles
from app.config import GMAIL_SENDER, DIGEST_RECIPIENT, DATABASE_PATH


RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
]


def main():
    from datetime import datetime
    run_start = datetime.utcnow().isoformat()

    try:
        plan = build_digest_plan()
        print("Digest plan:", plan)

        # Dynamic date — always fetch yesterday's news
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        # Step 1: fetch
        rss_articles = fetch_rss_articles(RSS_FEEDS)

        newsapi_articles = fetch_newsapi_articles(
            query="artificial intelligence OR llm OR openai OR Trump OR india OR US OR war OR technology",
            from_date=yesterday,
            page_size=10,
        )

        all_articles = rss_articles + newsapi_articles

        # Step 2: normalize
        normalized_articles = [normalize_article(article) for article in all_articles]

        # Step 3: dedupe
        unique_articles = dedupe_articles(normalized_articles)

        # Step 4: filter already-sent
        sent_hashes = get_sent_hashes()
        unsent_articles = filter_already_sent(unique_articles, sent_hashes)

        # Step 5: topic filtering
        topic_rules = get_active_topic_rules()
        topic_filtered_articles = filter_and_tag_articles_by_topic(
            unsent_articles,
            topic_rules,
        )

        # Step 6: ranking
        source_weights = get_source_weights()
        ranked_articles = rank_articles(topic_filtered_articles, source_weights)

        # Step 7: evaluate topic coverage
        undercovered_topics = find_undercovered_topics(
            ranked_articles,
            target_topics=plan["target_topics"],
            min_articles_per_topic=plan["min_articles_per_topic"],
        )

        print("Undercovered topics:", undercovered_topics)

        # Step 8: adaptive retry for weak coverage
        if undercovered_topics:
            print("Fetching extra articles for undercovered topics...")
            extra_articles = []

            for topic in undercovered_topics:
                extra_query = plan["fallback_queries"].get(topic)
                if not extra_query:
                    continue

                extra_news = fetch_newsapi_articles(
                    query=extra_query,
                    from_date=yesterday,
                    page_size=10,
                )
                extra_articles.extend(extra_news)

            if extra_articles:
                print(f"Fetched {len(extra_articles)} extra articles.")
                normalized_extra = [normalize_article(a) for a in extra_articles]
                combined_articles = dedupe_articles(ranked_articles + normalized_extra)
                combined_unsent = filter_already_sent(combined_articles, sent_hashes)
                combined_filtered = filter_and_tag_articles_by_topic(combined_unsent, topic_rules)
                ranked_articles = rank_articles(combined_filtered, source_weights)

        # Step 9: LLM-based final selection
        final_articles = llm_select_final_articles(
            ranked_articles,
            max_final_articles=plan["max_final_articles"],
        )

        print(f"Final selected articles count: {len(final_articles)}")

        # Step 10: summarize
        summarized_articles = summarize_articles(final_articles, limit=len(final_articles))

        # Step 11: build HTML
        html_digest = build_digest_html(
            summarized_articles,
            title="Daily News Digest",
        )

        # Step 12: send email
        creds = get_gmail_credentials()
        print("About to send email...")
        send_html_email(
            creds=creds,
            sender=GMAIL_SENDER,
            recipient=DIGEST_RECIPIENT,
            subject="Daily News Digest",
            html_body=html_digest,
        )
        print("Email sent successfully.")

        # Step 13: persist results
        save_articles(summarized_articles)
        sent_hashes_to_save = [
            article["article_hash"]
            for article in summarized_articles
            if article.get("article_hash")
        ]
        save_sent_articles(sent_hashes_to_save, str(date.today()))
        print("Sent article hashes saved successfully.")

        # Step 14: log run
        from datetime import datetime
        log_pipeline_run(
            run_started_at=run_start,
            run_finished_at=datetime.utcnow().isoformat(),
            articles_ingested=len(all_articles),
            articles_sent=len(summarized_articles),
            status="success",
        )

    except Exception as e:
        from datetime import datetime
        log_pipeline_run(
            run_started_at=run_start,
            run_finished_at=datetime.utcnow().isoformat(),
            articles_ingested=0,
            articles_sent=0,
            status="failed",
            error_message=str(e),
        )
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
