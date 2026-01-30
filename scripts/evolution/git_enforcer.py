"""
Git Enforcement Module for Agent Compliance

Ensures agents follow git rules:
1. Pull before starting work
2. Commit atomically after changes
3. Use handoff for significant changes
4. Keep working directory clean
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database import EvolutionDatabase


class GitEnforcer:
    """Enforces git compliance for agents."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.db = EvolutionDatabase()
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def _run_git(self, args: List[str], check: bool = True) -> Tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            if check and result.returncode != 0:
                self.errors.append(f"Git command failed: git {' '.join(args)} - {result.stderr}")
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            self.errors.append(f"Git command error: {e}")
            return 1, "", str(e)

    def check_remote_sync(self) -> bool:
        """Check if local branch is synced with remote."""
        # Get current branch
        rc, branch, _ = self._run_git(["branch", "--show-current"], check=False)
        if rc != 0:
            return False

        branch = branch.strip()

        # Check if remote exists
        rc, _, _ = self._run_git(["rev-parse", f"origin/{branch}"], check=False)
        if rc != 0:
            # No remote tracking branch
            return True  # Not an error if no remote

        # Check if local is behind remote
        rc, behind, _ = self._run_git(
            ["rev-list", "--count", f"HEAD..origin/{branch}"],
            check=False
        )
        if rc == 0:
            behind_count = int(behind.strip())
            if behind_count > 0:
                self.warnings.append(
                    f"Local branch is {behind_count} commit(s) behind origin/{branch}. "
                    "Run: git pull --rebase origin main"
                )
                return False

        return True

    def check_uncommitted_changes(self) -> Tuple[int, List[str]]:
        """Check for uncommitted changes. Returns (count, list of files)."""
        rc, status, _ = self._run_git(["status", "--porcelain"], check=False)
        if rc != 0:
            return 0, []

        lines = [line.strip() for line in status.split('\n') if line.strip()]
        files = [line[3:] for line in lines]  # Remove status prefix

        return len(files), files

    def check_last_handoff(self) -> Optional[datetime]:
        """Get timestamp of last handoff from database."""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp FROM evolution_log
                WHERE event_type = 'handoff'
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()

            if row:
                return datetime.fromisoformat(row[0])
            return None
        except Exception:
            return None

    def enforce_pre_work(self) -> bool:
        """
        Enforce git rules BEFORE starting work.
        Should be called when agent starts.
        """
        self.warnings = []
        self.errors = []

        # Check 1: Verify we're in a git repo
        rc, _, _ = self._run_git(["rev-parse", "--git-dir"], check=False)
        if rc != 0:
            self.errors.append("Not in a git repository!")
            return False

        # Check 2: Verify remote is accessible
        self.check_remote_sync()

        # Check 3: Check for existing uncommitted changes
        change_count, files = self.check_uncommitted_changes()
        if change_count > 0:
            self.warnings.append(
                f"Found {change_count} uncommitted file(s) from previous work. "
                f"Consider running: ./scripts/handoff.sh 'chore: commit pending changes'"
            )

        return len(self.errors) == 0

    def enforce_pre_commit(self) -> bool:
        """
        Enforce git rules BEFORE committing.
        Should be called from pre-commit hook.
        """
        self.warnings = []
        self.errors = []

        # Check 1: Remote sync
        self.check_remote_sync()

        # Check 2: Evolution system is active
        if not (self.project_root / "scripts" / "evolution" / "orchestrator.py").exists():
            self.warnings.append("Evolution system not found. Documentation may be out of sync.")

        return len(self.errors) == 0

    def enforce_post_work(self, force: bool = False) -> Dict:
        """
        Enforce git rules AFTER completing work.
        Should be called when agent finishes.

        Args:
            force: If True, fail if there are uncommitted changes

        Returns:
            Dict with status and recommendations
        """
        self.warnings = []
        self.errors = []

        change_count, files = self.check_uncommitted_changes()

        result = {
            "status": "clean",
            "changes": change_count,
            "files": files,
            "warnings": [],
            "errors": [],
            "recommendation": None
        }

        if change_count > 0:
            if change_count > 50:
                result["status"] = "critical"
                result["recommendation"] = (
                    "CRITICAL: Too many uncommitted changes. "
                    "Run: ./scripts/handoff.sh 'feat: implement [feature name]'"
                )
            elif change_count > 10:
                result["status"] = "warning"
                result["recommendation"] = (
                    "WARNING: Multiple uncommitted changes. "
                    "Run: ./scripts/handoff.sh 'feat: [description]'"
                )
            else:
                result["status"] = "notice"
                result["recommendation"] = (
                    "Consider committing: "
                    "./scripts/handoff.sh 'fix: [description]'"
                )

            if force:
                self.errors.append(f"Uncommitted changes detected: {change_count} file(s)")

        result["warnings"] = self.warnings
        result["errors"] = self.errors

        return result

    def print_report(self):
        """Print enforcement report."""
        print("=" * 50)
        print("GIT COMPLIANCE REPORT")
        print("=" * 50)

        if self.errors:
            print("\n❌ ERRORS (Must fix before proceeding):")
            for error in self.errors:
                print(f"   - {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS (Should address):")
            for warning in self.warnings:
                print(f"   - {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All git compliance checks passed!")

        print("=" * 50)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Git Enforcement for Agent Compliance"
    )
    parser.add_argument(
        "action",
        choices=["pre-work", "pre-commit", "post-work", "check"],
        help="Enforcement action to run"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fail on warnings as well as errors"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    enforcer = GitEnforcer()

    if args.action == "pre-work":
        success = enforcer.enforce_pre_work()
        if args.json:
            print(json.dumps({
                "success": success,
                "warnings": enforcer.warnings,
                "errors": enforcer.errors
            }))
        else:
            enforcer.print_report()
        sys.exit(0 if success else 1)

    elif args.action == "pre-commit":
        success = enforcer.enforce_pre_commit()
        if args.json:
            print(json.dumps({
                "success": success,
                "warnings": enforcer.warnings,
                "errors": enforcer.errors
            }))
        else:
            enforcer.print_report()
        sys.exit(0 if success else 1)

    elif args.action == "post-work":
        result = enforcer.enforce_post_work(force=args.force)
        if args.json:
            print(json.dumps(result))
        else:
            print("=" * 50)
            print("POST-WORK GIT CHECK")
            print("=" * 50)
            print(f"\nStatus: {result['status'].upper()}")
            print(f"Uncommitted files: {result['changes']}")

            if result['recommendation']:
                print(f"\n👉 {result['recommendation']}")

            if result['warnings']:
                print("\nWarnings:")
                for w in result['warnings']:
                    print(f"  - {w}")

        sys.exit(0 if result['status'] != 'critical' else 1)

    elif args.action == "check":
        enforcer.enforce_pre_work()
        enforcer.print_report()
        sys.exit(0 if not enforcer.errors else 1)


if __name__ == "__main__":
    main()
