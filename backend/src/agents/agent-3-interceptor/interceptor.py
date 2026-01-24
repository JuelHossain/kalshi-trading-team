import os
import json
import logging
import math
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import requests

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

try:
    from dotenv import load_dotenv
    load_dotenv(".env")
    load_dotenv(".env.local")
    load_dotenv("backend/.env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Interceptor")

@dataclass
class AsymmetryPackage:
    ticker: str
    kalshi_price: float
    vegas_prob: float
    delta_score: float

class Interceptor:
    def __init__(self):
        self.rapid_api_key = os.getenv("RAPID_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
        self.threshold = 0.05  # 5% Gap
        
        # Mapping of common sports to their RapidAPI hosts
        self.sport_hosts = {
            "nba": "api-basketball.p.rapidapi.com",
            "nfl": "api-american-football.p.rapidapi.com",
            "mlb": "api-baseball.p.rapidapi.com",
            "nhl": "api-hockey.p.rapidapi.com",
            "soccer": "api-football-v1.p.rapidapi.com"
        }

    def fetch_vegas_odds(self, sport: str = "nba") -> List[Dict]:
        """Vegas Sync: Fetch odds from RapidAPI (API-Sports)"""
        if not self.rapid_api_key:
            logger.error("RAPID_API_KEY not found in environment")
            return []

        host = self.sport_hosts.get(sport.lower(), "api-basketball.p.rapidapi.com")
        url = f"https://{host}/odds"
        
        # Note: In a real scenario, you'd need league/season. 
        # For NBA, league 12 is usually NBA.
        params = {"league": "12", "season": "2023-2024"} 
        
        headers = {
            "X-RapidAPI-Key": self.rapid_api_key,
            "X-RapidAPI-Host": host
        }

        try:
            logger.info(f"Fetching {sport} odds from {host}...")
            # response = requests.get(url, headers=headers, params=params, timeout=10)
            # if response.status_code == 200:
            #    return response.json().get("response", [])
            
            # Mock data for demonstration if API call is skipped or fails
            return [
                {
                    "teams": {"home": {"name": "Los Angeles Lakers"}, "away": {"name": "Boston Celtics"}},
                    "bookmakers": [{
                        "name": "Bet365",
                        "bets": [{
                            "name": "Match Winner", 
                            "values": [{"value": "Home", "odd": "1.85"}, {"value": "Away", "odd": "2.05"}]
                        }]
                    }]
                }
            ]
        except Exception as e:
            logger.error(f"Failed to fetch Vegas odds: {e}")
            return []

    def simplified_fuzzy_match(self, ticker: str, targets: List[str]) -> Optional[str]:
        """Name matching logic (tries RapidFuzz, then Gemini, then basic)"""
        if not targets:
            return None
            
        ticker = ticker.upper()
        # Common mappings for specific sports
        mappings = {
            "LAL": "Lakers", "BOS": "Celtics", "GSW": "Warriors", 
            "PHX": "Suns", "KC": "Chiefs", "BAL": "Ravens"
        }
        search_term = mappings.get(ticker, ticker)

        # 1. Try RapidFuzz if available
        if HAS_RAPIDFUZZ:
            match = process.extractOne(search_term, targets, scorer=fuzz.WRatio)
            if match and match[1] > 70:
                return match[0]

        # 2. Simple Substring Fallback
        for target in targets:
            if search_term.lower() in target.lower():
                return target
        return None

    def gemini_fuzzy_match(self, ticker: str, team_names: List[str]) -> Optional[str]:
        """Fuzzy Matching: Use Gemini Flash for complex name mapping"""
        if not self.gemini_api_key:
            return self.simplified_fuzzy_match(ticker, team_names)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
        
        prompt = f"""
        Task: Match the ticker to the most likely team from the list.
        Ticker: {ticker}
        Teams: {', '.join(team_names)}
        
        Return ONLY the team name from the list that matches, or 'None' if no clear match.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                result = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if result in team_names:
                    return result
        except Exception:
            pass
        
        return self.simplified_fuzzy_match(ticker, team_names)

    def calculate_asymmetry(self, kalshi_data: List[Dict], vegas_odds: List[Dict]) -> List[AsymmetryPackage]:
        """The Delta Brain: Compare Kalshi price probability to Vegas implied probability"""
        packages = []
        vegas_map = {}
        
        for game in vegas_odds:
            home = game["teams"]["home"]["name"]
            away = game["teams"]["away"]["name"]
            
            for bookie in game.get("bookmakers", []):
                for bet in bookie.get("bets", []):
                    if bet["name"] == "Match Winner":
                        for val in bet["values"]:
                            team = home if val["value"] == "Home" else away
                            odd = float(val["odd"])
                            vegas_map[team] = 1.0 / odd
                if vegas_map: break

        team_names = list(vegas_map.keys())
        
        for market in kalshi_data:
            ticker = market.get("ticker", "")
            k_prob = market.get("kalshi_prob", 0.5)
            
            # Fuzzy match
            matched_team = self.gemini_fuzzy_match(ticker, team_names)
            
            if matched_team:
                v_prob = vegas_map[matched_team]
                gap = v_prob - k_prob
                
                # Threshold Guard: Gap > 5%
                if gap > self.threshold:
                    logger.info(f"Signal Found: {ticker} (Gap: {gap:.2%})")
                    packages.append(AsymmetryPackage(
                        ticker=ticker,
                        kalshi_price=k_prob,
                        vegas_prob=v_prob,
                        delta_score=gap
                    ))
        
        return packages

    def process_markets(self, scouted_markets: List[Dict]):
        """Output: An 'Asymmetry Package' for the Analyst"""
        vegas_data = self.fetch_vegas_odds()
        results = self.calculate_asymmetry(scouted_markets, vegas_data)
        return [asdict(p) for p in results]

if __name__ == "__main__":
    # Example input from Agent 2 (The Scout)
    sample_input = [
        {"ticker": "LAL", "kalshi_prob": 0.40}, 
        {"ticker": "BOS", "kalshi_prob": 0.55}
    ]
    
    interceptor = Interceptor()
    asymmetry_report = interceptor.process_markets(sample_input)
    print(json.dumps(asymmetry_report, indent=2))
