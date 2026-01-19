# app/models.py
from app.db import get_db_connection

def find_existing_lead(phone: str, email: str | None):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id FROM leads
        WHERE phone_number = %s
           OR (%s IS NOT NULL AND email = %s)
        LIMIT 1
        """,
        (phone, email, email)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def create_lead(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO leads (
            first_name, last_name, phone_number, email,
            city, vehicle_type, budget
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
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




def get_unsynced_leads():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, phone_number, email, city, crm_person_id
        FROM leads
        WHERE crm_person_id IS NULL
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    keys = ["id", "first_name", "last_name", "phone_number", "email", "city", "crm_person_id"]
    return [dict(zip(keys, r)) for r in rows]


def update_crm_person_id(lead_id, crm_person_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE leads
        SET crm_person_id = %s
        WHERE id = %s
    """, (crm_person_id, lead_id))

    conn.commit()
    cur.close()
    conn.close()

