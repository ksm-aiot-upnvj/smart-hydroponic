from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
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
    ALGORITHM: str = "ES256"
    ACCESS_TOKEN_EXPIRE: str = Field(validation_alias="JWT_EXPIRES_IN")
    JWT_PRIVATE_KEY: str = Field(validation_alias="JWT_PRIVATE_KEY")
    JWT_PUBLIC_KEY: str = Field(validation_alias="JWT_PUBLIC_KEY")
    SUPERUSER_USERNAME: str = Field(validation_alias="SUPERUSER_USERNAME")
    SUPERUSER_EMAIL: str = Field(validation_alias="SUPERUSER_EMAIL")
    SUPERUSER_PASSWORD: str = Field(validation_alias="SUPERUSER_PASSWORD")
    SUPERUSER_ROLE: str = Field(validation_alias="SUPERUSER_ROLE")

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
