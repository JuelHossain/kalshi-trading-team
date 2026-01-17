import os
import json
import asyncio
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

try:
    import google.generativeai as genai
except ImportError:
    pass

class FixerAgent(BaseAgent):
    """
    Agent 13: The Fixer (Gemini 1.5 Pro)
    Role: AI Diagnostics & Root Cause Analysis.
    Triggers on system errors to provide suggested hotfixes.
    """
    
    def __init__(self, agent_id: int, bus: EventBus):
        super().__init__("FIXER", agent_id, bus)
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
        self.model = None

    async def start(self):
        if not self.api_key:
            await self.log("GEMINI_API_KEY missing. Fixer Offline.")
            return

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        await self.log("Fixer AI Engine Online (Gemini 1.5 Pro). Monitoring for failures.")
        
        # Subscribe to System Logs to find ERRORs
        await self.bus.subscribe("SYSTEM_LOG", self.handle_error_log)

    async def handle_error_log(self, message):
        level = message.payload.get('level')
        if level == "ERROR":
            error_msg = message.payload.get('message')
            await self.log(f"Detected Error: {error_msg}. Analyzing Root Cause...")
            
            analysis = await self.analyze_error(error_msg)
            
            # Publish Fix proposal
            await self.bus.publish("ERROR_FIX", analysis, self.name)
            
            # If confidence is high, log it explicitly
            if analysis.get('confidence', 0) > 80:
                await self.log(f"{Fore.GREEN}FIX PROPOSAL: {analysis['suggestedFix']}{Style.RESET_ALL}")
            
            # CRITICAL CIRCUIT BREAKER: Pause if confidence is extreme
            if analysis.get('confidence', 0) > 95:
                from core.db import set_system_status
                await self.log(f"{Fore.RED}EXTREME ERROR DETECTED. AUTO-PAUSING SYSTEM.{Style.RESET_ALL}")
                await set_system_status("PAUSED", f"Fixer Auto-Pause: {analysis.get('rootCause')}")


    async def analyze_error(self, error_message: str) -> Dict[str, Any]:
        if not self.model:
            return {"rootCause": "Offline", "suggestedFix": "N/A", "confidence": 0}

        prompt = f"""
        You are a Senior DevOps Engineer. A mission-critical trading bot encountered an error.
        
        Error: "{error_message}"
        
        Task:
        1. Analyze the root cause deeply.
        2. Provide a specific, actionable "Code Hotfix" or CLI command.
        3. Estimate confidence score (0-100).
        
        Return Strictly JSON:
        {{
            "rootCause": "string",
            "suggestedFix": "string",
            "confidence": int
        }}
        """
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            await self.log(f"AI Analysis failed: {e}")
            return {"rootCause": f"AI Failure: {e}", "suggestedFix": "Manual check", "confidence": 0}
