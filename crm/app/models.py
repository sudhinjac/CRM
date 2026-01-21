from app.db import get_db_connection

# -------------------------------------------------
# Find existing lead (email preferred, phone fallback)
# RETURNS lead_id (business ID)
# -------------------------------------------------
def find_existing_lead(phone: str, email: str | None):
    conn = get_db_connection()
    cur = conn.cursor()

    if email:
        cur.execute(
            "SELECT lead_id FROM leads WHERE email = %s LIMIT 1",
            (email,)
        )
        row = cur.fetchone()
        if row:
            cur.close()
            conn.close()
            return row[0]

    if phone:
        cur.execute(
            "SELECT lead_id FROM leads WHERE phone = %s LIMIT 1",
            (phone,)
        )
        row = cur.fetchone()
        if row:
            cur.close()
            conn.close()
            return row[0]

    cur.close()
    conn.close()
    return None


# -------------------------------------------------
# Create new lead
# RETURNS lead_id
# -------------------------------------------------
def create_lead(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO leads (
            lead_id,
            first_name,
            last_name,
            full_name,
            email,
            phone,
            employment_status,
            job_title,
            monthly_salary_min,
            monthly_salary_max,
            crm_synced,
            task_created
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, false)
        RETURNING lead_id
        """,
        (
            data.lead_id,
            data.first_name,
            data.last_name,
            data.full_name,
            data.email,
            data.phone,
            data.employment_status,
            data.job_title,
            data.monthly_salary_min,
            data.monthly_salary_max,
        ),
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
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    lead_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    city,
                    country,
                    employment_status,
                    job_title,
                    monthly_salary_min
                FROM leads
                WHERE crm_synced = FALSE
            """)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()

    return [dict(zip(cols, row)) for row in rows]


# -------------------------------------------------
# Mark lead as CRM-synced
# -------------------------------------------------
def mark_lead_crm_synced(lead_id: str, crm_person_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE leads
        SET
            crm_synced = TRUE,
            crm_person_id = %s,
            updated_at = now()
        WHERE lead_id = %s
        """,
        (crm_person_id, lead_id)
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------
# Search leads
# -------------------------------------------------
def search_leads(phone=None, email=None, name=None):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            lead_id,
            first_name,
            last_name,
            email,
            phone,
            crm_synced
        FROM leads
        WHERE
            (%s IS NULL OR phone ILIKE %s)
        AND (%s IS NULL OR email ILIKE %s)
        AND (
            %s IS NULL
            OR first_name ILIKE %s
            OR last_name ILIKE %s
        )
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (
            phone, f"%{phone}%" if phone else None,
            email, f"%{email}%" if email else None,
            name, f"%{name}%", f"%{name}%"
        )
    )

    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]


# -------------------------------------------------
# Get lead by BUSINESS lead_id (API-safe)
# -------------------------------------------------
def get_lead_by_id(lead_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            lead_id,
            first_name,
            last_name,
            email,
            phone,
            crm_synced,
            created_at
        FROM leads
        WHERE lead_id = %s
        """,
        (lead_id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "lead_id": row[0],
        "first_name": row[1],
        "last_name": row[2],
        "email": row[3],
        "phone": row[4],
        "crm_synced": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
    }
