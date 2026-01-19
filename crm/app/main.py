# app/main.py
from fastapi import FastAPI, HTTPException
from app.schemas import LeadCreate
from app.models import find_existing_lead, create_lead
from app.crm import create_person_in_crm
from fastapi import HTTPException
from fastapi import FastAPI
from app.models import get_unsynced_leads, update_crm_person_id
from app.crm import find_person_in_crm, create_person_in_crm
from app.models import get_unsynced_leads, update_crm_person_id



app = FastAPI(title="Lead Intake API")

@app.post("/leads")
def create_or_get_lead(payload: LeadCreate):
    existing_id = find_existing_lead(
        payload.phone_number,
        payload.email
    )

    if existing_id:
        return {
            "status": "existing",
            "lead_id": existing_id
        }

    lead_id = create_lead(payload)

    return {
        "status": "created",
        "lead_id": lead_id
    }
    
@app.post("/sync-crm")
def sync_all_leads_to_crm():
    synced = []
    linked_existing = []

    leads = get_unsynced_leads()

    for lead in leads:
        crm_id = find_person_in_crm(
            email=lead["email"],
            phone=lead["phone_number"]
        )

        if not crm_id:
            crm_id = create_person_in_crm(lead)
            synced.append(lead["id"])
        else:
            linked_existing.append(lead["id"])

        update_crm_person_id(lead["id"], crm_id)

    return {
        "created_in_crm": synced,
        "linked_existing": linked_existing
    }
