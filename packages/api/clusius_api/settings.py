from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://clusius:clusius@localhost:5432/clusius"
    redis_url: str = "redis://localhost:6379/0"
    results_dir: str = "bench/results"
    reports_dir: str = "bench/results"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Comma-separated list of origins allowed to call this API from a browser.
    cors_allow_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]
