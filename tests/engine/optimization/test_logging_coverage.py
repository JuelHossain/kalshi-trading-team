"""
Comprehensive tests for verifying logging coverage across the codebase.

This test suite ensures:
- All critical functions have proper logging
- Error paths are logged appropriately
- Important state changes are logged
- Log levels are used correctly
- Critical modules have comprehensive logging
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


# =============================================================================
# Helper Functions
# =============================================================================

def extract_function_with_logging(
    tree: ast.Module,
    analyzer_class: type
) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract functions and their logging statements.

    Args:
        tree: AST tree of the module
        analyzer_class: FunctionAnalyzer class

    Returns:
        Tuple of (functions, logging_calls)
    """
    analyzer = analyzer_class(str(tree))
    analyzer.visit(tree)
    return analyzer.functions, analyzer.logging_calls


def has_logging_in_function(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    logging_calls: List[Dict]
) -> bool:
    """
    Check if a function contains any logging statements.

    Args:
        func_node: Function AST node
        logging_calls: List of logging calls in the module

    Returns:
        bool: True if function has logging
    """
    func_start = func_node.lineno
    func_end = func_node.end_lineno or func_start

    for log_call in logging_calls:
        if func_start <= log_call["lineno"] <= func_end:
            return True
    return False


# =============================================================================
# Test: Critical Functions Have Logging
# =============================================================================

@pytest.mark.logging
def test_critical_functions_have_logging(
    ast_cache: Dict[Path, ast.Module],
    function_analyzer: type,
    critical_modules: Dict[str, Path]
) -> None:
    """
    Test that all critical functions have logging statements.

    Ensures that public functions in critical modules
    have appropriate logging for observability.

    Args:
        ast_cache: Cached AST trees for all files
        function_analyzer: FunctionAnalyzer class
        critical_modules: Dictionary of critical module paths
    """
    violations = []

    for module_name, module_path in critical_modules.items():
        if module_path not in ast_cache:
            continue

        tree = ast_cache[module_path]
        functions, logging_calls = extract_function_with_logging(
            tree, function_analyzer
        )

        # Check public functions (not starting with _)
        for func in functions:
            if func["name"].startswith("_"):
                continue  # Skip private functions

            # Get the function node
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == func["name"]:
                        func_node = node
                        break

            if not func_node:
                continue

            # Check if function has logging
            if not has_logging_in_function(func_node, logging_calls):
                violations.append({
                    "module": module_name,
                    "function": func["name"],
                    "line": func["lineno"],
                })

    if violations:
        violation_details = "\n".join([
            f"  {v['module']}.{v['function']}() at line {v['line']}"
            for v in violations[:20]  # Show first 20
        ])
        pytest.fail(
            f"Found {len(violations)} critical functions without logging:\n"
            f"{violation_details}\n"
            f"Please add logging to all public critical functions."
        )


@pytest.mark.logging
def test_entry_exit_points_logged(
    ast_cache: Dict[Path, ast.Module],
    function_analyzer: type,
    engine_root: Path
) -> None:
    """
    Test that entry and exit points are logged.

    Ensures that API endpoints and main entry points
    have logging for request tracking.

    Args:
        ast_cache: Cached AST trees for all files
        function_analyzer: FunctionAnalyzer class
        engine_root: Path to engine root directory
    """
    # Check HTTP API server
    server_path = engine_root / "http_api" / "server.py"
    if server_path not in ast_cache:
        pytest.skip("HTTP server file not in cache")

    tree = ast_cache[server_path]
    functions, logging_calls = extract_function_with_logging(tree, function_analyzer)

    # Find API endpoint functions (typically decorated)
    unlogged_endpoints = []

    for func in functions:
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func["name"]:
                    func_node = node
                    break

        if not func_node:
            continue

        # Check if it's an endpoint (has route-like decorators or name)
        is_endpoint = (
            "route" in str(func["decorator_list"]).lower() or
            "get" in func["name"].lower() or
            "post" in func["name"].lower() or
            "endpoint" in func["name"].lower()
        )

        if is_endpoint and not has_logging_in_function(func_node, logging_calls):
            unlogged_endpoints.append({
                "function": func["name"],
                "line": func["lineno"],
            })

    if unlogged_endpoints:
        pytest.fail(
            f"Found {len(unlogged_endpoints)} API endpoints without logging:\n" +
            "\n".join([
                f"  {e['function']}() at line {e['line']}"
                for e in unlogged_endpoints
            ]) +
            "\nAll API endpoints should log requests."
        )


@pytest.mark.logging
def test_external_api_calls_logged(
    ast_cache: Dict[Path, ast.Module],
    function_analyzer: type
) -> None:
    """
    Test that external API calls have logging.

    Ensures that calls to external services (Kalshi, OpenAI, etc.)
    are logged for debugging and monitoring.

    Args:
        ast_cache: Cached AST trees for all files
        function_analyzer: FunctionAnalyzer class
    """
    violations = []

    for file_path, tree in ast_cache.items():
        if "test" in str(file_path):
            continue

        functions, logging_calls = extract_function_with_logging(
            tree, function_analyzer
        )

        for func in functions:
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == func["name"]:
                        func_node = node
                        break

            if not func_node:
                continue

            # Check if function makes external API calls
            has_external_call = False
            for node in ast.walk(func_node):
                if isinstance(node, ast.Call):
                    call_name = ast.unparse(node.func)
                    # Check for common API call patterns
                    if any(pattern in call_name.lower() for pattern in [
                        "kalshi", "openai", "request", "fetch",
                        "get_", "post_", "query_", "client.",
                    ]):
                        has_external_call = True
                        break

            if has_external_call and not has_logging_in_function(
                func_node, logging_calls
            ):
                violations.append({
                    "file": str(file_path),
                    "function": func["name"],
                    "line": func["lineno"],
                })

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['function']}()"
            for v in violations[:15]
        ])
        pytest.fail(
            f"Found {len(violations)} functions with external API calls but no logging:\n"
            f"{violation_details}\n"
            f"External API calls should be logged for monitoring."
        )


# =============================================================================
# Test: Error Paths Are Logged
# =============================================================================

@pytest.mark.logging
def test_exception_handlers_have_logging(
    ast_cache: Dict[Path, ast.Module],
    function_analyzer: type
) -> None:
    """
    Test that exception handlers have logging.

    Ensures that all except blocks log the error
    for proper debugging and monitoring.

    Args:
        ast_cache: Cached AST trees for all files
        function_analyzer: FunctionAnalyzer class
    """
    violations = []

    for file_path, tree in ast_cache.items():
        if "test" in str(file_path):
            continue

        analyzer = function_analyzer(str(file_path))
        analyzer.visit(tree)

        # Get all exception handlers
        for handler in analyzer.exception_handlers:
            # Check if there's logging in the handler
            handler_has_logging = False

            # Walk the tree to find logging calls in exception handlers
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if node.lineno == handler["lineno"] + 1:  # Right after except
                        call_name = ast.unparse(node.func)
                        if "log" in call_name.lower():
                            handler_has_logging = True
                            break

            if not handler_has_logging:
                violations.append({
                    "file": str(file_path),
                    "line": handler["lineno"],
                    "type": handler["type"],
                })

    # Allow some violations for simple exception handlers
    if len(violations) > 20:
        pytest.fail(
            f"Found {len(violations)} exception handlers without logging.\n"
            f"Exception handlers should log errors for debugging."
        )


@pytest.mark.logging
def test_error_conditions_logged(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that error conditions are properly logged.

    Checks for common error conditions and ensures
    they have associated logging.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    # Patterns that indicate error conditions
    error_patterns = [
        (r"if\s+.*error", "error check"),
        (r"if\s+.*failed", "failure check"),
        (r"if\s+.*invalid", "validation check"),
        (r"if\s+not\s+.*:", "negation check"),
    ]

    violations = []

    for file_path, tree in ast_cache.items():
        if "test" in str(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        for pattern, desc in error_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                lines = content.split("\n")

                # Check next 5 lines for logging
                has_logging = False
                for i in range(line_num, min(line_num + 5, len(lines))):
                    if "log" in lines[i].lower():
                        has_logging = True
                        break

                if not has_logging:
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": line_num,
                        "pattern": desc,
                    })

    # Allow some violations for non-critical error checks
    if len(violations) > 30:
        pytest.fail(
            f"Found {len(violations)} error conditions without logging.\n"
            f"Important error conditions should be logged."
        )


# =============================================================================
# Test: State Changes Are Logged
# =============================================================================

@pytest.mark.logging
def test_vault_state_changes_logged(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that vault state changes are logged.

    Ensures that balance changes, transactions, and
    important vault state transitions are logged.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    vault_path = engine_root / "core" / "vault.py"

    if vault_path not in ast_cache:
        pytest.skip("Vault file not in cache")

    tree = ast_cache[vault_path]

    # Find state-changing functions
    state_change_functions = {
        "deposit", "withdraw", "trade", "update_balance",
        "add_transaction", "set_balance", "initialize",
    }

    try:
        with open(vault_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        pytest.skip("Could not read vault file")

    unlogged_state_changes = []

    for func_name in state_change_functions:
        # Check if function exists
        if f"def {func_name}" not in content:
            continue

        # Find the function
        func_match = re.search(
            rf"(?:async\s+)?def\s+{func_name}\s*\(",
            content
        )

        if not func_match:
            continue

        func_start = func_match.start()
        # Get function body (simplified)
        func_body_match = re.search(
            r"(?s)(:.*?)(?=\n    (?:async\s+)?def|\nclass|\Z)",
            content[func_start:]
        )

        if func_body_match:
            func_body = func_body_match.group(1)
            if "log" not in func_body.lower():
                unlogged_state_changes.append(func_name)

    if unlogged_state_changes:
        pytest.fail(
            f"Found state change functions without logging: {unlogged_state_changes}\n"
            f"Vault state changes must be logged for audit trail."
        )


@pytest.mark.logging
def test_agent_state_transitions_logged(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that agent state transitions are logged.

    Ensures that agent startup, shutdown, and state
    changes are properly logged.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    agent_files = [
        "agents/brain/agent.py",
        "agents/senses/agent.py",
        "agents/soul/agent.py",
        "agents/hand/agent.py",
    ]

    violations = []

    for rel_path in agent_files:
        file_path = engine_root / rel_path
        if file_path not in ast_cache:
            continue

        tree = ast_cache[file_path]

        # Look for state transition methods
        state_methods = ["start", "stop", "initialize", "shutdown", "run"]

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        for method in state_methods:
            if f"def {method}" not in content:
                continue

            # Check if method has logging
            method_match = re.search(
                rf"(?:async\s+)?def\s+{method}\s*\(",
                content
            )

            if method_match:
                method_start = method_match.start()
                method_body_match = re.search(
                    r"(?s)(:.*?)(?=\n    (?:async\s+)?def|\nclass|\Z)",
                    content[method_start:]
                )

                if method_body_match:
                    method_body = method_body_match.group(1)
                    if "log" not in method_body.lower():
                        violations.append({
                            "agent": rel_path,
                            "method": method,
                        })

    if violations:
        violation_details = "\n".join([
            f"  {v['agent']} - {v['method']}()"
            for v in violations
        ])
        pytest.fail(
            f"Found agent state transitions without logging:\n"
            f"{violation_details}\n"
            f"Agent state changes should be logged."
        )


# =============================================================================
# Test: Log Levels Are Appropriate
# =============================================================================

@pytest.mark.logging
def test_error_level_used_for_errors(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that ERROR log level is used for actual errors.

    Ensures error logging uses the correct level.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    violations = []

    for file_path, tree in ast_cache.items():
        if "test" in str(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Check for error logging with wrong level
        # e.g., logging an exception with info() instead of error()
        wrong_error_logging = re.finditer(
            r"logger\.(info|debug|warning)\(.*(?:exception|error|failed)",
            content,
            re.IGNORECASE
        )

        for match in wrong_error_logging:
            line_num = content[:match.start()].count("\n") + 1
            violations.append({
                "file": str(file_path.relative_to(engine_root)),
                "line": line_num,
                "content": match.group(0),
            })

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['content'][:60]}"
            for v in violations[:10]
        ])
        pytest.fail(
            f"Found {len(violations)} instances of wrong log level for errors:\n"
            f"{violation_details}\n"
            f"Errors should use logger.error() or logger.exception()."
        )


@pytest.mark.logging
def test_critical_failures_use_critical_level(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that critical failures use CRITICAL log level.

    Ensures system-critical failures are marked appropriately.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    critical_keywords = [
        "fatal", "crash", "system failure", "shutdown",
        "catastrophic", "unrecoverable",
    ]

    violations = []

    for file_path, tree in ast_cache.items():
        if "test" in str(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        for keyword in critical_keywords:
            # Look for critical keywords not logged with critical()
            pattern = rf'logger\.(info|debug|warning|error)\([^)]*{keyword}'
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                violations.append({
                    "file": str(file_path.relative_to(engine_root)),
                    "line": line_num,
                    "keyword": keyword,
                    "content": match.group(0),
                })

    if violations:
        pytest.fail(
            f"Found {len(violations)} critical failures not using CRITICAL level.\n"
            f"Critical failures should use logger.critical()."
        )


# =============================================================================
# Test: Logging in Critical Modules
# =============================================================================

@pytest.mark.logging
def test_vault_has_comprehensive_logging(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that vault module has comprehensive logging.

    The vault handles financial operations and requires
    extensive logging for audit and debugging.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    vault_path = engine_root / "core" / "vault.py"

    if vault_path not in ast_cache:
        pytest.skip("Vault file not in cache")

    tree = ast_cache[vault_path]

    # Count logging statements
    logging_count = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = ast.unparse(node.func)
            if "log" in call_name.lower():
                logging_count += 1

    # Vault should have at least 10 logging statements
    if logging_count < 10:
        pytest.fail(
            f"Vault has only {logging_count} logging statements.\n"
            f"Expected at least 10 for comprehensive audit trail."
        )


@pytest.mark.logging
def test_brain_agent_logs_decisions(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that brain agent logs trading decisions.

    Ensures that buy/sell/hold decisions are logged
    for tracking and analysis.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    brain_path = engine_root / "agents" / "brain" / "agent.py"

    if brain_path not in ast_cache:
        pytest.skip("Brain agent file not in cache")

    try:
        with open(brain_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        pytest.skip("Could not read brain agent file")

    # Check for decision-related logging
    decision_patterns = [
        r"logger\.\w+\([^)]*decision",
        r"logger\.\w+\([^)]*buy",
        r"logger\.\w+\([^)]*sell",
        r"logger\.\w+\([^)]*hold",
        r"logger\.\w+\([^)]*signal",
    ]

    has_decision_logging = False
    for pattern in decision_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            has_decision_logging = True
            break

    if not has_decision_logging:
        pytest.fail(
            "Brain agent does not log trading decisions.\n"
            "All trading decisions should be logged."
        )


@pytest.mark.logging
def test_scanner_logs_market_scans(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that market scanner logs scan operations.

    Ensures that market scans are logged for monitoring.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    scanner_path = engine_root / "agents" / "senses" / "scanner.py"

    if scanner_path not in ast_cache:
        pytest.skip("Scanner file not in cache")

    try:
        with open(scanner_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        pytest.skip("Could not read scanner file")

    # Check for scan-related logging
    scan_patterns = [
        r"logger\.\w+\([^)]*scan",
        r"logger\.\w+\([^)]*market",
        r"logger\.\w+\([^)]*ticker",
        r"logger\.\w+\([^)]*fetched",
    ]

    has_scan_logging = any(
        re.search(pattern, content, re.IGNORECASE)
        for pattern in scan_patterns
    )

    if not has_scan_logging:
        pytest.fail(
            "Market scanner does not log scan operations.\n"
            "Market scans should be logged for monitoring."
        )


@pytest.mark.logging
def test_http_server_logs_requests(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that HTTP server logs API requests.

    Ensures that incoming requests are logged for
    access tracking and debugging.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    server_path = engine_root / "http_api" / "server.py"

    if server_path not in ast_cache:
        pytest.skip("HTTP server file not in cache")

    try:
        with open(server_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        pytest.skip("Could not read server file")

    # Check for request logging
    request_patterns = [
        r"logger\.\w+\([^)]*request",
        r"logger\.\w+\([^)]*endpoint",
        r"logger\.\w+\([^)]*GET|POST",
        r"@.*log.*request",
    ]

    has_request_logging = any(
        re.search(pattern, content, re.IGNORECASE)
        for pattern in request_patterns
    )

    if not has_request_logging:
        pytest.fail(
            "HTTP server does not log API requests.\n"
            "API requests should be logged for access tracking."
        )


# =============================================================================
# Test: Logging Best Practices
# =============================================================================

@pytest.mark.logging
def test_no_print_statements_in_production(
    python_files: List[Path],
    engine_root: Path
) -> None:
    """
    Test that print statements are not used in production code.

    Ensures all output goes through the logging system.

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
                for line_num, line in enumerate(f, 1):
                    # Check for print statements (not in comments)
                    stripped = line.strip()
                    if stripped.startswith("print(") and not stripped.startswith("#"):
                        violations.append({
                            "file": str(file_path.relative_to(engine_root)),
                            "line": line_num,
                            "content": stripped,
                        })
        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['content'][:60]}"
            for v in violations[:15]
        ])
        pytest.fail(
            f"Found {len(violations)} print statements in production code:\n"
            f"{violation_details}\n"
            f"Use logger instead of print for production code."
        )


@pytest.mark.logging
def test_log_messages_are_meaningful(
    engine_root: Path,
    ast_cache: Dict[Path, ast.Module]
) -> None:
    """
    Test that log messages provide meaningful information.

    Checks for empty log messages or very short messages
    that don't provide context.

    Args:
        engine_root: Path to engine root directory
        ast_cache: Cached AST trees for all files
    """
    violations = []

    for file_path, tree in ast_cache.items():
        if "test" in str(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Check for empty or very short log messages
        bad_log_patterns = [
            r'logger\.\w+\(["\']["\']',  # Empty string
            r'logger\.\w+\(["\'].["\']',  # Single character
            r'logger\.\w+\(["\'][a-z]["\']',  # Single letter
        ]

        for pattern in bad_log_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                violations.append({
                    "file": str(file_path.relative_to(engine_root)),
                    "line": line_num,
                    "content": match.group(0),
                })

    if violations:
        pytest.fail(
            f"Found {len(violations)} log messages that are not meaningful.\n"
            f"Log messages should provide context and information."
        )
