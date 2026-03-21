from rag.prompts.grounding_contract import SCORING_GROUNDING_RULES, UNIVERSAL_LLM_RULES


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
