import requests
import json
import os
from datetime import datetime, timezone

V2_API_URL = "https://clinicaltrials.gov/api/v2/studies/"
V1_API_URL = "https://clinicaltrials.gov/api/query/full_studies"

RESULTS_FILE = "clinical_trials_hybrid_fixed.json"

NCT_IDS = [
    "NCT05771155",
    "NCT06732804",
    "NCT06570772",
    "NCT06400719",
]


# ------------------ HELPERS ------------------

def load_previous_data():
    """Load previous JSON file if exists"""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def index_by_nct(data):
    """Convert list → dict for fast lookup"""
    return {item["nct_id"]: item for item in data}


IMPORTANT_FIELDS = [
    "status",
    "phase",
    "enrollment",
    "primary_completion_date",
    "completion_date",
    "outcomes",
    "interventions",
]


def is_different(new, old):
    """Compare key fields only"""
    for key in IMPORTANT_FIELDS:
        if new.get(key) != old.get(key):
            return True
    return False


# ------------------ V2 FETCH ------------------

def fetch_trial_v2(nct_id):
    url = f"{V2_API_URL}{nct_id}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    protocol = data.get("protocolSection", {})

    def safe_get(d, path, default=None):
        for key in path:
            if isinstance(d, dict):
                d = d.get(key, default)
            else:
                return default
        return d

    def get_list_of_names(items):
        if not items:
            return []
        if isinstance(items, list):
            return [i.get("name") for i in items if isinstance(i, dict)]
        return [str(items)]

    def get_outcomes(outcomes):
        if isinstance(outcomes, list):
            return [o.get("measure") for o in outcomes if isinstance(o, dict)]
        return [str(outcomes)] if outcomes else []

    def get_locations(locations):
        if not isinstance(locations, list):
            return []
        results = []
        for l in locations:
            fac = l.get("facility", {})
            if isinstance(fac, dict):
                parts = [
                    fac.get("name"),
                    fac.get("city"),
                    fac.get("country")
                ]
                results.append(", ".join(filter(None, parts)))
        return results

    return {
        "nct_id": nct_id,
        "brief_title": safe_get(protocol, ["identificationModule", "briefTitle"]),
        "official_title": safe_get(protocol, ["identificationModule", "officialTitle"]),
        "status": safe_get(protocol, ["statusModule", "overallStatus"]),
        "study_type": safe_get(protocol, ["designModule", "studyType"]),
        "phase": safe_get(protocol, ["designModule", "phases"]),
        "start_date": safe_get(protocol, ["statusModule", "startDateStruct", "startDate"]),
        "primary_completion_date": safe_get(protocol, ["statusModule", "primaryCompletionDateStruct", "primaryCompletionDate"]),
        "completion_date": safe_get(protocol, ["statusModule", "completionDateStruct", "completionDate"]),
        "enrollment": safe_get(protocol, ["designModule", "enrollmentInfo", "count"]),
        "conditions": safe_get(protocol, ["conditionsModule", "conditions"], []),
        "interventions": get_list_of_names(safe_get(protocol, ["armsInterventionsModule", "interventions"])),
        "outcomes": get_outcomes(safe_get(protocol, ["outcomesModule", "primaryOutcomes"])),
        "eligibility": safe_get(protocol, ["eligibilityModule", "eligibilityCriteria"]),
        "ages": safe_get(protocol, ["eligibilityModule", "minimumAge"]),
        "sexes": safe_get(protocol, ["eligibilityModule", "sex"]),
        "locations": get_locations(safe_get(protocol, ["contactsLocationsModule", "locations"])),
        "sponsor": safe_get(protocol, ["sponsorCollaboratorsModule", "leadSponsor", "name"]),
        "collaborators": get_list_of_names(safe_get(protocol, ["sponsorCollaboratorsModule", "collaborators"])),
        "last_update_posted": safe_get(protocol, ["statusModule", "lastUpdatePostDateStruct", "lastUpdatePostDate"]),
        "_api_version": "v2"
    }


# ------------------ V1 FALLBACK ------------------

def fetch_trial_v1(nct_id):
    params = {"expr": nct_id, "min_rnk": 1, "max_rnk": 1, "fmt": "json"}
    r = requests.get(V1_API_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    studies = data.get("FullStudiesResponse", {}).get("FullStudies", [])
    if not studies:
        print(f"⚠️ No data found for {nct_id}")
        return None

    study = studies[0]["Study"]
    protocol = study["ProtocolSection"]

    def flatten_interventions(interventions):
        if not interventions:
            return []
        return [f"{i.get('InterventionType','')} - {i.get('InterventionName','')}" for i in interventions]

    def flatten_outcomes(outcomes):
        if not outcomes:
            return []
        return [f"{o.get('Measure','')} ({o.get('TimeFrame','')})" for o in outcomes]

    def flatten_locations(locations):
        if not locations:
            return []
        return [", ".join(filter(None, [
            l.get("Facility", {}).get("Name"),
            l.get("Facility", {}).get("Address", {}).get("City"),
            l.get("Facility", {}).get("Address", {}).get("Country")
        ])) for l in locations]

    def flatten_collaborators(collabs):
        if not collabs:
            return []
        return [c.get("CollaboratorName") for c in collabs]

    return {
        "nct_id": nct_id,
        "brief_title": protocol.get("IdentificationModule", {}).get("BriefTitle"),
        "official_title": protocol.get("IdentificationModule", {}).get("OfficialTitle"),
        "status": protocol.get("StatusModule", {}).get("OverallStatus"),
        "study_type": protocol.get("DesignModule", {}).get("StudyType"),
        "phase": protocol.get("DesignModule", {}).get("PhaseList", {}).get("Phase"),
        "start_date": protocol.get("StatusModule", {}).get("StartDateStruct", {}).get("StartDate"),
        "primary_completion_date": protocol.get("StatusModule", {}).get("PrimaryCompletionDateStruct", {}).get("PrimaryCompletionDate"),
        "completion_date": protocol.get("StatusModule", {}).get("CompletionDateStruct", {}).get("CompletionDate"),
        "enrollment": protocol.get("DesignModule", {}).get("EnrollmentInfo", {}).get("EnrollmentCount"),
        "conditions": protocol.get("ConditionsModule", {}).get("ConditionList", {}).get("Condition", []),
        "interventions": flatten_interventions(protocol.get("ArmsInterventionsModule", {}).get("InterventionList", {}).get("Intervention", [])),
        "outcomes": flatten_outcomes(protocol.get("OutcomesModule", {}).get("PrimaryOutcomeList", {}).get("PrimaryOutcome", [])),
        "eligibility": protocol.get("EligibilityModule", {}).get("EligibilityCriteria"),
        "ages": protocol.get("EligibilityModule", {}).get("MinimumAge"),
        "sexes": protocol.get("EligibilityModule", {}).get("Gender"),
        "locations": flatten_locations(protocol.get("ContactsLocationsModule", {}).get("LocationList", {}).get("Location", [])),
        "sponsor": protocol.get("SponsorCollaboratorsModule", {}).get("LeadSponsor", {}).get("LeadSponsorName"),
        "collaborators": flatten_collaborators(protocol.get("SponsorCollaboratorsModule", {}).get("CollaboratorList", {}).get("Collaborator", [])),
        "last_update_posted": protocol.get("StatusModule", {}).get("LastUpdatePostDateStruct", {}).get("LastUpdatePostDate"),
        "_api_version": "v1"
    }


# ------------------ FETCH WRAPPER ------------------

def fetch_trial(nct_id):
    try:
        trial = fetch_trial_v2(nct_id)
        print(f"✅ {nct_id} fetched via v2 API")
        return trial
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"🔄 Falling back to v1 API for {nct_id}")
            return fetch_trial_v1(nct_id)
        else:
            print(f"❌ HTTP error for {nct_id}: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error for {nct_id}: {e}")
    return None


# ------------------ MAIN ------------------

if __name__ == "__main__":
    previous_data = load_previous_data()
    previous_index = index_by_nct(previous_data)

    results = []

    for nct in NCT_IDS:
        trial = fetch_trial(nct)
        if not trial:
            continue

        old_trial = previous_index.get(nct)

        if not old_trial:
            trial["change_status"] = "new"
        else:
            if is_different(trial, old_trial):
                trial["change_status"] = "updated"
            else:
                trial["change_status"] = "unchanged"

        trial["last_checked"] = datetime.now(timezone.utc).isoformat()

        results.append(trial)

    if results:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Saved {len(results)} trials with change tracking")
    else:
        print("\n⚠️ No data saved")