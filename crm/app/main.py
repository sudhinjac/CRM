# app/main.py
from fastapi import FastAPI, HTTPException, Query
from typing import Optional

from app.db import get_db_connection
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
    mark_lead_crm_synced,
)

app = FastAPI(title="Lead Intake & Task Orchestration API")

# -------------------------------------------------
# CREATE OR DEDUP LEAD
# -------------------------------------------------
@app.post("/leads")
def create_or_get_lead(payload: LeadCreate):
    existing_lead_id = find_existing_lead(
        phone=payload.phone,
        email=payload.email,
    )
    if existing_lead_id:
        return {"status": "existing", "lead_id": existing_lead_id}

    lead_id = create_lead(payload)
    return {"status": "created", "lead_id": lead_id}


# -------------------------------------------------
# SYNC UNSYNCED LEADS TO TWENTY CRM
# -------------------------------------------------
@app.post("/sync-crm")
def sync_all_leads_to_crm():
    synced, failed = [], []
    leads = get_unsynced_leads()

    for lead in leads:
        lead_id = lead["lead_id"]

        try:
            crm_person_id = upsert_person_in_crm(lead)
            mark_lead_crm_synced(lead_id, crm_person_id)
            synced.append(lead_id)

        except Exception as e:
            failed.append({
                "lead_id": lead_id,
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
# SEARCH LEADS
# -------------------------------------------------
@app.get("/leads/search")
def search_leads_api(
    phone: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
):
    return {
        "results": search_leads(
            phone=phone,
            email=email,
            name=name,
        )
    }


# -------------------------------------------------
# GET LEAD BY BUSINESS ID
# -------------------------------------------------
@app.get("/leads/{lead_id}")
def get_lead_details(lead_id: str):
    lead = get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# -------------------------------------------------
# LIST ALL LEADS
# -------------------------------------------------
@app.get("/leads")
def list_leads():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT lead_id, email, crm_synced
        FROM leads
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "lead_id": r[0],
            "email": r[1],
            "crm_synced": r[2],
        }
        for r in rows
    ]


# -------------------------------------------------
# AUTO-ASSIGN CRM TASKS
# -------------------------------------------------
@app.post("/tasks/auto-assign")
def auto_assign_tasks():
    members = get_workspace_members()
    people = get_people_without_open_tasks()

    created, failed = [], []

    for person in people:
        assignee = pick_member_with_lowest_load(members)

        try:
            task_id = create_task_for_person(person, assignee["id"])
            created.append({
                "task_id": task_id,
                "customer": f"{person['name']['firstName']} {person['name']['lastName']}",
                "assigned_to": assignee["userEmail"],
            })
        except Exception as e:
            failed.append({
                "customer": person["name"],
                "error": str(e),
            })

    return {
        "tasks_created": len(created),
        "tasks_failed": len(failed),
        "details": created + failed,
    }
