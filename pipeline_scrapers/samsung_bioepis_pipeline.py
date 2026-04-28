import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


URL = "https://www.samsungbioepis.com/en/product/product02.do"

# Stage labels as they appear in alt text of pipeline images
STAGE_LABELS = ["Preclinical", "Phase I", "Phase III", "Filing", "Approval", "Launch"]


def infer_current_phase(trial_links):
    """
    Infer the highest active phase from trial link labels.
    e.g. 'Learn more about the clinical trial (phase III)' → 'Phase III'
    """
    phase_order = ["phase i", "phase ii", "phase iii", "phase iv"]
    highest = None
    for link in trial_links:
        text_lower = link["text"].lower()
        for phase in reversed(phase_order):
            if phase in text_lower:
                if highest is None or phase_order.index(phase) > phase_order.index(highest):
                    highest = phase
                break
    phase_labels = {
        "phase i": "Phase I",
        "phase ii": "Phase II",
        "phase iii": "Phase III",
        "phase iv": "Phase IV",
    }
    return phase_labels.get(highest) if highest else None


def extract_trial_links(soup):
    """Extract all clinical trial links from a pip_box."""
    trial_links = []
    for a in soup.select("div.status a"):
        onclick = a.get("onclick", "")
        url = ""
        # Extract URL from onclick like: linkPageMessage('https://...', popupInfoMsg);
        match = re.search(r"'(https?://[^']+)'", onclick)
        if match:
            url = match.group(1)
        trial_links.append({
            "text": a.get_text(strip=True),
            "url": url
        })
    return trial_links


def build_stage_pipeline(current_phase, trial_links):
    """
    Build a list of stage dicts with active=True for stages up to and including
    the inferred current phase.
    """
    # Map phase names to stage indices (0-based)
    phase_to_index = {
        "preclinical": 0,
        "phase i": 1,
        "phase ii": 1,   # treat as Phase I slot for simplicity
        "phase iii": 2,
        "filing": 3,
        "approval": 4,
        "launch": 5,
    }

    active_up_to = -1
    if current_phase:
        active_up_to = phase_to_index.get(current_phase.lower(), -1)

    # If no phase from links, check if there are any trial links at all (implies at least Phase I)
    if active_up_to == -1 and trial_links:
        active_up_to = 1  # default to Phase I if links exist

    # If no links and no phase, assume Preclinical
    if active_up_to == -1:
        active_up_to = 0

    stages = []
    for i, label in enumerate(STAGE_LABELS):
        stages.append({
            "stage": label,
            "active": i <= active_up_to
        })
    return stages


def fetch_samsung_pipeline(limit=None, save_to_file=False, output_file="samsung_bioepis_pipeline.json"):
    """
    Scrapes Samsung Bioepis pipeline page and returns standardized JSON.

    Args:
        limit (int, optional): Max number of pipeline entries to scrape.
        save_to_file (bool): Whether to save the result to a JSON file.
        output_file (str): Output filename if save_to_file is True.

    Returns:
        dict: Structured pipeline data.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    pipeline = []

    try:
        driver.get(URL)
        time.sleep(3)  # Wait for JS to load

        boxes = driver.find_elements(By.CSS_SELECTOR, "div.pip_box")

        for idx, box in enumerate(boxes):
            if limit and idx >= limit:
                break

            soup = BeautifulSoup(box.get_attribute("outerHTML"), "html.parser")

            # --- Product code / name ---
            title_tag = soup.select_one("h5.con_tit")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # --- Product type (Biosimilar candidate / Novel biologic) ---
            type_tag = soup.select_one("p.con_stit.bio")
            product_type = type_tag.get_text(strip=True) if type_tag else ""

            # --- Info fields (Molecule, Reference Biologic, Therapeutic Area) ---
            info_dict = {}
            for li in soup.select("ul.pip_info li"):
                strong = li.find("strong")
                span = li.find("span")
                if strong and span:
                    key = strong.get_text(strip=True)
                    value = span.get_text(separator=" ", strip=True)
                    info_dict[key] = value

            molecule = info_dict.get("Molecule", "")
            reference = info_dict.get("Reference Biologic", "")
            therapeutic_area = info_dict.get("Therapeutic Area", "")

            # --- Trial links ---
            trial_links = extract_trial_links(soup)

            # --- Infer current phase from trial link text ---
            current_phase = infer_current_phase(trial_links)

            # --- Build stage pipeline ---
            stages = build_stage_pipeline(current_phase, trial_links)

            clinical_info = {
                "phase": current_phase,
                "link": trial_links[0]["url"] if trial_links else None,
            }

            # --- Assemble product entry ---
            product = {
                "name": title,
                "code": title,
                "type": product_type,
                "details": {
                    "INN": molecule or None,
                    "Reference Drug": reference or None,
                    "Originator": None,
                    "Therapeutic Area": therapeutic_area or None,
                    "Partner": None,
                    "molecule": molecule,
                    "reference_biologic": reference,
                    "therapeutic_area": therapeutic_area,
                },
                "current_phase": current_phase,
                "stages": stages,
                "clinical_info": clinical_info,
                "status_note": product_type or None,
                "clinical_trials": trial_links,
            }

            pipeline.append(product)
            print(f"  ✓ Parsed: {title} ({product_type}) — {current_phase or 'Preclinical'}")

    finally:
        driver.quit()

    result = {
        "company": "Samsung Bioepis",
        "source_url": URL,
        "pipeline_count": len(pipeline),
        "pipeline": pipeline,
    }

    if save_to_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Saved {len(pipeline)} entries to '{output_file}'")

    return result


if __name__ == "__main__":
    print(f"Scraping: {URL}\n")
    data = fetch_samsung_pipeline(save_to_file=True)
    print(f"\n--- Preview (first entry) ---")
    if data["pipeline"]:
        print(json.dumps(data["pipeline"][0], indent=4, ensure_ascii=False))
    print(f"\nTotal entries scraped: {data['pipeline_count']}")
