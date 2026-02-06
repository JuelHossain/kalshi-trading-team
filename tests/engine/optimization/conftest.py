"""
Shared fixtures and utilities for optimization tests.

Provides common test fixtures for analyzing code quality,
detecting mock data, verifying logging coverage, and checking for duplicates.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def engine_root() -> Path:
    """
    Get the path to the engine root directory.

    Returns:
        Path: Absolute path to the engine directory
    """
    # Navigate from tests/engine/optimization/ to engine/
    current_path = Path(__file__).resolve()
    return current_path.parent.parent.parent / "engine"


@pytest.fixture(scope="session")
def python_files(engine_root: Path) -> List[Path]:
    """
    Get all Python files in the engine directory.

    Args:
        engine_root: Path to engine root directory

    Returns:
        List[Path]: All Python files found
    """
    return list(engine_root.rglob("*.py"))


@pytest.fixture(scope="session")
def critical_modules(engine_root: Path) -> Dict[str, Path]:
    """
    Get paths to critical modules that require special attention.

    Args:
        engine_root: Path to engine root directory

    Returns:
        Dict[str, Path]: Mapping of module name to file path
    """
    modules = {
        "vault": engine_root / "core" / "vault.py",
        "ai_client": engine_root / "core" / "ai_client.py",
        "brain_agent": engine_root / "agents" / "brain" / "agent.py",
        "senses_agent": engine_root / "agents" / "senses" / "agent.py",
        "soul_agent": engine_root / "agents" / "soul" / "agent.py",
        "scanner": engine_root / "agents" / "senses" / "scanner.py",
        "http_server": engine_root / "http_api" / "server.py",
    }

    # Filter to only existing modules
    return {k: v for k, v in modules.items() if v.exists()}


# =============================================================================
# Mock Detection Patterns
# =============================================================================

@pytest.fixture(scope="session")
def mock_patterns() -> List[re.Pattern]:
    """
    Get regex patterns that indicate mock/placeholder data.

    Returns:
        List[re.Pattern]: Compiled regex patterns for mock detection
    """
    patterns = [
        r"MOCK_",                      # MOCK_ prefix variables/functions
        r"mock_data",                  # mock_data variable
        r"fallback.*mock",             # fallback to mock
        r"placeholder",                # placeholder values
        r"TODO.*implement",            # unimplemented features
        r"FIXME.*mock",                # mock-related FIXMEs
        r"XXX.*mock",                  # mock-related XXX comments
        r"HACK.*mock",                 # mock-related HACKs
        r"fake.*data",                 # fake data references
        r"dummy.*data",                # dummy data references
        r"test_data.*production",      # test data in production
        r"hardcoded.*value",           # hardcoded values
        r"example\.com",               # example URLs
        r"placeholder\.com",           # placeholder URLs
    ]
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


@pytest.fixture(scope="session")
def api_mock_patterns() -> List[re.Pattern]:
    """
    Get patterns specific to API mocking.

    Returns:
        List[re.Pattern]: Compiled regex patterns for API mock detection
    """
    patterns = [
        r"return\s+{[^}]*}.*#.*mock",  # Mock return dict
        r"return\s+\".*\".*#.*mock",   # Mock return string
        r"simulate.*response",         # Simulated API responses
        r"mock.*response",             # Mock response objects
    ]
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


# =============================================================================
# AST Analysis Utilities
# =============================================================================

@pytest.fixture(scope="session")
def ast_cache(python_files: List[Path]) -> Dict[Path, ast.Module]:
    """
    Cache parsed AST trees for all Python files.

    Args:
        python_files: List of Python files to parse

    Returns:
        Dict[Path, ast.Module]: Mapping of file path to AST tree
    """
    cache = {}
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
                cache[file_path] = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            # Skip files that can't be parsed
            print(f"Warning: Could not parse {file_path}: {e}")
    return cache


class FunctionAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing function definitions and their properties."""

    def __init__(self, filename: str):
        self.filename = filename
        self.functions = []
        self.imports = []
        self.logging_calls = []
        self.exception_handlers = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition and collect metadata."""
        self.functions.append({
            "name": node.name,
            "lineno": node.lineno,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "has_docstring": ast.get_docstring(node) is not None,
            "decorator_list": [ast.unparse(d) for d in node.decorator_list],
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self.visit_FunctionDef(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            self.imports.append({
                "name": alias.name,
                "lineno": node.lineno,
                "alias": alias.asname,
            })

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from import statement."""
        module = node.module or ""
        for alias in node.names:
            self.imports.append({
                "name": f"{module}.{alias.name}",
                "lineno": node.lineno,
                "alias": alias.asname,
            })

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call and check for logging."""
        func_name = self._get_call_name(node)

        # Check for logging calls
        if func_name and any(log_method in func_name for log_method in [
            "logger.debug", "logger.info", "logger.warning",
            "logger.error", "logger.critical", "logger.exception",
            "log.debug", "log.info", "log.warning",
            "log.error", "log.critical", "log.exception",
        ]):
            self.logging_calls.append({
                "function": func_name,
                "lineno": node.lineno,
            })

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Visit exception handler."""
        self.exception_handlers.append({
            "type": ast.unparse(node.type) if node.type else "bare",
            "lineno": node.lineno,
        })
        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Extract the full name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return ast.unparse(node.func)
        return None


@pytest.fixture
def function_analyzer() -> type:
    """Return the FunctionAnalyzer class for AST analysis."""
    return FunctionAnalyzer


# =============================================================================
# Logging Capture Fixtures
# =============================================================================

@pytest.fixture
def log_capture() -> List[str]:
    """
    Create a list to capture log messages during tests.

    Returns:
        List[str]: List to store captured log messages
    """
    return []


@pytest.fixture
def mock_logger(log_capture: List[str]):
    """
    Create a mock logger that captures log messages.

    Args:
        log_capture: List to store captured messages

    Returns:
        Mock logger object
    """
    class MockLogger:
        def __init__(self, capture_list: List[str]):
            self._capture = capture_list
            self.name = "test_logger"

        def debug(self, msg: str, *args, **kwargs):
            self._capture.append(f"DEBUG: {msg}")

        def info(self, msg: str, *args, **kwargs):
            self._capture.append(f"INFO: {msg}")

        def warning(self, msg: str, *args, **kwargs):
            self._capture.append(f"WARNING: {msg}")

        def error(self, msg: str, *args, **kwargs):
            self._capture.append(f"ERROR: {msg}")

        def critical(self, msg: str, *args, **kwargs):
            self._capture.append(f"CRITICAL: {msg}")

        def exception(self, msg: str, *args, **kwargs):
            self._capture.append(f"EXCEPTION: {msg}")

    return MockLogger(log_capture)


# =============================================================================
# Code Analysis Helpers
# =============================================================================

@pytest.fixture(scope="session")
def duplicate_threshold() -> int:
    """
    Get the minimum number of lines for code to be considered a duplicate.

    Returns:
        int: Minimum lines for duplicate detection (default: 5)
    """
    return 5


@pytest.fixture(scope="session")
def similarity_threshold() -> float:
    """
    Get the similarity threshold for detecting similar code.

    Returns:
        float: Similarity ratio (default: 0.8)
    """
    return 0.8


@pytest.fixture
def code_similarity_checker():
    """
    Create a code similarity checker function.

    Returns:
        Callable that compares two code blocks for similarity
    """
    def check_similarity(code1: str, code2: str) -> float:
        """
        Calculate similarity ratio between two code blocks.

        Uses SequenceMatcher from difflib to calculate similarity.

        Args:
            code1: First code block
            code2: Second code block

        Returns:
            float: Similarity ratio between 0 and 1
        """
        from difflib import SequenceMatcher

        # Normalize whitespace
        code1_normalized = " ".join(code1.split())
        code2_normalized = " ".join(code2.split())

        return SequenceMatcher(None, code1_normalized, code2_normalized).ratio()

    return check_similarity


# =============================================================================
# Test Result Fixtures
# =============================================================================

@pytest.fixture
def test_results():
    """
    Create a dictionary to store test results for reporting.

    Returns:
        Dict: Dictionary to store test metrics
    """
    return {
        "mock_violations": [],
        "missing_logging": [],
        "duplicates_found": [],
        "quality_issues": [],
    }


# =============================================================================
# Test Skip Markers
# =============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers for optimization tests.

    Args:
        config: pytest config object
    """
    config.addinivalue_line(
        "markers",
        "mock: tests related to mock data detection"
    )
    config.addinivalue_line(
        "markers",
        "logging: tests related to logging coverage"
    )
    config.addinivalue_line(
        "markers",
        "duplicates: tests related to code duplication"
    )
    config.addinivalue_line(
        "markers",
        "quality: tests related to code quality"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
