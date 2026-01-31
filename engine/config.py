
import os

from dotenv import load_dotenv

# Load Env
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# --- APP CONFIG ---
IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
JSON_LOGS = os.getenv("JSON_LOGS", "false").lower() == "true"
PORT = int(os.getenv("PORT", "3002"))

# --- AGENT CONFIG ---
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
MAX_VARIANCE = float(os.getenv("MAX_VARIANCE", "0.25"))
MAX_STAKE_CENTS = 7500  # $75
PROFIT_LOCK_THRESHOLD_CENTS = 5000 # $50

# --- VAULT CONFIG ---
HARD_FLOOR_CENTS = 25500 # $255
VAULT_Principal_CENTS = 30000 # $300
DAILY_PROFIT_GOAL_CENTS = 5000 # $50

# --- SAFETY CONFIG ---
KILL_SWITCH = os.getenv("KILL_SWITCH", "false").lower() == "true"
SIMULATION_ITERATIONS = 10000

# --- API KEYS ---
# (Loaded via os.environ in agents, but defined here for reference)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
