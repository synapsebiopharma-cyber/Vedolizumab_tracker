import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime

# --- Cache JSON loading to prevent reloading on every rerun ---
@st.cache_data
def load_json_file(file_path):
    """Load and cache JSON file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"❌ File not found: {file_path}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON parsing error in {file_path}: {e}")
        st.stop()


def sort_news_by_date(items):
    """Sort news items newest first, tolerating missing or invalid dates."""
    def parse_date(value):
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return datetime.min

    return sorted(items, key=lambda item: parse_date(item.get("date")), reverse=True)

# --- CSS Styling ---
custom_css = """
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}
.company-logo {
    position: absolute;
    top: 1rem;
    right: 2rem;
}
h1 {
    font-size: 2rem !important;
    margin-bottom: 0.5rem;
}
h2 {
    font-size: 1.8rem !important;
    margin-bottom: 0.5rem;
}
.company-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.news-tag {
    background-color: #007ACC;  /* Blue for normal tags */
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 6px;
    margin-left: 8px;
}
.new-badge {
    background-color: #FF0000;  /* Red for NEW */
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 6px;
    margin-left: 8px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- Sidebar toggle ---
use_ai_filter = st.sidebar.toggle("AI Filter", value=True)  # ✅ ON by default

# --- Load JSON file depending on toggle ---
if use_ai_filter:
    enriched_json_path = os.path.join(os.path.dirname(__file__), "..", "results_enriched.json")
    data = load_json_file(enriched_json_path)
    st.sidebar.success("✅ AI Filter: ON (showing enriched results)")
else:
    raw_json_path = os.path.join(os.path.dirname(__file__), "..", "results.json")
    data = load_json_file(raw_json_path)
    st.sidebar.warning("⚠️ AI Filter: OFF (showing raw results)")

last_updated = data.get("last_updated", "Unknown")

# --- Safely extract companies ---
if "companies" not in data:
    st.error("❌ No 'companies' key found in JSON data")
    st.stop()

companies = [c.get("company", "Unknown") for c in data.get("companies", [])]
if not companies:
    st.error("❌ No companies found in data")
    st.stop()

# --- Company Dashboard ---
st.title("📊 Company Dashboard")
company_name = st.sidebar.selectbox("Select a Company", companies)

company_data = next((c for c in data["companies"] if c["company"] == company_name), None)

if not company_data:
    st.error(f"❌ Company data not found for {company_name}")
    st.stop()

# Correct path resolution
logo_path = os.path.join(os.path.dirname(__file__), "logos", f"{company_name}.png")


st.markdown('<div class="company-header">', unsafe_allow_html=True)
st.markdown(f"<h1>{company_name} Dashboard</h1>", unsafe_allow_html=True)
st.caption(f"🕒 Last Updated: {last_updated}")

if os.path.exists(logo_path):
    st.image(logo_path, width=120)
else:
    st.write("⚠️ Logo not found:", logo_path)

st.markdown('<div class="company-logo">', unsafe_allow_html=True)


def format_pipeline_status(value):
    if isinstance(value, list):
        return ", ".join(part for part in value if part)
    return value or ""

# --- Website News ---
st.header(f"{company_name} Website")
if company_data.get("website"):
    news_df = pd.DataFrame(company_data["website"])
    for _, row in news_df.iterrows():
        tags_html = []
        if "tag" in row and pd.notna(row["tag"]):
            tags_html.append(f"<span class='news-tag'>{row['tag']}</span>")
        if row.get("new") is True:
            tags_html.append("<span class='new-badge'>NEW</span>")
        tag_html = " ".join(tags_html)

        st.markdown(
            f"- **{row['date']}**: [{row['title']}]({row['link']}) {tag_html}",
            unsafe_allow_html=True
        )
else:
    st.write(f"No {company_name} website news available.")

# --- Google News ---
st.header("Google News")
if company_data.get("google_news"):
    gnews_df = pd.DataFrame(sort_news_by_date(company_data["google_news"]))
    for _, row in gnews_df.iterrows():
        tags_html = []
        if "tag" in row and pd.notna(row["tag"]):
            tags_html.append(f"<span class='news-tag'>{row['tag']}</span>")
        if row.get("new") is True:
            tags_html.append("<span class='new-badge'>NEW</span>")
        tag_html = " ".join(tags_html)

        st.markdown(
            f"- **{row['date']}**: [{row['title']}]({row['link']}) {tag_html}",
            unsafe_allow_html=True
        )
else:
    st.write(f"No {company_name} Google News available.")

# --- Pipeline ---
st.header("Drug Pipeline")
pipeline_data = company_data.get("pipeline", [])

if isinstance(pipeline_data, list) and len(pipeline_data) > 0:
    pipeline_df = pd.DataFrame([
        {
            "Drug": p.get("name") or p.get("code", ""),
            "Therapeutic Area": (
                p.get("details", {}).get("Therapeutic Area")
                or p.get("details", {}).get("therapeutic_area", "")
            ),
            "Stage": next((s["stage"] for s in reversed(p.get("stages", [])) if s.get("active")), "Unknown"),
            "Status": format_pipeline_status(
                p.get("status_note") or p.get("current_phase", "")
            ),
        }
        for p in pipeline_data if p.get("name") or p.get("code")
    ])
    st.dataframe(pipeline_df)
else:
    st.write("No pipeline data available.")
