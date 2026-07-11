---
name: cbm-intelligence
description: "Use when exploring code structure (callers, callees, classes, architecture). Graph-backed code intelligence — replaces grep with structural queries. 158 languages, sub-ms, 120x fewer tokens."
version: 1.0.0
author: GalaxyVN
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: ["CodeGraph", "Codebase", "TokenSaving", "Indexing"]
---

# CBM Intelligence — Graph-Backed Code Exploration

You have `cbm_*` tools that build a persistent knowledge graph of the codebase. These are **dramatically more token-efficient** than grep/read_file for code exploration.

## Decision Rule

Code STRUCTURE (callers, callees, classes, imports, dead code, architecture) → cbm tools.
Raw TEXT content (comments, strings, config values) → `search_files`.

## Quick Reference

| Instead of... | Use... |
|---|---|
| `grep "function_name"` | `cbm_search(name_pattern=".*function_name.*")` |
| `read_file` to see what's in a file | `cbm_search(file_pattern="path/to/file")` |
| `grep` to find callers | `cbm_trace(function_name="X", direction="inbound")` |
| `grep` to find callees | `cbm_trace(function_name="X", direction="outbound")` |
| `find . -name "*.py"` | `cbm_search(label="Function", file_pattern=".*\\.py")` |
| Reading multiple files to understand structure | `cbm_architecture()` |
| Manual call chain tracing | `cbm_trace(function_name="main", depth=5)` |

## Workflow

### 1. Architecture → 2. Search → 3. Trace → 4. Code → 5. Impact

```
cbm_architecture()                                                    # overview
cbm_search(label="Function", name_pattern=".*process.*")              # find symbols
cbm_trace(function_name="handle_request", direction="inbound")        # callers
cbm_code_snippet(qualified_name="project.src.module.function_name")   # read source
cbm_changes() / cbm_dead_code()                                       # impact
```

### Deep queries

```
cbm_query(query="MATCH (f:Method)-[:CALLS]->(g:Method) WHERE f.name = 'main' RETURN g.name LIMIT 10")
```

Use `cbm_search` first to discover exact qualified names. Use `cbm_schema()` to check available labels.

## Tool Reference

| Tool | What it does |
|------|-------------|
| `cbm_index` | Index a repository (must run first) |
| `cbm_search` | Structural search by label, name pattern, file pattern, degree |
| `cbm_search_code` | Graph-augmented grep — deduplicates into functions. **`regex=true` for `\|` patterns** |
| `cbm_trace` | BFS call graph traversal (callers/callees) |
| `cbm_architecture` | Languages, packages, clusters, hotspots |
| `cbm_query` | Cypher-like graph queries (read-only) |
| `cbm_code_snippet` | Read source for a specific symbol |
| `cbm_dead_code` | Find functions with zero callers |
| `cbm_changes` | Map git diff to affected symbols |
| `cbm_schema` | Graph schema (node labels, edge types) |
| `cbm_projects` | List indexed projects |
| `cbm_delete` | Remove a project from the graph |

## Pitfalls

1. **`cbm_search_code` with `|` returns 0** — Must set `regex=true`. Without it, `|` is matched literally. Always use `regex=true` for alternation patterns like `foo|bar`.

2. **Java/Kotlin uses `Method` not `Function`** — `MATCH (f:Function)` returns 0 for JVM projects. Use `MATCH (f:Method)`. Run `cbm_schema()` first.

3. **Never fall back to grep when cbm returns 0** — Investigate WHY first: (a) pattern has `|`? → `regex=true` (b) Cypher uses `Function` for Java? → `Method` (c) index stale? → `cbm_index`. Only after all three fail, use `search_files` and tell the user.

4. **`trace_path` needs exact names** — Use `cbm_search(name_pattern=...)` first to discover the exact qualified name.

5. **`search_graph` returns degree counts, not edge targets** — To see what X calls, use `cbm_trace` or `cbm_query` with Cypher.

6. **`query_graph` Cypher limitations (v0.9.0)** — `NOT EXISTS { pattern }` and `OPTIONAL MATCH` are NOT supported. `min_degree`/`max_degree` are accepted but don't actually filter.

7. **`qualified_name` format** — Uses dashed paths: `C-Users-foo-repo.src.main.java.com.example.MyClass.myMethod`. Get from `cbm_search` results.

8. **Project name format** — Path separators → dashes. Get from `cbm_projects`, don't guess.

9. **`cbm_dead_code` limitation** — Uses `search_graph` with `max_degree=0` which returns ALL methods in v0.9.0 (filter doesn't work). Use `cbm_trace` on individual methods for accurate dead code detection.

10. **Token savings** — 5 CBM queries ≈ 3,400 tokens vs 412,000 via grep/read_file.
