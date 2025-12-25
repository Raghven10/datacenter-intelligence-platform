import redis
import json
from sqlalchemy.orm import Session
from app.models.notification import Notification
import os

# Redis connection from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class NotificationManager:
    @staticmethod
    def create_notification(db: Session, user_id: int, title: str, message: str, type: str = "info"):
        # 1. Save to Database
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # 2. Publish to Redis for real-time delivery
        payload = {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "created_at": notification.created_at.isoformat()
        }
        try:
            redis_client.publish(f"user_notifications_{user_id}", json.dumps(payload))
        except Exception as e:
            print(f"Failed to publish to Redis: {e}")
        
        return notification

    @staticmethod
    def broadcast_to_role(db: Session, role_name: str, title: str, message: str, type: str = "info"):
        from app.models.user import User
        from app.models.role import Role
        
        # Find all users with this role (case-insensitive)
        users = db.query(User).join(User.roles).filter(Role.name.ilike(role_name)).all()
        # Also check primary role for backward compatibility
        primary_users = db.query(User).join(Role, User.role_id == Role.id).filter(Role.name.ilike(role_name)).all()
        
        all_users = set(users) | set(primary_users)
        
        for user in all_users:
            NotificationManager.create_notification(db, user.id, title, message, type)
