from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.core.auth_guard import require_user
from app.core.audit import log_action

router = APIRouter(prefix="/audit")
templates = Jinja2Templates(directory="app/templates")

def sysadmin_required(user=Depends(require_user)):
    if not user.role or user.role.name.lower() != 'sysadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator access required"
        )
    return user

@router.get("/list")
def list_audit_logs(
    request: Request, 
    db: Session = Depends(get_db), 
    user=Depends(sysadmin_required)
):
    # Log the fetch action itself
    log_action(db, "FETCH", target_table="audit_logs", description="System administrator accessed audit logs")
    db.commit() # Need to commit the fetch log

    page = int(request.query_params.get("page", 1))
    per_page = 20
    
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    
    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return templates.TemplateResponse("audit_logs.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "page": page,
        "per_page": per_page,
        "total": total,
        "title": "Security Audit Trail"
    })
