import asyncio
import os

from colorama import Fore, Style


class RecursiveVault:
    """
    PROTOCOL: The Recursive Vault
    Hard-coded capital preservation lock.
    """

    def __init__(self):
        # Configuration from Env
        self.PRINCIPAL_CAPITAL_CENTS = int(os.getenv("VAULT_PRINCIPAL_CENTS", "30000"))
        self.DAILY_PROFIT_THRESHOLD_CENTS = int(os.getenv("VAULT_PROFIT_THRESHOLD_CENTS", "5000"))
        self.KILL_SWITCH_THRESHOLD_PCT = 0.85

        self.start_of_day_balance = 0
        self.current_balance = 0
        self.is_locked = False
        self.kill_switch_active = False
        self.initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self, current_balance_cents: int):
        async with self._lock:
            self.start_of_day_balance = current_balance_cents
            self.current_balance = current_balance_cents
            self.initialized = True
            # Initial kill switch check
            await self._check_kill_switch()
            print(
                f"{Fore.CYAN}[VAULT] Initialized. SOD Balance: ${self.start_of_day_balance/100:.2f}{Style.RESET_ALL}"
            )

    async def update_balance(self, new_balance_cents: int):
        async with self._lock:
            self.current_balance = new_balance_cents
            await self._check_lock()
            await self._check_kill_switch()

    async def _check_kill_switch(self):
        threshold = self.PRINCIPAL_CAPITAL_CENTS * self.KILL_SWITCH_THRESHOLD_PCT
        if self.current_balance < threshold:
            if not self.kill_switch_active:
                print(
                    f"{Fore.RED}[VAULT] [!] CRITICAL: Balance (${self.current_balance/100:.2f}) < 85% Principal Threshold (${threshold/100:.2f}).{Style.RESET_ALL}"
                )
                print(
                    f"{Fore.RED}[VAULT] KILL SWITCH ACTIVATED. HALTING ALL OPERATIONS.{Style.RESET_ALL}"
                )
                self.kill_switch_active = True
        else:
            self.kill_switch_active = False

    async def _check_lock(self) -> bool:

        if not self.initialized:
            return False

        daily_profit = self.current_balance - self.start_of_day_balance

        if daily_profit >= self.DAILY_PROFIT_THRESHOLD_CENTS:
            if not self.is_locked:
                print(
                    f"{Fore.GREEN}[VAULT] [LOCKED] PROFIT THRESHOLD (${daily_profit/100:.2f}) REACHED.{Style.RESET_ALL}"
                )
                print(
                    f"{Fore.GREEN}[VAULT] PRINCIPAL PROTECTION ACTIVATED. FROZEN ${self.PRINCIPAL_CAPITAL_CENTS/100:.2f}.{Style.RESET_ALL}"
                )
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
