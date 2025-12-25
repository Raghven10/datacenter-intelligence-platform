
from sqlalchemy import Column, Integer, String
from app.db.base import Base
from sqlalchemy.orm import relationship

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


    primary_users = relationship("User", back_populates="role")
    users = relationship("User", secondary="user_roles", back_populates="roles")