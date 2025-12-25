from fastapi import APIRouter, Request, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from app.db.session import get_db
from app.core.auth_guard import require_user
from app.core.audit import log_action
from app.models.equipment import Equipment
from app.models.user import User
from app.models.daily_inspection import DailyInspection
from app.models.di_equipment_log import DIEquipmentLog
from app.models.place import Place
from app.models.equipment_type import EquipmentType

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    log_action(db, "FETCH", target_table="dashboard", description="Accessed Command Center dashboard")
    if not user:
        return RedirectResponse("/login?error=login_required", status_code=status.HTTP_302_FOUND)

    equipments = db.query(Equipment).all()
    
    # Basic Stats
    total_assets = len(equipments)
    operational_assets = len([e for e in equipments if e.serviceability == 'S'])
    faulty_assets = total_assets - operational_assets
    
    # Today's DI Status
    today_di = db.query(DailyInspection).filter(DailyInspection.inspection_date == date.today()).order_by(DailyInspection.id.desc()).first()
    today_di_status = today_di.status if today_di else "PENDING"
    pending_with = today_di.forwarded_to if today_di else None
    today_di_id = today_di.id if today_di else None
    
    # Distribution by Type
    type_dist = db.query(EquipmentType.name, func.count(Equipment.id)).join(Equipment).group_by(EquipmentType.name).all()
    distribution_by_type = {name: count for name, count in type_dist}
    
    # Distribution by Place
    place_dist = db.query(Place.name, func.count(Equipment.id)).join(Equipment).group_by(Place.name).all()
    distribution_by_place = {name: count for name, count in place_dist}
    
    # Recent Faults (Last 10 unserviceable logs)
    # Joining with Equipment to get the name
    recent_faults = db.query(DIEquipmentLog, Equipment.name).join(Equipment).filter(DIEquipmentLog.serviceability == 'US').order_by(DIEquipmentLog.id.desc()).limit(10).all()
    
    # Fault Trend (Simple mock or actual aggregation if history exists)
    # Let's get counts of 'US' per inspection date for last 7 inspections
    fault_trend_query = db.query(DailyInspection.inspection_date, func.count(DIEquipmentLog.id))\
        .join(DIEquipmentLog)\
        .filter(DIEquipmentLog.serviceability == 'US')\
        .group_by(DailyInspection.inspection_date)\
        .order_by(DailyInspection.inspection_date.desc())\
        .limit(7).all()
    
    fault_trend = [{"date": str(d), "count": c} for d, c in reversed(fault_trend_query)]

    if "application/json" in request.headers.get("accept", ""):
        return {
            "stats": {
                "total_assets": total_assets,
                "operational_assets": operational_assets,
                "faulty_assets": faulty_assets,
                "today_di_status": today_di_status
            },
            "distribution_by_type": distribution_by_type,
            "distribution_by_place": distribution_by_place,
            "fault_trend": fault_trend
        }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_assets": total_assets,
        "operational_assets": operational_assets,
        "faulty_assets": faulty_assets,
        "today_di": today_di,  # Pass full object
        "today_di_status": today_di_status,
        "pending_with": pending_with,
        "today_di_id": today_di_id,
        "distribution_by_type": distribution_by_type,
        "distribution_by_place": distribution_by_place,
        "recent_faults": recent_faults,
        "fault_trend": fault_trend,
        "current_date": date.today(),
        "title": "Command Center"
    })
