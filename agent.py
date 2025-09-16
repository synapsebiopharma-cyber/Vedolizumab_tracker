import os
import sys
import json
import time
import random
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

# --- Configuration ---
MODEL_NAME = "gemini-1.5-pro"
MAX_RETRIES = 3

# --- Load environment variables ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("🔴 Error: GEMINI_API_KEY not set in environment or .env file.")
    sys.exit(1)
genai.configure(api_key=api_key)


def extract_news_sections(input_file="results.json"):
    """
    Extract only company name + website + google_news sections.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    companies = data["companies"] if "companies" in data else data

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
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
    You are an expert AI assistant specializing in cleaning and categorizing pharmaceutical and biotech news.
    Analyze the following JSON content.
    For EACH company in "companies", do the following:
    1. Filter out irrelevant news articles.
    2. Deduplicate repeated stories.
    3. Add a field "tag" for each news item with one of:
       - "FDA Approval"
       - "Clinical Trial"
       - "Pipeline"
       - "Collaboration"
       - "Financial"
       - "Other"
       - "Acquisition"
       - "Inspection"
    4. Mention each article's key observations within a "detail" field using the link given
    Return ONLY VALID JSON WITH THE SAME STRUCTURE, just cleaned, tagged and with a "detail" field.

    JSON Input:
    {json.dumps(news_data, indent=2, ensure_ascii=False)}
    """

    response = None
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            break
        except exceptions.ResourceExhausted as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 5 * (2 ** attempt) + random.uniform(0, 1)
                print(f"⏳ Rate limit hit. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise e

    if not response:
        print("🔴 Failed to get response.")
        sys.exit(1)

    cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
    # print("==== CLEANED TEXT ====")
    # print(cleaned_text)
    # print("======================")
    return json.loads(cleaned_text)


def merge_enriched_news(full_data, enriched_news, output_file="results_enriched.json"):
    """
    Merge enriched news sections back into the full JSON structure.
    """
    enriched_map = {c["company"]: c for c in enriched_news["companies"]}

    companies = full_data["companies"] if "companies" in full_data else full_data
    for company in companies:
        cname = company.get("company")
        if cname in enriched_map:
            company["google_news"] = enriched_map[cname].get("google_news", [])
            company["website"] = enriched_map[cname].get("website", [])

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Final enriched results saved to {output_file}")


if __name__ == "__main__":
    news_data, full_data = extract_news_sections("results.json")
    enriched_news = enrich_news(news_data)
    merge_enriched_news(full_data, enriched_news)