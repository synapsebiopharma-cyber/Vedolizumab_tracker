import json
from datetime import datetime, timedelta

from dotenv import load_dotenv

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
from website_scrapers.samsung_bioepis_scraper import fetch_bioepis_news
from GN_scraper.GW_central import fetch_google_news_rss

# --- Pipeline scrapers ---
from pipeline_scrapers.alvotech_pipeline import fetch_alvotech_pipeline
from pipeline_scrapers.celltrion_pipeline import fetch_celltrion_pipeline
from pipeline_scrapers.Dr_Reddy_pipeline import fetch_dr_reddys_pipeline
from pipeline_scrapers.polpharma_pipeline import fetch_polpharma_pipeline
from pipeline_scrapers.samsung_pipeline import fetch_samsung_pipeline
from pipeline_scrapers.sandoz_pipeline import fetch_sandoz_pipeline
from pipeline_scrapers.samsung_bioepis_pipeline import fetch_samsung_pipeline as fetch_samsung_bioepis_pipeline

# --- Korea scrapers ---
from Korean.Business_korea import scrape_news_section
from Korean.koreabiomed import scrape_news

# --- Clinical trials ---
from Trials.CT import NCT_IDS, fetch_trial
from Trials.fetch_ctri import fetch_ctri_trials
from Trials.fetch_eu_ctis import fetch_eu_ctis_trials

# --- Investor scrapers ---
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

load_dotenv()

RESULTS_FILE = "results.json"
KOREAN_RESULTS_FILE = "korean_results.json"
CLINICAL_TRIALS_FILE = "clinical_trials_hybrid_fixed.json"
CTRI_TRIALS_FILE = "ctri_trials.json"
EU_CTIS_TRIALS_FILE = "eu_ctis_trials.json"
INVESTOR_RESULTS_FILE = "investor_results.json"

SCRAPERS = {
    "Polpharma": {"website": fetch_polpharma_news, "pipeline": fetch_polpharma_pipeline},
    "Alvotech": {"website": fetch_alvotech_news, "pipeline": fetch_alvotech_pipeline},
    "Fresenius": {"website": fetch_fresenius_news},
    "Dr Reddy": {"website": fetch_dr_reddys_news, "pipeline": fetch_dr_reddys_pipeline},
    "Celltrion": {"website": fetch_celltrion_news, "pipeline": fetch_celltrion_pipeline},
    "Samsung Biologics": {"website": fetch_samsung_news, "pipeline": fetch_samsung_pipeline},
    "Samsung Bioepis": {"website": fetch_bioepis_news, "pipeline": fetch_samsung_bioepis_pipeline},
    "Sandoz": {"website": fetch_sandoz_news, "pipeline": fetch_sandoz_pipeline},
    "Biocon": {"website": fetch_biocon_news},
    "Advanz": {"website": fetch_advanz_news},
    "Teva": {"website": fetch_teva_news},
    "MS Pharma": {"website": fetch_mspharma_news},
    "Fuji Pharma": {"website": fetch_fuji_news},
}

INVESTOR_SCRAPERS = {
    "Alvotech": fetch_alvotech_investor,
    "Biocon": fetch_biocon_investor,
    "Celltrion": fetch_celltrion_investor,
    "Dr Reddy": fetch_dr_reddy_investor,
    "Fresenius": fetch_fresenius_investor,
    "Samsung Biologics": fetch_samsung_investor,
    "Teva": fetch_teva_investor,
}


def load_results(file_path, key_name):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict) and key_name in data:
                return data[key_name]
            return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        print(
            f"Warning: JSON parse error in {file_path}: {exc}. "
            "Starting with an empty list to avoid data loss."
        )
        return []


def save_results(file_path, key_name, data):
    wrapper = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        key_name: data,
    }
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(wrapper, file, indent=2, ensure_ascii=False)


def parse_item_datetime(date_value):
    """
    Parse supported date strings from news scrapers into a datetime.
    Returns None when the format is unknown.
    """
    text = str(date_value or "").strip()
    if not text:
        return None

    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def is_recent_item(item, window_hours=24):
    """
    Return True only when the item's date falls within the recent time window.
    """
    published_at = parse_item_datetime(item.get("date"))
    if published_at is None:
        return False
    return datetime.now() - published_at <= timedelta(hours=window_hours)


def mark_new_items(old_list, new_list, unique_key="link", recent_hours=None):
    """
    Mark items in new_list as new when their unique key was not present before.
    """
    old_keys = {item.get(unique_key) for item in old_list}

    updated_list = []
    for item in new_list:
        item_copy = item.copy()
        is_unseen = item.get(unique_key) not in old_keys
        is_recent = True if recent_hours is None else is_recent_item(item, recent_hours)
        item_copy["new"] = is_unseen and is_recent
        updated_list.append(item_copy)

    return updated_list


def keep_all_items(data_list):
    """
    Keep the full item history in the repository JSON files.
    The Streamlit app reads directly from these tracked files.
    """
    return data_list


def clear_pipeline_new_flags(pipeline_list):
    """
    Pipeline entries are not trimmed, so we reset prior new flags each run.
    """
    updated = []
    for item in pipeline_list:
        item_copy = item.copy()
        item_copy["new"] = False
        updated.append(item_copy)
    return updated


def run_all_scrapers():
    results = load_results(RESULTS_FILE, "companies")
    updated = False

    for company, sources in SCRAPERS.items():
        company_entry = next((company_data for company_data in results if company_data["company"] == company), None)
        if not company_entry:
            company_entry = {
                "company": company,
                "website": [],
                "google_news": [],
                "pipeline": [],
            }
            results.append(company_entry)

        if "website" in sources:
            try:
                new_data = sources["website"]()
                company_entry["website"] = mark_new_items(
                    company_entry["website"], new_data, recent_hours=24
                )
                company_entry["website"] = keep_all_items(company_entry["website"])
                updated = True
            except Exception as exc:
                print(f"Warning: error scraping {company} (website): {exc}")

        if "pipeline" in sources:
            try:
                new_data_dict = sources["pipeline"]()
                new_pipeline_list = new_data_dict.get("pipeline", [])
                company_entry["pipeline"] = clear_pipeline_new_flags(company_entry["pipeline"])
                company_entry["pipeline"] = mark_new_items(
                    company_entry["pipeline"], new_pipeline_list
                )
                updated = True
            except Exception as exc:
                print(f"Warning: error scraping {company} (pipeline): {exc}")

        try:
            new_data = fetch_google_news_rss(company)
            company_entry["google_news"] = mark_new_items(
                company_entry["google_news"], new_data, recent_hours=24
            )
            company_entry["google_news"] = keep_all_items(company_entry["google_news"])
            updated = True
        except Exception as exc:
            print(f"Warning: error scraping {company} (google_news): {exc}")

    if updated:
        save_results(RESULTS_FILE, "companies", results)
        print("Company results updated.")
    else:
        print("No new company updates found.")


def run_korean_scrapers():
    results = load_results(KOREAN_RESULTS_FILE, "sources")
    updated = False

    sources = {
        # "Business Korea": scrape_news_section,
        "Korea Biomedical Review": scrape_news,
    }

    for source_name, scraper_func in sources.items():
        source_entry = next((source for source in results if source["source"] == source_name), None)
        if not source_entry:
            source_entry = {"source": source_name, "articles": []}
            results.append(source_entry)

        try:
            new_data = scraper_func()
            source_entry["articles"] = mark_new_items(
                source_entry["articles"], new_data, recent_hours=24
            )
            source_entry["articles"] = keep_all_items(source_entry["articles"])
            updated = True
        except Exception as exc:
            print(f"Warning: error scraping {source_name}: {exc}")

    if updated:
        save_results(KOREAN_RESULTS_FILE, "sources", results)
        print("Korean news results updated.")
    else:
        print("No new Korean updates found.")


def run_clinical_trials():
    trials = []
    updated = False

    for nct_id in NCT_IDS:
        try:
            trial = fetch_trial(nct_id)
            if trial:
                trials.append(trial)
                updated = True
        except Exception as exc:
            print(f"Warning: error fetching trial {nct_id}: {exc}")

    if updated:
        with open(CLINICAL_TRIALS_FILE, "w", encoding="utf-8") as file:
            json.dump(trials, file, ensure_ascii=False, indent=2)
        print(f"ClinicalTrials.gov results updated. ({len(trials)} trials saved)")
    else:
        print("No new ClinicalTrials.gov updates found.")


def run_ctri_trials():
    try:
        trials = fetch_ctri_trials()
        if trials:
            with open(CTRI_TRIALS_FILE, "w", encoding="utf-8") as file:
                json.dump(trials, file, ensure_ascii=False, indent=2)
            print(f"CTRI results updated. ({len(trials)} trials saved)")
        else:
            print("No new CTRI updates found.")
    except Exception as exc:
        print(f"Warning: error fetching CTRI trials: {exc}")


def run_eu_ctis_trials():
    try:
        trials = fetch_eu_ctis_trials()
        if trials:
            with open(EU_CTIS_TRIALS_FILE, "w", encoding="utf-8") as file:
                json.dump(trials, file, ensure_ascii=False, indent=2)
            print(f"EU CTIS results updated. ({len(trials)} trials saved)")
        else:
            print("No new EU CTIS updates found.")
    except Exception as exc:
        print(f"Warning: error fetching EU CTIS trials: {exc}")


def run_investor_scrapers():
    results = load_results(INVESTOR_RESULTS_FILE, "companies")
    updated = False

    for company, scraper_func in INVESTOR_SCRAPERS.items():
        company_entry = next((company_data for company_data in results if company_data["company"] == company), None)
        if not company_entry:
            company_entry = {"company": company, "investor_news": []}
            results.append(company_entry)

        try:
            new_data = scraper_func()
            company_entry["investor_news"] = mark_new_items(
                company_entry["investor_news"], new_data, recent_hours=24
            )
            company_entry["investor_news"] = keep_all_items(company_entry["investor_news"])
            updated = True
        except Exception as exc:
            print(f"Warning: error scraping {company} (investor): {exc}")

    if updated:
        save_results(INVESTOR_RESULTS_FILE, "companies", results)
        print("Investor results updated.")
    else:
        print("No new investor updates found.")


if __name__ == "__main__":
    print("Running company scrapers...")
    run_all_scrapers()

    print("\nRunning AI enrichment for company news...")
    run_enrichment()

    print("\nRunning Korean scrapers...")
    run_korean_scrapers()

    print("\nRunning AI enrichment for Korean news...")
    run_korean_enrichment()

    print("\nRunning ClinicalTrials.gov scraper...")
    run_clinical_trials()

    print("\nRunning CTRI scraper...")
    run_ctri_trials()

    print("\nRunning EU CTIS scraper...")
    run_eu_ctis_trials()

    print("\nRunning investor scrapers...")
    run_investor_scrapers()
