import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


URL = "https://www.drreddysbiologics.com/pipeline"   # <-- replace with actual pipeline page

def fetch_dr_reddys_pipeline():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(URL)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    pipeline_data = {
        "company": "Dr Reddy",
        "pipeline": []
    }

    # Each row
    rows = soup.select("div.body")
    for row in rows:
        cols = row.select("p.item")
        if not cols or len(cols) < 3:
            continue

        product = cols[0].get_text(strip=True)
        therapeutic_area = cols[1].get_text(strip=True)
        drug_type = cols[2].get_text(strip=True)

        # Stages
        stage_divs = row.select("div.item")
        stage_names = ["Early Development", "Pre Clinical", "Phase 1", "Phase 3", "Under Approval"]
        stages = []

        for i, stage_name in enumerate(stage_names):
            # If the page has fewer stage divs, fallback to None
            stage_text = stage_divs[i].get_text(strip=True) if i < len(stage_divs) else None

            if stage_text and stage_text.lower() != "yet to start":
                active_flag = True
            else:
                active_flag = False

            stages.append({
                "stage": stage_name,
                "text": stage_text,
                "active": active_flag
            })

        drug_entry = {
            "name": product,
            "details": {
                "INN": None,
                "Reference Drug": None,
                "Originator": None,
                "Therapeutic Area": therapeutic_area,
                "Partner": None,
                "Type": drug_type
            },
            "stages": stages,
            "clinical_info": {
                "phase": None,
                "link": None
            },
            "status_note": None
        }

        pipeline_data["pipeline"].append(drug_entry)

    return pipeline_data


if __name__ == "__main__":
    result = fetch_dr_reddys_pipeline()
    print(json.dumps(result, indent=4))
