from sqlalchemy import Column, Integer, ForeignKey, String, Float
from sqlalchemy.orm import relationship
from app.db.base import Base

class DIEquipmentLog(Base):
    __tablename__ = "di_equipment_logs"

    id = Column(Integer, primary_key=True)
    di_id = Column(Integer, ForeignKey("daily_inspections.id"))
    equipment_id = Column(Integer, ForeignKey("equipments.id"))
    serviceability = Column(String(5)) # S / US
    status = Column(String(5))         # On / Off
    cleaning_status = Column(String(20)) # Clean / Dirty / etc
    remarks = Column(String(255))
    
    # Optional Fields
    pressure = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    frequency = Column(Float, nullable=True)
    resistance = Column(Float, nullable=True)

    # Relationships
    di = relationship("DailyInspection", back_populates="equipment_logs")