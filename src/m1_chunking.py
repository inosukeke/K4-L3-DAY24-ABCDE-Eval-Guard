"""m1: document loading and hierarchical chunking for the K4 Track 3A RAG pipeline.

Reads Markdown policy documents from ``config.DATA_DIR`` and splits each
document into parent/child chunks. The implementation is intentionally
lightweight: it preserves the metadata required by the rest of the
pipeline (source file, section heading) and is fully deterministic so
the answer-generation step can be reproduced offline.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable

from config import DATA_DIR, HIERARCHICAL_CHILD_SIZE, HIERARCHICAL_PARENT_SIZE


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    parent_id: str | None = None


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", flags=re.MULTILINE)
_PARAGRAPH_RE = re.compile(r"\n\s*\n")


def _read_markdown(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_documents(data_dir: str = DATA_DIR) -> list[dict]:
    """Return a list of documents (raw text + metadata) from the corpus directory."""
    documents: list[dict] = []
    if not os.path.isdir(data_dir):
        return documents
    for name in sorted(os.listdir(data_dir)):
        if not name.lower().endswith(".md"):
            continue
        full_path = os.path.join(data_dir, name)
        text = _read_markdown(full_path)
        if not text.strip():
            continue
        documents.append({
            "text": text,
            "metadata": {"source": name, "path": full_path},
        })
    return documents


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    last_idx = 0
    last_heading = ""
    for match in _HEADING_RE.finditer(text):
        if match.start() > last_idx:
            body = text[last_idx:match.start()].strip()
            if body:
                sections.append((last_heading, body))
        last_heading = match.group(2).strip()
        last_idx = match.end()
    if last_idx < len(text):
        body = text[last_idx:].strip()
        if body:
            sections.append((last_heading, body))
    if not sections:
        sections.append(("", text.strip()))
    return sections


def _split_paragraphs(body: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in _PARAGRAPH_RE.split(body) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i + max_chars])
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


def chunk_hierarchical(
    text: str,
    metadata: dict | None = None,
    *,
    parent_size: int = HIERARCHICAL_PARENT_SIZE,
    child_size: int = HIERARCHICAL_CHILD_SIZE,
) -> tuple[list[Chunk], list[Chunk]]:
    base_meta = dict(metadata or {})
    source = base_meta.get("source", "document")
    sections = _split_by_headings(text)

    parents: list[Chunk] = []
    children: list[Chunk] = []
    parent_counter = 0
    child_counter = 0

    for heading, body in sections:
        body_chunks = _split_paragraphs(body, parent_size) if body else [""]
        for parent_text in body_chunks:
            parent_counter += 1
            parent_id = f"{source}::p{parent_counter}"
            parent_meta = {**base_meta, "section": heading, "level": "parent"}
            parents.append(Chunk(text=parent_text, metadata=parent_meta, parent_id=parent_id))

            sub_chunks = _split_paragraphs(parent_text, child_size) if parent_text else [parent_text]
            for child_text in sub_chunks:
                child_counter += 1
                child_meta = {**base_meta, "section": heading, "level": "child", "chunk_index": child_counter}
                children.append(Chunk(text=child_text, metadata=child_meta, parent_id=parent_id))

    return parents, children


def flatten_children(children: Iterable[Chunk]) -> list[dict]:
    return [{"text": child.text, "metadata": dict(child.metadata)} for child in children]
