# DealScannr RAG

Retrieval, connector lanes, Groq synthesis, and **grounding enforcement**.

## Flow (scan path)

1. Connectors (`connectors/`) fetch public signals per lane (SEC, courts, GitHub, hiring, news).
2. Chunks are embedded and optionally written to Qdrant (`dealscannr_chunks`).
3. `engine.RAGEngine` retrieves labeled evidence, calls Groq, then **`pipeline/llm_report_output.parse_validate_report_output`**:
   - Parses JSON into `ReportOutput`.
   - **Strips any `chunk_id` citations not present in the evidence set** and decrements `confidence_score` by **0.1 per removed citation** (floor 0).

## Grounding contract

Do not duplicate long prompt text. Import from `prompts/grounding_contract.py` only.

## Connector retries

`BaseConnector.fetch_with_retry` wraps `fetch` with exponential backoff on hard failures. `pipeline/runner.run_all_connectors` uses it.
