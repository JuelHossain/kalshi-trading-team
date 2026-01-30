#!/usr/bin/env python3
"""
Test Generator Script for Sentient Alpha

Analyzes source files and generates appropriate test scaffolding.
Supports:
- .tsx files: Vitest + React Testing Library
- .ts files: Vitest for utilities/hooks
- .py files: pytest with mocks

Usage:
    python generate_test.py <file-path>
"""

import sys
import os
import re
import ast
from pathlib import Path
from typing import List, Tuple, Optional


def get_project_root() -> Path:
    """Find the project root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / "package.json").exists() or (current / "engine").exists():
            return current
        current = current.parent
    return Path.cwd()


def analyze_tsx_component(content: str, filename: str) -> dict:
    """Analyze a TSX file to extract component information."""
    info = {
        "component_name": None,
        "props": [],
        "hooks_used": [],
        "is_default_export": False,
        "imports": []
    }

    # Extract component name
    component_patterns = [
        r'export\s+default\s+function\s+(\w+)',
        r'export\s+function\s+(\w+)',
        r'export\s+const\s+(\w+)\s*=',
        r'function\s+(\w+)\s*\(',
        r'const\s+(\w+)\s*:\s*React\.FC',
    ]

    for pattern in component_patterns:
        match = re.search(pattern, content)
        if match:
            info["component_name"] = match.group(1)
            break

    # Check for default export
    info["is_default_export"] = "export default" in content

    # Extract props interface
    props_pattern = r'interface\s+(\w+Props?)\s*\{([^}]+)\}'
    props_match = re.search(props_pattern, content, re.DOTALL)
    if props_match:
        props_text = props_match.group(2)
        # Simple prop extraction
        prop_lines = [line.strip() for line in props_text.split('\n') if ':' in line.strip()]
        for line in prop_lines:
            if ':' in line:
                prop_name = line.split(':')[0].strip().replace('?', '')
                info["props"].append(prop_name)

    # Detect hooks used
    hooks = ['useState', 'useEffect', 'useCallback', 'useMemo', 'useRef', 'useContext']
    for hook in hooks:
        if hook in content:
            info["hooks_used"].append(hook)

    # Extract imports for mocking
    import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
    info["imports"] = re.findall(import_pattern, content)

    return info


def analyze_python_file(content: str, filename: str) -> dict:
    """Analyze a Python file to extract function and class information."""
    info = {
        "functions": [],
        "classes": [],
        "imports": [],
        "module_name": Path(filename).stem
    }

    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions and test functions
                if not node.name.startswith('_') and not node.name.startswith('test_'):
                    args = [arg.arg for arg in node.args.args if arg.arg != 'self']
                    info["functions"].append({
                        "name": node.name,
                        "args": args
                    })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if not item.name.startswith('_') or item.name == '__init__':
                            methods.append(item.name)
                info["classes"].append({
                    "name": node.name,
                    "methods": methods
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    info["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    info["imports"].append(node.module)
    except SyntaxError:
        pass

    return info


def generate_tsx_test(file_path: Path, info: dict) -> str:
    """Generate Vitest + React Testing Library test for a TSX component."""
    component_name = info["component_name"] or file_path.stem

    test_content = f'''import {{ describe, it, expect, vi }} from 'vitest';
import {{ render, screen, fireEvent }} from '@testing-library/react';
import {component_name} from '../{file_path.name}';

// Mock dependencies
{generate_tsx_mocks(info)}

describe('{component_name}', () => {{
  it('renders without crashing', () => {{
    render(<{component_name} />);
    // Add your assertions here
  }});

{generate_tsx_prop_tests(info)}
{generate_tsx_interaction_tests(info)}
}});
'''
    return test_content


def generate_tsx_mocks(info: dict) -> str:
    """Generate mock statements for TSX tests."""
    mocks = []

    # Mock common hooks if used
    if 'useRouter' in str(info.get('imports', [])):
        mocks.append("vi.mock('next/router', () => ({ useRouter: vi.fn() }));")

    # Add more mock patterns as needed
    return '\n'.join(mocks) if mocks else '// Add mocks here as needed'


def generate_tsx_prop_tests(info: dict) -> str:
    """Generate prop-based tests for TSX components."""
    if not info.get('props'):
        return ''

    tests = []
    for prop in info['props'][:3]:  # Limit to first 3 props
        tests.append(f'''  it('handles {prop} prop correctly', () => {{
    render(<{info['component_name']} {prop}="test-value" />);
    // Assert {prop} behavior
  }});''')

    return '\n\n'.join(tests)


def generate_tsx_interaction_tests(info: dict) -> str:
    """Generate interaction tests for TSX components."""
    if 'useState' in info.get('hooks_used', []):
        return '''  it('handles user interactions', () => {
    render(<''' + info['component_name'] + ''' />);
    // Add interaction tests
    // Example: fireEvent.click(screen.getByRole('button'));
  });'''
    return ''


def generate_ts_test(file_path: Path, info: dict) -> str:
    """Generate Vitest test for a TypeScript utility/hook file."""
    module_name = file_path.stem

    test_content = f'''import {{ describe, it, expect, vi, beforeEach, afterEach }} from 'vitest';
import * as {module_name} from '../{file_path.name}';

// Mock dependencies
vi.mock('../dependencies', () => ({{
  // Add mocks here
}}));

describe('{module_name}', () => {{
  beforeEach(() => {{
    // Setup before each test
  }});

  afterEach(() => {{
    // Cleanup after each test
    vi.clearAllMocks();
  }});

  it('should be defined', () => {{
    expect({module_name}).toBeDefined();
  }});

  // Add more tests here
}});
'''
    return test_content


def generate_python_test(file_path: Path, info: dict) -> str:
    """Generate pytest test for a Python module."""
    module_name = info.get('module_name', file_path.stem)
    module_path = str(file_path.parent).replace(os.sep, '.').replace('engine.', '')

    test_content = f'''import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from {module_path}.{module_name} import (
{generate_python_imports(info)}
)


{generate_python_test_classes(info)}
'''
    return test_content


def generate_python_imports(info: dict) -> str:
    """Generate import list for Python tests."""
    imports = []

    for func in info.get('functions', []):
        imports.append(f"    {func['name']},")

    for cls in info.get('classes', []):
        imports.append(f"    {cls['name']},")

    if not imports:
        imports.append(f"    # Add imports here,")

    return '\n'.join(imports)


def generate_python_test_classes(info: dict) -> str:
    """Generate test classes for Python modules."""
    tests = []

    # Generate tests for functions
    for func in info.get('functions', []):
        test_class = f'''class Test{func['name'].title().replace('_', '')}:
    """Tests for {func['name']} function."""

    def test_{func['name']}_basic(self):
        """Test basic functionality."""
        # Arrange
        {generate_python_args(func['args'])}

        # Act
        result = {func['name']}({', '.join(func['args'])})

        # Assert
        assert result is not None

    def test_{func['name']}_edge_cases(self):
        """Test edge cases."""
        pass
'''
        tests.append(test_class)

    # Generate tests for classes
    for cls in info.get('classes', []):
        test_class = f'''class Test{cls['name']}:
    """Tests for {cls['name']} class."""

    @pytest.fixture
    def instance(self):
        """Create a test instance."""
        return {cls['name']}()

    def test_initialization(self, instance):
        """Test instance creation."""
        assert instance is not None
'''
        for method in cls.get('methods', [])[:3]:  # Limit to first 3 methods
            test_class += f'''
    def test_{method}(self, instance):
        """Test {method} method."""
        # Add test implementation
        pass
'''
        tests.append(test_class)

    if not tests:
        tests.append('''class TestModule:
    """Tests for the module."""

    def test_module_imports(self):
        """Test that module imports work."""
        pass
''')

    return '\n\n'.join(tests)


def generate_python_args(args: List[str]) -> str:
    """Generate argument assignments for Python tests."""
    if not args:
        return "# No arguments"

    assignments = []
    for arg in args:
        assignments.append(f"{arg} = None  # TODO: Set appropriate value")
    return '\n        '.join(assignments)


def get_test_output_path(source_path: Path, project_root: Path) -> Path:
    """Determine the output path for the test file."""
    relative_path = source_path.relative_to(project_root)

    if source_path.suffix in ['.tsx', '.ts']:
        # Frontend: place in __tests__ directory next to source
        test_dir = source_path.parent / '__tests__'
        test_filename = f"{source_path.stem}.test{source_path.suffix}"
        return test_dir / test_filename

    elif source_path.suffix == '.py':
        # Backend: place in engine/tests/
        test_dir = project_root / 'engine' / 'tests'
        test_filename = f"test_{source_path.stem}.py"
        return test_dir / test_filename

    raise ValueError(f"Unsupported file type: {source_path.suffix}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_test.py <file-path>")
        sys.exit(1)

    source_path = Path(sys.argv[1]).resolve()
    project_root = get_project_root()

    if not source_path.exists():
        print(f"Error: File not found: {source_path}")
        sys.exit(1)

    # Read source file
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Analyze based on file type
    if source_path.suffix == '.tsx':
        info = analyze_tsx_component(content, source_path.name)
        test_content = generate_tsx_test(source_path, info)
    elif source_path.suffix == '.ts':
        info = analyze_tsx_component(content, source_path.name)  # Reuse for hooks/utilities
        test_content = generate_ts_test(source_path, info)
    elif source_path.suffix == '.py':
        info = analyze_python_file(content, source_path.name)
        test_content = generate_python_test(source_path, info)
    else:
        print(f"Error: Unsupported file type: {source_path.suffix}")
        sys.exit(1)

    # Determine output path
    output_path = get_test_output_path(source_path, project_root)

    # Create test directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write test file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"Generated test file: {output_path}")
    print(f"Source: {source_path}")
    print(f"Detected: {info}")


if __name__ == '__main__':
    main()
