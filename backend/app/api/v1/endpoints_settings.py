"""
SPARSH - Storage Settings Endpoints

Admin-only endpoints for configuring the file storage backend.
Supports Google Drive via OAuth 2.0 User Authorization.

User-facing messages are kept non-technical.
All developer-facing details are logged server-side only.
"""

import io
import logging
import re
import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin
from app.models.app_settings import AppSettings
from app.models.user import User
from app.core.config import settings
from app.core.encryption import encrypt_string, decrypt_string
from app.schemas.settings_schema import (
    StorageSettingsResponse,
    StorageVerifyRequest,
    StorageVerifyResponse,
    StorageTestUploadResponse,
    StorageSaveRequest,
    DriveAvailabilityResponse,
    OAuthStartResponse,
    OAuthCallbackResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Full scope required because 'drive.file' cannot read folders created manually by the user
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "openid",
    "email",
]

# Regex to extract folder ID from various Google Drive URL formats
FOLDER_URL_PATTERN = re.compile(
    r"(?:https?://)?drive\.google\.com/(?:drive/)?(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)"
)


# ============================================
# Internal Helpers
# ============================================

def _get_or_create_settings(db: Session) -> AppSettings:
    """
    Get the first AppSettings row.
    If none exists, create one automatically with defaults.
    """
    row = db.query(AppSettings).first()
    if not row:
        row = AppSettings(storage_provider="google_drive")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _extract_folder_id(url: str) -> str | None:
    """Extract a Google Drive folder ID from a URL string."""
    match = FOLDER_URL_PATTERN.search(url.strip())
    if match:
        return match.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{10,}$", url.strip()):
        return url.strip()
    return None


def _is_oauth_configured() -> bool:
    """Check whether the developer has configured Google OAuth credentials."""
    return bool(settings.GOOGLE_CLIENT_ID) and bool(settings.GOOGLE_CLIENT_SECRET)


def _get_oauth_credentials(db: Session):
    """
    Build Google OAuth Credentials from the stored refresh token.
    Returns a google.oauth2.credentials.Credentials object.
    Raises RuntimeError if credentials are missing or invalid.
    """
    row = _get_or_create_settings(db)

    if not row.google_oauth_refresh_token_encrypted:
        raise RuntimeError("Google Drive is not connected. Please connect via OAuth first.")

    try:
        from google.oauth2.credentials import Credentials

        refresh_token = decrypt_string(row.google_oauth_refresh_token_encrypted)

        creds = Credentials(
            token=None,  # Will be refreshed automatically
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=DRIVE_SCOPES,
        )
        return creds
    except Exception as e:
        logger.error(f"Failed to build OAuth credentials: {e}", exc_info=True)
        raise RuntimeError("Failed to load Google Drive credentials. Please reconnect.")


def _get_drive_service(db: Session):
    """
    Build and return a Google Drive API service using OAuth credentials.
    """
    creds = _get_oauth_credentials(db)

    try:
        from googleapiclient.discovery import build

        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build Drive service: {e}", exc_info=True)
        raise RuntimeError("Failed to connect to Google Drive. Please try reconnecting.")


# ============================================
# GET — Google Drive Availability Check
# ============================================

@router.get("/storage/drive-availability", response_model=DriveAvailabilityResponse)
def check_drive_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Lightweight check: is Google Drive OAuth configured by the developer?
    """
    available = _is_oauth_configured()
    return DriveAvailabilityResponse(
        google_drive_available=available,
        message=None if available else (
            "Google Drive integration is not configured on this server. "
            "The developer must set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        ),
    )


# ============================================
# GET — Current Storage Status
# ============================================

@router.get("/storage", response_model=StorageSettingsResponse)
def get_storage_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Return the current storage configuration and connection status."""
    row = _get_or_create_settings(db)

    return StorageSettingsResponse(
        storage_provider=row.storage_provider,
        google_drive_connected=bool(row.google_oauth_refresh_token_encrypted),
        google_user_email=row.google_user_email,
        folder_url_saved=bool(row.drive_folder_id),
        drive_folder_id=row.drive_folder_id,
        last_verified_at=row.last_verified_at,
        last_successful_upload_at=row.last_successful_upload_at,
        updated_at=row.updated_at,
    )


# ============================================
# GET — Start OAuth Flow
# ============================================

@router.get("/storage/oauth/start", response_model=OAuthStartResponse)
def start_oauth_flow(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Generate the Google OAuth authorization URL.
    The frontend should open this URL in a new window/tab.
    """
    if not _is_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server.",
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(DRIVE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": "sparsh_drive_connect",
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return OAuthStartResponse(auth_url=auth_url)


# ============================================
# GET — OAuth Callback (Google redirects here)
# ============================================

@router.get("/storage/oauth/callback")
async def oauth_callback(
    code: str = Query(None),
    error: str = Query(None),
    state: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Google redirects here after user grants (or denies) permission.
    Exchanges the auth code for tokens, stores the refresh token,
    and redirects back to the dashboard.
    """
    # Base URL for the dashboard
    dashboard_url = "/dashboard.html"
    hash_fragment = "#storage-settings"

    if error:
        logger.warning(f"OAuth denied by user: {error}")
        return RedirectResponse(
            url=f"{dashboard_url}?oauth_error={urllib.parse.quote(error)}{hash_fragment}"
        )

    if not code:
        return RedirectResponse(
            url=f"{dashboard_url}?oauth_error=no_code_received{hash_fragment}"
        )

    try:
        import httpx

        # Exchange authorization code for tokens
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data=token_data)
            token_json = token_resp.json()

        if "error" in token_json:
            logger.error(f"Token exchange failed: {token_json}")
            return RedirectResponse(
                url=f"{dashboard_url}?oauth_error=token_exchange_failed{hash_fragment}"
            )

        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")

        if not refresh_token:
            logger.error("No refresh token received from Google. Missing access_type=offline or prompt=consent?")
            return RedirectResponse(
                url=f"{dashboard_url}?oauth_error=no_refresh_token{hash_fragment}"
            )

        # Get user info (email) using the access token
        async with httpx.AsyncClient() as client:
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo = userinfo_resp.json()

        user_email = userinfo.get("email", "unknown@gmail.com")

        # Store encrypted refresh token in DB
        row = _get_or_create_settings(db)
        row.google_oauth_refresh_token_encrypted = encrypt_string(refresh_token)
        row.google_user_email = user_email
        row.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Google Drive connected for user: {user_email}")

        return RedirectResponse(
            url=f"{dashboard_url}?oauth_success=true&email={urllib.parse.quote(user_email)}{hash_fragment}"
        )

    except Exception as e:
        logger.error(f"OAuth callback processing failed: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{dashboard_url}?oauth_error=server_error{hash_fragment}"
        )


# ============================================
# POST — Disconnect Google Drive
# ============================================

@router.post("/storage/oauth/disconnect", response_model=OAuthCallbackResponse)
def disconnect_google_drive(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Disconnect Google Drive by clearing stored OAuth tokens.
    """
    row = _get_or_create_settings(db)
    row.google_oauth_refresh_token_encrypted = None
    row.google_user_email = None
    row.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Google Drive disconnected by admin: {current_user.username}")

    return OAuthCallbackResponse(
        success=True,
        message="Google Drive has been disconnected.",
    )


# ============================================
# POST — Verify Folder Access
# ============================================

@router.post("/storage/verify", response_model=StorageVerifyResponse)
def verify_folder(
    request: StorageVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Verify that the connected Google account can access the given Drive folder.
    """
    folder_id = _extract_folder_id(request.folder_url)
    if not folder_id:
        return StorageVerifyResponse(
            verified=False,
            message="Invalid Google Drive folder URL. Please paste the full URL from your browser.",
        )

    try:
        service = _get_drive_service(db)
    except RuntimeError as e:
        return StorageVerifyResponse(verified=False, message=str(e))

    try:
        folder_meta = service.files().get(
            fileId=folder_id,
            fields="id,name,mimeType",
        ).execute()

        if folder_meta.get("mimeType") != "application/vnd.google-apps.folder":
            return StorageVerifyResponse(
                verified=False,
                folder_id=folder_id,
                message="The URL does not point to a Google Drive folder.",
            )

        # Update last_verified_at in DB
        row = _get_or_create_settings(db)
        row.last_verified_at = datetime.now(timezone.utc)
        db.commit()

        return StorageVerifyResponse(
            verified=True,
            folder_id=folder_id,
            folder_name=folder_meta.get("name"),
            message="Folder verified successfully.",
        )

    except Exception as e:
        logger.warning(f"Folder verification failed for ID '{folder_id}': {e}")
        error_str = str(e).lower()

        if "404" in error_str or "not found" in error_str:
            return StorageVerifyResponse(
                verified=False,
                folder_id=folder_id,
                message=(
                    "Cannot access this folder. The folder may not exist, "
                    "or you don't have permission to view it."
                ),
            )

        return StorageVerifyResponse(
            verified=False,
            folder_id=folder_id,
            message="Cannot access this folder. Please check the URL and try again.",
        )


# ============================================
# POST — Test Upload
# ============================================

@router.post("/storage/test-upload", response_model=StorageTestUploadResponse)
def test_upload(
    request: StorageVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Perform a test upload to the verified Google Drive folder.
    Uses the connected admin's OAuth credentials.
    """
    folder_id = _extract_folder_id(request.folder_url)
    if not folder_id:
        return StorageTestUploadResponse(
            success=False,
            message="Invalid Google Drive folder URL.",
        )

    try:
        service = _get_drive_service(db)
    except RuntimeError as e:
        return StorageTestUploadResponse(success=False, message=str(e))

    try:
        from googleapiclient.http import MediaIoBaseUpload

        test_content = b"SPARSH Storage Test - This file can be safely deleted."
        media = MediaIoBaseUpload(
            io.BytesIO(test_content),
            mimetype="text/plain",
            resumable=False,
        )
        file_metadata = {
            "name": "_sparsh_test_upload.txt",
            "parents": [folder_id],
        }

        created_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name",
        ).execute()

        test_file_id = created_file.get("id")

        # Clean up test file
        try:
            service.files().delete(fileId=test_file_id).execute()
        except Exception as del_err:
            logger.warning(f"Could not delete test file: {del_err}")

        # Update last_successful_upload_at in DB
        row = _get_or_create_settings(db)
        row.last_successful_upload_at = datetime.now(timezone.utc)
        db.commit()

        return StorageTestUploadResponse(
            success=True,
            message="Test upload successful! SPARSH can upload files to this folder.",
        )

    except Exception as e:
        logger.error(f"Test upload failed: {e}", exc_info=True)

        return StorageTestUploadResponse(
            success=False,
            message="Test upload failed. Please ensure you have access to this folder and try again.",
        )


# ============================================
# PUT — Save Storage Settings
# ============================================

@router.put("/storage", response_model=StorageSettingsResponse)
def save_storage_settings(
    request: StorageSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Save storage configuration to the database."""
    if request.storage_provider != "google_drive":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage provider must be 'google_drive'.",
        )

    if not request.drive_folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A verified Google Drive folder is required.",
        )

    row = _get_or_create_settings(db)
    row.storage_provider = "google_drive"
    row.drive_folder_id = request.drive_folder_id
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)

    logger.info(f"Storage settings updated by {current_user.username}: provider={row.storage_provider}")

    return StorageSettingsResponse(
        storage_provider=row.storage_provider,
        google_drive_connected=bool(row.google_oauth_refresh_token_encrypted),
        google_user_email=row.google_user_email,
        folder_url_saved=bool(row.drive_folder_id),
        drive_folder_id=row.drive_folder_id,
        last_verified_at=row.last_verified_at,
        last_successful_upload_at=row.last_successful_upload_at,
        updated_at=row.updated_at,
    )
