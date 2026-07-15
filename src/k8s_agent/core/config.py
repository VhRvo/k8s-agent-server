from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    litellm_model_id: str = "openai/minimax-m2.7-wa8a"
    litellm_api_base: str = "http://localhost:4000/v1"
    litellm_api_key: str = "sk-xxx"
    server_host: str = "0.0.0.0"
    server_port: int = 7777
    inspection_interval_minutes: int = 30
    inspection_max_records: int = 50
    sqlite_path: str = "data/inspections.db"
    log_level: str = "INFO"
    agent_db_path: str = "data/agent.db"
    agent_user_id: str = "default"
    agent_history_messages: int = 20


settings = Settings()
