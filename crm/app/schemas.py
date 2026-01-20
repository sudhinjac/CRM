# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr] = None
    city: Optional[str] = None
    country: Optional[str] = None
    employment_status: Optional[str] = None
    job_title: Optional[str] = None
    monthly_salary_min: Optional[float] = None
