from typing import Literal

from rag.prompts.grounding_contract import SCORING_GROUNDING_RULES, UNIVERSAL_LLM_RULES

VERDICT_LEVEL: dict[str, int] = {"INSUFFICIENT": 0, "PASS": 1, "MEET": 2, "FLAG": 3}
SCORING_TO_SYNTHESIS: dict[str, str] = {"green": "MEET", "yellow": "PASS", "red": "FLAG"}


def reconcile_verdicts(
    synthesis_verdict: str,
    scoring_verdict_raw: str,
    synthesis_confidence: float,
    scoring_confidence: float,
) -> tuple[str, float, bool]:
    """Compare synthesis verdict with scoring verdict.

    Returns (final_verdict, final_confidence, needs_review).
    If they conflict by 2+ levels, flag needs_review and pick the lower-confidence verdict.
    """
    mapped = SCORING_TO_SYNTHESIS.get(scoring_verdict_raw, "PASS")
    sv = VERDICT_LEVEL.get(synthesis_verdict, 1)
    scv = VERDICT_LEVEL.get(mapped, 1)

    if abs(sv - scv) >= 2:
        lower = mapped if scv < sv else synthesis_verdict
        return lower, min(synthesis_confidence, scoring_confidence), True
    return synthesis_verdict, synthesis_confidence, False


def scoring_prompt(
    summary: str,
    signals_json: str,
    *,
    preliminary: bool = False,
) -> str:
    pre = ""
    if preliminary:
        pre = """
PRELIMINARY (no Qdrant index; live web / model only):
- Never use verdict "green".
- Confidence must be <= 0.68.
- Default to "yellow" unless there are clear red-flag risks in the text.
"""
    return f"""Based on this due diligence summary and signals, assign a single verdict and confidence (0.0-1.0).

Summary: {summary}

Signals: {signals_json}
{pre}

{SCORING_GROUNDING_RULES}

{UNIVERSAL_LLM_RULES}

Rules:
- green: Strong positive signals overall, no major red flags (only when full indexed DD exists).
- yellow: Mixed or uncertain; some concerns but not disqualifying.
- red: Significant red flags (litigation, key departures, negative sentiment, etc.).

Output ONLY a JSON object with no other text:
{{"verdict": "green"|"yellow"|"red", "confidence": 0.85}}
"""
