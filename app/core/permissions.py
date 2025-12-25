"""
Permission System for Role-Based Access Control
Provides decorators and helper functions for checking user permissions
"""

from functools import wraps
from fastapi import HTTPException, status
from app.models.user import User

def require_role(role_name: str):
    """
    Decorator to require a specific role for accessing an endpoint
    Usage: @require_role("sysadmin")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs (injected by dependency)
            current_user = kwargs.get('current_user')
            if not current_user or not isinstance(current_user, User):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not current_user.has_role(role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {role_name} role"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_role(role_names: list):
    """
    Decorator to require any of the specified roles
    Usage: @require_any_role(["sysadmin", "admin"])
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or not isinstance(current_user, User):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not current_user.has_any_role(role_names):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {', '.join(role_names)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def can_modify_user_roles(current_user: User, target_user: User) -> bool:
    """
    Check if current user can modify target user's roles
    
    Rules:
    - Sysadmin can modify anyone's roles
    - Admin can modify non-admin/non-sysadmin users' roles
    - Regular users cannot modify any roles
    """
    if not current_user:
        return False
    
    # Sysadmin can modify anyone
    if current_user.is_sysadmin():
        return True
    
    # Admin can modify non-admin users
    if current_user.is_admin():
        # Cannot modify sysadmin or admin users
        if target_user.is_admin() or target_user.is_sysadmin():
            return False
        return True
    
    # Regular users cannot modify roles
    return False

def can_assign_role(current_user: User, role_name: str) -> bool:
    """
    Check if current user can assign a specific role
    
    Rules:
    - Sysadmin can assign any role
    - Admin can assign roles except sysadmin and admin
    - Regular users cannot assign any roles
    """
    if not current_user:
        return False
    
    # Sysadmin can assign any role
    if current_user.is_sysadmin():
        return True
    
    # Admin can assign roles except sysadmin and admin
    if current_user.is_admin():
        if role_name in ["sysadmin", "admin"]:
            return False
        return True
    
    # Regular users cannot assign roles
    return False

def can_reset_password(current_user: User, target_user: User) -> bool:
    """
    Check if current user can reset target user's password
    
    Rules:
    - Sysadmin can reset anyone's password
    - Admin can reset non-admin users' passwords
    - Users can reset their own password
    """
    if not current_user:
        return False
    
    # Users can always reset their own password
    if current_user.id == target_user.id:
        return True
    
    # Sysadmin can reset anyone's password
    if current_user.is_sysadmin():
        return True
    
    # Admin can reset non-admin users' passwords
    if current_user.is_admin():
        if target_user.is_admin() or target_user.is_sysadmin():
            return False
        return True
    
    return False

def can_delete_user(current_user: User, target_user: User) -> bool:
    """
    Check if current user can delete target user
    
    Rules:
    - Sysadmin can delete anyone except themselves
    - Admin can delete non-admin users
    - Regular users cannot delete anyone
    """
    if not current_user:
        return False
    
    # Cannot delete yourself
    if current_user.id == target_user.id:
        return False
    
    # Sysadmin can delete anyone (except themselves, checked above)
    if current_user.is_sysadmin():
        return True
    
    # Admin can delete non-admin users
    if current_user.is_admin():
        if target_user.is_admin() or target_user.is_sysadmin():
            return False
        return True
    
    return False

def can_create_user(current_user: User) -> bool:
    """
    Check if current user can create new users
    
    Rules:
    - Sysadmin and Admin can create users
    - Regular users cannot create users
    """
    if not current_user:
        return False
    
    return current_user.is_admin() or current_user.is_sysadmin()
