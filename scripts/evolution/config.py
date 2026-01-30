"""
Configuration loader for the evolution system.

Loads and validates evolution configuration from ai-env/evolution/config.yaml.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Try to import yaml, provide fallback if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None


@dataclass
class MappingRule:
    """A single file-to-documentation mapping rule."""
    name: str
    patterns: List[str]
    doc_targets: List[str]
    update_mode: str  # 'sync' or 'async'
    triggers_soul: bool = False


@dataclass
class SignificanceConfig:
    """Configuration for determining change significance."""
    min_lines_changed: int = 5
    high_value_files: List[str] = field(default_factory=list)
    high_value_patterns: List[str] = field(default_factory=list)


class EvolutionConfig:
    """Main configuration class for the evolution system."""

    DEFAULT_CONFIG_PATH = "ai-env/evolution/config.yaml"

    # Default significance rules when config file is missing
    SIGNIFICANCE_RULES = {
        'agent_logic': {
            'patterns': ['engine/agents/*.py'],
            'triggers_soul': True,
            'doc_targets': ['personas', 'logic_gates'],
            'update_mode': 'sync'
        },
        'schema_change': {
            'patterns': ['engine/core/synapse.py', 'engine/core/vault.py'],
            'triggers_soul': True,
            'doc_targets': ['synapse_schema'],
            'update_mode': 'sync'
        },
        'frontend_change': {
            'patterns': ['frontend/src/components/*.tsx', 'frontend/src/components/*.ts'],
            'triggers_soul': False,
            'doc_targets': ['ui-design', 'architecture'],
            'update_mode': 'async'
        },
        'core_logic': {
            'patterns': ['engine/core/*.py'],
            'triggers_soul': True,
            'doc_targets': ['core-ops', 'logic_gates'],
            'update_mode': 'sync'
        },
        'workflow_change': {
            'patterns': ['ai-env/workflows/*.md'],
            'triggers_soul': False,
            'doc_targets': ['workflows'],
            'update_mode': 'async'
        },
        'skill_change': {
            'patterns': ['ai-env/skills/*/SKILL.md'],
            'triggers_soul': False,
            'doc_targets': ['skills'],
            'update_mode': 'async'
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self.mappings: List[MappingRule] = []
        self.significance: SignificanceConfig = SignificanceConfig()
        self._load()

    def _load(self) -> None:
        """Load configuration from YAML file or use defaults."""
        config_file = Path(self.config_path)

        if config_file.exists() and HAS_YAML:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                self._config = {}
        else:
            # Use default configuration
            self._config = {
                'mappings': {
                    name: {
                        'patterns': rule['patterns'],
                        'doc_targets': [f"ai-env/{target}" for target in rule['doc_targets']],
                        'update_mode': rule['update_mode'],
                        'triggers_soul': rule['triggers_soul']
                    }
                    for name, rule in self.SIGNIFICANCE_RULES.items()
                },
                'significance': {
                    'min_lines_changed': 5,
                    'high_value_files': [
                        'engine/agents/brain.py',
                        'engine/agents/hand.py',
                        'engine/core/synapse.py',
                        'engine/core/vault.py'
                    ]
                }
            }
            # Save default config for future use
            self._save_default_config()

        self._parse_config()

    def _save_default_config(self) -> None:
        """Save the default configuration to file."""
        if not HAS_YAML:
            return  # Can't save without yaml
        try:
            config_dir = Path(self.config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=True)
        except Exception as e:
            print(f"Warning: Could not save default config: {e}")

    def _parse_config(self) -> None:
        """Parse loaded configuration into structured objects."""
        # Parse mappings
        mappings_data = self._config.get('mappings', {})
        for name, data in mappings_data.items():
            self.mappings.append(MappingRule(
                name=name,
                patterns=data.get('patterns', []),
                doc_targets=data.get('doc_targets', []),
                update_mode=data.get('update_mode', 'async'),
                triggers_soul=data.get('triggers_soul', False)
            ))

        # Parse significance config
        sig_data = self._config.get('significance', {})
        self.significance = SignificanceConfig(
            min_lines_changed=sig_data.get('min_lines_changed', 5),
            high_value_files=sig_data.get('high_value_files', []),
            high_value_patterns=sig_data.get('high_value_patterns', [])
        )

    def get_mapping_for_file(self, file_path: str) -> Optional[MappingRule]:
        """
        Find the mapping rule that matches a given file path.

        Args:
            file_path: Path to the changed file

        Returns:
            Matching MappingRule or None
        """
        from fnmatch import fnmatch

        for mapping in self.mappings:
            for pattern in mapping.patterns:
                if fnmatch(file_path, pattern):
                    return mapping
        return None

    def is_high_value_file(self, file_path: str) -> bool:
        """Check if a file is considered high-value for significance."""
        from fnmatch import fnmatch

        # Direct match
        if file_path in self.significance.high_value_files:
            return True

        # Pattern match
        for pattern in self.significance.high_value_patterns:
            if fnmatch(file_path, pattern):
                return True

        return False

    def get_all_doc_targets(self) -> List[str]:
        """Get all unique documentation targets across all mappings."""
        targets = set()
        for mapping in self.mappings:
            targets.update(mapping.doc_targets)
        return sorted(list(targets))


# Global config instance
_config_instance: Optional[EvolutionConfig] = None


def get_config() -> EvolutionConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = EvolutionConfig()
    return _config_instance


def reload_config() -> EvolutionConfig:
    """Reload and return a fresh configuration instance."""
    global _config_instance
    _config_instance = EvolutionConfig()
    return _config_instance
