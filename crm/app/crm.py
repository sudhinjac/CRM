import requests
import random
from typing import Dict, Any, List

from app.config import TWENTY_REST_URL, TWENTY_REST_TOKEN
from app.llm import generate_sales_followup_markdown

# No os.getenv here. Config already validated.
HEADERS = {
    "Authorization": f"Bearer {TWENTY_REST_TOKEN}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}

if not TWENTY_REST_TOKEN:
    raise RuntimeError("TWENTY_REST_TOKEN not set")

#HEADERS = {
 #   "Authorization": f"Bearer {TWENTY_REST_TOKEN}",
 #   "Content-Type": "application/json",
#}

#
# -------------------------------------------------
# PEOPLE UPSERT
# -------------------------------------------------
def upsert_person_in_crm(lead: Dict[str, Any]) -> str:
    email = lead.get("email")
    if not email:
        raise ValueError("Email is required for CRM sync")

    payload = {
        "name": {
            "firstName": str(lead.get("first_name", "")).strip(),
            "lastName": str(lead.get("last_name", "")).strip(),
        },
        "emails": {
            "primaryEmail": email.lower()
        },
    }

    if lead.get("job_title"):
        payload["jobTitle"] = str(lead["job_title"]).strip()

    if lead.get("current_credit") is not None:
        try:
            payload["budget"] = float(lead["current_credit"])
        except (TypeError, ValueError):
            pass

    # 1️⃣ UPSERT
    r = requests.post(
        f"{TWENTY_REST_URL}/people?upsert=true",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    if not r.ok:
        raise RuntimeError(f"CRM upsert failed: {r.text}")

    # 2️⃣ ALWAYS FETCH PERSON BY EMAIL (SOURCE OF TRUTH)
    lookup = requests.get(
        f"{TWENTY_REST_URL}/people",
        headers=HEADERS,
        params={
            "filter[emails.primaryEmail]": email.lower()
        },
        timeout=10,
    )

    if not lookup.ok:
        raise RuntimeError(f"CRM lookup failed: {lookup.text}")

    people = lookup.json().get("data", {}).get("people", [])

    if not people:
        raise RuntimeError("CRM person not found after upsert")

    return people[0]["id"]

# -------------------------------------------------
# WORKSPACE MEMBERS
# -------------------------------------------------
def get_workspace_members() -> List[Dict[str, Any]]:
    r = requests.get(
        f"{TWENTY_REST_URL}/workspaceMembers",
        headers=HEADERS,
        timeout=10,
    )
    if not r.ok:
        raise RuntimeError(r.text)
    return r.json()["data"]["workspaceMembers"]


# -------------------------------------------------
# TASK LOAD
# -------------------------------------------------
def get_open_task_count(member_id: str) -> int:
    r = requests.get(
        f"{TWENTY_REST_URL}/tasks",
        headers=HEADERS,
        params={
            "filter[assigneeId]": member_id,
            "filter[status]": "TODO",
        },
        timeout=10,
    )
    return r.json().get("totalCount", 0)


def pick_member_with_lowest_load(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    loads = [(m, get_open_task_count(m["id"])) for m in members]
    min_load = min(c for _, c in loads)
    return random.choice([m for m, c in loads if c == min_load])


# -------------------------------------------------
# PEOPLE WITHOUT TODO TASKS
# -------------------------------------------------
def get_people_without_open_tasks() -> List[Dict[str, Any]]:
    r_people = requests.get(
        f"{TWENTY_REST_URL}/people",
        headers=HEADERS,
        timeout=10,
    )
    people = r_people.json()["data"]["people"]

    r_tasks = requests.get(
        f"{TWENTY_REST_URL}/tasks",
        headers=HEADERS,
        params={"filter[status]": "TODO"},
        timeout=10,
    )
    tasks = r_tasks.json()["data"]["tasks"]
    existing_titles = {t["title"] for t in tasks}

    eligible = []
    for p in people:
        name = f"{p['name']['firstName']} {p['name']['lastName']}"
        title = f"📞 Sales Follow-up — {name}"
        if title not in existing_titles:
            eligible.append(p)

    return eligible


# -------------------------------------------------
# CREATE TASK
# -------------------------------------------------
def create_task_for_person(person: Dict[str, Any], assignee_id: str) -> str:
    full_name = f"{person['name']['firstName']} {person['name']['lastName']}"
    markdown_body = generate_sales_followup_markdown(person)
    payload = {
        "title": f"📞 Sales Follow-up — {full_name}",
        "status": "TODO",
        "assigneeId": assignee_id,
        "bodyV2": {
            "markdown": markdown_body,
        },
    }

    r = requests.post(
        f"{TWENTY_REST_URL}/tasks",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    if not r.ok:
        raise RuntimeError(f"Task creation failed: {r.text}")

    task = r.json()

    # ✅ REST response → task is top-level
    if "id" not in task:
        raise RuntimeError(f"Unexpected task response: {task}")

    return task["id"]
