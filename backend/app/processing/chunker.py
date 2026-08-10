from dataclasses import dataclass

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SentenceWindowNodeParser, SimpleNodeParser


@dataclass
class Chunk:
    text: str
    chunk_index: int
    token_count: int


def chunk_text(text: str, source_type: str = "text") -> list[Chunk]:
    if source_type == "spreadsheet":
        return _chunk_spreadsheet(text)
    if source_type == "whatsapp":
        return _chunk_whatsapp(text)
    return _chunk_standard(text)


def _chunk_standard(text: str) -> list[Chunk]:
    if not text.strip():
        return []

    doc = LlamaDocument(text=text)

    if len(text.split()) < 200:
        return [Chunk(text=text.strip(), chunk_index=0, token_count=len(text.split()))]

    parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )
    nodes = parser.get_nodes_from_documents([doc])

    chunks = []
    seen = set()
    idx = 0
    for node in nodes:
        t = node.text.strip()
        if t and t not in seen:
            seen.add(t)
            chunks.append(Chunk(text=t, chunk_index=idx, token_count=len(t.split())))
            idx += 1

    return chunks


def _chunk_spreadsheet(text: str) -> list[Chunk]:
    lines = text.strip().split("\n")
    if not lines:
        return []

    header = lines[0] if lines else ""
    data_lines = lines[1:] if len(lines) > 1 else []

    chunks = []
    batch_size = 20
    for i in range(0, max(len(data_lines), 1), batch_size):
        batch = data_lines[i : i + batch_size]
        chunk_text = header + "\n" + "\n".join(batch) if batch else header
        chunks.append(
            Chunk(
                text=chunk_text.strip(),
                chunk_index=len(chunks),
                token_count=len(chunk_text.split()),
            )
        )

    return chunks


def _chunk_whatsapp(text: str) -> list[Chunk]:
    if not text.strip():
        return []
    return [Chunk(text=text.strip(), chunk_index=0, token_count=len(text.split()))]
