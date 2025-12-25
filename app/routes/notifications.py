from fastapi import APIRouter, Request, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.notification import Notification
from app.core.auth_guard import require_user
from app.core.notifications import redis_client
import json
import asyncio

router = APIRouter(prefix="/notifications")

@router.get("/list")
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    notifications = db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        } for n in notifications
    ]

@router.post("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    return {"status": "success"}

@router.post("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "success"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"user_notifications_{user_id}")
    
    try:
        while True:
            # Check for new messages in Redis Pub/Sub
            message = pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message['data'])
            
            # Keep connection alive and allow for other tasks
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pubsub.unsubscribe(f"user_notifications_{user_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        pubsub.unsubscribe(f"user_notifications_{user_id}")
