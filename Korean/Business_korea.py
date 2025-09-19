import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def scrape_news_section():
    """
    Scrape news articles from a page using <section id="section-list"> with <ul class="type2">.

    Args:
        url (str): The page URL to scrape.

    Returns:
        list: A list of dictionaries with article data (same structure as previous scrapers).
    """
    url = "https://www.businesskorea.co.kr/news/articleList.html?sc_sub_section_code=S2N19&view_type=sm"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options= options)

    driver.get(url)
    time.sleep(3)  # wait for page load

    articles = driver.find_elements(By.CSS_SELECTOR, "section#section-list ul.type2 > li")
    news_data = []

    for article in articles:
        try:
            # Image
            img = article.find_element(By.CSS_SELECTOR, "a.thumb img").get_attribute("src")

            # Title + link (note: here it's inside h2)
            title_tag = article.find_element(By.CSS_SELECTOR, "h2.titles a")
            title = title_tag.text.strip()
            link = title_tag.get_attribute("href")

            # Summary
            summary = article.find_element(By.CSS_SELECTOR, "p.lead a").text.strip()

            # Byline -> category, author, date
            byline = article.find_elements(By.CSS_SELECTOR, "span.byline em")
            category = byline[0].text.strip() if len(byline) > 0 else ""
            author = byline[1].text.strip() if len(byline) > 1 else ""
            date = byline[2].text.strip() if len(byline) > 2 else ""

            news_data.append({
                "title": title,
                "link": link,
                "summary": summary,
                "category": category,
                "author": author,
                "date": date,
                "image_url": img
            })

        except Exception as e:
            print(f"⚠️ Skipping article due to error: {e}")

    driver.quit()
    return news_data
# print(scrape_news_section())