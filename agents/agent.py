import json
import os
import random
import re
import sys
import time

from dotenv import load_dotenv

try:
    import google.generativeai as genai
    from google.api_core import exceptions
except ImportError:
    genai = None
    exceptions = None


MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3
ENRICHMENT_MODE = os.getenv("NEWS_ENRICHMENT_MODE", "auto").strip().lower()

BASE_DIR = os.path.abspath(os.path.join(os.getcwd(), "."))
INPUT_FILE = os.path.join(BASE_DIR, "results.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "results_enriched.json")

VALID_TAGS = (
    "FDA Approval",
    "Clinical Trial",
    "Pipeline",
    "Collaboration",
    "Financial",
    "Other",
    "Acquisition",
    "Inspection",
)

TAG_KEYWORDS = {
    "FDA Approval": (
        "fda approval",
        "approved",
        "approval",
        "clearance",
        "authorized",
        "authorisation",
        "marketing authorization",
        "marketing authorisation",
        "bLA approval",
    ),
    "Clinical Trial": (
        "clinical trial",
        "phase 1",
        "phase 2",
        "phase 3",
        "phase i",
        "phase ii",
        "phase iii",
        "study",
        "trial",
        "patient enrollment",
        "topline",
    ),
    "Pipeline": (
        "pipeline",
        "biosimilar",
        "generic",
        "candidate",
        "development",
        "launch",
        "submission",
        "filing",
        "commercial launch",
        "proposed",
    ),
    "Collaboration": (
        "partner",
        "partnership",
        "collaboration",
        "alliance",
        "licensing",
        "license",
        "distribution",
        "agreement",
        "co-development",
        "co-development",
        "supply",
    ),
    "Financial": (
        "earnings",
        "revenue",
        "profit",
        "quarterly",
        "financial results",
        "sales",
        "income",
        "guidance",
        "funding",
        "ipo",
    ),
    "Acquisition": (
        "acquisition",
        "acquire",
        "acquires",
        "merger",
        "buyout",
        "takeover",
    ),
    "Inspection": (
        "inspection",
        "warning letter",
        "483",
        "form 483",
        "gmp",
        "manufacturing issue",
        "plant audit",
        "compliance issue",
    ),
}

KEEP_KEYWORDS = (
    "biosimilar",
    "generic",
    "vedolizumab",
    "adalimumab",
    "ustekinumab",
    "natalizumab",
    "ranibizumab",
    "tirzepatide",
    "semaglutide",
    "tocilizumab",
    "trastuzumab",
    "pegfilgrastim",
    "bevacizumab",
)

IRRELEVANT_KEYWORDS = (
    "share price",
    "shares rise",
    "shares fall",
    "stock price",
    "stock falls",
    "stock rises",
    "dividend",
    "forex",
    "crypto",
    "mutual fund",
    "sensex",
    "nifty",
)

COMPANY_STOP_WORDS = {
    "inc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "group",
    "plc",
    "sa",
    "ag",
    "nv",
    "llc",
    "biologics",
    "pharma",
    "pharmaceuticals",
}


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key and genai is not None:
    genai.configure(api_key=api_key)


def parse_companies_container(data):
    return data.get("companies", data) if isinstance(data, dict) else data


def extract_news_sections(input_file=INPUT_FILE):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    companies = parse_companies_container(data)

    news_data = {"companies": []}
    for company in companies:
        news_data["companies"].append(
            {
                "company": company.get("company"),
                "google_news": company.get("google_news", []),
            }
        )

    return news_data, data


def normalize_text(value):
    value = str(value or "").lower().strip()
    value = re.sub(r"\s*[-|]\s*[^-|]+$", "", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def company_tokens(company_name):
    tokens = []
    for token in normalize_text(company_name).split():
        if len(token) > 2 and token not in COMPANY_STOP_WORDS:
            tokens.append(token)
    return tokens


def article_text(item):
    return " ".join(
        str(item.get(field, "") or "")
        for field in ("title", "source", "summary", "description")
    ).strip()


def contains_keyword(text, keyword):
    pattern = r"\b" + re.escape(keyword).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text) is not None


def classify_tag(item):
    text = normalize_text(article_text(item))
    for tag in (
        "FDA Approval",
        "Clinical Trial",
        "Acquisition",
        "Inspection",
        "Collaboration",
        "Financial",
        "Pipeline",
    ):
        if any(contains_keyword(text, keyword) for keyword in TAG_KEYWORDS[tag]):
            return tag
    return "Other"


def is_relevant_article(company_name, item):
    text = normalize_text(article_text(item))
    if not text:
        return False

    if any(contains_keyword(text, keyword) for keyword in KEEP_KEYWORDS):
        return True

    tokens = company_tokens(company_name)
    mentions_company = any(token in text for token in tokens)
    if not mentions_company:
        return False

    if any(contains_keyword(text, keyword) for keyword in IRRELEVANT_KEYWORDS):
        business_signal = any(
            contains_keyword(text, keyword)
            for keyword in (
                "approval",
                "trial",
                "biosimilar",
                "generic",
                "launch",
                "partner",
                "acquisition",
                "inspection",
                "manufacturing",
                "plant",
                "facility",
            )
        )
        if not business_signal:
            return False

    return True


def dedupe_articles(items):
    seen = set()
    deduped = []
    for item in items:
        key = normalize_text(item.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def local_enrich_news(news_data):
    enriched = {"companies": []}

    for company in news_data.get("companies", []):
        filtered_items = []
        for item in company.get("google_news", []):
            if not is_relevant_article(company.get("company", ""), item):
                continue

            enriched_item = dict(item)
            tag = classify_tag(enriched_item)
            enriched_item["tag"] = tag if tag in VALID_TAGS else "Other"
            filtered_items.append(enriched_item)

        enriched["companies"].append(
            {
                "company": company.get("company"),
                "google_news": dedupe_articles(filtered_items),
            }
        )

    return enriched


def build_prompt(news_data):
    return f"""
You are an expert AI assistant specializing in cleaning and categorizing pharmaceutical and biotech news.
Analyze the following JSON content. Your response MUST be only the JSON object, with no other text or markdown formatting.

For EACH company in "companies", do the following:
1. Filter out irrelevant news articles from google_news (e.g., stock market noise, non-company news),
   but do NOT remove any news related to biosimilars, generics, or their brand names.
2. Deduplicate stories that report on the same event.
3. For EACH remaining news item in "google_news":
   - Add a "tag" field with one of these exact values:
     "FDA Approval", "Clinical Trial", "Pipeline", "Collaboration",
     "Financial", "Other", "Acquisition", "Inspection"

Return ONLY A VALID JSON object with the same structure, but cleaned and tagged.
JSON Input:
{json.dumps(news_data, indent=2, ensure_ascii=False)}
""".strip()


def clean_model_response(text):
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def validate_enriched_news(enriched):
    if not isinstance(enriched, dict):
        raise ValueError("Model response is not a JSON object.")

    companies = enriched.get("companies")
    if not isinstance(companies, list):
        raise ValueError("Model response is missing a companies list.")

    for company in companies:
        company.setdefault("google_news", [])
        for item in company.get("google_news", []):
            if item.get("tag") not in VALID_TAGS:
                item["tag"] = "Other"

    return enriched


def gemini_enrich_news(news_data):
    if genai is None or exceptions is None:
        raise RuntimeError("google-generativeai is not installed.")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    model = genai.GenerativeModel(MODEL_NAME)
    prompt = build_prompt(news_data)

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            enriched = json.loads(clean_model_response(getattr(response, "text", "")))
            return validate_enriched_news(enriched)

        except exceptions.ResourceExhausted:
            if attempt == MAX_RETRIES - 1:
                raise
            wait_time = 5 * (2**attempt) + random.uniform(0, 1)
            print(
                f"Rate limit hit. Retrying in {wait_time:.2f}s "
                f"(attempt {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(wait_time)

        except (json.JSONDecodeError, AttributeError, ValueError):
            if attempt == MAX_RETRIES - 1:
                raise
            print(
                f"Failed to parse model JSON. Retrying "
                f"(attempt {attempt + 2}/{MAX_RETRIES})"
            )
            time.sleep(5)


def enrich_news(news_data):
    if ENRICHMENT_MODE == "local":
        print("Using local enrichment mode.")
        return local_enrich_news(news_data)

    if ENRICHMENT_MODE not in {"auto", "api"}:
        print(
            f"Unknown NEWS_ENRICHMENT_MODE='{ENRICHMENT_MODE}'. "
            "Falling back to auto mode."
        )

    try:
        print("Trying Gemini enrichment...")
        return gemini_enrich_news(news_data)
    except Exception as exc:
        if ENRICHMENT_MODE == "api":
            raise

        print(f"Gemini enrichment unavailable: {exc}")
        print("Falling back to local rule-based enrichment.")
        return local_enrich_news(news_data)


def merge_enriched_news(full_data, enriched_news, output_file=OUTPUT_FILE):
    enriched_map = {c["company"]: c for c in enriched_news["companies"]}

    companies = parse_companies_container(full_data)
    for company in companies:
        cname = company.get("company")
        if cname in enriched_map:
            company["google_news"] = enriched_map[cname].get("google_news", [])

    if isinstance(full_data, dict) and "companies" in full_data:
        full_data["companies"] = companies
    else:
        full_data = companies

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)

    print(f"Final enriched results saved to {output_file}")


def run_enrichment(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    try:
        print("1. Extracting relevant sections from JSON...")
        news_data, full_data = extract_news_sections(input_file)

        print("2. Enriching news data...")
        enriched_news = enrich_news(news_data)

        print("3. Merging enriched data and saving final results...")
        merge_enriched_news(full_data, enriched_news, output_file)

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_enrichment()
