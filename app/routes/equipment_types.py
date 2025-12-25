from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.equipment_type import EquipmentType
from app.core.auth_guard import require_user
from app.core.audit import log_action
from app.schemas.equipment_type import EquipmentTypeCreate, EquipmentTypeUpdate

router = APIRouter(prefix="/equipment_types")
templates = Jinja2Templates(directory="app/templates")

# List
@router.get("/")
def list_equipment_types(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    log_action(db, "FETCH", target_table="equipment_types", description="Fetched equipment types list")
    types = db.query(EquipmentType).all()
    if "application/json" in request.headers.get("accept", ""):
        return [{"id": t.id, "name": t.name} for t in types]

    return templates.TemplateResponse("equipment_types_list.html", {
        "request": request,
        "user": user,
        "types": types,
        "title": "Equipment Types"
    })

# Create Form
@router.get("/create")
def create_equipment_type_form(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse("equipment_types_form.html", {
        "request": request,
        "user": user,
        "title": "Create Equipment Type"
    })

# Create Action
@router.post("/create")
def create_equipment_type(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    # Check duplicate
    existing = db.query(EquipmentType).filter(EquipmentType.name == name).first()
    if existing:
        return templates.TemplateResponse("equipment_types_form.html", {
            "request": request,
            "user": user,
            "error": "Equipment Type already exists",
            "name": name,
            "title": "Create Equipment Type"
        })
    
    new_type = EquipmentType(name=name)
    db.add(new_type)
    db.commit()
    
    # Flash success (using session)
    # Flash success (using session)
    request.session["flash_success"] = "Equipment Type created successfully"

    if "application/json" in request.headers.get("accept", ""):
        return {"id": new_type.id, "name": new_type.name, "message": "Created successfully"}

    return RedirectResponse("/equipment_types/", status_code=status.HTTP_302_FOUND)

# Edit Form
@router.get("/{id}/edit")
def edit_equipment_type_form(id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    etype = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not etype:
        raise HTTPException(status_code=404, detail="Equipment Type not found")
        
    return templates.TemplateResponse("equipment_types_form.html", {
        "request": request,
        "user": user,
        "type": etype,
        "title": "Edit Equipment Type"
    })

# Edit Action
@router.post("/{id}/edit")
def edit_equipment_type(
    id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    etype = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not etype:
        raise HTTPException(status_code=404, detail="Equipment Type not found")

    # Check duplicate if name changed
    if etype.name != name:
        existing = db.query(EquipmentType).filter(EquipmentType.name == name).first()
        if existing:
             return templates.TemplateResponse("equipment_types_form.html", {
                "request": request,
                "user": user,
                "type": etype,
                "error": "Equipment Type name already exists",
                "title": "Edit Equipment Type"
            })
    
    etype.name = name
    db.commit()
    
    request.session["flash_success"] = "Equipment Type updated successfully"

    if "application/json" in request.headers.get("accept", ""):
        return {"id": etype.id, "name": etype.name, "message": "Updated successfully"}

    return RedirectResponse("/equipment_types/", status_code=status.HTTP_302_FOUND)

# Delete
@router.get("/{id}/delete")
def delete_equipment_type(id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    etype = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not etype:
         raise HTTPException(status_code=404, detail="Equipment Type not found")
         
    # Check if used? (Optional for now, SqlAlchemy might error or cascade depending on setup)
    # The model defines relationship, but not cascade behavior explicitly in equipment_type.py side for db constraint.
    # We'll just try to delete.
    
    try:
        db.delete(etype)
        db.commit()
        request.session["flash_success"] = "Equipment Type deleted successfully"
    except Exception as e:
        db.rollback()
        request.session["flash_error"] = "Cannot delete: Type likely in use."
        
    return RedirectResponse("/equipment_types/", status_code=status.HTTP_302_FOUND)
