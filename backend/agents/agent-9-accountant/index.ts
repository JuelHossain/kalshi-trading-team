import { kalshiFetch } from '../../services/kalshiService';

export const fetchPortfolioBalance = async (isPaperTrading: boolean) => {
    // Agent 9: The Accountant
    try {
        const data = await kalshiFetch('/portfolio/balance', 'GET', undefined, isPaperTrading);
        // Kalshi V2 returns balance in cents usually, need to check specific V2 response
        // Assuming response has 'balance' field. 
        // Real V2 response for /portfolio/balance is { balance: number } (in cents)
        const balanceCents = data.balance || 0;

        console.log(`[Agent 9] Audited Balance: $${(balanceCents / 100).toFixed(2)}`);
        return balanceCents / 100;
    } catch (e) {
        console.error("[Agent 9] Balance Check Failed", e);
        return 0;
    }
};
