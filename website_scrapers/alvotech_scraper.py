from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

URL = "https://investors.alvotech.com/news-events/news-releases"  # <- update if actual URL differs

def fetch_alvotech_news(limit=5):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/114.0.5735.90 Safari/537.36")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.node--nir-news--nir-widget-list"))
        )

        # Each news entry is inside an <article> with class node--nir-news--nir-widget-list
        articles = driver.find_elements(By.CSS_SELECTOR, "article.node--nir-news--nir-widget-list")

        news_items = []

        for article in articles[:limit]:
            # Extract date (day + year span)
            day_el = article.find_element(By.CSS_SELECTOR, ".ndq-press-date .press-date")
            year_el = article.find_element(By.CSS_SELECTOR, ".ndq-press-date .press-year")
            date = f"{day_el.text.strip()} {year_el.text.strip()}"

            # Extract title & link
            title_el = article.find_element(By.CSS_SELECTOR, ".nir-widget--news--headline a")
            title = title_el.text.strip()
            link = title_el.get_attribute("href")

            news_items.append({
                "date": date,
                "title": title,
                "link": link
            })
        return news_items

    finally:    
        driver.quit()

if __name__ == "__main__":
    data = fetch_alvotech_news(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))