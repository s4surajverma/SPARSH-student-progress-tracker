"""
School Result Analysis System - FastAPI Dependencies

Reusable dependency functions injected into route handlers.
Provides:
- Database session management
- JWT authentication
- Role-based access control guards
"""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

# OAuth2 scheme — extracts the Bearer token from the Authorization header.
# tokenUrl points to the login endpoint for Swagger UI integration.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ============================================
# Database Dependency
# ============================================

def get_db() -> Generator[Session, None, None]:
    """
    Yields a SQLAlchemy database session for the duration of a single request.
    Automatically closes the session when the request completes,
    preventing connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# Authentication Dependencies
# ============================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the JWT token and retrieve the corresponding User from the database.
    Raises 401 if the token is invalid, expired, or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the authenticated user's account is active.
    Raises 403 if the user has been disabled by an admin.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


# ============================================
# Role-Based Access Control Guards
# ============================================

def require_role(*allowed_roles: str):
    """
    Factory function that creates a role-checking dependency.
    Accepts one or more role strings.

    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...

        @router.get("/admin-or-teacher")
        def shared_endpoint(user: User = Depends(require_role("admin", "teacher"))):
            ...
    """
    def role_guard(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}",
            )
        return current_user
    return role_guard


# --- Convenience shortcuts for common role patterns ---
get_current_admin = require_role("admin")
get_current_teacher = require_role("teacher")
get_current_principal = require_role("principal")
get_current_admin_or_teacher = require_role("admin", "teacher")
