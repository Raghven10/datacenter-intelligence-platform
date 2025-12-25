from fastapi import HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from jose import jwt
from app.core.security import ALGORITHM, SECRET_KEY
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.user import User
from app.core.audit import set_audit_user


def login_required(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login?error=login_required", status_code=302)
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return RedirectResponse("/login?error=login_required", status_code=302)

        # Fetch the actual user object from DB with roles eagerly loaded
        user = db.query(User).options(joinedload(User.roles)).filter(User.username == username).first()
        if not user:
            return RedirectResponse("/login?error=login_required", status_code=302)

        request.state.user = user  # ✅ set the actual User ORM object
        set_audit_user(user.id) # ✅ Set for audit logging

    except Exception:
        return RedirectResponse("/login?error=login_required", status_code=302)

    return None  # means login is valid

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Login required")
    
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    # Eager load roles relationship
    user = db.query(User).options(joinedload(User.roles)).filter(User.username==username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    set_audit_user(user.id) # ✅ Set for audit logging
    return user

def require_user(user: User = Depends(get_current_user)):
    return user

def admin_required(user=Depends(get_current_user)):
    # if user.get("role") != "admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin access required"
    #     )
    return user