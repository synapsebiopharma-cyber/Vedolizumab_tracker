from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

URL = "https://www.celltrion.com/en-us/company/media-center/press-release"  # replace with actual Celltrion news page

def fetch_celltrion_news(limit=10):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL)
        time.sleep(3)  # allow JS to load

        news_items = []
        li_elements = driver.find_elements(By.CSS_SELECTOR, "ul.normal li")

        for li in li_elements[:limit]:
            link_el = li.find_element(By.CSS_SELECTOR, "div.contsWrap a")
            title_el = link_el.find_element(By.CSS_SELECTOR, "p.subject")
            date_el = link_el.find_element(By.CSS_SELECTOR, "span.date")

            title = title_el.text.strip()
            date = date_el.text.strip()
            news_id = link_el.get_attribute("no")  # e.g. "4098"

            # Build detail URL using news_id (Celltrion typically uses /board/detail?no={id})
            detail_url = f"https://www.celltrion.com/en-us/company/media-center/press-release/{news_id}"

            news_items.append({
                "date": date,
                "title": title,
                "link": detail_url
            })

        return news_items

    finally:
        driver.quit()