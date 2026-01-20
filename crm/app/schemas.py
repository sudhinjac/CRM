# app/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import date


class LeadCreate(BaseModel):
    lead_id: str

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None

    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None

    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None

    vehicle_type: Optional[str] = None
    current_credit: Optional[str] = None

    employment_status: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None

    monthly_salary_min: Optional[float] = None
    monthly_salary_max: Optional[float] = None

    employment_length: Optional[str] = None
    length_at_company: Optional[str] = None
    length_at_home_address: Optional[str] = None
