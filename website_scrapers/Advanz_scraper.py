from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

NEWS_URL = "https://www.advanzpharma.com/news"


def fetch_advanz_news(limit=10):
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
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.card"))
        )

        articles = driver.find_elements(By.CSS_SELECTOR, "article.card")

        news_items = []

        for article in articles[:limit]:
            # Link: the <a> is a direct sibling before the card content, wrapping the whole card
            try:
                link_el = article.find_element(By.XPATH, "./preceding-sibling::a | ./parent::li/a | .//a")
                # The <a> is actually BEFORE the <article> inside the <li>, so go up to <li>
                li = article.find_element(By.XPATH, "..")
                link_el = li.find_element(By.TAG_NAME, "a")
                link = link_el.get_attribute("href") or ""
            except Exception:
                link = None

            # Title: use the `title` attribute on .card__title for the full untruncated text
            try:
                title_el = article.find_element(By.CSS_SELECTOR, ".card__title")
                title = title_el.get_attribute("title") or title_el.text.strip()
            except Exception:
                title = None

            # Date: text inside .card__date
            try:
                date_el = article.find_element(By.CSS_SELECTOR, ".card__date")
                date = date_el.text.strip()
            except Exception:
                date = None

            # Category: text inside .card__category (e.g. "Press Releases")
            try:
                cat_el = article.find_element(By.CSS_SELECTOR, ".card__category")
                category = cat_el.text.strip().rstrip("—").strip()
            except Exception:
                category = None

            if title:
                news_items.append({
                    "date": date,
                    "title": title,
                    "category": category,
                    "link": link,
                })

        return news_items

    finally:
        driver.quit()


if __name__ == "__main__":
    data = fetch_advanz_news(limit=10)
    print(json.dumps(data, indent=4, ensure_ascii=False))