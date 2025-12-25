from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth_guard import require_user
from app.models.user import User, user_roles
from app.models.role import Role
import shutil
import os
from pathlib import Path
from app.core.audit import log_action, set_audit_user

router = APIRouter(prefix="/profile")

UPLOAD_DIR = Path("app/static/profile_pics")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/update")
async def update_profile_details(
    request: Request,
    full_name: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if full_name and full_name.strip():
        user.full_name = full_name.strip()
        log_action(db, "PROFILE_UPDATE", description=f"Updated display name to {user.full_name}")
        db.commit()
        request.session["flash_success"] = "Profile details updated"
    else:
        # If empty, maybe allow clearing? Or just ignore? 
        # Using existing pattern: if empty, dont update or set to username?
        # Let's enforce non-empty for display name if it's the primary ID.
        request.session["flash_error"] = "Display name cannot be empty"
        
    return RedirectResponse("/profile", status_code=303)

@router.post("/upload-picture")
async def upload_profile_picture(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith("image/"):
        request.session["flash_error"] = "File must be an image"
        return RedirectResponse("/profile", status_code=303)

    # Save file with username as filename (overwriting existing)
    extension = file.filename.split(".")[-1]
    if extension not in ["jpg", "jpeg", "png", "gif", "webp"]:
         request.session["flash_error"] = "Invalid image format"
         return RedirectResponse("/profile", status_code=303)

    filename = f"{user.username}.{extension}"
    file_path = UPLOAD_DIR / filename
    
    # Remove old profile pic if exists with different extension
    for ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        old_path = UPLOAD_DIR / f"{user.username}.{ext}"
        if old_path.exists():
            old_path.unlink()

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    set_audit_user(user.id)
    log_action(db, "PROFILE_UPDATE", description=f"Updated profile picture")
    db.commit()

    request.session["flash_success"] = "Profile picture updated"
    return RedirectResponse("/profile", status_code=303)


@router.post("/handover-role")
async def handover_role(
    request: Request,
    role_id: int = Form(...),
    target_user_id: int = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    # Verify user has this role
    role_to_transfer = None
    
    # Check primary role
    if user.role_id == role_id:
        role_to_transfer = user.role
        # Cannot transfer if it's the ONLY role and secondary roles are empty? 
        # For now, let's allow it, but we need to verify logic.
        # Actually, best to swap primary role to something else or NULL if possible?
        # Typically systems don't allow user to have NO role.
        # Let's assume we are transferring a secondary role or swapping primary.
        # Simplified logic: If primary, we set primary to 'User' (id likely 2) or something default.
        pass
    else:
        # Check secondary roles
        for r in user.roles:
            if r.id == role_id:
                role_to_transfer = r
                break
    
    if not role_to_transfer:
        request.session["flash_error"] = "You do not hold this role."
        return RedirectResponse("/profile", status_code=303)

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        request.session["flash_error"] = "Target user not found."
        return RedirectResponse("/profile", status_code=303)
        
    if target_user.id == user.id:
         request.session["flash_error"] = "Cannot handover role to yourself."
         return RedirectResponse("/profile", status_code=303)

    # Perform Transfer
    
    # 1. Remove from current user
    if user.role_id == role_id:
        # If it's primary, demote to 'user' role (assuming 'user' role exists and is safe default)
        default_role = db.query(Role).filter(Role.name == "user").first()
        if default_role:
             user.role_id = default_role.id
        else:
             # If no default user role, forbid transfer of primary role for now to prevent lockout
             request.session["flash_error"] = "Cannot transfer primary role without a fallback."
             return RedirectResponse("/profile", status_code=303)
    else:
        user.roles.remove(role_to_transfer)

    # 2. Add to target user
    # Check if target already has this role
    if target_user.role_id != role_id and role_to_transfer not in target_user.roles:
        target_user.roles.append(role_to_transfer)
        
    set_audit_user(user.id)
    log_action(db, "ROLE_HANDOVER", description=f"Handed over role {role_to_transfer.name} to {target_user.username}")
    db.commit()

    request.session["flash_success"] = f"Role {role_to_transfer.name} successfully handed over to {target_user.username}"
    return RedirectResponse("/profile", status_code=303)
