import requests
import xml.etree.ElementTree as ET
import json
import re
from urllib.parse import quote
from datetime import datetime
from email.utils import parsedate_to_datetime

BLOCKED_KEYWORDS = ["advertisement", "sponsored", "promo", "offer", "discount"]

def is_relevant(title: str, source: str = "") -> bool:
    text = (title + " " + source).lower()
    return not any(word in text for word in BLOCKED_KEYWORDS)

def clean_html(text: str) -> str:
    """Strip any residual HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()

def parse_rss_date(date_str: str) -> str:
    """Convert RFC 2822 date string to a readable format."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str

def fetch_google_news_rss(query: str, limit: int = 10, lang: str = "en", country: str = "US") -> list:
    """
    Fetch news articles from Google News RSS feed.

    Args:
        query:   Search query string.
        limit:   Maximum number of results to return.
        lang:    Language code (e.g. 'en', 'de', 'fr').
        country: Country code (e.g. 'US', 'GB', 'DE').

    Returns:
        List of dicts with keys: date, title, source, link.
    """
    encoded_query = quote(query)
    url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded_query}"
        f"&hl={lang}-{country}"
        f"&gl={country}"
        f"&ceid={country}:{lang}"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch RSS feed: HTTP {response.status_code}")

    root = ET.fromstring(response.content)
    channel = root.find("channel")
    if channel is None:
        raise Exception("Invalid RSS feed: no <channel> element found.")

    results = []
    items = channel.findall("item")

    for item in items[:limit]:
        try:
            title   = clean_html(item.findtext("title", default=""))
            link    = item.findtext("link", default="")
            pub_date = parse_rss_date(item.findtext("pubDate", default=""))

            # Source is inside <source url="...">Publisher Name</source>
            source_tag = item.find("source")
            source = source_tag.text.strip() if source_tag is not None and source_tag.text else ""

            if not title:
                continue

            if is_relevant(title, source):
                results.append({
                    "date": pub_date,
                    "title": title,
                    "source": source,
                    "link": link,
                })
            else:
                print(f"⏩ Skipped irrelevant: {title}")

        except Exception as e:
            print(f"⚠️  Error parsing item: {e}")

    return results


if __name__ == "__main__":
    query   = "Celltrion biosimilar"
    results = fetch_google_news_rss(query, limit=15)

    output_file = "google_news_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Fetched {len(results)} results → saved to {output_file}\n")
    for r in results:
        print(f"  {r['date']}  |  {r['source']:<30}  |  {r['title']}")