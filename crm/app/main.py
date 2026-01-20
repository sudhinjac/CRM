# app/main.py

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List

from app.schemas import LeadCreate
from app.crm import (
    upsert_person_in_crm,
    get_workspace_members,
    pick_member_with_lowest_load,
    get_people_without_open_tasks,
    create_task_for_person,
)
from app.models import (
    find_existing_lead,
    create_lead,
    get_unsynced_leads,
    search_leads,
    get_lead_by_id,
)

app = FastAPI(title="Lead Intake & Task Orchestration API")

# -------------------------------------------------
# LEADS
# -------------------------------------------------
@app.post("/leads")
def create_or_get_lead(payload: LeadCreate):
    existing_id = find_existing_lead(
        phone=payload.phone,
        email=payload.email,
    )

    if existing_id:
        return {"status": "existing", "lead_id": str(existing_id)}

    lead_id = create_lead(payload)
    return {"status": "created", "lead_id": str(lead_id)}


# -------------------------------------------------
# SYNC LEADS → CRM (NO DB COLUMN REQUIRED)
# -------------------------------------------------
@app.post("/sync-crm")
def sync_all_leads_to_crm():
    synced, failed = [], []

    leads = get_unsynced_leads()

    for lead in leads:
        try:
            upsert_person_in_crm(lead)
            synced.append(str(lead["id"]))
        except Exception as e:
            failed.append({
                "lead_id": str(lead["id"]),
                "error": str(e),
            })

    return {
        "total": len(leads),
        "synced_count": len(synced),
        "failed_count": len(failed),
        "synced": synced,
        "failed": failed,
    }


# -------------------------------------------------
# SEARCH
# -------------------------------------------------
@app.get("/leads/search")
def search_leads_api(
    phone: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
):
    results = search_leads(phone=phone, email=email, name=name)
    return {"count": len(results), "results": results}


# -------------------------------------------------
# DETAILS
# -------------------------------------------------
@app.get("/leads/{lead_id}")
def get_lead_details(lead_id: str):
    lead = get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# -------------------------------------------------
# AUTO TASK ASSIGNMENT
# -------------------------------------------------
@app.post("/tasks/auto-assign")
def auto_assign_tasks():
    members = get_workspace_members()
    if not members:
        raise HTTPException(status_code=500, detail="No workspace members found")

    people = get_people_without_open_tasks()

    created, failed = [], []

    for person in people:
        assignee = pick_member_with_lowest_load(members)

        try:
            task_id = create_task_for_person(
                person=person,
                assignee_id=assignee["id"],
            )
            created.append({
                "task_id": task_id,
                "customer": f"{person['name']['firstName']} {person['name']['lastName']}",
                "assigned_to": assignee["userEmail"],
            })
        except Exception as e:
            failed.append({
                "customer": f"{person['name']['firstName']} {person['name']['lastName']}",
                "error": str(e),
            })

    return {
        "tasks_created": len(created),
        "tasks_failed": len(failed),
        "details": created + failed,
    }
