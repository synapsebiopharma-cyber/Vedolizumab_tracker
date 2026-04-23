import requests
import json
import os
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE     = "https://euclinicaltrials.eu/ctis-public-api/retrieve"
RESULTS_FILE = "clinical_trials_eu.json"

EU_TRIAL_IDS = [
    "2022-502778-18-00",
    "2025-522534-31-00",
]

# Manually maintained — add sponsor for each trial ID here
SPONSOR_OVERRIDES = {
    "2022-502778-18-00": "Polpharma Biologics S.A.",
    "2025-522534-31-00": "Polpharma Biologics S.A.",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

IMPORTANT_FIELDS = [
    "status",
    "phase",
    "enrollment",
    "primary_completion_date",
    "completion_date",
    "outcomes",
    "interventions",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_previous_data():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def index_by_id(data):
    return {item["nct_id"]: item for item in data}


def is_different(new, old):
    for key in IMPORTANT_FIELDS:
        if new.get(key) != old.get(key):
            return True
    return False


def safe_get(d, *path, default=None):
    for key in path:
        if isinstance(d, dict):
            d = d.get(key, default)
        elif isinstance(d, list) and isinstance(key, int):
            d = d[key] if key < len(d) else default
        else:
            return default
        if d is None:
            return default
    return d


# ── Phase mapping ─────────────────────────────────────────────────────────────
PHASE_MAP = {
    "1": ["PHASE1"],
    "2": ["PHASE2"],
    "3": ["PHASE3"],
    "4": ["PHASE4"],
    "5": ["PHASE3"],        # CTIS "5" = Phase III equivalent
    "6": ["PHASE1", "PHASE2"],
    "7": ["PHASE2", "PHASE3"],
}

# ── Status mapping ────────────────────────────────────────────────────────────
STATUS_MAP = {
    "Authorised":         "AUTHORIZED",
    "Ended":              "COMPLETED",
    "Ongoing":            "RECRUITING",
    "Withdrawn":          "WITHDRAWN",
    "Suspended":          "SUSPENDED",
    "Not Authorised":     "NOT_AUTHORIZED",
    "Temporarily Halted": "SUSPENDED",
}

# ── Core parser ───────────────────────────────────────────────────────────────

def parse_eu_trial(data: dict, trial_id: str) -> dict:
    auth                = safe_get(data, "authorizedApplication", default={})
    part1               = safe_get(auth, "authorizedPartI", default={})
    details             = safe_get(part1, "trialDetails", default={})
    identifiers         = safe_get(details, "clinicalTrialIdentifiers", default={})
    trial_info          = safe_get(details, "trialInformation", default={})
    eligibility_section = safe_get(details, "eligibilityCriteria", default={})

    # ── Titles ────────────────────────────────────────────────────────────────
    brief_title    = safe_get(identifiers, "publicTitle")
    official_title = safe_get(identifiers, "fullTitle")
    short_title    = safe_get(identifiers, "shortTitle")

    # ── Status ────────────────────────────────────────────────────────────────
    raw_status = data.get("ctStatus", "")
    status = STATUS_MAP.get(raw_status, raw_status.upper().replace(" ", "_") if raw_status else None)

    # ── Phase ─────────────────────────────────────────────────────────────────
    trial_category = safe_get(trial_info, "trialCategory", default={})
    phase_code     = str(safe_get(trial_category, "trialPhase", default=""))
    phase          = PHASE_MAP.get(phase_code, [f"PHASE_{phase_code}"] if phase_code else None)

    # ── Dates ─────────────────────────────────────────────────────────────────
    start_date              = data.get("startDateEU")   # already YYYY-MM-DD
    completion_date         = data.get("endDateEU")
    primary_completion_date = completion_date           # CTIS doesn't separate these

    # ── Enrollment ────────────────────────────────────────────────────────────
    enrollment = safe_get(part1, "rowSubjectCount")
    if enrollment is not None:
        try:
            enrollment = int(enrollment)
        except (ValueError, TypeError):
            enrollment = None

    # ── Conditions ────────────────────────────────────────────────────────────
    medical_cond = safe_get(trial_info, "medicalCondition", "partIMedicalConditions", default=[])
    conditions = [
        c.get("medicalCondition")
        for c in medical_cond
        if isinstance(c, dict) and c.get("medicalCondition")
    ]

    # ── Interventions (products) ──────────────────────────────────────────────
    products      = safe_get(part1, "products", default=[])
    interventions = []
    for p in products:
        name   = safe_get(p, "productDictionaryInfo", "prodName") or safe_get(p, "productName")
        active = safe_get(p, "productDictionaryInfo", "activeSubstanceName")
        route  = safe_get(p, "routes", 0)
        parts  = [x for x in [name, active, route] if x]
        if parts:
            interventions.append(" | ".join(parts))

    # ── Outcomes ─────────────────────────────────────────────────────────────
    main_obj       = safe_get(trial_info, "trialObjective", "mainObjective")
    secondary_objs = safe_get(trial_info, "trialObjective", "secondaryObjectives", default=[])
    outcomes = []
    if main_obj:
        outcomes.append(main_obj)
    for obj in secondary_objs:
        text = obj.get("secondaryObjective") if isinstance(obj, dict) else None
        if text:
            outcomes.append(text)

    # ── Eligibility ───────────────────────────────────────────────────────────
    inclusion_items = safe_get(eligibility_section, "principalInclusionCriteria", default=[])
    exclusion_items = safe_get(eligibility_section, "principalExclusionCriteria", default=[])

    inclusion_text = "\n".join(
        c.get("principalInclusionCriteria", "")
        for c in inclusion_items if isinstance(c, dict)
    )
    exclusion_text = "\n".join(
        c.get("principalExclusionCriteria", "")
        for c in exclusion_items if isinstance(c, dict)
    )

    parts = []
    if inclusion_text.strip():
        parts.append("Inclusion Criteria:\n" + inclusion_text.strip())
    if exclusion_text.strip():
        parts.append("Exclusion Criteria:\n" + exclusion_text.strip())
    eligibility = "\n\n".join(parts) if parts else None

    # ── Ages / sex (not directly available in API) ────────────────────────────
    ages  = None
    sexes = None

    # ── Locations (countries) ─────────────────────────────────────────────────
    countries = safe_get(part1, "rowCountriesInfo", default=[])
    locations = [c.get("name") for c in countries if isinstance(c, dict) and c.get("name")]

    # ── Last update ────────────────────────────────────────────────────────────
    last_update_posted = (data.get("publishDate") or "")[:10] or None

    # ── Study type ─────────────────────────────────────────────────────────────
    cat_code     = safe_get(trial_category, "trialCategory")
    CATEGORY_MAP = {"1": "INTERVENTIONAL", "2": "INTERVENTIONAL", "3": "OBSERVATIONAL"}
    study_type   = CATEGORY_MAP.get(str(cat_code), "INTERVENTIONAL")

    # ── Secondary IDs ──────────────────────────────────────────────────────────
    who_utn = safe_get(identifiers, "secondaryIdentifyingNumbers", "whoUniversalTrialNumber", "number")

    return {
        "nct_id":                  trial_id,
        "eu_ct_number":            data.get("ctNumber", trial_id),
        "registry":                "EU_CTIS",
        "brief_title":             brief_title,
        "official_title":          official_title,
        "short_title":             short_title,
        "status":                  status,
        "study_type":              study_type,
        "phase":                   phase,
        "start_date":              start_date,
        "primary_completion_date": primary_completion_date,
        "completion_date":         completion_date,
        "enrollment":              enrollment,
        "conditions":              conditions,
        "interventions":           interventions,
        "outcomes":                outcomes,
        "eligibility":             eligibility,
        "ages":                    ages,
        "sexes":                   sexes,
        "locations":               locations,
        "sponsor":                 None,   # set from SPONSOR_OVERRIDES in fetch_eu_trial
        "collaborators":           [],
        "who_utn":                 who_utn,
        "last_update_posted":      last_update_posted,
        "_api_version":            "eu_ctis_v1",
    }


# ── Fetch wrapper ─────────────────────────────────────────────────────────────

def fetch_eu_trial(trial_id: str) -> dict | None:
    url = f"{API_BASE}/{trial_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        trial = parse_eu_trial(r.json(), trial_id)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error for {trial_id}: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error for {trial_id}: {e}")
        return None

    # Apply manual sponsor override
    trial["sponsor"] = SPONSOR_OVERRIDES.get(trial_id)

    print(f"✅ {trial_id} fetched | Sponsor: {trial['sponsor'] or 'NOT SET'}")
    return trial


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_eu_ctis_trials() -> list[dict]:
    """Fetch all EU CTIS trials, track changes, persist to disk, and return results."""
    previous_data  = load_previous_data()
    previous_index = index_by_id(previous_data)

    results = []

    for trial_id in EU_TRIAL_IDS:
        trial = fetch_eu_trial(trial_id)
        if not trial:
            continue

        old_trial = previous_index.get(trial_id)

        if not old_trial:
            trial["change_status"] = "new"
        elif is_different(trial, old_trial):
            trial["change_status"] = "updated"
        else:
            trial["change_status"] = "unchanged"

        trial["last_checked"] = datetime.now(timezone.utc).isoformat()
        results.append(trial)

    if results:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved {len(results)} EU trial(s) with change tracking → {RESULTS_FILE}")
    else:
        print("\n⚠️ No data saved")

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fetch_eu_ctis_trials()