from html import escape
from datetime import date
from urllib.parse import quote

TRACKER_BASE_URL = "http://localhost:5001"


def build_tracking_url(article: dict) -> str:
    """
    Wrap the article URL through the local tracking server.
    When the user clicks the link, the tracker records the click
    and redirects them to the real article.
    """
    url = article.get("url", "")
    article_hash = article.get("article_hash", "")
    source = article.get("source", "")
    topic = article.get("topic", "")
    sent_date = str(date.today())

    if not url:
        return "#"

    tracking_url = (
        f"{TRACKER_BASE_URL}/click"
        f"?hash={quote(article_hash)}"
        f"&url={quote(url)}"
        f"&source={quote(source)}"
        f"&topic={quote(topic)}"
        f"&date={sent_date}"
    )
    return tracking_url


def build_digest_html(articles: list[dict], title: str = "Daily News Digest") -> str:
    sections = []

    for article in articles:
        headline = escape(article.get("title", "Untitled"))
        tracking_url = escape(build_tracking_url(article), quote=True)
        source = escape(article.get("source", "Unknown"))
        topic = escape(article.get("topic") or "General")
        llm_summary = escape(article.get("llm_summary", ""))
        score = article.get("score", "")

        section = f"""
        <div style="margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid #e0e0e0;">
            <h3 style="margin: 0 0 8px 0; font-size: 17px; line-height: 1.4;">
                <a href="{tracking_url}" target="_blank"
                   style="text-decoration: none; color: #1a73e8;">
                    {headline}
                </a>
            </h3>
            <p style="margin: 0 0 8px 0; color: #888; font-size: 13px;">
                <strong>{source}</strong> &nbsp;·&nbsp;
                <span style="background: #f0f4ff; color: #3c5a99;
                             padding: 2px 8px; border-radius: 10px;
                             font-size: 12px;">{topic}</span>
                &nbsp;·&nbsp; Score: {round(score, 2) if score else '—'}
            </p>
            <p style="margin: 0; font-size: 15px; line-height: 1.6; color: #333;">
                {llm_summary}
            </p>
        </div>
        """
        sections.append(section)

    today_str = date.today().strftime("%A, %B %d %Y")

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 680px;
                   margin: auto; padding: 32px 20px; background: #ffffff;">

        <div style="border-bottom: 3px solid #1a73e8; padding-bottom: 16px; margin-bottom: 28px;">
            <h1 style="margin: 0; font-size: 26px; color: #1a1a1a;">
                {escape(title)}
            </h1>
            <p style="margin: 6px 0 0; color: #888; font-size: 14px;">
                {today_str} &nbsp;·&nbsp; {len(articles)} stories
            </p>
        </div>

        {''.join(sections)}

        <div style="margin-top: 32px; padding-top: 16px;
                    border-top: 1px solid #e0e0e0; color: #aaa; font-size: 12px;">
            <p>You are receiving this because you set up the News Digest Agent.</p>
        </div>

      </body>
    </html>
    """

    return html
