from dotenv import load_dotenv
import os

# -------------------------------------------------
# Load .env FIRST (this fixes your runtime error)
# -------------------------------------------------
load_dotenv()

# -------------------------------------------------
# App
# -------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "dev")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8000))

# -------------------------------------------------
# Database
# -------------------------------------------------
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# -------------------------------------------------
# Twenty CRM (CLOUD)
# -------------------------------------------------
TWENTY_REST_URL = os.getenv("TWENTY_REST_URL")
TWENTY_REST_TOKEN = os.getenv("TWENTY_REST_TOKEN")

# -------------------------------------------------
# Security
# -------------------------------------------------
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

# -------------------------------------------------
# HARD VALIDATION (fail fast, fail loud)
# -------------------------------------------------
missing = []

if not DB_HOST:
    missing.append("DB_HOST")
if not DB_NAME:
    missing.append("DB_NAME")
if not DB_USER:
    missing.append("DB_USER")
if not DB_PASSWORD:
    missing.append("DB_PASSWORD")

if not TWENTY_REST_URL:
    missing.append("TWENTY_REST_URL")
if not TWENTY_REST_TOKEN:
    missing.append("TWENTY_REST_TOKEN")

if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
