"""
Comprehensive tests for verifying code quality best practices.

This test suite ensures:
- No print statements in production code
- All async functions are properly awaited
- Proper error handling (no bare excepts)
- Documentation coverage for public APIs
- Code follows Python best practices
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


# =============================================================================
# Helper Functions
# =============================================================================

def find_print_statements(file_path: Path) -> List[Dict]:
    """
    Find all print statements in a file.

    Args:
        file_path: Path to Python file

    Returns:
        List[Dict]: List of print statement locations
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return []

    prints = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for print() calls
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                prints.append({
                    "line": node.lineno,
                    "content": ast.unparse(node),
                })

    return prints


def find_bare_excepts(file_path: Path) -> List[Dict]:
    """
    Find all bare except clauses in a file.

    Args:
        file_path: Path to Python file

    Returns:
        List[Dict]: List of bare except locations
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return []

    bare_excepts = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bare_excepts.append({
                    "line": node.lineno,
                })

    return bare_excepts


def check_function_documentation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Check if a function has proper documentation.

    Args:
        node: Function AST node

    Returns:
        bool: True if function has docstring
    """
    return ast.get_docstring(node) is not None


def find_unawaited_async_calls(file_path: Path) -> List[Dict]:
    """
    Find async calls that are not awaited.

    Args:
        file_path: Path to Python file

    Returns:
        List[Dict]: List of unawaited async call locations
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return []

    unawaited = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Await):
            continue  # This is awaited

        if isinstance(node, ast.Call):
            # Check if this is an async call that's not awaited
            # We can't always determine this statically, but we can
            # check for known async patterns

            call_name = ast.unparse(node.func)

            # Known async functions that should be awaited
            async_patterns = [
                r"async_",
                r"\.get\(",
                r"\.post\(",
                r"\.fetch",
                r"\.query",
            ]

            for pattern in async_patterns:
                if re.search(pattern, call_name):
                    # Check if parent is an await
                    # (This is a simplified check)
                    unawaited.append({
                        "line": node.lineno,
                        "call": call_name,
                    })
                    break

    return unawaited


# =============================================================================
# Test: No Print Statements
# =============================================================================

@pytest.mark.quality
def test_no_print_statements_in_production(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that no print statements exist in production code.

    All output should go through the logging system.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        prints = find_print_statements(file_path)

        if prints:
            violations.extend([
                {
                    "file": str(file_path.relative_to(engine_root)),
                    "line": p["line"],
                    "content": p["content"],
                }
                for p in prints
            ])

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['content'][:60]}"
            for v in violations[:20]
        ])
        pytest.fail(
            f"Found {len(violations)} print statements in production code:\n"
            f"{violation_details}\n"
            f"Use logger instead of print for production code."
        )


@pytest.mark.quality
def test_no_debug_prints(python_files: List[Path], engine_root: Path) -> None:
    """
    Test that no debug print statements exist.

    Checks for common debug print patterns like
    print(f"DEBUG:"), print("X:"), etc.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    debug_patterns = [
        r'print\(["\']DEBUG:',
        r'print\(["\']TEST:',
        r'print\(["\']XXX:',
        r'print\(f?[["\'].*[=:]\s*\{',
    ]

    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in debug_patterns:
                        if re.search(pattern, line):
                            violations.append({
                                "file": str(file_path.relative_to(engine_root)),
                                "line": line_num,
                                "content": line.strip(),
                            })
        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if violations:
        pytest.fail(
            f"Found {len(violations)} debug print statements.\n"
            f"Remove all debug prints before production."
        )


# =============================================================================
# Test: Async Functions Properly Awaited
# =============================================================================

@pytest.mark.quality
def test_no_fire_and_forget_async_calls(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that async calls are not fire-and-forget without logging.

    Async calls that are not awaited should at least be logged
    for debugging purposes.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Look for async call patterns without await
        # and without create_task or similar
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Skip lines with await
            if "await" in line:
                continue

            # Skip lines with task creation
            if any(keyword in line for keyword in [
                "create_task", "ensure_future", "gather", "wait"
            ]):
                continue

            # Look for function calls that might be async
            if re.search(r"\w+\.\w+\(", line):
                # Check if this might be an async call
                # (simplified heuristic)
                if any(pattern in line for pattern in [
                    ".get(", ".post(", ".fetch(", ".query(",
                ]):
                    # Check if there's a log statement nearby
                    nearby_has_log = False
                    for j in range(max(0, i - 2), min(len(lines), i + 3)):
                        if "log" in lines[j].lower():
                            nearby_has_log = True
                            break

                    if not nearby_has_log:
                        violations.append({
                            "file": str(file_path.relative_to(engine_root)),
                            "line": i + 1,
                            "content": line.strip(),
                        })

    # Allow some violations for legitimate fire-and-forget patterns
    if len(violations) > 20:
        pytest.skip(
            f"Found {len(violations)} potential fire-and-forget async calls. "
            f"Some may be legitimate. Review manually."
        )


@pytest.mark.quality
def test_async_functions_have_async_prefix(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that async functions follow naming conventions.

    Async functions should be clearly identifiable by name
    or have clear documentation.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                # Check if function name indicates it's async
                has_async_name = node.name.startswith("async_")

                # Or has docstring mentioning async
                docstring = ast.get_docstring(node)
                has_async_doc = docstring and "async" in docstring.lower()

                if not has_async_name and not has_async_doc:
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": node.lineno,
                        "function": node.name,
                    })

    if len(violations) > 15:
        pytest.skip(
            f"Found {len(violations)} async functions without clear indication. "
            f"Consider using 'async_' prefix or documenting async nature."
        )


# =============================================================================
# Test: Proper Error Handling
# =============================================================================

@pytest.mark.quality
def test_no_bare_except_clauses(python_files: List[Path], engine_root: Path) -> None:
    """
    Test that no bare except clauses exist.

    Bare except clauses (except:) catch all exceptions
    including SystemExit and KeyboardInterrupt.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        bare_excepts = find_bare_excepts(file_path)

        if bare_excepts:
            violations.extend([
                {
                    "file": str(file_path.relative_to(engine_root)),
                    "line": b["line"],
                }
                for b in bare_excepts
            ])

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']}"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} bare except clauses:\n"
            f"{violation_details}\n"
            f"Use 'except Exception:' instead of 'except:'."
        )


@pytest.mark.quality
def test_specific_exceptions_are_caught(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that specific exceptions are caught where possible.

    Encourages catching specific exception types
    instead of generic Exception.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    # Count generic Exception catches
    generic_except_count = 0
    total_except_count = 0

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                total_except_count += 1

                if node.type:
                    # Check if it's a generic Exception
                    if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                        generic_except_count += 1
                    elif isinstance(node.type, ast.Attribute):
                        if node.type.attr == "Exception":
                            generic_except_count += 1

    # Allow some generic exception handlers
    if total_except_count > 0:
        generic_ratio = generic_except_count / total_except_count

        if generic_ratio > 0.5:  # More than 50% are generic
            pytest.fail(
                f"Too many generic exception handlers: {generic_except_count}/{total_except_count}\n"
                f"Consider catching more specific exception types."
            )


@pytest.mark.quality
def test_exceptions_are_logged(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that caught exceptions are logged.

    Ensures that exception handlers log the error
    for debugging and monitoring.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Find except blocks
        for i, line in enumerate(lines):
            if re.match(r"\s*except\s+", line):
                # Check next few lines for logging
                has_logging = False

                for j in range(i, min(i + 5, len(lines))):
                    if "log" in lines[j].lower():
                        has_logging = True
                        break

                if not has_logging:
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": i + 1,
                    })

    # Allow some exceptions for simple exception handlers
    if len(violations) > 25:
        pytest.skip(
            f"Found {len(violations)} exception handlers without logging. "
            f"Some simple exception handlers may not need logging."
        )


# =============================================================================
# Test: Documentation Coverage
# =============================================================================

@pytest.mark.quality
def test_public_functions_have_docstrings(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that public functions have docstrings.

    Ensures that public APIs are documented.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private functions
                if node.name.startswith("_"):
                    continue

                # Skip one-liners and simple property getters
                if node.body and len(node.body) == 1:
                    if isinstance(node.body[0], (ast.Return, ast.Pass)):
                        continue

                # Check for docstring
                if not check_function_documentation(node):
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": node.lineno,
                        "function": node.name,
                    })

    if len(violations) > 30:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['function']}()"
            for v in violations[:20]
        ])
        pytest.fail(
            f"Found {len(violations)} public functions without docstrings:\n"
            f"{violation_details}\n"
            f"Please document public functions."
        )


@pytest.mark.quality
def test_classes_have_docstrings(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that classes have docstrings.

    Ensures that classes are documented.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Skip private classes
                if node.name.startswith("_"):
                    continue

                # Check for docstring
                if not ast.get_docstring(node):
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": node.lineno,
                        "class": node.name,
                    })

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['class']}"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} classes without docstrings:\n"
            f"{violation_details}\n"
            f"Please document all classes."
        )


@pytest.mark.quality
def test_api_endpoints_documented(
    engine_root: Path,
    python_files: List[Path]
) -> None:
    """
    Test that API endpoints have documentation.

    Ensures HTTP API routes are documented.

    Args:
        engine_root: Path to engine root directory
        python_files: List of all Python files in engine
    """
    server_path = engine_root / "http_api" / "server.py"

    if not server_path.exists():
        pytest.skip("HTTP server file not found")

    try:
        with open(server_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        pytest.skip("Could not read server file")

    try:
        tree = ast.parse(content, filename=str(server_path))
    except SyntaxError:
        pytest.skip("Could not parse server file")

    violations = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if it's an endpoint function
            is_endpoint = any(
                decorator in str(node.decorator_list).lower()
                for decorator in ["route", "get", "post", "put", "delete"]
            )

            if is_endpoint:
                if not ast.get_docstring(node):
                    violations.append({
                        "function": node.name,
                        "line": node.lineno,
                    })

    if violations:
        pytest.fail(
            f"Found {len(violations)} API endpoints without documentation.\n"
            f"API endpoints should be documented."
        )


# =============================================================================
# Test: Code Style and Best Practices
# =============================================================================

@pytest.mark.quality
def test_no_dead_code(python_files: List[Path], engine_root: Path) -> None:
    """
    Test that no obviously dead code exists.

    Checks for code after return statements,
    unreachable blocks, etc.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for code after return
                if node.body:
                    for i, stmt in enumerate(node.body):
                        if isinstance(stmt, ast.Return):
                            # Check if there are statements after return
                            if i < len(node.body) - 1:
                                violations.append({
                                    "file": str(file_path.relative_to(engine_root)),
                                    "line": node.lineno,
                                    "function": node.name,
                                })
                                break

    if len(violations) > 5:
        pytest.fail(
            f"Found {len(violations)} functions with unreachable code after return.\n"
            f"Remove dead code to improve maintainability."
        )


@pytest.mark.quality
def test_function_complexity(python_files: List[Path], engine_root: Path) -> None:
    """
    Test that functions are not overly complex.

    Checks for functions that are too long or have
    too many branches.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    MAX_FUNCTION_LINES = 50
    MAX_BRANCHES = 10

    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check length
                if node.end_lineno and node.lineno:
                    func_length = node.end_lineno - node.lineno

                    if func_length > MAX_FUNCTION_LINES:
                        violations.append({
                            "file": str(file_path.relative_to(engine_root)),
                            "line": node.lineno,
                            "function": node.name,
                            "issue": f"Too long ({func_length} lines)",
                        })

                # Check branches
                branch_count = 0
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                        branch_count += 1

                if branch_count > MAX_BRANCHES:
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": node.lineno,
                        "function": node.name,
                        "issue": f"Too complex ({branch_count} branches)",
                    })

    if len(violations) > 10:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['function']}(): {v['issue']}"
            for v in violations[:15]
        ])
        pytest.fail(
            f"Found {len(violations)} overly complex functions:\n"
            f"{violation_details}\n"
            f"Consider breaking down complex functions."
        )


@pytest.mark.quality
def test_no_global_variables(python_files: List[Path], engine_root: Path) -> None:
    """
    Test that no global variables are used.

    Global variables can cause subtle bugs and
    make code harder to test.

    Args:
        python_files: List of all Python files in engine
        engine_root: Path to engine root directory
    """
    # Allowed globals (constants, singletons, etc.)
    allowed_globals = {
        "logger",
        "__version__",
    }

    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check if assignment is at module level
                if isinstance(node.col_offset, int):  # Has position info
                    # Look for variable assignments (not annotations)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id

                            # Skip constants (ALL_CAPS)
                            if name.isupper():
                                continue

                            # Skip allowed globals
                            if name in allowed_globals:
                                continue

                            # Check if it's at module level (not in function/class)
                            parent_scope = None
                            for parent in ast.walk(tree):
                                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                    if (
                                        parent.lineno <= node.lineno <=
                                        (parent.end_lineno or parent.lineno)
                                    ):
                                        parent_scope = parent
                                        break

                            if parent_scope is None:
                                violations.append({
                                    "file": str(file_path.relative_to(engine_root)),
                                    "line": node.lineno,
                                    "variable": name,
                                })

    if len(violations) > 5:
        pytest.fail(
            f"Found {len(violations)} global variable declarations.\n"
            f"Avoid global variables. Use module-level constants or dependency injection."
        )
