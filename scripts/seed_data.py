"""Seed script to populate the database with initial data."""

from datetime import datetime

from app.core.database import Base, SessionLocal, engine
from app.models import Qualification, QualificationStatus, QualificationType, User, UserRole
from app.services.auth_service import AuthService


def seed_database():
    """Populate the database with seed data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if data already exists
    if db.query(User).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    # Create admin user
    admin = AuthService.create_user(
        db,
        email="admin@qvs.edu",
        full_name="System Administrator",
        password="Admin@123",
        role=UserRole.ADMIN,
    )

    # Create verifier user
    verifier = AuthService.create_user(
        db,
        email="verifier@qvs.edu",
        full_name="Test Verifier",
        password="Verifier@123",
        role=UserRole.VERIFIER,
    )

    # Create sample qualifications
    qualifications = [
        Qualification(
            title="Bachelor of Science in Computer Science",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Midlands State University",
            holder_name="John Doe",
            holder_email="john.doe@example.com",
            holder_id_number="ID123456",
            date_issued=datetime(2020, 6, 15),
            registration_number="CS2020/001",
            serial_number="MSU-CS-2020-001",
            description="Four-year undergraduate degree in Computer Science",
            status=QualificationStatus.VERIFIED,
            registered_by=admin.id,
        ),
        Qualification(
            title="Master of Commerce in Information Systems Management",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Midlands State University",
            holder_name="Jane Smith",
            holder_email="jane.smith@example.com",
            holder_id_number="ID789012",
            date_issued=datetime(2023, 11, 30),
            registration_number="IS2023/045",
            serial_number="MSU-IS-2023-045",
            description="Postgraduate degree in Information Systems Management",
            status=QualificationStatus.PENDING,
            registered_by=admin.id,
        ),
        Qualification(
            title="AWS Certified Solutions Architect",
            qualification_type=QualificationType.PROFESSIONAL_CERTIFICATION,
            issuing_institution="Amazon Web Services",
            holder_name="Bob Wilson",
            holder_email="bob.wilson@example.com",
            holder_id_number="ID345678",
            date_issued=datetime(2024, 3, 10),
            date_expires=datetime(2027, 3, 10),
            registration_number="AWS-SA-2024-789",
            serial_number="AWS-SA-2024-789",
            description="Professional certification for AWS cloud architecture",
            status=QualificationStatus.VERIFIED,
            registered_by=verifier.id,
        ),
    ]

    for q in qualifications:
        db.add(q)

    db.commit()
    print(f"Seeded database with {len(qualifications)} qualifications and 2 users.")
    db.close()


if __name__ == "__main__":
    seed_database()
