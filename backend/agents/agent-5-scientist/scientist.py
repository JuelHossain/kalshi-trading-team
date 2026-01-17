import numpy as np
import sys
import json
import multiprocessing
from typing import Dict, Any

def run_simulation(base_prob: float, std_dev: float, iterations: int) -> float:
    """
    Runs a Monte Carlo simulation for a given base probability and standard deviation.
    Using numpy for high performance.
    """
    # Generate random drifts based on historical standard deviation
    # We use a normal distribution for the drift
    drifts = np.random.normal(0, std_dev, iterations)
    
    # Apply drifts to base probability and clip to [0, 1]
    simulated_probs = np.clip(base_prob + drifts, 0, 1)
    
    # Determine wins: each simulation is a Bernoulli trial with the simulated probability
    random_samples = np.random.random(iterations)
    wins = np.sum(random_samples < simulated_probs)
    
    return float(wins / iterations)

def calculate_ev(win_rate: float, price_cents: float) -> float:
    """
    Calculates Expected Value (EV) per dollar wagered.
    Kalshi payout is $1 if win, $0 if lose.
    Cost is price_cents / 100.
    Profit if win: (100 - price_cents) / 100
    Loss if lose: price_cents / 100
    EV = (win_rate * Profit) - ((1 - win_rate) * Loss)
    """
    profit = (100 - price_cents) / 100
    loss = price_cents / 100
    ev = (win_rate * profit) - ((1 - win_rate) * loss)
    return float(ev)

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        base_prob = input_data.get('base_prob', 0.5)
        # Default historical std_dev if not provided (e.g., 0.05 or 5%)
        std_dev = input_data.get('std_dev', 0.05)
        iterations = input_data.get('iterations', 10000)
        price_cents = input_data.get('price_cents', 50) # Default mid-price
        
        # Cloud Strategy: Multi-processed loop (local implementation)
        # For 10k iterations, numpy is fast enough on a single core, 
        # but the prompt asks for multi-processed logic.
        # We can split the 10k iterations into smaller chunks across CPUs.
        
        num_cpus = multiprocessing.cpu_count()
        if num_cpus < 1: num_cpus = 1
        iters_per_cpu = iterations // num_cpus
        
        with multiprocessing.Pool(processes=num_cpus) as pool:
            # Run simulation chunks in parallel
            results = pool.starmap(run_simulation, [(base_prob, std_dev, iters_per_cpu)] * num_cpus)
            
        # Average the win rates from all processes
        sim_win_rate = sum(results) / len(results)
        
        # EV Calculation
        ev_score = calculate_ev(sim_win_rate, price_cents)
        
        # Variance Report (Standard Deviation of the mean)
        # Using the standard formula for Bernoulli variance
        variance = (sim_win_rate * (1 - sim_win_rate)) / iterations
        
        # Veto Trigger: If win-rate < 58%, return 'WARNING'
        status = 'SUCCESS'
        if sim_win_rate < 0.58:
            status = 'WARNING'
            
        output = {
            "status": status,
            "win_rate": sim_win_rate,
            "ev_score": ev_score,
            "variance_report": {
                "variance": variance,
                "std_dev": float(np.sqrt(variance)),
                "confidence_interval": [float(sim_win_rate - 1.96 * np.sqrt(variance)), float(sim_win_rate + 1.96 * np.sqrt(variance))]
            },
            "iterations": iterations
        }
        
        print(json.dumps(output))
        
    except Exception as e:
        print(json.dumps({"error": str(e), "status": "ERROR"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
