"""
Schema documentation updater.

Updates ai-env/schemas/ files when core data structures or schemas change.
"""

import re
import ast
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from datetime import datetime

from scripts.evolution.updaters import BaseUpdater
from scripts.evolution.analyzer import ChangeAnalysis, ChangeType


class SchemaUpdater(BaseUpdater):
    """Updates schema documentation based on code changes."""

    SCHEMA_DIR = Path("ai-env/schemas")

    # Mapping of source files to schema documentation
    SCHEMA_MAPPINGS = {
        'engine/core/synapse.py': ['synapse_schema.md'],
        'engine/core/vault.py': ['synapse_schema.md', 'logic_gates.md'],
        'engine/core/bus.py': ['synapse_schema.md'],
        'engine/core/network.py': ['synapse_schema.md'],
        'engine/agents/brain.py': ['logic_gates.md'],
        'engine/agents/hand.py': ['logic_gates.md'],
    }

    def can_handle(self, target: str) -> bool:
        """Check if this updater can handle the target."""
        return 'schema' in target.lower() or target.endswith('.md') and 'schema' in target

    def update(self, target: str, analysis: ChangeAnalysis) -> List[str]:
        """
        Update schema documentation based on analysis.

        Args:
            target: The documentation target
            analysis: The change analysis

        Returns:
            List of updated schema files
        """
        updated = []

        # Determine which schema files need updating
        schema_files_to_update = self._determine_schema_updates(analysis)

        for schema_file, source_files in schema_files_to_update.items():
            schema_path = self.SCHEMA_DIR / schema_file
            if schema_path.exists():
                if self._update_schema_file(schema_path, source_files, analysis):
                    updated.append(str(schema_path))

        return updated

    def _determine_schema_updates(self, analysis: ChangeAnalysis) -> Dict[str, List[str]]:
        """
        Determine which schema files need updating based on changed files.

        Returns:
            Dict mapping schema file to list of source files that triggered update
        """
        updates: Dict[str, List[str]] = {}

        for change in analysis.changes:
            for source_pattern, schema_files in self.SCHEMA_MAPPINGS.items():
                if self._match_pattern(change.file_path, source_pattern):
                    for schema_file in schema_files:
                        if schema_file not in updates:
                            updates[schema_file] = []
                        if change.file_path not in updates[schema_file]:
                            updates[schema_file].append(change.file_path)

        return updates

    def _match_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if a file path matches a pattern."""
        # Simple pattern matching - can be enhanced
        return pattern in file_path or file_path.endswith(pattern.replace('*', ''))

    def _update_schema_file(
        self,
        schema_path: Path,
        source_files: List[str],
        analysis: ChangeAnalysis
    ) -> bool:
        """
        Update a specific schema file.

        Args:
            schema_path: Path to the schema file
            source_files: List of source files that triggered this update
            analysis: The change analysis

        Returns:
            True if file was updated
        """
        try:
            content = schema_path.read_text(encoding='utf-8')

            # Extract new schema information from source files
            schema_updates = self._extract_schema_from_sources(source_files)

            # Update the schema file
            for update in schema_updates:
                content = self._apply_schema_update(content, update)

            # Add evolution marker
            content = self._add_evolution_marker(content, source_files, analysis)

            schema_path.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            print(f"Error updating schema file {schema_path}: {e}")
            return False

    def _extract_schema_from_sources(self, source_files: List[str]) -> List[Dict]:
        """
        Extract schema information from source files.

        This parses Python files to find dataclasses, TypedDicts, and other
        schema-defining structures.
        """
        updates = []

        for source_file in source_files:
            source_path = Path(source_file)
            if not source_path.exists():
                continue

            try:
                source_content = source_path.read_text(encoding='utf-8')
                tree = ast.parse(source_content)

                # Find dataclasses
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        update = self._process_class_def(node, source_file)
                        if update:
                            updates.append(update)

            except SyntaxError:
                # Skip files with syntax errors
                continue
            except Exception as e:
                print(f"Warning: Could not parse {source_file}: {e}")
                continue

        return updates

    def _process_class_def(self, node: ast.ClassDef, source_file: str) -> Optional[Dict]:
        """Process a class definition to extract schema information."""
        # Check if it's a dataclass or similar schema class
        is_dataclass = any(
            isinstance(decorator, ast.Name) and decorator.id == 'dataclass'
            for decorator in node.decorator_list
        )

        if not is_dataclass and not node.name.endswith(('Model', 'Schema', 'Config')):
            return None

        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                field_name = item.target.id if isinstance(item.target, ast.Name) else str(item.target)
                field_type = self._get_type_string(item.annotation)
                fields.append({
                    'name': field_name,
                    'type': field_type
                })

        return {
            'class_name': node.name,
            'source_file': source_file,
            'fields': fields
        }

    def _get_type_string(self, annotation: ast.AST) -> str:
        """Convert an AST annotation to a type string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            value = self._get_type_string(annotation.value)
            slice_val = self._get_type_string(annotation.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Attribute):
            return f"{self._get_type_string(annotation.value)}.{annotation.attr}"
        else:
            return str(annotation)

    def _apply_schema_update(self, content: str, update: Dict) -> str:
        """Apply a schema update to the content."""
        class_name = update['class_name']

        # Check if this class is already documented
        if class_name in content:
            # Update existing documentation
            return self._update_existing_schema(content, update)
        else:
            # Add new schema documentation
            return self._add_new_schema(content, update)

    def _update_existing_schema(self, content: str, update: Dict) -> str:
        """Update existing schema documentation."""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated merging
        timestamp = datetime.now().strftime('%Y-%m-%d')

        update_marker = f"\n\n> **Auto-updated**: {timestamp} from `{update['source_file']}`\n"

        # Find the class section and append update marker
        class_pattern = rf"(##?\s*{update['class_name']}.*?)(\n##|\Z)"
        match = re.search(class_pattern, content, re.DOTALL)

        if match:
            insert_pos = match.end(1)
            content = content[:insert_pos] + update_marker + content[insert_pos:]

        return content

    def _add_new_schema(self, content: str, update: Dict) -> str:
        """Add new schema documentation."""
        timestamp = datetime.now().strftime('%Y-%m-%d')

        new_section = f"""

## {update['class_name']}

> **Source**: `{update['source_file']}`
> **Added**: {timestamp}

### Fields

| Field | Type |
|-------|------|
"""
        for field in update['fields']:
            new_section += f"| `{field['name']}` | `{field['type']}` |\n"

        return content.rstrip() + new_section

    def _add_evolution_marker(
        self,
        content: str,
        source_files: List[str],
        analysis: ChangeAnalysis
    ) -> str:
        """Add an evolution marker to track when the schema was last updated."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        marker = f"""\n
---

*Last schema evolution: {timestamp}*
*Triggered by changes in: {', '.join(f'`{f}`' for f in source_files)}*
"""

        # Check if there's already an evolution marker
        if "*Last schema evolution:" in content:
            # Replace existing marker
            content = re.sub(
                r'\n---\n\n\*Last schema evolution:.*?\*',
                marker.strip(),
                content,
                flags=re.DOTALL
            )
        else:
            content = content.rstrip() + marker

        return content
