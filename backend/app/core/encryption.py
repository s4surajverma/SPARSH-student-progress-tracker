"""
SPARSH - Credential Encryption Module

Provides Fernet-based encryption for sensitive data stored in the database.
Used for encrypting OAuth refresh tokens and any other credentials.
"""

import json
from cryptography.fernet import Fernet
from app.core.config import settings

# Initialize a global Fernet instance using the configured secret key.
# This will throw an error if the key is invalid.
_fernet = Fernet(settings.FERNET_SECRET_KEY.encode('utf-8'))


def encrypt_credentials(payload: dict) -> str:
    """
    Encrypt a dictionary (e.g., Google Service Account JSON) into a Fernet token.
    Returns the URL-safe base64-encoded string.
    """
    json_bytes = json.dumps(payload).encode('utf-8')
    token_bytes = _fernet.encrypt(json_bytes)
    return token_bytes.decode('utf-8')


def decrypt_credentials(token: str) -> dict:
    """
    Decrypt a Fernet token back into the original dictionary.
    """
    token_bytes = token.encode('utf-8')
    json_bytes = _fernet.decrypt(token_bytes)
    return json.loads(json_bytes.decode('utf-8'))


def encrypt_string(plaintext: str) -> str:
    """
    Encrypt a plain string (e.g., an OAuth refresh token) into a Fernet token.
    Returns the URL-safe base64-encoded string.
    """
    token_bytes = _fernet.encrypt(plaintext.encode('utf-8'))
    return token_bytes.decode('utf-8')


def decrypt_string(token: str) -> str:
    """
    Decrypt a Fernet token back into the original plain string.
    """
    token_bytes = token.encode('utf-8')
    plaintext_bytes = _fernet.decrypt(token_bytes)
    return plaintext_bytes.decode('utf-8')
