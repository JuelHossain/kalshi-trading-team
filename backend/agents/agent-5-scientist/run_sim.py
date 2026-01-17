# Agent 5: The Simulation Scientist (Python Core)
import sys
import json
import numpy as np

def run_monte_carlo(market_title, win_prob, current_price_cents):
    """
    Runs 10,000 simulations to calculate Expected Value (EV) and Risk.
    """
    SIM_COUNT = 10000
    wager = 100 # Standard unit for Sim
    
    # 1. Setup Probabilities
    # We treat the Analyst's confidence as the 'True Probability' for the sim
    # If Analyst says 75%, we simulate a world where the event happens 75% of the time.
    
    # Simulate Outcomes (1 = Win, 0 = Loss)
    outcomes = np.random.binomial(1, win_prob, SIM_COUNT)
    
    # 2. Calculate PnL for each sim
    # Cost = price (cents) * contracts
    # Payout = 100 cents * contracts (if win)
    
    cost_per_contract = current_price_cents / 100.0
    payout_per_contract = 1.0
    
    # PnL Vector: (Outcome * Payout) - Cost
    # If Win: 1.0 - Cost
    # If Loss: 0.0 - Cost
    
    pnl_vector = (outcomes * payout_per_contract) - cost_per_contract
    
    # 3. Aggregation
    mean_ev = np.mean(pnl_vector)
    win_rate = np.mean(outcomes)
    roi_percent = (mean_ev / cost_per_contract) * 100
    
    # 4. VaR (Value at Risk) - 95th Percentile drawback? 
    # For binary options, VaR is just the cost if we lose. 
    # But let's look at variance of PnL.
    variance = np.var(pnl_vector)
    
    # 5. Decision Logic (The Veto)
    # Protocol: Win Rate > 58% OR ROI > 5% required
    
    status = "APPROVED"
    reason = "EV Positive"
    
    if win_rate < 0.58 and roi_percent < 10.0:
        status = "WARNING"
        reason = "Win-rate low & ROI insufficient"
        
    if mean_ev < 0:
        status = "REJECTED"
        reason = "Negative EV"

    return {
        "status": status,
        "reason": reason,
        "ev": round(mean_ev, 4),
        "roi": round(roi_percent, 2),
        "win_rate": round(win_rate, 2),
        "sim_count": SIM_COUNT,
        "variance": round(variance, 4)
    }

if __name__ == "__main__":
    try:
        # Input: JSON string from stdin or arguments
        # Args: market_title, win_prob (float), price_cents (int)
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Insufficient Arguments"}))
            sys.exit(1)
            
        title = sys.argv[1]
        prob = float(sys.argv[2])
        price = float(sys.argv[3])
        
        result = run_monte_carlo(title, prob, price)
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({"error": str(e), "status": "ERROR"}))
