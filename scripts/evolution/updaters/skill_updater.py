"""
Skill documentation updater.

Updates ai-env/skills/ documentation when related code or skill definitions change.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime

from scripts.evolution.updaters import BaseUpdater
from scripts.evolution.analyzer import ChangeAnalysis, ChangeType


class SkillUpdater(BaseUpdater):
    """Updates skill documentation based on code changes."""

    SKILLS_DIR = Path("ai-env/skills")

    # Mapping of code areas to relevant skills
    CODE_TO_SKILL_MAPPINGS = {
        'frontend/src/components': ['ui-design'],
        'frontend/src/hooks': ['ui-design'],
        'frontend/src/store': ['ui-design'],
        'engine/core': ['core-ops'],
        'engine/agents': ['agent-logic', 'agent-contracts'],
        'ai-env/workflows': ['git-workflow'],
        'scripts': ['sys-evolution', 'sys-maintenance'],
        'engine/core/auth': ['safety-security'],
        'engine/core/vault': ['safety-security', 'resilience'],
    }

    def can_handle(self, target: str) -> bool:
        """Check if this updater can handle the target."""
        return 'skill' in target.lower() or 'ai-env/skills' in target

    def update(self, target: str, analysis: ChangeAnalysis) -> List[str]:
        """
        Update skill documentation based on analysis.

        Args:
            target: The documentation target
            analysis: The change analysis

        Returns:
            List of updated skill files
        """
        updated = []

        # Determine which skills need updating
        skills_to_update = self._determine_skills_to_update(analysis)

        for skill_name in skills_to_update:
            skill_file = self.SKILLS_DIR / skill_name / "SKILL.md"
            if skill_file.exists():
                if self._update_skill_file(skill_file, skill_name, analysis):
                    updated.append(str(skill_file))

        return updated

    def _determine_skills_to_update(self, analysis: ChangeAnalysis) -> Set[str]:
        """Determine which skills need updating based on changed files."""
        skills = set()

        for change in analysis.changes:
            file_path = change.file_path

            # Check direct skill changes
            if 'ai-env/skills/' in file_path:
                skill_match = re.search(r'ai-env/skills/([^/]+)', file_path)
                if skill_match:
                    skills.add(skill_match.group(1))

            # Check code-to-skill mappings
            for code_pattern, mapped_skills in self.CODE_TO_SKILL_MAPPINGS.items():
                if code_pattern in file_path or file_path.startswith(code_pattern):
                    skills.update(mapped_skills)

        return skills

    def _update_skill_file(
        self,
        skill_file: Path,
        skill_name: str,
        analysis: ChangeAnalysis
    ) -> bool:
        """
        Update a specific skill file.

        Args:
            skill_file: Path to the skill file
            skill_name: Name of the skill
            analysis: The change analysis

        Returns:
            True if file was updated
        """
        try:
            content = skill_file.read_text(encoding='utf-8')

            # Get relevant changes for this skill
            relevant_changes = self._get_relevant_changes(skill_name, analysis)

            if not relevant_changes:
                return False

            # Update the evolution context section
            content = self._update_evolution_context(content, skill_name, relevant_changes)

            # Update the last modified timestamp
            content = self._update_timestamp(content)

            skill_file.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            print(f"Error updating skill file {skill_file}: {e}")
            return False

    def _get_relevant_changes(
        self,
        skill_name: str,
        analysis: ChangeAnalysis
    ) -> List[str]:
        """Get changes relevant to a specific skill."""
        relevant = []

        for change in analysis.changes:
            file_path = change.file_path

            # Check if this change is relevant to the skill
            for code_pattern, mapped_skills in self.CODE_TO_SKILL_MAPPINGS.items():
                if skill_name in mapped_skills:
                    if code_pattern in file_path or file_path.startswith(code_pattern):
                        relevant.append(file_path)
                        break

        return relevant

    def _update_evolution_context(
        self,
        content: str,
        skill_name: str,
        relevant_changes: List[str]
    ) -> str:
        """Update or add the evolution context section."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        evolution_entry = f"""
### Evolution Entry [{timestamp}]
- **Trigger**: Code changes detected
- **Files**: {', '.join(f'`{c}`' for c in relevant_changes[:3])}
"""
        if len(relevant_changes) > 3:
            evolution_entry += f"- **Additional**: {len(relevant_changes) - 3} more files\n"

        if "## Evolution Context" in content:
            # Append to existing section
            section_start = content.find("## Evolution Context")
            next_section = content.find("##", section_start + 1)

            if next_section == -1:
                content = content.rstrip() + evolution_entry
            else:
                content = (
                    content[:next_section].rstrip() +
                    evolution_entry + "\n\n" +
                    content[next_section:]
                )
        else:
            # Add new section before any scripts section or at end
            scripts_section = content.find("## Scripts")
            if scripts_section == -1:
                scripts_section = content.find("## 📝 Automation Scripts")

            if scripts_section != -1:
                content = (
                    content[:scripts_section].rstrip() +
                    "\n\n## Evolution Context\n" +
                    evolution_entry + "\n\n" +
                    content[scripts_section:]
                )
            else:
                content = content.rstrip() + "\n\n## Evolution Context\n" + evolution_entry

        return content

    def _update_timestamp(self, content: str) -> str:
        """Update the last modified timestamp in the skill file."""
        timestamp = datetime.now().strftime('%Y-%m-%d')

        # Look for existing timestamp in frontmatter
        if "---" in content[:100]:
            # Update or add last_modified field
            if "last_modified:" in content:
                content = re.sub(
                    r'last_modified:.*',
                    f'last_modified: {timestamp}',
                    content
                )
            else:
                # Add last_modified after description
                content = re.sub(
                    r'(description:.*)',
                    rf'\1\nlast_modified: {timestamp}',
                    content
                )

        return content
