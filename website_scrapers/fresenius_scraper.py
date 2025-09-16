from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

URL = "https://www.fresenius-kabi.com/news"   # adjust if actual URL differs

def fetch_fresenius_news(limit=5):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        time.sleep(3)  # wait for rendering

        # Select news list items
        articles = driver.find_elements(By.CSS_SELECTOR, "ul#list-f69c69a1fc li.cmp-list__item")

        news_items = []

        for article in articles[:limit]:
            # Title & link
            title_el = article.find_element(By.CSS_SELECTOR, "h5.cmp-teaser__title")
            title = title_el.text.strip()

            link_el = article.find_element(By.CSS_SELECTOR, "a.cmp-teaser__link")
            link = link_el.get_attribute("href")

            # Date
            date_el = article.find_element(By.CSS_SELECTOR, "span.cmp-teaser__date")
            date = date_el.text.strip()

            # Category (optional)
            category_el = article.find_element(By.CSS_SELECTOR, "span.cmp-teaser__category")
            category = category_el.text.strip()

            # Description (optional teaser text)
            desc_el = article.find_element(By.CSS_SELECTOR, "div.cmp-teaser__description")
            description = desc_el.text.strip()

            news_items.append({
                "date": date,
                "category": category,
                "title": title,
                "link": link,
                "description": description
            })

        return news_items

    finally:
        driver.quit()