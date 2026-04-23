import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


URL = "https://www.mspharma.com/news-releases?mnuId=3028"  # replace if different


def fetch_mspharma_news(limit=10):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        time.sleep(5)  # allow Angular content to load

        news_items = []

        # Each news block
        cards = driver.find_elements(By.CSS_SELECTOR, "div.col-md-12.mb-3.py-2")

        for card in cards[:limit]:
            try:
                # Title
                title_el = card.find_element(By.CSS_SELECTOR, "span.card-title")
                title = title_el.text.strip()

                # Date
                date_el = card.find_element(By.CSS_SELECTOR, "p.post-date span")
                date = date_el.text.strip()

                # Try to get link (if href exists)
                try:
                    link_el = card.find_element(By.CSS_SELECTOR, "a.btn.btn-primary")
                    link = link_el.get_attribute("href")

                    # If no real href, fallback
                    if not link:
                        link = URL
                except:
                    link = URL

                news_items.append({
                    "date": date,
                    "title": title,
                    "link": link
                })

            except Exception as e:
                print("Skipping one item:", e)

        return news_items

    finally:
        driver.quit()


if __name__ == "__main__":
    data = fetch_mspharma_news(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))