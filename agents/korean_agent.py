# korean_news_enricher.py

import os
import sys
import json
import time
import random
import re

from dotenv import load_dotenv

try:
    import google.generativeai as genai
    from google.api_core import exceptions
except ImportError:
    genai = None
    exceptions = None

# --- Config ---
MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3
ENRICHMENT_MODE = os.getenv("KOREAN_NEWS_ENRICHMENT_MODE", "auto").strip().lower()

# --- Paths ---
BASE_DIR = os.path.abspath(os.path.join(os.getcwd(), ".")) # one level outside 
INPUT_FILE = os.path.join(BASE_DIR, "korean_results.json") 
OUTPUT_FILE = os.path.join(BASE_DIR, "korean_results_enriched.json")

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
        "authorization",
        "authorisation",
        "marketing authorization",
        "marketing authorisation",
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
    "vedolizumab",
    "biosimilar",
    "generic",
    "brand",
    "celltrion",
    "samsung bioepis",
    "alvotech",
    "biocon",
    "mabxience",
    "approval",
    "clinical trial",
    "pipeline",
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
    "kospi",
    "kosdaq",
)

# --- Load env ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key and genai is not None:
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


def normalize_text(value):
    value = str(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


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


def is_relevant_article(item):
    text = normalize_text(article_text(item))
    if not text:
        return False

    if any(contains_keyword(text, keyword) for keyword in KEEP_KEYWORDS):
        return True

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
                "facility",
                "pharma",
                "biotech",
            )
        )
        if not business_signal:
            return False

    pharma_signal = any(
        contains_keyword(text, keyword)
        for keyword in (
            "drug",
            "biologic",
            "biosimilar",
            "generic",
            "pharma",
            "biotech",
            "treatment",
            "therapy",
            "clinical",
            "manufacturing",
        )
    )
    return pharma_signal


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


def local_enrich_korean_news(news_data):
    enriched = {"sources": []}

    for source in news_data.get("sources", []):
        filtered_items = []
        for article in source.get("articles", []):
            if not is_relevant_article(article):
                continue

            enriched_article = dict(article)
            tag = classify_tag(enriched_article)
            enriched_article["tag"] = tag if tag in VALID_TAGS else "Other"
            filtered_items.append(enriched_article)

        enriched["sources"].append(
            {
                "source": source.get("source"),
                "articles": dedupe_articles(filtered_items),
            }
        )

    return enriched


def build_prompt(news_data):
    return f"""
    You are an expert AI assistant specializing in pharmaceutical and biotech news.
    Analyze the following JSON content. Your response MUST be only the JSON object, with no other text or markdown.

    For EACH 'source' and its 'articles':
    1. Filter out irrelevant news (e.g., stock/finance, non-company stories). Keep biosimilars, generics, brand-related articles.
    2. Deduplicate similar articles.
    3. For EACH remaining article:
       - Add a "tag" field with one of:
         "FDA Approval", "Clinical Trial", "Pipeline", "Collaboration",
         "Financial", "Other", "Acquisition", "Inspection"

    Do NOT add a 'detail' or summary field.

    Return ONLY a valid JSON with the same structure, cleaned and tagged.

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

    sources = enriched.get("sources")
    if not isinstance(sources, list):
        raise ValueError("Model response is missing a sources list.")

    for source in sources:
        source.setdefault("articles", [])
        for article in source.get("articles", []):
            if article.get("tag") not in VALID_TAGS:
                article["tag"] = "Other"

    return enriched


def gemini_enrich_korean_news(news_data):
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

        except exceptions.ResourceExhausted as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 5 * (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limit hit. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Aborting.")
                raise e

        except (json.JSONDecodeError, AttributeError, ValueError):
            if attempt < MAX_RETRIES - 1:
                print(f"Invalid JSON response. Retrying... (Attempt {attempt+2}/{MAX_RETRIES})")
                time.sleep(5)
            else:
                print("Could not parse JSON. Last response:")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(response.text)
                raise


def enrich_korean_news(news_data):
    """
    Clean, deduplicate, and tag Korean news articles.
    Falls back to a local rule-based filter if Gemini is unavailable.
    """
    if ENRICHMENT_MODE == "local":
        print("Using local enrichment mode.")
        return local_enrich_korean_news(news_data)

    if ENRICHMENT_MODE not in {"auto", "api"}:
        print(
            f"Unknown KOREAN_NEWS_ENRICHMENT_MODE='{ENRICHMENT_MODE}'. "
            "Falling back to auto mode."
        )

    try:
        print("Trying Gemini enrichment...")
        return gemini_enrich_korean_news(news_data)
    except Exception as exc:
        if ENRICHMENT_MODE == "api":
            raise

        print(f"Gemini enrichment unavailable: {exc}")
        print("Falling back to local rule-based enrichment.")
        return local_enrich_korean_news(news_data)


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
        print(f"Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
