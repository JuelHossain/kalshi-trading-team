# Agent 5: The Simulation Scientist (Python Core)
import sys
import json
import numpy as np

def run_monte_carlo(market_title, win_prob, current_price_cents):
    """
    Runs 10,000 simulations to calculate Expected Value (EV) and Risk.
    
    CRITICAL FIX: Uses Beta distribution to model uncertainty in analyst's probability
    estimate rather than treating it as ground truth.
    """
    SIM_COUNT = 10000
    wager = 100 # Standard unit for Sim
    
    # 1. Model Uncertainty in Analyst's Estimate
    # Use Beta distribution centered on analyst's probability
    # Alpha and Beta parameters control the variance
    # Higher values = more confidence in estimate
    
    # Conservative approach: assume moderate uncertainty
    # For 70% confidence, this gives ~±8% standard deviation
    confidence_strength = 20  # Higher = less variance
    alpha = win_prob * confidence_strength
    beta = (1 - win_prob) * confidence_strength
    
    # Generate probability samples from Beta distribution
    prob_samples = np.random.beta(alpha, beta, SIM_COUNT)
    
    # Simulate outcomes using the sampled probabilities
    outcomes = np.random.binomial(1, prob_samples)
    
    # 2. Calculate PnL for each sim
    cost_per_contract = current_price_cents / 100.0
    payout_per_contract = 1.0
    
    # PnL Vector: (Outcome * Payout) - Cost
    pnl_vector = (outcomes * payout_per_contract) - cost_per_contract
    
    # 3. Aggregation
    mean_ev = np.mean(pnl_vector)
    win_rate = np.mean(outcomes)
    roi_percent = (mean_ev / cost_per_contract) * 100 if cost_per_contract > 0 else 0
    
    # 4. Risk Metrics
    variance = np.var(pnl_vector)
    percentile_5 = np.percentile(pnl_vector, 5)  # 5th percentile (VaR)
    
    # 5. Decision Logic (The Veto) - FIXED: OR instead of AND
    # Protocol: Win Rate > 58% AND ROI > 5% required
    
    status = "APPROVED"
    reason = "EV Positive with acceptable risk"
    
    # CRITICAL FIX #8: Changed AND to OR for proper veto logic
    if win_rate < 0.58 or roi_percent < 5.0:
        status = "WARNING"
        reason = f"Win-rate ({win_rate:.1%}) or ROI ({roi_percent:.1f}%) below threshold"
        
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
        "variance": round(variance, 4),
        "var_5pct": round(percentile_5, 4)
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
