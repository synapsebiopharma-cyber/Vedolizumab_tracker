import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

NEWS_URL = "https://www.samsungbioepis.com/en/newsroom/newsroomList.do"
BASE_URL = "https://www.samsungbioepis.com/en/newsroom/"


def fetch_bioepis_news(limit=10):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(NEWS_URL)
        time.sleep(3)  # let page load JS

        news_items = []
        items = driver.find_elements(By.CSS_SELECTOR, "ul.news_box li")

        for item in items[:limit]:
            try:
                link_el = item.find_element(By.CSS_SELECTOR, "a")
                title_el = item.find_element(By.CSS_SELECTOR, "span.txt")
                date_el = item.find_element(By.CSS_SELECTOR, "span.date")

                # Build absolute URL from the onclick attribute or href
                # The href uses a relative path like "./newsroomView.do?idx=..."
                raw_href = link_el.get_attribute("href") or ""
                # Selenium usually resolves relative URLs, but ensure it's absolute
                if raw_href.startswith("http"):
                    link = raw_href
                else:
                    # Fallback: extract idx from onclick and build URL manually
                    onclick = link_el.get_attribute("onclick") or ""
                    # onclick="javascript:goDetail(event,549, '1');"
                    idx = None
                    if "goDetail" in onclick:
                        parts = onclick.replace("javascript:goDetail(event,", "").split(",")
                        idx = parts[0].strip()
                    link = f"{BASE_URL}newsroomView.do?idx={idx}" if idx else raw_href

                news_items.append({
                    "date": date_el.text.strip(),
                    "title": title_el.text.strip(),
                    "link": link,
                })

            except Exception as e:
                print(f"Skipping item due to error: {e}")
                continue

        return news_items

    finally:
        driver.quit()


if __name__ == "__main__":
    data = fetch_bioepis_news(limit=6)
    print(json.dumps(data, indent=4, ensure_ascii=False))