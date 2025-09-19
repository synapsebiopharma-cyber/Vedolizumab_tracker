# news_enricher.py

import os
import sys
import json
import time
import random
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

# --- Configuration ---
MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3

# --- Paths ---
BASE_DIR = os.path.abspath(os.path.join(os.getcwd(), "."))  # one level outside current dir
INPUT_FILE = os.path.join(BASE_DIR, "results.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "results_enriched.json")

# --- Load environment variables ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("🔴 Error: GEMINI_API_KEY not set in environment or .env file.")
    sys.exit(1)
genai.configure(api_key=api_key)


def extract_news_sections(input_file=INPUT_FILE):
    """
    Extract only company name + website + google_news sections from the input JSON file.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both {"companies": [...]} and [...] formats
    companies = data.get("companies", data)

    news_data = {"companies": []}
    for company in companies:
        news_data["companies"].append({
            "company": company.get("company"),
            "website": company.get("website", []),
            "google_news": company.get("google_news", [])
        })

    return news_data, data


def enrich_news(news_data):
    """
    Send the reduced news JSON as text to Gemini for cleaning and tagging.
    Includes robust error handling and retries for API issues and invalid JSON responses.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
    You are an expert AI assistant specializing in cleaning and categorizing pharmaceutical and biotech news.
    Analyze the following JSON content. Your response MUST be only the JSON object, with no other text or markdown formatting.

    For EACH company in "companies", do the following:
    1. Filter out irrelevant news articles from BOTH website and google_news (e.g., stock market noise, non-company news),
       but do NOT remove any news related to biosimilars, generics, or their brand names.
    2. Deduplicate stories that report on the same event.
    3. For EACH remaining news item in BOTH "website" and "google_news":
        - Add a "tag" field with one of these exact values:
          "FDA Approval", "Clinical Trial", "Pipeline", "Collaboration",
          "Financial", "Other", "Acquisition", "Inspection"

    Return ONLY A VALID JSON object with the same structure, but cleaned and tagged.
    JSON Input:
    {json.dumps(news_data, indent=2, ensure_ascii=False)}
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)

            # Clean the response text to remove markdown code fences and whitespace
            cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()

            # Attempt to parse the JSON. If it fails, retry
            enriched = json.loads(cleaned_text)

            # Safety net: enforce tag field
            for company in enriched.get("companies", []):
                for section in ["website", "google_news"]:
                    for item in company.get(section, []):
                        if "tag" not in item or not item["tag"]:
                            item["tag"] = "Other"

            return enriched

        except exceptions.ResourceExhausted as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 5 * (2 ** attempt) + random.uniform(0, 1)
                print(f"⏳ Rate limit hit. Retrying in {wait_time:.2f}s... (Attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                print("🔴 Max retries reached for rate limiting. Aborting.")
                raise e

        except (json.JSONDecodeError, AttributeError) as e:
            if attempt < MAX_RETRIES - 1:
                print(f"🟠 Failed to parse JSON from model response. Retrying... (Attempt {attempt + 2}/{MAX_RETRIES})")
                time.sleep(5)
            else:
                print("🔴 Could not parse JSON response after multiple retries. Aborting.")
                if 'response' in locals() and hasattr(response, 'text'):
                    print("==== FAILED RESPONSE TEXT ====")
                    print(response.text)
                    print("==============================")
                raise e

    print("🔴 Failed to get a valid response from the model after all retries.")
    sys.exit(1)


def merge_enriched_news(full_data, enriched_news, output_file=OUTPUT_FILE):
    """
    Merge enriched news sections back into the full JSON structure.
    """
    enriched_map = {c["company"]: c for c in enriched_news["companies"]}

    companies = full_data.get("companies", full_data)
    for company in companies:
        cname = company.get("company")
        if cname in enriched_map:
            company["website"] = enriched_map[cname].get("website", [])
            company["google_news"] = enriched_map[cname].get("google_news", [])

    if "companies" in full_data:
        full_data["companies"] = companies
    else:
        full_data = companies

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Final enriched results saved to {output_file}")


def run_enrichment(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    """
    Full pipeline: extract -> enrich -> merge -> save
    """
    try:
        print("1. Extracting relevant sections from JSON...")
        news_data, full_data = extract_news_sections(input_file)

        print("2. Enriching news data with Gemini AI...")
        enriched_news = enrich_news(news_data)

        print("3. Merging enriched data and saving final results...")
        merge_enriched_news(full_data, enriched_news, output_file)

    except FileNotFoundError:
        print(f"🔴 Error: Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
