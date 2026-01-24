import { ErrorAnalysis } from '@shared/types';
import { queryGemini } from '../../services/aiService';

export const analyzeSystemError = async (
  errorMessage: string,
  context: string
): Promise<ErrorAnalysis> => {
  // Agent 13: The Fixer

  try {
    const prompt = `You are a Senior DevOps Engineer and Systems Architect. 
        A mission-critical high-frequency trading bot encountered the following error.

        Error Message: "${errorMessage}"
        Context: "${context}"
        
        Task:
        1. Analyze the root cause deeply. Use the context provided.
        2. Provide a specific, actionable "Code Hotfix" or CLI command.
        3. Estimate confidence score (0-100).
        
        Return STRICTLY valid JSON with no markdown formatting.
        Format:
        {
            "rootCause": "string",
            "suggestedFix": "string",
            "confidence": integer
        }`;

    const text = await queryGemini(prompt);

    // Clean up markdown if present
    const jsonStr = text
      .replace(/```json/g, '')
      .replace(/```/g, '')
      .trim();
    return JSON.parse(jsonStr) as ErrorAnalysis;
  } catch (e: any) {
    console.error('Debugger Failed:', e);
    return {
      rootCause: `AI Debugger Failed: ${e.message}`,
      suggestedFix: 'Check Gemini API Key & Permissions.',
      confidence: 0,
    };
  }
};
