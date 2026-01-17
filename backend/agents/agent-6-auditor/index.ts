import { queryGroq } from "../../services/aiService";

export const auditDecision = async (
    marketTitle: string,
    analystVerdict: string,
    analystConfidence: number
): Promise<{ approved: boolean; reason: string; auditorConfidence: number }> => {
    // Agent 6: The Auditor
    // PROTOCOL: The Committee Veto (Requires 85% Consensus)

    try {
        const systemPrompt = "You are the Pessimist Auditor. Your job is to find reasons why a trade will FAIL. Be cynical and paranoid. Return STRICTLY valid JSON.";
        const userPrompt = `Review this trade:
        Market: "${marketTitle}"
        Analyst Verdict: "${analystVerdict}"

        Give me a confidence score (0-100) on success.
        Output strictly JSON: { "approved": boolean, "reason": string, "auditorConfidence": number }`;

        const responseText = await queryGroq(userPrompt, systemPrompt);

        // Clean up markdown if present
        const jsonStr = responseText.replace(/```json/g, '').replace(/```/g, '').trim();
        const result = JSON.parse(jsonStr);

        // Calculate Consensus
        const averageConfidence = (analystConfidence + result.auditorConfidence) / 2;
        const consensusReached = averageConfidence >= 85;

        if (!consensusReached) {
            return {
                approved: false,
                reason: `COMMITTEE VETO: Consensus (${averageConfidence.toFixed(1)}%) < 85%. ${result.reason}`,
                auditorConfidence: result.auditorConfidence
            };
        }

        return { ...result, approved: true };
    } catch (e: any) {
        console.error("[Agent 6] Audit Failed:", e.message);
        return { approved: false, reason: `Audit Error: ${e.message} - Fail Closed`, auditorConfidence: 0 };
    }
}
