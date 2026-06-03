#!/usr/bin/env python3
"""Search a local repository context index with lightweight lexical ranking."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_INDEX = Path(".agent/indexing-project/index.json")
TOKEN_PATTERN = re.compile(r"[\w.-]+", re.UNICODE)


def normalize(text: str) -> str:
    return text.casefold()


def tokenize(text: str) -> set[str]:
    return {normalize(token) for token in TOKEN_PATTERN.findall(text)}


def score(query: str, text: str, *, symbol: bool = False) -> int:
    normalized_query = normalize(query)
    normalized_text = normalize(text)
    query_tokens = tokenize(query)
    text_tokens = tokenize(text)
    value = len(query_tokens & text_tokens) * 5
    if normalized_query in normalized_text:
        value += 15
    if symbol and normalized_query == normalize(text.splitlines()[0]):
        value += 30
    return value


def excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 3] + "..."


def candidates(index: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in index.get("files", []):
        path = record["path"]
        if record.get("kind") == "python":
            module_text = "\n".join(
                [path, record.get("module_docstring", ""), " ".join(record.get("imports", []))]
            )
            results.append(
                {
                    "path": path,
                    "line": 1,
                    "kind": "python-module",
                    "label": path,
                    "text": module_text,
                }
            )
            for symbol in record.get("symbols", []):
                text = "\n".join(
                    [
                        symbol["symbol"],
                        symbol.get("signature", ""),
                        symbol.get("docstring", ""),
                        " ".join(record.get("imports", [])),
                    ]
                )
                results.append(
                    {
                        "path": path,
                        "line": symbol["start_line"],
                        "kind": symbol["kind"],
                        "label": symbol["symbol"],
                        "text": text,
                        "symbol": True,
                    }
                )
        elif record.get("kind") == "markdown":
            for section in record.get("sections", []):
                results.append(
                    {
                        "path": path,
                        "line": section["start_line"],
                        "kind": section["kind"],
                        "label": section["heading"],
                        "text": section["text"],
                    }
                )
        elif record.get("kind") == "project-config":
            results.append(
                {
                    "path": path,
                    "line": 1,
                    "kind": "project-config",
                    "label": path,
                    "text": record.get("text", ""),
                }
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--index", type=Path)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    index_path = args.index.resolve() if args.index else root / DEFAULT_INDEX
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run index_project.py first.")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    ranked = []
    for candidate in candidates(index):
        value = score(args.query, candidate["text"], symbol=candidate.get("symbol", False))
        if value:
            ranked.append({**candidate, "score": value})
    ranked.sort(key=lambda item: (-item["score"], item["path"], item["line"]))
    ranked = ranked[: args.limit]
    if args.json:
        print(json.dumps(ranked, ensure_ascii=False, indent=2))
        return
    if not ranked:
        print("No indexed matches.")
        return
    for item in ranked:
        print(f"{item['path']}:{item['line']} [{item['kind']}] {item['label']} (score={item['score']})")
        print(f"  {excerpt(item['text'])}")


if __name__ == "__main__":
    main()
