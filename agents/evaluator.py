def count_articles_by_topic(articles: list[dict]) -> dict[str, int]:
    counts = {}
    for article in articles:
        topic = article.get("topic")
        if not topic:
            continue
        counts[topic] = counts.get(topic, 0) + 1
    return counts


def find_undercovered_topics(
    articles: list[dict],
    target_topics: list[str],
    min_articles_per_topic: int
) -> list[str]:
    counts = count_articles_by_topic(articles)

    undercovered = []
    for topic in target_topics:
        if counts.get(topic, 0) < min_articles_per_topic:
            undercovered.append(topic)

    return undercovered