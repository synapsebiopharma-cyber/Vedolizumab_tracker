import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import time

URL = "https://www.fresenius-kabi.com/news"

def safe_text(article, css_selector, default=""):
    try:
        return article.find_element(By.CSS_SELECTOR, css_selector).text.strip()
    except NoSuchElementException:
        return default

def safe_attr(article, css_selector, attr, default=""):
    try:
        return article.find_element(By.CSS_SELECTOR, css_selector).get_attribute(attr)
    except NoSuchElementException:
        return default

def fetch_fresenius_news(limit=5):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        time.sleep(3)

        articles = driver.find_elements(
            By.CSS_SELECTOR, "ul#list-f69c69a1fc li.cmp-list__item"
        )

        news_items = []
        for article in articles[:limit]:
            news_items.append({
                "date":        safe_text(article, "span.cmp-teaser__date"),
                "category":    safe_text(article, "span.cmp-teaser__category"),
                "title":       safe_text(article, "h5.cmp-teaser__title"),
                "link":        safe_attr(article, "a.cmp-teaser__link", "href"),
                "description": safe_text(article, "div.cmp-teaser__description"),
            })

        return news_items

    finally:
        driver.quit()

if __name__ == "__main__":
    data = fetch_fresenius_news(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))