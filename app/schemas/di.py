from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class DIBase(BaseModel):
    inspection_date: date
    status: str

class DICreate(BaseModel):
    # Form data is complex, typically handle manually or separate schema
    pass 

class DIResponse(DIBase):
    id: int
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True
