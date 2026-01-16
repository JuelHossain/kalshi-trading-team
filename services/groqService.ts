import { CONFIG } from '../config';

export const scanMarketsWithGroq = async (): Promise<string> => {
  try {
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${CONFIG.GROQ_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: [{
          role: 'user',
          content: 'Scan the current prediction market landscape for high-volatility events. Return 3 concise potential market names (e.g. "Fed Rate Cut", "GDP Growth", "Oil Price"). Return ONLY the names separated by commas.'
        }],
        model: 'llama3-70b-8192',
        temperature: 0.5,
        max_tokens: 50
      })
    });

    if (!response.ok) throw new Error(`Groq API Error: ${response.status}`);
    
    const data = await response.json();
    return data.choices[0]?.message?.content || "Fed Interest Rate, Nvidia Earnings, Bitcoin Spot ETF";
  } catch (error) {
    console.error("Agent 2 (Groq) Failed:", error);
    // Fallback if API fails
    return "US Inflation CPI, Senate Control 2024, SpaceX Launch";
  }
};
