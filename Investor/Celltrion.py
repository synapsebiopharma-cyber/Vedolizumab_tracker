#!/usr/bin/env python3
"""
Celltrion Earnings Release Scraper (Selenium version)
Scrapes earnings releases from https://celltrion.com/en-us/investment/ir/earnings
Uses a headless browser to render the JS-heavy page.

Requirements:
    pip install selenium beautifulsoup4 webdriver-manager requests
"""

import json
import os
import re
import requests
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

BASE_URL = "https://celltrion.com"
START_URL = "https://celltrion.com/en-us/investment/ir/earnings"
OUTPUT_FILE = "celltrion_earnings.json"

DOWNLOAD_ENDPOINT = "https://celltrion.com/common/file/download"


# ---------------------------------------------------------------------------
# Driver setup
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Page fetching (handles pagination)
# ---------------------------------------------------------------------------

def fetch_all_pages():
    """
    Fetches all paginated pages and returns a list of HTML source strings.
    The site renders pagination via JS clicks, so we navigate page-by-page.
    """
    print("Launching headless Chrome...")
    driver = get_driver()
    all_html = []

    try:
        driver.get(START_URL)

        # Wait for the earnings list to be present
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.download li"))
        )

        while True:
            # Capture current page HTML
            all_html.append(driver.page_source)
            print(f"  Captured page {len(all_html)}...")

            # Try to find and click the "next" pagination button
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "li.nextBtn:not(.disable) a")
            except Exception:
                break

            # Click next and wait for list to refresh
            current_first = driver.find_element(
                By.CSS_SELECTOR, "ul.download li:first-child .subject"
            ).text
            next_btn.click()

            WebDriverWait(driver, 15).until(
                lambda d: d.find_element(
                    By.CSS_SELECTOR, "ul.download li:first-child .subject"
                ).text != current_first
            )

    finally:
        driver.quit()

    return all_html


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_earnings(html_pages: list[str]) -> list[dict]:
    """
    Parses all page HTMLs and returns a unified list of earnings release dicts.
    """
    releases = []

    for page_html in html_pages:
        soup = BeautifulSoup(page_html, "html.parser")
        items = soup.select("ul.download li")

        for item in items:
            # Title
            subject_el = item.select_one(".subject")
            if not subject_el:
                continue
            title = subject_el.get_text(strip=True)

            # Date
            date_el = item.select_one(".date")
            raw_date = date_el.get_text(strip=True) if date_el else ""
            iso_date = normalise_date(raw_date)

            # encdata attribute on the download button
            btn = item.select_one("button[encdata]")
            enc_data = btn.get("encdata", "") if btn else ""

            # Derive a stable ID
            release_id = make_id(title, iso_date)

            releases.append({
                "id": release_id,
                "title": title,
                "date": iso_date,
                "raw_date": raw_date,
                "enc_data": enc_data,
                "new": False,
            })

    return releases


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalise_date(raw: str) -> str:
    """Convert '2026.02.05' → '2026-02-05'. Falls back to raw string."""
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return raw


def make_id(title: str, date: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title + "|" + date).lower()).strip("-")
    return slug


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_existing() -> dict | None:
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data: dict):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved → {OUTPUT_FILE}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_celltrion_investor() -> list[dict]:
    """Fetch Celltrion earnings releases, track new items, persist to disk, and return the releases list."""
    html_pages = fetch_all_pages()

    print("Parsing earnings releases...")
    fetched = parse_earnings(html_pages)

    if not fetched:
        print("No earnings releases found — page structure may have changed.")
        return []

    existing = load_existing()
    is_first_run = existing is None
    known_ids = {e["id"] for e in existing["releases"]} if existing else set()

    new_count = 0
    for release in fetched:
        if not is_first_run and release["id"] not in known_ids:
            release["new"] = True
            new_count += 1

    runs = (existing.get("total_runs", 0) + 1) if existing else 1

    output = {
        "source": START_URL,
        "last_fetched": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runs": runs,
        "new_on_last_run": new_count,
        "releases": fetched,
    }

    save(output)

    print(f"\nTotal releases captured : {len(fetched)}")
    if is_first_run:
        print("First run — all releases stored, none marked as new.")
    else:
        print(f"{new_count} new release(s) found and marked with \"new\": true.")

    print("\n--- Summary ---")
    for r in fetched:
        flag = " ★ NEW" if r["new"] else ""
        print(f"  [{r['date']}] {r['title']}{flag}")

    return fetched


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    fetch_celltrion_investor()