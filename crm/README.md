## Lead Intake & Twenty CRM Orchestration Service

This project is a small FastAPI-based service that:

- **Accepts and deduplicates inbound leads** into a PostgreSQL database.
- **Synchronizes leads into Twenty CRM** as People records.
- **Auto-creates follow-up tasks** in Twenty and assigns them to workspace members with the lowest workload.

The overall design is clean and modular: configuration is centralized, database access is in a single layer, schema validation is handled by Pydantic, CRM integration is isolated in its own module, and the FastAPI app wires these pieces together. For a small/medium service this structure is **good enough and production-friendly**, with obvious extension points (e.g. connection pooling, logging, async) if needed later.

---

## Project Structure

- **`app/config.py`**  
  - Loads environment variables from the project root `.env` file using `python-dotenv`.  
  - Exposes **database configuration** (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) and **Twenty REST config** (`TWENTY_REST_URL`, `TWENTY_REST_TOKEN`).  
  - Performs a **fail-fast validation**: if any required variable is missing, it raises a `RuntimeError` during import so misconfiguration is detected immediately.

- **`app/db.py`**  
  - Defines `get_db_connection()` which returns a new `psycopg2` PostgreSQL connection using values from `config.py`.  
  - Keeps the database connection logic in one place so other modules don’t duplicate connection details.

- **`app/schemas.py`**  
  - Contains Pydantic models for FastAPI request/response validation.  
  - `LeadCreate` defines the fields accepted when creating a lead (lead ID, contact info, address, vehicle and employment info, salary ranges, etc.).  
  - FastAPI automatically validates incoming JSON against this model in the `POST /leads` endpoint.

- **`app/llm.py`** (local LLM copywriting helper)  
  - Calls a local Ollama model (default `llama3.1:8b`) to craft rich, conversion-focused markdown for CRM follow-up tasks.  
  - Adds headings/emojis, bold emphasis, optional color spans, and a concise “next steps” checklist aimed at closing the sale.  
  - Has built-in fallback to a static template so task creation never breaks if the LLM is offline.

- **`app/models.py`** (database access layer)  
  - Implements the low-level **SQL operations** on the `leads` table, using `get_db_connection()`:
    - `find_existing_lead(phone, email)` – checks for an existing lead by email (preferred) and then by phone; returns the business `lead_id` if found.  
    - `create_lead(data)` – inserts a new lead row using the `LeadCreate` payload, initializes `crm_synced` and `task_created` as `false`, and returns the new `lead_id`.  
    - `get_unsynced_leads()` – returns a list of all leads where `crm_synced = FALSE` as dictionaries, used for batch syncing to CRM.  
    - `mark_lead_crm_synced(lead_id, crm_person_id)` – marks a lead as synced and stores the `crm_person_id` from Twenty, updating `updated_at`.  
    - `search_leads(phone, email, name)` – supports filtered search on phone/email/name with case-insensitive `ILIKE`, returning the most recent 50 leads.  
    - `get_lead_by_id(lead_id)` – fetches a single lead by business `lead_id` and returns a clean dict (with `created_at` as ISO string).
  - This file acts as the **persistence layer**, keeping SQL separate from API and CRM logic.

- **`app/crm.py`** (integration with Twenty CRM)  
  - Uses `TWENTY_REST_URL` and `TWENTY_REST_TOKEN` from `config.py` to build `HEADERS` for all REST calls, and fails fast if the token is not set.  
  - **People upsert**:
    - `upsert_person_in_crm(lead)` – upserts a Twenty Person based on the lead’s email and name, optionally including job title and budget (`current_credit`).  
    - After the upsert, it performs a **lookup by email** (`/people?filter[emails.primaryEmail]=...`) and returns the canonical Person `id`.  
  - **Workspace members & task load**:
    - `get_workspace_members()` – fetches all workspace members from `/workspaceMembers`.  
    - `get_open_task_count(member_id)` – returns the count of TODO tasks for a given member via `/tasks`.  
    - `pick_member_with_lowest_load(members)` – computes each member’s open task count and randomly picks among those with the minimum value (simple load balancing).  
  - **People without TODO tasks**:
    - `get_people_without_open_tasks()` – fetches all people and all TODO tasks; constructs the expected task title (`"📞 Sales Follow-up — <name>"`) and returns people who do **not** already have such a TODO task.  
  - **Task creation**:
    - `create_task_for_person(person, assignee_id)` – creates a TODO task in Twenty for a Person using the LLM-generated markdown from `llm.py`, assigns it to the given workspace member, and validates the response structure; falls back to the static template if the LLM fails.

- **`app/main.py`** (FastAPI application and routes)  
  - Creates the FastAPI app: `app = FastAPI(title="Lead Intake & Task Orchestration API")`.  
  - **Lead creation & deduplication**  
    - `POST /leads` (`create_or_get_lead`)  
      - Accepts a `LeadCreate` body.  
      - Uses `find_existing_lead` to check for an existing lead by email/phone.  
      - If found, returns `{"status": "existing", "lead_id": ...}`; otherwise creates a new row via `create_lead` and returns `{"status": "created", "lead_id": ...}`.
  - **Sync unsynced leads to Twenty CRM**  
    - `POST /sync-crm` (`sync_all_leads_to_crm`)  
      - Fetches all `crm_synced = FALSE` leads via `get_unsynced_leads()`.  
      - For each lead, calls `upsert_person_in_crm` and then `mark_lead_crm_synced` to store the returned `crm_person_id`.  
      - Returns a summary with counts and per-lead failures: `total`, `synced_count`, `failed_count`, `synced`, `failed`.
  - **Lead search and retrieval**  
    - `GET /leads/search` (`search_leads_api`) – exposes `search_leads()` with optional query params `phone`, `email`, and `name`, returning a `results` list.  
    - `GET /leads/{lead_id}` (`get_lead_details`) – returns a single lead by business `lead_id` or `404` if not found.  
    - `GET /leads` (`list_leads`) – returns a minimal list of all leads (`lead_id`, `email`, `crm_synced`) ordered by `created_at DESC`.
  - **Auto-create and assign CRM tasks**  
    - `POST /tasks/auto-assign` (`auto_assign_tasks`)  
      - Gets workspace members (`get_workspace_members`) and eligible people without existing TODO follow-up tasks (`get_people_without_open_tasks`).  
      - For each eligible person, picks the member with the lowest open TODO load (`pick_member_with_lowest_load`) and creates a task with `create_task_for_person`.  
      - Returns counts of created vs failed tasks and a merged `details` list for transparency.

- **`app/__init__.py`**  
  - Currently empty; exists so `app` is treated as a Python package. This allows imports like `from app.models import ...`.

---

## Running the API

1. **Install dependencies** (example with `pip`):

```bash
pip install fastapi uvicorn psycopg2-binary python-dotenv requests
```

2. **Create a `.env` file at the project root** with at least:

```env
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password

TWENTY_REST_URL=https://api.twenty.com/v1
TWENTY_REST_TOKEN=your-twenty-rest-api-token
```

3. **Run the FastAPI app** (from the project root):

```bash
uvicorn app.main:app --reload
```

4. **Explore the API docs**:

- Open `http://127.0.0.1:8000/docs` in your browser for the interactive Swagger UI.

---

## Notes on Design & Possible Improvements

- The current layout is **solid for a small service**: clear separation between config, DB layer, schemas, CRM integration, and API routes.  
- Possible next improvements if the project grows:
  - Introduce **connection pooling** (e.g. via `psycopg2` pool or an async driver like `asyncpg`) and FastAPI dependencies for DB sessions.  
  - Add a **logging strategy** and centralized error handling around external API calls (retries, timeouts, structured logs).  
  - Extract **domain/services layer** (e.g. “LeadService”, “TaskService”) to sit between routes and `models.py`/`crm.py` once business rules become more complex.  
- As-is, the design is simple, readable, and maintainable, and should be easy for another developer to onboard and extend.

---

## Using the Local LLM (Ollama)

- The LLM call is optional; if it fails, tasks still get created with the static fallback template.  
- Default model: `llama3.1:8b`. Change it in `app/llm.py` to any model you have (e.g., `deepseek-r1:14b`, `codellama:13b`).  
- Ensure Ollama is running locally and the model is pulled: `ollama run llama3.1:8b` (first run pulls it).  
- Toggle on/off without code changes using env flag: `ENABLE_LLM_COPYWRITING=true` (default) or `false` to force the static template.
