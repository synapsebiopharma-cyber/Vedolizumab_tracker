#!/usr/bin/env python3
"""
Alvotech Investor Events Scraper (Selenium version)
Uses a headless browser to bypass bot protection / timeout issues.

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

URL = "https://investors.alvotech.com/news-events/events"
OUTPUT_FILE = "alvotech_events.json"
BASE_URL = "https://investors.alvotech.com"


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
        # Wait until at least one event row is present
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".row.border-bottom"))
        )
        html = driver.page_source
        return html
    finally:
        driver.quit()


def parse_events(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".row.border-bottom")
    events = []

    for row in rows:
        title_el = row.select_one(".field-nir-event-title .field__item")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        link_el = title_el.find("a")
        href = BASE_URL + link_el["href"] if link_el and link_el.get("href") else None

        date_el = row.select_one(".ndq-date")
        time_text = ""
        date_text = ""
        if date_el:
            hide_el = date_el.select_one(".ndq-hide")
            if hide_el:
                time_text = hide_el.get_text(strip=True)
                hide_el.decompose()
            date_text = date_el.get_text(strip=True)

        webcast_el = row.select_one(".normal-webcast-link a")
        webcast = None
        if webcast_el:
            webcast = {
                "text": webcast_el.get_text(strip=True),
                "url": webcast_el.get("href", "")
            }

        docs = []
        for a in row.select(".field-nir-event-assets-ref a"):
            text = a.get_text(strip=True)
            url = a.get("href", "")
            if text and url:
                if url.startswith("/"):
                    url = BASE_URL + url
                docs.append({"text": text, "url": url})

        event_id = (title + "|" + date_text).lower().replace(" ", "-")

        events.append({
            "id": event_id,
            "title": title,
            "url": href,
            "date": date_text,
            "time": time_text,
            "webcast": webcast,
            "docs": docs,
            "new": False
        })

    return events


def load_existing():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_alvotech_investor() -> list[dict]:
    """Fetch Alvotech investor events, track new items, persist to disk, and return the events list."""
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
        "events": fetched
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
    fetch_alvotech_investor()