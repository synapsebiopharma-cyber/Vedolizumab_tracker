import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

BASE_URL = "https://www.sandoz.com"
NEWS_URL = "https://www.sandoz.com/media/news/"

def fetch_sandoz_news(limit=10):
    options = Options()
    options.add_argument("--headless")   # remove this if you want to see the browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(NEWS_URL)

        # ✅ Accept cookie popup if it appears
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            # print("✅ Accepted cookies")
        except:
            pass
            # print("⚠️ No cookie popup found (maybe already accepted).")

        time.sleep(10)  # let page refresh after popup

        news_items = []
        articles = driver.find_elements(By.CSS_SELECTOR, "div.row.country-en div.news-filter")

        for article in articles[:limit]:
            try:
                # title + link
                link_el = article.find_element(By.CSS_SELECTOR, "a.anchor.no-underline")
                href = link_el.get_attribute("href")
                link = href if href.startswith("http") else BASE_URL + href
                title = article.find_element(By.CSS_SELECTOR, "h4.news-filter-content-heading.bold").text.strip()

                # date (second <span>)
                date_section = article.find_element(By.CSS_SELECTOR, ".news-filter-content-date-section")
                spans = date_section.find_elements(By.TAG_NAME, "span")
                date = spans[1].text.strip() if len(spans) > 1 else ""

                news_items.append({
                    "date": date,
                    "title": title,
                    "link": link
                })
            except Exception as e:
                print("Error parsing article:", e)

        return news_items

    finally:
        driver.quit()
if __name__ == "__main__":
    data = fetch_sandoz_news(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))