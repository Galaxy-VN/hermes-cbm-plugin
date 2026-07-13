"""Auto-indexing logic for the current project."""
import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger("cbm")

# Track what's been indexed in this session
_indexed_projects: dict = {}  # path -> project_name


def _detect_project_name(repo_path: str) -> Optional[str]:
    """Detect project name from git remote or directory name."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract name from URL: https://github.com/user/repo.git -> repo
            name = url.rstrip("/").rsplit("/", 1)[-1]
            name = name.removesuffix(".git")
            if name:
                return name
    except Exception:
        pass

    return os.path.basename(repo_path)


def _is_git_repo(path: str) -> bool:
    """Check if path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and "true" in result.stdout.lower()
    except Exception:
        return False


def auto_index_project(cwd: Optional[str] = None) -> Optional[str]:
    """
    Auto-index the current project if not already indexed.
    Returns the project name, or None if indexing failed/skipped.
    """
    from .tools import _find_binary, _run_cbm

    binary = _find_binary()
    if not binary:
        logger.debug("CBM binary not found, skipping auto-index")
        return None

    repo_path = cwd or os.getcwd()
    repo_path = os.path.abspath(repo_path)

    # Skip if not a git repo
    if not _is_git_repo(repo_path):
        logger.debug("Not a git repo: %s, skipping auto-index", repo_path)
        return None

    # Check if already indexed
    if repo_path in _indexed_projects:
        return _indexed_projects[repo_path]

    # Check with list_projects
    try:
        from .tools import _run_detached
        rc, out, _ = _run_detached([binary, "cli", "list_projects"], timeout=30)
        if rc == 0 and out.strip():
            projects = json.loads(out)
            project_list = projects if isinstance(projects, list) else projects.get("projects", [])
            project_name = _detect_project_name(repo_path)

            for p in project_list:
                p_name = p.get("name", "")
                p_path = p.get("path", "")
                if p_name == project_name or os.path.abspath(p_path) == repo_path:
                    _indexed_projects[repo_path] = p_name
                    logger.info("CBM: project already indexed: %s", p_name)
                    return p_name
    except Exception as e:
        logger.debug("CBM list_projects failed: %s", e)

    # Index the project
    project_name = _detect_project_name(repo_path)
    logger.info("CBM: auto-indexing project: %s at %s", project_name, repo_path)

    try:
        result = subprocess.run(
            [binary, "cli", "index_repository", json.dumps({
                "repo_path": repo_path,
                "project_name": project_name,
            })],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "CBM_LOG_LEVEL": "warn"},
        )
        if result.returncode == 0:
            _indexed_projects[repo_path] = project_name
            logger.info("CBM: indexed project: %s", project_name)
            return project_name
        else:
            logger.warning("CBM: indexing failed: %s", result.stderr.strip())
            return None
    except subprocess.TimeoutExpired:
        logger.warning("CBM: indexing timed out for %s", repo_path)
        return None
    except Exception as e:
        logger.warning("CBM: indexing error: %s", e)
        return None
