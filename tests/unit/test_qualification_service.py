"""Unit tests for the QualificationService."""

import pytest

from app.models import QualificationStatus, QualificationType
from app.schemas.qualification import QualificationCreate, QualificationUpdate
from app.services.qualification_service import QualificationService


class TestQualificationService:
    """Tests for QualificationService methods."""

    def test_create_qualification(self, db_session, admin_user):
        """Test creating a qualification."""
        data = QualificationCreate(
            title="Test Degree",
            qualification_type="degree",
            issuing_institution="Test University",
            holder_name="Test Holder",
            holder_email="holder@test.com",
            holder_id_number="ID123",
            date_issued="2020-01-01T00:00:00",
            registration_number="REG001",
            serial_number="SN001",
        )
        qual = QualificationService.create_qualification(db_session, data, admin_user)
        assert qual.id is not None
        assert qual.title == "Test Degree"
        assert qual.status == QualificationStatus.PENDING
        assert qual.registered_by == admin_user.id

    def test_get_qualification_by_id(self, db_session, admin_user, sample_qualification_data):
        """Test getting a qualification by ID."""
        data = QualificationCreate(**sample_qualification_data)
        created = QualificationService.create_qualification(db_session, data, admin_user)
        found = QualificationService.get_qualification(db_session, created.id)
        assert found is not None
        assert found.title == sample_qualification_data["title"]

    def test_get_qualification_not_found(self, db_session):
        """Test getting a nonexistent qualification returns None."""
        result = QualificationService.get_qualification(db_session, 9999)
        assert result is None

    def test_search_qualifications(self, db_session, admin_user, sample_qualification_data):
        """Test searching qualifications."""
        data = QualificationCreate(**sample_qualification_data)
        QualificationService.create_qualification(db_session, data, admin_user)
        result = QualificationService.search_qualifications(db_session, query="Computer")
        assert result.total == 1
        assert len(result.items) == 1
        assert result.page == 1

    def test_search_qualifications_empty(self, db_session):
        """Test searching with no results."""
        result = QualificationService.search_qualifications(db_session, query="nonexistent")
        assert result.total == 0
        assert len(result.items) == 0

    def test_search_qualifications_by_type(self, db_session, admin_user, sample_qualification_data):
        """Test filtering by qualification type."""
        data = QualificationCreate(**sample_qualification_data)
        QualificationService.create_qualification(db_session, data, admin_user)
        result = QualificationService.search_qualifications(db_session, qualification_type="degree")
        assert result.total == 1

    def test_update_qualification(self, db_session, admin_user, sample_qualification_data):
        """Test updating a qualification."""
        data = QualificationCreate(**sample_qualification_data)
        created = QualificationService.create_qualification(db_session, data, admin_user)
        update = QualificationUpdate(title="Updated Title")
        updated = QualificationService.update_qualification(db_session, created.id, update)
        assert updated.title == "Updated Title"

    def test_update_qualification_not_found(self, db_session):
        """Test updating a nonexistent qualification returns None."""
        update = QualificationUpdate(title="Updated")
        result = QualificationService.update_qualification(db_session, 9999, update)
        assert result is None

    def test_soft_delete_qualification(self, db_session, admin_user, sample_qualification_data):
        """Test soft deleting a qualification."""
        data = QualificationCreate(**sample_qualification_data)
        created = QualificationService.create_qualification(db_session, data, admin_user)
        deleted = QualificationService.soft_delete_qualification(db_session, created.id)
        assert deleted is True
        found = QualificationService.get_qualification(db_session, created.id)
        assert found is None

    def test_soft_delete_not_found(self, db_session):
        """Test soft deleting a nonexistent qualification returns False."""
        result = QualificationService.soft_delete_qualification(db_session, 9999)
        assert result is False
