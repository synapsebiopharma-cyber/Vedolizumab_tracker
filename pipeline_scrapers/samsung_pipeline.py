import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Comment


URL = "https://www.samsungbioepis.com/en/product/product02.do"


def fetch_samsung_pipeline(limit=None, save_to_file=True):
    """
    Scrapes Samsung Bioepis pipeline and outputs standardized JSON.
    """

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    pipeline = []

    try:
        driver.get(URL)
        time.sleep(3)

        boxes = driver.find_elements(By.CSS_SELECTOR, "div.pip_box")

        for idx, box in enumerate(boxes):
            if limit and idx >= limit:
                break

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(box.get_attribute("outerHTML"), "html.parser")

            # Title / Code
            title_tag = soup.select_one("h5.con_tit")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Info list
            info_dict = {}
            for li in soup.select("ul.pip_info li"):
                strong = li.find("strong")
                span = li.find("span")
                if strong and span:
                    info_dict[strong.get_text(strip=True)] = span.get_text(strip=True)

            molecule = info_dict.get("Molecule", "")
            reference = info_dict.get("Reference Biologic", "")
            therapeutic_area = info_dict.get("Therapeutic Area", "")

            # Extract development phase from comments
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            phase_comment = ""
            for c in comments:
                if "Phase" in c:
                    phase_comment = c.strip().replace("<p class=\"comment\">", "").replace("</p>", "")
                    break

            # Trial links
            trial_links = []
            for a in soup.select("div.status a"):
                onclick = a.get("onclick", "")
                url = ""
                if "http" in onclick:
                    start = onclick.find("('") + 2
                    end = onclick.find("',")
                    url = onclick[start:end]
                trial_links.append({
                    "text": a.get_text(strip=True),
                    "url": url
                })

            # Map phase to standardized stages
            phase_text = phase_comment.lower()
            stages = [
                {"stage": "EARLY PHASE", "active": "early" in phase_text},
                {"stage": "PRE-CLINICAL", "active": "pre" in phase_text},
                {"stage": "CLINICAL TRIALS", "active": "phase" in phase_text or "clinical" in phase_text},
                {"stage": "FILING", "active": "submission" in phase_text or "filing" in phase_text},
                {"stage": "APPROVAL", "active": "approval" in phase_text},
                {"stage": "LAUNCH", "active": "launch" in phase_text},
            ]

            # Build standardized product entry
            product = {
                "name": title if title else molecule,
                "details": {
                    "INN": molecule,
                    "Reference Drug": reference,
                    "Originator": None,           # placeholder
                    "Therapeutic Area": therapeutic_area,
                    "Partner": None               # placeholder
                },
                "stages": stages,
                "clinical_info": {
                    "phase": phase_comment,
                    "link": None  # individual trial links stored separately
                },
                "status_note": None,
                "clinical_trials": trial_links  # keep trial links
            }

            pipeline.append(product)

    finally:
        driver.quit()

    result = {
        "company": "Samsung Biologics",
        "pipeline": pipeline
    }

    # if save_to_file:
    #     with open("samsung_pipeline.json", "w", encoding="utf-8") as f:
    #         json.dump(result, f, indent=4, ensure_ascii=False)
    #     print("✅ Data saved to samsung_pipeline.json")

    return result

# print(fetch_samsung_pipeline())
if __name__ == "__main__":
    data = fetch_samsung_pipeline(limit=5)
    print(json.dumps(data, indent=4, ensure_ascii=False))
