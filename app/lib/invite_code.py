import base64
import secrets


def generate_invite_code() -> str:
    """8-character base32 code (40 bits entropy)."""
    return base64.b32encode(secrets.token_bytes(5)).decode("ascii").rstrip("=").upper()
