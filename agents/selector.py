import json
import logging
import os
import re
import anthropic

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"  # fastest + cheapest Claude model


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers."""
    return re.sub(r"```(?:json)?|```", "", text).strip()


def _extract_json_object(text: str) -> str:
    """Pull the first {...} JSON object out of text."""
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    return match.group(0) if match else text


def _parse_selected_ids(raw_output: str, max_id: int) -> set[int]:
    """Parse LLM output into a set of valid integer article IDs."""
    cleaned = _strip_markdown_fences(raw_output)
    cleaned = _extract_json_object(cleaned)

    parsed = json.loads(cleaned)
    selected_ids = parsed.get("selected_ids", [])

    if not isinstance(selected_ids, list):
        raise ValueError(f"selected_ids is not a list, got: {type(selected_ids)}")

    valid_ids = set()
    for item in selected_ids:
        try:
            article_id = int(item)
            if 1 <= article_id <= max_id:
                valid_ids.add(article_id)
            else:
                logger.debug("Ignoring out-of-range id: %s", article_id)
        except (ValueError, TypeError):
            logger.debug("Ignoring non-integer id: %s", item)

    return valid_ids


def llm_select_final_articles(
    articles: list[dict],
    max_final_articles: int = 30,
) -> list[dict]:
    """
    Use Claude Haiku to select the best articles for the digest.
    Falls back to top-ranked articles by score if the API call fails.
    """
    if not articles:
        return []

    candidate_articles = articles[:20]

    candidate_payload = [
        {
            "id": idx,
            "title": article.get("title"),
            "topic": article.get("topic"),
            "source": article.get("source"),
            "score": article.get("score"),
            "summary": article.get("summary"),
        }
        for idx, article in enumerate(candidate_articles, start=1)
    ]

    prompt = f"""You are selecting stories for a daily email news digest.

Your goal:
- Choose the {max_final_articles} best stories from the candidates below.
- Prioritize importance and newsworthiness.
- Maintain diversity across topics.
- Avoid repetitive or overly similar stories.
- Prefer higher-quality, more meaningful stories.

You MUST respond with ONLY a valid JSON object, no extra text or markdown:
{{"selected_ids": [1, 2, 3]}}

Candidates:
{json.dumps(candidate_payload, indent=2)}
"""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=(
                "You are a news curator. You ONLY respond with valid JSON. "
                "No explanations, no markdown, no extra text."
            ),
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        raw_output = message.content[0].text or ""
        logger.debug("Raw Claude selector output: %s", raw_output)

        selected_ids = _parse_selected_ids(raw_output, max_id=len(candidate_articles))

        if not selected_ids:
            raise ValueError("Claude returned an empty selected_ids list.")

        logger.info(
            "Claude selected %d article IDs: %s",
            len(selected_ids), sorted(selected_ids)
        )

    except Exception as e:
        logger.warning(
            "Claude selection failed (%s). Falling back to top-%d scored articles.",
            e, max_final_articles,
        )
        return candidate_articles[:max_final_articles]

    selected_articles = [
        article
        for idx, article in enumerate(candidate_articles, start=1)
        if idx in selected_ids
    ]

    return selected_articles[:max_final_articles]
