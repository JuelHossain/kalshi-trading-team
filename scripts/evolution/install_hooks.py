#!/usr/bin/env python3
"""
Installation script for the evolution system git hooks.

This script installs the pre-commit and post-commit hooks into the
.git/hooks directory, making them executable and backing up any
existing hooks.
"""

import os
import sys
import shutil
import platform
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    # This script is in scripts/evolution/
    return Path(__file__).parent.parent.parent


def get_git_hooks_dir() -> Path:
    """Get the git hooks directory."""
    return get_project_root() / ".git" / "hooks"


def backup_existing_hook(hooks_dir: Path, hook_name: str) -> bool:
    """Backup an existing hook if it exists."""
    hook_path = hooks_dir / hook_name
    if hook_path.exists():
        backup_path = hooks_dir / f"{hook_name}.backup.{int(os.path.getmtime(hook_path))}"
        print(f"Backing up existing {hook_name} to {backup_path.name}")
        shutil.copy2(hook_path, backup_path)
        return True
    return False


def install_hook(hooks_dir: Path, source_dir: Path, hook_name: str) -> bool:
    """Install a single hook."""
    # Determine which hook file to use based on platform
    is_windows = platform.system() == "Windows"

    if is_windows:
        source_hook = source_dir / f"{hook_name}-evo.bat"
        target_hook = hooks_dir / f"{hook_name}.bat"
    else:
        source_hook = source_dir / f"{hook_name}-evo.sh"
        target_hook = hooks_dir / hook_name

    if not source_hook.exists():
        print(f"Error: Source hook not found: {source_hook}")
        return False

    # Backup existing hook
    backup_existing_hook(hooks_dir, target_hook.name)

    # Copy the hook
    shutil.copy2(source_hook, target_hook)

    # Make executable on Unix
    if not is_windows:
        os.chmod(target_hook, 0o755)

    print(f"Installed {hook_name} hook: {target_hook}")
    return True


def create_wrapper_hook(hooks_dir: Path, hook_name: str) -> bool:
    """
    Create a wrapper hook that calls both the evolution hook and any existing user hook.

    This allows the evolution system to coexist with user-defined hooks.
    """
    is_windows = platform.system() == "Windows"

    if is_windows:
        # On Windows, create a .bat wrapper
        wrapper_path = hooks_dir / f"{hook_name}.bat"
        wrapper_content = f"""@echo off
REM Auto-generated wrapper for {hook_name} hooks

REM Run evolution hook first
set "EVO_HOOK=%~dp0{hook_name}-evo.bat"
if exist "%EVO_HOOK%" (
    call "%EVO_HOOK%"
)

REM Run user hook if it exists
set "USER_HOOK=%~dp0{hook_name}.user.bat"
if exist "%USER_HOOK%" (
    call "%USER_HOOK%"
)
"""
    else:
        # On Unix, create a shell wrapper
        wrapper_path = hooks_dir / hook_name
        wrapper_content = f"""#!/bin/bash
# Auto-generated wrapper for {hook_name} hooks

# Run evolution hook first
EVO_HOOK="$(dirname "$0")/{hook_name}-evo.sh"
if [ -x "$EVO_HOOK" ]; then
    "$EVO_HOOK"
    EVO_EXIT=$?
    if [ $EVO_EXIT -ne 0 ]; then
        echo "Warning: Evolution hook exited with code $EVO_EXIT"
    fi
fi

# Run user hook if it exists
USER_HOOK="$(dirname "$0")/{hook_name}.user"
if [ -x "$USER_HOOK" ]; then
    "$USER_HOOK"
    exit $?
fi

exit 0
"""

    wrapper_path.write_text(wrapper_content, encoding='utf-8')

    if not is_windows:
        os.chmod(wrapper_path, 0o755)

    print(f"Created wrapper hook: {wrapper_path}")
    return True


def main():
    """Main installation function."""
    print("=" * 60)
    print("Sentient Alpha Evolution System - Hook Installation")
    print("=" * 60)

    project_root = get_project_root()
    hooks_dir = get_git_hooks_dir()
    source_dir = project_root / "scripts" / "hooks"

    # Check if we're in a git repository
    if not hooks_dir.exists():
        print(f"Error: Not a git repository or .git directory not found")
        print(f"Expected: {hooks_dir}")
        return 1

    # Check if hooks source directory exists
    if not source_dir.exists():
        print(f"Error: Hooks source directory not found: {source_dir}")
        return 1

    print(f"Project root: {project_root}")
    print(f"Git hooks dir: {hooks_dir}")
    print(f"Source dir: {source_dir}")
    print()

    # Install pre-commit hook
    print("Installing pre-commit hook...")
    if install_hook(hooks_dir, source_dir, "pre-commit"):
        print("  Success!")
    else:
        print("  Failed!")

    print()

    # Install post-commit hook
    print("Installing post-commit hook...")
    if install_hook(hooks_dir, source_dir, "post-commit"):
        print("  Success!")
    else:
        print("  Failed!")

    print()
    print("=" * 60)
    print("Installation complete!")
    print()
    print("To disable the evolution system temporarily:")
    print("  export EVOLUTION_DISABLED=1  # Unix")
    print("  set EVOLUTION_DISABLED=1     # Windows")
    print()
    print("To uninstall:")
    print("  rm .git/hooks/pre-commit .git/hooks/post-commit")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
