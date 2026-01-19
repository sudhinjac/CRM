# app/models.py
from app.db import get_db_connection


# -------------------------------------------------
# Find existing lead (SAFE + deterministic)
# -------------------------------------------------
def find_existing_lead(phone: str, email: str | None):
    conn = get_db_connection()
    cur = conn.cursor()

    # 1️⃣ Prefer email match
    if email:
        cur.execute(
            """
            SELECT id
            FROM leads
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )
        row = cur.fetchone()
        if row:
            cur.close()
            conn.close()
            return row[0]

    # 2️⃣ Fallback to phone match
    cur.execute(
        """
        SELECT id
        FROM leads
        WHERE phone_number = %s
        LIMIT 1
        """,
        (phone,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


# -------------------------------------------------
# Create new lead
# -------------------------------------------------
def create_lead(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO leads (
            first_name,
            last_name,
            phone_number,
            email,
            city,
            vehicle_type,
            budget,
            crm_synced
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,FALSE)
        RETURNING id
        """,
        (
            data.first_name,
            data.last_name,
            data.phone_number,
            data.email,
            data.city,
            data.vehicle_type,
            data.budget,
        )
    )

    lead_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return lead_id


# -------------------------------------------------
# Get leads NOT synced to CRM
# -------------------------------------------------
def get_unsynced_leads():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            first_name,
            last_name,
            phone_number,
            email,
            city
        FROM leads
        WHERE crm_synced = FALSE
        """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    keys = [
        "id",
        "first_name",
        "last_name",
        "phone_number",
        "email",
        "city",
    ]

    return [dict(zip(keys, row)) for row in rows]


# -------------------------------------------------
# Mark lead as CRM-synced (ATOMIC)
# -------------------------------------------------
def update_crm_person_id(lead_id, crm_person_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE leads
        SET
            crm_person_id = %s,
            crm_synced = TRUE,
            updated_at = now()
        WHERE id = %s
        """,
        (crm_person_id, lead_id)
    )

    conn.commit()
    cur.close()
    conn.close()

def search_leads(phone=None, email=None, name=None):
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
    SELECT *
    FROM leads
    WHERE
        (%s IS NULL OR phone_number ILIKE %s)
    AND (%s IS NULL OR email ILIKE %s)
    AND (%s IS NULL OR first_name ILIKE %s OR last_name ILIKE %s)
    ORDER BY created_at DESC
    LIMIT 50
    """

    cur.execute(
        query,
        (
            phone, f"%{phone}%" if phone else None,
            email, f"%{email}%" if email else None,
            name, f"%{name}%", f"%{name}%"
        )
    )

    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [dict(zip(cols, row)) for row in rows]


def get_lead_by_id(lead_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM leads WHERE id = %s",
        (lead_id,)
    )

    row = cur.fetchone()
    if not row:
        return None

    cols = [desc[0] for desc in cur.description]
    lead = dict(zip(cols, row))

    cur.close()
    conn.close()
    return lead
