def score_article_for_topic(article: dict, keywords: list[str]) -> int:
    title = (article.get("title") or "").lower()
    summary = (article.get("summary") or "").lower()

    score = 0

    for keyword in keywords:
        kw = keyword.lower().strip()
        if not kw:
            continue

        if kw in title:
            score += 2

        if kw in summary:
            score += 1

    return score


def assign_topic(article: dict, topic_rules: dict[str, list[str]]) -> dict:
    best_topic = None
    best_score = 0

    for topic_name, keywords in topic_rules.items():
        score = score_article_for_topic(article, keywords)

        if score > best_score:
            best_topic = topic_name
            best_score = score

    enriched = article.copy()
    enriched["topic"] = best_topic
    enriched["topic_score"] = best_score

    return enriched


def filter_and_tag_articles_by_topic(
    articles: list[dict],
    topic_rules: dict[str, list[str]]
) -> list[dict]:
    tagged_articles = []

    for article in articles:
        enriched = assign_topic(article, topic_rules)

        if enriched["topic"] is not None and enriched["topic_score"] > 0:
            tagged_articles.append(enriched)

    return tagged_articles