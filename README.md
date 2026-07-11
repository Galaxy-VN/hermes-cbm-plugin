# hermes-cbm-plugin

> Graph-backed code intelligence for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — powered by [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)

Replaces `grep`/`search_files` with **structural graph queries** that understand your code's architecture — functions, classes, call chains, packages, routes. 158 languages. Sub-ms queries. 120x fewer tokens.

## Why?

Hermes ships with `search_files` (regex grep) and `read_file` (raw text). Those match comments, strings, and formatting equally. This plugin adds:

- **Structural search** — find by label (Function, Class, Route), name pattern, file scope, degree
- **Call graph traversal** — who calls what, across files and packages (import-aware, type-inferred)
- **Architecture overview** — languages, packages, entry points, Louvain clusters in one call
- **Dead code detection** — functions with zero callers
- **Impact analysis** — blast radius of your current git diff
- **Cypher queries** — read-only graph query language for complex analysis

The result: **120x fewer tokens** for code navigation tasks and zero false-positive matches.

## Prerequisites

Install codebase-memory-mcp:

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash

# Windows (PowerShell)
Invoke-WebRequest -Uri https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.ps1 -OutFile install.ps1
.\install.ps1
```

## Installation

### Quick install (from GitHub)

```bash
hermes plugins install Galaxy-VN/hermes-cbm-plugin
hermes plugins enable cbm
```

### Manual install

```bash
git clone https://github.com/Galaxy-VN/hermes-cbm-plugin.git ~/.hermes/plugins/cbm
hermes plugins enable cbm
```

Or add to `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - cbm
```

## Tools (12)

| Tool | What it does | Replaces |
|------|-------------|----------|
| `cbm_index` | Index a repository into the graph | — |
| `cbm_search` | Structural search by label, name, degree | `search_files` / grep |
| `cbm_search_code` | Graph-augmented grep (deduplicates into functions). Supports `regex=true` for alternation patterns | `search_files` |
| `cbm_trace` | Call graph BFS traversal (callers/callees) | `grep` for function calls |
| `cbm_architecture` | Languages, packages, clusters, hotspots | Manual exploration |
| `cbm_query` | Cypher-like graph queries | Complex grep chains |
| `cbm_code_snippet` | Read source for a specific symbol | `read_file` on whole file |
| `cbm_dead_code` | Find functions with zero callers | `grep` + manual analysis |
| `cbm_changes` | Map git diff to affected symbols | Manual impact analysis |
| `cbm_schema` | Graph schema (node/edge counts) | — |
| `cbm_projects` | List indexed projects | — |
| `cbm_delete` | Remove a project from the graph | — |

## Steering Hints

The plugin automatically injects hints into built-in tool descriptions:

- `search_files` → *"PREFER cbm_search_code for code-level search"*
- `read_file` → *"PREFER cbm_architecture / cbm_search for codebase understanding"*

No prompt changes needed — the model naturally prefers the graph tools.

## Bundled Skill

After enabling, load the skill for detailed usage guidance:

```
skill_view("cbm:cbm-intelligence")
```

**Note:** The skill lives inside the plugin's `skills/` directory. If `skill_view` doesn't find it, ensure the `skills/` directory was copied during installation (see Troubleshooting).

## Slash Command

```
/cbm status     → Show CBM binary status, indexed projects
/cbm index      → Index the current project
/cbm search     → Search the knowledge graph
/cbm trace      → Trace call paths
/cbm arch       → Architecture overview
/cbm dead       → Find dead code
/cbm projects   → List indexed projects
/cbm clear      → Remove a project
/cbm help       → Show usage
```

## Subagent Integration

The plugin forces `cbm` into every subagent's default toolsets, so `delegate_task` spawns automatically get graph-backed code intelligence. Steering hints are injected into child prompts.

## Configuration

### Auto-indexing

The plugin auto-indexes the current project on session start (git repos only). To disable:

```yaml
# Not currently configurable via config.yaml — remove the on_session_start hook
# by editing __init__.py if needed.
```

### Custom binary location

If `codebase-memory-mcp` is not on PATH, ensure it's in one of:
- `~/.local/bin/`
- `~/.cargo/bin/`
- Or add to PATH in your shell profile

## Architecture

```
__init__.py     ← Plugin registration, steering, hooks, toolset injection
schemas.py      ← Tool schemas (what the LLM sees)
tools.py        ← Tool handlers (subprocess calls to CBM CLI)
cli.py          ← /cbm slash command handlers
auto_index.py   ← Auto-indexing logic (git repo detection, project naming)
skills/
  cbm-intelligence/
    SKILL.md    ← Bundled skill with usage guidance
tests/
  test_cbm_plugin.py ← Unit tests
```

## How It Works

```
User: "What calls ProcessOrder?"

Agent calls: cbm_trace(function_name="ProcessOrder", direction="inbound")

CBM binary: executes graph query, returns structured results

Agent: presents the call chain in plain English
```

The plugin wraps the codebase-memory-mcp CLI as native Hermes tools. The binary does all the heavy lifting (tree-sitter parsing, graph storage, query execution). The plugin adds steering, auto-indexing, and Hermes integration.

## Token Efficiency

| Approach | Tokens | Notes |
|----------|--------|-------|
| 5 grep/read cycles | ~412,000 | File-by-file exploration |
| 5 CBM queries | ~3,400 | Graph-backed exploration |
| **Savings** | **99.2%** | Structural queries replace brute-force |

## Supported Languages

158 languages via vendored tree-sitter grammars. Full Hybrid LSP type resolution for:
Python, TypeScript, JavaScript, JSX, TSX, PHP, C#, Go, C, C++, Java, Kotlin, Rust, Perl.

## License

MIT

## Troubleshooting

### Bundled skill not showing

The plugin's `skills/` directory must exist at `~/.hermes/plugins/cbm/skills/`. If missing:

```bash
# Copy from source repo
cp -r skills/ ~/.hermes/plugins/cbm/skills/
```

Then restart Hermes. The skill registers via `ctx.register_skill()` in `__init__.py`.

### `cbm_search_code` with `|` returns 0

Set `regex=true` — the pipe is matched literally by default:

```
cbm_search_code(pattern="foo|bar", regex=true)
```

### `cbm_query` returns 0 for Java projects

Use `Method` label, not `Function`:

```
cbm_query(query="MATCH (f:Method)-[:CALLS]->(g:Method) WHERE f.name = 'main' RETURN g.name")
```
