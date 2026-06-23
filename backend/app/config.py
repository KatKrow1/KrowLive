"""Application configuration."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_key: str = ""
    google_places_api_key: str = ""
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    debug: bool = True

    enrichment_provider: str = "none"
    enrichment_api_key: str = ""
    enrichment_api_url: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_timeout_seconds: float = 120.0
    ollama_max_executive_calls: int = 6
    ollama_refinement_model: str = "qwen3"
    ollama_refinement_timeout_seconds: float = 420.0

    @field_validator("enrichment_provider")
    @classmethod
    def normalize_enrichment_provider(cls, value: str) -> str:
        normalized = (value or "none").lower().strip()
        if normalized not in ("none", "custom", "ollama"):
            raise ValueError('ENRICHMENT_PROVIDER must be "none", "custom", or "ollama"')
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
