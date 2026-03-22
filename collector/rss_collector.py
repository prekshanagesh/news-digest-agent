import feedparser
from datetime import datetime, timezone

def _to_iso8601(struct_time_obj):
    if not struct_time_obj:
        return None
    return datetime(*struct_time_obj[:6],tzinfo=timezone.utc).isoformat()
def fetch_rss_articles(feed_urls: list[str])->list[dict]:
    articles=[]
    for feed_url in feed_urls:
        print(f"\n Checking feed:{feed_url}")
        feed=feedparser.parse(feed_url)
        feed_title=getattr(feed.feed,"title",feed_url)
        print("Feed title:",getattr(feed.feed,"title","NO TITLE"))
        print("Number of entries:",len(feed.entries))
        print("Bozo flag:", getattr(feed, "bozo", None))
        if getattr(feed, "bozo",0):
            print("Parse issue repr:", repr(getattr(feed,"bozo_exception",None)))
        for entry in feed.entries:
            publish_iso=None
            if getattr(entry, "published_parsed",None):
                publish_iso=_to_iso8601(entry.published_parsed)
            elif getattr(entry,"updated_parsed",None):
                publish_iso=_to_iso8601(entry.updated_parsed)
            article={
                "title": getattr(entry,"title","").strip(),
                "url":getattr(entry,"link","").strip(),
                "source": feed_title,
                "published_at":publish_iso,
                "summary": getattr(entry, "summary","").strip(),
                "raw_source_type":"rss",
            }

            if article["title"] and article["url"]:
                articles.append(article)
    return articles 