import { GoogleGenAI, Type } from "@google/genai";
import { DebateResponse } from "../../types";

const initGenAI = () => {
    const apiKey = process.env.API_KEY; // Using properly exposed env var via vite define or process.env shim
    if (!apiKey) return null;
    return new GoogleGenAI({ apiKey });
};

export const runCommitteeDebate = async (market: string): Promise<DebateResponse> => {
    const ai = initGenAI();

    if (!ai) {
        throw new Error("System: API_KEY missing. Agent 4 Offline.");
    }

    try {
        const response = await ai.models.generateContent({
            model: "gemini-3-flash-preview",
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
        console.error("Gemini API Failed.", error);
        throw error;
    }
};
