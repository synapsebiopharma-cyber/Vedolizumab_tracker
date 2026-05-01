import json
import pandas as pd
import streamlit as st
import os

st.title("📰 Korean Biopharma News")

# --- Cache JSON loading to prevent reloading on every rerun ---
@st.cache_data
def load_korean_json(file_path, modified_time=None):
    """Load and cache Korean news JSON file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"Could not find {file_path}")
        return {"sources": []}
    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error in {file_path}: {e}")
        return {"sources": []}

# --- Sidebar toggle for AI Filter ---
use_ai_filter = st.sidebar.toggle("AI Filter", value=True)  # ✅ ON by default

# --- Load JSON file depending on toggle ---
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if use_ai_filter:
    json_path = os.path.join(root_dir, "korean_results_enriched.json")
    json_mtime = os.path.getmtime(json_path) if os.path.exists(json_path) else None
    korean_news = load_korean_json(json_path, json_mtime)
    st.sidebar.success("✅ AI Filter: ON (showing enriched results)")
else:
    json_path = os.path.join(root_dir, "korean_results.json")
    json_mtime = os.path.getmtime(json_path) if os.path.exists(json_path) else None
    korean_news = load_korean_json(json_path, json_mtime)
    st.sidebar.warning("⚠️ AI Filter: OFF (showing raw results)")


# --- Custom CSS to make content full width ---
st.markdown(
    """
    <style>
    .block-container {
        max-width: 100% !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .news-card {
        width: 100%;
        border: 1px solid #ddd;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 12px;
        background-color: #f9f9f9;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .new-badge {
        background-color: #ff4b4b;
        color: white;
        font-size: 0.7rem;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 6px;
        margin-left: 6px;
    }
    .news-tag {
        background-color: #007ACC;
        color: white;
        font-size: 0.7rem;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 6px;
        margin-left: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Display Korean News ---
for source in korean_news.get("sources", []):
    with st.expander(source["source"], expanded=True):
        news_df = pd.DataFrame(source.get("articles", []))
        for _, row in news_df.iterrows():
            new_html = "<span class='new-badge'>NEW</span>" if row.get("new") is True else ""
            tag_html = f"<span class='news-tag'>{row['tag']}</span>" if "tag" in row and row["tag"] else ""

            st.markdown(
                f"""
                <div class="news-card">
                    <span style="color:#555;font-size:0.85rem;">{row.get('date','')}</span> {new_html} {tag_html}<br>
                    <a href='{row.get('link','')}' target='_blank' style='text-decoration:none;color:#007ACC;font-weight:bold;font-size:1rem;'>{row.get('title','')}</a>
                    <p style='color:#333;margin-top:5px;font-size:0.9rem;'>{row.get('summary','')}</p>
                </div>
                """, unsafe_allow_html=True
            )
