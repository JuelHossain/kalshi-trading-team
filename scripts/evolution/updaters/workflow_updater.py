"""
Workflow documentation updater.

Updates ai-env/workflows/ files when workflow definitions or related code changes.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime

from scripts.evolution.updaters import BaseUpdater
from scripts.evolution.analyzer import ChangeAnalysis, ChangeType


class WorkflowUpdater(BaseUpdater):
    """Updates workflow documentation based on code changes."""

    WORKFLOWS_DIR = Path("ai-env/workflows")

    # Mapping of code patterns to workflow files
    WORKFLOW_MAPPINGS = {
        'health': ['engine/core', 'engine/agents', 'engine/main.py'],
        'inspect_signals': ['engine/core/synapse.py', 'engine/agents'],
        'run_app': ['engine/main.py', 'engine/core', 'frontend/'],
        'sync': ['ai-env/skills/', 'ai-env/workflows/', 'ai-env/schemas/'],
    }

    def can_handle(self, target: str) -> bool:
        """Check if this updater can handle the target."""
        return 'workflow' in target.lower() or 'ai-env/workflows' in target

    def update(self, target: str, analysis: ChangeAnalysis) -> List[str]:
        """
        Update workflow documentation based on analysis.

        Args:
            target: The documentation target
            analysis: The change analysis

        Returns:
            List of updated workflow files
        """
        updated = []

        # Determine which workflows need updating
        workflows_to_update = self._determine_workflows_to_update(analysis)

        for workflow_name in workflows_to_update:
            workflow_file = self.WORKFLOWS_DIR / f"{workflow_name}.md"
            if workflow_file.exists():
                if self._update_workflow_file(workflow_file, workflow_name, analysis):
                    updated.append(str(workflow_file))

        return updated

    def _determine_workflows_to_update(self, analysis: ChangeAnalysis) -> Set[str]:
        """Determine which workflows need updating based on changed files."""
        workflows = set()

        for change in analysis.changes:
            file_path = change.file_path

            # Check if workflow file itself changed
            if 'ai-env/workflows/' in file_path:
                workflow_match = re.search(r'ai-env/workflows/(\w+)\.md', file_path)
                if workflow_match:
                    workflows.add(workflow_match.group(1))

            # Check code-to-workflow mappings
            for workflow_name, code_patterns in self.WORKFLOW_MAPPINGS.items():
                for pattern in code_patterns:
                    if pattern in file_path or file_path.startswith(pattern.rstrip('/')):
                        workflows.add(workflow_name)
                        break

        return workflows

    def _update_workflow_file(
        self,
        workflow_file: Path,
        workflow_name: str,
        analysis: ChangeAnalysis
    ) -> bool:
        """
        Update a specific workflow file.

        Args:
            workflow_file: Path to the workflow file
            workflow_name: Name of the workflow
            analysis: The change analysis

        Returns:
            True if file was updated
        """
        try:
            content = workflow_file.read_text(encoding='utf-8')

            # Get relevant changes for this workflow
            relevant_changes = self._get_relevant_changes(workflow_name, analysis)

            if not relevant_changes:
                return False

            # Update the last updated timestamp
            content = self._update_timestamp(content)

            # Add/update dependencies section
            content = self._update_dependencies(content, relevant_changes)

            # Add evolution note
            content = self._add_evolution_note(content, relevant_changes)

            workflow_file.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            print(f"Error updating workflow file {workflow_file}: {e}")
            return False

    def _get_relevant_changes(
        self,
        workflow_name: str,
        analysis: ChangeAnalysis
    ) -> List[str]:
        """Get changes relevant to a specific workflow."""
        relevant = []

        code_patterns = self.WORKFLOW_MAPPINGS.get(workflow_name, [])

        for change in analysis.changes:
            file_path = change.file_path

            for pattern in code_patterns:
                if pattern in file_path or file_path.startswith(pattern.rstrip('/')):
                    relevant.append(file_path)
                    break

        return relevant

    def _update_timestamp(self, content: str) -> str:
        """Update the last updated timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d')

        # Look for existing last updated
        if re.search(r'\*\*Last Updated\*\*:?', content, re.IGNORECASE):
            content = re.sub(
                r'(\*\*Last Updated\*\*:\s*)\d{4}-\d{2}-\d{2}',
                rf'\g<1>{timestamp}',
                content,
                flags=re.IGNORECASE
            )
        else:
            # Add at the beginning after title
            title_match = re.search(r'^(# .+)$', content, re.MULTILINE)
            if title_match:
                insert_pos = title_match.end()
                content = (
                    content[:insert_pos] +
                    f"\n\n**Last Updated**: {timestamp}" +
                    content[insert_pos:]
                )

        return content

    def _update_dependencies(self, content: str, relevant_changes: List[str]) -> str:
        """Update or add a dependencies section."""
        if not relevant_changes:
            return content

        # Create dependencies section content
        deps_content = "## Dependencies\n\nThis workflow depends on:\n\n"
        for change in relevant_changes[:5]:  # Limit to 5
            deps_content += f"- `{change}`\n"

        if len(relevant_changes) > 5:
            deps_content += f"- *and {len(relevant_changes) - 5} more files*\n"

        if "## Dependencies" in content:
            # Replace existing section
            content = re.sub(
                r'## Dependencies.*?\n(?=##|$)',
                deps_content,
                content,
                flags=re.DOTALL
            )
        else:
            # Add before last section or at end
            last_section = content.rfind("\n## ")
            if last_section != -1:
                content = content[:last_section] + "\n\n" + deps_content + content[last_section:]
            else:
                content = content.rstrip() + "\n\n" + deps_content

        return content

    def _add_evolution_note(self, content: str, relevant_changes: List[str]) -> str:
        """Add an evolution note to track changes."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        note = f"""

---

*Evolution Note [{timestamp}]: Auto-updated due to changes in related code.*
"""

        # Only add if not already present
        if "*Evolution Note" not in content:
            content = content.rstrip() + note

        return content
