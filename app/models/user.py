from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.orm import relationship

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))  # Keep for backward compatibility
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    role = relationship("Role", foreign_keys=[role_id], back_populates="primary_users")  # Primary role
    roles = relationship("Role", secondary=user_roles, back_populates="users")  # Multiple roles
    notifications = relationship("Notification", back_populates="user")
    daily_inspections = relationship("DailyInspection", back_populates="user")
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role (case-insensitive)"""
        if not role_name:
            return False
        role_name_lower = role_name.lower()
        
        # Check primary role
        if self.role and self.role.name.lower() == role_name_lower:
            return True
            
        # Check secondary roles
        return any(r.name.lower() == role_name_lower for r in self.roles)
    
    def has_any_role(self, role_names: list) -> bool:
        """Check if user has any of the specified roles"""
        return any(self.has_role(role) for role in role_names)
    
    def is_sysadmin(self) -> bool:
        """Check if user is a system administrator"""
        return self.has_role("sysadmin")
    
    def is_admin(self) -> bool:
        """Check if user is an admin or sysadmin"""
        return self.has_any_role(["sysadmin", "admin"])