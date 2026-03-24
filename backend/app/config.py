from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (graph-query/), so .env is found even when uvicorn cwd is backend/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_repo_path(value: str) -> str:
    """Resolve relative paths from .env against repo root (not process cwd)."""
    if not value or not str(value).strip():
        return value
    p = Path(value).expanduser()
    if p.is_absolute():
        return str(p.resolve())
    return str((_PROJECT_ROOT / p).resolve())


class Settings(BaseSettings):
    app_name: str = "Graph Query API"
    app_env: str = "dev"
    cors_origins: str = "http://localhost:5173"
    data_dir: str = str(_PROJECT_ROOT / "data")
    data_entity_dir: str = str(_PROJECT_ROOT / "sap-o2c-data")
    schema_dictionary_path: str = str(_PROJECT_ROOT / "backend" / "app" / "prompts" / "schema_dictionary.json")
    guardrail_policy_path: str = str(_PROJECT_ROOT / "backend" / "app" / "prompts" / "guardrail_policy.md")
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    # No default: set LLM_MODEL in .env to any model id your key can use with generateContent.
    llm_model: str = ""
    llm_temperature: float = 0.1
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        # Shared root .env may include frontend-only vars (e.g. VITE_API_BASE).
        extra="ignore",
    )

    @field_validator("data_dir", "data_entity_dir", "schema_dictionary_path", "guardrail_policy_path", mode="before")
    @classmethod
    def _repo_relative_paths(cls, value: str) -> str:
        return _resolve_repo_path(value)


settings = Settings()
