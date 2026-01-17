import { GoogleGenAI } from "@google/genai";
import { CONFIG } from '../../config';

const initGenAI = () => {
    const apiKey = CONFIG.GEMINI_API_KEY || process.env.API_KEY;
    if (!apiKey) return null;
    return new GoogleGenAI({ apiKey });
};

export const auditDecision = async (marketTitle: string, analystVerdict: string): Promise<{ approved: boolean; reason: string }> => {
    // Agent 6: The Auditor (Cynical Reviewer)
    const ai = initGenAI();
    if (!ai) return { approved: true, reason: "Auditor Offline - Bypassing" };

    try {
        const response = await ai.models.generateContent({
            model: "gemini-3-flash-preview",
            contents: `Role: Financial Auditor.
            Task: Review a trade decision for hallucination or extreme bias.
            
            Market: "${marketTitle}"
            Analyst Verdict: "${analystVerdict}"
            
            If the verdict seems rational (even if risky), APPROVE.
            If the verdict ignores obvious reality (e.g., "The sun will not set today"), REJECT.
            
            Output JSON: { "approved": boolean, "reason": string }`,
            config: { responseMimeType: "application/json" }
        });

        const text = response.text || "{}";
        return JSON.parse(text);
    } catch (e) {
        console.error("[Agent 6] Audit Failed", e);
        return { approved: true, reason: "Audit Error - Fail Open" };
    }
}
