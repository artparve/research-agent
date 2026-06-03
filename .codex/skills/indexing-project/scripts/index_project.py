#!/usr/bin/env python3
"""Build an incremental, secret-aware context index for a Python repository."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path(".agent/indexing-project/index.json")
IGNORED_DIRS = {
    ".agent",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
IGNORED_NAMES = {
    ".env",
    "poetry.lock",
}
IGNORED_SUFFIXES = {
    ".csv",
    ".db",
    ".key",
    ".log",
    ".parquet",
    ".pem",
    ".sqlite",
}
SECRET_PATTERN = re.compile(
    r"(OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|PRIVATE KEY|password\s*=|token\s*=)",
    re.IGNORECASE,
)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_ignored(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in IGNORED_DIRS for part in relative.parts[:-1]):
        return True
    if path.name in IGNORED_NAMES or path.name.startswith(".env."):
        return True
    return path.suffix.lower() in IGNORED_SUFFIXES


def discover_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or is_ignored(path, root):
            continue
        if path.suffix.lower() in {".py", ".md"} or path.name == "pyproject.toml":
            files.append(path)
    return sorted(files)


def is_python_project(root: Path, files: list[Path]) -> bool:
    markers = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
    return any((root / marker).exists() for marker in markers) or any(
        path.suffix == ".py" for path in files
    )


def read_safe_text(path: Path) -> tuple[str | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None, "non-utf8"
    if SECRET_PATTERN.search(text):
        return None, "secret-like-content"
    return text, None


def symbol_signature(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        try:
            return f"{node.name}{ast.unparse(node.args)}"
        except Exception:
            return node.name
    return getattr(node, "name", "")


def parse_python(path: Path, text: str) -> dict[str, Any]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as error:
        return {"kind": "python", "error": f"syntax-error: {error.msg}:{error.lineno}"}

    imports: list[str] = []
    symbols: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")

    def add_symbol(node: ast.AST, kind: str, qualified_name: str) -> None:
        symbols.append(
            {
                "kind": kind,
                "symbol": qualified_name,
                "signature": symbol_signature(node),
                "start_line": getattr(node, "lineno", 1),
                "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                "docstring": ast.get_docstring(node) or "",
            }
        )

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            add_symbol(node, "class", node.name)
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_symbol(child, "method", f"{node.name}.{child.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_symbol(node, "function", node.name)

    return {
        "kind": "python",
        "module_docstring": ast.get_docstring(tree) or "",
        "imports": sorted(set(imports)),
        "symbols": symbols,
    }


def parse_markdown(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    headings: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        match = HEADING_PATTERN.match(line)
        if match:
            headings.append((line_number, len(match.group(1)), match.group(2)))
    for index, (start_line, level, heading) in enumerate(headings):
        end_line = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        sections.append(
            {
                "kind": "markdown-section",
                "heading": heading,
                "level": level,
                "start_line": start_line,
                "end_line": end_line,
                "text": "\n".join(lines[start_line - 1 : end_line]),
            }
        )
    if not sections and text.strip():
        sections.append(
            {
                "kind": "markdown-section",
                "heading": "(document)",
                "level": 0,
                "start_line": 1,
                "end_line": len(lines),
                "text": text,
            }
        )
    return {"kind": "markdown", "sections": sections}


def parse_file(path: Path, root: Path) -> dict[str, Any]:
    relative_path = path.relative_to(root).as_posix()
    digest = file_hash(path)
    text, skipped_reason = read_safe_text(path)
    record: dict[str, Any] = {"path": relative_path, "hash": digest}
    if skipped_reason:
        record.update({"kind": "skipped", "reason": skipped_reason})
    elif path.suffix.lower() == ".py":
        record.update(parse_python(path, text or ""))
    elif path.suffix.lower() == ".md":
        record.update(parse_markdown(text or ""))
    else:
        record.update({"kind": "project-config", "text": text or ""})
    return record


def load_previous(output: Path) -> dict[str, Any]:
    if not output.exists():
        return {}
    try:
        return json.loads(output.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_index(root: Path, output: Path) -> dict[str, Any]:
    files = discover_files(root)
    if not is_python_project(root, files):
        raise SystemExit("Not a Python project: indexing skipped.")

    previous = load_previous(output)
    previous_files = {record["path"]: record for record in previous.get("files", [])}
    records: list[dict[str, Any]] = []
    changed = 0
    for path in files:
        relative_path = path.relative_to(root).as_posix()
        digest = file_hash(path)
        old_record = previous_files.get(relative_path)
        if old_record and old_record.get("hash") == digest:
            records.append(old_record)
            continue
        records.append(parse_file(path, root))
        changed += 1

    current_paths = {record["path"] for record in records}
    deleted = len(set(previous_files) - current_paths)
    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "project_type": "python",
        "files": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(records)} files: {changed} changed, {deleted} deleted.")
    print(f"Index: {output}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / DEFAULT_OUTPUT
    build_index(root, output)


if __name__ == "__main__":
    main()
