"""
DATA MANAGER — the ONLY file that touches employees.json and detections.json directly.

Why this file exists:
Every other file (dashboard.py) will call the functions below instead of
opening JSON files itself. This way, if we ever switch to a real database
later, we only need to rewrite the INSIDE of these functions — nothing
in the dashboard will need to change.

Files used:
- employees.json  -> editable list of {person_id: {name, department}}
- detections.json -> written by test_pipeline.py (tracking + violations)
"""
import json
import os

# =========================================================
# PATHS — change here if your folder structure is different
# =========================================================

# BASE_DIR = the folder this file (data_manager.py) physically sits in,
# i.e. "SafeVisionAI - Airport". Using this instead of a plain relative
# path means the paths below work correctly NO MATTER which folder you
# run "streamlit run dashboard.py" from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# detections.json + screenshots live one folder up, inside "SafeVisionAI/output"
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "SafeVisionAI-detections", "output")
EMPLOYEES_FILE = os.path.join(OUTPUT_DIR, "employees.json")
DETECTIONS_FILE = os.path.join(OUTPUT_DIR, "detections.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# LOW-LEVEL HELPERS (private — other files should not call these directly)
# =========================================================

def _read_json(path, default):
    """Reads a JSON file. If it doesn't exist yet, returns `default` instead of crashing."""
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # file exists but is empty/corrupted -> treat as empty
            return default


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# =========================================================
# EMPLOYEES — the editable name/department list
# =========================================================

def load_employees():
    """
    Returns all employees as a dict:
    { "1": {"name": "Ali Khan", "department": "Security"}, ... }
    """
    return _read_json(EMPLOYEES_FILE, {})


def save_employee(person_id, name, department):
    """
    Adds a NEW employee or UPDATES an existing one (rename, change department).
    person_id is converted to string because JSON keys must be strings.
    """
    employees = load_employees()
    employees[str(person_id)] = {"name": name, "department": department}
    _write_json(EMPLOYEES_FILE, employees)


def delete_employee(person_id):
    """Removes an employee entry (does NOT delete their detection history)."""
    employees = load_employees()
    employees.pop(str(person_id), None)  # does nothing if id not found, no crash
    _write_json(EMPLOYEES_FILE, employees)


# =========================================================
# DETECTIONS — read-only from the dashboard's point of view
# (test_pipeline.py is the only thing that writes to this file)
# =========================================================

def load_detections():
    """Returns the raw detections.json content: {"people": {...}, "violations": [...]}"""
    return _read_json(DETECTIONS_FILE, {"people": {}, "violations": []})


def get_all_people_status():
    """
    Merges tracking data + employee info into one list, ready for a table.
    Returns a list of dicts, one per person, e.g.:
    [
      {"person_id": "1", "name": "Ali Khan", "department": "Security",
       "violating": True, "helmet": True, "vest": False, ...}
    ]
    person_id always appears only ONCE per person, because we loop over
    the "people" dict's keys, and dict keys can never repeat.
    """
    detections = load_detections()
    employees = load_employees()

    rows = []
    for person_id, status in detections.get("people", {}).items():
        employee_info = employees.get(person_id, {"name": "Unknown", "department": "Unassigned"})
        rows.append({
            "person_id": person_id,
            "name": employee_info.get("name", "Unknown"),
            "department": employee_info.get("department", "Unassigned"),
            **status,  # adds helmet, vest, boots, goggles, gloves, violating, last_seen_frame
        })
    return rows


def get_violations_for(person_id):
    """
    Returns every violation entry logged for one specific person_id,
    newest first. Used by the detail page.
    """
    detections = load_detections()
    person_id = str(person_id)
    matches = [v for v in detections.get("violations", []) if str(v["person_id"]) == person_id]
    return sorted(matches, key=lambda v: v["timestamp"], reverse=True)


def remove_violation(person_id, frame, timestamp, delete_screenshot=True):
    """
    Deletes one specific violation entry (e.g. a false positive) from
    detections.json, matched by person_id + frame + timestamp together
    (so we don't accidentally delete the wrong one).
    """
    detections = load_detections()
    violations = detections.get("violations", [])

    remaining = []
    for v in violations:
        is_match = (
            str(v["person_id"]) == str(person_id)
            and v["frame"] == frame
            and v["timestamp"] == timestamp
        )
        if is_match and delete_screenshot:
            screenshot_path = v.get("screenshot")
            if screenshot_path and os.path.exists(screenshot_path):
                os.remove(screenshot_path)
        if not is_match:
            remaining.append(v)

    detections["violations"] = remaining
    _write_json(DETECTIONS_FILE, detections)
