# Indexing Strategy

Use this reference when the lightweight local index is no longer sufficient.

## Indexed Entities

- Python modules, classes, functions, methods, imports, and docstrings
- Markdown sections split by headings
- Project metadata such as `pyproject.toml`
- Paths and line numbers for every navigable result

## Retrieval Layers

Prefer a hybrid retrieval stack for larger repositories:

1. Lexical search with `rg`, SQLite FTS5, BM25, or Tantivy
2. Symbol search with Python AST, LSP, or ctags
3. Vector search with embeddings for conceptual queries
4. Optional reranking with boosts for exact symbols, paths, docstrings, and recently
   modified files

Expand selected results with nearby symbols, matching tests, and related documentation.

## Incremental Updates

Track file hashes. Reparse changed files, remove deleted files, and treat renames as delete
plus add unless the storage layer supports path updates.

## Storage Options

Start locally:

- `.agent/indexing-project/index.json` for the bundled lightweight implementation
- SQLite FTS5 for scalable keyword and symbol search
- Chroma, LanceDB, or Qdrant for local vector search

For a shared service, add repository-level access control and use Qdrant, Weaviate, or
OpenSearch.

## Security

Exclude virtual environments, caches, builds, `.env` files, private keys, databases, logs,
and large generated datasets. Scan candidate text for secret markers before persisting it.
