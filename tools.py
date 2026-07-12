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
        os.path.join(home, ".local", "bin", "codebase-memory-mcp.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            _BINARY = c
            return _BINARY

    return None


def _ensure_binary() -> Optional[str]:
    """Find or auto-install the codebase-memory-mcp binary."""
    binary = _find_binary()
    if binary:
        return binary

    # Auto-install
    logger.info("CBM: binary not found, downloading...")
    try:
        return _download_binary()
    except Exception as e:
        logger.warning("CBM: auto-install failed: %s", e)
        return None


def _download_binary() -> Optional[str]:
    """Download codebase-memory-mcp binary from GitHub releases."""
    import platform
    import zipfile
    import tarfile
    import io
    import stat
    from urllib.request import urlopen, Request

    system = platform.system().lower()  # windows, linux, darwin
    machine = platform.machine().lower()  # amd64, x86_64, arm64, aarch64

    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        logger.warning("CBM: unsupported architecture: %s", machine)
        return None

    if system == "windows":
        asset = f"codebase-memory-mcp-windows-{arch}.zip"
        ext = ".zip"
    elif system == "darwin":
        asset = f"codebase-memory-mcp-darwin-{arch}.tar.gz"
        ext = ".tar.gz"
    elif system == "linux":
        asset = f"codebase-memory-mcp-linux-{arch}.tar.gz"
        ext = ".tar.gz"
    else:
        logger.warning("CBM: unsupported OS: %s", system)
        return None

    # Get latest release URL
    api_url = "https://api.github.com/repos/DeusData/codebase-memory-mcp/releases/latest"
    req = Request(api_url, headers={"Accept": "application/vnd.github.v3+json"})
    with urlopen(req, timeout=30) as resp:
        release = json.loads(resp.read())

    download_url = None
    for a in release.get("assets", []):
        if a["name"] == asset:
            download_url = a["browser_download_url"]
            break

    if not download_url:
        logger.warning("CBM: release asset not found: %s", asset)
        return None

    # Download
    logger.info("CBM: downloading %s...", asset)
    req = Request(download_url)
    with urlopen(req, timeout=120) as resp:
        data = resp.read()

    # Install to ~/.local/bin/
    install_dir = os.path.join(os.path.expanduser("~"), ".local", "bin")

    os.makedirs(install_dir, exist_ok=True)

    binary_name = "codebase-memory-mcp.exe" if system == "windows" else "codebase-memory-mcp"
    dest = os.path.join(install_dir, binary_name)

    # Extract
    if ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Find the binary in the zip
            for name in zf.namelist():
                if name.endswith(binary_name) or name == binary_name:
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        dst.write(src.read())
                    break
            else:
                # Fallback: extract all and look for executable
                zf.extractall(install_dir)
    elif ext == ".tar.gz":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for member in tf.getmembers():
                if member.name.endswith(binary_name) or member.name == binary_name:
                    src = tf.extractfile(member)
                    with open(dest, "wb") as dst:
                        dst.write(src.read())
                    break

    # Make executable (Unix)
    if system != "windows":
        os.chmod(dest, os.stat(dest).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    if os.path.isfile(dest):
        global _BINARY
        _BINARY = dest
        logger.info("CBM: installed binary to %s", dest)
        return dest

    logger.warning("CBM: extraction failed, binary not found at %s", dest)
    return None

def _get_project_from_cwd() -> str:
    """Convert CWD to project name: path separators → dashes."""
    return os.getcwd().replace("\\", "-").replace("/", "-").replace(":", "")

def _run_cbm(args: dict, timeout: int = 30) -> str:
    """Run a codebase-memory-mcp CLI command and return JSON output."""
    if "project" not in args:
        args["project"] = _get_project_from_cwd()
    binary = _ensure_binary()
    if not binary:
        return json.dumps({
            "error": "codebase-memory-mcp binary not found and auto-install failed."
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
    binary = _ensure_binary()
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
