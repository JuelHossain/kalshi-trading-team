"""
Comprehensive tests for verifying removal of mock data from production code.

This test suite ensures:
- No fallback mock data exists in AI responses
- All API calls use real data only
- No placeholder/MOCK prefixes exist in production code
- No hardcoded mock responses
- Real data is used in all critical paths
"""

import ast
import re
from pathlib import Path
from typing import List, Set, Tuple

import pytest


# =============================================================================
# Test: No Mock Patterns in Production Code
# =============================================================================

@pytest.mark.mock
def test_no_mock_prefixes_in_production_code(
    python_files: List[Path],
    mock_patterns: List[re.Pattern]
) -> None:
    """
    Test that no mock patterns exist in production code.

    Scans all Python files for common mock/placeholder patterns
    and ensures none are present in production code.

    Args:
        python_files: List of all Python files in engine
        mock_patterns: Regex patterns for mock detection
    """
    violations = []

    for file_path in python_files:
        # Skip test files themselves
        if "test" in file_path.name or "tests" in file_path.parts:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in mock_patterns:
                matches = pattern.finditer(content)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count("\n") + 1
                    line_content = content.split("\n")[line_num - 1].strip()

                    # Skip comments and docstrings
                    if line_content.startswith("#") or line_content.startswith('"""'):
                        continue

                    violations.append({
                        "file": str(file_path.relative_to(file_path.parents[2])),
                        "line": line_num,
                        "pattern": pattern.pattern,
                        "content": line_content,
                    })
        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - Pattern: {v['pattern']}\n    {v['content']}"
            for v in violations[:10]  # Show first 10
        ])
        pytest.fail(
            f"Found {len(violations)} mock pattern violations:\n"
            f"{violation_details}\n"
            f"Please remove all mock/placeholder patterns from production code."
        )


@pytest.mark.mock
def test_no_mock_imports_in_production(python_files: List[Path]) -> None:
    """
    Test that no mock imports exist in production code.

    Ensures that test-only imports (like unittest.mock)
    are not imported in production code.

    Args:
        python_files: List of all Python files in engine
    """
    mock_imports = {
        "unittest.mock",
        "mock",
        "mox",
        "flexmock",
        "doublex",
    }

    violations = []

    for file_path in python_files:
        # Skip test files
        if "test" in file_path.name or "tests" in file_path.parts:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(mock_import in alias.name for mock_import in mock_imports):
                            violations.append({
                                "file": str(file_path.relative_to(file_path.parents[2])),
                                "line": node.lineno,
                                "import": alias.name,
                            })
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(
                        mock_import in node.module
                        for mock_import in mock_imports
                    ):
                        violations.append({
                            "file": str(file_path.relative_to(file_path.parents[2])),
                            "line": node.lineno,
                            "import": node.module,
                        })
        except (SyntaxError, UnicodeDecodeError):
            continue

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - import {v['import']}"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} mock imports in production code:\n"
            f"{violation_details}\n"
            f"Mock imports should only be in test files."
        )


# =============================================================================
# Test: No Fallback Mock Data in AI Responses
# =============================================================================

@pytest.mark.mock
def test_no_fallback_mock_data_in_ai_client(
    engine_root: Path,
    api_mock_patterns: List[re.Pattern]
) -> None:
    """
    Test that AI client doesn't have fallback mock data.

    Ensures the AI client doesn't return mock data when
    real API calls fail.

    Args:
        engine_root: Path to engine root directory
        api_mock_patterns: Regex patterns for API mock detection
    """
    ai_client_path = engine_root / "core" / "ai_client.py"

    if not ai_client_path.exists():
        pytest.skip("AI client file not found")

    with open(ai_client_path, "r", encoding="utf-8") as f:
        content = f.read()

    violations = []

    # Check for mock return values in fallback logic
    fallback_section = re.search(
        r"def.*fallback.*:.*?(?=\n    def|\nclass|\Z)",
        content,
        re.DOTALL | re.IGNORECASE
    )

    if fallback_section:
        for pattern in api_mock_patterns:
            if pattern.search(fallback_section.group(0)):
                violations.append({
                    "pattern": pattern.pattern,
                    "context": "fallback method",
                })

    # Check for hardcoded mock responses
    hardcoded_return = re.search(
        r'return\s+["\'].*mock.*["\']',
        content,
        re.IGNORECASE
    )

    if hardcoded_return:
        violations.append({
            "pattern": "hardcoded mock return",
            "context": hardcoded_return.group(0),
        })

    if violations:
        pytest.fail(
            f"Found mock data in AI client fallback logic:\n"
            f"{violations}\n"
            f"AI client should fail gracefully or use real data only."
        )


@pytest.mark.mock
def test_real_api_calls_in_critical_modules(
    critical_modules: dict,
    api_mock_patterns: List[re.Pattern]
) -> None:
    """
    Test that critical modules use real API calls, not mocks.

    Args:
        critical_modules: Dictionary of critical module paths
        api_mock_patterns: Regex patterns for API mock detection
    """
    violations = []

    for module_name, module_path in critical_modules.items():
        if not module_path.exists():
            continue

        try:
            with open(module_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for API functions that might return mock data
            api_functions = re.finditer(
                r"async def (?:get_|fetch_|query_|call_).*?\(.*?\):",
                content
            )

            for func_match in api_functions:
                func_start = func_match.end()
                # Get function body (simplified)
                func_body_match = re.search(
                    r"(?s)(.*?)(?=\n    async def|\n    def|\nclass|\Z)",
                    content[func_start:]
                )

                if func_body_match:
                    func_body = func_body_match.group(1)

                    for pattern in api_mock_patterns:
                        if pattern.search(func_body):
                            violations.append({
                                "module": module_name,
                                "function": func_match.group(1),
                                "pattern": pattern.pattern,
                            })
        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if violations:
        violation_details = "\n".join([
            f"  {v['module']}.{v['function']}() - {v['pattern']}"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} API functions with mock data:\n"
            f"{violation_details}\n"
            f"Critical modules must use real API calls only."
        )


# =============================================================================
# Test: No Hardcoded Mock Data
# =============================================================================

@pytest.mark.mock
def test_no_hardcoded_mock_market_data(engine_root: Path) -> None:
    """
    Test that no hardcoded mock market data exists.

    Ensures market data is fetched from real sources,
    not hardcoded values.

    Args:
        engine_root: Path to engine root directory
    """
    # Common mock market data patterns
    mock_market_patterns = [
        r"price\s*=\s*[0-9]+\.?[0-9]*\s*#.*mock",
        r"market_id\s*=\s*['\"].*MOCK",
        r"ticker\s*=\s*['\"].*TEST",
        r"balance\s*=\s*[0-9]+\s*#.*test",
        r"position\s*=\s*{.*'mock'",
    ]

    violations = []

    for pattern in mock_market_patterns:
        for file_path in engine_root.rglob("*.py"):
            if "test" in file_path.name:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append({
                                "file": str(file_path.relative_to(engine_root)),
                                "line": line_num,
                                "content": line.strip(),
                            })
            except (UnicodeDecodeError, FileNotFoundError):
                continue

    if violations:
        pytest.fail(
            f"Found {len(violations)} instances of hardcoded mock market data.\n"
            f"All market data should come from real API calls."
        )


@pytest.mark.mock
def test_no_mock_trading_signals(engine_root: Path) -> None:
    """
    Test that no mock trading signals exist in production.

    Ensures trading signals are generated by real logic,
    not mock implementations.

    Args:
        engine_root: Path to engine root directory
    """
    mock_signal_patterns = [
        r"signal\s*=\s*['\"]((BUY|SELL|HOLD)_MOCK|MOCK_(BUY|SELL|HOLD))['\"]",
        r"confidence\s*=\s*0\.\d+\s*#.*mock",
        r"return\s*{\s*'signal':\s*['\"].*MOCK",
    ]

    violations = []

    for pattern in mock_signal_patterns:
        for file_path in engine_root.rglob("*.py"):
            if "test" in file_path.name:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1
                    violations.append({
                        "file": str(file_path.relative_to(engine_root)),
                        "line": line_num,
                        "content": match.group(0),
                    })
            except (UnicodeDecodeError, FileNotFoundError):
                continue

    if violations:
        pytest.fail(
            f"Found {len(violations)} mock trading signals.\n"
            f"All signals must be generated by real trading logic."
        )


# =============================================================================
# Test: Real Data in Critical Paths
# =============================================================================

@pytest.mark.mock
def test_vault_uses_real_data(engine_root: Path) -> None:
    """
    Test that vault operations use real data, not mock values.

    Ensures financial operations are based on real data.

    Args:
        engine_root: Path to engine root directory
    """
    vault_path = engine_root / "core" / "vault.py"

    if not vault_path.exists():
        pytest.skip("Vault file not found")

    with open(vault_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Look for mock data in vault operations
    issues = []

    # Check for hardcoded initial balances that look like mocks
    hardcoded_balance = re.search(
        r"initial.*balance.*=.*[0-9]+\s*#.*(?:mock|test|fake)",
        content,
        re.IGNORECASE
    )

    if hardcoded_balance:
        issues.append(f"Hardcoded mock balance: {hardcoded_balance.group(0)}")

    # Check for mock transaction data
    mock_transaction = re.search(
        r"transaction.*=.*{.*'mock'|'MOCK",
        content,
        re.IGNORECASE
    )

    if mock_transaction:
        issues.append(f"Mock transaction data: {mock_transaction.group(0)}")

    if issues:
        pytest.fail(
            f"Found mock data in vault operations:\n" + "\n".join(issues) +
            "\nVault must use real financial data only."
        )


@pytest.mark.mock
def test_trading_execution_uses_real_market_data(
    engine_root: Path
) -> None:
    """
    Test that trading execution uses real market data.

    Ensures trades are executed based on real market conditions.

    Args:
        engine_root: Path to engine root directory
    """
    execution_path = engine_root / "agents" / "hand" / "execution.py"

    if not execution_path.exists():
        pytest.skip("Execution file not found")

    with open(execution_path, "r", encoding="utf-8") as f:
        content = f.read()

    issues = []

    # Check for mock market data in execution
    mock_market_data = [
        r"market_price\s*=\s*[0-9]+\s*#.*mock",
        r"order.*=.*{.*'mock'",
        r"execution.*=.*['\"].*MOCK",
    ]

    for pattern in mock_market_data:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Pattern matched: {pattern}")

    if issues:
        pytest.fail(
            f"Found mock market data in trading execution:\n" + "\n".join(issues) +
            "\nExecution must use real market data from API."
        )


@pytest.mark.mock
def test_signal_generation_uses_real_inputs(engine_root: Path) -> None:
    """
    Test that signal generation uses real input data.

    Ensures trading signals are based on real market analysis.

    Args:
        engine_root: Path to engine root directory
    """
    # Check brain agent and scanner
    files_to_check = [
        engine_root / "agents" / "brain" / "agent.py",
        engine_root / "agents" / "senses" / "scanner.py",
    ]

    issues = []

    for file_path in files_to_check:
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for mock input data
        if re.search(r"market_data\s*=\s*{.*'mock'", content, re.IGNORECASE):
            issues.append(f"{file_path.name}: Mock market_data input")

        if re.search(r"analyze.*\(.*mock", content, re.IGNORECASE):
            issues.append(f"{file_path.name}: Mock function parameters")

    if issues:
        pytest.fail(
            f"Found mock inputs in signal generation:\n" + "\n".join(issues) +
            "\nSignal generation must use real market data."
        )


# =============================================================================
# Test: No TODO/FIXME Mocks in Production
# =============================================================================

@pytest.mark.mock
def test_no_todo_mock_implementations(python_files: List[Path]) -> None:
    """
    Test that no TODO comments reference mock implementations.

    Ensures all mock-related TODOs are resolved or moved to tests.

    Args:
        python_files: List of all Python files in engine
    """
    todo_mock_patterns = [
        r"# TODO:.*implement.*mock",
        r"# TODO:.*add.*real.*data",
        r"# FIXME:.*remove.*mock",
        r"# XXX:.*mock.*data",
    ]

    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in todo_mock_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append({
                                "file": str(file_path.relative_to(file_path.parents[2])),
                                "line": line_num,
                                "content": line.strip(),
                            })
        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if violations:
        pytest.fail(
            f"Found {len(violations)} TODO/FIXME comments about mock data.\n"
            f"Please resolve all mock-related TODOs before production."
        )


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.mock
@pytest.mark.slow
def test_end_to_end_no_mock_data_in_api_calls(
    engine_root: Path,
    mock_patterns: List[re.Pattern]
) -> None:
    """
    End-to-end test that no mock data exists in the full API call chain.

    This test traces through the entire flow from API calls to response handling
    to ensure no mock data is introduced at any point.

    Args:
        engine_root: Path to engine root directory
        mock_patterns: Regex patterns for mock detection
    """
    # Define the API call chain
    api_chain = [
        "agents/senses/scanner.py",      # Market data fetching
        "agents/brain/agent.py",         # Decision making
        "agents/hand/execution.py",      # Order execution
        "core/vault.py",                 # State management
    ]

    violations_in_chain = {}

    for rel_path in api_chain:
        file_path = engine_root / rel_path
        if not file_path.exists():
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            file_violations = []
            for pattern in mock_patterns:
                if pattern.search(content):
                    file_violations.append(pattern.pattern)

            if file_violations:
                violations_in_chain[rel_path] = file_violations

        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if violations_in_chain:
        pytest.fail(
            f"Found mock data in API call chain:\n" +
            "\n".join([
                f"  {file}: {', '.join(patterns)}"
                for file, patterns in violations_in_chain.items()
            ]) +
            "\nThe entire chain must use real data."
        )
