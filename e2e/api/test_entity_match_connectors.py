"""Unit-style checks for litigation connector entity disambiguation (no live HTTP)."""

from rag.connectors.courtlistener import case_matches_entity
from rag.connectors.sec_edgar import sec_filing_entity_matches


def test_courtlistener_rejects_linear_controls_homonym():
    assert not case_matches_entity(
        "Peterson v. Linear Controls, Inc.",
        "Linear",
        "linear.app",
    )
    assert not case_matches_entity("People v. Linear Controls", "Linear", "linear.app")


def test_courtlistener_keeps_versus_captions():
    assert case_matches_entity("Linear v. Acme Corp", "Linear", "linear.app")
    assert case_matches_entity("Acme LLC v. Linear", "Linear", "linear.app")


def test_sec_rejects_linear_technology_when_target_is_linear():
    assert not sec_filing_entity_matches("Linear", "Linear Technology Corp")
    assert not sec_filing_entity_matches("Linear", "LINEAR TECHNOLOGIES INC")


def test_sec_allows_normal_corporate_suffixes():
    assert sec_filing_entity_matches("Notion Labs", "Notion Labs Inc.")
    assert sec_filing_entity_matches("Acme", "Acme Corp")


def test_sec_rejects_different_notion():
    assert not sec_filing_entity_matches("Notion Labs", "Notion Accessories Inc")
