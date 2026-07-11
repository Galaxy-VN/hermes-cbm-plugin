"""Tool handlers — subprocess calls to codebase-memory-mcp CLI."""
import json
import logging
import os
import shutil
import subprocess
from typing import Any, Optional

logger = logging.getLogger("cbm")

# Cache the binary path once found
_BINARY: Optional[str] = None


def _find_binary() -> Optional[str]:
    """Locate the codebase-memory-mcp binary."""
    global _BINARY
    if _BINARY is not None:
        return _BINARY

    # Check PATH first
    found = shutil.which("codebase-memory-mcp")
    if found:
        _BINARY = found
        return _BINARY

    # Check common install locations
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".local", "bin", "codebase-memory-mcp"),
        os.path.join(home, ".cargo", "bin", "codebase-memory-mcp"),
        # npm global
        os.path.join(home, "node_modules", ".bin", "codebase-memory-mcp"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            _BINARY = c
            return _BINARY

    return None

def _get_project_from_cwd() -> str:
    """Convert CWD to project name: path separators → dashes."""
    return os.getcwd().replace("\\", "-").replace("/", "-").replace(":", "")

def _run_cbm(args: dict, timeout: int = 30) -> str:
    """Run a codebase-memory-mcp CLI command and return JSON output."""
    if "project" not in args:
        args["project"] = _get_project_from_cwd()
    binary = _find_binary()
    if not binary:
        return json.dumps({
            "error": (
                "codebase-memory-mcp binary not found. Install it:\n"
                "  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash\n"
                "Or add it to PATH."
            )
        })

    cli_args = [binary, "cli"]
    # Build the CLI command: binary cli <tool_name> '<json_args>'
    # The tool name is in args["tool"], rest is the JSON payload
    tool_name = args.pop("_cli_tool", None)
    if not tool_name:
        return json.dumps({"error": "Missing _cli_tool parameter"})

    cli_args.extend([tool_name, json.dumps(args)])

    try:
        result = subprocess.run(
            cli_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CBM_LOG_LEVEL": "warn"},
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            return json.dumps({"error": f"CBM CLI error (exit {result.returncode}): {stderr}"})
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"CBM CLI timed out after {timeout}s"})
    except FileNotFoundError:
        return json.dumps({"error": f"Binary not found at: {binary}"})
    except Exception as e:
        return json.dumps({"error": f"CBM CLI failed: {e}"})


def is_available() -> bool:
    """Check if the binary is installed and working."""
    binary = _find_binary()
    if not binary:
        return False
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Tool handlers ──────────────────────────────────────────────────────


def index_repository(args: dict, **kwargs) -> str:
    """Index a repository into the knowledge graph."""
    repo_path = args.get("repo_path", os.getcwd())
    project_name = args.get("project_name")

    payload = {"repo_path": os.path.abspath(repo_path)}
    if project_name:
        payload["project_name"] = project_name

    return _run_cbm({**payload, "_cli_tool": "index_repository"}, timeout=120)


def search_graph(args: dict, **kwargs) -> str:
    """Search the knowledge graph."""
    payload = {}
    project = args.get("project")
    if project:
        payload["project"] = project
    if args.get("query"):
        payload["query"] = args["query"]
    if args.get("name_pattern"):
        payload["name_pattern"] = args["name_pattern"]
    if args.get("label"):
        payload["label"] = args["label"]
    if args.get("file_pattern"):
        payload["file_pattern"] = args["file_pattern"]
    if args.get("min_degree") is not None:
        payload["min_degree"] = args["min_degree"]
    if args.get("max_degree") is not None:
        payload["max_degree"] = args["max_degree"]
    payload["limit"] = args.get("limit", 50)
    payload["offset"] = args.get("offset", 0)

    return _run_cbm({**payload, "_cli_tool": "search_graph"})


def search_code(args: dict, **kwargs) -> str:
    """Graph-augmented code search."""
    payload = {"pattern": args["pattern"]}
    project = args.get("project")
    if project:
        payload["project"] = project
    if args.get("file_pattern"):
        payload["file_pattern"] = args["file_pattern"]
    if args.get("path_filter"):
        payload["path_filter"] = args["path_filter"]
    payload["mode"] = args.get("mode", "compact")
    payload["limit"] = args.get("limit", 10)
    if args.get("regex") is not None:
        payload["regex"] = args["regex"]

    return _run_cbm({**payload, "_cli_tool": "search_code"})


def trace_path(args: dict, **kwargs) -> str:
    """Trace call paths through the graph."""
    payload = {
        "function_name": args["function_name"],
        "direction": args.get("direction", "both"),
        "depth": args.get("depth", 3),
    }
    project = args.get("project")
    if project:
        payload["project"] = project
    if args.get("include_tests"):
        payload["include_tests"] = True

    return _run_cbm({**payload, "_cli_tool": "trace_path"})


def get_architecture(args: dict, **kwargs) -> str:
    """Get architecture overview."""
    payload = {}
    if args.get("path"):
        payload["path"] = args["path"]
    if args.get("aspects"):
        payload["aspects"] = args["aspects"]

    return _run_cbm({**payload, "_cli_tool": "get_architecture"})


def query_graph(args: dict, **kwargs) -> str:
    """Execute a Cypher-like graph query."""
    payload = {"query": args["query"]}
    if args.get("max_rows") is not None:
        payload["max_rows"] = args["max_rows"]
    project = args.get("project")
    if project:
        payload["project"] = project

    return _run_cbm({**payload, "_cli_tool": "query_graph"})


def get_code_snippet(args: dict, **kwargs) -> str:
    """Read source code for a symbol by qualified name."""
    payload = {"qualified_name": args["qualified_name"]}
    project = args.get("project")
    if project:
        payload["project"] = project

    return _run_cbm({**payload, "_cli_tool": "get_code_snippet"})


def detect_changes(args: dict, **kwargs) -> str:
    """Map git diff to affected symbols."""
    return _run_cbm({"_cli_tool": "detect_changes"})


def get_graph_schema(args: dict, **kwargs) -> str:
    """Get graph schema."""
    project = args.get("project")
    payload = {}
    if project:
        payload["project"] = project
    return _run_cbm({**payload, "_cli_tool": "get_graph_schema"})


def list_projects(args: dict, **kwargs) -> str:
    """List indexed projects."""
    return _run_cbm({"_cli_tool": "list_projects"})


def delete_project(args: dict, **kwargs) -> str:
    """Delete a project from the graph."""
    return _run_cbm({"project": args["project"], "_cli_tool": "delete_project"})


def detect_dead_code(args: dict, **kwargs) -> str:
    """Find dead code via search_graph with degree filter."""
    project = args.get("project")
    payload = {
        "query": "Method",
        "label": "Method",
        "max_degree": 0,
        "limit": args.get("limit", 50),
    }
    if project:
        payload["project"] = project
    return _run_cbm({**payload, "_cli_tool": "search_graph"})
