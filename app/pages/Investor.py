import os
import json
import urllib.parse
import streamlit as st
import pandas as pd
from datetime import datetime

# --- Cache JSON loading ---
@st.cache_data
def load_json_file(file_path, modified_time=None):
    """Load and cache JSON file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON parsing error in {file_path}: {e}")
        return None

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
h1 { font-size: 2rem !important; margin-bottom: 0.5rem; }
h2 { font-size: 1.8rem !important; margin-bottom: 0.5rem; }
h3 { font-size: 1.2rem !important; margin-bottom: 0.3rem; }
.event-card {
    width: 100%;
    border: 1px solid #ddd;
    padding: 12px 16px;
    border-radius: 10px;
    margin-bottom: 10px;
    background-color: #f9f9f9;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
}
.event-card:hover { border-color: #aaa; }
.event-date { color: #555; font-size: 0.82rem; margin-bottom: 5px; }
.event-title {
    text-decoration: none;
    color: #007ACC;
    font-weight: bold;
    font-size: 1rem;
}
.event-title:hover { text-decoration: underline; }
.event-summary { color: #333; margin-top: 5px; font-size: 0.9rem; }
.event-sponsor { font-size: 0.8rem; color: #aaa; margin-top: 5px; }
.doc-links { font-size: 0.8rem; margin-top: 6px; }
.doc-links a { color: #007ACC; text-decoration: none; }
.news-tag {
    background-color: #007ACC;
    color: white;
    font-size: 0.7rem;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 6px;
    margin-left: 6px;
}
.new-badge {
    background-color: #FF0000;
    color: white;
    font-size: 0.7rem;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 6px;
    margin-left: 6px;
}
.section-divider {
    border-top: 1px solid #eee;
    margin: 0.75rem 0 1rem 0;
}
</style>
"""

# --- Config ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COMPANY_CONFIG = {
    "Alvotech":           ("alvotech_events.json",              "events"),
    "Biocon":             ("biocon_earnings.json",              "biocon_recordings"),
    "Celltrion":          ("celltrion_earnings.json",           "celltrion_releases"),
    "Samsung Biologics":  ("samsung_biologics_notices.json",    "notices"),
    "Teva Pharma":        ("teva_pharma_events.json",           "events"),
    "Dr. Reddy's":        ("drreddys_quarterly_results.json",   "quarterly"),
}

# --- Helpers ---

def parse_date_flexible(date_str):
    if not date_str:
        return None
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%d %B %Y", "%d-%m-%Y", "%Y/%m/%d",
                "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            continue
    return None


def badge_new():
    return "<span class='new-badge'>NEW</span>"


def badge_tag(text):
    return "<span class='news-tag'>" + text + "</span>"


def doc_links_html(docs):
    if not docs:
        return ""
    parts = []
    for d in docs:
        if d.get("url") and d.get("text"):
            parts.append("<a href='" + d["url"] + "' target='_blank'>" + d["text"] + "</a>")
    if not parts:
        return ""
    return "<div class='doc-links'>📎 " + " &nbsp;·&nbsp; ".join(parts) + "</div>"


def render_card(date_display, title, url=None, badges="", extra_html=""):
    """
    Single helper that emits one .event-card.
    All fragments are assembled as plain string concatenation — no nested f-strings
    with conditional HTML — so there is no risk of stray tags leaking out.
    """
    if url and url != "#":
        title_part = "<a class='event-title' href='" + url + "' target='_blank'>" + title + "</a>"
    else:
        title_part = "<strong>" + title + "</strong>"

    html = (
        "<div class='event-card'>"
        + "<div class='event-date'>📅 " + str(date_display) + "</div>"
        + "<div>" + title_part + badges + "</div>"
        + extra_html
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# --- Render functions ---

def render_events(data, company, show_upcoming_only):
    events = data.get("events", [])
    if not events:
        st.caption("No events data available.")
        return

    today = datetime.today()
    filtered = []
    for e in events:
        dt = parse_date_flexible(e.get("date", ""))
        if show_upcoming_only and dt and dt < today:
            continue
        filtered.append((dt, e))

    filtered.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=not show_upcoming_only)

    if not filtered:
        st.caption("No upcoming events found.")
        return

    for dt, e in filtered:
        badges = badge_new() if e.get("new") else ""
        time_str = " &nbsp;" + e["time"] if e.get("time") else ""
        date_display = str(e.get("date", "TBD")) + time_str

        webcast = e.get("webcast")
        webcast_url = None
        if isinstance(webcast, str):
            webcast_url = webcast
        elif isinstance(webcast, dict):
            webcast_url = webcast.get("url")
        webcast_part = (
            " &nbsp;<a href='" + webcast_url + "' target='_blank'>🎙️ Webcast</a>"
            if webcast_url else ""
        )

        extra = doc_links_html(e.get("docs", [])) + webcast_part

        render_card(
            date_display=date_display,
            title=e.get("title", "Untitled"),
            url=e.get("url", "#"),
            badges=badges,
            extra_html=extra,
        )


def render_biocon_recordings(data, company, show_upcoming_only):
    recordings = data.get("recordings", [])
    if not recordings:
        st.caption("No recordings data available.")
        return

    today = datetime.today()
    filtered = []
    for item in recordings:
        dt = parse_date_flexible(item.get("date", ""))
        if show_upcoming_only and dt and dt < today:
            continue
        filtered.append((dt, item))

    filtered.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)

    if not filtered:
        st.caption("No matching recordings found.")
        return

    current_fy = None
    for dt, item in filtered:
        fy = item.get("fiscal_year", "")
        if fy and fy != current_fy:
            current_fy = fy
            st.markdown("**" + fy + "**")

        youtube_url = item.get("youtube_url", "")
        embed_url = item.get("embed_url", "")
        extra = (
            "<a href='" + youtube_url + "' target='_blank' style='font-size:0.85rem;'>▶ Watch on YouTube</a>"
            if embed_url and youtube_url else ""
        )

        render_card(
            date_display=item.get("date", "TBD"),
            title=item.get("title", "Untitled"),
            url=youtube_url or None,
            badges=badge_new() if item.get("new") else "",
            extra_html=extra,
        )


def render_celltrion_releases(data, company, show_upcoming_only):
    releases = data.get("releases", [])
    if not releases:
        st.caption("No releases data available.")
        return

    CELLTRION_BASE = "https://celltrion.com/en-us/investment/ir/earnings"

    today = datetime.today()
    filtered = []
    for item in releases:
        dt = parse_date_flexible(item.get("date", ""))
        if show_upcoming_only and dt and dt < today:
            continue
        filtered.append((dt, item))

    filtered.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)

    if not filtered:
        st.caption("No matching releases found.")
        return

    for dt, item in filtered:
        enc = item.get("enc_data", "")
        url = CELLTRION_BASE + "?file=" + urllib.parse.quote(enc, safe="") if enc else CELLTRION_BASE

        render_card(
            date_display=item.get("date") or item.get("raw_date") or "TBD",
            title=item.get("title", "Untitled"),
            url=url,
            badges=badge_new() if item.get("new") else "",
        )


def render_earnings(data, company, show_upcoming_only):
    items = (
        data.get("earnings") or data.get("results") or
        data.get("announcements") or data.get("events") or []
    )
    if not items and isinstance(data, list):
        items = data
    if not items:
        for v in data.values():
            if isinstance(v, list) and v:
                items = v
                break
    if not items:
        st.caption("No earnings data available.")
        return

    today = datetime.today()
    filtered = []
    for item in items:
        date_val = item.get("date") or item.get("period") or item.get("quarter") or ""
        dt = parse_date_flexible(str(date_val))
        if show_upcoming_only and dt and dt < today:
            continue
        filtered.append((dt, item))

    filtered.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)

    if not filtered:
        st.caption("No matching data found.")
        return

    for dt, item in filtered:
        title = (
            item.get("title") or item.get("headline") or
            item.get("quarter") or item.get("period") or "Update"
        )
        summary = item.get("summary") or item.get("description") or ""
        summary_html = "<p class='event-summary'>" + summary + "</p>" if summary else ""
        extra = summary_html + doc_links_html(item.get("docs", []))

        render_card(
            date_display=item.get("date") or item.get("period") or "TBD",
            title=title,
            url=item.get("url") or item.get("link") or "#",
            badges=badge_new() if item.get("new") else "",
            extra_html=extra,
        )


def render_notices(data, company, show_upcoming_only):
    items = (
        data.get("notices") or data.get("announcements") or
        data.get("events") or data.get("news") or []
    )
    if not items:
        for v in data.values():
            if isinstance(v, list) and v:
                items = v
                break
    if not items:
        st.caption("No notices data available.")
        return

    today = datetime.today()
    filtered = []
    for item in items:
        date_val = item.get("date") or item.get("published") or ""
        dt = parse_date_flexible(str(date_val))
        if show_upcoming_only and dt and dt < today:
            continue
        filtered.append((dt, item))

    filtered.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)

    for dt, item in filtered:
        tag = item.get("tag") or item.get("category") or ""
        badges = (badge_tag(tag) if tag else "") + (badge_new() if item.get("new") else "")

        render_card(
            date_display=item.get("date") or item.get("published") or "TBD",
            title=item.get("title") or item.get("headline") or "Notice",
            url=item.get("url") or item.get("link") or "#",
            badges=badges,
        )


def render_trials(data, company, show_upcoming_only):
    items = (
        data.get("trials") or data.get("studies") or
        data.get("results") or data.get("events") or []
    )
    if not items:
        for v in data.values():
            if isinstance(v, list) and v:
                items = v
                break
    if not items:
        st.caption("No clinical trials data available.")
        return

    for item in items:
        status = item.get("status") or item.get("phase") or ""
        sponsor = item.get("sponsor") or item.get("company") or ""
        badges = (badge_tag(status) if status else "") + (badge_new() if item.get("new") else "")
        sponsor_html = "<div class='event-sponsor'>🏢 " + sponsor + "</div>" if sponsor else ""

        render_card(
            date_display=(
                item.get("date") or item.get("start_date") or
                item.get("last_updated") or "TBD"
            ),
            title=item.get("title") or item.get("study_title") or item.get("name") or "Trial",
            url=item.get("url") or item.get("link") or "#",
            badges=badges,
            extra_html=sponsor_html,
        )


def render_quarterly(data, company, show_upcoming_only):
    items = (
        data.get("quarterly_results") or data.get("results") or
        data.get("earnings") or data.get("events") or []
    )
    if not items:
        for v in data.values():
            if isinstance(v, list) and v:
                items = v
                break
    if not items:
        st.caption("No quarterly results data available.")
        return

    today = datetime.today()
    filtered = []
    for item in items:
        date_val = item.get("date") or item.get("period") or item.get("quarter") or ""
        dt = parse_date_flexible(str(date_val))
        if show_upcoming_only and dt and dt < today:
            continue
        filtered.append((dt, item))

    filtered.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)

    for dt, item in filtered:
        title = (
            item.get("title") or item.get("quarter") or
            item.get("period") or "Quarterly Result"
        )
        summary = item.get("summary") or item.get("highlights") or ""
        summary_html = "<p class='event-summary'>" + summary + "</p>" if summary else ""
        extra = summary_html + doc_links_html(item.get("docs", []))

        render_card(
            date_display=item.get("date") or item.get("period") or "TBD",
            title=title,
            url=item.get("url") or item.get("link") or "#",
            badges=badge_new() if item.get("new") else "",
            extra_html=extra,
        )


RENDER_MAP = {
    "events":               render_events,
    "earnings":             render_earnings,
    "notices":              render_notices,
    "trials":               render_trials,
    "quarterly":            render_quarterly,
    "biocon_recordings":    render_biocon_recordings,
    "celltrion_releases":   render_celltrion_releases,
}

# --- Page Layout ---
st.markdown(custom_css, unsafe_allow_html=True)
st.title("📈 Investor Updates")

# --- Sidebar controls ---
companies = list(COMPANY_CONFIG.keys())
selected_company = st.sidebar.selectbox("Select Company", companies)
show_upcoming_only = st.sidebar.toggle("Upcoming Events Only", value=False)
st.sidebar.markdown("---")
st.sidebar.caption("Toggle to filter only future-dated events/results.")

# --- Load data ---
json_file, data_type = COMPANY_CONFIG[selected_company]
json_path = os.path.join(BASE_DIR, json_file)
json_mtime = os.path.getmtime(json_path) if os.path.exists(json_path) else None
data = load_json_file(json_path, json_mtime)

# --- Header ---
logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos", f"{selected_company}.png")
col1, col2 = st.columns([6, 1])
with col1:
    st.subheader(f"{selected_company} — Investor Updates")
    if isinstance(data, dict):
        last_fetched = data.get("last_fetched") or data.get("last_updated") or data.get("last_run") or ""
        total_runs = data.get("total_runs", "")
        new_count = data.get("new_on_last_run", 0)
        meta_parts = []
        if last_fetched:
            meta_parts.append("🕒 Last fetched: " + (last_fetched[:10] if len(last_fetched) >= 10 else last_fetched))
        if total_runs:
            meta_parts.append("🔄 Runs: " + str(total_runs))
        if new_count:
            meta_parts.append("🆕 New on last run: " + str(new_count))
        if meta_parts:
            st.caption("  |  ".join(meta_parts))
with col2:
    if os.path.exists(logo_path):
        st.image(logo_path, width=100)

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# --- Render ---
if data is None:
    st.error(f"❌ Could not load `{json_file}`. Make sure it exists in the project root.")
else:
    render_fn = RENDER_MAP.get(data_type, render_events)
    render_fn(data, selected_company, show_upcoming_only)
