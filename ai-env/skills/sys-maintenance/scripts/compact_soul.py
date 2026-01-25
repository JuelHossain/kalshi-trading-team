import os
import re
from datetime import datetime

def compact_soul():
    soul_path = "ai-env/soul/identity.md"
    archive_dir = "ai-env/soul/archives"
    
    if not os.path.exists(soul_path):
        print("Soul file not found.")
        return

    with open(soul_path, "r") as f:
        content = f.read()

    # Find the Recent Intuition header
    header_marker = "##"
    search_term = "Recent Intuition"
    
    # Simple strategy: find the start of the section and the start of the next section (if any)
    start_idx = content.find(search_term)
    if start_idx == -1:
        print("Error: Could not find 'Recent Intuition' section.")
        return
    
    # Backup to the ## before it
    while start_idx > 0 and content[start_idx:start_idx+2] != "##":
        start_idx -= 1
        
    essence_part = content[:start_idx]
    intuition_part = content[start_idx:]

    # Entries are separated by \n### 
    entries = intuition_part.split("\n### ")
    header = entries[0]
    snapshots = entries[1:]

    print(f"Found {len(snapshots)} snapshots.")

    if len(snapshots) > 10:
        os.makedirs(archive_dir, exist_ok=True)
        
        to_archive = snapshots[:-5] # Keep last 5
        to_keep = snapshots[-5:]

        # Extract date range for naming
        def get_date(s):
            match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', s)
            return match.group(1) if match else "unknown"
        
        start_date = get_date(to_archive[0])
        end_date = get_date(to_archive[-1])
        archive_name = f"{archive_dir}/soul_archive_{start_date}_to_{end_date}.md"
        
        with open(archive_name, "w") as f:
            f.write(f"# Project Soul Archive: {start_date} to {end_date}\n\n")
            for s in to_archive:
                f.write(f"\n### {s.strip()}\n")

        print(f"Archived {len(to_archive)} snapshots to {archive_name}")

        with open(soul_path, "w") as f:
            f.write(essence_part)
            f.write(header)
            for s in to_keep:
                f.write(f"\n### {s.strip()}\n")
        
        print("Compaction complete.")

if __name__ == "__main__":
    compact_soul()
