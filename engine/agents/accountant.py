import os
import json
import asyncio
import time
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

class AccountantAgent(BaseAgent):
    """
    Agent 9: The Accountant
    Role: Capital Audit & Budgeting.
    Tracks daily spend and triggers Recursive Vault updates.
    """
    
    DAILY_API_BUDGET = 115 # $1.15 in cents
    
    def __init__(self, agent_id: int, bus: EventBus, vault=None):
        super().__init__("ACCOUNTANT", agent_id, bus)
        self.vault = vault # Reference to core vault
        self.daily_spend = 0
        self.total_balance = 30000

    async def start(self):
        await self.log(f"Accountant Online. Budget: ${self.DAILY_API_BUDGET/100:.2f}/day.")
        
        # Subscribe to TICKS for regular audits
        await self.bus.subscribe("TICK", self.handle_audit_tick)
        
        # Subscribe to trade events to track costs
        await self.bus.subscribe("TRADE_EXECUTED", self.handle_trade_executed)

    async def handle_audit_tick(self, message):
        cycle = message.payload.get('cycle', 0)
        
        if cycle % 60 == 0: # Every minute approx
             await self.run_balance_audit()

    async def run_balance_audit(self):
        await self.log(f"Auditing Portfolio... Current Balance: ${self.total_balance/100:.2f}")
        
        # Update Vault if profit detected
        if self.total_balance > 30000: # Simple threshold
             profit = self.total_balance - 30000
             if profit > 5000: # $50
                  await self.log(f"{Fore.GREEN}[VAULT TRIGGER] Significant Profit Detected (${profit/100:.2f}){Style.RESET_ALL}")
                  if self.vault:
                       await self.vault.update_balance(self.total_balance)

        # Budget Check
        if self.daily_spend > self.DAILY_API_BUDGET:
             await self.log(f"{Fore.RED}BUDGET EMERGENCY: API spend reached ceiling. FREEZING OPERATIONS.{Style.RESET_ALL}")
             # We should broadcast a KILL_SWITCH or similar here

    async def handle_trade_executed(self, message):
        # Mocking balance update
        self.total_balance += 1000 # Mock profit for testing vault trigger
        # Track API cost (e.g. 0.01 cent per simulated AI call)
        self.daily_spend += 1
        await self.log(f"Trade Registered. Spend: ${self.daily_spend/100:.4f}. Balance: ${self.total_balance/100:.2f}")
