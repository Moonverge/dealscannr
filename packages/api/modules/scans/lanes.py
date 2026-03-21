"""Connector → diligence lane mapping (shared by scan status + diff)."""

LANE_CONNECTORS: dict[str, list[str]] = {
    "litigation": ["sec_edgar", "courtlistener"],
    "engineering": ["github_connector"],
    "hiring": ["hiring_connector"],
    "news": ["news_connector", "wikipedia"],
}
