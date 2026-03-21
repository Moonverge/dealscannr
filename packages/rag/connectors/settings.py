"""Runtime secrets/options for connectors (built from API settings / env)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectorSettings:
    courtlistener_api_key: str | None = None
    github_token: str | None = None
    newsapi_key: str | None = None
    firecrawl_api_key: str | None = None
    adzuna_app_id: str | None = None
    adzuna_api_key: str | None = None
    adzuna_country: str = "us"
