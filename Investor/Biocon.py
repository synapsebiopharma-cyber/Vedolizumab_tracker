#!/usr/bin/env python3
"""
Biocon Quarterly Earnings Recordings Scraper (Selenium version)
Extracts earnings call video posts from Biocon's investor relations page.

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

URL = "https://www.biocon.com/news-biocon/video-gallery-biocon/quarterly-statements-biocon/#1653297216088-5a4e9281-2d49"
OUTPUT_FILE = "biocon_earnings.json"


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
    print("Launching headless Chrome...")
    driver = get_driver()
    try:
        driver.get(URL)
        # Wait until at least one iframe (YouTube embed) is present on the page
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='youtube']"))
        )
        html = driver.page_source
        return html
    finally:
        driver.quit()


def extract_youtube_id(src: str) -> str | None:
    """Extract YouTube video ID from an embed URL."""
    match = re.search(r"youtube\.com/embed/([A-Za-z0-9_-]+)", src)
    return match.group(1) if match else None


def parse_recordings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # The section of interest lives inside the tab panel with the quarterly statements
    # We look for the tab panel that contains the earnings content.
    # The target panel body holds rows with video widgets + text columns.
    panel_body = soup.find("div", class_="vc_tta-panel-body")

    # Fallback: search the whole page if the panel structure isn't found
    search_root = panel_body if panel_body else soup

    recordings = []

    # Each fiscal year group is a row containing a heading (FY 20XX)
    # followed by another row with up to 4 video+text column pairs.
    # We iterate over all inner rows and group them by FY heading.
    current_fy = "Unknown"

    inner_rows = search_root.find_all("div", class_="vc_row")
    for row in inner_rows:
        # Check if this row is a FY heading row
        h3 = row.find("h3")
        if h3 and re.search(r"FY\s*\d{4}", h3.get_text()):
            current_fy = h3.get_text(strip=True)
            continue

        # Each column may contain a video widget and a text column
        columns = row.find_all("div", class_="vc_column_container")
        for col in columns:
            # Look for a YouTube iframe
            iframe = col.find("iframe", src=re.compile(r"youtube\.com/embed/"))
            if not iframe:
                continue

            src = iframe.get("src", "")
            video_id = extract_youtube_id(src)
            youtube_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            embed_url = src.split("?")[0] if src else None

            # Title from the video widget title attribute or the text column
            title_from_iframe = iframe.get("title", "").strip()

            # Text column: bold <p> is title, lighter <p> is date
            text_col = col.find("div", class_="wpb_text_column")
            title = ""
            date_str = ""
            if text_col:
                paras = text_col.find_all("p")
                if len(paras) >= 1:
                    title = paras[0].get_text(strip=True)
                if len(paras) >= 2:
                    date_str = paras[1].get_text(strip=True)

            # Fall back to iframe title if text column title is empty
            if not title:
                title = title_from_iframe

            if not title and not video_id:
                continue

            # Build a stable ID from title + date
            raw_id = (title + "|" + date_str).lower()
            event_id = re.sub(r"[^a-z0-9|]+", "-", raw_id).strip("-")

            recordings.append({
                "id": event_id,
                "fiscal_year": current_fy,
                "title": title,
                "date": date_str,
                "youtube_video_id": video_id,
                "youtube_url": youtube_url,
                "embed_url": embed_url,
                "new": False,
            })

    return recordings


def load_existing() -> dict | None:
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save(data: dict):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_biocon_investor() -> list[dict]:
    """Fetch Biocon earnings recordings, track new items, persist to disk, and return the recordings list."""
    html = fetch_page()

    print("Parsing recordings...")
    fetched = parse_recordings(html)

    if not fetched:
        print("No recordings found — page structure may have changed.")
        return []

    existing = load_existing()
    is_first_run = existing is None
    known_ids = {e["id"] for e in existing["recordings"]} if existing else set()

    new_count = 0
    for rec in fetched:
        if not is_first_run and rec["id"] not in known_ids:
            rec["new"] = True
            new_count += 1

    runs = (existing.get("total_runs", 0) + 1) if existing else 1

    output = {
        "source": URL,
        "last_fetched": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runs": runs,
        "new_on_last_run": new_count,
        "recordings": fetched,
    }

    save(output)
    print(f"Saved {len(fetched)} recordings to {OUTPUT_FILE}")
    if is_first_run:
        print("First run — all recordings stored, none marked as new.")
    else:
        print(f"{new_count} new recording(s) found and marked with \"new\": true.")

    # Print a summary table
    print("\n--- Summary ---")
    for rec in fetched:
        print(f"  [{rec['fiscal_year']}] {rec['title']} | {rec['date']} | {rec['youtube_url']}")

    return fetched


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fetch_biocon_investor()