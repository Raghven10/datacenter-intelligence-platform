from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date

from app.db.session import get_db
from app.core.auth_guard import require_user
from fastapi.templating import Jinja2Templates

from app.models.daily_inspection import DailyInspection
from app.models.di_workflow import DIWorkflow
from app.models.equipment import Equipment
from app.models.di_equipment_log import DIEquipmentLog
from app.core.notifications import NotificationManager
from app.models.role import Role
from app.models.user import User
from sqlalchemy import func

import datetime
router = APIRouter(prefix="/di", tags=["Daily Inspection"])
templates = Jinja2Templates(directory="app/templates")

# -------------------------
# DI FLOW CONFIG
# -------------------------
DI_FLOW = {
    "submitted": "oic elect",
    "oic elect_approved": "oic datashell",
    "oic datashell_approved": "cdo",
    "cdo_approved": "completed"
}

# -------------------------
# DI FORM
# -------------------------
@router.get("/form")
def di_form(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    # Fetch all equipments grouped by place
    equipments = db.query(Equipment).join(Equipment.place).order_by(Equipment.place_id).all()
    
    # Group equipments by place
    places = {}
    for eq in equipments:
        if eq.place_id not in places:
            places[eq.place_id] = {
                "name": eq.place.name if eq.place else "Unknown",
                "equipments": []
            }
        places[eq.place_id]["equipments"].append(eq)

    # Fetch potential escalation users (Role: OIC Elect)
    # The first level after operator/submission is OIC Elect as per DI_FLOW
    from sqlalchemy import func
    from app.models.user import User
    next_role_name = DI_FLOW.get("submitted")
    oic_role = db.query(Role).filter(func.lower(Role.name) == next_role_name.lower()).first()
    oic_users = []
    if oic_role:
        oic_users = db.query(User).filter(
            (User.role_id == oic_role.id) | 
            (User.roles.any(id=oic_role.id))
        ).all()

    return templates.TemplateResponse(
        "di_form.html",
        {
            "request": request,
            "user": user,
            "places": places,
            "oic_users": oic_users,
            "next_role": next_role_name.upper()
        }
    )

@router.post("/form")
async def submit_di(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    form = await request.form()
    
    # Create DI entry
    di = DailyInspection(
        inspection_date=date.today(),
        created_by=user.id,
        status="submitted",
        final_remarks=form.get("final_remarks"),
        forwarded_to=form.get("forwarded_to")
    )
    db.add(di)
    db.commit()
    db.refresh(di)
    
    # Loop through equipments and save logs
    # Form keys expected: 
    # serviceability_{id}, status_{id}, cleaning_{id}, remarks_{id}
    # Optional: pressure_{id}, temperature_{id}, etc.
    
    # We iterate over keys to find IDs
    processed_ids = set()
    for key in form.keys():
        if key.startswith("serviceability_"):
            eq_id = int(key.split("_")[1])
            if eq_id in processed_ids:
                continue
            processed_ids.add(eq_id)
            
            serviceability = form.get(f"serviceability_{eq_id}")
            status_val = form.get(f"status_{eq_id}")
            cleaning = form.get(f"cleaning_{eq_id}")
            remarks = form.get(f"remarks_{eq_id}", "")
            
            # Optional fields
            def get_float(k):
                val = form.get(f"{k}_{eq_id}")
                return float(val) if val else None
                
            log = DIEquipmentLog(
                di_id=di.id,
                equipment_id=eq_id,
                serviceability=serviceability,
                status=status_val,
                cleaning_status=cleaning,
                remarks=remarks,
                pressure=get_float("pressure"),
                temperature=get_float("temperature"),
                humidity=get_float("humidity"),
                voltage=get_float("voltage"),
                frequency=get_float("frequency"),
                resistance=get_float("resistance")
            )
            db.add(log)
            
            # Update Equipment Table with latest status
            eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
            if eq:
                eq.serviceability = serviceability
                eq.status = status_val
                
                # Trigger buzzer/alert if marked US during DI
                if serviceability == "US":
                    NotificationManager.broadcast_to_role(db, "sysadmin", "Critical Asset Alert", 
                                                          f"Asset '{eq.name}' has been marked as UNSERVICEABLE during daily inspection by {user.username}.", "error")
    
    db.commit()

    # Notify Supervisor/Next Role
    target = form.get("forwarded_to")
    NotificationManager.broadcast_to_role(db, "supervisor", "New DI Report Submitted", 
                                          f"A new inspection report has been submitted by {user.username} and is pending review.", "info")
    
    # If a specific user was selected, also notify them directly
    target_user = db.query(User).filter(User.username == target).first()
    if target_user:
        NotificationManager.create_notification(db, target_user.id, "DI Report Escalated to You",
                                                f"A new DI report from {user.username} has been escalated to you for review.", "info")

    db.commit()

    return RedirectResponse(f"/di/view/{di.id}", status_code=302)

@router.get("/view/{di_id}")
def view_di(
    di_id: int,
    request: Request,
    embed: int = 0,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    di = db.query(DailyInspection).filter(DailyInspection.id == di_id).first()
    if not di:
        raise HTTPException(status_code=404, detail="DI not found")

    # Fetch logs and group by place
    logs = db.query(DIEquipmentLog).filter(DIEquipmentLog.di_id == di.id).all()
    
    # We need to structure it like the form: places with equipments and their logs
    # Fetch all equipments grouped by place
    equipments = db.query(Equipment).join(Equipment.place).order_by(Equipment.place_id).all()
    
    places = {}
    log_map = {l.equipment_id: l for l in logs}
    
    for eq in equipments:
        if eq.place_id not in places:
            places[eq.place_id] = {
                "name": eq.place.name if eq.place else "Unknown",
                "equipments": []
            }
        # Attach the log for this DI to the equipment object for easy access in template
        eq.log = log_map.get(eq.id)
        places[eq.place_id]["equipments"].append(eq)

    # Authorization check for reviewer
    can_act = False
    if di.status not in ["completed", "rejected"]:
        # Check if user matches the forwarded_to (either username or role)
        is_target_user = (user.username == di.forwarded_to)
        is_target_role = user.has_role(di.forwarded_to)
        if is_target_user or is_target_role:
            can_act = True

    # Determine next potential roles/users for escalation dropdown
    next_users = []
    next_role_name = None
    if can_act:
        flow_key = f"{di.status}_approved"
        if di.status == "submitted":
            flow_key = "oic elect_approved"
        
        next_role_name = DI_FLOW.get(flow_key)
        
        if next_role_name and next_role_name != "completed":
            role_obj = db.query(Role).filter(func.lower(Role.name) == next_role_name.lower()).first()
            if role_obj:
                next_users = db.query(User).filter(
                    (User.role_id == role_obj.id) | 
                    (User.roles.any(id=role_obj.id))
                ).all()

    return templates.TemplateResponse(
        "di_view.html",
        {
            "request": request,
            "user": user,
            "di": di,
            "places": places,
            "embed": embed == 1,
            "can_act": can_act,
            "next_users": next_users,
            "next_role": next_role_name.upper() if next_role_name else None
        }
    )

@router.get("/print/{di_id}")
def print_di(
    di_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    di = db.query(DailyInspection).filter(DailyInspection.id == di_id).first()
    if not di:
        raise HTTPException(status_code=404, detail="DI not found")

    logs = db.query(DIEquipmentLog).filter(DIEquipmentLog.di_id == di.id).all()
    equipments = db.query(Equipment).join(Equipment.place).order_by(Equipment.place_id).all()
    
    places = {}
    log_map = {l.equipment_id: l for l in logs}
    
    for eq in equipments:
        if eq.place_id not in places:
            places[eq.place_id] = {
                "name": eq.place.name if eq.place else "Unknown",
                "equipments": []
            }
        eq.log = log_map.get(eq.id)
        places[eq.place_id]["equipments"].append(eq)

    return templates.TemplateResponse(
        "di_print.html",
        {
            "request": request,
            "user": user,
            "di": di,
            "places": places
        }
    )

# -------------------------
# CREATE DI
# -------------------------
@router.post("/create")
def create_di(
    inspection_date: date = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    di = DailyInspection(
        inspection_date=inspection_date,
        created_by=user.id,
        status="submitted",
    )
    db.add(di)
    db.commit()
    db.refresh(di)

    return RedirectResponse("/di/list", status_code=302)

# -------------------------
# LIST DI
# -------------------------
@router.get("/list")
def list_di(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    di_list = db.query(DailyInspection).order_by(
        DailyInspection.created_at.desc()
    ).all()

    return templates.TemplateResponse(
        "di_list.html",
        {
            "request": request,
            "user": user,
            "di_list": di_list,
        }
    )

# -------------------------
# APPROVE DI
# -------------------------
@router.post("/workflow/approve/{di_id}")
def approve_di(
    di_id: int,
    comments: str = Form(None),
    escalate_to: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    di = db.query(DailyInspection).filter_by(id=di_id).first()
    if not di:
        raise HTTPException(404, "DI not found")

    # Determine status transition
    current_status = di.status
    flow_key = f"{current_status}_approved"
    if current_status == "submitted":
        flow_key = "oic elect_approved" # If OIC Elect approved the 'submitted' report
        
    next_role = DI_FLOW.get(flow_key)
    
    # Update Status
    if next_role == "completed":
        di.status = "completed"
        di.forwarded_to = "Completed"
    elif next_role:
        di.status = flow_key # e.g. "oic elect_approved"
        # Use user-selected escalation if provided, otherwise the role name
        di.forwarded_to = escalate_to if escalate_to else next_role
    else:
        # Last resort - check if CDO is acting
        if user.has_role("cdo"):
             di.status = "completed"
             di.forwarded_to = "Completed"
        else:
            di.status = "approved"
            di.forwarded_to = "Reviewer"

    # Log workflow
    wf = DIWorkflow(
        di_id=di.id,
        from_role=user.role.name if user.role else "Reviewer",
        to_role=di.forwarded_to,
        action="approved",
        comments=comments,
        acted_by=user.id
    )
    db.add(wf)
    
    # Notifications
    NotificationManager.create_notification(db, di.created_by, "DI Report Update", 
                                            f"Your report from {di.inspection_date} was approved/advanced by {user.username}.", "success")
    
    if di.status != "completed":
        # Notify the next forwarded entity (could be role or user)
        target_user = db.query(User).filter(User.username == di.forwarded_to).first()
        if target_user:
            NotificationManager.create_notification(db, target_user.id, "DI Pending Review",
                                                    f"A DI report has been escalated to you by {user.username}.", "info")
        else:
            NotificationManager.broadcast_to_role(db, di.forwarded_to, "Pending DI Approval", 
                                                  f"A DI report is pending review for role: {di.forwarded_to}.", "info")

    db.commit()
    return RedirectResponse("/di/tracking", status_code=302)

# -------------------------
# REJECT DI
# -------------------------
@router.post("/workflow/reject/{di_id}")
def reject_di(
    di_id: int,
    comments: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    di = db.query(DailyInspection).filter_by(id=di_id).first()
    if not di:
        raise HTTPException(404, "DI not found")

    wf = DIWorkflow(
        di_id=di.id,
        from_role=user.role.name,
        to_role="creator",
        action="rejected",
        comments=comments,
        acted_by=user.id,
    )

    db.add(wf)
    di.status = "rejected"
    
    # Notify creator
    NotificationManager.create_notification(db, di.created_by, "DI Report Rejected", 
                                            f"Your report from {di.inspection_date} was rejected by {user.username}. Comments: {comments}", "error")
    
    db.commit()

    return RedirectResponse("/di/list", status_code=302)


# -------------------------
# WORKFLOW TRACKING
# -------------------------
@router.get("/tracking")
def di_tracking(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    # Fetch all DIs with their workflow history
    di_list = db.query(DailyInspection).order_by(DailyInspection.created_at.desc()).all()
    
    return templates.TemplateResponse("di_tracking.html", {
        "request": request,
        "user": user,
        "di_list": di_list
    })


# -------------------------
# WORKFLOW NUDGE (NOTIFICATION)
# -------------------------
@router.post("/nudge/{di_id}")
def nudge_personnel(
    di_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    di = db.query(DailyInspection).filter(DailyInspection.id == di_id).first()
    if not di:
        raise HTTPException(status_code=404, detail="DI entry not found")
        
    if not di.forwarded_to or di.status in ["completed", "rejected"]:
        raise HTTPException(status_code=400, detail="Cannot nudge this report in its current state")
        
    # Send notification to the role currently holding the DI
    target_role = di.forwarded_to
    
    NotificationManager.broadcast_to_role(
        db, 
        role_name=target_role,
        title="DI Report Pending Action",
        message=f"DI Report Date: {di.inspection_date} is pending your review/action. Sent by {user.username}.",
        type="warning"
    )
    
    if "application/json" in request.headers.get("accept", ""):
        return {"message": f"Nudge sent to {target_role}"}
        
    return RedirectResponse("/di/tracking", status_code=302)
