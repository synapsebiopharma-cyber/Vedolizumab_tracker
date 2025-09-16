from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

URL = "https://www.drreddys.com/drreddys-media"  # adjust if actual URL differs

def fetch_dr_reddys_news(limit=5):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        time.sleep(3)  # wait for content to render

        news_cards = driver.find_elements(By.CSS_SELECTOR, "div.media-release-card")

        news_items = []
        for card in news_cards[:limit]:
            link_el = card.find_element(By.CSS_SELECTOR, "a.mobile-link-array")
            link = link_el.get_attribute("href")

            date_el = card.find_element(By.CSS_SELECTOR, "span.MuiTypography-root")
            date = date_el.text.strip()

            title_el = card.find_element(By.CSS_SELECTOR, "p.MuiTypography-root")
            title = title_el.text.strip()

            news_items.append({
                "date": date,
                "title": title,
                "link": link
            })

        return news_items

    finally:
        driver.quit()