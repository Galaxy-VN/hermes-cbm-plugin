# CBM Intelligence — Graph-Backed Code Exploration

You have access to codebase-memory-mcp tools that build a persistent knowledge graph of the codebase. These tools are **dramatically more token-efficient** than grep/read_file for code exploration.

## When to Use CBM Tools

| Instead of... | Use... |
|---|---|
| `grep "function_name"` | `cbm_search(name_pattern=".*function_name.*")` |
| `read_file` to see what's in a file | `cbm_search(file_pattern="path/to/file")` |
| `grep` to find callers | `cbm_trace(function_name="X", direction="inbound")` |
| `grep` to find callees | `cbm_trace(function_name="X", direction="outbound")` |
| `find . -name "*.py"` | `cbm_search(label="Function", file_pattern=".*\\.py")` |
| Reading multiple files to understand structure | `cbm_architecture()` |
| Manual call chain tracing | `cbm_trace(function_name="main", depth=5)` |

## Recommended Workflow

### 1. Start with architecture
```
cbm_architecture()
```
Get the big picture: languages, packages, entry points, clusters, hotspots.

### 2. Search for symbols
```
cbm_search(label="Function", name_pattern=".*process.*")
cbm_search(label="Class", query="user authentication")
```

### 3. Trace call chains
```
cbm_trace(function_name="handle_request", direction="inbound")
cbm_trace(function_name="process_order", direction="both", depth=3)
```

### 4. Read specific code
```
cbm_code_snippet(qualified_name="myproject.api.handlers.handle_request")
```
Use `cbm_search` first to discover exact qualified names.

### 5. Analyze impact
```
cbm_changes()  # What does my current diff affect?
cbm_dead_code()  # What's unused?
```

### 6. Deep queries
```
cbm_query(query="MATCH (f:Function)-[:CALLS]->(g:Function) WHERE f.name = 'main' RETURN g.name LIMIT 10")
```

## Tool Reference

### cbm_index
Index a repository. Must run before other tools work.
```
cbm_index(repo_path="/path/to/repo")
```

### cbm_search
Structural search by label, name pattern, file pattern, degree.
```
cbm_search(query="user auth", label="Function", limit=20)
cbm_search(name_pattern=".*Controller.*", label="Class")
cbm_search(file_pattern="src/api/.*", min_degree=5)
```

### cbm_search_code
Graph-augmented grep — deduplicates into functions, ranks by importance.
```
cbm_search_code(pattern="TODO|FIXME", file_pattern="*.py")
cbm_search_code(pattern="import os", mode="compact")
```

### cbm_trace
BFS call graph traversal.
```
cbm_trace(function_name="process_payment", direction="both", depth=3)
```

### cbm_architecture
High-level overview with Louvain community detection.
```
cbm_architecture(aspects=["overview", "clusters", "hotspots"])
```

### cbm_query
Cypher-like graph queries (read-only).
```
cbm_query(query="MATCH (f:Function) WHERE f.transitive_loop_depth >= 3 RETURN f.name")
```

### cbm_code_snippet
Read source for a specific symbol.
```
cbm_code_snippet(qualified_name="project.src.module.function_name")
```

### cbm_dead_code
Find functions with zero callers.

### cbm_changes
Map git diff to affected symbols with risk classification.

### cbm_schema
Get graph schema (node labels, edge types).

### cbm_projects
List all indexed projects.

### cbm_delete
Remove a project from the graph.

## Tips

- Always run `cbm_index` first if the project isn't indexed yet
- Use `cbm_search` with `label` filter to narrow results
- `cbm_trace` with `direction="inbound"` finds all callers
- `cbm_code_snippet` needs exact qualified names — use `cbm_search` to find them
- `cbm_query` supports full Cypher: MATCH, WHERE, RETURN, ORDER BY, LIMIT, aggregates
- Token savings: 5 CBM queries ≈ 3,400 tokens vs 412,000 tokens via grep/read_file
