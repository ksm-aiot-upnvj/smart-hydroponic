import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt, returning a UTF-8 string.

    Password hashing lives here (not in route handlers) so every creation and
    update path — the register route, the update route and superuser
    provisioning — uses the same implementation.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
