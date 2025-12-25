"""
New User Management Endpoints with Enhanced RBAC
Add these to app/routes/users.py
"""

from typing import List
from fastapi import Form
from app.core.permissions import (
    can_modify_user_roles, can_assign_role, can_reset_password,
    can_delete_user, can_create_user
)
from app.core.security import hash_password

# Add to existing users.py router

@router.post("/create")
def create_user_by_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role_ids: str = Form(...),  # Comma-separated role IDs
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """Create a new user (sysadmin/admin only)"""
    
    # Check permission
    if not can_create_user(current_user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to create users"
        )
    
    # Check if username exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Parse role IDs
    role_id_list = [int(rid.strip()) for rid in role_ids.split(",") if rid.strip()]
    
    # Validate roles can be assigned
    roles_to_assign = db.query(Role).filter(Role.id.in_(role_id_list)).all()
    for role in roles_to_assign:
        if not can_assign_role(current_user, role.name):
            raise HTTPException(
                status_code=403,
                detail=f"You cannot assign the '{role.name}' role"
            )
    
    # Create user
    hashed_password = hash_password(password)
    primary_role = roles_to_assign[0] if roles_to_assign else None
    
    user = User(
        username=username,
        password_hash=hashed_password,
        role_id=primary_role.id if primary_role else None,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assign all roles
    user.roles.extend(roles_to_assign)
    db.commit()
    
    log_action(db, "CREATE", target_table="users", target_id=user.id, 
               description=f"Created user {username} with roles: {', '.join(r.name for r in roles_to_assign)}")
    
    if "application/json" in request.headers.get("accept", ""):
        return {"message": "User created successfully", "user_id": user.id}
    
    return RedirectResponse("/users/", status_code=302)


@router.post("/{user_id}/roles")
def update_user_roles(
    user_id: int,
    request: Request,
    role_ids: str = Form(...),  # Comma-separated role IDs
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """Update user's roles (with permission checks)"""
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check permission to modify this user's roles
    if not can_modify_user_roles(current_user, target_user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this user's roles"
        )
    
    # Parse and validate roles
    role_id_list = [int(rid.strip()) for rid in role_ids.split(",") if rid.strip()]
    roles_to_assign = db.query(Role).filter(Role.id.in_(role_id_list)).all()
    
    for role in roles_to_assign:
        if not can_assign_role(current_user, role.name):
            raise HTTPException(
                status_code=403,
                detail=f"You cannot assign the '{role.name}' role"
            )
    
    # Update roles
    target_user.roles.clear()
    target_user.roles.extend(roles_to_assign)
    
    # Update primary role
    if roles_to_assign:
        target_user.role_id = roles_to_assign[0].id
    
    db.commit()
    
    log_action(db, "UPDATE", target_table="users", target_id=user_id,
               description=f"Updated roles for {target_user.username}: {', '.join(r.name for r in roles_to_assign)}")
    
    if "application/json" in request.headers.get("accept", ""):
        return {"message": "Roles updated successfully"}
    
    return RedirectResponse("/users/", status_code=302)


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """Reset user's password (admin only, cannot view existing password)"""
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check permission
    if not can_reset_password(current_user, target_user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to reset this user's password"
        )
    
    # Reset password (never expose existing password)
    target_user.password_hash = hash_password(new_password)
    db.commit()
    
    log_action(db, "UPDATE", target_table="users", target_id=user_id,
               description=f"Password reset for user {target_user.username}")
    
    if "application/json" in request.headers.get("accept", ""):
        return {"message": "Password reset successfully"}
    
    return RedirectResponse("/users/", status_code=302)


@router.put("/me/password")
def change_own_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """User changes their own password (requires old password)"""
    
    from app.core.security import verify_password
    
    # Verify old password
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid current password")
    
    # Update password
    current_user.password_hash = hash_password(new_password)
    db.commit()
    
    log_action(db, "UPDATE", target_table="users", target_id=current_user.id,
               description="User changed their own password")
    
    if "application/json" in request.headers.get("accept", ""):
        return {"message": "Password changed successfully"}
    
    return RedirectResponse("/dashboard", status_code=302)
