#!/usr/bin/env python3
"""
Dr. Reddy's Quarterly Results Scraper (Selenium version)
Scrapes press presentations and quarterly result reports from:
  https://www.drreddys.com/drreddys-media#presentationsreports

Dates are inferred from the PDF URL path (e.g. /2025-07/ → July 2025).
Tracks new entries across runs using a local JSON file.

Requirements:
    pip install selenium beautifulsoup4 webdriver-manager
"""

import json
import os
import re
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

URL = "https://www.drreddys.com/drreddys-media#presentationsreports"
OUTPUT_FILE = "drreddys_quarterly_results.json"
BASE_URL = "https://www.drreddys.com"

# ── Selenium helpers ──────────────────────────────────────────────────────────

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
    """Launch headless Chrome, load the page, and return page source."""
    print("Launching headless Chrome...")
    driver = get_driver()
    try:
        driver.get(URL)

        # Wait until at least one presentation card is present
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".press-presentations-list-card")
            )
        )

        # Small extra wait to let any lazy-loaded tabs/panels render
        import time
        time.sleep(2)

        return driver.page_source
    finally:
        driver.quit()


# ── Date inference ────────────────────────────────────────────────────────────

MONTH_MAP = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}

def infer_date_from_url(url: str) -> str:
    """
    Extract an approximate date from the CMS path segment.
    e.g.  /cms/sites/default/files/2025-07/Final-press-...pdf
          → "Jul 2025"
    """
    match = re.search(r"/(\d{4})-(\d{2})/", url)
    if match:
        year, month = match.group(1), match.group(2)
        return f"{MONTH_MAP.get(month, month)} {year}"
    return "Unknown"


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a.press-presentations-list-card")

    results = []
    for card in cards:
        title_el = card.select_one("h3")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        lower = title.lower()
        if not any(kw in lower for kw in [
            "press presentation", "quarterly result", "annual result",
            "q1", "q2", "q3", "q4", "fy"
        ]):
            continue

        href = card.get("href", "")
        if href and href.startswith("/"):
            href = BASE_URL + href

        date_str = infer_date_from_url(href)
        entry_id = re.sub(r"\s+", "-", title.lower().strip())

        results.append({
            "id": entry_id,
            "title": title,
            "url": href,
            "approximate_date": date_str,
            "new": False,
        })

    return results


# ── Persistence helpers ───────────────────────────────────────────────────────

def load_existing() -> dict | None:
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data: dict) -> None:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_dr_reddy_investor() -> list[dict]:
    """Fetch Dr. Reddy's quarterly results, track new items, persist to disk, and return the results list."""
    html = fetch_page()

    print("Parsing quarterly results...")
    fetched = parse_results(html)

    if not fetched:
        print("No results found — page structure may have changed.")
        return []

    existing = load_existing()
    is_first_run = existing is None
    known_ids = {e["id"] for e in existing["results"]} if existing else set()

    new_count = 0
    for entry in fetched:
        if not is_first_run and entry["id"] not in known_ids:
            entry["new"] = True
            new_count += 1

    runs = (existing.get("total_runs", 0) + 1) if existing else 1

    output = {
        "source": URL,
        "last_fetched": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runs": runs,
        "new_on_last_run": new_count,
        "results": fetched,
    }

    save(output)
    print(f"Saved {len(fetched)} entries to {OUTPUT_FILE}")
    if is_first_run:
        print("First run — all entries stored, none marked as new.")
    else:
        print(f"{new_count} new result(s) found and marked with \"new\": true.")

    return fetched


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fetch_dr_reddy_investor()