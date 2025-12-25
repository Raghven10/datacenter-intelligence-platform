from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.models.role import Role
from app.core.auth_guard import require_user
from app.core.audit import log_action

router = APIRouter(prefix="/roles", tags=["Roles"])
templates = Jinja2Templates(directory="app/templates")


# -------------------------
# List Roles
# -------------------------
@router.get("/")
def list_roles(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    log_action(db, "FETCH", target_table="roles", description="Accessed access roles repository")
    search = request.query_params.get("search", "")
    page = int(request.query_params.get("page", 1))
    per_page = 10

    query = db.query(Role)
    if search:
        query = query.filter(Role.name.ilike(f"%{search}%"))

    total = query.count()
    roles = query.offset((page - 1) * per_page).limit(per_page).all()

    if "application/json" in request.headers.get("accept", ""):
        return [{"id": r.id, "name": r.name} for r in roles]

    return templates.TemplateResponse(
        "roles.html",
        {
            "request": request,
            "user": user,
            "roles": roles,
            "page": page,
            "per_page": per_page,
            "total": total,
            "search": search,
        },
    )


# -------------------------
# Create Role
# -------------------------
@router.post("/create")
def create_role(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    if db.query(Role).filter(Role.name == name).first():
        raise HTTPException(status_code=400, detail="Role already exists")

    role = Role(name=name)
    db.add(role)
    log_action(db, "CREATE", target_table="roles", description=f"Created new access role: {name}")
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"id": role.id, "name": role.name, "message": "Role created"}

    return RedirectResponse("/roles/", status_code=302)


# -------------------------
# Edit Role
# -------------------------
@router.post("/edit/{role_id}")
def edit_role(
    role_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.name = name
    log_action(db, "UPDATE", target_table="roles", target_id=role_id, description=f"Updated role name to {name}")
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"id": role.id, "name": role.name, "message": "Role updated"}

    return RedirectResponse("/roles/", status_code=302)


# -------------------------
# Delete Role
# -------------------------
@router.get("/delete/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.primary_users or role.users:
        raise HTTPException(
            status_code=400,
            detail="Role is assigned to users and cannot be deleted",
        )

    log_action(db, "DELETE", target_table="roles", target_id=role_id, description=f"Deleted role: {role.name}")
    db.delete(role)
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"message": "Role deleted successfully", "id": role_id}

    return RedirectResponse("/roles/", status_code=302)
