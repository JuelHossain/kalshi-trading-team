import { GoogleGenAI, Type } from "@google/genai";
import { ErrorAnalysis } from "../../types";

import { CONFIG } from "../../config";

const initGenAI = () => {
    const apiKey = CONFIG.GEMINI_API_KEY || process.env.API_KEY;
    if (!apiKey) {
        console.error("Agent 13: Missing GEMINI_API_KEY");
        return null;
    }
    return new GoogleGenAI({ apiKey });
};

export const analyzeSystemError = async (errorMessage: string, context: string): Promise<ErrorAnalysis> => {
    // Agent 13: The Fixer
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
            model: "gemini-3-flash-preview",
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
    } catch (e: any) {
        console.error("Debugger Failed:", e);
        return {
            rootCause: `AI Debugger Failed: ${e.message}`,
            suggestedFix: "Check Gemini API Key & Permissions.",
            confidence: 0
        };
    }
}
