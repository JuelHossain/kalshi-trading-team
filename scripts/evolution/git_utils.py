"""
Git operations wrapper for the evolution system.

Provides safe, cross-platform git operations with error handling.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class GitChange:
    """Represents a single git change."""
    status: str  # A (Added), M (Modified), D (Deleted), R (Renamed), etc.
    file_path: str
    old_path: Optional[str] = None  # For renames
    lines_added: int = 0
    lines_removed: int = 0


class GitUtils:
    """Utility class for git operations."""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self._git_available = self._check_git()

    def _check_git(self) -> bool:
        """Check if git is available."""
        try:
            subprocess.run(
                ['git', '--version'],
                cwd=self.repo_path,
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _run_git(self, args: List[str], check: bool = True) -> Tuple[int, str, str]:
        """
        Run a git command and return results.

        Args:
            args: Git command arguments
            check: Whether to raise on non-zero exit

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        if not self._git_available:
            raise RuntimeError("Git is not available")

        cmd = ['git'] + args
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if check and result.returncode != 0:
            raise RuntimeError(
                f"Git command failed: {' '.join(args)}\n"
                f"stderr: {result.stderr}"
            )

        return result.returncode, result.stdout, result.stderr

    def get_staged_files(self) -> List[GitChange]:
        """
        Get list of staged files with their status.

        Returns:
            List of GitChange objects
        """
        _, stdout, _ = self._run_git(['diff', '--cached', '--name-status'])

        changes = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('\t')
            status = parts[0][0]  # First character is the status

            if status == 'R':
                # Rename: status\told_path\tnew_path
                changes.append(GitChange(
                    status=status,
                    file_path=parts[2],
                    old_path=parts[1]
                ))
            else:
                changes.append(GitChange(
                    status=status,
                    file_path=parts[1]
                ))

        # Get line counts for each file
        for change in changes:
            if change.status != 'D':  # Skip deleted files
                try:
                    _, diff_stdout, _ = self._run_git(
                        ['diff', '--cached', '--numstat', change.file_path],
                        check=False
                    )
                    if diff_stdout:
                        parts = diff_stdout.strip().split('\t')
                        if len(parts) >= 2:
                            change.lines_added = int(parts[0]) if parts[0].isdigit() else 0
                            change.lines_removed = int(parts[1]) if parts[1].isdigit() else 0
                except Exception:
                    pass

        return changes

    def get_changed_files_since(self, commit_hash: str) -> List[GitChange]:
        """
        Get files changed since a specific commit.

        Args:
            commit_hash: The commit to compare against

        Returns:
            List of GitChange objects
        """
        _, stdout, _ = self._run_git(
            ['diff', '--name-status', f'{commit_hash}..HEAD']
        )

        changes = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('\t')
            status = parts[0][0]

            if status == 'R':
                changes.append(GitChange(
                    status=status,
                    file_path=parts[2],
                    old_path=parts[1]
                ))
            else:
                changes.append(GitChange(
                    status=status,
                    file_path=parts[1]
                ))

        return changes

    def get_last_commit_info(self) -> dict:
        """
        Get information about the last commit.

        Returns:
            Dict with hash, message, author, date
        """
        format_str = '%H|%s|%an|%ae|%ad'
        _, stdout, _ = self._run_git(
            ['log', '-1', f'--format={format_str}']
        )

        parts = stdout.strip().split('|')
        return {
            'hash': parts[0] if len(parts) > 0 else '',
            'message': parts[1] if len(parts) > 1 else '',
            'author_name': parts[2] if len(parts) > 2 else '',
            'author_email': parts[3] if len(parts) > 3 else '',
            'date': parts[4] if len(parts) > 4 else ''
        }

    def get_commit_info(self, commit_hash: str) -> dict:
        """
        Get information about a specific commit.

        Args:
            commit_hash: The commit hash

        Returns:
            Dict with commit information
        """
        format_str = '%H|%s|%an|%ae|%ad|%b'
        _, stdout, _ = self._run_git(
            ['log', '-1', f'--format={format_str}', commit_hash]
        )

        parts = stdout.strip().split('|')
        return {
            'hash': parts[0] if len(parts) > 0 else '',
            'message': parts[1] if len(parts) > 1 else '',
            'author_name': parts[2] if len(parts) > 2 else '',
            'author_email': parts[3] if len(parts) > 3 else '',
            'date': parts[4] if len(parts) > 4 else '',
            'body': parts[5] if len(parts) > 5 else ''
        }

    def get_current_branch(self) -> str:
        """Get the current git branch name."""
        _, stdout, _ = self._run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
        return stdout.strip()

    def get_repo_root(self) -> Path:
        """Get the repository root directory."""
        _, stdout, _ = self._run_git(['rev-parse', '--show-toplevel'])
        return Path(stdout.strip())

    def stage_files(self, files: List[str]) -> bool:
        """
        Stage files for commit.

        Args:
            files: List of file paths to stage

        Returns:
            True if successful
        """
        try:
            self._run_git(['add'] + files)
            return True
        except RuntimeError:
            return False

    def unstage_files(self, files: List[str]) -> bool:
        """
        Unstage files.

        Args:
            files: List of file paths to unstage

        Returns:
            True if successful
        """
        try:
            self._run_git(['reset', 'HEAD'] + files)
            return True
        except RuntimeError:
            return False

    def has_staged_changes(self) -> bool:
        """Check if there are staged changes."""
        _, stdout, _ = self._run_git(
            ['diff', '--cached', '--quiet'],
            check=False
        )
        return stdout == ''  # Non-zero exit means there are changes

    def is_in_git_repo(self) -> bool:
        """Check if current directory is in a git repository."""
        try:
            self._run_git(['rev-parse', '--git-dir'])
            return True
        except RuntimeError:
            return False

    def get_file_content_at_commit(self, file_path: str, commit_hash: str) -> Optional[str]:
        """
        Get file content at a specific commit.

        Args:
            file_path: Path to the file
            commit_hash: Commit hash

        Returns:
            File content or None if not found
        """
        try:
            _, stdout, _ = self._run_git(
                ['show', f'{commit_hash}:{file_path}'],
                check=False
            )
            return stdout
        except RuntimeError:
            return None

    def get_diff_stat(self, commit_hash: Optional[str] = None) -> dict:
        """
        Get diff statistics.

        Args:
            commit_hash: Optional commit to get stats for

        Returns:
            Dict with files_changed, insertions, deletions
        """
        if commit_hash:
            _, stdout, _ = self._run_git(
                ['diff', '--cached', '--shortstat', commit_hash]
            )
        else:
            _, stdout, _ = self._run_git(['diff', '--cached', '--shortstat'])

        stats = {'files_changed': 0, 'insertions': 0, 'deletions': 0}

        if stdout:
            # Parse output like: "5 files changed, 100 insertions(+), 20 deletions(-)"
            files_match = re.search(r'(\d+) files? changed', stdout)
            insertions_match = re.search(r'(\d+) insertions?', stdout)
            deletions_match = re.search(r'(\d+) deletions?', stdout)

            if files_match:
                stats['files_changed'] = int(files_match.group(1))
            if insertions_match:
                stats['insertions'] = int(insertions_match.group(1))
            if deletions_match:
                stats['deletions'] = int(deletions_match.group(1))

        return stats
