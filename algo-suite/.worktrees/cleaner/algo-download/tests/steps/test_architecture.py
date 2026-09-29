"""Step definitions for architecture.feature."""

from __future__ import annotations

import ast
from pathlib import Path

from pytest_bdd import scenarios, then, when

scenarios("../features/architecture.feature")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _PROJECT_ROOT / "src"
_CORE_MODULES = (
    "algo_download/source.py",
    "algo_download/orchestrator.py",
    "algo_download/registry.py",
    "algo_download/request.py",
    "algo_download/result.py",
)
_ADAPTER_IMPORT = "algo_download.adapters"
_HTTP_IMPORT_ROOTS = frozenset({"httpx", "requests", "urllib"})


def _module_path(module: str) -> Path:
    """Return the source path for a module relative to the algo-download package."""
    return _SRC_ROOT / module


def _imports(path: Path) -> tuple[str, ...]:
    """Return the top-level module imports declared in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return tuple(imports)


@when("I inspect the algo-download core modules")
def _inspect_core_modules(context: dict[str, object]) -> None:
    """Collect import declarations for every core module under review."""
    context["core_imports"] = {
        module: _imports(_module_path(module)) for module in _CORE_MODULES
    }


@then("no core module imports provider adapters")
def _no_adapter_imports(context: dict[str, object]) -> None:
    """Assert that application core modules do not depend on provider adapters."""
    imports_by_module = context["core_imports"]
    assert isinstance(imports_by_module, dict)
    violations = {
        module: imports
        for module, imports in imports_by_module.items()
        if any(
            imported == _ADAPTER_IMPORT or imported.startswith(f"{_ADAPTER_IMPORT}.")
            for imported in imports
        )
    }
    assert violations == {}


@then("no core module imports HTTP client libraries")
def _no_http_imports(context: dict[str, object]) -> None:
    """Assert that HTTP client details remain inside provider adapters."""
    imports_by_module = context["core_imports"]
    assert isinstance(imports_by_module, dict)
    violations = {
        module: imports
        for module, imports in imports_by_module.items()
        if any(imported.partition(".")[0] in _HTTP_IMPORT_ROOTS for imported in imports)
    }
    assert violations == {}
