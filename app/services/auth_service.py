"""Authentication service for user management."""

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User, UserRole


class AuthService:
    """Service for authentication and user management operations."""

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        full_name: str,
        password: str,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """Create a new user with hashed password."""
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError("User with this email already exists")

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        """Authenticate a user by email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user_role(db: Session, user_id: int, role: UserRole) -> User | None:
        """Update a user's role."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        user.role = role
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> User | None:
        """Deactivate a user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user
