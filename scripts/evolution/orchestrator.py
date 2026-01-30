"""
Sync/async coordinator for the evolution system.

Manages the execution of documentation updates based on analysis results,
coordinating between synchronous (pre-commit) and asynchronous (post-commit)
update modes.
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import traceback

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.evolution.config import get_config
from scripts.evolution.database import get_database, EvolutionRecord
from scripts.evolution.git_utils import GitUtils
from scripts.evolution.analyzer import ChangeAnalyzer, ChangeAnalysis


class UpdateMode(Enum):
    """Update execution modes."""
    SYNC = "sync"
    ASYNC = "async"


class UpdateStatus(Enum):
    """Status of an update operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class UpdateResult:
    """Result of an update operation."""
    status: UpdateStatus
    updates_performed: List[str]
    errors: List[str]
    soul_snapshot_path: Optional[str] = None


class EvolutionOrchestrator:
    """Orchestrates documentation evolution updates."""

    def __init__(self):
        self.config = get_config()
        self.database = get_database()
        self.git = GitUtils()
        self.analyzer = ChangeAnalyzer()
        self._updaters: Dict[str, Callable] = {}
        self._register_default_updaters()

    def _register_default_updaters(self) -> None:
        """Register the default set of documentation updaters."""
        # Import updaters here to avoid circular imports
        try:
            from scripts.evolution.updaters.persona_updater import PersonaUpdater
            from scripts.evolution.updaters.schema_updater import SchemaUpdater
            from scripts.evolution.updaters.skill_updater import SkillUpdater
            from scripts.evolution.updaters.workflow_updater import WorkflowUpdater
            from scripts.evolution.updaters.soul_updater import SoulUpdater

            self._updaters['personas'] = PersonaUpdater()
            self._updaters['schemas'] = SchemaUpdater()
            self._updaters['skills'] = SkillUpdater()
            self._updaters['workflows'] = WorkflowUpdater()
            self._updaters['soul'] = SoulUpdater()
        except ImportError as e:
            print(f"Warning: Could not load some updaters: {e}")

    def run_sync(self, analysis: Optional[ChangeAnalysis] = None) -> UpdateResult:
        """
        Run synchronous documentation updates.

        This is called during pre-commit and must complete before the commit.

        Args:
            analysis: Pre-computed analysis, or None to analyze staged changes

        Returns:
            UpdateResult with status and details
        """
        result = UpdateResult(
            status=UpdateStatus.PENDING,
            updates_performed=[],
            errors=[]
        )

        try:
            if analysis is None:
                analysis = self.analyzer.analyze_staged()

            # If not significant, skip updates
            if not analysis.is_significant:
                result.status = UpdateStatus.SKIPPED
                result.updates_performed.append("Analysis: not significant, skipping")
                return result

            result.status = UpdateStatus.RUNNING

            # Log the evolution start
            commit_info = self.git.get_last_commit_info()
            # Use a unique temp ID for pending commits
            import time
            temp_hash = f"pending_{int(time.time())}"
            record = EvolutionRecord(
                commit_hash=temp_hash,
                commit_message=commit_info.get('message', ''),
                changed_files=[c.file_path for c in analysis.changes],
                doc_targets=list(analysis.doc_targets),
                is_significant=analysis.is_significant,
                update_mode='sync',
                triggers_soul=analysis.triggers_soul,
                status='running',
                branch=self.git.get_current_branch()
            )
            record_id = self.database.log_evolution(record)

            # Execute updates based on doc targets
            for target in analysis.doc_targets:
                try:
                    self._execute_update(target, analysis, result)
                except Exception as e:
                    error_msg = f"Failed to update {target}: {str(e)}"
                    result.errors.append(error_msg)
                    print(f"Error: {error_msg}")

            # Create soul snapshot if needed
            if analysis.triggers_soul:
                try:
                    soul_updater = self._updaters.get('soul')
                    if soul_updater:
                        snapshot_path = soul_updater.create_snapshot(analysis)
                        result.soul_snapshot_path = snapshot_path
                        result.updates_performed.append(f"Soul snapshot: {snapshot_path}")
                except Exception as e:
                    error_msg = f"Failed to create soul snapshot: {str(e)}"
                    result.errors.append(error_msg)
                    print(f"Error: {error_msg}")

            # Stage any updated documentation files
            self._stage_documentation_updates()

            # Update final status
            if result.errors:
                result.status = UpdateStatus.FAILED
                self.database.update_status(
                    record.commit_hash,
                    'failed',
                    '\n'.join(result.errors)
                )
            else:
                result.status = UpdateStatus.COMPLETED
                self.database.update_status(record.commit_hash, 'completed')

        except Exception as e:
            result.status = UpdateStatus.FAILED
            result.errors.append(f"Orchestrator error: {str(e)}")
            traceback.print_exc()

        return result

    def run_async(self, commit_hash: Optional[str] = None) -> UpdateResult:
        """
        Run asynchronous documentation updates.

        This is called after commit and runs in the background.

        Args:
            commit_hash: The commit hash to process, or None for last commit

        Returns:
            UpdateResult with status and details
        """
        result = UpdateResult(
            status=UpdateStatus.PENDING,
            updates_performed=[],
            errors=[]
        )

        try:
            # Get commit info
            if commit_hash is None:
                commit_info = self.git.get_last_commit_info()
                commit_hash = commit_info['hash']
            else:
                commit_info = self.git.get_commit_info(commit_hash)

            # Analyze the commit
            analysis = self.analyzer.analyze_commit(commit_hash)

            # If not significant, skip
            if not analysis.is_significant:
                result.status = UpdateStatus.SKIPPED
                # Log the skip
                record = EvolutionRecord(
                    commit_hash=commit_hash,
                    commit_message=commit_info.get('message', ''),
                    changed_files=[c.file_path for c in analysis.changes],
                    doc_targets=list(analysis.doc_targets),
                    is_significant=False,
                    update_mode='async',
                    triggers_soul=False,
                    status='skipped',
                    branch=self.git.get_current_branch()
                )
                self.database.log_evolution(record)
                return result

            result.status = UpdateStatus.RUNNING

            # Log the evolution start
            record = EvolutionRecord(
                commit_hash=commit_hash,
                commit_message=commit_info.get('message', ''),
                changed_files=[c.file_path for c in analysis.changes],
                doc_targets=list(analysis.doc_targets),
                is_significant=analysis.is_significant,
                update_mode='async',
                triggers_soul=analysis.triggers_soul,
                status='running',
                branch=self.git.get_current_branch()
            )
            self.database.log_evolution(record)

            # Execute async updates
            for target in analysis.doc_targets:
                try:
                    # For async, we only update if the target doesn't require sync
                    mapping = self.config.get_mapping_for_file(target)
                    if mapping and mapping.update_mode == 'sync':
                        continue  # Skip sync-only targets in async mode

                    self._execute_update(target, analysis, result)
                except Exception as e:
                    error_msg = f"Failed to update {target}: {str(e)}"
                    result.errors.append(error_msg)
                    print(f"Error: {error_msg}")

            # Create soul snapshot if needed (for async too)
            if analysis.triggers_soul:
                try:
                    soul_updater = self._updaters.get('soul')
                    if soul_updater:
                        snapshot_path = soul_updater.create_snapshot(analysis)
                        result.soul_snapshot_path = snapshot_path
                        result.updates_performed.append(f"Soul snapshot: {snapshot_path}")
                except Exception as e:
                    error_msg = f"Failed to create soul snapshot: {str(e)}"
                    result.errors.append(error_msg)

            # Update final status
            if result.errors:
                result.status = UpdateStatus.FAILED
                self.database.update_status(
                    commit_hash,
                    'failed',
                    '\n'.join(result.errors)
                )
            else:
                result.status = UpdateStatus.COMPLETED
                self.database.update_status(commit_hash, 'completed')

        except Exception as e:
            result.status = UpdateStatus.FAILED
            result.errors.append(f"Orchestrator error: {str(e)}")
            traceback.print_exc()

        return result

    def _execute_update(self, target: str, analysis: ChangeAnalysis, result: UpdateResult) -> None:
        """
        Execute a single documentation update.

        Args:
            target: Documentation target path or identifier
            analysis: The change analysis
            result: UpdateResult to append results to
        """
        # Determine which updater to use based on target
        updater_key = None

        if 'persona' in target.lower():
            updater_key = 'personas'
        elif 'schema' in target.lower():
            updater_key = 'schemas'
        elif 'skill' in target.lower():
            updater_key = 'skills'
        elif 'workflow' in target.lower():
            updater_key = 'workflows'
        elif 'soul' in target.lower():
            updater_key = 'soul'

        if updater_key and updater_key in self._updaters:
            updater = self._updaters[updater_key]
            updated_files = updater.update(target, analysis)
            if updated_files:
                result.updates_performed.extend(updated_files)
        else:
            # Generic update - just log that we would update this target
            result.updates_performed.append(f"Would update: {target}")

    def _stage_documentation_updates(self) -> None:
        """Stage any documentation files that were updated."""
        # Find modified documentation files
        doc_patterns = ['ai-env/**/*.md', 'ai-env/**/*.yaml']

        for pattern in doc_patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    # Check if file is modified
                    _, stdout, _ = self.git._run_git(
                        ['status', '--porcelain', str(file_path)],
                        check=False
                    )
                    if stdout.strip():
                        # File has changes, stage it
                        self.git.stage_files([str(file_path)])

    def get_pending_updates(self) -> List[EvolutionRecord]:
        """Get all pending async updates."""
        return self.database.get_pending_async_updates()

    def process_pending_updates(self) -> List[UpdateResult]:
        """Process all pending async updates."""
        pending = self.get_pending_updates()
        results = []

        for record in pending:
            result = self.run_async(record.commit_hash)
            results.append(result)

        return results

    def get_stats(self) -> Dict:
        """Get evolution system statistics."""
        return self.database.get_stats()


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Orchestrate documentation evolution updates'
    )
    parser.add_argument(
        'command',
        choices=['sync', 'async', 'process-pending', 'stats'],
        help='Command to execute'
    )
    parser.add_argument(
        '--commit',
        help='Commit hash (for async mode)'
    )
    parser.add_argument(
        '--message',
        help='Commit message (for async mode)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    orchestrator = EvolutionOrchestrator()

    if args.command == 'sync':
        result = orchestrator.run_sync()
    elif args.command == 'async':
        result = orchestrator.run_async(args.commit)
    elif args.command == 'process-pending':
        results = orchestrator.process_pending_updates()
        if args.json:
            import json
            print(json.dumps([
                {
                    'status': r.status.value,
                    'updates': r.updates_performed,
                    'errors': r.errors
                }
                for r in results
            ], indent=2))
        else:
            print(f"Processed {len(results)} pending updates")
            for i, r in enumerate(results):
                print(f"  {i+1}. {r.status.value}: {len(r.updates_performed)} updates")
        return 0
    elif args.command == 'stats':
        stats = orchestrator.get_stats()
        if args.json:
            import json
            print(json.dumps(stats, indent=2))
        else:
            print("Evolution System Statistics:")
            print(f"  Total records: {stats.get('total_records', 0)}")
            print(f"  Significant changes: {stats.get('significant_changes', 0)}")
            print(f"  Soul snapshots: {stats.get('soul_snapshots', 0)}")
            print(f"  Last 24h: {stats.get('last_24h', 0)}")
            print("  By status:")
            for status, count in stats.get('by_status', {}).items():
                print(f"    {status}: {count}")
        return 0
    else:
        parser.print_help()
        return 1

    if args.json:
        import json
        print(json.dumps({
            'status': result.status.value,
            'updates': result.updates_performed,
            'errors': result.errors,
            'soul_snapshot': result.soul_snapshot_path
        }, indent=2))
    else:
        print(f"Update status: {result.status.value}")
        print(f"Updates performed: {len(result.updates_performed)}")
        for update in result.updates_performed:
            print(f"  - {update}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for error in result.errors:
                print(f"  - {error}")

    return 0 if result.status in [UpdateStatus.COMPLETED, UpdateStatus.SKIPPED] else 1


if __name__ == '__main__':
    sys.exit(main())
