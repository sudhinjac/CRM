import os
import requests

TWENTY_API_URL = os.getenv("TWENTY_API_URL")
TWENTY_API_TOKEN = os.getenv("TWENTY_API_TOKEN")

if not TWENTY_API_URL or not TWENTY_API_TOKEN:
    raise RuntimeError("TWENTY_API_URL or TWENTY_API_TOKEN not set")

HEADERS = {
    "Authorization": f"Bearer {TWENTY_API_TOKEN}",
    "Content-Type": "application/json",
}

# -------------------------------------------------
# FIND PERSON BY EMAIL
# -------------------------------------------------
FIND_PERSON_BY_EMAIL = """
query FindPersonByEmail($email: String!) {
  people(
    filter: {
      emails: { primaryEmail: { eq: $email } }
    }
  ) {
    edges {
      node {
        id
      }
    }
  }
}
"""

# -------------------------------------------------
# FIND PERSON BY PHONE
# -------------------------------------------------
FIND_PERSON_BY_PHONE = """
query FindPersonByPhone($phone: String!) {
  people(
    filter: {
      phones: { primaryPhoneNumber: { eq: $phone } }
    }
  ) {
    edges {
      node {
        id
      }
    }
  }
}
"""

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
        raise Exception(f"Twenty GraphQL error: {payload['errors']}")

    return payload["data"]


def find_person_in_crm(email: str | None, phone: str | None) -> str | None:
    """
    Lookup order:
    1. Email
    2. Phone
    """

    # 1️⃣ Try email first
    if email:
        data = _execute_graphql(
            FIND_PERSON_BY_EMAIL,
            {"email": email}
        )

        edges = data["people"]["edges"]
        if edges:
            return edges[0]["node"]["id"]

    # 2️⃣ Try phone
    if phone:
        phone_10 = phone[-10:]

        data = _execute_graphql(
            FIND_PERSON_BY_PHONE,
            {"phone": phone_10}
        )

        edges = data["people"]["edges"]
        if edges:
            return edges[0]["node"]["id"]

    return None


# -------------------------------------------------
# CREATE PERSON
# -------------------------------------------------
CREATE_PERSON_MUTATION = """
mutation CreatePerson($data: PersonCreateInput!) {
  createPerson(data: $data) {
    id
  }
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
    }

    if lead.get("email"):
        data["emails"] = {
            "primaryEmail": lead["email"]
        }

    if lead.get("city"):
        data["city"] = lead["city"]

    payload = {
        "query": CREATE_PERSON_MUTATION,
        "variables": {"data": data},
    }

    r = requests.post(
        TWENTY_API_URL,
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    r.raise_for_status()
    response = r.json()

    if "errors" in response:
        raise Exception(f"CreatePerson failed: {response['errors']}")

    person = response.get("data", {}).get("createPerson")
    if not person:
        raise Exception(f"Unexpected CRM response: {response}")

    return person["id"]
