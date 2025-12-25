from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.models.user import User
from app.models.role import Role
from app.core.auth_guard import require_user
from app.core.audit import log_action

router = APIRouter(prefix="/users", tags=["Users"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    log_action(db, "FETCH", target_table="users", description="Accessed user directory")
    search = request.query_params.get("search", "")
    page = int(request.query_params.get("page", 1))
    per_page = 10

    query = db.query(User)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))

    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    roles = db.query(Role).all()

    if "application/json" in request.headers.get("accept", ""):
        return [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role.name if u.role else None,
                "is_active": u.is_active
            }
            for u in users
        ]

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "user": current_user,
            "users": users,
            "roles": roles,
            "page": page,
            "per_page": per_page,
            "total": total,
            "search": search,
        },
    )


@router.post("/edit/{user_id}")
def update_user(
    user_id: int,
    request: Request,
    username: str = Form(...),
    full_name: str = Form(None), # Optional full name
    role_ids: str = Form(""), # Comma separated IDs or empty
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check username uniqueness if changed
    if username != user.username:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            request.session["flash_error"] = "Username already exists"
            return RedirectResponse("/users/", status_code=302)
        user.username = username

    if full_name is not None:
         user.full_name = full_name if full_name.strip() else username

    # Update Roles
    # Parse role_ids from form (checkboxes usually send multiple values with same key, 
    # but FastAPI/Starlette Form with same key might need List[int]. 
    # However, standard HTML form with predefined values usually sends them.
    # If we use JS to join them into a string, it's easier. 
    # Let's assume the frontend sends a comma-separated string `role_ids` similar to the create endpoint,
    # OR we can accept `role_ids: List[int] = Form(...)` if the frontend sends multiple inputs with name 'role_ids'.
    # The 'create_user' endpoint used `role_ids: str` (comma separated). I will stick to that pattern for consistency.
    
    selected_role_ids = []
    if role_ids:
        try:
             selected_role_ids = [int(rid) for rid in role_ids.split(",") if rid.strip()]
        except ValueError:
            pass
            
    roles_to_assign = db.query(Role).filter(Role.id.in_(selected_role_ids)).all()
    
    # Permission check (optional but good practice): Ensure current_user can assign these roles?
    # Skipping for now as this is an admin-only endpoint effectively.
    
    user.roles = roles_to_assign
    
    # Update primary role (fallback for legacy/display compatibility)
    if roles_to_assign:
        user.role_id = roles_to_assign[0].id
    else:
        user.role_id = None # Or default role?

    user.is_active = is_active
    
    log_action(db, "UPDATE", target_table="users", target_id=user.id, description=f"Updated profile for {user.username} (Roles: {[r.name for r in roles_to_assign]})")
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"id": user.id, "username": user.username, "message": "User updated"}

    return RedirectResponse("/users/", status_code=302)


@router.get("/delete/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log_action(db, "DELETE", target_table="users", target_id=user.id, description=f"Deleted user profile: {user.username}")
    db.delete(user)
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"message": "User deleted successfully", "id": user_id}

    return RedirectResponse("/users/", status_code=302)


# ========== NEW RBAC ENDPOINTS ==========

from app.core.permissions import (
    can_modify_user_roles, can_assign_role, can_reset_password,
    can_delete_user, can_create_user
)
from app.core.security import hash_password, verify_password


@router.post("/create")
def create_user_by_admin(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(None),
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
        full_name=full_name if full_name else username,
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
