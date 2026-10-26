from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from typing import Self


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
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        return self


settings = Settings()
