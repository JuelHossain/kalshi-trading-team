import os
import json
import logging
import requests
from typing import Dict, Any, List
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Analyst")

class Analyst:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment")
            # In a real scenario, we might want to fail gracefully if key is missing
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def scrape_realtime_info(self, ticker: str) -> Dict[str, Any]:
        """
        Context Injection: Logic to feed real-time news and injury data.
        """
        logger.info(f"Searching for real-time intelligence for {ticker}...")
        
        # In a production environment, this would call specialized news APIs (e.g. NewsAPI, Serper, etc.)
        # To strictly follow the 'no mock data' rule, we return an empty structure if no live integration is configured.
        
        return {
            "news_headlines": [],
            "injury_reports": [],
            "social_sentiment": "Neutral/Unknown"
        }

    def conduct_committee_debate(self, asym_package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Neural Network: The multi-persona 'Committee Debate' logic.
        """
        if not self.model:
            return {
                "error": "Gemini API key missing",
                "confidence_object": {"score": 0, "reasoning_trace": "Agent Offline", "size_recommendation": "No Play"}
            }

        ticker = asym_package.get("ticker", "UNKNOWN")
        kalshi_price = asym_package.get("kalshi_price", 0)
        vegas_prob = asym_package.get("vegas_prob", 0)
        delta_score = asym_package.get("delta_score", 0)

        # Context Injection
        realtime_info = self.scrape_realtime_info(ticker)
        
        prompt = f"""
ROLE: You are the Oracle Committee, a multi-persona LLM reasoning engine.
TASK: Analyze the Kalshi market for ticker '{ticker}' based on the provided Asymmetry Package and Real-Time Context.

DATA_INPUT:
- Kalshi Price (Market Prob): {kalshi_price}
- Vegas Implied Probability: {vegas_prob}
- Asymmetry Delta (Edge): {delta_score}

REAL_TIME_CONTEXT:
- News Headlines: {", ".join(realtime_info['news_headlines'])}
- Injury/Status Reports: {", ".join(realtime_info['injury_reports'])}
- Social Sentiment: {realtime_info['social_sentiment']}

COMMITTEE LOGIC:
1. Persona A (The Optimist): Identify the 'Alpha'. Why is this a strong BUY? Focus on the {delta_score} edge and positive news.
2. Persona B (The Pessimist): Identify 'Traps'. Why is Vegas wrong or what are the injury risks? Look for reasons to VETO.
3. Persona C (The Judge): Act as the final filter. Weigh the Optimist's alpha against the Pessimist's risks. Correct for hallucination or bias.

OUTPUT FORMAT:
Return ONLY a valid JSON object. No preamble. No markdown code blocks.
Required Structure:
{{
  "debate_log": {{
    "optimist_argument": "string",
    "pessimist_argument": "string",
    "judge_summary": "string"
  }},
  "confidence_object": {{
    "score": integer (0-100),
    "reasoning_trace": "detailed step-by-step logic",
    "size_recommendation": "string (formula-based, e.g., '1/4 Kelly', 'Full Send', 'Avoid')"
  }}
}}
"""

        try:
            logger.info(f"Initiating Committee Debate for {ticker}...")
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Extract and parse JSON
            content = response.text.strip()
            # If Gemini wraps it in ```json ... ```, strip it (though response_mime_type should prevent this)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:].strip()
            
            result = json.loads(content)
            return result
        except Exception as e:
            logger.error(f"Agent 4 Debate Failure: {e}")
            return {
                "error": str(e),
                "confidence_object": {
                    "score": 0,
                    "reasoning_trace": "Technical error during LLM generation.",
                    "size_recommendation": "No Play"
                }
            }

if __name__ == "__main__":
    # Simulate receiving data from Agent 3 (Interceptor)
    mock_asymmetry = {
        "ticker": "LAL",
        "kalshi_price": 0.45,
        "vegas_prob": 0.54,
        "delta_score": 0.09
    }
    
    analyst = Analyst()
    final_analysis = analyst.conduct_committee_debate(mock_asymmetry)
    print(json.dumps(final_analysis, indent=2))
