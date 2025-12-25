import contextvars
from sqlalchemy import event
from app.models.audit_log import AuditLog
import json

# Context variable to store current user ID
current_user_id = contextvars.ContextVar("current_user_id", default=None)

def set_audit_user(user_id: int):
    current_user_id.set(user_id)

def get_audit_user():
    return current_user_id.get()

def log_action(db, action: str, target_table: str = None, target_id: str = None, description: str = None):
    # If db is not provided, we create a temporary session
    # but usually we want to use the active session to keep it atomic
    user_id = get_audit_user()
    
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        target_table=target_table,
        target_id=str(target_id) if target_id else None,
        description=description
    )
    db.add(audit_entry)
    # We don't commit here, we let the parent transaction handle it

# SQLAlchemy Listeners
def register_audit_listeners(session_cls):
    @event.listens_for(session_cls, 'after_flush')
    def receive_after_flush(session, flush_context):
        for obj in session.new:
            if isinstance(obj, AuditLog):
                continue
            
            log_action(
                session, 
                "CREATE", 
                target_table=obj.__tablename__, 
                target_id=getattr(obj, 'id', None),
                description=f"Created new {obj.__tablename__} entry"
            )

        for obj in session.dirty:
            if isinstance(obj, AuditLog):
                continue
            
            # Simple diff for update description
            changed_attrs = []
            for attr in obj.__mapper__.attrs:
                # Use history to see what changed
                history = getattr(getattr(obj, attr.key), 'history', None)
                # This is a bit complex for a generic listener without more specialized logic
                # So we just log the update for now
                pass

            log_action(
                session, 
                "UPDATE", 
                target_table=obj.__tablename__, 
                target_id=getattr(obj, 'id', None),
                description=f"Updated {obj.__tablename__} (ID: {getattr(obj, 'id', 'N/A')})"
            )

        for obj in session.deleted:
            if isinstance(obj, AuditLog):
                continue
                
            log_action(
                session, 
                "DELETE", 
                target_table=obj.__tablename__, 
                target_id=getattr(obj, 'id', None),
                description=f"Deleted {obj.__tablename__} (ID: {getattr(obj, 'id', 'N/A')})"
            )
