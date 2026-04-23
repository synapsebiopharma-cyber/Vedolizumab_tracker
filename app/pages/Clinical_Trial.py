import json
import os
import streamlit as st
import pandas as pd

st.title("🧪 Clinical Trials")

# ── Cache JSON loading ────────────────────────────────────────────────────────
@st.cache_data
def load_trials_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"Could not find {file_path}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error in {file_path}: {e}")
        return []

# ── Path resolution ───────────────────────────────────────────────────────────
# mirrors investor.py: JSONs are two levels up from this file
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

JSON_FILES = [
    "clinical_trials_hybrid_fixed.json",
    "clinical_trials_eu.json",
    "clinical_trials_ctri.json",
]

all_trials = []
for json_name in JSON_FILES:
    json_path = os.path.join(ROOT_DIR, json_name)
    if not os.path.exists(json_path):
        st.warning("Could not load `" + json_name + "`. Make sure it exists in the project root.")
    else:
        all_trials.extend(load_trials_json(json_path))

if not all_trials:
    st.error("No clinical trials data found across any of the JSON files.")
    st.stop()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { max-width:100% !important; padding-left:2rem; padding-right:2rem; }
.trial-card {
    border:1px solid #ddd; padding:16px; border-radius:10px;
    margin-bottom:16px; background-color:#f9f9f9;
    box-shadow:2px 2px 5px rgba(0,0,0,0.05);
}
.badge {
    display:inline-block; font-size:0.72rem; font-weight:bold;
    padding:2px 8px; border-radius:6px; margin-right:4px; color:white;
}
.badge-phase             { background-color:#6f42c1; }
.badge-status-recruiting { background-color:#28a745; }
.badge-status-active     { background-color:#007ACC; }
.badge-status-other      { background-color:#6c757d; }
.badge-registry-nct      { background-color:#0d6efd; }
.badge-registry-eu       { background-color:#0a7a5e; }
.badge-registry-ctri     { background-color:#c25e00; }
.badge-registry-other    { background-color:#555;    }
.new-badge {
    background-color:#FF0000; color:white; font-size:0.75rem;
    font-weight:bold; padding:2px 6px; border-radius:6px; margin-left:8px;
}
.updated-badge {
    background-color:#FFA500; color:black; font-size:0.75rem;
    font-weight:bold; padding:2px 6px; border-radius:6px; margin-left:8px;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalise_registry(registry, nct_id=""):
    """Return a canonical registry key, inferring from nct_id when registry is blank."""
    r = (registry or "").upper().strip()
    if r in ("EU_CTIS", "EU CTIS", "EU"):
        return "EU_CTIS"
    if r == "CTRI":
        return "CTRI"
    if r in ("NCT", "CLINICALTRIALS.GOV", "CLINICALTRIALS"):
        return "NCT"
    nid = (nct_id or "").strip()
    if nid.upper().startswith("NCT"):
        return "NCT"
    if nid.upper().startswith("CTRI"):
        return "CTRI"
    if "-" in nid and len(nid) > 15:   # EU CTIS pattern: 2022-502778-18-00
        return "EU_CTIS"
    return "NCT"   # default — covers hybrid/ClinicalTrials.gov entries

REGISTRY_LABELS = {
    "NCT":     "ClinicalTrials.gov",
    "EU_CTIS": "EU CTIS",
    "CTRI":    "CTRI",
}
REGISTRY_BADGE_CLS = {
    "NCT":     "badge-registry-nct",
    "EU_CTIS": "badge-registry-eu",
    "CTRI":    "badge-registry-ctri",
}

def status_badge_class(status):
    s = (status or "").upper()
    if "RECRUITING" in s and "NOT" not in s:
        return "badge-status-recruiting"
    if "ACTIVE" in s or "AUTHORIZED" in s:
        return "badge-status-active"
    return "badge-status-other"

def make_registry_badge(registry, nct_id=""):
    key   = normalise_registry(registry, nct_id)
    label = REGISTRY_LABELS.get(key, registry or "Unknown")
    cls   = REGISTRY_BADGE_CLS.get(key, "badge-registry-other")
    return "<span class='badge " + cls + "'>" + label + "</span>"

def trial_url(t):
    nct_id = t.get("nct_id", "")
    key = normalise_registry(t.get("registry", ""), nct_id)
    if key == "CTRI":
        ctri_id = t.get("ctri_id") or nct_id
        return "https://ctri.nic.in/Clinicaltrials/showallp.php?mid1=&EncHid=&Nnid=" + ctri_id
    if key == "EU_CTIS":
        eu_num = t.get("eu_ct_number") or nct_id
        return "https://www.clinicaltrialsregister.eu/ctr-search/trial/" + eu_num
    return "https://clinicaltrials.gov/study/" + nct_id

# ── Registry filter ───────────────────────────────────────────────────────────
reg_keys = sorted({
    normalise_registry(t.get("registry", ""), t.get("nct_id", ""))
    for t in all_trials
})
registry_options  = ["All"] + [REGISTRY_LABELS.get(k, k) for k in reg_keys]
label_to_key      = {v: k for k, v in REGISTRY_LABELS.items()}

selected_label = st.selectbox("Filter by Registry", registry_options)
selected_key   = label_to_key.get(selected_label)

if selected_label == "All":
    trials = all_trials
else:
    trials = [
        t for t in all_trials
        if normalise_registry(t.get("registry", ""), t.get("nct_id", "")) == selected_key
    ]

st.caption("Showing **" + str(len(trials)) + "** of **" + str(len(all_trials)) + "** trials")

# ── View toggle ───────────────────────────────────────────────────────────────
view_mode = st.radio("View", ["Cards", "Table"], horizontal=True)

# ── TABLE VIEW ────────────────────────────────────────────────────────────────
if view_mode == "Table":
    rows = []
    for t in trials:
        reg_key = normalise_registry(t.get("registry", ""), t.get("nct_id", ""))
        rows.append({
            "Registry":   REGISTRY_LABELS.get(reg_key, reg_key),
            "ID":         t.get("nct_id") or t.get("eu_ct_number") or t.get("ctri_id") or "",
            "Title":      t.get("brief_title", ""),
            "Phase":      ", ".join(t.get("phase") or []),
            "Status":     t.get("status", ""),
            "Sponsor":    t.get("sponsor", ""),
            "Condition":  ", ".join(t.get("conditions") or []),
            "Enrollment": t.get("enrollment", ""),
            "Change":     (t.get("change_status") or "").upper(),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── CARD VIEW ─────────────────────────────────────────────────────────────────
else:
    for t in trials:
        nct_id        = t.get("nct_id", "")
        title         = t.get("brief_title") or "N/A"
        status        = t.get("status") or "Unknown"
        sponsor       = t.get("sponsor") or "Unknown"
        phases        = t.get("phase") or []
        conditions    = t.get("conditions") or []
        enrollment    = t.get("enrollment")
        outcomes      = t.get("outcomes") or []
        interventions = t.get("interventions") or []
        locations     = t.get("locations") or []
        change_status = t.get("change_status") or ""
        registry      = t.get("registry") or ""
        who_utn       = t.get("who_utn") or ""
        short_title   = t.get("short_title") or ""

        # Build every HTML snippet as a plain string — no nested f-string conditionals
        phase_badges = "".join(
            "<span class='badge badge-phase'>" + p.replace("PHASE", "Phase ") + "</span>"
            for p in phases
        )

        status_label = status.replace("_", " ").title()
        status_html  = "<span class='badge " + status_badge_class(status) + "'>" + status_label + "</span>"
        reg_html     = make_registry_badge(registry, nct_id)

        if change_status == "new":
            change_html = "<span class='new-badge'>NEW</span>"
        elif change_status == "updated":
            change_html = "<span class='updated-badge'>UPDATED</span>"
        else:
            change_html = ""

        url = trial_url(t)

        enrollment_html = (
            "&nbsp;|&nbsp; <strong>Enrollment:</strong> " + str(enrollment)
            if enrollment else ""
        )
        short_title_html = (
            "<p style='margin:2px 0;font-size:0.9rem;'><strong>Short Title:</strong> " + short_title + "</p>"
            if short_title else ""
        )
        conditions_str = ", ".join(conditions) or "N/A"
        interventions_html = (
            "<p style='margin:2px 0;font-size:0.9rem;'><strong>Interventions:</strong> "
            + ", ".join(interventions) + "</p>"
            if interventions else ""
        )
        who_utn_html = (
            "<p style='margin:2px 0;font-size:0.9rem;'><strong>WHO UTN:</strong> " + who_utn + "</p>"
            if who_utn else ""
        )

        card_html = (
            "<div class='trial-card'>"
            "<div style='margin-bottom:8px;'>"
            + reg_html + " " + phase_badges + " " + status_html + " " + change_html
            + "</div>"
            "<p style='margin:2px 0;font-size:0.9rem;'>"
            "<strong>ID:</strong> <a href='" + url + "' target='_blank'>" + nct_id + "</a>"
            "&nbsp;|&nbsp; <strong>Sponsor:</strong> " + sponsor
            + enrollment_html
            + "</p>"
            + short_title_html
            + "<p style='margin:2px 0;font-size:0.9rem;'>"
            "<strong>Condition(s):</strong> " + conditions_str
            + "</p>"
            + interventions_html
            + who_utn_html
            + "</div>"
        )

        with st.expander("🔬 " + title, expanded=False):
            st.markdown(card_html, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if outcomes:
                    st.markdown("**🎯 Primary Outcome(s)**")
                    for o in outcomes:
                        st.markdown("- " + o)

            with col2:
                if locations:
                    st.markdown("**📍 Locations**")
                    for loc in locations[:5]:
                        st.markdown("- " + loc)
                    if len(locations) > 5:
                        st.markdown("*...and " + str(len(locations) - 5) + " more*")

            eligibility = t.get("eligibility") or ""
            if eligibility:
                with st.expander("📋 Eligibility Criteria", expanded=False):
                    st.markdown(eligibility)