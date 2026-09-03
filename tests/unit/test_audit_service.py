"""Unit tests for the AuditService."""

from app.models import AuditAction
from app.services.audit_service import AuditService


class TestAuditService:
    """Tests for AuditService methods."""

    def test_log_action(self, db_session, admin_user):
        """Test creating an audit log entry."""
        log = AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.CREATE,
            entity_type="qualification",
            entity_id=1,
            description="Created qualification",
        )
        assert log.id is not None
        assert log.action == AuditAction.CREATE
        assert log.entity_type == "qualification"
        assert log.description == "Created qualification"

    def test_log_action_with_values(self, db_session, admin_user):
        """Test creating an audit log with old and new values."""
        log = AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.UPDATE,
            entity_type="qualification",
            entity_id=1,
            description="Updated qualification",
            old_values={"title": "Old Title"},
            new_values={"title": "New Title"},
        )
        assert log.old_values is not None
        assert log.new_values is not None
        assert "Old Title" in log.old_values
        assert "New Title" in log.new_values

    def test_search_audit_logs(self, db_session, admin_user):
        """Test searching audit logs."""
        AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.CREATE,
            entity_type="qualification",
            entity_id=1,
            description="Created qualification 1",
        )
        AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.VERIFY,
            entity_type="qualification",
            entity_id=1,
            description="Verified qualification 1",
        )
        result = AuditService.search_audit_logs(db_session)
        assert result.total == 2
        assert len(result.items) == 2

    def test_search_audit_logs_by_action(self, db_session, admin_user):
        """Test filtering audit logs by action."""
        AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.CREATE,
            entity_type="qualification",
            description="Created",
        )
        AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.VERIFY,
            entity_type="qualification",
            description="Verified",
        )
        result = AuditService.search_audit_logs(db_session, action="verify")
        assert result.total == 1
        assert result.items[0].action == AuditAction.VERIFY

    def test_get_audit_log_by_id(self, db_session, admin_user):
        """Test getting a single audit log by ID."""
        log = AuditService.log_action(
            db_session,
            user_id=admin_user.id,
            action=AuditAction.LOGIN,
            entity_type="user",
            description="User logged in",
        )
        found = AuditService.get_audit_log_by_id(db_session, log.id)
        assert found is not None
        assert found.id == log.id

    def test_get_audit_log_not_found(self, db_session):
        """Test getting a nonexistent audit log returns None."""
        result = AuditService.get_audit_log_by_id(db_session, 9999)
        assert result is None
