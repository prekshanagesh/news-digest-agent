from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def clean_url(url: str)-> str:
    parsed=urlparse(url)
    filtered_query=[(k,v) for k,v in parse_qsl(parsed.query)if not k.startswith("utm_")]
    return urlunparse(parsed._replace(query=urlencode(filtered_query)))

def normalize_article(article:dict) -> dict:
    return{
        "title": (article.get("title") or "").strip(),
        "url":clean_url((article.get("url")or "").strip()),
        "source":(article.get("source")or"").strip(),
        "published_at":article.get("published_at"),
        "summary":(article.get("summary")or "").strip(),
        "topic":None,
        "score":None,
        "raw_source_type":article.get("raw_source_type"),
    }