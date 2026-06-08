"""
SPARSH - Storage Settings Schemas

Pydantic DTOs for the Storage Settings admin workflow.
Supports OAuth-based Google Drive integration.
"""

from datetime import datetime
from pydantic import BaseModel


class StorageSettingsResponse(BaseModel):
    """Current storage configuration returned to the Admin."""
    storage_provider: str  # "google_drive"
    google_drive_connected: bool = False
    google_user_email: str | None = None
    folder_url_saved: bool = False
    drive_folder_id: str | None = None
    last_verified_at: datetime | None = None
    last_successful_upload_at: datetime | None = None
    updated_at: datetime | None = None


class OAuthStartResponse(BaseModel):
    """Response containing the Google OAuth authorization URL."""
    auth_url: str


class OAuthCallbackResponse(BaseModel):
    """Result of processing the OAuth callback."""
    success: bool
    google_user_email: str | None = None
    message: str


class StorageVerifyRequest(BaseModel):
    """Request to verify a Google Drive folder URL."""
    folder_url: str


class StorageVerifyResponse(BaseModel):
    """Result of a folder verification attempt."""
    verified: bool
    folder_id: str | None = None
    folder_name: str | None = None
    message: str


class StorageTestUploadResponse(BaseModel):
    """Result of a test upload attempt."""
    success: bool
    message: str


class StorageSaveRequest(BaseModel):
    """Request to save storage settings."""
    storage_provider: str  # "google_drive"
    drive_folder_id: str | None = None


class DriveAvailabilityResponse(BaseModel):
    """Whether Google Drive integration is available on this server."""
    google_drive_available: bool
    message: str | None = None
