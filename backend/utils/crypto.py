from config.config import settings
from pathlib import Path


def _read_key(path_str: str) -> str:
    """Read a PEM key file, raising RuntimeError with a clear message on failure."""
    try:
        return Path(path_str).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"JWT key file not found: {exc.filename}") from exc


def load_signing_key() -> str:
    if settings.ALGORITHM != "ES256":
        raise ValueError(f"Unsupported algorithm: {settings.ALGORITHM}")
    return _read_key(settings.JWT_PRIVATE_KEY)


def load_verification_key() -> str:
    if settings.ALGORITHM != "ES256":
        raise ValueError(f"Unsupported algorithm: {settings.ALGORITHM}")
    return _read_key(settings.JWT_PUBLIC_KEY)
