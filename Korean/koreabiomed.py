import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def scrape_news():
    url = "https://www.koreabiomed.com/news/articleList.html?page=1&total=6954&sc_section_code=S1N2&sc_sub_section_code=&sc_serial_code=&sc_area=&sc_level=&sc_article_type=&sc_view_level=&sc_sdate=&sc_edate=&sc_serial_number=&sc_word=&box_idxno=&sc_multi_code=&sc_is_image=&sc_is_movie=&sc_user_name=&sc_order_by=E&view_type=sm"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    # Wait for the actual list to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.type1 > li"))
        )
    except Exception as e:
        print(f"[ERROR] List not found: {e}")
        driver.quit()
        return []

    articles = driver.find_elements(By.CSS_SELECTOR, "ul.type1 > li")

    # Exclude the hidden #sample <li> template element
    articles = [a for a in articles if a.get_attribute("id") != "sample"]

    news_data = []

    for i, article in enumerate(articles):
        try:
            # Title + link  →  <h4 class="titles"><a href="...">Title</a></h4>
            title_tag = article.find_element(By.CSS_SELECTOR, "h4.titles a")
            title = title_tag.text.strip()
            link = title_tag.get_attribute("href")

            # Category  →  <em class="info category">Bio</em>
            try:
                category = article.find_element(By.CSS_SELECTOR, "em.info.category").text.strip()
            except:
                category = ""

            # Author  →  <em class="info name">Hong Sook</em>
            try:
                author = article.find_element(By.CSS_SELECTOR, "em.info.name").text.strip()
            except:
                author = ""

            # Date  →  <em class="info dated">04.21 14:04</em>
            try:
                date = article.find_element(By.CSS_SELECTOR, "em.info.dated").text.strip()
            except:
                date = ""

            news_data.append({
                "title": title,
                "link": link,
                "category": category,
                "author": author,
                "date": date,
            })

        except Exception as e:
            print(f"[WARN] Skipping article {i+1}: {e}")

    driver.quit()
    return news_data


if __name__ == "__main__":
    data = scrape_news()
    print(json.dumps(data, indent=4, ensure_ascii=False))