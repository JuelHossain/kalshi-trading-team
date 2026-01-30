#!/usr/bin/env python3
"""
Test script for the evolution system.

This script tests the various components of the evolution system
without requiring actual git commits.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.evolution.analyzer import ChangeAnalyzer, ChangeAnalysis, ChangeType
from scripts.evolution.config import get_config
from scripts.evolution.database import get_database, EvolutionRecord
from scripts.evolution.git_utils import GitUtils
from scripts.evolution.orchestrator import EvolutionOrchestrator


def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    config = get_config()
    assert len(config.mappings) > 0, "No mappings loaded"
    assert config.significance.min_lines_changed > 0, "Invalid min_lines_changed"
    print("  Config loaded successfully")
    print(f"  Mappings: {len(config.mappings)}")
    print(f"  High-value files: {len(config.significance.high_value_files)}")
    return True


def test_database():
    """Test database operations."""
    print("\nTesting database...")
    db = get_database()

    # Test logging
    record = EvolutionRecord(
        commit_hash="test_" + os.urandom(4).hex(),
        commit_message="Test commit",
        changed_files=["test.py"],
        doc_targets=["test.md"],
        is_significant=True,
        update_mode="sync",
        soul_snapshot_created=True,
        status="completed",
        branch="main",
        agent_tag="test"
    )

    record_id = db.log_evolution(record)
    assert record_id > 0, "Failed to log evolution"
    print(f"  Logged evolution record: {record_id}")

    # Test retrieval
    retrieved = db.get_record(record.commit_hash)
    assert retrieved is not None, "Failed to retrieve record"
    assert retrieved.commit_hash == record.commit_hash
    print("  Record retrieval works")

    # Test stats
    stats = db.get_stats()
    assert 'total_records' in stats
    print(f"  Stats: {stats}")

    return True


def test_analyzer():
    """Test change analyzer."""
    print("\nTesting analyzer...")
    analyzer = ChangeAnalyzer()

    # Create mock changes
    class MockChange:
        def __init__(self, path, status, added=0, removed=0):
            self.file_path = path
            self.status = status
            self.lines_added = added
            self.lines_removed = removed

    # Test with significant changes
    changes = [
        MockChange("engine/agents/brain.py", "M", 50, 10),
        MockChange("engine/core/synapse.py", "M", 20, 5),
    ]

    analysis = analyzer._analyze_changes(changes)

    assert analysis.is_significant, "Should be significant"
    assert analysis.triggers_soul, "Should trigger soul"
    assert analysis.update_mode == "sync", "Should be sync"
    assert ChangeType.AGENT_LOGIC in analysis.change_types
    print("  Significant change detection works")

    # Test with insignificant changes
    changes = [
        MockChange("README.md", "M", 2, 1),
    ]
    analysis = analyzer._analyze_changes(changes)
    assert not analysis.is_significant, "Should not be significant"
    print("  Insignificant change detection works")

    return True


def test_git_utils():
    """Test git utilities."""
    print("\nTesting git utils...")
    git = GitUtils()

    # Test repo detection
    assert git.is_in_git_repo(), "Should be in git repo"
    print("  Git repo detected")

    # Test branch
    branch = git.get_current_branch()
    assert branch, "Should have a branch"
    print(f"  Current branch: {branch}")

    # Test commit info
    info = git.get_last_commit_info()
    assert 'hash' in info, "Should have commit hash"
    print(f"  Last commit: {info['hash'][:8]}")

    return True


def test_updaters():
    """Test documentation updaters."""
    print("\nTesting updaters...")

    from scripts.evolution.updaters.soul_updater import SoulUpdater
    from scripts.evolution.updaters.persona_updater import PersonaUpdater

    # Test soul updater
    soul = SoulUpdater()
    assert soul.can_handle("soul_snapshot"), "Should handle soul targets"
    print("  Soul updater initialized")

    # Test persona updater
    persona = PersonaUpdater()
    assert persona.can_handle("ai-env/personas/"), "Should handle persona targets"
    print("  Persona updater initialized")

    return True


def test_orchestrator():
    """Test orchestrator."""
    print("\nTesting orchestrator...")
    orch = EvolutionOrchestrator()

    # Check components
    assert orch.config is not None
    assert orch.database is not None
    assert orch.git is not None
    assert orch.analyzer is not None
    print("  Orchestrator components initialized")

    # Check stats
    stats = orch.get_stats()
    assert 'total_records' in stats
    print(f"  Stats: {stats}")

    return True


def test_hooks():
    """Test hook scripts exist and are valid."""
    print("\nTesting hook scripts...")

    hooks_dir = Path(__file__).parent.parent / "hooks"

    # Check Unix hooks
    pre_commit = hooks_dir / "pre-commit-evo.sh"
    post_commit = hooks_dir / "post-commit-evo.sh"

    assert pre_commit.exists(), "pre-commit-evo.sh not found"
    assert post_commit.exists(), "post-commit-evo.sh not found"
    print("  Unix hook scripts exist")

    # Check Windows hooks
    pre_commit_bat = hooks_dir / "pre-commit-evo.bat"
    post_commit_bat = hooks_dir / "post-commit-evo.bat"

    assert pre_commit_bat.exists(), "pre-commit-evo.bat not found"
    assert post_commit_bat.exists(), "post-commit-evo.bat not found"
    print("  Windows hook scripts exist")

    # Check content
    pre_content = pre_commit.read_text()
    assert "analyzer.py" in pre_content, "Missing analyzer reference"
    assert "orchestrator.py" in pre_content, "Missing orchestrator reference"
    print("  Hook scripts have correct content")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Sentient Alpha Evolution System - Test Suite")
    print("=" * 60)

    tests = [
        ("Configuration", test_config),
        ("Database", test_database),
        ("Git Utils", test_git_utils),
        ("Analyzer", test_analyzer),
        ("Updaters", test_updaters),
        ("Orchestrator", test_orchestrator),
        ("Hooks", test_hooks),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"  {name}: PASSED")
            else:
                failed += 1
                print(f"  {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
