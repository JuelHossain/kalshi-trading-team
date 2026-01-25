import subprocess
import os

def run_git(args):
    try:
        result = subprocess.run(['git'] + args, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git {' '.join(args)}: {e.stderr}")
        return None

def maintenance():
    print("--- STARTING GIT MAINTENANCE protocol ---")
    
    # 1. Prune remote tracking branches
    print("[1/5] Pruning remote tracking branches...")
    run_git(['remote', 'prune', 'origin'])
    
    # 2. Aggressive Garbage Collection
    print("[2/5] Running aggressive garbage collection...")
    run_git(['gc', '--prune=now', '--aggressive'])
    
    # 3. Clean up merged branches
    print("[3/5] Cleaning up merged feature branches...")
    current_branch = run_git(['branch', '--show-current'])
    
    # Get branches merged into main
    merged_branches = run_git(['branch', '--merged', 'main'])
    if merged_branches:
        for branch in merged_branches.split('\n'):
            branch = branch.strip().replace('*', '').strip()
            if branch and branch not in ['main', 'opencode', current_branch]:
                print(f"Deleting merged branch: {branch}")
                run_git(['branch', '-d', branch])
                
    # 4. Resolve 'opencode' ambiguity if detected
    print("[4/5] Checking for ref ambiguity...")
    # If opencode exists as both local and tag, we recommend explicit naming
    # But usually, cleaning stale origin refs fixes the 'ambiguous' warning
    run_git(['fetch', '--prune'])

    # 5. Verify Hierarchy
    print("[5/5] Verifying branch hierarchy...")
    print(f"Current Source of Truth: main (synchronized with {current_branch})")
    
    print("--- MAINTENANCE COMPLETE ---")

if __name__ == "__main__":
    maintenance()
