import { CONFIG } from '../../config';

// Interface for normalized odds data
export interface ShadowOdd {
    event: string;
    bookmaker: string;
    home_prob: number;
    away_prob: number;
    timestamp: string;
}

// Helper: Transform API data to Probabilities
const normalizeOdds = (rawData: any[]): ShadowOdd[] => {
    if (!rawData) return [];

    return rawData.slice(0, 5).map(match => {
        const bookie = match.bookmakers?.[0]; // Grab first bookmaker
        const homeOdd = parseFloat(bookie?.bets?.[0]?.values?.find((v: any) => v.value === 'Home')?.odd || '2.0');
        const awayOdd = parseFloat(bookie?.bets?.[0]?.values?.find((v: any) => v.value === 'Away')?.odd || '2.0');

        return {
            event: `${match.teams.home.name} vs ${match.teams.away.name}`,
            bookmaker: bookie?.name || 'Unknown',
            home_prob: 1 / homeOdd,
            away_prob: 1 / awayOdd,
            timestamp: new Date(match.update).toISOString()
        };
    });
};

export const fetchVegasOdds = async (sport: string = 'football'): Promise<ShadowOdd[]> => {
    console.log(`[Agent 3] Intercepting odds for ${sport}...`);

    if (!CONFIG.RAPID_API_KEY) {
        throw new Error("[Agent 3] RAPID_API_KEY missing. Cannot intercept.");
    }

    try {
        const response = await fetch(`https://api-football-v1.p.rapidapi.com/v3/odds?league=39&season=2023`, {
            method: 'GET',
            headers: {
                'X-RapidAPI-Key': CONFIG.RAPID_API_KEY,
                'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
            }
        });

        if (!response.ok) throw new Error(`RapidAPI Error: ${response.status}`);
        const data = await response.json();
        return normalizeOdds(data.response);

    } catch (error: any) {
        console.warn(`[Agent 3] API Error (${error.message}). Switching to SHADOW MODE (Mock Data).`);

        // Fallback Mock Data (Shadow Mode)
        return [
            {
                event: 'Shadow Protocol: KC vs BAL',
                bookmaker: 'Vegas (Simulated)',
                home_prob: 0.55,
                away_prob: 0.45,
                timestamp: new Date().toISOString()
            },
            {
                event: 'Shadow Protocol: LAL vs BOS',
                bookmaker: 'Pinnacle (Simulated)',
                home_prob: 0.48,
                away_prob: 0.52,
                timestamp: new Date().toISOString()
            }
        ];
    }
};
