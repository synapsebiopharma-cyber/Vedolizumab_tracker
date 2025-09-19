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

# --- Korea Scrapers ---
from Korean.Business_korea import scrape_news_section
from Korean.koreabiomed import scrape_news_type2

# --- AI agents ---
from agents.agent import run_enrichment
from agents.korean_agent import run_korean_enrichment

# Load env variables
load_dotenv()

# --- File locations ---
RESULTS_FILE = "results.json"
KOREAN_RESULTS_FILE = "korean_results.json"

# --- Define scrapers by company ---
SCRAPERS = {
    "Polpharma": {"website": fetch_polpharma_news, "pipeline": fetch_polpharma_pipeline},
    "Alvotech": {"website": fetch_alvotech_news, "pipeline": fetch_alvotech_pipeline},
    "Fresenius": {"website": fetch_fresenius_news},
    "Dr Reddy": {"website": fetch_dr_reddys_news, "pipeline": fetch_dr_reddys_pipeline},
    "Celltrion": {"website": fetch_celltrion_news, "pipeline": fetch_celltrion_pipeline},
    "Samsung Biologics": {"website": fetch_samsung_news, "pipeline": fetch_samsung_pipeline},
    "Sandoz": {"website": fetch_sandoz_news, "pipeline": fetch_sandoz_pipeline},
    "Biocon": {"website": fetch_biocon_news},
}

# --- Helper functions ---
def load_results(file_path, key_name):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and key_name in data:
                return data[key_name]
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_results(file_path, key_name, data):
    wrapper = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        key_name: data,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, indent=2, ensure_ascii=False)

def mark_new_items(old_list, new_list):
    old_lookup = [{k: v for k, v in item.items() if k != "new"} for item in old_list]
    updated_list = []
    for item in new_list:
        if item in old_lookup:
            old_item = next(
                o
                for o in old_list
                if {k: v for k, v in o.items() if k != "new"} == item
            )
            old_item.pop("new", None)
            updated_list.append(old_item)
        else:
            new_item = item.copy()
            new_item["new"] = True
            updated_list.append(new_item)
    return updated_list

# --- Company scraping function ---
def run_all_scrapers():
    results = load_results(RESULTS_FILE, "companies")
    updated = False

    for company, sources in SCRAPERS.items():
        company_entry = next((c for c in results if c["company"] == company), None)
        if not company_entry:
            company_entry = {
                "company": company,
                "website": [],
                "google_news": [],
                "pipeline": [],
            }
            results.append(company_entry)

        # Website scraper
        if "website" in sources:
            try:
                new_data = sources["website"]()
                company_entry["website"] = mark_new_items(
                    company_entry["website"], new_data
                )
                updated = True
            except Exception as e:
                print(f"⚠️ Error scraping {company} (website): {e}")

        # Pipeline scraper
        if "pipeline" in sources:
            try:
                new_data_dict = sources["pipeline"]()
                new_pipeline_list = new_data_dict.get("pipeline", [])
                company_entry["pipeline"] = mark_new_items(
                    company_entry["pipeline"], new_pipeline_list
                )
                updated = True
            except Exception as e:
                print(f"⚠️ Error scraping {company} (pipeline): {e}")

        # Google News scraper
        try:
            new_data = fetch_google_news(company)
            company_entry["google_news"] = mark_new_items(
                company_entry["google_news"], new_data
            )
            updated = True
        except Exception as e:
            print(f"⚠️ Error scraping {company} (google_news): {e}")

    if updated:
        save_results(RESULTS_FILE, "companies", results)
        print("✅ Company results updated.")
    else:
        print("ℹ️ No new company updates found.")

# --- Korean scraping function ---
def run_korean_scrapers():
    results = load_results(KOREAN_RESULTS_FILE, "sources")
    updated = False

    SOURCES = {
        "Business Korea": scrape_news_section,
        "Korea Biomedical Review": scrape_news_type2,
    }

    for source_name, scraper_func in SOURCES.items():
        source_entry = next((s for s in results if s["source"] == source_name), None)
        if not source_entry:
            source_entry = {"source": source_name, "articles": []}
            results.append(source_entry)

        try:
            new_data = scraper_func()
            source_entry["articles"] = mark_new_items(
                source_entry["articles"], new_data
            )
            updated = True
        except Exception as e:
            print(f"⚠️ Error scraping {source_name}: {e}")

    if updated:
        save_results(KOREAN_RESULTS_FILE, "sources", results)
        print("✅ Korean news results updated.")
    else:
        print("ℹ️ No new Korean updates found.")

# --- Main runner ---
if __name__ == "__main__":
    print("🚀 Running company scrapers...")
    run_all_scrapers()

    # --- Run AI enrichment for company news ---
    print("\n🤖 Running AI enrichment for company news...")
    run_enrichment()  # saves results_enriched.json automatically

    print("\n🌏 Running Korean scrapers...")
    run_korean_scrapers()

    # --- Run AI enrichment for Korean news ---
    print("\n🤖 Running AI enrichment for Korean news...")
    run_korean_enrichment()  # saves korean_results_enriched.json automatically
