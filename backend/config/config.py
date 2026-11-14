from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from sqlalchemy.engine import URL
from typing import Self
import re


_EXPIRY_PATTERN = re.compile(r"(\d+)\s*([smhdSMHD])?")
_EXPIRY_MULTIPLIERS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_expiry_seconds(value: str) -> int:
    """Parse an access-token expiry into a positive number of seconds.

    Accepts a bare integer (interpreted as seconds) or ``<amount><unit>`` where
    the unit is one of ``s``/``m``/``h``/``d``. Malformed, non-numeric, or
    non-positive values raise ``ValueError``: a bad expiry is a configuration
    error and must never be silently replaced by a default.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("JWT_EXPIRES_IN must be a non-empty string")

    match = _EXPIRY_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError(
            "JWT_EXPIRES_IN must be an integer number of seconds or use the "
            "form <amount><unit> with unit one of s/m/h/d (for example "
            "'3600' or '1h')"
        )

    amount = int(match.group(1))
    unit = (match.group(2) or "s").lower()
    seconds = amount * _EXPIRY_MULTIPLIERS[unit]
    if seconds <= 0:
        raise ValueError("JWT_EXPIRES_IN must be greater than zero")
    return seconds


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    DATABASE_HOST: str = Field(validation_alias="PGHOST", default="")
    DATABASE_PORT: int = Field(validation_alias="PGPORT", default=5432)
    DATABASE_USER: str = Field(validation_alias="PGUSER", default="")
    DATABASE_PASSWORD: str = Field(validation_alias="PGPASSWORD", default="")
    DATABASE_NAME: str = Field(validation_alias="PGDATABASE", default="")
    DATABASE_URL: str | None = None
    # Comma-separated list of allowed browser origins, or "*".
    CORS_ALLOW_ORIGINS: str = "*"
    # Interface the CoAP server binds to. Loopback by default; containers set
    # COAP_HOST=0.0.0.0 so the ESP nodes can reach it.
    COAP_HOST: str = "127.0.0.1"
    # Aggregator pairing/rate-limit tuning.
    HYDROPONIC_MIN_INTERVAL_SECONDS: float = 0.1
    HYDROPONIC_PAIR_TIMEOUT_SECONDS: float = 60.0
    # Automation thresholds used when no nutrition profile is active.
    HYDROPONIC_MOISTURE_THRESHOLD: float = 60.0
    HYDROPONIC_TEMPERATURE_THRESHOLD: float = 30.0
    ALGORITHM: str = "ES256"
    ACCESS_TOKEN_EXPIRE: str = Field(validation_alias="JWT_EXPIRES_IN")
    JWT_PRIVATE_KEY: str = Field(validation_alias="JWT_PRIVATE_KEY")
    JWT_PUBLIC_KEY: str = Field(validation_alias="JWT_PUBLIC_KEY")
    SUPERUSER_USERNAME: str = Field(validation_alias="SUPERUSER_USERNAME")
    SUPERUSER_EMAIL: str = Field(validation_alias="SUPERUSER_EMAIL")
    SUPERUSER_PASSWORD: str = Field(validation_alias="SUPERUSER_PASSWORD")
    SUPERUSER_ROLE: str = Field(validation_alias="SUPERUSER_ROLE")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _blank_database_url_is_none(cls, value: object) -> object:
        """Treat an empty/whitespace DATABASE_URL as unset.

        The containers are given `DATABASE_URL: ""` so the URL is rebuilt from
        PGHOST/PGPORT/... and a host-oriented value in `.env` (for example
        `localhost:5433`) can never leak into a container network.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("ACCESS_TOKEN_EXPIRE")
    @classmethod
    def _validate_access_token_expire(cls, value: str) -> str:
        """Reject malformed or non-positive ``JWT_EXPIRES_IN`` at load time.

        The value is validated but kept in its original string form so the
        setting continues to round-trip as configured.
        """
        parse_expiry_seconds(value)
        return value

    @property
    def access_token_expire_seconds(self) -> int:
        """``JWT_EXPIRES_IN`` expressed as a positive number of seconds."""
        return parse_expiry_seconds(self.ACCESS_TOKEN_EXPIRE)

    @property
    def cors_allow_origins(self) -> list[str]:
        """`CORS_ALLOW_ORIGINS` split into a list, ignoring empty entries."""
        return [
            origin.strip()
            for origin in self.CORS_ALLOW_ORIGINS.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def _build_database_url(self) -> Self:
        if self.DATABASE_URL is None:
            missing = [
                alias
                for alias, value in (
                    ("PGHOST", self.DATABASE_HOST),
                    ("PGUSER", self.DATABASE_USER),
                    ("PGPASSWORD", self.DATABASE_PASSWORD),
                    ("PGDATABASE", self.DATABASE_NAME),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "Either DATABASE_URL must be set explicitly, or all of the "
                    f"following must be provided: {', '.join(missing)}"
                )
            self.DATABASE_URL = URL.create(
                "postgresql+asyncpg",
                username=self.DATABASE_USER,
                password=self.DATABASE_PASSWORD,
                host=self.DATABASE_HOST,
                port=self.DATABASE_PORT,
                database=self.DATABASE_NAME,
            ).render_as_string(hide_password=False)
        return self


settings = Settings()
