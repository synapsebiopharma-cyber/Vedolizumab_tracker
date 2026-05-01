import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

URL = "https://www.sandoz.com/business/biosimilars/our-biosimilars/"


def fetch_sandoz_pipeline(save_to_file=True):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    pipeline = []

    try:
        driver.get(URL)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.select_one("div.richtext table")
        if not table:
            return {"company": "Sandoz", "pipeline": []}

        # Known section labels to detect header cells
        SECTION_LABELS = {
            "marketed", "regulatory review", "clinical development",
            "technical development", "early development"
        }

        current_section = None

        for row in table.select("tr"):
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            # ── Detect section-header rows ──────────────────────────────
            # A section header row has a rotated <th> with rowspan > 1
            # It may or may not also contain data cells in the same <tr>
            section_th = None
            for cell in cells:
                text = cell.get_text(strip=True).lower()
                if cell.name == "th" and cell.has_attr("rowspan") and text in SECTION_LABELS:
                    section_th = cell
                    current_section = cell.get_text(strip=True)
                    break

            # After removing the section <th>, collect the remaining cells
            remaining = [c for c in cells if c is not section_th]

            # Skip pure header rows (column titles row) and empty rows
            # The column-title row has <th> elements with bold labels like "Own/Targeted Brand"
            if all(c.name == "th" for c in remaining):
                continue  # column header row — skip

            # We need exactly 4 data columns: brand, area, status, sales
            if len(remaining) < 4:
                continue  # section-only row with no data yet, or malformed

            brand           = remaining[0].get_text(" ", strip=True)
            therapeutic_area = remaining[1].get_text(" ", strip=True)
            status          = remaining[2].get_text(" ", strip=True)
            sales_target    = remaining[3].get_text(" ", strip=True)

            # Skip if brand looks like a column header label
            if not brand or brand.lower() in ("own/targeted brand", ""):
                continue

            status_lower = status.lower()
            stages = [
                {"stage": "EARLY PHASE",    "active": "early" in status_lower},
                {"stage": "PRE-CLINICAL",   "active": "preclinical" in status_lower},
                {"stage": "CLINICAL TRIALS","active": "clinical" in status_lower},
                {"stage": "FILING",         "active": "regulatory" in status_lower or "submission" in status_lower},
                {"stage": "APPROVAL",       "active": "approved" in status_lower or "marketed" in status_lower},
                {"stage": "LAUNCH",         "active": "marketed" in status_lower},
            ]

            pipeline.append({
                "name": brand,
                "details": {
                    "INN": None,
                    "Reference Drug": None,
                    "Originator": None,
                    "Therapeutic Area": therapeutic_area,
                    "Partner": None,
                },
                "stages": stages,
                "clinical_info": {
                    "phase": status,
                    "section": current_section,
                    "link": None,
                },
                "status_note": sales_target,
            })

    finally:
        driver.quit()

    result = {"company": "Sandoz", "pipeline": pipeline}

    if save_to_file:
        with open("sandoz_pipeline.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print("✅ Data saved to sandoz_pipeline.json")

    return result


if __name__ == "__main__":
    data = fetch_sandoz_pipeline()
    print(json.dumps(data, indent=4, ensure_ascii=False))