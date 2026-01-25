import os

def sync():
    source_dir = "ai-env/skills"
    target_dir = ".opencode/skills"

    if not os.path.exists(target_dir):
        print(f"Error: {target_dir} does not exist (Broken link?)")
        return

    # If target is a symlink to source (as we set it up), individual files are already synced
    # However, if target_dir is a directory containing symlinks to individual skills, 
    # we need to ensure every folder in source has a link in target.
    
    # Check if target_dir is itself a symlink to source_dir
    if os.path.islink(target_dir):
        target_path = os.readlink(target_dir)
        if target_path.endswith("ai-env/skills"):
            print("Universal symlink detected. all skills are automatically synced.")
            return

    # If it's a real directory, sync individual kids
    for skill in os.listdir(source_dir):
        src_skill = os.path.join(source_dir, skill)
        trg_skill = os.path.join(target_dir, skill)
        if not os.path.exists(trg_skill):
            os.symlink(os.path.abspath(src_skill), trg_skill)
            print(f"Linked new skill: {skill}")

if __name__ == "__main__":
    sync()
