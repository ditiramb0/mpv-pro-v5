from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MPV PRO V5"
    environment: str = "development"
    tradingview_webhook_secret: str = ""
    finnhub_api_key: str = ""
    twelve_data_api_key: str = ""
    max_daily_loss_percent: float = 3.0
    max_consecutive_losses: int = 3
    emergency_halt: bool = False
    database_url: str = "sqlite:///./mpv_pro_v5.db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
