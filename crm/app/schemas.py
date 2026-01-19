# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    city: Optional[str] = None
    vehicle_type: Optional[str] = None
    budget: Optional[float] = None
