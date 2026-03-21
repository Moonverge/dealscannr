from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = Path(__file__).resolve()


def _dotenv_paths() -> tuple[str, ...]:
    ing_dir = _HERE.parent
    repo_root = _HERE.parents[2]
    paths: list[Path] = []
    if (repo_root / ".env").is_file():
        paths.append(repo_root / ".env")
    api_env = ing_dir.parent / "api" / ".env"
    if api_env.is_file():
        paths.append(api_env)
    if (ing_dir / ".env").is_file():
        paths.append(ing_dir / ".env")
    if not paths:
        cwd = Path.cwd() / ".env"
        if cwd.is_file():
            paths.append(cwd)
    return tuple(str(p) for p in paths)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_dotenv_paths() or (".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    qdrant_url: str = "http://localhost:5500"
    openai_api_key: str | None = None
    together_api_key: str | None = None
    nomic_api_key: str | None = None
    groq_api_key: str | None = None
    firecrawl_api_key: str | None = None


settings = Settings()
