import requests
from typing import Dict, Any, Optional
from config import TWENTY_REST_URL, TWENTY_REST_TOKEN


if not TWENTY_REST_TOKEN:
    raise RuntimeError("TWENTY_REST_TOKEN is not set")


HEADERS = {
    "Authorization": f"Bearer {TWENTY_REST_TOKEN}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = "".join(c for c in str(phone) if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else None


def upsert_person_in_crm(lead: Dict[str, Any]) -> str:
    payload: Dict[str, Any] = {}

    # --------------------
    # NAME
    # --------------------
    first = str(lead.get("first_name", "")).strip()
    last = str(lead.get("last_name", "")).strip()

    if first or last:
        payload["name"] = {
            "firstName": first,
            "lastName": last,
        }

    # --------------------
    # EMAIL (REQUIRED)
    # --------------------
    email = lead.get("email")
    if not email:
        raise ValueError(f"Lead {lead.get('lead_id')} has no email")

    payload["emails"] = {
        "primaryEmail": email.strip().lower()
    }

    # --------------------
    # PHONE
    # --------------------
    phone = _normalize_phone(lead.get("phone"))
    if phone:
        payload["phones"] = {
            "primaryPhoneNumber": phone,
            "primaryPhoneCallingCode": "+1",
            "primaryPhoneCountryCode": "CA",
        }

    # --------------------
    # JOB TITLE
    # --------------------
    if lead.get("job_title"):
        payload["jobTitle"] = str(lead["job_title"]).strip()

    # --------------------
    # BUDGET (SAFE CONVERSION)
    # --------------------
    credit = lead.get("current_credit")
    try:
        payload["budget"] = float(credit)
    except (TypeError, ValueError):
        pass  # ignore non-numeric values safely

    # --------------------
    # UPSERT TO TWENTY
    # --------------------
    r = requests.post(
        f"{TWENTY_REST_URL}/people?upsert=true",
        headers=HEADERS,
        json=payload,
        timeout=(3, 10),
    )

    if not r.ok:
        raise RuntimeError(
            f"Twenty CRM error {r.status_code}: {r.text}"
        )

    data = r.json()

    # REST returns a list when return=representation
    if isinstance(data, list) and data and "id" in data[0]:
        return data[0]["id"]

    raise RuntimeError(f"Unexpected CRM response: {data}")
