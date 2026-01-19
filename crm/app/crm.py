import os
import requests
from typing import Optional

TWENTY_API_URL = os.getenv("TWENTY_API_URL")  # http://localhost:3000/graphql
TWENTY_API_TOKEN = os.getenv("TWENTY_API_TOKEN")

if not TWENTY_API_URL or not TWENTY_API_TOKEN:
    raise RuntimeError("TWENTY_API_URL or TWENTY_API_TOKEN not set")

HEADERS = {
    "Authorization": f"Bearer {TWENTY_API_TOKEN}",
    "Content-Type": "application/json",
}

# -------------------------------------------------
# GraphQL executor
# -------------------------------------------------
def _execute_graphql(query: str, variables: dict):
    r = requests.post(
        TWENTY_API_URL,
        headers=HEADERS,
        json={"query": query, "variables": variables},
        timeout=10,
    )
    r.raise_for_status()
    payload = r.json()

    if "errors" in payload:
        raise Exception(payload["errors"])

    return payload["data"]

# -------------------------------------------------
# Find person
# -------------------------------------------------
FIND_PERSON_BY_EMAIL = """
query ($email: String!) {
  people(filter: { emails: { primaryEmail: { eq: $email } } }) {
    edges { node { id } }
  }
}
"""

FIND_PERSON_BY_PHONE = """
query ($phone: String!) {
  people(filter: { phones: { primaryPhoneNumber: { eq: $phone } } }) {
    edges { node { id } }
  }
}
"""

def find_person_in_crm(email: Optional[str], phone: Optional[str]) -> Optional[str]:
    if email:
        data = _execute_graphql(FIND_PERSON_BY_EMAIL, {"email": email})
        edges = data["people"]["edges"]
        if edges:
            return edges[0]["node"]["id"]

    if phone:
        phone_10 = phone[-10:]
        data = _execute_graphql(FIND_PERSON_BY_PHONE, {"phone": phone_10})
        edges = data["people"]["edges"]
        if edges:
            return edges[0]["node"]["id"]

    return None

# -------------------------------------------------
# Create person (SAFE fields only)
# -------------------------------------------------
CREATE_PERSON_MUTATION = """
mutation ($data: PersonCreateInput!) {
  createPerson(data: $data) { id }
}
"""

def create_person_in_crm(lead: dict) -> str:
    data = {
        "name": {
            "firstName": lead["first_name"],
            "lastName": lead["last_name"],
        },
        "phones": {
            "primaryPhoneNumber": lead["phone_number"][-10:],
            "primaryPhoneCountryCode": "IN",
            "primaryPhoneCallingCode": "+91",
        },
        "city": lead.get("city"),
    }

    if lead.get("email"):
        data["emails"] = {
            "primaryEmail": lead["email"]
        }

    try:
        response = _execute_graphql(
            CREATE_PERSON_MUTATION,
            {"data": data}
        )
        return response["createPerson"]["id"]

    except Exception as e:
        # Handle duplicate race safely
        crm_id = find_person_in_crm(
            lead.get("email"),
            lead.get("phone_number")
        )
        if crm_id:
            return crm_id
        raise
      
