from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()

from db import get_db_connection
from crm import upsert_person_in_crm

app = FastAPI()

@app.post("/sync-crm")
def sync_crm():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            lead_id,
            first_name,
            last_name,
            email,
            phone,
            job_title,
            current_credit
        FROM leads
        WHERE crm_synced = FALSE
    """)

    rows = cur.fetchall()
    cols = [c[0] for c in cur.description]

    synced, failed = [], []

    for row in rows:
        lead = dict(zip(cols, row))
        try:
            crm_id = upsert_person_in_crm(lead)

            cur.execute("""
                UPDATE leads
                SET crm_synced = TRUE,
                    crm_person_id = %s
                WHERE lead_id = %s
            """, (crm_id, lead["lead_id"]))

            synced.append(lead["lead_id"])

        except Exception as e:
            failed.append({
                "lead_id": lead["lead_id"],
                "error": str(e)
            })

    conn.commit()
    cur.close()
    conn.close()

    return {
        "total": len(rows),
        "synced_count": len(synced),
        "failed_count": len(failed),
        "failed": failed,
    }
