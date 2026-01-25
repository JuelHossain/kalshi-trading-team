import sys
import os

# Add engine to path
sys.path.append(os.path.join(os.getcwd(), 'engine'))

from agents.brain import BrainAgent
from core.bus import EventBus

bus = EventBus()
brain = BrainAgent(3, bus)

print(f"PERSONA - OPTIMIST:\n{brain.personas['optimist']}\n")
print(f"PERSONA - CRITIC:\n{brain.personas['critic']}\n")

if "# Persona: The Optimist" in brain.personas['optimist']:
    print("✅ SUCCESS: Optimist persona loaded from OpenCode.")
else:
    print("❌ FAILURE: Optimist persona not loaded correctly.")

if "# Persona: The Critic" in brain.personas['critic']:
    print("✅ SUCCESS: Critic persona loaded from OpenCode.")
else:
    print("❌ FAILURE: Critic persona not loaded correctly.")
