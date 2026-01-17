import { SchemaType } from "@google/generative-ai";
import { DebateResponse } from "@shared/types";
import { initGenAI, queryGroq, queryGemini } from "../../services/aiService";
import { retrieveReflexiveMemory } from "../agent-10-historian";

// ------------------------------------------------------------------
// MATH: KELLY CRITERION
// ------------------------------------------------------------------
const calculateKelly = (winProb: number, marketPriceCents: number): number => {
    // WinProb (0-1), MarketPrice (1-99)
    // b (Net Odds) = (Payout - Cost) / Cost
    if (marketPriceCents <= 0 || marketPriceCents >= 100) return 0;

    const marketProb = marketPriceCents / 100;
    const netOdds = (1 - marketProb) / marketProb;

    // Full Kelly = p - (1-p)/b
    const kellyFraction = winProb - ((1 - winProb) / netOdds);

    // Safety: Fractional Kelly (1/4) and cap at 10% of bankroll per trade
    const safeKelly = kellyFraction * 0.25;

    return Math.max(0, Math.min(safeKelly, 0.10));
};

// ------------------------------------------------------------------
// DEBATE LOGIC
// ------------------------------------------------------------------

export const runCommitteeDebate = async (market: string, currentPriceCents: number): Promise<DebateResponse> => {
    const ai = initGenAI();
    if (!ai) throw new Error("Agent 4 Offline: AI Init Failed");

    console.log(`[Agent 4] Starting Committee Debate for: "${market}"`);

    // 1. REFLEXIVE MEMORY (RAG)
    const pastLessons = await retrieveReflexiveMemory(market, market);
    const contextInjection = pastLessons ? `\n\nCRITICAL PAST LESSONS (DO NOT REPEAT MISTAKES):\n${pastLessons}` : "";

    // 2. THE OPTIMIST (Gemini 1.5 Pro)
    const optimistPrompt = `You are The Optimist (Bull). 
    Argue why we should BUY "YES" on this Kalshi market: "${market}".
    Current Price: ${currentPriceCents} cents.
    Focus on positive alpha, momentum, and structural advantages.
    Keep it concise (2 sentences).${contextInjection}`;

    const optimistArg = await queryGemini(optimistPrompt);

    // 3. THE PESSIMIST (Llama 3.1 70B via Groq)
    const pessimistPrompt = `You are The Pessimist (Bear).
    Argue why we should BUY "NO" (or Sell "Yes") on this Kalshi market: "${market}".
    Current Price: ${currentPriceCents} cents.
    Focus on risks, overvaluation, and why the crowd is wrong.
    Keep it concise (2 sentences).${contextInjection}`;

    const pessimistArg = await queryGroq(pessimistPrompt, "You are a skeptical risk manager.", "llama-3.1-70b-versatile");

    // 4. THE JUDGE (Gemini 1.5 Pro - Structured Output)
    console.log(`[Agent 4] Judge is deliberating...`);

    const judgePrompt = `Act as The Judge. Weigh the arguments for market "${market}" (Price: ${currentPriceCents}¢).
    
    [OPTIMIST ARGUMENT]: ${optimistArg}
    [PESSIMIST ARGUMENT]: ${pessimistArg}
    ${contextInjection}
    
    Decide the true probability of YES winning (0-100%).
    Provide a final verdict/reasoning.`;

    const model = ai.getGenerativeModel({
        model: "gemini-1.5-pro",
        generationConfig: {
            responseMimeType: "application/json",
            responseSchema: {
                type: SchemaType.OBJECT,
                properties: {
                    optimistArg: { type: SchemaType.STRING },
                    pessimistArg: { type: SchemaType.STRING },
                    judgeVerdict: { type: SchemaType.STRING },
                    confidenceScore: { type: SchemaType.INTEGER },
                },
                required: ["optimistArg", "judgeVerdict", "confidenceScore"]
            }
        }
    });

    const result = await model.generateContent(judgePrompt);
    const discussion = JSON.parse(result.response.text());

    // 5. CALCULATE SIZE
    const winProb = discussion.confidenceScore / 100;
    const recommendedSize = calculateKelly(winProb, currentPriceCents);

    return {
        ...discussion,
        pessimistArg: pessimistArg, // Ensure Llama's output is included even if Gemini hallucinated it (override)
        recommendedSize: recommendedSize,
        market: market
    };
};
