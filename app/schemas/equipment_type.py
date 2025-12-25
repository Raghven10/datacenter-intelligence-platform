from pydantic import BaseModel

class EquipmentTypeBase(BaseModel):
    name: str

class EquipmentTypeCreate(EquipmentTypeBase):
    pass

class EquipmentTypeUpdate(EquipmentTypeBase):
    pass

class EquipmentTypeResponse(EquipmentTypeBase):
    id: int

    class Config:
        from_attributes = True
