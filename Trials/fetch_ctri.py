import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────

RESULTS_FILE = "clinical_trials_ctri.json"

# Add as many CTRI URLs / IDs as needed.
# Each entry can be a full URL or just the EncHid value.
CTRI_ENTRIES = [
    {
        "ctri_id": "CTRI/2024/05/067203",
        "url": "https://ctri.nic.in/Clinicaltrials/pmaindet2.php?EncHid=MTAzMjUy&Enc=&userName="
    },
    {
        "ctri_id": "CTRI/2025/02/080437",
        "url": "https://ctri.nic.in/Clinicaltrials/pmaindet2.php?EncHid=MTE2ODY2&Enc=&userName="
    },
    {
        "ctri_id": "CTRI/2026/01/100705",
        "url": "https://ctri.nic.in/Clinicaltrials/pmaindet2.php?EncHid=MTQ1NTc3&Enc=&userName="
    },
    {
        "ctri_id": "CTRI/2023/10/058307",
        "url": "https://ctri.nic.in/Clinicaltrials/pmaindet2.php?EncHid=OTA2MTU=&Enc=&userName="
    },
    # Add more trials here:
    # {"ctri_id": "CTRI/...", "url": "https://ctri.nic.in/..."},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
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

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_previous_data():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def index_by_id(data, key="nct_id"):
    return {item[key]: item for item in data if key in item}


def is_different(new, old):
    for key in IMPORTANT_FIELDS:
        if new.get(key) != old.get(key):
            return True
    return False


def clean(text: str) -> str:
    """Strip extra whitespace and common encoding artifacts."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("â€™", "'").replace("â€", "–")
    text = text.replace("Â®", "®").replace("Î»", "λ").replace("âˆž", "∞")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_date(raw: str) -> str:
    """Normalise DD/MM/YYYY → YYYY-MM-DD; pass through anything else."""
    raw = clean(raw)
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return raw or None


def row_text(row) -> str:
    return clean(row.get_text(" ", strip=True))


# ── Core Parser ───────────────────────────────────────────────────────────────

def parse_ctri_html(html: str, ctri_id: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # Build a label→cell map from every <tr> that has exactly 2 <td> children
    label_map: dict[str, str] = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).rstrip(":").lower()
            value = clean(cells[1].get_text(" ", strip=True))
            if label:
                label_map[label] = value

    def get(key_fragment: str, default=None):
        """Case-insensitive substring search over label_map keys."""
        for k, v in label_map.items():
            if key_fragment.lower() in k:
                return v
        return default

    # ── Title / ID ──────────────────────────────────────────────────────────
    brief_title   = get("public title")
    official_title = get("scientific title")

    # ── Status ──────────────────────────────────────────────────────────────
    recruitment_india = get("recruitment status of trial (india)", "")
    recruitment_global = get("recruitment status of trial (global)", "")
    raw_status = recruitment_india or recruitment_global or ""
    STATUS_MAP = {
        "completed":          "COMPLETED",
        "recruiting":         "RECRUITING",
        "not yet recruiting": "NOT_YET_RECRUITING",
        "active":             "ACTIVE_NOT_RECRUITING",
        "terminated":         "TERMINATED",
        "suspended":          "SUSPENDED",
        "withdrawn":          "WITHDRAWN",
        "not applicable":     "NOT_APPLICABLE",
    }
    status = STATUS_MAP.get(raw_status.lower(), raw_status.upper() or None)

    # ── Phase ────────────────────────────────────────────────────────────────
    phase_raw = get("phase of trial", "")
    phases = []
    for p in re.findall(r"phase\s*(\d+)", phase_raw, re.IGNORECASE):
        phases.append(f"PHASE{p}")
    phase = phases if phases else ([phase_raw] if phase_raw else None)

    # ── Enrollment ───────────────────────────────────────────────────────────
    sample_size_raw = get("target sample size", "")
    enrollment = None
    m = re.search(r'total sample size\s*=\s*["\']?(\d+)', sample_size_raw, re.IGNORECASE)
    if m:
        enrollment = int(m.group(1))

    # ── Dates ────────────────────────────────────────────────────────────────
    start_date               = parse_date(get("date of first enrollment (india)", ""))
    completion_date          = parse_date(get("date of study completion (india)", ""))
    primary_completion_date  = completion_date  # CTRI does not separate these

    # ── Conditions ───────────────────────────────────────────────────────────
    conditions_raw = get("health condition", "")
    conditions_cell = None
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "health condition" in label:
                conditions_cell = cells[1]
                break
    if conditions_cell:
        inner_rows = conditions_cell.find_all("tr")
        conditions = list({
            clean(r.find_all("td")[-1].get_text(" ", strip=True))
            for r in inner_rows
            if len(r.find_all("td")) >= 2
               and clean(r.find_all("td")[-1].get_text()).lower()
               not in ("condition", "health type", "")
        })
    else:
        conditions = [conditions_raw] if conditions_raw else []

    # ── Interventions ─────────────────────────────────────────────────────
    interventions = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "intervention" in label and "comparator" in label:
                inner_rows = cells[1].find_all("tr")
                for row in inner_rows:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        itype = clean(tds[0].get_text())
                        iname = clean(tds[1].get_text()) if len(tds) > 1 else ""
                        if iname and iname.lower() not in ("type", "name", "details"):
                            interventions.append(iname)
                break

    # ── Outcomes ─────────────────────────────────────────────────────────────
    outcomes = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "primary outcome" in label:
                inner_rows = cells[1].find_all("tr")
                for row in inner_rows:
                    tds = row.find_all("td")
                    if tds:
                        text = clean(tds[0].get_text())
                        if text and text.lower() not in ("outcome", "timepoints"):
                            outcomes.append(text)
                break

    # ── Eligibility ───────────────────────────────────────────────────────────
    inclusion_raw = ""
    exclusion_raw = ""
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "inclusion criteria" in label:
                inclusion_raw = clean(cells[1].get_text("\n", strip=True))
            elif "exclusion" in label:
                exclusion_raw = clean(cells[1].get_text("\n", strip=True))

    eligibility = None
    parts = []
    if inclusion_raw:
        parts.append("Inclusion Criteria:\n" + inclusion_raw)
    if exclusion_raw:
        parts.append("Exclusion Criteria:\n" + exclusion_raw)
    if parts:
        eligibility = "\n\n".join(parts)

    # ── Age / Sex ─────────────────────────────────────────────────────────────
    ages = None
    sexes = None
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "inclusion criteria" in label:
                inner = cells[1]
                for row in inner.find_all("tr"):
                    tds = row.find_all("td")
                    if len(tds) == 2:
                        sub_label = clean(tds[0].get_text()).lower()
                        sub_val   = clean(tds[1].get_text())
                        if "age from" in sub_label:
                            ages = sub_val
                        elif "gender" in sub_label:
                            sexes = sub_val
                break

    # ── Sponsor / Collaborators ───────────────────────────────────────────────
    sponsor = None
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "primary sponsor" in label:
                inner_rows = cells[1].find_all("tr")
                for row in inner_rows:
                    tds = row.find_all("td")
                    if len(tds) == 2 and "name" in clean(tds[0].get_text()).lower():
                        sponsor = clean(tds[1].get_text())
                        break
                break

    collab_raw = get("details of secondary sponsor", "")
    collaborators = [c.strip() for c in collab_raw.split("\n") if c.strip() and c.strip().upper() != "NIL"]

    # ── Locations ─────────────────────────────────────────────────────────────
    locations = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) == 2:
            label = clean(cells[0].get_text(" ", strip=True)).lower()
            if "sites of study" in label:
                inner_rows = cells[1].find_all("tr")
                for row in inner_rows:
                    tds = row.find_all("td")
                    if len(tds) >= 3:
                        site_name = clean(tds[1].get_text())
                        site_addr = clean(tds[2].get_text())
                        if site_name and site_name.lower() not in ("name of site",):
                            addr_parts = [p.strip() for p in site_addr.split("\n") if p.strip()]
                            loc = site_name
                            if addr_parts:
                                loc += ", " + addr_parts[-1]
                            locations.append(loc)
                break

    # ── Last update ───────────────────────────────────────────────────────────
    last_update_posted = parse_date(get("last modified on", ""))

    # ── Study type / design ───────────────────────────────────────────────────
    study_type = get("type of trial", None)
    study_design = get("study design", None)

    # ── Assemble normalised record ────────────────────────────────────────────
    return {
        "nct_id":                 ctri_id,
        "ctri_id":                ctri_id,
        "registry":               "CTRI",
        "brief_title":            brief_title,
        "official_title":         official_title,
        "status":                 status,
        "study_type":             study_type,
        "study_design":           study_design,
        "phase":                  phase,
        "start_date":             start_date,
        "primary_completion_date": primary_completion_date,
        "completion_date":        completion_date,
        "enrollment":             enrollment,
        "conditions":             conditions,
        "interventions":          interventions,
        "outcomes":               outcomes,
        "eligibility":            eligibility,
        "ages":                   ages,
        "sexes":                  sexes,
        "locations":              locations,
        "sponsor":                sponsor,
        "collaborators":          collaborators,
        "last_update_posted":     last_update_posted,
        "_api_version":           "ctri_html",
    }


# ── Fetch + Parse ─────────────────────────────────────────────────────────────

def fetch_ctri_trial(entry: dict) -> dict | None:
    """Fetch and parse a single CTRI trial entry. Returns None on failure."""
    ctri_id = entry["ctri_id"]
    url     = entry["url"]
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        trial = parse_ctri_html(r.text, ctri_id)
        print(f"✅ {ctri_id} scraped from CTRI")
        return trial
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error for {ctri_id}: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error for {ctri_id}: {e}")
    return None


# ── Public API (imported by main.py) ─────────────────────────────────────────

def fetch_ctri_trials() -> list[dict]:
    """
    Fetch all CTRI trials defined in CTRI_ENTRIES, apply change tracking
    against the previous saved file, and return the results list.
    Called by main.py's run_ctri_trials().
    """
    previous_data  = load_previous_data()
    previous_index = index_by_id(previous_data, key="nct_id")

    results = []
    for entry in CTRI_ENTRIES:
        trial = fetch_ctri_trial(entry)
        if not trial:
            continue

        ctri_id   = trial["nct_id"]
        old_trial = previous_index.get(ctri_id)

        if not old_trial:
            trial["change_status"] = "new"
        elif is_different(trial, old_trial):
            trial["change_status"] = "updated"
        else:
            trial["change_status"] = "unchanged"

        trial["last_checked"] = datetime.now(timezone.utc).isoformat()
        results.append(trial)

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = fetch_ctri_trials()

    if results:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved {len(results)} CTRI trial(s) with change tracking → {RESULTS_FILE}")
    else:
        print("\n⚠️ No data saved")