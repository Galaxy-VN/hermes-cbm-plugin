"""Tests for the CBM plugin."""
import json
import os
import subprocess
from unittest.mock import MagicMock, patch, mock_open

import pytest


class TestBinaryDetection:
    """Test binary path detection."""

    @patch("shutil.which", return_value="/usr/local/bin/codebase-memory-mcp")
    def test_find_binary_in_path(self, mock_which):
        import cbm.tools as t
        t._BINARY = None

        result = t._find_binary()
        assert result == "/usr/local/bin/codebase-memory-mcp"
        mock_which.assert_called_once_with("codebase-memory-mcp")

    @patch("shutil.which", return_value=None)
    @patch("os.path.isfile", return_value=False)
    def test_find_binary_not_found(self, mock_isfile, mock_which):
        import cbm.tools as t
        t._BINARY = None

        result = t._find_binary()
        assert result is None


class TestToolHandlers:
    """Test tool handler functions."""

    @patch("cbm.tools._run_cbm")
    def test_index_repository(self, mock_run):
        mock_run.return_value = '{"status": "indexed", "nodes": 100}'
        from cbm.tools import index_repository

        result = index_repository({"repo_path": "/tmp/test"})
        assert "indexed" in result
        mock_run.assert_called_once()

    @patch("cbm.tools._run_cbm")
    def test_search_graph(self, mock_run):
        mock_run.return_value = '{"results": [{"name": "main"}]}'
        from cbm.tools import search_graph

        result = search_graph({"query": "main function", "label": "Function"})
        assert "main" in result

    @patch("cbm.tools._run_cbm")
    def test_trace_path(self, mock_run):
        mock_run.return_value = '{"callers": [], "callees": []}'
        from cbm.tools import trace_path

        result = trace_path({"function_name": "process_order"})
        assert "callers" in result

    @patch("cbm.tools._run_cbm")
    def test_search_code(self, mock_run):
        mock_run.return_value = '{"matches": []}'
        from cbm.tools import search_code

        result = search_code({"pattern": "TODO"})
        assert "matches" in result

    @patch("cbm.tools._run_cbm")
    def test_get_architecture(self, mock_run):
        mock_run.return_value = '{"languages": ["python"]}'
        from cbm.tools import get_architecture

        result = get_architecture({})
        assert "python" in result

    @patch("cbm.tools._run_cbm")
    def test_query_graph(self, mock_run):
        mock_run.return_value = '{"results": []}'
        from cbm.tools import query_graph

        result = query_graph({"query": "MATCH (f:Function) RETURN f.name LIMIT 5"})
        assert "results" in result


class TestAutoIndex:
    """Test auto-indexing logic."""

    @patch("subprocess.run")
    def test_detect_project_name_from_git(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/my-project.git\n"
        )
        from cbm.auto_index import _detect_project_name

        name = _detect_project_name("/tmp/repo")
        assert name == "my-project"

    @patch("subprocess.run")
    def test_detect_project_name_fallback(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        from cbm.auto_index import _detect_project_name

        name = _detect_project_name("/tmp/my-project")
        assert name == "my-project"

    @patch("subprocess.run")
    def test_is_git_repo(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
        from cbm.auto_index import _is_git_repo

        assert _is_git_repo("/tmp/repo") is True

    @patch("subprocess.run")
    def test_is_not_git_repo(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="false\n")
        from cbm.auto_index import _is_git_repo

        assert _is_git_repo("/tmp/not-repo") is False


class TestSchemas:
    """Test that all schemas are valid."""

    def test_all_schemas_have_required_fields(self):
        from cbm.schemas import ALL_SCHEMAS

        for schema in ALL_SCHEMAS:
            assert "name" in schema, f"Schema missing 'name': {schema}"
            assert "description" in schema, f"Schema missing 'description': {schema}"
            assert "parameters" in schema, f"Schema missing 'parameters': {schema}"
            assert schema["parameters"]["type"] == "object"
            assert "properties" in schema["parameters"]

    def test_schema_count(self):
        from cbm.schemas import ALL_SCHEMAS
        assert len(ALL_SCHEMAS) == 12, f"Expected 12 schemas, got {len(ALL_SCHEMAS)}"

    def test_no_duplicate_names(self):
        from cbm.schemas import ALL_SCHEMAS
        names = [s["name"] for s in ALL_SCHEMAS]
        assert len(names) == len(set(names)), "Duplicate schema names found"

    def test_schema_names_match_handlers(self):
        from cbm.schemas import ALL_SCHEMAS
        from cbm.tools import (
            index_repository, search_graph, search_code, trace_path,
            get_architecture, query_graph, get_code_snippet,
            detect_dead_code, detect_changes, get_graph_schema,
            list_projects, delete_project,
        )

        handler_map = {
            "cbm_index": index_repository,
            "cbm_search": search_graph,
            "cbm_search_code": search_code,
            "cbm_trace": trace_path,
            "cbm_architecture": get_architecture,
            "cbm_query": query_graph,
            "cbm_code_snippet": get_code_snippet,
            "cbm_dead_code": detect_dead_code,
            "cbm_changes": detect_changes,
            "cbm_schema": get_graph_schema,
            "cbm_projects": list_projects,
            "cbm_delete": delete_project,
        }

        for schema in ALL_SCHEMAS:
            name = schema["name"]
            assert name in handler_map, f"No handler for schema: {name}"
            assert callable(handler_map[name]), f"Handler not callable: {name}"


class TestCLI:
    """Test CLI slash command handlers."""

    def test_help_command(self):
        from cbm.cli import _handle_cbm_slash

        result = _handle_cbm_slash("help")
        assert "cbm" in result.lower()
        assert "index" in result
        assert "search" in result

    def test_unknown_subcommand(self):
        from cbm.cli import _handle_cbm_slash

        result = _handle_cbm_slash("unknown")
        assert "Unknown" in result


class TestIntegration:
    """Integration tests (require CBM binary)."""

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/.local/bin/codebase-memory-mcp")),
        reason="CBM binary not installed"
    )
    def test_is_available(self):
        from cbm.tools import is_available
        assert is_available() is True
