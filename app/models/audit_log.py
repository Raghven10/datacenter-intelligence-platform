from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.orm import relationship

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Null for anonymous actions or system tasks
    action = Column(String(50), nullable=False) # CREATE, UPDATE, DELETE, FETCH, LOGIN, etc.
    target_table = Column(String(50), nullable=True)
    target_id = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
