from pydantic import Field
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

    # Target-mode SSH endpoints for the operator-provisioned C4A + x86 pair. Deliberately
    # operator-configured (env/secret), not per-request user input — an API caller should
    # never be able to hand this service an arbitrary SSH host + key to connect to.
    target_arm_host: str | None = Field(default=None, validation_alias="CLUSIUS_TARGET_ARM_HOST")
    target_arm_user: str = Field(default="clusius", validation_alias="CLUSIUS_TARGET_ARM_USER")
    target_arm_ssh_key_path: str | None = Field(
        default=None, validation_alias="CLUSIUS_TARGET_ARM_SSH_KEY_PATH"
    )
    target_arm_price_per_hour: float | None = Field(
        default=None, validation_alias="CLUSIUS_TARGET_ARM_PRICE_PER_HOUR"
    )
    target_arm_instance_type: str = Field(
        default="c4a-standard-2", validation_alias="CLUSIUS_TARGET_ARM_INSTANCE_TYPE"
    )

    target_x86_host: str | None = Field(default=None, validation_alias="CLUSIUS_TARGET_X86_HOST")
    target_x86_user: str = Field(default="clusius", validation_alias="CLUSIUS_TARGET_X86_USER")
    target_x86_ssh_key_path: str | None = Field(
        default=None, validation_alias="CLUSIUS_TARGET_X86_SSH_KEY_PATH"
    )
    target_x86_price_per_hour: float | None = Field(
        default=None, validation_alias="CLUSIUS_TARGET_X86_PRICE_PER_HOUR"
    )
    target_x86_instance_type: str = Field(
        default="c4-standard-2", validation_alias="CLUSIUS_TARGET_X86_INSTANCE_TYPE"
    )

    default_hf_model_id: str = Field(
        default="Qwen/Qwen2.5-0.5B-Instruct", validation_alias="CLUSIUS_DEFAULT_HF_MODEL_ID"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def ssh_targets_configured(self) -> bool:
        return bool(self.target_arm_host and self.target_x86_host)
