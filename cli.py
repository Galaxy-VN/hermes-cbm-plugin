"""CLI and slash command handlers."""
import json
import os
import subprocess
from typing import Optional


def _handle_cbm_slash(raw_args: str) -> Optional[str]:
    """Handler for /cbm command."""
    from .tools import _find_binary, is_available

    argv = raw_args.strip().split()
    if not argv or argv[0] in ("help", "-h", "--help"):
        return (
            "/cbm — Codebase intelligence via codebase-memory-mcp\n\n"
            "Subcommands:\n"
            "  status     Show CBM binary status, indexed projects\n"
            "  index      Index the current project (or specify path)\n"
            "  search     Search the knowledge graph\n"
            "  trace      Trace call paths\n"
            "  arch       Architecture overview\n"
            "  dead       Find dead code\n"
            "  projects   List indexed projects\n"
            "  clear      Remove a project from the graph\n"
        )

    sub = argv[0]

    if sub == "status":
        lines = ["[cbm] Status:"]
        binary = _find_binary()
        if binary:
            lines.append(f"  Binary: {binary}")
            try:
                result = subprocess.run(
                    [binary, "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                lines.append(f"  Version: {result.stdout.strip()}")
            except Exception:
                lines.append("  Version: unknown")
        else:
            lines.append("  Binary: NOT FOUND")
            lines.append("  Install: curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash")
            return "\n".join(lines)

        # Show indexed projects
        try:
            result = subprocess.run(
                [binary, "cli", "list_projects"],
                capture_output=True, text=True, timeout=10,
                env={**os.environ, "CBM_LOG_LEVEL": "warn"},
            )
            if result.returncode == 0:
                projects = json.loads(result.stdout)
                project_list = projects if isinstance(projects, list) else projects.get("projects", [])
                lines.append(f"  Indexed projects: {len(project_list)}")
                for p in project_list[:10]:
                    name = p.get("name", "?")
                    nodes = p.get("node_count", "?")
                    edges = p.get("edge_count", "?")
                    lines.append(f"    {name}: {nodes} nodes, {edges} edges")
            else:
                lines.append("  Projects: unable to list")
        except Exception as e:
            lines.append(f"  Projects error: {e}")

        return "\n".join(lines)

    if sub == "index":
        from .auto_index import auto_index_project
        path = argv[1] if len(argv) > 1 else None
        project = auto_index_project(path)
        if project:
            return f"[cbm] Project indexed: {project}"
        return "[cbm] Indexing failed or skipped (not a git repo?)"

    if sub == "search":
        query = " ".join(argv[1:]) if len(argv) > 1 else ""
        if not query:
            return "Usage: /cbm search <query>"
        from .tools import search_graph
        result = search_graph({"query": query})
        return result

    if sub == "trace":
        func_name = argv[1] if len(argv) > 1 else ""
        if not func_name:
            return "Usage: /cbm trace <function_name>"
        from .tools import trace_path
        result = trace_path({"function_name": func_name})
        return result

    if sub == "arch":
        from .tools import get_architecture
        result = get_architecture({})
        return result

    if sub == "dead":
        from .tools import detect_dead_code
        result = detect_dead_code({})
        return result

    if sub == "projects":
        from .tools import list_projects
        result = list_projects({})
        return result

    if sub == "clear":
        project = argv[1] if len(argv) > 1 else ""
        if not project:
            return "Usage: /cbm clear <project_name>"
        from .tools import delete_project
        result = delete_project({"project": project})
        return result

    return f"Unknown subcommand: {sub}\nRun `/cbm help` for usage."
