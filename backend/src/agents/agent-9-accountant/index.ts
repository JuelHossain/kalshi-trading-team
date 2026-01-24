import { kalshiService } from '../../services/kalshiService';
import { supabase } from '../../services/dbService';
import { getDailySpend } from '../../services/costTracker';

const PRINCIPAL_CAPITAL = 30000; // $300.00 in cents
const PROFIT_THRESHOLD = 5000; // $50.00 in cents
const BUDGET_CEILING = 1.15; // $1.15 in dollars

export const fetchPortfolioBalance = async (isPaperTrading: boolean) => {
  // Agent 9: The Accountant
  try {
    const data = await kalshiService.fetch('/portfolio/balance', 'GET', undefined, isPaperTrading);
    const balanceCents = data.balance || 0;

    // Check Daily Profit (Reflexive Memory via Supabase)
    const { data: history } = (await supabase
      ?.from('balance_history')
      .select('balance_cents')
      .gte('created_at', new Date().toISOString().split('T')[0])
      .order('created_at', { ascending: true })
      .limit(1)) || { data: null };

    const startOfDayBalance = history?.[0]?.balance_cents || balanceCents;
    const dailyProfit = balanceCents - startOfDayBalance;

    // Check API Spend
    const totalSpend = await getDailySpend();
    if (totalSpend > BUDGET_CEILING) {
      console.error(
        `[Agent 9] BUDGET CEILING BREACHED: $${totalSpend.toFixed(2)}. Freezing execution.`
      );
      return 0; // Returning 0 bankroll to halt trades
    }

    let availableCents = balanceCents;

    // PROTOCOL: The Recursive Vault
    // Once daily profit hits $50.00, we freeze the $300 principal.
    if (dailyProfit >= PROFIT_THRESHOLD) {
      console.log(
        `[Agent 9] RECURSIVE VAULT ACTIVE: Profit ($${(dailyProfit / 100).toFixed(2)}) > $50. House Money only.`
      );
      availableCents = balanceCents - PRINCIPAL_CAPITAL;
    }

    // PROTOCOL: Budget Ceiling
    // TODO: Implement actual cost tracking for API/Cloud spend
    // For now, we audit the limit.
    console.log(
      `[Agent 9] Auditor Report: Balance: $${(balanceCents / 100).toFixed(2)} | Spend: $${totalSpend.toFixed(4)} | Avail: $${(availableCents / 100).toFixed(2)}`
    );

    return availableCents / 100;
  } catch (e) {
    console.error('[Agent 9] Balance Audit Failed', e);
    return 0;
  }
};

export const auditApiSpend = async (cost: number) => {
  // Agent 9 Audit: Ensure we stay under $1.15/day
  // In a real scenario, this would persist to DB and check daily sum.
  if (cost > BUDGET_CEILING) {
    console.error(`[Agent 9] CRITICAL: API Spend Protocol Violated ($${cost})`);
    return false;
  }
  return true;
};
