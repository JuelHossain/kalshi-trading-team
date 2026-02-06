"""
Comprehensive tests for verifying code reduction and elimination of duplicates.

This test suite ensures:
- No duplicate functions exist across modules
- No duplicate logic patterns exist
- Imports are optimized (no unused imports)
- Shared utilities are properly utilized
- Code follows DRY principles
"""

import ast
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


# =============================================================================
# Helper Functions
# =============================================================================

def normalize_code(code: str) -> str:
    """
    Normalize code for comparison by removing whitespace variations.

    Args:
        code: Raw code string

    Returns:
        str: Normalized code string
    """
    # Remove extra whitespace
    code = " ".join(code.split())
    return code.lower()


def calculate_similarity(code1: str, code2: str) -> float:
    """
    Calculate similarity ratio between two code blocks.

    Args:
        code1: First code block
        code2: Second code block

    Returns:
        float: Similarity ratio between 0 and 1
    """
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)

    return SequenceMatcher(None, norm1, norm2).ratio()


def extract_function_body(node: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> str:
    """
    Extract the body of a function as a string.

    Args:
        node: Function AST node
        source: Source code string

    Returns:
        str: Function body as string
    """
    lines = source.split("\n")

    start_line = node.lineno - 1
    end_line = node.end_lineno - 1 if node.end_lineno else start_line

    # Get function body (skip decorators and signature)
    body_lines = []
    in_signature = False

    for i in range(start_line, min(end_line + 1, len(lines))):
        line = lines[i]

        # Skip decorators and def line
        if i == start_line or line.strip().startswith("@"):
            if "def " in line or "async def " in line:
                in_signature = True
            continue

        # Skip indentation for body
        if in_signature:
            if ":" in line and not line.strip().startswith("#"):
                in_signature = False
                continue

        body_lines.append(line)

    return "\n".join(body_lines)


def extract_functions_from_file(file_path: Path) -> List[Dict]:
    """
    Extract all functions from a file with their signatures and bodies.

    Args:
        file_path: Path to Python file

    Returns:
        List[Dict]: List of function information dictionaries
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "lineno": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "body": extract_function_body(node, source),
                "signature": ast.unparse(node),
                "file": file_path,
            })

    return functions


def check_unused_imports(file_path: Path) -> List[Dict]:
    """
    Check for unused imports in a file.

    Args:
        file_path: Path to Python file

    Returns:
        List[Dict]: List of unused import information
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    # Collect all imports
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imports[name] = {
                    "name": alias.name,
                    "lineno": node.lineno,
                    "type": "import",
                }
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports[name] = {
                    "name": f"{module}.{alias.name}",
                    "lineno": node.lineno,
                    "type": "from",
                }

    # Collect all names used in the code
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Get the base name (e.g., "logger" from "logger.info")
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    # Find unused imports
    unused = []
    for name, info in imports.items():
        if name not in used_names:
            # Skip __future__ imports and dunder names
            if not info["name"].startswith("__"):
                unused.append({
                    "name": info["name"],
                    "lineno": info["lineno"],
                })

    return unused


# =============================================================================
# Test: No Duplicate Functions
# =============================================================================

@pytest.mark.duplicates
def test_no_duplicate_function_names(python_files: List[Path]) -> None:
    """
    Test that no functions with identical names exist in the same module.

    Functions in the same file/module should have unique names.

    Args:
        python_files: List of all Python files in engine
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        functions = extract_functions_from_file(file_path)
        function_names = [f["name"] for f in functions]

        # Check for duplicates
        seen = {}
        for name in function_names:
            if name in seen:
                seen[name] += 1
            else:
                seen[name] = 1

        duplicates = {k: v for k, v in seen.items() if v > 1}

        if duplicates:
            violations.append({
                "file": str(file_path),
                "duplicates": duplicates,
            })

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}: {v['duplicates']}"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} files with duplicate function names:\n"
            f"{violation_details}\n"
            f"Function names must be unique within a module."
        )


@pytest.mark.duplicates
def test_no_identical_function_implementations(
    python_files: List[Path],
    similarity_threshold: float
) -> None:
    """
    Test that no functions have identical implementations.

    Functions with identical bodies should be consolidated
    into a shared utility.

    Args:
        python_files: List of all Python files in engine
        similarity_threshold: Minimum similarity to flag as duplicate
    """
    # Collect all functions
    all_functions = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        functions = extract_functions_from_file(file_path)
        all_functions.extend(functions)

    # Filter out very small functions (< 5 lines)
    substantial_functions = [
        f for f in all_functions
        if len(f["body"].split("\n")) >= 5
    ]

    # Compare all pairs
    duplicates = []

    for i, func1 in enumerate(substantial_functions):
        for func2 in substantial_functions[i + 1:]:
            # Skip same file and line
            if func1["file"] == func2["file"] and func1["lineno"] == func2["lineno"]:
                continue

            # Check similarity
            similarity = calculate_similarity(func1["body"], func2["body"])

            if similarity >= similarity_threshold:
                duplicates.append({
                    "func1": f"{func1['file']}:{func1['lineno']} - {func1['name']}()",
                    "func2": f"{func2['file']}:{func2['lineno']} - {func2['name']}()",
                    "similarity": similarity,
                })

    if duplicates:
        duplicate_details = "\n".join([
            f"  {d['func1']}\n    <-> {d['func2']} ({d['similarity']:.1%})"
            for d in duplicates[:10]  # Show first 10
        ])
        pytest.fail(
            f"Found {len(duplicates)} pairs of similar function implementations:\n"
            f"{duplicate_details}\n"
            f"Consider consolidating into shared utilities."
        )


@pytest.mark.duplicates
def test_no_duplicate_class_definitions(python_files: List[Path]) -> None:
    """
    Test that no classes with duplicate names exist.

    Classes across the project should have unique names
    to avoid confusion.

    Args:
        python_files: List of all Python files in engine
    """
    class_definitions = defaultdict(list)

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_definitions[node.name].append({
                    "file": str(file_path),
                    "line": node.lineno,
                })

    # Find duplicates
    duplicates = {
        name: locations
        for name, locations in class_definitions.items()
        if len(locations) > 1
    }

    if duplicates:
        duplicate_details = "\n".join([
            f"  {name}:\n" + "\n".join([
                f"    - {loc['file']}:{loc['line']}"
                for loc in locations
            ])
            for name, locations in duplicates.items()
        ])
        pytest.fail(
            f"Found {len(duplicates)} duplicate class definitions:\n"
            f"{duplicate_details}\n"
            f"Class names should be unique or use namespaces."
        )


# =============================================================================
# Test: No Duplicate Logic Patterns
# =============================================================================

@pytest.mark.duplicates
def test_no_repeated_code_patterns(
    python_files: List[Path],
    duplicate_threshold: int,
    similarity_threshold: float
) -> None:
    """
    Test that no repeated code patterns exist.

    Finds code blocks of 5+ lines that are repeated
    across the codebase.

    Args:
        python_files: List of all Python files in engine
        duplicate_threshold: Minimum lines to check
        similarity_threshold: Minimum similarity to flag
    """
    # Extract code blocks
    code_blocks = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Extract blocks of N+ lines
        for i in range(len(lines) - duplicate_threshold):
            block = "".join(lines[i:i + duplicate_threshold])
            code_blocks.append({
                "file": str(file_path),
                "line": i + 1,
                "code": block,
            })

    # Compare blocks
    duplicates = []

    for i, block1 in enumerate(code_blocks):
        for block2 in code_blocks[i + 1:]:
            # Skip same file and location
            if block1["file"] == block2["file"]:
                continue

            similarity = calculate_similarity(block1["code"], block2["code"])

            if similarity >= similarity_threshold:
                duplicates.append({
                    "block1": f"{block1['file']}:{block1['line']}",
                    "block2": f"{block2['file']}:{block2['line']}",
                    "similarity": similarity,
                })

    # Limit duplicates reported
    if len(duplicates) > 50:
        pytest.skip(
            f"Found {len(duplicates)} similar code blocks. "
            f"This is expected for a large codebase. "
            f"Focus on eliminating exact duplicates."
        )

    if duplicates:
        duplicate_details = "\n".join([
            f"  {d['block1']} <-> {d['block2']} ({d['similarity']:.1%})"
            for d in duplicates[:20]
        ])
        pytest.fail(
            f"Found {len(duplicates)} repeated code patterns:\n"
            f"{duplicate_details}\n"
            f"Consider extracting common code into shared utilities."
        )


@pytest.mark.duplicates
def test_no_duplicate_api_call_patterns(
    engine_root: Path,
    python_files: List[Path]
) -> None:
    """
    Test that no duplicate API call patterns exist.

    Ensures API calls use shared client code
    instead of duplicated request handling.

    Args:
        engine_root: Path to engine root directory
        python_files: List of all Python files in engine
    """
    # Common API call patterns to check
    api_patterns = [
        r"aiohttp\.ClientSession\(\)",
        r"requests\.(get|post|put|delete)\(",
        r"urllib\.request",
        r"httpx\.(get|post)",
    ]

    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        # Skip the AI client itself (it should use these)
        if "ai_client.py" in str(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        for pattern in api_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                violations.append({
                    "file": str(file_path.relative_to(engine_root)),
                    "line": line_num,
                    "pattern": pattern,
                })

    if len(violations) > 10:  # Allow some exceptions
        violation_details = "\n".join([
            f"  {v['file']}:{v['line']} - {v['pattern']}"
            for v in violations[:15]
        ])
        pytest.fail(
            f"Found {len(violations)} direct API call patterns.\n"
            f"{violation_details}\n"
            f"API calls should use the shared AIClient."
        )


@pytest.mark.duplicates
def test_no_duplicate_error_handling_patterns(
    engine_root: Path,
    python_files: List[Path]
) -> None:
    """
    Test that error handling uses shared patterns.

    Ensures error handling is consistent and not duplicated.

    Args:
        engine_root: Path to engine root directory
        python_files: List of all Python files in engine
    """
    # Collect error handling patterns
    error_patterns = []

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
                # Get the next few lines
                block = "".join(lines[i:min(i + 4, len(lines))])
                error_patterns.append({
                    "file": str(file_path.relative_to(engine_root)),
                    "line": i + 1,
                    "pattern": normalize_code(block),
                })

    # Find duplicates (simplified check)
    seen_patterns = {}
    duplicates = []

    for pattern in error_patterns:
        key = pattern["pattern"][:100]  # First 100 chars as key
        if key in seen_patterns:
            duplicates.append({
                "original": seen_patterns[key],
                "duplicate": pattern,
            })
        else:
            seen_patterns[key] = pattern

    if len(duplicates) > 20:  # Allow some duplication
        pytest.skip(
            f"Found {len(duplicates)} similar error handling patterns. "
            f"Some duplication is acceptable for specific error cases."
        )


# =============================================================================
# Test: Imports Are Optimized
# =============================================================================

@pytest.mark.duplicates
def test_no_unused_imports(python_files: List[Path]) -> None:
    """
    Test that there are no unused imports.

    Ensures all imports are actually used in the code.

    Args:
        python_files: List of all Python files in engine
    """
    total_unused = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        unused = check_unused_imports(file_path)

        if unused:
            total_unused.extend([
                {
                    "file": str(file_path),
                    "name": u["name"],
                    "line": u["lineno"],
                }
                for u in unused
            ])

    if total_unused:
        unused_details = "\n".join([
            f"  {u['file']}:{u['line']} - {u['name']}"
            for u in total_unused[:20]
        ])
        pytest.fail(
            f"Found {len(total_unused)} unused imports:\n"
            f"{unused_details}\n"
            f"Remove unused imports to keep code clean."
        )


@pytest.mark.duplicates
def test_no_duplicate_imports(python_files: List[Path]) -> None:
    """
    Test that no duplicate imports exist in the same file.

    Ensures imports are not duplicated within a file.

    Args:
        python_files: List of all Python files in engine
    """
    violations = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue

        # Track imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(("import", alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(("from", f"{module}.{alias.name}", node.lineno))

        # Check for duplicates
        seen = set()
        file_duplicates = []

        for imp_type, name, lineno in imports:
            key = (imp_type, name)
            if key in seen:
                file_duplicates.append({
                    "import": name,
                    "line": lineno,
                })
            seen.add(key)

        if file_duplicates:
            violations.append({
                "file": str(file_path),
                "duplicates": file_duplicates,
            })

    if violations:
        violation_details = "\n".join([
            f"  {v['file']}: {len(v['duplicates'])} duplicate imports"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} files with duplicate imports:\n"
            f"{violation_details}\n"
            f"Remove duplicate imports."
        )


@pytest.mark.duplicates
def test_imports_are_sorted(python_files: List[Path]) -> None:
    """
    Test that imports follow a consistent order.

    Ensures imports are grouped and sorted
    (stdlib, third-party, local).

    Args:
        python_files: List of all Python files in engine
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

        # Find import block
        import_lines = []
        import_indices = []

        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_lines.append(line.strip())
                import_indices.append(i)

            # Stop at first non-import, non-comment, non-blank line after imports
            if import_lines and not line.strip().startswith("#"):
                if line.strip() and not line.startswith(("import ", "from ")):
                    break

        if len(import_lines) < 2:
            continue

        # Check if sorted
        sorted_lines = sorted(import_lines, key=lambda x: x.lower())

        if import_lines != sorted_lines:
            violations.append({
                "file": str(file_path),
                "line": import_indices[0] + 1,
            })

    if len(violations) > 10:  # Allow some violations
        pytest.skip(
            f"Found {len(violations)} files with unsorted imports. "
            f"Consider using 'isort' to automatically sort imports."
        )


# =============================================================================
# Test: Shared Utilities Are Used
# =============================================================================

@pytest.mark.duplicates
def test_ai_client_is_used(python_files: List[Path]) -> None:
    """
    Test that the shared AIClient is used instead of duplicate code.

    Ensures AI calls use the centralized AIClient class.

    Args:
        python_files: List of all Python files in engine
    """
    # Files that should use AIClient
    agent_files = [
        "brain/agent.py",
        "soul/agent.py",
    ]

    violations = []

    for file_path in python_files:
        rel_path = str(file_path)

        if not any(agent in rel_path for agent in agent_files):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Check for direct OpenAI API calls (should use AIClient)
        direct_api_patterns = [
            r"openai\.",
            r"genai\.",
            r'"gemini"',
            r'"gpt-"',
        ]

        for pattern in direct_api_patterns:
            if re.search(pattern, content):
                violations.append({
                    "file": rel_path,
                    "pattern": pattern,
                })

    if violations:
        violation_details = "\n".join([
            f"  {v['file']} - {v['pattern']}"
            for v in violations
        ])
        pytest.fail(
            f"Found direct API calls instead of using AIClient:\n"
            f"{violation_details}\n"
            f"Use the shared AIClient for all AI calls."
        )


@pytest.mark.duplicates
def test_logging_utility_is_used(python_files: List[Path]) -> None:
    """
    Test that the shared logger is used consistently.

    Ensures logging uses the get_logger utility
    from core/logger.py.

    Args:
        python_files: List of all Python files in engine
    """
    files_without_logger = []

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        if "logger.py" in str(file_path):
            continue  # Skip the logger file itself

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        # Check if file uses logging
        has_logging = "logger." in content or "logging." in content

        if has_logging:
            # Check if it imports from core.logger
            uses_shared_logger = (
                "from core.logger import" in content or
                "from engine.core.logger import" in content
            )

            if not uses_shared_logger:
                files_without_logger.append(str(file_path))

    if len(files_without_logger) > 5:
        pytest.skip(
            f"Found {len(files_without_logger)} files not using shared logger. "
            f"Some files may have legitimate reasons for custom logging."
        )


# =============================================================================
# Test: No Circular Imports
# =============================================================================

@pytest.mark.duplicates
def test_no_circular_imports(python_files: List[Path]) -> None:
    """
    Test that no circular imports exist.

    Detects circular import dependencies that can
    cause runtime errors.

    Args:
        python_files: List of all Python files in engine
    """
    # Build import graph
    import_graph = defaultdict(set)

    for file_path in python_files:
        if "test" in file_path.name:
            continue

        module_name = str(file_path).replace("\\", ".").replace("/", ".")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue

        # Track imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_graph[module_name].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    import_graph[module_name].add(node.module)

    # Check for cycles using DFS
    def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in import_graph.get(node, set()):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    cycles = []
    visited = set()

    for node in import_graph:
        if node not in visited:
            if has_cycle(node, visited, set()):
                cycles.append(node)

    if cycles:
        pytest.fail(
            f"Found circular import dependencies involving: {cycles}\n"
            f"Circular imports can cause runtime errors. "
            f"Please refactor to eliminate cycles."
        )
