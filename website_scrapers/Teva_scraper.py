from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

BASE_URL = "https://www.tevapharm.com"
NEWS_URL = f"{BASE_URL}/news-and-media/latest-news/"


def fetch_teva_news(limit=10):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.5735.90 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(NEWS_URL)

        # Wait for news cards to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.vi-card-news"))
        )

        cards = driver.find_elements(By.CSS_SELECTOR, "div.vi-card-news")

        news_items = []

        for card in cards[:limit]:
            # Date: prefer datetime attribute for clean ISO format, fall back to visible text
            try:
                time_el = card.find_element(By.CSS_SELECTOR, "time.vi-card-news__date")
                date = time_el.get_attribute("datetime") or time_el.text.strip()
            except Exception:
                date = None

            # Title
            try:
                title_el = card.find_element(By.CSS_SELECTOR, ".vi-card-news__title")
                title = title_el.text.strip()
            except Exception:
                title = None

            # Link: the <a> trigger holds the relative href
            try:
                link_el = card.find_element(By.CSS_SELECTOR, "a.vi-card-news__trigger")
                href = link_el.get_attribute("href") or ""
                # Build absolute URL if relative
                link = href if href.startswith("http") else BASE_URL + href
            except Exception:
                link = None

            if title:
                news_items.append({
                    "date": date,
                    "title": title,
                    "link": link,
                })

        return news_items

    finally:
        driver.quit()


if __name__ == "__main__":
    data = fetch_teva_news(limit=10)
    print(json.dumps(data, indent=4, ensure_ascii=False))