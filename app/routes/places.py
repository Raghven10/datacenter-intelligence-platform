from fastapi import APIRouter, Form, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.place import Place
from app.core.auth_guard import require_user
from app.core.audit import log_action

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

# List all places
@router.get("/places")
def list_places(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    search = request.query_params.get("search", "")
    page = int(request.query_params.get("page", 1))
    per_page = 10
    query = db.query(Place)
    if search:
        query = query.filter(Place.name.ilike(f"%{search}%"))
    total = query.count()
    places = query.offset((page-1)*per_page).limit(per_page).all()
    if "application/json" in request.headers.get("accept", ""):
        return [
            {"id": p.id, "name": p.name, "description": p.description}
            for p in places
        ]

    return templates.TemplateResponse("places.html", {
        "request": request,
        "user": user,
        "places": places,
        "page": page,
        "per_page": per_page,
        "total": total,
        "search": search
    })

# Add new place page
@router.post("/places/create")
def create_place(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    place = Place(name=name, description=description)
    db.add(place)
    log_action(db, "CREATE", target_table="places", description=f"Created new facility area: {name}")
    db.commit()
    if "application/json" in request.headers.get("accept", ""):
        return {"id": place.id, "name": place.name, "message": "Place created"}
    return RedirectResponse("/places/", status_code=302)

# POST API to save new place
@router.post("/places/edit/{place_id}")
def edit_place(
    place_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(None),  # ✅ added description
    db: Session = Depends(get_db),
    user=Depends(require_user)
):

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Update both name and description
    place.name = name
    place.description = description  # ✅ update description
    log_action(db, "UPDATE", target_table="places", target_id=place_id, description=f"Modified place configuration for {name}")
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"id": place.id, "name": place.name, "message": "Place updated"}

    return RedirectResponse("/places/", status_code=302)



@router.get("/places/delete/{place_id}")
def delete_place(
    place_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    log_action(db, "DELETE", target_table="places", target_id=place_id, description=f"Decommissioned facility area: {place.name}")
    db.delete(place)
    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return {"message": "Place deleted successfully", "id": place_id}

    return RedirectResponse("/places/", status_code=302)
