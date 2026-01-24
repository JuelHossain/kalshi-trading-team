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

  return rawData.slice(0, 5).map((match) => {
    const bookie = match.bookmakers?.[0]; // Grab first bookmaker
    const homeOdd = parseFloat(
      bookie?.bets?.[0]?.values?.find((v: any) => v.value === 'Home')?.odd || '2.0'
    );
    const awayOdd = parseFloat(
      bookie?.bets?.[0]?.values?.find((v: any) => v.value === 'Away')?.odd || '2.0'
    );

    return {
      event: `${match.teams.home.name} vs ${match.teams.away.name}`,
      bookmaker: bookie?.name || 'Unknown',
      home_prob: 1 / homeOdd,
      away_prob: 1 / awayOdd,
      timestamp: new Date(match.update).toISOString(),
    };
  });
};

import { fetchRapidData } from '../../services/aiService';

// ... (Interface and normalizeOdds helper remain the same, or are re-included)
// Actually I need to re-declare imports and interfaces if I replace the whole block or manage chunks carefully.
// I will replace fetchVegasOdds implementation.

export const fetchVegasOdds = async (
  sport: string = 'american-football_nfl'
): Promise<ShadowOdd[]> => {
  console.log(`[Agent 3] Intercepting odds for ${sport}...`);

  try {
    // Using 'The Lines' API or 'API-Sports' via our generalized service
    // For NFL: league=1 (example)
    const host = 'v1.american-football.api-sports.io';
    const endpoint = '/odds';
    // Note: Real IDs would be needed. Using a generic 'live' or 'next' call if possible.
    // Or strictly mapping sports.

    const data = await fetchRapidData(endpoint, host, { league: '1', season: '2023' });
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
        timestamp: new Date().toISOString(),
      },
      {
        event: 'Shadow Protocol: LAL vs BOS',
        bookmaker: 'Pinnacle (Simulated)',
        home_prob: 0.48,
        away_prob: 0.52,
        timestamp: new Date().toISOString(),
      },
    ];
  }
};
