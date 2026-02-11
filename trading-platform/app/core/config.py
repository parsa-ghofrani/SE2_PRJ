from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str
    
    # JWT (from auth service)
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Redis (from notification service)
    redis_host: str = "localhost"
    redis_port: int = 6379
    
    # ✅ Blockchain (اضافه کنید)
    chain_rpc_url: str = "http://localhost:8545"
    chain_sender_private_key: str
    trade_ledger_address: str
    
    # ✅ SIWE (اضافه کنید)
    app_domain: str = "localhost"
    app_origin: str = "http://localhost:8000"
    siwe_nonce_ttl_seconds: int = 300


settings = Settings()