import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def fetch_alvotech_pipeline(url="https://www.alvotech.com/pipeline", save_to_file=True):
    """
    Scrapes the Alvotech pipeline and outputs standardized JSON.
    """

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(5)  # wait for JS content

    products = []
    pipeline_items = driver.find_elements(By.CSS_SELECTOR, "li.Pipeline_pipelineItem__Gs8H4")

    for item in pipeline_items:
        # Product name
        name = item.find_element(By.CSS_SELECTOR, "h3.Pipeline_pipelineItem__title__nrT_I").text.strip()

        # Details mapping to standardized keys
        details = {"INN": None, "Reference Drug": None, "Originator": None, 
                   "Therapeutic Area": None, "Partner": None}
        try:
            info_types = item.find_elements(By.CSS_SELECTOR, "dt.Pipeline_pipelineItem__infoType__35Qlr")
            info_defs = item.find_elements(By.CSS_SELECTOR, "dd.Pipeline_pipelineItem__infoDefinition__c_Pic")
            for dt, dd in zip(info_types, info_defs):
                key = dt.text.strip().lower()
                val = dd.text.strip()
                if "inn" in key:
                    details["INN"] = val
                elif "reference" in key or "originator product" in key:
                    details["Reference Drug"] = val
                elif "originator" in key:
                    details["Originator"] = val
                elif "therapeutic area" in key:
                    details["Therapeutic Area"] = val
                elif "partner" in key:
                    details["Partner"] = val
        except:
            pass

        # Stages
        stages = []
        try:
            stage_items = item.find_elements(By.CSS_SELECTOR, "ul.Pipeline_pipelineItem__stages__Q2HWP li")
            for stage in stage_items:
                stage_name = stage.text.strip()
                active = "Pipeline_active__qqWY3" in stage.get_attribute("class")
                stages.append({"stage": stage_name, "active": active})
        except:
            pass

        # Approvals / status note
        status_note = []
        try:
            approvals_list = item.find_elements(By.CSS_SELECTOR, "div.Pipeline_pipelineItem__approvals__6D0iD ul li")
            status_note = [li.text.strip() for li in approvals_list]
        except:
            pass

        # Clinical info placeholder
        clinical_info = {"phase": None, "link": None}

        products.append({
            "name": name,
            "details": details,
            "stages": stages,
            "clinical_info": clinical_info,
            "status_note": status_note
        })

    driver.quit()

    result = {"company": "Alvotech", "pipeline": products}

    # if save_to_file:
    #     with open("alvotech_pipeline.json", "w", encoding="utf-8") as f:
    #         json.dump(result, f, indent=4, ensure_ascii=False)
    #     print("✅ Data saved to alvotech_pipeline.json")

    return result

# print(fetch_alvotech_pipeline())
if __name__ == "__main__":
    data = fetch_alvotech_pipeline()
    print(json.dumps(data, indent=4, ensure_ascii=False))
