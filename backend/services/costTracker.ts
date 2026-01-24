import { supabase } from './dbService';

export const trackApiCost = async (service: string, model: string, cost: number) => {
  console.log(`[Cost Tracker] ${service} (${model}): $${cost.toFixed(4)}`);

  if (supabase) {
    await supabase.from('api_spend').insert([
      {
        service,
        model,
        cost,
        created_at: new Date().toISOString(),
      },
    ]);
  }
};

export const getDailySpend = async (): Promise<number> => {
  if (!supabase) return 0;

  const today = new Date().toISOString().split('T')[0];
  const { data } = await supabase.from('api_spend').select('cost').gte('created_at', today);

  return (data || []).reduce((sum, item) => sum + item.cost, 0);
};
