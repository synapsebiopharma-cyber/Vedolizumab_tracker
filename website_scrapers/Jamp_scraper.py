import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.jamppharma.ca/en/news/"  # update if needed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def fetch_jamp_news(limit=None):
    response = requests.get(URL, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Target the main container
    container = soup.select_one("ol.post-archive__posts__list")
    if not container:
        print("❌ Could not find news container")
        return []

    articles = container.select("article.post-preview")

    news_items = []

    for article in articles[:limit]:
        try:
            # Title + Link
            link_tag = article.select_one("a.post-preview__link")
            title = link_tag.get("title", "").strip()
            link = link_tag.get("href", "").strip()

            # Date
            date_tag = article.select_one("time")   
            date = date_tag.text.strip() if date_tag else ""

            news_items.append({
                "title": title,
                "date": date,
                "link": link
            })

        except Exception as e:
            print(f"⚠️ Skipping one item due to error: {e}")
            continue

    return news_items


def save_to_json(data, filename="jamp_news.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    news = fetch_jamp_news(limit=None)  # set limit=5 if needed
    save_to_json(news)

    print(json.dumps(news, indent=4, ensure_ascii=False))