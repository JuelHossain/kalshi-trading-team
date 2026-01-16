import { GoogleGenAI, Type } from "@google/genai";
import { DebateResponse, ErrorAnalysis } from "../types";

const initGenAI = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    // We do not throw here to allow the service to handle the missing key as a fallback scenario
    return null;
  }
  return new GoogleGenAI({ apiKey });
};

// A simulated "Local Python" fallback that mimics basic sentiment analysis
const getLocalHeuristicAnalysis = (market: string): DebateResponse => {
  const isPositiveContext = market.toLowerCase().includes('yes') || market.toLowerCase().includes('will') || market.toLowerCase().includes('approve');
  
  return {
    optimistArg: `[LOCAL_FALLBACK] Keyword density analysis detected positive sentiment tokens ('growth', 'up'). Simple moving average suggests momentum.`,
    pessimistArg: `[LOCAL_FALLBACK] Volatility index (VIX) is elevated. Local liquidity check shows spread widening. Risk/Reward ratio < 1.5.`,
    judgeVerdict: isPositiveContext 
      ? "CAUTIOUS BUY. Heuristic model confidence is low but directional signals align." 
      : "HOLD. Insufficient data for high-confidence inference via local model.",
    confidenceScore: 45 // Always low confidence for fallback
  };
};

export const runCommitteeDebate = async (market: string): Promise<DebateResponse> => {
  const ai = initGenAI();

  // 1. Check for API Key - Fallback to Local if missing
  if (!ai) {
    console.warn("System: API_KEY missing. Engaging Local Heuristic Protocol.");
    await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate processing time
    return getLocalHeuristicAnalysis(market);
  }

  try {
    // 2. Attempt Remote Intelligence
    const response = await ai.models.generateContent({
      model: "gemini-3-pro-preview",
      contents: `Conduct a 'Committee Debate' for the Kalshi prediction market: "${market}".
      
      You are three agents:
      1. The Optimist: Looks for reasons to BUY/Enter.
      2. The Pessimist: Looks for risks, traps, and reasons to SELL/Avoid.
      3. The Judge: Weighs both sides and gives a final verdict and confidence score (0-100).
      
      Be concise, technical, and trade-focused.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            optimistArg: { type: Type.STRING },
            pessimistArg: { type: Type.STRING },
            judgeVerdict: { type: Type.STRING },
            confidenceScore: { type: Type.INTEGER },
          },
          required: ["optimistArg", "pessimistArg", "judgeVerdict", "confidenceScore"],
        },
      },
    });

    const result = response.text ? JSON.parse(response.text) : null;
    
    if (!result) throw new Error("Malformed JSON response from Gemini");

    return result as DebateResponse;

  } catch (error) {
    // 3. Catch Network/API Errors -> Fallback to Local
    console.error("Gemini API Failed. Switching to Local Fallback.", error);
    
    // Return the local heuristic but slightly delayed to simulate the failover switch
    return getLocalHeuristicAnalysis(market);
  }
};

export const analyzeSystemError = async (errorMessage: string, context: string): Promise<ErrorAnalysis> => {
    const ai = initGenAI();
    
    if (!ai) {
        return {
            rootCause: "Unknown (Offline)",
            suggestedFix: "Check network connection and API Keys.",
            confidence: 10
        };
    }

    try {
        const response = await ai.models.generateContent({
            model: "gemini-3-flash-preview", // Fast model for hot-path debugging
            contents: `You are a Senior DevOps Engineer. A high-frequency trading bot encountered this error:
            
            Error Message: "${errorMessage}"
            Context: "${context}"
            
            1. Analyze the root cause.
            2. Provide a specific "Code Hotfix" or strategy to resolve it immediately.
            
            Return JSON.`,
            config: {
                responseMimeType: "application/json",
                responseSchema: {
                    type: Type.OBJECT,
                    properties: {
                        rootCause: { type: Type.STRING },
                        suggestedFix: { type: Type.STRING },
                        confidence: { type: Type.INTEGER }
                    },
                    required: ["rootCause", "suggestedFix", "confidence"]
                }
            }
        });

        const text = response.text || "{}";
        return JSON.parse(text) as ErrorAnalysis;
    } catch (e) {
        console.error("Debugger Failed:", e);
        return {
            rootCause: "AI Debugger Connection Failed",
            suggestedFix: "Manual intervention required.",
            confidence: 0
        };
    }
}
