from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days default


settings = Settings()
