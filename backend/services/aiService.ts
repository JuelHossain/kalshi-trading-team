import { GoogleGenerativeAI } from "@google/generative-ai";
import { CONFIG } from '../config';

// ---------------------------------------------------------
// KEY ROTATION & RATE LIMIT MANAGER
// ---------------------------------------------------------

class KeyManager {
    private keys: string[];
    private currentIndex: number = 0;
    private name: string;

    constructor(name: string, keyString: string) {
        this.name = name;
        this.keys = keyString ? keyString.split(',').map(k => k.trim()).filter(k => k.length > 0) : [];
        if (this.keys.length === 0) console.warn(`[${name}] No API Keys found.`);
    }

    public getNextKey(): string {
        if (this.keys.length === 0) throw new Error(`[${this.name}] No keys available.`);
        const key = this.keys[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.keys.length;
        return key;
    }
}

const groqKeys = new KeyManager('Groq', CONFIG.GROQ_API_KEY);
const geminiKeys = new KeyManager('Gemini', CONFIG.GEMINI_API_KEY);
const rapidKeys = new KeyManager('RapidAPI', CONFIG.RAPID_API_KEY);

// ---------------------------------------------------------
// GEMINI CLIENT (SDK)
// ---------------------------------------------------------

export const initGenAI = (): GoogleGenerativeAI | null => {
    try {
        const key = geminiKeys.getNextKey();
        return new GoogleGenerativeAI(key);
    } catch (e) {
        console.error("Failed to init GenAI:", e);
        return null;
    }
};

export const queryGemini = async (prompt: string) => {
    const ai = initGenAI();
    if (!ai) throw new Error("Gemini AI not initialized");

    try {
        const model = ai.getGenerativeModel({ model: "gemini-1.5-pro" });
        const result = await model.generateContent(prompt);
        return result.response.text();
    } catch (e: any) {
        console.error("[Gemini] Request Failed:", e.message);
        throw e;
    }
};

export const generateEmbedding = async (text: string): Promise<number[]> => {
    const ai = initGenAI();
    if (!ai) return [];

    try {
        const model = ai.getGenerativeModel({ model: "text-embedding-004" });
        const result = await model.embedContent(text);
        // GoogleGenerativeAI embedding response structure:
        return result.embedding.values || [];
    } catch (e: any) {
        console.error("[Gemini] Embedding Failed:", e.message);
        return [];
    }
};

// ---------------------------------------------------------
// GROQ CLIENT (OPENAI COMPATIBLE)
// ---------------------------------------------------------

export const queryGroq = async (prompt: string, systemPrompt: string = "You are a helpful assistant.", model: string = "llama-3.1-70b-versatile") => {
    const key = groqKeys.getNextKey();

    try {
        const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${key}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                messages: [
                    { role: "system", content: systemPrompt },
                    { role: "user", content: prompt }
                ],
                model: model,
                temperature: 0.1, // Precision mode
                max_tokens: 1024
            })
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(`Groq API Error ${response.status}: ${err}`);
        }

        const data = await response.json();
        return data.choices[0]?.message?.content || "";
    } catch (e: any) {
        console.error("[Groq] Request Failed:", e.message);
        throw e;
    }
}

// ---------------------------------------------------------
// RAPIDAPI CLIENT
// ---------------------------------------------------------

export const fetchRapidData = async (endpoint: string, host: string, params: Record<string, string> = {}) => {
    const key = rapidKeys.getNextKey();
    const queryString = new URLSearchParams(params).toString();
    const url = `https://${host}${endpoint}${queryString ? '?' + queryString : ''}`;

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-RapidAPI-Key': key,
                'X-RapidAPI-Host': host
            }
        });

        if (!response.ok) {
            throw new Error(`RapidAPI Error ${response.status}`);
        }

        return await response.json();
    } catch (e: any) {
        console.error(`[RapidAPI] Failed (${host}):`, e.message);
        throw e;
    }
}

// ---------------------------------------------------------
// UNIFIED AI GATEWAY (Round-Robin / Failover)
// ---------------------------------------------------------

export const fastClassify = async (text: string, categories: string[]) => {
    // Priority: Groq (Speed) -> Gemini (Fallback)
    const prompt = `Classify the following text into one of these categories: ${categories.join(', ')}. Return ONLY the category name. Text: "${text}"`;

    try {
        return await queryGroq(prompt, "You are a fast classification engine.");
    } catch (e) {
        console.warn("[AI] Groq failed, failing over to Gemini...");
        return await queryGemini(prompt);
    }
}
