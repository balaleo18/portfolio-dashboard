import logging
from cryptography.fernet import Fernet
from backend.app.config import settings

logger = logging.getLogger(__name__)

_fallback_key = None

def get_fernet() -> Fernet:
    global _fallback_key
    key_str = settings.ENCRYPTION_KEY
    if key_str == "your_fernet_encryption_key_here":
        if _fallback_key is None:
            _fallback_key = Fernet.generate_key()
            logger.warning(
                "SECURITY WARNING: Using temporary in-memory Fernet key. "
                "Data will not persist across app restarts! Please set ENCRYPTION_KEY in your .env file."
            )
        return Fernet(_fallback_key)
    try:
        return Fernet(key_str.encode())
    except Exception as e:
        logger.error(f"Failed to parse ENCRYPTION_KEY from env, error: {e}")
        if _fallback_key is None:
            _fallback_key = Fernet.generate_key()
        return Fernet(_fallback_key)

def encrypt_token(token: str) -> str:
    if not token:
        return ""
    f = get_fernet()
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    f = get_fernet()
    try:
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ""
