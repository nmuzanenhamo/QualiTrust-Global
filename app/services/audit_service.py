"""Audit logging service for immutable audit trail."""

import json
import math

from sqlalchemy.orm import Session, Query

from app.models import AuditAction, AuditLog, User
from app.schemas.audit import AuditLogSearchResult


class AuditService:
    """Service for audit log operations."""

    @staticmethod
    def log_action(
        db: Session,
        user_id: int | None,
        action: AuditAction,
        entity_type: str,
        entity_id: int | None = None,
        description: str = "",
        qualification_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
    ) -> AuditLog:
        """Create an immutable audit log entry."""
        audit_log = AuditLog(
            user_id=user_id,
            qualification_id=qualification_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def search_audit_logs(
        db: Session,
        user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        qualification_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogSearchResult:
        """Search audit logs with filters and pagination."""
        q: Query = db.query(AuditLog)

        if user_id:
            q = q.filter(AuditLog.user_id == user_id)

        if action:
            q = q.filter(AuditLog.action == AuditAction(action))

        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)

        if entity_id:
            q = q.filter(AuditLog.entity_id == entity_id)

        if qualification_id:
            q = q.filter(AuditLog.qualification_id == qualification_id)

        if start_date:
            from datetime import datetime as dt
            q = q.filter(AuditLog.created_at >= dt.fromisoformat(start_date))

        if end_date:
            from datetime import datetime as dt
            q = q.filter(AuditLog.created_at <= dt.fromisoformat(end_date))

        total = q.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = q.order_by(AuditLog.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return AuditLogSearchResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_audit_log_by_id(db: Session, log_id: int) -> AuditLog | None:
        """Get a single audit log entry by ID."""
        return db.query(AuditLog).filter(AuditLog.id == log_id).first()
