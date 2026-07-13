"""CBM Plugin — codebase-memory-mcp integration for Hermes Agent.

Replaces grep with graph-backed structural queries: search, trace, architecture,
dead code detection, call graph traversal. 158 languages, sub-ms queries.
"""
import logging
import os
import subprocess
import sys
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger("cbm")

# Track the UI server process
_ui_process: Optional[subprocess.Popen] = None


def _start_ui_server(binary: str, port: int = 9749) -> None:
    """Start the MCP server in background for web UI access."""
    global _ui_process
    try:
        shim = str(Path(__file__).parent / "server_shim.py")
        _ui_process = subprocess.Popen(
            [sys.executable, shim, binary],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        logger.info("CBM server started (pid %d), UI at http://localhost:%d", _ui_process.pid, port)
    except Exception as e:
        logger.warning("CBM: failed to start server: %s", e)


def register(ctx: Any) -> None:
    """Wire schemas to handlers, register hooks and steering."""
    from . import schemas, tools, cli

    # ── Register tools ──────────────────────────────────────────────────
    TOOL_HANDLERS = {
        "cbm_index": tools.index_repository,
        "cbm_search": tools.search_graph,
        "cbm_search_code": tools.search_code,
        "cbm_trace": tools.trace_path,
        "cbm_architecture": tools.get_architecture,
        "cbm_query": tools.query_graph,
        "cbm_code_snippet": tools.get_code_snippet,
        "cbm_dead_code": tools.detect_dead_code,
        "cbm_changes": tools.detect_changes,
        "cbm_schema": tools.get_graph_schema,
        "cbm_projects": tools.list_projects,
        "cbm_delete": tools.delete_project,
    }

    for schema in schemas.ALL_SCHEMAS:
        tool_name = schema["name"]
        handler = TOOL_HANDLERS.get(tool_name)
        if handler:
            ctx.register_tool(
                name=tool_name,
                toolset="cbm",
                schema=schema,
                handler=handler,
            )

    # ── Register slash command ──────────────────────────────────────────
    ctx.register_command(
        "cbm",
        handler=cli._handle_cbm_slash,
        description="Codebase intelligence: graph search, call tracing, architecture.",
    )

    # ── Hook: auto-index on session start ────────────────────────────
    def _on_session_start(**kwargs: Any) -> None:
        """Auto-index the current project when a session starts."""
        from .auto_index import auto_index_project
        from .tools import _ensure_binary
        try:
            binary = _ensure_binary()
            if binary:
                logger.info("CBM: binary at %s", binary)
                auto_index_project()
                _start_ui_server(binary)
            else:
                logger.warning("CBM: binary not found after auto-install")
        except Exception as e:
            logger.warning("CBM: session start error: %s", e)

    ctx.register_hook("on_session_start", _on_session_start)

    # ── Hook: stop UI server on shutdown ─────────────────────────────
    def _on_session_end(**kwargs: Any) -> None:
        global _ui_process
        if _ui_process and _ui_process.poll() is None:
            _ui_process.terminate()
            logger.info("CBM server stopped (pid %d)", _ui_process.pid)
            _ui_process = None

    ctx.register_hook("on_session_end", _on_session_end)

    # ── Hook: inject graph context before LLM calls ────────────────────
    def _pre_llm_call_inject(**kwargs: Any) -> Optional[dict]:
        """
        Before each LLM turn, detect if the user is asking about code structure
        and inject relevant graph context (architecture overview, symbol counts).
        """
        try:
            user_message = kwargs.get("user_message", "")
            if not user_message:
                return None

            # Only inject for code-related queries
            code_keywords = [
                "function", "class", "call", "trace", "architecture",
                "structure", "where is", "who calls", "dependency",
                "import", "module", "package", "dead code", "refactor",
            ]
            msg_lower = user_message.lower()
            if not any(kw in msg_lower for kw in code_keywords):
                return None

            from .tools import _ensure_binary
            binary = _ensure_binary()
            if not binary:
                return None

            # Get project list to know what's indexed
            import subprocess, json
            result = subprocess.run(
                [binary, "cli", "list_projects"],
                capture_output=True, text=True, timeout=5,
                env={**os.environ, "CBM_LOG_LEVEL": "warn"},
            )
            if result.returncode != 0:
                return None

            projects = json.loads(result.stdout)
            project_list = projects if isinstance(projects, list) else projects.get("projects", [])
            if not project_list:
                return None

            # Inject a compact summary
            parts = ["[cbm context] Indexed projects available for graph queries:"]
            for p in project_list[:5]:
                name = p.get("name", "?")
                nodes = p.get("nodes", 0)
                parts.append(f"  {name}: {nodes} nodes")
            parts.append(
                "\nUse cbm_search, cbm_trace, cbm_architecture for code exploration. "
                "PREFER these over grep/search_files for structural queries."
            )

            return {"context": "\n".join(parts)}
        except Exception as e:
            logger.debug("CBM pre_llm_call hook error: %s", e)
            return None

    ctx.register_hook("pre_llm_call", _pre_llm_call_inject)

    # ── Register bundled skill ──────────────────────────────────────────
    _plugin_dir = Path(__file__).parent
    _skill_dir = _plugin_dir / "skills" / "cbm-intelligence"
    _skill_md = _skill_dir / "SKILL.md"
    if _skill_md.exists():
        ctx.register_skill(
            name="cbm-intelligence",
            path=_skill_md,
            description="Codebase intelligence via graph queries — replaces grep with structural search.",
        )

    # ── Inject into Hermes toolsets ─────────────────────────────────────
    try:
        import toolsets

        if "cbm" not in toolsets.TOOLSETS:
            toolsets.TOOLSETS["cbm"] = {
                "description": "Codebase intelligence via codebase-memory-mcp: graph search, call tracing, architecture, dead code.",
                "tools": list(TOOL_HANDLERS.keys()),
                "includes": [],
            }

        # Inject into core toolsets
        for t in TOOL_HANDLERS:
            if t not in toolsets._HERMES_CORE_TOOLS:
                toolsets._HERMES_CORE_TOOLS.append(t)

        for preset in ["hermes-acp", "hermes-api-server"]:
            if preset in toolsets.TOOLSETS:
                tools_list = toolsets.TOOLSETS[preset]["tools"]
                for t in TOOL_HANDLERS:
                    if t not in tools_list:
                        tools_list.append(t)

        # ── Steering hints on built-in tools ────────────────────────────
        import tools.registry

        # search_files → prefer cbm_search_code
        sf_entry = tools.registry.registry.get_entry("search_files")
        if sf_entry and "description" in sf_entry.schema:
            hint = (
                "\n\nFor code-level search (find functions, classes, patterns in source), "
                "PREFER cbm_search_code — it's graph-augmented, deduplicates into containing "
                "functions, and won't match comments or strings. Use cbm_search for structural "
                "queries (find by label, name pattern, degree)."
            )
            if hint not in sf_entry.schema["description"]:
                sf_entry.schema["description"] += hint

        # read_file → prefer cbm_code_snippet / cbm_search
        rf_entry = tools.registry.registry.get_entry("read_file")
        if rf_entry and "description" in rf_entry.schema:
            hint = (
                "\n\nFor understanding what a codebase contains (functions, classes, call chains), "
                "PREFER cbm_architecture for overview, cbm_search for finding specific symbols, "
                "or cbm_code_snippet to read a specific function. Much more token-efficient."
            )
            if hint not in rf_entry.schema["description"]:
                rf_entry.schema["description"] += hint

        # ── Refresh delegate_task toolsets ───────────────────────────────
        try:
            import tools.delegate_tool as dt

            dt._SUBAGENT_TOOLSETS = sorted(
                name for name, defn in toolsets.TOOLSETS.items()
                if name not in dt._EXCLUDED_TOOLSET_NAMES
                and not name.startswith("hermes-")
                and not all(t in dt.DELEGATE_BLOCKED_TOOLS for t in defn.get("tools", []))
            )
            dt._TOOLSET_LIST_STR = ", ".join(f"'{n}'" for n in dt._SUBAGENT_TOOLSETS)

            # Force cbm into default subagent toolsets
            if "cbm" not in dt.DEFAULT_TOOLSETS:
                dt.DEFAULT_TOOLSETS.append("cbm")

            # Inject steering into child prompts
            _CBM_STEERING = (
                "\n\n## Graph-Backed Code Intelligence (PREFER over grep/read_file)\n"
                "You have codebase-memory-mcp tools. USE THEM FIRST for any code exploration.\n\n"
                "**Discovery:**\n"
                "- `cbm_architecture()` — overview: languages, packages, entry points, clusters.\n"
                "- `cbm_search(label='Function', name_pattern='.*keyword.*')` — find symbols.\n"
                "- `cbm_search_code(pattern='text')` — graph-augmented grep.\n\n"
                "**Navigation:**\n"
                "- `cbm_trace(function_name='name')` — call chain: who calls what.\n"
                "- `cbm_code_snippet(qualified_name='...')` — read a specific function.\n"
                "- `cbm_query(query='MATCH ... RETURN ...')` — Cypher graph queries.\n\n"
                "**Quality:**\n"
                "- `cbm_dead_code()` — find unused functions.\n"
                "- `cbm_changes()` — blast radius of your current diff.\n"
                "- `cbm_schema()` — what's in the graph.\n\n"
                "**Workflow:** architecture → search → trace → code_snippet → edit.\n"
                "**Anti-pattern:** grep for a function name when cbm_search gives you the exact node."
            )

            _orig_build_prompt = dt._build_child_system_prompt

            def _patched_build_prompt(*args, **kwargs):
                base = _orig_build_prompt(*args, **kwargs)
                if _CBM_STEERING not in base:
                    base = base + _CBM_STEERING
                return base

            dt._build_child_system_prompt = _patched_build_prompt

            _orig_build_agent = dt._build_child_agent

            def _patched_build_agent(*args, **kwargs):
                ts = kwargs.get("toolsets")
                if ts is not None and "cbm" not in ts:
                    kwargs["toolsets"] = list(ts) + ["cbm"]
                return _orig_build_agent(*args, **kwargs)

            dt._build_child_agent = _patched_build_agent

            logger.info("CBM: refreshed delegate_task toolsets, forced cbm into defaults")
        except Exception as e:
            logger.warning("CBM: failed to refresh delegate_task toolsets: %s", e)

    except ImportError:
        logger.debug("CBM: toolsets module not available, skipping toolset injection")

    logger.info("CBM plugin registered: 12 tools, 2 hooks, /cbm command, 1 skill")

    # ── Start MCP server + auto-index on register ─────────────────
    try:
        from .auto_index import auto_index_project
        from .tools import _ensure_binary
        binary = _ensure_binary()
        if binary:
            logger.info("CBM: binary at %s", binary)
            auto_index_project()
            _start_ui_server(binary)
        else:
            logger.warning("CBM: binary not found after auto-install")
    except Exception as e:
        logger.warning("CBM: startup error: %s", e)
