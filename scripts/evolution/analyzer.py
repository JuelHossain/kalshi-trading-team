"""
Change detection and analysis engine for the evolution system.

Analyzes git staged files, classifies changes, and determines significance
for documentation updates.
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.evolution.config import get_config, MappingRule
from scripts.evolution.git_utils import GitUtils, GitChange


class ChangeType(Enum):
    """Types of changes that can be detected."""
    AGENT_LOGIC = "agent_logic"
    SCHEMA_CHANGE = "schema_change"
    FRONTEND_CHANGE = "frontend_change"
    CORE_LOGIC = "core_logic"
    WORKFLOW_CHANGE = "workflow_change"
    SKILL_CHANGE = "skill_change"
    CONFIG_CHANGE = "config_change"
    TEST_CHANGE = "test_change"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


@dataclass
class ChangeAnalysis:
    """Complete analysis of a set of changes."""
    changes: List[GitChange] = field(default_factory=list)
    change_types: Set[ChangeType] = field(default_factory=set)
    affected_mappings: List[MappingRule] = field(default_factory=list)
    is_significant: bool = False
    significance_reasons: List[str] = field(default_factory=list)
    doc_targets: Set[str] = field(default_factory=set)
    triggers_soul: bool = False
    update_mode: str = "async"
    total_lines_changed: int = 0
    high_value_files: List[str] = field(default_factory=list)


class ChangeAnalyzer:
    """Analyzes git changes and determines documentation impact."""

    # File patterns for classification
    PATTERNS = {
        ChangeType.AGENT_LOGIC: [
            r'engine/agents/.*\.py$',
            r'engine/agents/.*\.pyi$',
        ],
        ChangeType.SCHEMA_CHANGE: [
            r'engine/core/synapse\.py$',
            r'engine/core/vault\.py$',
            r'engine/core/bus\.py$',
            r'engine/core/network\.py$',
        ],
        ChangeType.FRONTEND_CHANGE: [
            r'frontend/src/.*\.tsx?$',
            r'frontend/src/.*\.jsx?$',
            r'frontend/src/.*\.css$',
            r'frontend/src/.*\.scss$',
        ],
        ChangeType.CORE_LOGIC: [
            r'engine/core/.*\.py$',
            r'engine/main\.py$',
        ],
        ChangeType.WORKFLOW_CHANGE: [
            r'ai-env/workflows/.*\.md$',
        ],
        ChangeType.SKILL_CHANGE: [
            r'ai-env/skills/.*/SKILL\.md$',
            r'ai-env/skills/.*/scripts/.*\.py$',
        ],
        ChangeType.CONFIG_CHANGE: [
            r'.*\.yaml$',
            r'.*\.yml$',
            r'.*\.json$',
            r'.*\.toml$',
            r'.*requirements.*\.txt$',
        ],
        ChangeType.TEST_CHANGE: [
            r'.*/test.*\.py$',
            r'.*/.*_test\.py$',
            r'.*/tests?/.*\.py$',
        ],
        ChangeType.DOCUMENTATION: [
            r'.*\.md$',
            r'ai-env/personas/.*$',
            r'ai-env/schemas/.*$',
            r'ai-env/soul/.*$',
        ],
    }

    def __init__(self):
        self.config = get_config()
        self.git = GitUtils()

    def analyze_staged(self) -> ChangeAnalysis:
        """
        Analyze currently staged changes.

        Returns:
            ChangeAnalysis with complete analysis
        """
        changes = self.git.get_staged_files()
        return self._analyze_changes(changes)

    def analyze_commit(self, commit_hash: str) -> ChangeAnalysis:
        """
        Analyze changes in a specific commit.

        Args:
            commit_hash: The commit to analyze

        Returns:
            ChangeAnalysis with complete analysis
        """
        # Get changes from parent to this commit
        changes = self.git.get_changed_files_since(f"{commit_hash}^")
        return self._analyze_changes(changes)

    def _analyze_changes(self, changes: List[GitChange]) -> ChangeAnalysis:
        """
        Perform complete analysis on a list of changes.

        Args:
            changes: List of GitChange objects

        Returns:
            Complete ChangeAnalysis
        """
        analysis = ChangeAnalysis(changes=changes)

        if not changes:
            return analysis

        # Calculate total lines changed
        analysis.total_lines_changed = sum(
            c.lines_added + c.lines_removed for c in changes
        )

        # Classify each change
        for change in changes:
            change_type = self._classify_change(change.file_path)
            analysis.change_types.add(change_type)

            # Check for mapping matches
            mapping = self.config.get_mapping_for_file(change.file_path)
            if mapping and mapping not in analysis.affected_mappings:
                analysis.affected_mappings.append(mapping)

            # Check if high-value file
            if self.config.is_high_value_file(change.file_path):
                analysis.high_value_files.append(change.file_path)

        # Determine significance
        analysis.is_significant, analysis.significance_reasons = self._determine_significance(analysis)

        # Collect doc targets
        analysis.doc_targets = self._collect_doc_targets(analysis)

        # Determine if soul snapshot needed
        analysis.triggers_soul = any(
            mapping.triggers_soul for mapping in analysis.affected_mappings
        ) and analysis.is_significant

        # Determine update mode (sync takes precedence)
        analysis.update_mode = self._determine_update_mode(analysis)

        return analysis

    def _classify_change(self, file_path: str) -> ChangeType:
        """
        Classify a single file change by type.

        Args:
            file_path: Path to the changed file

        Returns:
            ChangeType enum value
        """
        for change_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, file_path):
                    return change_type
        return ChangeType.UNKNOWN

    def _determine_significance(self, analysis: ChangeAnalysis) -> Tuple[bool, List[str]]:
        """
        Determine if changes are significant enough for documentation updates.

        Args:
            analysis: The change analysis to evaluate

        Returns:
            Tuple of (is_significant, reasons)
        """
        reasons = []

        # Check minimum lines changed
        if analysis.total_lines_changed >= self.config.significance.min_lines_changed:
            reasons.append(
                f"Lines changed ({analysis.total_lines_changed}) >= threshold "
                f"({self.config.significance.min_lines_changed})"
            )

        # Check for high-value files
        if analysis.high_value_files:
            reasons.append(f"High-value files modified: {', '.join(analysis.high_value_files)}")

        # Check for agent logic changes
        if ChangeType.AGENT_LOGIC in analysis.change_types:
            reasons.append("Agent logic modified")

        # Check for schema changes
        if ChangeType.SCHEMA_CHANGE in analysis.change_types:
            reasons.append("Core schema modified")

        # Check for core logic changes
        if ChangeType.CORE_LOGIC in analysis.change_types:
            reasons.append("Core logic modified")

        # Check for new files (status 'A')
        new_files = [c.file_path for c in analysis.changes if c.status == 'A']
        if new_files:
            reasons.append(f"New files added: {len(new_files)}")

        # Check for deleted files (status 'D')
        deleted_files = [c.file_path for c in analysis.changes if c.status == 'D']
        if deleted_files:
            reasons.append(f"Files deleted: {len(deleted_files)}")

        is_significant = len(reasons) > 0
        return is_significant, reasons

    def _collect_doc_targets(self, analysis: ChangeAnalysis) -> Set[str]:
        """
        Collect all documentation targets that need updating.

        Args:
            analysis: The change analysis

        Returns:
            Set of documentation target paths
        """
        targets = set()

        for mapping in analysis.affected_mappings:
            targets.update(mapping.doc_targets)

        # Add type-specific targets
        type_targets = {
            ChangeType.AGENT_LOGIC: ['ai-env/personas/', 'ai-env/schemas/logic_gates.md'],
            ChangeType.SCHEMA_CHANGE: ['ai-env/schemas/synapse_schema.md', 'ai-env/schemas/'],
            ChangeType.FRONTEND_CHANGE: ['ai-env/skills/ui-design/SKILL.md'],
            ChangeType.CORE_LOGIC: ['ai-env/skills/core-ops/SKILL.md'],
            ChangeType.WORKFLOW_CHANGE: ['ai-env/workflows/'],
            ChangeType.SKILL_CHANGE: ['ai-env/skills/'],
        }

        for change_type in analysis.change_types:
            if change_type in type_targets:
                targets.update(type_targets[change_type])

        return targets

    def _determine_update_mode(self, analysis: ChangeAnalysis) -> str:
        """
        Determine whether to use sync or async update mode.

        Args:
            analysis: The change analysis

        Returns:
            'sync' or 'async'
        """
        # If any mapping requires sync, use sync
        for mapping in analysis.affected_mappings:
            if mapping.update_mode == 'sync':
                return 'sync'

        # Significant changes to core logic should be sync
        if analysis.is_significant and any(
            t in analysis.change_types
            for t in [ChangeType.AGENT_LOGIC, ChangeType.SCHEMA_CHANGE, ChangeType.CORE_LOGIC]
        ):
            return 'sync'

        return 'async'

    def get_summary(self, analysis: ChangeAnalysis) -> str:
        """
        Generate a human-readable summary of the analysis.

        Args:
            analysis: The change analysis

        Returns:
            Formatted summary string
        """
        lines = [
            "=" * 60,
            "EVOLUTION ANALYSIS SUMMARY",
            "=" * 60,
            f"Files changed: {len(analysis.changes)}",
            f"Total lines changed: {analysis.total_lines_changed}",
            f"Change types: {', '.join(t.value for t in analysis.change_types)}",
            "",
            "SIGNIFICANCE:",
            f"  Is significant: {'YES' if analysis.is_significant else 'NO'}",
        ]

        if analysis.significance_reasons:
            lines.append("  Reasons:")
            for reason in analysis.significance_reasons:
                lines.append(f"    - {reason}")

        lines.extend([
            "",
            "DOCUMENTATION IMPACT:",
            f"  Triggers soul snapshot: {'YES' if analysis.triggers_soul else 'NO'}",
            f"  Update mode: {analysis.update_mode}",
            "  Doc targets:",
        ])

        for target in sorted(analysis.doc_targets):
            lines.append(f"    - {target}")

        lines.extend([
            "",
            "FILES:",
        ])

        for change in analysis.changes:
            lines.append(
                f"  [{change.status}] {change.file_path} "
                f"(+{change.lines_added}/-{change.lines_removed})"
            )

        lines.append("=" * 60)

        return '\n'.join(lines)


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze git changes for documentation evolution'
    )
    parser.add_argument(
        'command',
        choices=['pre-commit', 'post-commit', 'analyze'],
        help='Analysis command to run'
    )
    parser.add_argument(
        '--commit',
        help='Commit hash to analyze (for post-commit)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    analyzer = ChangeAnalyzer()

    if args.command == 'pre-commit':
        analysis = analyzer.analyze_staged()
    elif args.command == 'post-commit':
        if not args.commit:
            # Get last commit
            info = analyzer.git.get_last_commit_info()
            args.commit = info['hash']
        analysis = analyzer.analyze_commit(args.commit)
    else:
        analysis = analyzer.analyze_staged()

    if args.json:
        import json
        result = {
            'is_significant': analysis.is_significant,
            'triggers_soul': analysis.triggers_soul,
            'update_mode': analysis.update_mode,
            'doc_targets': list(analysis.doc_targets),
            'change_types': [t.value for t in analysis.change_types],
            'significance_reasons': analysis.significance_reasons,
            'files': [
                {
                    'path': c.file_path,
                    'status': c.status,
                    'lines_added': c.lines_added,
                    'lines_removed': c.lines_removed
                }
                for c in analysis.changes
            ]
        }
        print(json.dumps(result, indent=2))
    else:
        print(analyzer.get_summary(analysis))

    # Exit with code 0 if significant, 1 if not (for shell scripting)
    return 0 if analysis.is_significant else 1


if __name__ == '__main__':
    sys.exit(main())
