---
name: indexing-project
description: Build and use a lightweight local repository context index for more efficient coding-agent work. Use when Codex is working in a Python repository and needs to understand architecture, locate relevant symbols, connect code with Markdown documentation, gather context before edits, or refresh repository context after substantial changes.
---

# Indexing Project

Use a local, incremental index as a context-navigation aid. Treat source files as the
authority: open the relevant source lines before editing.

## Workflow

1. Read the repository `AGENTS.md` and follow its project-specific rules.
2. Confirm that the current repository is a Python project. Look for `pyproject.toml`,
   `setup.py`, `setup.cfg`, `requirements.txt`, or tracked `.py` files.
3. Update the index from the repository root:

   ```bash
   python3 <skill-dir>/scripts/index_project.py --root "$PWD"
   ```

4. Search the index before implementing a feature, tracing behavior, or changing a public
   API:

   ```bash
   python3 <skill-dir>/scripts/search_index.py --root "$PWD" "search terms"
   ```

5. Use `rg` for exact text, call-site, and configuration searches. The index narrows the
   search area; `rg` verifies the current code.
6. Open the matching code, nearby tests, and related Markdown sections before editing.
7. Refresh the index after substantial source or documentation changes when later work in
   the same repository needs the updated context.

## Search Strategy

- Search exact symbol names for known functions, classes, methods, and modules.
- Search domain phrases when the relevant implementation is unknown.
- Inspect neighboring symbols and imports from the indexed Python record.
- Search tests for the selected symbol or module with `rg`.
- Search Markdown results for architecture decisions, usage constraints, and documented
  behavior.

The generated index lives at `.agent/indexing-project/index.json` inside the target
repository. It is derived local state; do not commit it unless the repository explicitly
requires that.

## Security Rules

- Do not index `.env` files, credentials, private keys, databases, logs, caches, virtual
  environments, or generated build directories.
- Keep secret-like text out of the index even when it appears in an otherwise indexable
  file.
- Do not substitute index snippets for a direct source read before making a change.

## Advanced Design

Read [references/indexing-strategy.md](references/indexing-strategy.md) when extending this
skill with embeddings, vector storage, file watchers, or a production indexing service.
