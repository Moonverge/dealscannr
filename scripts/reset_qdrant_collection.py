"""Delete dealscannr_chunks — run when switching embedding providers / fixing dim mismatch."""

from __future__ import annotations

import os
import sys

from qdrant_client import QdrantClient


def main() -> int:
    url = (os.environ.get("QDRANT_URL") or "").strip()
    if not url:
        print("Set QDRANT_URL", file=sys.stderr)
        return 1
    u = url.rstrip("/")
    key = (os.environ.get("QDRANT_API_KEY") or "").strip() or None
    client = (
        QdrantClient(url=u, api_key=key, check_compatibility=False)
        if key
        else QdrantClient(url=u, check_compatibility=False)
    )
    try:
        client.delete_collection("dealscannr_chunks")
    except Exception as e:
        low = str(e).lower()
        if "not found" in low or "404" in low or "does not exist" in low:
            print("Collection already absent; nothing to delete.")
            return 0
        raise
    print("Collection deleted. It will be recreated on next scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
