import json
from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.audit_log import AuditLog

class AuditService:
    @staticmethod
    def log(action: str, entity_type: str = None, entity_id: int = None, details: dict = None):
        try:
            user_id = current_user.id if current_user and current_user.is_authenticated else None
            ip = request.remote_addr if request else None

            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=json.dumps(details, ensure_ascii=False) if details else None,
                ip_address=ip
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            db.session.rollback()
