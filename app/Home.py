import os
import json
import streamlit as st
import pandas as pd

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
    with open(enriched_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.sidebar.success("✅ AI Filter: ON (showing enriched results)")
else:
    raw_json_path = os.path.join(os.path.dirname(__file__), "..", "results.json")
    with open(raw_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.sidebar.warning("⚠️ AI Filter: OFF (showing raw results)")

last_updated = data.get("last_updated", "Unknown")
companies = [c["company"] for c in data.get("companies", data)]  # support both formats

# --- Company Dashboard ---
st.title("📊 Company Dashboard")
company_name = st.sidebar.selectbox("Select a Company", companies)

if "companies" in data:  # new format
    company_data = next(c for c in data["companies"] if c["company"] == company_name)
else:  # old format
    company_data = next(c for c in data if c["company"] == company_name)

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
    gnews_df = pd.DataFrame(company_data["google_news"])
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
            "Drug": p.get("name", ""),
            "Therapeutic Area": p.get("details", {}).get("Therapeutic Area", ""),
            "Stage": next((s["stage"] for s in reversed(p.get("stages", [])) if s.get("active")), "Unknown"),
            "Status": p.get("status_note", "")
        }
        for p in pipeline_data if p.get("name")
    ])
    st.dataframe(pipeline_df)
else:
    st.write("No pipeline data available.")
