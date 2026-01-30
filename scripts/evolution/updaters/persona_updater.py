"""
Persona documentation updater.

Updates ai-env/personas/ files when agent logic changes are detected.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime

from scripts.evolution.updaters import BaseUpdater
from scripts.evolution.analyzer import ChangeAnalysis, ChangeType


class PersonaUpdater(BaseUpdater):
    """Updates persona documentation based on agent logic changes."""

    PERSONA_DIR = Path("ai-env/personas")
    AGENT_TO_PERSONA = {
        'brain': 'optimist',
        'hand': 'critic',
        'senses': 'optimist',
        'soul': 'optimist',
    }

    def can_handle(self, target: str) -> bool:
        """Check if this updater can handle the target."""
        return 'persona' in target.lower()

    def update(self, target: str, analysis: ChangeAnalysis) -> List[str]:
        """
        Update persona documentation based on analysis.

        Args:
            target: The documentation target
            analysis: The change analysis

        Returns:
            List of updated persona files
        """
        updated = []

        # Determine which agents were modified
        modified_agents = self._get_modified_agents(analysis)

        for agent_name in modified_agents:
            persona_file = self._get_persona_for_agent(agent_name)
            if persona_file and persona_file.exists():
                if self._update_persona_file(persona_file, agent_name, analysis):
                    updated.append(str(persona_file))

        # Also update if new logic gates were detected
        if self._has_logic_changes(analysis):
            for persona_file in self.PERSONA_DIR.glob("*.md"):
                if self._append_logic_context(persona_file, analysis):
                    if str(persona_file) not in updated:
                        updated.append(str(persona_file))

        return updated

    def _get_modified_agents(self, analysis: ChangeAnalysis) -> Set[str]:
        """Extract agent names from modified files."""
        agents = set()

        for change in analysis.changes:
            # Match engine/agents/{agent_name}.py
            match = re.search(r'engine/agents/(\w+)\.py', change.file_path)
            if match:
                agents.add(match.group(1).lower())

        return agents

    def _get_persona_for_agent(self, agent_name: str) -> Optional[Path]:
        """Get the persona file path for an agent."""
        persona_name = self.AGENT_TO_PERSONA.get(agent_name)
        if persona_name:
            return self.PERSONA_DIR / f"{persona_name}.md"
        return None

    def _has_logic_changes(self, analysis: ChangeAnalysis) -> bool:
        """Check if the analysis contains logic-related changes."""
        return any(ct in analysis.change_types for ct in [
            ChangeType.AGENT_LOGIC,
            ChangeType.CORE_LOGIC
        ])

    def _update_persona_file(
        self,
        persona_file: Path,
        agent_name: str,
        analysis: ChangeAnalysis
    ) -> bool:
        """
        Update a specific persona file with evolution context.

        Args:
            persona_file: Path to the persona file
            agent_name: Name of the modified agent
            analysis: The change analysis

        Returns:
            True if file was updated
        """
        try:
            content = persona_file.read_text(encoding='utf-8')

            # Check if there's already an evolution section
            evolution_section = self._generate_evolution_section(agent_name, analysis)

            if "## Evolution Context" in content:
                # Append to existing section
                content = self._append_to_section(
                    content,
                    "## Evolution Context",
                    evolution_section
                )
            else:
                # Add new section at end
                content = content.rstrip() + "\n\n" + evolution_section

            persona_file.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            print(f"Error updating persona file {persona_file}: {e}")
            return False

    def _append_logic_context(
        self,
        persona_file: Path,
        analysis: ChangeAnalysis
    ) -> bool:
        """Append logic context to persona file."""
        try:
            content = persona_file.read_text(encoding='utf-8')

            # Extract logic changes summary
            logic_summary = self._extract_logic_summary(analysis)
            if not logic_summary:
                return False

            section = f"""
### Logic Update [{datetime.now().strftime('%Y-%m-%d')}]
- **Files Modified**: {len([c for c in analysis.changes if 'agents' in c.file_path])}
- **Key Changes**: {logic_summary}
"""

            if "## Recent Logic Updates" in content:
                content = self._append_to_section(
                    content,
                    "## Recent Logic Updates",
                    section
                )
            else:
                content = content.rstrip() + "\n\n## Recent Logic Updates\n" + section

            persona_file.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            print(f"Error appending logic context to {persona_file}: {e}")
            return False

    def _generate_evolution_section(
        self,
        agent_name: str,
        analysis: ChangeAnalysis
    ) -> str:
        """Generate an evolution context section."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Get files related to this agent
        agent_files = [
            c.file_path for c in analysis.changes
            if agent_name in c.file_path.lower()
        ]

        return f"""## Evolution Context

### Last Updated: {timestamp}

**Agent Modified**: `{agent_name}`

**Files Changed**:
{chr(10).join(f"- `{f}`" for f in agent_files)}

**Impact**: Logic changes may affect decision thresholds and behavior patterns.
Review related logic gates in `ai-env/schemas/logic_gates.md`.
"""

    def _extract_logic_summary(self, analysis: ChangeAnalysis) -> str:
        """Extract a summary of logic changes from analysis."""
        summaries = []

        for change in analysis.changes:
            if 'brain' in change.file_path:
                summaries.append("Brain decision logic")
            elif 'hand' in change.file_path:
                summaries.append("Hand execution logic")
            elif 'senses' in change.file_path:
                summaries.append("Senses data collection")
            elif 'soul' in change.file_path:
                summaries.append("Soul orchestration")

        return ", ".join(set(summaries)) if summaries else "General logic updates"

    def _append_to_section(self, content: str, section_header: str, new_content: str) -> str:
        """Append content to an existing section."""
        # Find the section
        section_start = content.find(section_header)
        if section_start == -1:
            return content + new_content

        # Find the next section (if any)
        next_section = content.find("##", section_start + len(section_header))

        if next_section == -1:
            # Append to end of content
            return content.rstrip() + "\n" + new_content
        else:
            # Insert before next section
            return (
                content[:next_section].rstrip() +
                "\n" + new_content + "\n\n" +
                content[next_section:]
            )
