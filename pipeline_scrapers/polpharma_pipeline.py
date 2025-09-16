import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


URL = "https://polpharmabiologics.com/en/pipeline-portfolio/biosimilar-pipeline/"


def fetch_polpharma_pipeline(limit=None, save_to_file=True):
    """
    Scrapes Polpharma's pipeline page and outputs standardized pipeline JSON.
    """

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Phase map based on divider (5 or 6 steps usually)
    phase_map = {
        5: ["Cell line development",
            "Process & formulation development",
            "Clinical development",
            "Submission preparation",
            "Approved"],
        6: ["Cell line development",
            "Process & formulation development",
            "Clinical development",
            "Submission preparation",
            "In review",
            "Approved"]
    }

    pipeline = []

    try:
        driver.get(URL)
        time.sleep(3)

        rows = driver.find_elements(By.CSS_SELECTOR, "div.c-pipeline_row:not(.-header)")

        for idx, row in enumerate(rows):
            if limit and idx >= limit:
                break

            cols = row.find_elements(By.CSS_SELECTOR, "div.c-pipeline_col span")
            inn = cols[0].text.strip() if len(cols) > 0 else ""
            ref_drug = cols[1].text.strip() if len(cols) > 1 else ""
            originator = cols[2].text.strip() if len(cols) > 2 else ""
            therapeutic_area = cols[3].text.strip() if len(cols) > 3 else ""
            partner = cols[4].text.strip() if len(cols) > 4 else ""

            # Progress / Phase
            try:
                bar = row.find_element(By.CSS_SELECTOR, "div.c-pipelineBar")
                percent = int(bar.get_attribute("data-percent"))
                divider = int(bar.get_attribute("data-divider"))
                stage_index = percent // (divider * 10)
                phase = phase_map.get(divider, [])[stage_index - 1] if stage_index > 0 else ""
            except:
                phase = ""

            # Status note
            try:
                status_note = row.find_element(By.CSS_SELECTOR, "div.c-pipeline_col.-absolute span").text.strip()
            except:
                status_note = ""

            # Map phase into standardized stages
            phase_text = phase.lower()
            stages = [
                {"stage": "EARLY PHASE", "active": "early" in phase_text or "cell line" in phase_text},
                {"stage": "PRE-CLINICAL", "active": "process" in phase_text or "formulation" in phase_text},
                {"stage": "CLINICAL TRIALS", "active": "clinical" in phase_text},
                {"stage": "FILING", "active": "submission" in phase_text},
                {"stage": "APPROVAL", "active": "approved" in phase_text or "in review" in phase_text},
                {"stage": "LAUNCH", "active": False},  # Polpharma doesn't mark launch separately
            ]

            # Build standardized product entry
            product = {
                "name": inn if inn else ref_drug,  # use INN as primary name, fallback to reference
                "details": {
                    "INN": inn,
                    "Reference Drug": ref_drug,
                    "Originator": originator,
                    "Therapeutic Area": therapeutic_area,
                    "Partner": partner
                },
                "stages": stages,
                "clinical_info": {
                    "phase": phase,
                    "link": None  # no link available
                },
                "status_note": status_note
            }

            pipeline.append(product)

    finally:
        driver.quit()

    result = {
        "company": "Polpharma",
        "pipeline": pipeline
    }

    # if save_to_file:
    #     with open("polpharma_pipeline.json", "w", encoding="utf-8") as f:
    #         json.dump(result, f, indent=4, ensure_ascii=False)
    #     print("✅ Data saved to polpharma_pipeline.json")

    return result

# print(fetch_polpharma_pipeline())
if __name__ == "__main__":
    data = fetch_polpharma_pipeline(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))
