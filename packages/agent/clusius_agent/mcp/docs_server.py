"""MCP server exposing a `search_docs` tool over a local markdown corpus.

Uses a dependency-free TF-IDF + cosine similarity ranking so the document/vector-store
tool has no ML runtime of its own to install or optimize — the router/generator models
are the optimization target, not this retrieval index.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path

from mcp.server.fastmcp import FastMCP

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class DocIndex:
    def __init__(self, docs_path: Path) -> None:
        self.docs_path = docs_path
        self.documents: dict[str, str] = {}
        self.term_freqs: dict[str, Counter[str]] = {}
        self.doc_freq: Counter[str] = Counter()
        self._load()

    def _load(self) -> None:
        for path in sorted(self.docs_path.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.documents[path.name] = text
            tokens = _tokenize(text)
            tf = Counter(tokens)
            self.term_freqs[path.name] = tf
            for term in tf:
                self.doc_freq[term] += 1

    def _idf(self, term: str) -> float:
        n_docs = max(len(self.documents), 1)
        df = self.doc_freq.get(term, 0)
        return math.log((n_docs + 1) / (df + 1)) + 1.0

    def _vector(self, tf: Counter[str]) -> dict[str, float]:
        return {term: count * self._idf(term) for term, count in tf.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        shared = set(a) & set(b)
        numerator = sum(a[t] * b[t] for t in shared)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return numerator / (norm_a * norm_b)

    def search(self, query: str, top_k: int = 3) -> list[dict[str, object]]:
        query_vec = self._vector(Counter(_tokenize(query)))
        scored = []
        for name, tf in self.term_freqs.items():
            doc_vec = self._vector(tf)
            score = self._cosine(query_vec, doc_vec)
            if score > 0:
                scored.append((name, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        results = []
        for name, score in scored[:top_k]:
            results.append(
                {
                    "source": name,
                    "text": self.documents[name],
                    "score": round(score, 4),
                }
            )
        return results


def build_server(docs_path: str | None = None) -> FastMCP:
    resolved = Path(docs_path or os.environ.get("CLUSIUS_AGENT_DOCS_PATH", "bench/datasets/docs"))
    index = DocIndex(resolved)
    server = FastMCP("clusius-docs")

    @server.tool()
    def search_docs(query: str, top_k: int = 3) -> list[dict[str, object]]:
        """Search the local document store and return the top-k matching chunks."""
        return index.search(query, top_k=top_k)

    return server


mcp = build_server()

if __name__ == "__main__":
    mcp.run()
