import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st


@st.cache_data
def try_load_json_file(file_path, modified_time=None):
    """Load and cache JSON file, returning an error string on failure."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file), None
    except FileNotFoundError:
        return None, f"File not found: {file_path}"
    except json.JSONDecodeError as exc:
        return None, f"JSON parsing error in {file_path}: {exc}"


def load_dashboard_data(use_enriched=True):
    """Prefer enriched results, but fall back to raw results if needed."""
    app_dir = os.path.dirname(__file__)
    enriched_json_path = os.path.join(app_dir, "..", "results_enriched.json")
    raw_json_path = os.path.join(app_dir, "..", "results.json")

    if use_enriched:
        enriched_mtime = os.path.getmtime(enriched_json_path) if os.path.exists(enriched_json_path) else None
        enriched_data, enriched_error = try_load_json_file(enriched_json_path, enriched_mtime)
        if enriched_data is not None:
            st.sidebar.success("AI Filter: ON (showing enriched results)")
            return enriched_data

        raw_mtime = os.path.getmtime(raw_json_path) if os.path.exists(raw_json_path) else None
        raw_data, raw_error = try_load_json_file(raw_json_path, raw_mtime)
        if raw_data is not None:
            st.sidebar.warning(
                "AI Filter requested, but enriched data is invalid. Showing raw results instead."
            )
            st.warning(enriched_error)
            return raw_data

        st.error(enriched_error)
        st.error(raw_error)
        st.stop()

    raw_mtime = os.path.getmtime(raw_json_path) if os.path.exists(raw_json_path) else None
    raw_data, raw_error = try_load_json_file(raw_json_path, raw_mtime)
    if raw_data is not None:
        st.sidebar.warning("AI Filter: OFF (showing raw results)")
        return raw_data

    st.error(raw_error)
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
    background-color: #007ACC;
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 6px;
    margin-left: 8px;
}
.new-badge {
    background-color: #FF0000;
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

use_ai_filter = st.sidebar.toggle("AI Filter", value=True)
data = load_dashboard_data(use_ai_filter)
last_updated = data.get("last_updated", "Unknown")

if "companies" not in data:
    st.error("No 'companies' key found in JSON data")
    st.stop()

companies = [company.get("company", "Unknown") for company in data.get("companies", [])]
if not companies:
    st.error("No companies found in data")
    st.stop()

st.title("Company Dashboard")
company_name = st.sidebar.selectbox("Select a Company", companies)
company_data = next((company for company in data["companies"] if company["company"] == company_name), None)

if not company_data:
    st.error(f"Company data not found for {company_name}")
    st.stop()

logo_path = os.path.join(os.path.dirname(__file__), "logos", f"{company_name}.png")

st.markdown('<div class="company-header">', unsafe_allow_html=True)
st.markdown(f"<h1>{company_name} Dashboard</h1>", unsafe_allow_html=True)
st.caption(f"Last Updated: {last_updated}")

if os.path.exists(logo_path):
    st.image(logo_path, width=120)
else:
    st.write("Logo not found:", logo_path)

st.markdown('<div class="company-logo">', unsafe_allow_html=True)


def format_pipeline_status(value):
    if isinstance(value, list):
        return ", ".join(part for part in value if part)
    return value or ""


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
            unsafe_allow_html=True,
        )
else:
    st.write(f"No {company_name} website news available.")

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
            unsafe_allow_html=True,
        )
else:
    st.write(f"No {company_name} Google News available.")

st.header("Drug Pipeline")
pipeline_data = company_data.get("pipeline", [])

if isinstance(pipeline_data, list) and pipeline_data:
    pipeline_df = pd.DataFrame(
        [
            {
                "Drug": item.get("name") or item.get("code", ""),
                "Therapeutic Area": (
                    item.get("details", {}).get("Therapeutic Area")
                    or item.get("details", {}).get("therapeutic_area", "")
                ),
                "Stage": next(
                    (stage["stage"] for stage in reversed(item.get("stages", [])) if stage.get("active")),
                    "Unknown",
                ),
                "Status": format_pipeline_status(
                    item.get("status_note") or item.get("current_phase", "")
                ),
            }
            for item in pipeline_data
            if item.get("name") or item.get("code")
        ]
    )
    st.dataframe(pipeline_df)
else:
    st.write("No pipeline data available.")
