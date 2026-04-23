#!/usr/bin/env python3
"""
Samsung Biologics IR Notices Scraper (Selenium version)
Scrapes all CEO IR Newsletters / notices from:
    https://samsungbiologics.com/ir/resource/notice?tab=5

Uses a headless browser to handle JavaScript-rendered content.

Requirements:
    pip install selenium beautifulsoup4 webdriver-manager
"""

import json
import os
import time
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

URL = "https://samsungbiologics.com/ir/resource/notice?tab=5"
BASE_URL = "https://samsungbiologics.com"
OUTPUT_FILE = "samsung_biologics_notices.json"


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

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def fetch_page():
    """Launch headless Chrome, load the notices page, and return the HTML source."""
    print("Launching headless Chrome...")
    driver = get_driver()
    try:
        driver.get(URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".tbl-body a.tr"))
        )
        time.sleep(1)
        html = driver.page_source
        return html
    finally:
        driver.quit()


def build_full_url(href: str) -> str:
    """Resolve a relative or absolute href against the base URL."""
    if not href:
        return None
    if href.startswith("http"):
        return href
    return BASE_URL + href


def parse_notices(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".tbl-body a.tr")
    notices = []

    for row in rows:
        title_el = row.select_one(".tit")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        onclick = row.get("onclick", "")
        href = row.get("href", "")

        detail_url = None
        if "location.href='" in onclick:
            try:
                inner = onclick.split("location.href='")[1].split("'")[0]
                detail_url = build_full_url(inner)
            except IndexError:
                pass
        if not detail_url and href:
            detail_url = build_full_url(href)

        date_el = row.select_one(".tbl_date")
        date_text = date_el.get_text(strip=True) if date_el else ""

        notice_id = None
        if detail_url and "boardseq=" in detail_url:
            try:
                notice_id = "boardseq-" + detail_url.split("boardseq=")[1].split("&")[0]
            except IndexError:
                pass
        if not notice_id:
            notice_id = (title + "|" + date_text).lower().replace(" ", "-")

        notices.append({
            "id": notice_id,
            "title": title,
            "url": detail_url,
            "date": date_text,
            "new": False,
        })

    return notices


def load_existing() -> dict | None:
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data: dict) -> None:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_samsung_investor() -> list[dict]:
    """Fetch Samsung Biologics IR notices, track new items, persist to disk, and return the notices list."""
    html = fetch_page()

    print("Parsing notices...")
    fetched = parse_notices(html)

    if not fetched:
        print("No notices found — page structure may have changed.")
        return []

    existing = load_existing()
    is_first_run = existing is None
    known_ids = {n["id"] for n in existing["notices"]} if existing else set()

    new_count = 0
    for notice in fetched:
        if not is_first_run and notice["id"] not in known_ids:
            notice["new"] = True
            new_count += 1

    runs = (existing.get("total_runs", 0) + 1) if existing else 1

    output = {
        "source": URL,
        "last_fetched": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runs": runs,
        "new_on_last_run": new_count,
        "notices": fetched,
    }

    save(output)
    print(f"Saved {len(fetched)} notices to {OUTPUT_FILE}")
    if is_first_run:
        print("First run — all notices stored, none marked as new.")
    else:
        print(f"{new_count} new notice(s) found and marked with \"new\": true.")

    return fetched


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fetch_samsung_investor()