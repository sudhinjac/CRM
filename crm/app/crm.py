# app/crm.py

import os
import requests
import random
from typing import Dict, Any, Optional, List

TWENTY_REST_URL = os.getenv("TWENTY_REST_URL", "http://localhost:3000/rest")
TWENTY_API_TOKEN = os.getenv("TWENTY_API_TOKEN")

if not TWENTY_API_TOKEN:
    raise RuntimeError("TWENTY_API_TOKEN not set")

HEADERS = {
    "Authorization": f"Bearer {TWENTY_API_TOKEN}",
    "Content-Type": "application/json",
}

# -------------------------------------------------
# PEOPLE UPSERT
# -------------------------------------------------
def upsert_person_in_crm(lead: Dict[str, Any]) -> str:
    email = lead.get("email")
    if not email:
        raise ValueError("Email is required for CRM sync")

    payload: Dict[str, Any] = {
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

    r = requests.post(
        f"{TWENTY_REST_URL}/people?upsert=true",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    if not r.ok:
        raise RuntimeError(f"CRM error {r.status_code}: {r.text}")

    data = r.json()
    if isinstance(data, list) and data:
        return data[0]["id"]

    raise RuntimeError("Failed to resolve CRM person ID")


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
# TASK LOAD BALANCING
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
    if not r.ok:
        return 0
    return r.json().get("totalCount", 0)


def pick_member_with_lowest_load(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    loads = [(m, get_open_task_count(m["id"])) for m in members]
    min_load = min(count for _, count in loads)
    candidates = [m for m, count in loads if count == min_load]
    return random.choice(candidates)


# -------------------------------------------------
# FIND PEOPLE WITHOUT TODO TASKS
# (TITLE-BASED — RELIABLE)
# -------------------------------------------------
def get_people_without_open_tasks() -> List[Dict[str, Any]]:
    # Fetch all people
    r_people = requests.get(
        f"{TWENTY_REST_URL}/people",
        headers=HEADERS,
        timeout=10,
    )
    if not r_people.ok:
        raise RuntimeError(r_people.text)

    people = r_people.json()["data"]["people"]

    # Fetch all open tasks once
    r_tasks = requests.get(
        f"{TWENTY_REST_URL}/tasks",
        headers=HEADERS,
        params={"filter[status]": "TODO"},
        timeout=10,
    )
    if not r_tasks.ok:
        raise RuntimeError(r_tasks.text)

    tasks = r_tasks.json()["data"]["tasks"]
    task_titles = {t["title"] for t in tasks}

    eligible: List[Dict[str, Any]] = []

    for p in people:
        full_name = f"{p['name']['firstName']} {p['name']['lastName']}"
        expected_title = f"📞 Sales Follow-up — {full_name}"

        if expected_title not in task_titles:
            eligible.append(p)

    return eligible


# -------------------------------------------------
# CREATE TASK (LOUD & CLEAR)
# -------------------------------------------------
def create_task_for_person(person: Dict[str, Any], assignee_id: str) -> str:
    full_name = f"{person['name']['firstName']} {person['name']['lastName']}"

    payload = {
        "title": f"📞 Sales Follow-up — {full_name}",
        "status": "TODO",
        "assigneeId": assignee_id,
        "bodyV2": {
            "markdown": f"""
## 🔥 CUSTOMER FOLLOW-UP REQUIRED

### 👤 Customer
**Name:** {full_name}  
**Email:** {person['emails']['primaryEmail']}  
**City:** {person.get('city', '')}

---

### 📌 ACTION ITEMS
- 📞 Call the customer
- 💬 Understand requirements
- 💰 Confirm budget
- 📝 Update CRM after call

---

### ⏱ PRIORITY
🚨 **HIGH — DO TODAY**
"""
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

    return r.json()["data"]["task"]["id"]
