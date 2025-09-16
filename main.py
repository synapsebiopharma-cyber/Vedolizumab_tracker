import json
from dotenv import load_dotenv
from datetime import datetime

# --- Website scrapers ---
from website_scrapers.polpharma_scraper import fetch_polpharma_news
from website_scrapers.alvotech_scraper import fetch_alvotech_news
from website_scrapers.fresenius_scraper import fetch_fresenius_news
from website_scrapers.DrReddy_scraper import fetch_dr_reddys_news
from website_scrapers.celltrion_scraper import fetch_celltrion_news
from website_scrapers.samsung_scraper import fetch_samsung_news
from website_scrapers.Sandoz_scraper import fetch_sandoz_news
from website_scrapers.Biocon_scraper import fetch_biocon_news
from GN_scraper.GW_central import fetch_google_news

# --- Pipeline scrapers ---
from pipeline_scrapers.alvotech_pipeline import fetch_alvotech_pipeline
from pipeline_scrapers.celltrion_pipeline import fetch_celltrion_pipeline
from pipeline_scrapers.Dr_Reddy_pipeline import fetch_dr_reddys_pipeline
from pipeline_scrapers.polpharma_pipeline import fetch_polpharma_pipeline
from pipeline_scrapers.samsung_pipeline import fetch_samsung_pipeline
from pipeline_scrapers.sandoz_pipeline import fetch_sandoz_pipeline

load_dotenv()

RESULTS_FILE = "results.json"

# --- Define scrapers by company ---
SCRAPERS = {
    "Polpharma": {
        "website": fetch_polpharma_news,
        "pipeline": fetch_polpharma_pipeline
    },
    "Alvotech": {
        "website": fetch_alvotech_news,
        "pipeline": fetch_alvotech_pipeline
    },
    "Fresenius": {
        "website": fetch_fresenius_news
    },
    "Dr Reddy": {
        "website": fetch_dr_reddys_news,
        "pipeline": fetch_dr_reddys_pipeline
    },
    "Celltrion": {
        "website": fetch_celltrion_news,
        "pipeline": fetch_celltrion_pipeline
    },
    "Samsung Biologics": {
        "website": fetch_samsung_news,
        "pipeline": fetch_samsung_pipeline
    },
    "Sandoz": {
        "website": fetch_sandoz_news,
        "pipeline": fetch_sandoz_pipeline
    },
    "Biocon": {
        "website": fetch_biocon_news
    },
}

# --- Helper functions ---
def load_results():
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Unwrap if top-level contains "companies"
            if isinstance(data, dict) and "companies" in data:
                return data["companies"]
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_results(data):
    wrapper = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "companies": data
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, indent=2, ensure_ascii=False)


def mark_new_items(old_list, new_list):
    """
    Compare old and new lists, marking new items with "new": True.
    Removes the "new" flag for items that already exist.
    """
    # Strip old "new" flags
    old_lookup = [{k: v for k, v in item.items() if k != "new"} for item in old_list]

    updated_list = []
    for item in new_list:
        if item in old_lookup:
            # Existing item, remove "new" if present
            old_item = next(o for o in old_list if {k: v for k, v in o.items() if k != "new"} == item)
            old_item.pop("new", None)
            updated_list.append(old_item)
        else:
            # Mark as new
            new_item = item.copy()
            new_item["new"] = True
            updated_list.append(new_item)
    return updated_list


# --- Main scraping function ---
def run_all_scrapers():
    results = load_results()
    updated = False

    for company, sources in SCRAPERS.items():
        # Find or create company entry
        company_entry = next((c for c in results if c["company"] == company), None)
        if not company_entry:
            company_entry = {
                "company": company,
                "website": [],
                "google_news": [],
                "pipeline": []
            }
            results.append(company_entry)

        # 🔹 Run website scraper
        if "website" in sources:
            try:
                new_data = sources["website"]()
                company_entry["website"] = mark_new_items(company_entry["website"], new_data)
                updated = True
            except Exception as e:
                print(f"⚠️ Error scraping {company} (website): {e}")

        # 🔹 Run pipeline scraper
        if "pipeline" in sources:
            try:
                new_data_dict = sources["pipeline"]()
                # Extract list from dict
                new_pipeline_list = new_data_dict.get("pipeline", [])
                company_entry["pipeline"] = mark_new_items(company_entry["pipeline"], new_pipeline_list)
                updated = True
            except Exception as e:
                print(f"⚠️ Error scraping {company} (pipeline): {e}")

        # 🔹 Run Google News scraper
        try:
            new_data = fetch_google_news(company)
            company_entry["google_news"] = mark_new_items(company_entry["google_news"], new_data)
            updated = True
        except Exception as e:
            print(f"⚠️ Error scraping {company} (google_news): {e}")

    # Save results only if updates were found
    if updated:
        save_results(results)
        print("✅ Results updated: new changes found.")
    else:
        print("ℹ️ No new updates found. File not modified.")


if __name__ == "__main__":
    run_all_scrapers()
