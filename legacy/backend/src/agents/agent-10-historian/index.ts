import { logToDb, supabase } from '../../services/dbService';
import { generateEmbedding } from '../../services/aiService';

export const logTradeToHistory = async (
  agentId: number,
  ticker: string,
  action: 'BUY' | 'SELL' | 'HOLD',
  price: number,
  quantity: number,
  details: any
) => {
  await logToDb('trade_history', {
    agent_id: agentId,
    market_ticker: ticker,
    action,
    price_cents: price,
    quantity,
    status: details.status || 'PENDING',
    details: details,
  });
};

export const logTradeError = async (
  ticker: string,
  errorType: string,
  description: string,
  correctionPlan: string
) => {
  console.log(`[Agent 10] Logging Error: ${errorType} on ${ticker}`);

  // Generate Embedding for semantic search
  const embedding = await generateEmbedding(`${ticker} ${errorType} ${description}`);

  await logToDb('trade_errors', {
    market_ticker: ticker,
    error_type: errorType,
    description,
    correction_plan: correctionPlan,
    embedding: embedding.length > 0 ? embedding : null,
  });
};

export const retrieveReflexiveMemory = async (
  ticker: string,
  currentContext: string
): Promise<string> => {
  if (!supabase) return '';

  console.log(`[Agent 10] Scanning Reflexive Memory for ${ticker}...`);

  const embedding = await generateEmbedding(`${ticker} ${currentContext}`);
  if (embedding.length === 0) return '';

  const { data: errors, error } = await supabase.rpc('match_trade_errors', {
    query_embedding: embedding,
    match_threshold: 0.7, // Only relevant matches
    match_count: 3,
  });

  if (error) {
    console.error('[Agent 10] RAG Failed:', error);
    return '';
  }

  if (!errors || errors.length === 0) return 'No significant past errors found.';

  return errors
    .map(
      (e: any) =>
        `- PAST MISTAKE: ${e.description}. LESSON: ${e.correction_plan} (Sim: ${(e.similarity * 100).toFixed(0)}%)`
    )
    .join('\n');
};
