import json
import os

import pandas as pd
import streamlit as st

st.title("Clinical Trials")


@st.cache_data
def load_trials_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        st.warning(f"Could not find {file_path}")
        return []
    except json.JSONDecodeError as exc:
        st.error(f"JSON parsing error in {file_path}: {exc}")
        return []


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
        st.warning(f"Could not load `{json_name}`. Make sure it exists in the project root.")
    else:
        all_trials.extend(load_trials_json(json_path))

if not all_trials:
    st.error("No clinical trials data found across any of the JSON files.")
    st.stop()

st.markdown(
    """
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
.badge-registry-other    { background-color:#555; }
.new-badge {
    background-color:#FF0000; color:white; font-size:0.75rem;
    font-weight:bold; padding:2px 6px; border-radius:6px; margin-left:8px;
}
.updated-badge {
    background-color:#FFA500; color:black; font-size:0.75rem;
    font-weight:bold; padding:2px 6px; border-radius:6px; margin-left:8px;
}
</style>
""",
    unsafe_allow_html=True,
)


def normalise_registry(registry, nct_id=""):
    """Return a canonical registry key, inferring from nct_id when registry is blank."""
    normalized = (registry or "").upper().strip()
    if normalized in ("EU_CTIS", "EU CTIS", "EU"):
        return "EU_CTIS"
    if normalized == "CTRI":
        return "CTRI"
    if normalized in ("NCT", "CLINICALTRIALS.GOV", "CLINICALTRIALS"):
        return "NCT"

    normalized_id = (nct_id or "").strip()
    if normalized_id.upper().startswith("NCT"):
        return "NCT"
    if normalized_id.upper().startswith("CTRI"):
        return "CTRI"
    if "-" in normalized_id and len(normalized_id) > 15:
        return "EU_CTIS"
    return "NCT"


REGISTRY_LABELS = {
    "NCT": "ClinicalTrials.gov",
    "EU_CTIS": "EU CTIS",
    "CTRI": "CTRI",
}

REGISTRY_BADGE_CLS = {
    "NCT": "badge-registry-nct",
    "EU_CTIS": "badge-registry-eu",
    "CTRI": "badge-registry-ctri",
}


def status_badge_class(status):
    normalized = (status or "").upper()
    if "RECRUITING" in normalized and "NOT" not in normalized:
        return "badge-status-recruiting"
    if "ACTIVE" in normalized or "AUTHORIZED" in normalized:
        return "badge-status-active"
    return "badge-status-other"


def make_registry_badge(registry, nct_id=""):
    key = normalise_registry(registry, nct_id)
    label = REGISTRY_LABELS.get(key, registry or "Unknown")
    css_class = REGISTRY_BADGE_CLS.get(key, "badge-registry-other")
    return f"<span class='badge {css_class}'>{label}</span>"


def trial_url(trial):
    nct_id = trial.get("nct_id", "")
    key = normalise_registry(trial.get("registry", ""), nct_id)
    if key == "CTRI":
        ctri_id = trial.get("ctri_id") or nct_id
        return "https://ctri.nic.in/Clinicaltrials/showallp.php?mid1=&EncHid=&Nnid=" + ctri_id
    if key == "EU_CTIS":
        eu_num = trial.get("eu_ct_number") or nct_id
        return "https://www.clinicaltrialsregister.eu/ctr-search/trial/" + eu_num
    return "https://clinicaltrials.gov/study/" + nct_id


reg_keys = sorted(
    {
        normalise_registry(trial.get("registry", ""), trial.get("nct_id", ""))
        for trial in all_trials
    }
)
registry_options = ["All"] + [REGISTRY_LABELS.get(key, key) for key in reg_keys]
label_to_key = {label: key for key, label in REGISTRY_LABELS.items()}

selected_label = st.selectbox("Filter by Registry", registry_options)
selected_key = label_to_key.get(selected_label)

if selected_label == "All":
    trials = all_trials
else:
    trials = [
        trial
        for trial in all_trials
        if normalise_registry(trial.get("registry", ""), trial.get("nct_id", "")) == selected_key
    ]

st.caption(f"Showing **{len(trials)}** of **{len(all_trials)}** trials")

view_mode = st.radio("View", ["Cards", "Table"], horizontal=True)

if view_mode == "Table":
    rows = []
    for trial in trials:
        reg_key = normalise_registry(trial.get("registry", ""), trial.get("nct_id", ""))
        rows.append(
            {
                "Registry": REGISTRY_LABELS.get(reg_key, reg_key),
                "ID": trial.get("nct_id") or trial.get("eu_ct_number") or trial.get("ctri_id") or "",
                "Title": trial.get("brief_title", ""),
                "Phase": ", ".join(trial.get("phase") or []),
                "Status": trial.get("status", ""),
                "Sponsor": trial.get("sponsor", ""),
                "Condition": ", ".join(trial.get("conditions") or []),
                "Enrollment": trial.get("enrollment", ""),
                "Change": (trial.get("change_status") or "").upper(),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    for trial in trials:
        nct_id = trial.get("nct_id", "")
        title = trial.get("brief_title") or "N/A"
        status = trial.get("status") or "Unknown"
        sponsor = trial.get("sponsor") or "Unknown"
        phases = trial.get("phase") or []
        conditions = trial.get("conditions") or []
        enrollment = trial.get("enrollment")
        outcomes = trial.get("outcomes") or []
        interventions = trial.get("interventions") or []
        locations = trial.get("locations") or []
        change_status = trial.get("change_status") or ""
        registry = trial.get("registry") or ""
        who_utn = trial.get("who_utn") or ""
        short_title = trial.get("short_title") or ""

        phase_badges = "".join(
            "<span class='badge badge-phase'>" + phase.replace("PHASE", "Phase ") + "</span>"
            for phase in phases
        )

        status_label = status.replace("_", " ").title()
        status_html = (
            "<span class='badge " + status_badge_class(status) + "'>" + status_label + "</span>"
        )
        reg_html = make_registry_badge(registry, nct_id)

        if change_status == "new":
            change_html = "<span class='new-badge'>NEW</span>"
        elif change_status == "updated":
            change_html = "<span class='updated-badge'>UPDATED</span>"
        else:
            change_html = ""

        url = trial_url(trial)

        enrollment_html = (
            "&nbsp;|&nbsp; <strong>Enrollment:</strong> " + str(enrollment) if enrollment else ""
        )
        short_title_html = (
            "<p style='margin:2px 0;font-size:0.9rem;'><strong>Short Title:</strong> "
            + short_title
            + "</p>"
            if short_title
            else ""
        )
        conditions_str = ", ".join(conditions) or "N/A"
        interventions_html = (
            "<p style='margin:2px 0;font-size:0.9rem;'><strong>Interventions:</strong> "
            + ", ".join(interventions)
            + "</p>"
            if interventions
            else ""
        )
        who_utn_html = (
            "<p style='margin:2px 0;font-size:0.9rem;'><strong>WHO UTN:</strong> "
            + who_utn
            + "</p>"
            if who_utn
            else ""
        )

        card_html = (
            "<div class='trial-card'>"
            "<div style='margin-bottom:8px;'>"
            + reg_html
            + " "
            + phase_badges
            + " "
            + status_html
            + " "
            + change_html
            + "</div>"
            "<p style='margin:2px 0;font-size:0.9rem;'>"
            "<strong>ID:</strong> <a href='"
            + url
            + "' target='_blank'>"
            + nct_id
            + "</a>"
            "&nbsp;|&nbsp; <strong>Sponsor:</strong> "
            + sponsor
            + enrollment_html
            + "</p>"
            + short_title_html
            + "<p style='margin:2px 0;font-size:0.9rem;'>"
            "<strong>Condition(s):</strong> "
            + conditions_str
            + "</p>"
            + interventions_html
            + who_utn_html
            + "</div>"
        )

        with st.expander("🔬 " + title, expanded=True):
            st.markdown(card_html, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if outcomes:
                    st.markdown("**Primary Outcome(s)**")
                    for outcome in outcomes:
                        st.markdown("- " + outcome)

            with col2:
                if locations:
                    st.markdown("**Locations**")
                    for location in locations[:5]:
                        st.markdown("- " + location)
                    if len(locations) > 5:
                        st.markdown(f"*...and {len(locations) - 5} more*")

            eligibility = trial.get("eligibility") or ""
            if eligibility:
                with st.expander("Eligibility Criteria", expanded=False):
                    st.markdown(eligibility)
