import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

URL = "https://polpharma.pl/en/aktualnosci/kategoria/company-news/"

def fetch_polpharma_news(limit=5):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")  # optional, to ensure full rendering
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(URL)
        time.sleep(3)

        articles = driver.find_elements(By.CSS_SELECTOR, "article.app__box-news__item")
        news_items = []

        for article in articles[:limit]:
            title_el = article.find_element(By.CSS_SELECTOR, "h3.app__box-news__item__title a")
            title = title_el.text.strip()
            link = title_el.get_attribute("href")

            date_el = article.find_element(By.CSS_SELECTOR, "div.app__box-news__item__date")
            date = date_el.text.strip()

            news_items.append({
                "date": date,
                "title": title,
                "link": link
            })
        return news_items
    finally:
        driver.quit()

# print(fetch_polpharma_news())
if __name__ == "__main__":
    data = fetch_polpharma_news(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))