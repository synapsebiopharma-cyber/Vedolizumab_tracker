import os
import json
import streamlit as st
import pandas as pd

# --- CSS Styling ---
custom_css = """
<style>

/* Reduce page margins */
.block-container {
    padding-top: 1rem;
    padding-bottom: 5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}
/* Logo container aligned to far right */
.company-logo {
    position: absolute;
    top: 1rem;
    right: 2rem;
}

/* Adjust heading size */
h1 {
    font-size: 2rem !important;
    margin-bottom: 0.5rem;
}
h2 {
    font-size: 1.8rem !important;
    margin-bottom: 0.5rem;
}

/* Place logo at top-right */
.company-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Tag styling */
.news-tag {
    background-color: #007ACC;
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

# --- Load enriched JSON file ---
with open("results_enriched.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract metadata
last_updated = data.get("last_updated", "Unknown")
companies = [c["company"] for c in data.get("companies", data)]  # support both old & new format

# Sidebar company selection (dropdown, no typing)
company_name = st.sidebar.selectbox("Select a Company", companies)

# Get selected company data
if "companies" in data:  # new format with metadata
    company_data = next(c for c in data["companies"] if c["company"] == company_name)
else:  # fallback for old format
    company_data = next(c for c in data if c["company"] == company_name)

# --- Company Logo + Heading ---
logo_path = f"logos/{company_name}.png"  # assumes logos are in /logos

st.markdown('<div class="company-header">', unsafe_allow_html=True)

# Heading (left side)
st.markdown(f"<h1>{company_name} Dashboard</h1>", unsafe_allow_html=True)
st.caption(f"🕒 Last Updated: {last_updated}")

# Logo (right side)
if os.path.exists(logo_path):
    st.image(logo_path, width=120)

st.markdown('<div class="company-logo">', unsafe_allow_html=True)

# --- Website News (limit to top 5) ---
st.header(f"{company_name} Website")
if company_data.get("website"):
    news_df = pd.DataFrame(company_data["website"]).head(5)  # Limit to top 5
    for _, row in news_df.iterrows():
        tag_html = f"<span class='news-tag'>{row['tag']}</span>" if row.get("tag") else ""
        st.markdown(f"- **{row['date']}**: [{row['title']}]({row['link']}) {tag_html}", unsafe_allow_html=True)
else:
    st.write(f"No {company_name} website news available.")

# --- Google News (limit to top 5) ---
st.header("Google News")
if company_data.get("google_news"):
    gnews_df = pd.DataFrame(company_data["google_news"]).head(5)  # Limit to top 5
    for _, row in gnews_df.iterrows():
        tag_html = f"<span class='news-tag'>{row['tag']}</span>" if row.get("tag") else ""
        st.markdown(f"- **{row['date']}**: [{row['title']}]({row['link']}) {tag_html}", unsafe_allow_html=True)
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
            # ✅ get the *last true* stage
            "Stage": next((s["stage"] for s in reversed(p.get("stages", [])) if s.get("active")), "Unknown"),
            "Status": p.get("status_note", ""),
            "Tag": p.get("tag", "")  # NEW: add tag if present
        }
        for p in pipeline_data
        if p.get("name")  # filter out empty entries
    ])

    st.dataframe(pipeline_df)
else:
    st.write("No pipeline data available.")
