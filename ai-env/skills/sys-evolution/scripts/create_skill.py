import sys
import os

def create_skill(name, description):
    base_path = f"ai-env/skills/{name}"
    if os.path.exists(base_path):
        print(f"Error: Skill '{name}' already exists.")
        return

    os.makedirs(f"{base_path}/scripts")
    
    skill_md = f"""# Skill: {name.replace('-', ' ').title()}
---
description: {description}
---

## 🛠️ Usage
[Add usage instructions here]

## 📝 Automation Scripts
- `scripts/` - Add implementation scripts here.
"""
    with open(f"{base_path}/SKILL.md", "w") as f:
        f.write(skill_md)
    
    print(f"Skill '{name}' created successfully in ai-env/skills.")
    print("Reminder: Run '/sync' to update root symlinks.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 create_skill.py <name> <description>")
    else:
        create_skill(sys.argv[1], sys.argv[2])
