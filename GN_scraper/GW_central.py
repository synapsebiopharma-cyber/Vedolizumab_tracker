import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 🔹 Block stock/finance-related keywords
blocked_keywords = [
    "stock", "share", "shares", "market", "NSE", "BSE", "IPO", "equity",
    "price", "valuation", "trading", "chart", "breakout", "forecast", "gains",
    "dividend", "investment", "analyst", "sebi", "ipo", "nasdaq", "otcmkts",
    "ADR", "ETF", "mutual fund", "hedge fund", "rating", "target price",
    "celebrity", "Harry Potter", "obituary", "wedding", "sports", "season",
    "Netflix", "series", "thriller", "msn"
]

def is_relevant(text: str) -> bool:
    text = text.lower()
    return not any(word in text for word in blocked_keywords)


def fetch_google_news(search_term: str, limit: int = 10, save_json: bool = True):
    """
    Fetch Google News results for the last 24 hours.

    Args:
        search_term (str): Company or keyword to search for.
        limit (int): Max number of results.
        save_json (bool): Save output to JSON file.

    Returns:
        list[dict]: News items with 'date', 'title', 'link'.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    results = []
    try:
        print(f"Fetching Google News for {search_term}...")
        search_url = f"https://www.google.com/search?q={search_term}&tbm=nws&tbs=qdr:d"
        driver.get(search_url)
        time.sleep(2)

        articles = driver.find_elements(By.CSS_SELECTOR, "a.WlydOe")

        for article in articles[:limit]:
            try:
                link = article.get_attribute("href")

                try:
                    title = article.find_element(By.CSS_SELECTOR, "div.n0jPhd").text
                except:
                    title = ""

                try:
                    date = article.find_element(By.CSS_SELECTOR, "div.OSrXXb span").text
                except:
                    date = ""

                if title and is_relevant(title):
                    results.append({
                        "date": date,
                        "title": title,
                        "link": link
                    })
                else:
                    print(f"Skipped irrelevant/blocked article: {title}")

            except Exception as e:
                print("⚠️ Skipping one article due to error:", e)

    finally:
        driver.quit()

    # # Save to JSON file
    # if save_json:
    #     filename = f"{search_term.lower().replace(' ', '_')}_google_news.json"
    #     with open(filename, "w", encoding="utf-8") as f:
    #         json.dump(results, f, indent=2, ensure_ascii=False)
    #     print(f"✅ Saved {len(results)} news items to {filename}")

    return results


# Example usage
if __name__ == "__main__":
    news = fetch_google_news("Biocon", limit=5)
    print(json.dumps(news, indent=2, ensure_ascii=False))
