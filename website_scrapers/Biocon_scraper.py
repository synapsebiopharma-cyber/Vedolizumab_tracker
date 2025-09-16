from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BIOCON_URL = "https://www.biocon.com/news-biocon/press-releases/"  # main page for Biocon PRs

def fetch_biocon_news(limit=10):
    options = Options()
    options.add_argument("--headless")   # run without opening a browser window
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(BIOCON_URL)

        # wait until at least one article is visible
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.stm_posts_list_single"))
        )

        news_items = []
        articles = driver.find_elements(By.CSS_SELECTOR, "div.stm_posts_list_single")

        for article in articles[:limit]:
            try:
                # Title + link
                title_elem = article.find_element(By.CSS_SELECTOR, "h5 a")
                title = title_elem.text.strip()
                link = title_elem.get_attribute("href")

                # Date
                date_elem = article.find_element(By.CSS_SELECTOR, ".stm_posts_list_single__info .date")
                date = date_elem.text.strip()

                news_items.append({
                    "date": date,
                    "title": title,
                    "link": link
                })
            except Exception as e:
                print("⚠️ Error parsing article:", e)

        return news_items

    finally:
        driver.quit()
