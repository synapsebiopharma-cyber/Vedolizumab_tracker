import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def scrape_news_type2():
    """
    Scrape news articles from pages using <ul class="type2"> structure.

    Args:
        url (str): The page URL to scrape.

    Returns:
        list: A list of dictionaries containing article data.
    """
    url = "https://www.koreabiomed.com/news/articleList.html?page=1&total=6954&sc_section_code=S1N2&sc_sub_section_code=&sc_serial_code=&sc_area=&sc_level=&sc_article_type=&sc_view_level=&sc_sdate=&sc_edate=&sc_serial_number=&sc_word=&box_idxno=&sc_multi_code=&sc_is_image=&sc_is_movie=&sc_user_name=&sc_order_by=E&view_type=sm"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options )

    driver.get(url)
    time.sleep(3)  # wait for page load

    articles = driver.find_elements(By.CSS_SELECTOR, "ul.type2 > li")
    news_data = []

    for article in articles:
        try:
            # Thumbnail image
            img = article.find_element(By.CSS_SELECTOR, "a.thumb img").get_attribute("src")
            # Title and article link
            title_tag = article.find_element(By.CSS_SELECTOR, "h4.titles a")
            title = title_tag.text.strip()
            link = title_tag.get_attribute("href")
            # Summary text
            summary = article.find_element(By.CSS_SELECTOR, "p.lead a").text.strip()
            # Byline elements (category, author, date)
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
# print(scrape_news_type2())