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
from website_scrapers.Advanz_scraper import fetch_advanz_news
from website_scrapers.Teva_scraper import fetch_teva_news
from website_scrapers.MS_scraper import fetch_mspharma_news
from website_scrapers.Fuji_scraper import fetch_fuji_news
from GN_scraper.GW_central import fetch_google_news_rss

# --- Pipeline scrapers ---
from pipeline_scrapers.alvotech_pipeline import fetch_alvotech_pipeline
from pipeline_scrapers.celltrion_pipeline import fetch_celltrion_pipeline
from pipeline_scrapers.Dr_Reddy_pipeline import fetch_dr_reddys_pipeline
from pipeline_scrapers.polpharma_pipeline import fetch_polpharma_pipeline
from pipeline_scrapers.samsung_pipeline import fetch_samsung_pipeline
from pipeline_scrapers.sandoz_pipeline import fetch_sandoz_pipeline

# --- Korea Scrapers ---
from Korean.Business_korea import scrape_news_section
from Korean.koreabiomed import scrape_news

# --- Clinical Trials ---
from Trials.CT import fetch_trial, NCT_IDS
from Trials.fetch_ctri import fetch_ctri_trials
from Trials.fetch_eu_ctis import fetch_eu_ctis_trials

# --- Investor Scrapers ---
from Investor.Alvotech import fetch_alvotech_investor
from Investor.Biocon import fetch_biocon_investor
from Investor.Celltrion import fetch_celltrion_investor
from Investor.Dr_Reddy import fetch_dr_reddy_investor
from Investor.Freesenius import fetch_fresenius_investor
from Investor.Samsung import fetch_samsung_investor
from Investor.Teva import fetch_teva_investor

# --- AI agents ---
from agents.agent import run_enrichment
from agents.korean_agent import run_korean_enrichment

# --- Cloud Backup ---
from backup.backup import backup_to_firestore

# Load env variables
load_dotenv()

# --- File locations ---
RESULTS_FILE = "results.json"
KOREAN_RESULTS_FILE = "korean_results.json"
CLINICAL_TRIALS_FILE = "clinical_trials_hybrid_fixed.json"
CTRI_TRIALS_FILE = "ctri_trials.json"
EU_CTIS_TRIALS_FILE = "eu_ctis_trials.json"
INVESTOR_RESULTS_FILE = "investor_results.json"

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
    "Advanz": {"website": fetch_advanz_news},
    "Teva": {"website": fetch_teva_news},
    "MS Pharma": {"website": fetch_mspharma_news},
    "Fuji Pharma": {"website": fetch_fuji_news}
}

# --- Define investor scrapers by company ---
INVESTOR_SCRAPERS = {
    "Alvotech": fetch_alvotech_investor,
    "Biocon": fetch_biocon_investor,
    "Celltrion": fetch_celltrion_investor,
    "Dr Reddy": fetch_dr_reddy_investor,
    "Fresenius": fetch_fresenius_investor,
    "Samsung Biologics": fetch_samsung_investor,
    "Teva": fetch_teva_investor,
}

# --- Helper functions ---
def load_results(file_path, key_name):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and key_name in data:
                return data[key_name]
            return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error in {file_path}: {e}. Starting with empty list to avoid data loss — please inspect the file.")
        return []

def save_results(file_path, key_name, data):
    wrapper = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        key_name: data,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, indent=2, ensure_ascii=False)

def mark_new_items(old_list, new_list, unique_key="link"):
    """
    Marks items in new_list as 'new: True' if they were not present in old_list,
    and 'new: False' if they were. Recalculates 'new' tags fresh each time.
    """
    old_keys = {item.get(unique_key) for item in old_list}

    updated_list = []
    for item in new_list:
        item_copy = item.copy()
        item_copy["new"] = item.get(unique_key) not in old_keys
        updated_list.append(item_copy)

    return updated_list

def enforce_limit_and_backup(data_list, limit=10, company=None, section=None):
    """
    Keeps only the latest `limit` items in data_list.
    Moves the rest to Firestore (backup).
    If backup fails, the original list is returned untrimmed to prevent data loss.
    """
    if len(data_list) <= limit:
        return data_list

    keep = data_list[:limit]
    overflow = data_list[limit:]

    try:
        backup_to_firestore(company, section, overflow)
    except Exception as e:
        print(f"⚠️ Firestore backup failed for {company}/{section}: {e}. Skipping truncation to prevent data loss.")
        return data_list

    return keep

def clear_pipeline_new_flags(pipeline_list):
    """
    Clears 'new' flags on pipeline items that have been seen before.
    Since pipeline entries are never backed up or truncated, flags must be
    explicitly reset to prevent them from accumulating indefinitely.
    """
    updated = []
    for item in pipeline_list:
        item_copy = item.copy()
        item_copy["new"] = False
        updated.append(item_copy)
    return updated

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
                company_entry["website"] = enforce_limit_and_backup(
                    company_entry["website"], limit=10, company=company, section="website"
                )
                updated = True
            except Exception as e:
                print(f"⚠️ Error scraping {company} (website): {e}")

        # Pipeline scraper (NO backup, unlimited storage)
        if "pipeline" in sources:
            try:
                new_data_dict = sources["pipeline"]()
                new_pipeline_list = new_data_dict.get("pipeline", [])
                company_entry["pipeline"] = clear_pipeline_new_flags(company_entry["pipeline"])
                company_entry["pipeline"] = mark_new_items(
                    company_entry["pipeline"], new_pipeline_list
                )
                updated = True
            except Exception as e:
                print(f"⚠️ Error scraping {company} (pipeline): {e}")

        # Google News scraper
        try:
            new_data = fetch_google_news_rss(company)
            company_entry["google_news"] = mark_new_items(
                company_entry["google_news"], new_data
            )
            company_entry["google_news"] = enforce_limit_and_backup(
                company_entry["google_news"], limit=10, company=company, section="google_news"
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
        # "Business Korea": scrape_news_section,
        "Korea Biomedical Review": scrape_news,
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
            source_entry["articles"] = enforce_limit_and_backup(
                source_entry["articles"], limit=10, company=source_name, section="articles"
            )
            updated = True
        except Exception as e:
            print(f"⚠️ Error scraping {source_name}: {e}")

    if updated:
        save_results(KOREAN_RESULTS_FILE, "sources", results)
        print("✅ Korean news results updated.")
    else:
        print("ℹ️ No new Korean updates found.")

# --- Clinical Trials scraping function (ClinicalTrials.gov) ---
def run_clinical_trials():
    trials = []
    updated = False

    for nct_id in NCT_IDS:
        try:
            trial = fetch_trial(nct_id)
            if trial:
                trials.append(trial)
                updated = True
        except Exception as e:
            print(f"⚠️ Error fetching trial {nct_id}: {e}")

    if updated:
        with open(CLINICAL_TRIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(trials, f, ensure_ascii=False, indent=2)
        print(f"✅ ClinicalTrials.gov results updated. ({len(trials)} trials saved)")
    else:
        print("ℹ️ No new ClinicalTrials.gov updates found.")

# --- CTRI scraping function ---
def run_ctri_trials():
    try:
        trials = fetch_ctri_trials()
        if trials:
            with open(CTRI_TRIALS_FILE, "w", encoding="utf-8") as f:
                json.dump(trials, f, ensure_ascii=False, indent=2)
            print(f"✅ CTRI results updated. ({len(trials)} trials saved)")
        else:
            print("ℹ️ No new CTRI updates found.")
    except Exception as e:
        print(f"⚠️ Error fetching CTRI trials: {e}")

# --- EU CTIS scraping function ---
def run_eu_ctis_trials():
    try:
        trials = fetch_eu_ctis_trials()
        if trials:
            with open(EU_CTIS_TRIALS_FILE, "w", encoding="utf-8") as f:
                json.dump(trials, f, ensure_ascii=False, indent=2)
            print(f"✅ EU CTIS results updated. ({len(trials)} trials saved)")
        else:
            print("ℹ️ No new EU CTIS updates found.")
    except Exception as e:
        print(f"⚠️ Error fetching EU CTIS trials: {e}")

# --- Investor scraping function ---
def run_investor_scrapers():
    results = load_results(INVESTOR_RESULTS_FILE, "companies")
    updated = False

    for company, scraper_func in INVESTOR_SCRAPERS.items():
        company_entry = next((c for c in results if c["company"] == company), None)
        if not company_entry:
            company_entry = {"company": company, "investor_news": []}
            results.append(company_entry)

        try:
            new_data = scraper_func()
            company_entry["investor_news"] = mark_new_items(
                company_entry["investor_news"], new_data
            )
            company_entry["investor_news"] = enforce_limit_and_backup(
                company_entry["investor_news"], limit=10, company=company, section="investor_news"
            )
            updated = True
        except Exception as e:
            print(f"⚠️ Error scraping {company} (investor): {e}")

    if updated:
        save_results(INVESTOR_RESULTS_FILE, "companies", results)
        print("✅ Investor results updated.")
    else:
        print("ℹ️ No new investor updates found.")

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

    print("\n🔬 Running ClinicalTrials.gov scraper...")
    run_clinical_trials()  # saves clinical_trials_hybrid_fixed.json

    print("\n🔬 Running CTRI scraper...")
    run_ctri_trials()  # saves ctri_trials.json

    print("\n🔬 Running EU CTIS scraper...")
    run_eu_ctis_trials()  # saves eu_ctis_trials.json

    print("\n📈 Running investor scrapers...")
    run_investor_scrapers()  # saves investor_results.json