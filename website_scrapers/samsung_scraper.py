from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

NEWS_URL = "https://samsungbiologics.com/media/company-news?schBoardCtgryCcd=1"

def fetch_samsung_news(limit=10):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(NEWS_URL)
        time.sleep(3)  # let page load JS

        news_items = []
        boxes = driver.find_elements(By.CSS_SELECTOR, "div.cont.pix-in.ajaxlist div.box")

        for box in boxes[:limit]:
            link_el = box.find_element(By.CSS_SELECTOR, "a.tr")
            link = link_el.get_attribute("href")
            title_el = link_el.find_element(By.CSS_SELECTOR, "p[data-language='en']")
            date_el = link_el.find_element(By.CSS_SELECTOR, "dt span")
            summary_el = link_el.find_element(By.CSS_SELECTOR, "dd")

            news_items.append({
                "date": date_el.text.strip(),
                "title": title_el.text.strip(),
                "summary": summary_el.text.strip(),
                "link": link
            })

        return news_items

    finally:
        driver.quit()