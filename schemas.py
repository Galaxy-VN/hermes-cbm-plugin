"""Tool schemas — what the LLM sees for codebase-memory-mcp integration."""

INDEX_REPOSITORY = {
    "name": "cbm_index",
    "description": (
        "Index the current or specified repository into the codebase-memory knowledge graph. "
        "Must be called before any other cbm_* tools. Auto-sync keeps the graph fresh after indexing. "
        "Use this at the start of a session or when working with a new codebase."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "repo_path": {
                "type": "string",
                "description": "Absolute path to the repository root. Defaults to current working directory.",
            },
            "project_name": {
                "type": "string",
                "description": "Optional project name override. Auto-detected from git if omitted.",
            },
        },
        "required": [],
    },
}

SEARCH_GRAPH = {
    "name": "cbm_search",
    "description": (
        "Search the knowledge graph by label, name pattern, file pattern, or degree. "
        "Finds functions, classes, methods, interfaces, routes, and more — structural search, not text grep. "
        "Supports regex name patterns (e.g. '.*Handler.*'), label filters (Function, Class, Method), "
        "min/max degree, file scoping, and pagination. PREFER this over grep/search_files for code discovery."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Natural-language full-text search query. Tokens are split on whitespace; "
                    "camelCase identifiers are indexed as individual words. Results ranked with "
                    "structural boosting: Functions/Methods +10, Routes +8, Classes/Interfaces +5."
                ),
            },
            "name_pattern": {
                "type": "string",
                "description": "Regex pattern to match node names (e.g. '.*Handler.*', 'process_.*').",
            },
            "label": {
                "type": "string",
                "description": (
                    "Filter by node label: Function, Method, Class, Interface, Enum, Type, "
                    "Route, Resource, Package, File, Module."
                ),
            },
            "file_pattern": {
                "type": "string",
                "description": "Regex to filter by file path (e.g. 'src/api/.*').",
            },
            "min_degree": {
                "type": "integer",
                "description": "Minimum edge count (callers + callees) — finds highly-connected nodes.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return. Default 50.",
            },
            "offset": {
                "type": "integer",
                "description": "Skip first N results for pagination.",
            },
        },
        "required": [],
    },
}

SEARCH_CODE = {
    "name": "cbm_search_code",
    "description": (
        "Graph-augmented code search. Finds text patterns via grep, then enriches with knowledge graph: "
        "deduplicates into containing functions, ranks by structural importance. "
        "PREFER this over search_files for code-level grep — it gives you function context, not raw lines."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to search for in code.",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob for files to search (e.g. '*.py', '*.ts').",
            },
            "mode": {
                "type": "string",
                "enum": ["compact", "full", "files"],
                "description": "Result format: compact (signatures), full (with source), files (just paths).",
            },
            "limit": {
                "type": "integer",
                "description": "Max results. Default 10.",
            },
        },
        "required": ["pattern"],
    },
}

TRACE_PATH = {
    "name": "cbm_trace",
    "description": (
        "Trace call paths through the knowledge graph. Finds who calls a function and what it calls. "
        "BFS traversal with depth 1-5. PREFER this over grep for understanding call chains — "
        "it follows import-aware, type-inferred edges across files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "function_name": {
                "type": "string",
                "description": "Function or method name to trace (exact match).",
            },
            "direction": {
                "type": "string",
                "enum": ["inbound", "outbound", "both"],
                "description": "Trace callers (inbound), callees (outbound), or both. Default: both.",
            },
            "depth": {
                "type": "integer",
                "description": "Max traversal depth (1-5). Default: 3.",
            },
            "include_tests": {
                "type": "boolean",
                "description": "Include test files in results. Default: false.",
            },
        },
        "required": ["function_name"],
    },
}

GET_ARCHITECTURE = {
    "name": "cbm_architecture",
    "description": (
        "Get a high-level architecture overview of the codebase: languages, packages, entry points, "
        "routes, hotspots, boundaries, layers, and clusters (Louvain community detection). "
        "Use this to understand a codebase's structure without reading every file."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Optional directory prefix to scope the analysis.",
            },
            "aspects": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Aspects to include: overview, structure, dependencies, routes, languages, "
                    "packages, entry_points, hotspots, boundaries, layers, clusters. Default: all."
                ),
            },
        },
        "required": [],
    },
}

QUERY_GRAPH = {
    "name": "cbm_query",
    "description": (
        "Execute a Cypher-like read-only graph query. Supports MATCH, WHERE, RETURN, "
        "ORDER BY, LIMIT, aggregates (count, sum, avg, collect). "
        "Use for complex queries: 'MATCH (f:Function)-[:CALLS]->(g) WHERE f.name = 'main' RETURN g.name'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Cypher-like query string (read-only subset).",
            },
            "max_rows": {
                "type": "integer",
                "description": "Max rows to return. Default: unlimited (hard ceiling 100k).",
            },
        },
        "required": ["query"],
    },
}

GET_CODE_SNIPPET = {
    "name": "cbm_code_snippet",
    "description": (
        "Read source code for a function/class/method by its qualified name. "
        "Use cbm_search first to discover the exact qualified_name, then pass it here."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "qualified_name": {
                "type": "string",
                "description": "Full qualified name from cbm_search (e.g. 'myproject.src.utils.handler').",
            },
        },
        "required": ["qualified_name"],
    },
}

DEAD_CODE = {
    "name": "cbm_dead_code",
    "description": (
        "Find functions with zero callers (dead code). Excludes entry points (main, exported symbols). "
        "Uses Cypher query internally: MATCH (f:Function) WHERE NOT EXISTS { (f)<-[:CALLS]-() }."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

DETECT_CHANGES = {
    "name": "cbm_changes",
    "description": (
        "Map uncommitted git changes to affected symbols with blast radius and risk classification. "
        "Shows which functions/classes are impacted by your current diff."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_SCHEMA = {
    "name": "cbm_schema",
    "description": (
        "Get the knowledge graph schema: node labels, edge types, and their counts. "
        "Run this first to understand what data is available in the graph."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

LIST_PROJECTS = {
    "name": "cbm_projects",
    "description": "List all indexed projects with their node and edge counts.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

DELETE_PROJECT = {
    "name": "cbm_delete",
    "description": "Remove a project and all its graph data from the store.",
    "parameters": {
        "type": "object",
        "properties": {
            "project": {
                "type": "string",
                "description": "Project name to delete (use cbm_projects to list).",
            },
        },
        "required": ["project"],
    },
}

ALL_SCHEMAS = [
    INDEX_REPOSITORY,
    SEARCH_GRAPH,
    SEARCH_CODE,
    TRACE_PATH,
    GET_ARCHITECTURE,
    QUERY_GRAPH,
    GET_CODE_SNIPPET,
    DEAD_CODE,
    DETECT_CHANGES,
    GET_SCHEMA,
    LIST_PROJECTS,
    DELETE_PROJECT,
]
