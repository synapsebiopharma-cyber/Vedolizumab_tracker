import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def fetch_celltrion_pipeline(url="https://www.celltrion.com/en-us/products/pipelines/biologics", save_to_file=True):
    """
    Scrapes the Celltrion pipeline page and standardizes the output format with placeholders.
    """

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(5)  # wait for JS to load

    pipeline = []

    pipeline_items = driver.find_elements(By.CSS_SELECTOR, "dl.tbody > div")

    for item in pipeline_items:
        # Extract raw fields
        try:
            project_name = item.find_element(By.CSS_SELECTOR, "dt span").text.strip()
        except:
            project_name = None

        try:
            inn = item.find_element(By.XPATH, ".//dd[b[contains(text(),'INN')]]/span").text.strip()
        except:
            inn = None

        try:
            indications = item.find_element(By.XPATH, ".//dd[b[contains(text(),'Indications')]]/span").text.strip()
        except:
            indications = None

        clinical_info = {}
        try:
            clinical_dd = item.find_element(By.XPATH, ".//dd[b[contains(text(),'Clinical Info')]]")
            clinical_info["phase"] = clinical_dd.find_element(By.TAG_NAME, "span").text.strip()
            clinical_info["link"] = clinical_dd.find_element(By.TAG_NAME, "a").get_attribute("href")
        except:
            clinical_info = {}

        # Map phase into standardized stages
        phase_text = clinical_info.get("phase", "").lower()
        stages = [
            {"stage": "EARLY PHASE", "active": "early" in phase_text},
            {"stage": "PRE-CLINICAL", "active": "pre" in phase_text},
            {"stage": "CLINICAL TRIALS", "active": "phase" in phase_text},
            {"stage": "FILING", "active": "filing" in phase_text},
            {"stage": "APPROVAL", "active": "approval" in phase_text},
            {"stage": "LAUNCH", "active": "launch" in phase_text},
        ]

        # Build standardized product entry (with placeholders for consistency)
        product = {
            "name": project_name,
            "details": {
                "INN": inn,
                "Reference Drug": None,       # placeholder
                "Originator": None,           # placeholder
                "Therapeutic Area": None,     # placeholder
                "Partner": None,              # placeholder
                "Indications": indications
            },
            "stages": stages,
            "clinical_info": clinical_info,
            "status_note": None  # placeholder for notes if available
        }

        pipeline.append(product)

    driver.quit()

    result = {
        "company": "Celltrion",
        "pipeline": pipeline
    }

    # # Save JSON file
    # if save_to_file:
    #     with open("celltrion_pipeline.json", "w", encoding="utf-8") as f:
    #         json.dump(result, f, indent=4, ensure_ascii=False)
    #     print("✅ Data saved to celltrion_pipeline.json")

    return result

# print(fetch_celltrion_pipeline())
if __name__ == "__main__":
    data = fetch_celltrion_pipeline()
    print(json.dumps(data, indent=4, ensure_ascii=False))
