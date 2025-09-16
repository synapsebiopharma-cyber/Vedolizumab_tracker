import json
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

COOKIES_FILE = "linkedin_cookies.json"


def scrape_latest_posts(profile_url):
    """
    Logs into LinkedIn (or loads cookies), goes to a given profile,
    extracts the last 3 posts (text + date), and returns them as a Python list of dicts.
    """
    email = "synapsebiopharma@gmail.com"
    password = "Synapse@123"

    # 🔹 Setup Selenium
    options = Options()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless=new")  # comment if debugging

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.linkedin.com/")

    # 🔹 Load cookies if available
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)
    else:
        # 🔹 Perform login
        driver.get("https://www.linkedin.com/login")
        driver.find_element(By.ID, "username").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "password").send_keys(Keys.RETURN)
        time.sleep(8)

        # Save cookies for future use
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(driver.get_cookies(), f)

    # 🔹 Navigate to target profile
    driver.get(profile_url)
    time.sleep(5)

    posts_data = []

    try:
        # Scroll to load posts
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(3)

        post_elements = driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")

        for i, post in enumerate(post_elements[:3]):  # take 3 posts
            try:
                text_block = post.find_element(By.CSS_SELECTOR, "span.break-words")
                post_text = text_block.text.strip()
            except:
                post_text = "(No text content found)"

            try:
                # Extract post timestamp (relative like "2d ago")
                date_block = post.find_element(By.CSS_SELECTOR, "span.update-components-actor__sub-description")
                post_date = date_block.text.strip()
            except:
                post_date = "(No date found)"

            posts_data.append({
                "profile_url": profile_url,
                "post_number": i + 1,
                "post_text": post_text,
                "post_date": post_date,   # ✅ Added date
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })

    except Exception as e:
        posts_data.append({
            "profile_url": profile_url,
            "error": str(e),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    driver.quit()
    return posts_data

print(scrape_latest_posts("https://www.linkedin.com/company/polpharma/"))
# Example usage
if __name__ == "__main__":
    url = "https://www.linkedin.com/company/polpharma/"
    print(json.dumps(scrape_latest_posts(url), indent=2, ensure_ascii=False))
