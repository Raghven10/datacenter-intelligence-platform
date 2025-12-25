
from app.core.security import create_token, verify_password, hash_password
from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Depends, Form, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user import User
from app.core.audit import log_action, set_audit_user
from app.core.auth_guard import require_user


router = APIRouter(prefix="/auth")

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    set_audit_user(user.id)
    log_action(db, "SECURITY_LOGIN", description=f"Operator {username} successfully authenticated")
    db.commit()

    # ✅ Create JWT
    token = create_token({
        "sub": user.username,
        "role": user.role.name
    })

    # ✅ Redirect to dashboard
    response = RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_302_FOUND
    )

    # JWT cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )

    # 🔔 Flash success message
    request.session["flash_success"] = "Login successful"

    # Support JSON response
    if "application/json" in request.headers.get("accept", ""):
        # For JSON clients, we can return the token in the body too
        # But we also set the cookie just in case
        return {
            "access_token": token,
            "token_type": "bearer",
            "message": "Login successful"
        }

    return response




@router.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    
    
    # 1️⃣ Check if user already exists
    existing_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # 2️⃣ Hash password
    hashed_password = hash_password(password)
    
    # 🔐 Check if this is the first user (should become sysadmin)
    user_count = db.query(User).count()
    is_first_user = (user_count == 0)
    
    if is_first_user:
        # First user gets sysadmin role
        role = db.query(Role).filter(Role.name == "sysadmin").first()
        if not role:
            role = Role(name="sysadmin")
            db.add(role)
            db.commit()
            db.refresh(role)
    else:
        # Subsequent self-registrations get user role
        role = db.query(Role).filter(Role.name == "user").first()
        if not role:
            role = Role(name="user")
            db.add(role)
            db.commit()
            db.refresh(role)

    # 3️⃣ Create user
    user = User(
        username=username,
        password_hash=hashed_password,
        role_id=role.id,  # Primary role for backward compatibility
        is_active=True
    )

    # 4️⃣ Save to DB
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 5️⃣ Assign role to user.roles (multi-role support)
    user.roles.append(role)
    db.commit()

    set_audit_user(user.id)
    log_action(db, "SECURITY_REGISTER", description=f"New operator profile enrolled: {username}")
    db.commit()

    # 5️⃣ CREATE JWT (AUTO LOGIN)
    token = create_token({
        "sub": user.username,
        "role": user.role.name
    })

    # 6️⃣ Redirect to dashboard with JWT cookie
    if "application/json" in request.headers.get("accept", ""):
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "username": user.username
        }

    response = RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_302_FOUND
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )

    return response


@router.post("/switch-role")
def switch_role(
    request: Request,
    role_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_user)
):
    # Check if user has this role
    target_role = db.query(Role).filter(Role.id == role_id).first()
    if not target_role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if not current_user.has_role(target_role.name):
         raise HTTPException(status_code=403, detail="You do not have this role")

    # Update active role
    current_user.role_id = target_role.id
    db.commit()
    
    # Refresh Token
    token = create_token({
        "sub": current_user.username,
        "role": target_role.name
    })
    
    # Redirect
    referer = request.headers.get("referer") or "/dashboard"
    response = RedirectResponse(url=referer, status_code=status.HTTP_302_FOUND)
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )
    
    request.session["flash_success"] = f"Switched to {target_role.name} view"
    return response
