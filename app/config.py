from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "MPV PRO V5"
    environment: str = "development"
    tradingview_webhook_secret: str = ""
    database_url: str = "sqlite:///./mpv_pro_v5.db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
