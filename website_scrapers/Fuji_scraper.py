import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

URL = "https://www.fujipharma.jp/english/ir/news/"  # replace with actual page if different

def fetch_fuji_news(limit=10):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        time.sleep(3)  # allow page to load

        news_items = []

        items = driver.find_elements(By.CSS_SELECTOR, "dl.e_arra05_news_list div.list_item")

        for item in items[:limit]:
            # Date (first dt.item_head)
            date = item.find_element(By.CSS_SELECTOR, "dt.item_head").text.strip()

            # Title + Link
            link_el = item.find_element(By.CSS_SELECTOR, "dd.item_body a")
            title = link_el.text.strip()
            link = link_el.get_attribute("href")

            news_items.append({
                "date": date,
                "title": title,
                "link": link
            })

        return news_items

    finally:
        driver.quit()


if __name__ == "__main__":
    data = fetch_fuji_news(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))