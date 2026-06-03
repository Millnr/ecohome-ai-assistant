from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    flowise_url: str = "http://localhost:3000"
    flowise_api_key: str = ""
    flowise_chatflow_id: str = ""
    redis_url: str = "redis://localhost:6379"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"


settings = Settings()
