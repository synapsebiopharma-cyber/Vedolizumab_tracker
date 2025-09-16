import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


URL = "https://www.sandoz.com/business/biosimilars/our-biosimilars/"


def fetch_sandoz_pipeline(save_to_file=True):
    """
    Scrapes Sandoz biosimilars pipeline and outputs standardized JSON.
    """

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    pipeline = []

    try:
        driver.get(URL)
        time.sleep(3)  # wait for page to load

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.select_one("div.richtext table")
        if not table:
            return {"company": "Sandoz", "pipeline": []}

        current_section = None

        for row in table.select("tr"):
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            # Detect section headers (Marketed, Regulatory review, etc.)
            if len(cells) > 0 and cells[0].has_attr("rowspan"):
                current_section = cells[0].get_text(strip=True)
                brand = cells[1].get_text(" ", strip=True)
                therapeutic_area = cells[2].get_text(" ", strip=True)
                status = cells[3].get_text(" ", strip=True)
                sales_target = cells[4].get_text(" ", strip=True)
            elif current_section and len(cells) == 4:
                brand = cells[0].get_text(" ", strip=True)
                therapeutic_area = cells[1].get_text(" ", strip=True)
                status = cells[2].get_text(" ", strip=True)
                sales_target = cells[3].get_text(" ", strip=True)
            else:
                continue

            # Map section/status to standardized stages
            status_lower = status.lower()
            stages = [
                {"stage": "EARLY PHASE", "active": "pre" in status_lower or "early" in status_lower},
                {"stage": "PRE-CLINICAL", "active": "preclinical" in status_lower},
                {"stage": "CLINICAL TRIALS", "active": "clinical" in status_lower},
                {"stage": "FILING", "active": "regulatory" in status_lower or "submission" in status_lower},
                {"stage": "APPROVAL", "active": "approved" in status_lower or "marketed" in status_lower},
                {"stage": "LAUNCH", "active": "marketed" in status_lower}
            ]

            product = {
                "name": brand,
                "details": {
                    "INN": None,
                    "Reference Drug": None,
                    "Originator": None,
                    "Therapeutic Area": therapeutic_area,
                    "Partner": None
                },
                "stages": stages,
                "clinical_info": {
                    "phase": status,
                    "link": None
                },
                "status_note": sales_target
            }

            pipeline.append(product)

    finally:
        driver.quit()

    result = {"company": "Sandoz", "pipeline": pipeline}

    # if save_to_file:
    #     with open("sandoz_pipeline.json", "w", encoding="utf-8") as f:
    #         json.dump(result, f, indent=4, ensure_ascii=False)
    #     print("✅ Data saved to sandoz_pipeline.json")

    return result

# print(fetch_sandoz_pipeline())
if __name__ == "__main__":
    data = fetch_sandoz_pipeline()
    print(json.dumps(data, indent=4, ensure_ascii=False))
