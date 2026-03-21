def split_blocks(raw: str) -> list[tuple[str, str]]:
    raw = (raw or "").strip()
    if not raw:
        return []
    parts = raw.split("\n---\n")
    out: list[tuple[str, str]] = []
    for block in parts:
        block = block.strip()
        if not block:
            continue
        url = ""
        lines = block.split("\n")
        rest_start = 0
        if lines and lines[0].startswith("URL:"):
            url = lines[0].replace("URL:", "").strip()
            rest_start = 1
        body = "\n".join(lines[rest_start:]).strip()
        if len(body) < 40 and url:
            body = block
        out.append((url, body))
    return out


def window_chunks(text: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def build_chunk_payloads(blocks: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    urls: list[str] = []
    for url, body in blocks:
        for w in window_chunks(body):
            texts.append(w)
            urls.append(url or "aggregated")
    return texts, urls
