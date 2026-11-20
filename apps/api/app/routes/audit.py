from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_user, ensure_manager
from app.models import AuditEvent, Role, User

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("")
def audit_history(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    if user.role == Role.hod:
        # Audit records do not currently carry a department id. Only expose actions
        # performed by accounts assigned to this HOD's own department.
        query = (select(AuditEvent, User.full_name, User.email)
                 .outerjoin(User, AuditEvent.actor_id == User.id)
                 .where(User.department_id == user.department_id))
    elif user.role == Role.super_admin:
        query = select(AuditEvent, User.full_name, User.email).outerjoin(User, AuditEvent.actor_id == User.id)
    else:
        query = (select(AuditEvent, User.full_name, User.email)
                 .outerjoin(User, AuditEvent.actor_id == User.id)
                 .where(AuditEvent.institution_id == user.institution_id))
    rows = db.execute(query.order_by(AuditEvent.created_at.desc()).limit(200)).all()
    return [{"id": str(event.id), "action": event.action, "resource_type": event.resource_type,
             "resource_id": event.resource_id, "actor": name or "Former account",
             "actor_email": email, "created_at": event.created_at}
            for event, name, email in rows]
