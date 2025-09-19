import requests
from bs4 import BeautifulSoup
import json
import time
import random

blocked_keywords = ["advertisement", "sponsored", "promo", "offer", "discount"]

def is_relevant(title: str, source: str = "") -> bool:
    text = (title + " " + source).lower()
    return not any(word in text for word in blocked_keywords)

def fetch_google_news(query: str, limit: int = 10, lang: str = "en") -> list:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    url = f"https://www.google.com/search?q={query}&tbm=nws&hl={lang}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # Each article is wrapped in <a class="WlydOe">
    articles = soup.select("a.WlydOe")
    clusters = soup.select("g-section-with-header a.WlydOe")
    all_articles = articles + clusters

    for article in all_articles[:limit]:
        try:
            link = article.get("href")

            # --- Title ---
            title_tag = article.select_one("div.n0jPhd") or article.select_one("div.MgUUmf") or article.select_one("div.JheGif")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # --- Source ---
            source_tag = article.select_one("div.CEMjEf span") or article.select_one("div.MgUUmf span")
            source = source_tag.get_text(strip=True) if source_tag else ""

            # --- Date ---
            date_tag = article.select_one("div.OSrXXb span") or article.select_one("span.WG9SHc span")
            date = date_tag.get_text(strip=True) if date_tag else ""

            if title and is_relevant(title, source):
                results.append({
                    "date": date,
                    "title": title,
                    "source": source,
                    "link": link
                })
            else:
                print(f"⏩ Skipped irrelevant: {title}")

        except Exception as e:
            print("⚠️ Error parsing article:", e)

    return results


if __name__ == "__main__":
    query = "Celltrion biosimilar"
    results = fetch_google_news(query, limit=15)

    with open("google_news_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✅ Fetched {len(results)} results")
    for r in results:
        print(f"- {r['date']} | {r['source']} | {r['title']}")
