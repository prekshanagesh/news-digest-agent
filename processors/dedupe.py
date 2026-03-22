from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import re
import hashlib


TRACKING_PREFIXES = ("utm_",)

TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "src",
    "at_medium",
    "at_campaign",
}


def clean_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url)

    filtered_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.startswith(TRACKING_PREFIXES):
            continue
        if key in TRACKING_KEYS:
            continue
        filtered_query.append((key, value))

    cleaned_query = urlencode(filtered_query, doseq=True)
    cleaned = parsed._replace(query=cleaned_query, fragment="")

    return urlunparse(cleaned)


def normalize_title(title: str) -> str:
    if not title:
        return ""

    title = title.strip().lower()
    title = re.sub(r"\s+", " ", title)
    return title


def make_article_hash(article: dict) -> str:
    cleaned_url = clean_url(article.get("url", ""))
    normalized = normalize_title(article.get("title", ""))

    raw_key = f"{normalized}||{cleaned_url}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def dedupe_articles(articles: list[dict]) -> list[dict]:
    seen_hashes = set()
    unique_articles = []

    for article in articles:
        cleaned = article.copy()
        cleaned["url"] = clean_url(cleaned.get("url", ""))
        cleaned["normalized_title"] = normalize_title(cleaned.get("title", ""))
        cleaned["article_hash"] = make_article_hash(cleaned)

        if cleaned["article_hash"] in seen_hashes:
            continue

        seen_hashes.add(cleaned["article_hash"])
        unique_articles.append(cleaned)

    return unique_articles


def filter_already_sent(articles: list[dict], sent_hashes: set[str]) -> list[dict]:
    return [article for article in articles if article["article_hash"] not in sent_hashes]