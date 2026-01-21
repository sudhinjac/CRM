# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------
# Load .env from project root (EXPLICIT)
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # CRM/CRM
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# -------------------------------------------------
# Database
# -------------------------------------------------
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# -------------------------------------------------
# Twenty CRM (REST)
# -------------------------------------------------
TWENTY_REST_URL = os.getenv("TWENTY_REST_URL")
TWENTY_REST_TOKEN = os.getenv("TWENTY_REST_TOKEN")

# -------------------------------------------------
# Validation (fail fast)
# -------------------------------------------------
missing = []

for key, val in {
    "DB_HOST": DB_HOST,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "TWENTY_REST_URL": TWENTY_REST_URL,
    "TWENTY_REST_TOKEN": TWENTY_REST_TOKEN,
}.items():
    if not val:
        missing.append(key)

if missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing)}"
    )

