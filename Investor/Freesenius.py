#!/usr/bin/env python3
"""
Fresenius Investor News Scraper
Scrapes the first page of https://www.fresenius.com/investor-news-and-ad-hoc-news
and tracks new articles across runs.

Requirements:
    pip install selenium beautifulsoup4 webdriver-manager
"""

import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

URL = "https://www.fresenius.com/investor-news-and-ad-hoc-news"
OUTPUT_FILE = "fresenius_investor_news.json"
BASE_URL = "https://www.fresenius.com"


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    if USE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_page():
    print("Launching headless Chrome...")
    driver = get_driver()
    try:
        driver.get(URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card--news"))
        )
        return driver.page_source
    finally:
        driver.quit()


def parse_articles(html):
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for card in soup.select(".card.card--news"):
        link_el = card.select_one("a.card__link")
        title = link_el.get_text(strip=True) if link_el else ""
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = BASE_URL + href

        date_raw = card.select_one("p.date")
        date_raw = date_raw.get_text(strip=True) if date_raw else ""
        date, source = (date_raw.split(" · ", 1) + [""])[:2]

        meta_el = card.select_one("p.meta")
        meta = meta_el.get_text(strip=True) if meta_el else ""

        article_id = (title + "|" + date).lower().replace(" ", "-")

        articles.append({
            "id": article_id,
            "title": title,
            "url": href,
            "date": date,
            "source": source,
            "meta": meta,
            "new": False,
        })

    return articles


def load_existing():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_fresenius_investor() -> list[dict]:
    """Fetch Fresenius investor news, track new items, persist to disk, and return the articles list."""
    html = fetch_page()
    fetched = parse_articles(html)

    if not fetched:
        print("No articles found — page structure may have changed.")
        return []

    existing = load_existing()
    is_first_run = existing is None
    known_ids = {a["id"] for a in existing["articles"]} if existing else set()

    new_count = 0
    for article in fetched:
        if not is_first_run and article["id"] not in known_ids:
            article["new"] = True
            new_count += 1

    output = {
        "source": URL,
        "last_fetched": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runs": (existing.get("total_runs", 0) + 1) if existing else 1,
        "new_on_last_run": new_count,
        "articles": fetched,
    }

    save(output)
    print(f"Saved {len(fetched)} articles to {OUTPUT_FILE}")
    if is_first_run:
        print("First run — all articles stored, none marked as new.")
    else:
        print(f"{new_count} new article(s) detected.")
        if new_count:
            for a in fetched:
                if a["new"]:
                    print(f"  NEW: {a['date']} — {a['title']}")

    return fetched


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fetch_fresenius_investor()