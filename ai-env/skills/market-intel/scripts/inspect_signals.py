import sqlite3
import os

DB_PATH = "engine/ghost_memory.db"

def inspect_signals():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
        if not cursor.fetchone():
            print("ERROR: Table 'signals' not found. Has the engine run once?")
            return

        cursor.execute("SELECT ticker, confidence, ev, verdict, timestamp FROM signals ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        
        print(f"--- LATEST 5 SIGNALS FROM SYNAPSE ---")
        for row in rows:
            print(f"Ticker: {row[0]} | Conf: {row[1]*100:.1f}% | EV: {row[2]:.3f} | Result: {row[3]} | Time: {row[4]}")
        print("--------------------------------------")
        
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    inspect_signals()
