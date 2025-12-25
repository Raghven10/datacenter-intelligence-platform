from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import markdown
import os
from pathlib import Path
from app.core.auth_guard import login_required, require_user
from app.core.security import create_token, hash_password
from jose import jwt
from app.core.security import SECRET_KEY
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.equipment import Equipment
from app.models.user import User
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def home(request: Request):
    token = request.cookies.get("access_token")
    if token:
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return RedirectResponse("/dashboard")
        except:
            pass
    return RedirectResponse("/login")

@router.get("/login")
def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )


@router.get("/login")
def login_page(request: Request, error: str | None = None):
    token = request.cookies.get("access_token")
    if token:
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return RedirectResponse("/dashboard")
        except:
            pass

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )



@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        "register_public.html",
        {"request": request}
    )

@router.post("/register")
def register_user(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    # TODO: save user to DB
    return RedirectResponse("/login", status_code=302)



@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


# @router.get("/equipments")
# def equipments(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
@router.get("/profile")
def profile(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    all_users = db.query(User).filter(User.id != user.id).all()
    # Find profile picture
    profile_pic = None
    upload_dir = Path("app/static/profile_pics")
    for ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        if (upload_dir / f"{user.username}.{ext}").exists():
            profile_pic = f"/static/profile_pics/{user.username}.{ext}"
            break
            
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user, 
        "users": all_users,
        "profile_pic": profile_pic,
        "title": "User Profile"
    })

@router.get("/settings")
def settings(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "title": "Settings"})

@router.get("/user_manual")
def user_manual(request: Request):
    # Use absolute path that works in both local and Docker
    manual_path = Path(__file__).parent.parent.parent / "user_manual.md"
    
    if not manual_path.exists():
        return HTMLResponse("Manual not found.", status_code=404)
    
    with open(manual_path, "r") as f:
        text = f.read()
        html_content = markdown.markdown(text, extensions=['fenced_code', 'tables'])
        
    return templates.TemplateResponse("user_manual.html", {
        "request": request,
        "content": html_content
    })

#         "request": request,
#         "user": user,
#         "equipments": equipments
#     })