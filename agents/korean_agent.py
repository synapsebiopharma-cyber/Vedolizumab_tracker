# korean_news_enricher.py

import os
import sys
import json
import time
import random
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

# --- Config ---
MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3

# --- Paths ---
BASE_DIR = os.path.abspath(os.path.join(os.getcwd(), ".")) # one level outside 
INPUT_FILE = os.path.join(BASE_DIR, "korean_results.json") 
OUTPUT_FILE = os.path.join(BASE_DIR, "korean_results_enriched.json")

# --- Load env ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("🔴 Error: GEMINI_API_KEY not set.")
    sys.exit(1)
genai.configure(api_key=api_key)


def extract_news_sections(input_file=INPUT_FILE):
    """
    Extract 'sources' and 'articles' from the input JSON.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    news_data = {"sources": []}
    for source in data.get("sources", []):
        news_data["sources"].append({
            "source": source.get("source"),
            "articles": source.get("articles", [])
        })

    return news_data, data


def enrich_korean_news(news_data):
    """
    Clean, deduplicate, and tag Korean news articles (no summary added).
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
    You are an expert AI assistant specializing in pharmaceutical and biotech news.
    Analyze the following JSON content. Your response MUST be only the JSON object, with no other text or markdown.

    For EACH 'source' and its 'articles':
    1. Filter out irrelevant news (e.g., stock/finance, non-company stories). Keep biosimilars, generics, brand-related articles.
    2. Deduplicate similar articles.
    3. For EACH remaining article:
       - Add a "tag" field with one of:
         "FDA Approval", "Clinical Trial", "Pipeline", "Collaboration",
         "Financial", "Other", "Acquisition", "Inspection"

    ⚠️ Do NOT add a 'detail' or summary field.

    Return ONLY a valid JSON with the same structure, cleaned and tagged.

    JSON Input:
    {json.dumps(news_data, indent=2, ensure_ascii=False)}
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)

            cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            enriched = json.loads(cleaned_text)

            # Safety net: enforce tag field
            for source in enriched.get("sources", []):
                for article in source.get("articles", []):
                    if "tag" not in article or not article["tag"]:
                        article["tag"] = "Other"

            return enriched

        except exceptions.ResourceExhausted as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 5 * (2 ** attempt) + random.uniform(0, 1)
                print(f"⏳ Rate limit hit. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print("🔴 Max retries reached. Aborting.")
                raise e

        except (json.JSONDecodeError, AttributeError):
            if attempt < MAX_RETRIES - 1:
                print(f"🟠 Invalid JSON response. Retrying... (Attempt {attempt+2}/{MAX_RETRIES})")
                time.sleep(5)
            else:
                print("🔴 Could not parse JSON. Last response:")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(response.text)
                raise

    sys.exit(1)


def merge_enriched_news(full_data, enriched_news, output_file=OUTPUT_FILE):
    """
    Merge enriched articles back into the full JSON structure.
    """
    enriched_map = {s["source"]: s for s in enriched_news["sources"]}

    for source in full_data.get("sources", []):
        sname = source.get("source")
        if sname in enriched_map:
            source["articles"] = enriched_map[sname].get("articles", [])

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Final enriched results saved to {output_file}")


def run_korean_enrichment(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    """
    Full pipeline: extract -> enrich -> merge -> save
    """
    try:
        print("1. Extracting news sections...")
        news_data, full_data = extract_news_sections(input_file)

        print("2. Enriching with Gemini...")
        enriched_news = enrich_korean_news(news_data)

        print("3. Merging enriched news and saving...")
        merge_enriched_news(full_data, enriched_news, output_file)

    except FileNotFoundError:
        print(f"🔴 Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
