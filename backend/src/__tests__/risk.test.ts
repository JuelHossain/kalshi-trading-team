import { describe, it, expect } from 'vitest';
import { calculateRiskParams } from '../../agents/agent-8-executioner';

describe('Agent 8: Risk Engine', () => {
    it('should calculate zero wager for low win probability', () => {
        const balance = 1000;
        const winProb = 0.3; // 30% win prob
        const odds = 2.0;    // 50/50 payout

        const params = calculateRiskParams(balance, winProb, odds);
        expect(params.wager).toBe(0);
    });

    it('should apply safety factor and fractional kelly', () => {
        const balance = 1000;
        const winProb = 0.7; // 70% win prob
        const odds = 2.0;    // 50/50 payout

        // Kelly calculation: (2.0 * 0.7 - 0.3) / (2.0 - 1) = 1.1 / 1 = 1.1
        // Safety factor 0.25: 1.1 * 0.25 = 0.275
        // Capped at 5%: 0.05
        // 1000 * 0.05 = 50

        const params = calculateRiskParams(balance, winProb, odds);
        expect(params.wager).toBe(50);
    });

    it('should calculate reasonable wager for high edge', () => {
        const balance = 1000;
        const winProb = 0.6;
        const odds = 2.5; // High payout

        // Kelly: (2.5 * 0.6 - 0.4) / 1.5 = (1.5 - 0.4) / 1.5 = 0.73
        // Safety 0.25: 0.18
        // Cap 0.05: 1000 * 0.05 = 50

        const params = calculateRiskParams(balance, winProb, odds);
        expect(params.wager).toBeLessThanOrEqual(50);
        expect(params.wager).toBeGreaterThan(0);
    });
});
