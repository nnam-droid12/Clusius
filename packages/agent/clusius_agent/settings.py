from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLUSIUS_AGENT_", env_file=".env", extra="ignore")

    router_base_url: str = "http://localhost:8081/v1"
    router_model: str = "qwen2.5-1.5b-instruct"
    generator_base_url: str = "http://localhost:8082/v1"
    generator_model: str = "qwen2.5-7b-instruct"
    request_timeout_s: float = 60.0

    docs_path: str = "bench/datasets/docs"
    docs_top_k: int = 3
    web_search_max_results: int = 5

    serve_host: str = "0.0.0.0"
    serve_port: int = 8090
