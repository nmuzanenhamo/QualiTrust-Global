"""Qualification service for CRUD operations and business logic."""

import math

from sqlalchemy.orm import Session, Query

from app.models import Qualification, QualificationStatus, QualificationType, User
from app.schemas.qualification import (
    QualificationCreate,
    QualificationSearchResult,
    QualificationUpdate,
)


class QualificationService:
    """Service for qualification CRUD operations."""

    @staticmethod
    def create_qualification(
        db: Session,
        qualification_data: QualificationCreate,
        user: User,
    ) -> Qualification:
        """Register a new qualification."""
        qualification = Qualification(
            title=qualification_data.title,
            qualification_type=QualificationType(qualification_data.qualification_type),
            issuing_institution=qualification_data.issuing_institution,
            holder_name=qualification_data.holder_name,
            holder_email=qualification_data.holder_email,
            holder_id_number=qualification_data.holder_id_number,
            date_issued=qualification_data.date_issued,
            date_expires=qualification_data.date_expires,
            registration_number=qualification_data.registration_number,
            serial_number=qualification_data.serial_number,
            description=qualification_data.description,
            status=QualificationStatus.PENDING,
            registered_by=user.id,
        )
        db.add(qualification)
        db.commit()
        db.refresh(qualification)
        return qualification

    @staticmethod
    def get_qualification(db: Session, qualification_id: int) -> Qualification | None:
        """Get a qualification by ID (excludes soft-deleted)."""
        return (
            db.query(Qualification)
            .filter(Qualification.id == qualification_id, Qualification.is_deleted == False)
            .first()
        )

    @staticmethod
    def search_qualifications(
        db: Session,
        query: str | None = None,
        qualification_type: str | None = None,
        status: str | None = None,
        issuing_institution: str | None = None,
        holder_name: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> QualificationSearchResult:
        """Search and retrieve qualification records with pagination."""
        q: Query = db.query(Qualification).filter(Qualification.is_deleted == False)

        if query:
            q = q.filter(
                Qualification.title.ilike(f"%{query}%")
                | Qualification.holder_name.ilike(f"%{query}%")
                | Qualification.registration_number.ilike(f"%{query}%")
                | Qualification.serial_number.ilike(f"%{query}%")
            )

        if qualification_type:
            q = q.filter(Qualification.qualification_type == QualificationType(qualification_type))

        if status:
            q = q.filter(Qualification.status == QualificationStatus(status))

        if issuing_institution:
            q = q.filter(Qualification.issuing_institution.ilike(f"%{issuing_institution}%"))

        if holder_name:
            q = q.filter(Qualification.holder_name.ilike(f"%{holder_name}%"))

        total = q.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = q.order_by(Qualification.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return QualificationSearchResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_qualification(
        db: Session,
        qualification_id: int,
        update_data: QualificationUpdate,
    ) -> Qualification | None:
        """Update a qualification record."""
        qualification = QualificationService.get_qualification(db, qualification_id)
        if not qualification:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)

        if "qualification_type" in update_dict and update_dict["qualification_type"]:
            update_dict["qualification_type"] = QualificationType(update_dict["qualification_type"])

        if "status" in update_dict and update_dict["status"]:
            update_dict["status"] = QualificationStatus(update_dict["status"])

        for field, value in update_dict.items():
            setattr(qualification, field, value)

        db.commit()
        db.refresh(qualification)
        return qualification

    @staticmethod
    def soft_delete_qualification(db: Session, qualification_id: int) -> bool:
        """Soft delete a qualification."""
        qualification = QualificationService.get_qualification(db, qualification_id)
        if not qualification:
            return False
        qualification.is_deleted = True
        db.commit()
        return True
