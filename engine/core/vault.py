import asyncio
import os

from core.logger import get_logger

logger = get_logger("VAULT")


class RecursiveVault:
    """
    PROTOCOL: The Recursive Vault
    Hard-coded capital preservation lock.
    """

    def __init__(self):
        # Configuration from Env
        self.PRINCIPAL_CAPITAL_CENTS = int(os.getenv("VAULT_PRINCIPAL_CENTS", "30000"))
        self.DAILY_PROFIT_THRESHOLD_CENTS = int(os.getenv("VAULT_PROFIT_THRESHOLD_CENTS", "5000"))
        self.HARD_FLOOR_CENTS = 25500  # $255.00 Hard Floor
        self.KILL_SWITCH_THRESHOLD_PCT = 0.85
        self.DB_PATH = "engine/ghost_memory.db"

        self.start_of_day_balance = 0
        self.current_balance = 0
        self.is_locked = False
        self.kill_switch_active = False
        self.initialized = False
        self._lock = asyncio.Lock()

        # Atomic balance tracking
        self._reserved_funds: int = 0  # Funds reserved for pending orders
        
        # Initialize DB Schema
        self._ensure_db_schema()

    def _ensure_db_schema(self):
        """Ensure the local SQLite schema is ready for persistence."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vault_reservations (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    total_reserved INTEGER NOT NULL DEFAULT 0
                )
            """)
            # Ensure at least one row exists
            cursor.execute("INSERT OR IGNORE INTO vault_reservations (id, total_reserved) VALUES (1, 0)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Local DB Error: {e}")

    async def initialize(self, current_balance_cents: int):
        async with self._lock:
            self.start_of_day_balance = current_balance_cents
            self.current_balance = current_balance_cents
            self.initialized = True
            
            # Load persisted reservations
            try:
                import sqlite3
                conn = sqlite3.connect(self.DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT total_reserved FROM vault_reservations WHERE id = 1")
                row = cursor.fetchone()
                if row:
                    self._reserved_funds = row[0]
                    if self._reserved_funds > 0:
                        logger.warning(f"Restored ${self._reserved_funds/100:.2f} in reservations from local storage.")
                conn.close()
            except Exception as e:
                logger.error(f"Failed to load reservations: {e}")

            # Initial kill switch check
            await self._check_kill_switch()
            logger.info(f"Initialized. SOD Balance: ${self.start_of_day_balance/100:.2f}")

    async def update_balance(self, new_balance_cents: int):
        async with self._lock:
            self.current_balance = new_balance_cents
            await self._check_lock()
            await self._check_kill_switch()

    async def _check_kill_switch(self):
        threshold = self.PRINCIPAL_CAPITAL_CENTS * self.KILL_SWITCH_THRESHOLD_PCT
        if self.current_balance < threshold:
            if not self.kill_switch_active:
                logger.critical(f"🚨 CRITICAL: Balance (${self.current_balance/100:.2f}) < 85% Principal Threshold (${threshold/100:.2f}).")
                logger.critical("KILL SWITCH ACTIVATED. HALTING ALL OPERATIONS.")
                self.kill_switch_active = True
        else:
            self.kill_switch_active = False

    async def _check_lock(self) -> bool:

        if not self.initialized:
            return False

        daily_profit = self.current_balance - self.start_of_day_balance

        if daily_profit >= self.DAILY_PROFIT_THRESHOLD_CENTS:
            if not self.is_locked:
                logger.info(f"🔒 PROFIT THRESHOLD (${daily_profit/100:.2f}) REACHED.")
                logger.info(f"PRINCIPAL PROTECTION ACTIVATED. FROZEN ${self.PRINCIPAL_CAPITAL_CENTS/100:.2f}.")
                self.is_locked = True
            return True

        return False

    async def get_tradeable_capital(self) -> int:
        """
        Returns amount available to wager in CENTS.
        If Locked: Balance - Principal (House Money Only).
        If Unlocked: Balance (Risking Principal).
        """
        async with self._lock:
            if self.is_locked:
                tradeable = self.current_balance - self.PRINCIPAL_CAPITAL_CENTS
                return max(0, tradeable)

            return self.current_balance

    def get_available_balance(self) -> int:
        """Return balance minus reserved funds (what can actually be used)."""
        return self.current_balance - self._reserved_funds

    def _save_reservations(self):
        """Persist current reservation total to local DB."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE vault_reservations SET total_reserved = ? WHERE id = 1", (self._reserved_funds,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Persistence Error: {e}")

    def reserve_funds(self, amount: int) -> bool:
        """
        Reserve funds for a pending order.
        Returns True if reservation successful, False if insufficient funds.
        """
        available = self.get_available_balance()
        if available < amount:
            return False

        self._reserved_funds += amount
        self._save_reservations()
        logger.warning(f"Reserved ${amount/100:.2f}. Available: ${self.get_available_balance()/100:.2f}")
        return True

    def confirm_reservation(self, amount: int):
        """
        Confirm a reservation as spent (deduct from actual balance).
        Called when order is successfully placed.
        """
        self._reserved_funds -= amount
        self.current_balance -= amount
        self._save_reservations()
        logger.info(f"Order confirmed. Deducted ${amount/100:.2f}. New balance: ${self.current_balance/100:.2f}")

    def release_reservation(self, amount: int):
        """
        Release reserved funds back to available pool.
        Called when order fails or is cancelled.
        """
        self._reserved_funds -= amount
        self._save_reservations()
        logger.info(f"Released ${amount/100:.2f} reservation. Available: ${self.get_available_balance()/100:.2f}")

    def release_all_reservations(self):
        """Release ALL current reservations (Emergency Rollback)."""
        released = self._reserved_funds
        self._reserved_funds = 0
        self._save_reservations()
        logger.info(f"Emergency Rollback: Released ALL reservations (${released/100:.2f})")

    def lock_principal(self):
        """Lock the principal amount to prevent trading with it."""
        self.is_locked = True
        logger.info(f"PRINCIPAL LOCKED. ${self.PRINCIPAL_CAPITAL_CENTS/100:.2f} protected. Trading with house money only.")
