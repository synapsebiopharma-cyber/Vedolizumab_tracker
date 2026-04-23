#!/usr/bin/env python3
"""
Teva Pharma IR Events Scraper (Selenium version)
Scrapes the events currently listed on:
    https://ir.tevapharm.com/Events-and-Presentations/events-and-presentations/default.aspx

On each run it compares against the saved snapshot and flags any new events.

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

URL = "https://ir.tevapharm.com/Events-and-Presentations/events-and-presentations/default.aspx"
BASE_URL = "https://ir.tevapharm.com"
OUTPUT_FILE = "teva_pharma_events.json"


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


def fetch_page() -> str:
    print("Launching headless Chrome...")
    driver = get_driver()
    try:
        driver.get(URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".module_container--content .module_item")
            )
        )
        time.sleep(1.5)
        return driver.page_source
    finally:
        driver.quit()


def build_full_url(href: str) -> str | None:
    if not href:
        return None
    return href if href.startswith("http") else BASE_URL + href


def parse_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for item in soup.select(".module_container--content .module_item"):
        title_el = item.select_one(".module_headline-link")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        detail_url = build_full_url(title_el.get("href", ""))

        date_el = item.select_one(".module_date-text")
        date_text = date_el.get_text(strip=True) if date_el else ""

        webcast_el = item.select_one(".module_webcast-link")
        webcast = webcast_el.get("href") if webcast_el else None

        docs = []
        for a in item.select(".module_attachments .module_attachment-link"):
            doc_title = a.get_text(strip=True)
            doc_url = a.get("href", "")
            if doc_title and doc_url:
                docs.append({"title": doc_title, "url": doc_url})

        for css_cls, label in [
            ("module_presentation-link", "Presentation"),
            ("module_news-link", "Press Release"),
        ]:
            for a in item.select(f".{css_cls}"):
                url = a.get("href", "")
                if url and not any(d["url"] == url for d in docs):
                    docs.append({"title": label, "url": url})

        event_id = (title + "|" + date_text).lower().replace(" ", "-")

        events.append({
            "id": event_id,
            "title": title,
            "date": date_text,
            "url": detail_url,
            "webcast": webcast,
            "docs": docs,
            "new": False,
        })

    return events


def load_existing() -> dict | None:
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data: dict) -> None:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_teva_investor() -> list[dict]:
    """Fetch Teva IR events, track new items, persist to disk, and return the events list."""
    html = fetch_page()

    print("Parsing events...")
    fetched = parse_events(html)

    if not fetched:
        print("No events found — page structure may have changed.")
        return []

    existing = load_existing()
    is_first_run = existing is None
    known_ids = {e["id"] for e in existing["events"]} if existing else set()

    new_count = 0
    for event in fetched:
        if not is_first_run and event["id"] not in known_ids:
            event["new"] = True
            new_count += 1

    runs = (existing.get("total_runs", 0) + 1) if existing else 1

    output = {
        "source": URL,
        "last_fetched": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runs": runs,
        "new_on_last_run": new_count,
        "events": fetched,
    }

    save(output)
    print(f"Saved {len(fetched)} events to {OUTPUT_FILE}")
    if is_first_run:
        print("First run — all events stored, none marked as new.")
    else:
        print(f"{new_count} new event(s) found and marked with \"new\": true.")

    return fetched


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fetch_teva_investor()