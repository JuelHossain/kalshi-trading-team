import { spawn } from 'child_process';
import path from 'path';

export interface SimResults {
    ev: number;
    variance: number;
    status: string;
    report: any;
}

export const runMonteCarloSim = async (
    marketTitle: string,
    baseProb: number,
    priceCents: number = 50,
    stdDev: number = 0.05
): Promise<SimResults> => {
    // Agent 5: Sim Scientist
    console.log(`[Agent 5] Running Multi-Processed Monte Carlo for "${marketTitle}"...`);

    return new Promise((resolve, reject) => {
        // Calling run_sim.py with arguments: title, probability, price
        const pythonProcess = spawn('python3', [
            path.join(__dirname, 'run_sim.py'),
            marketTitle,
            baseProb.toString(),
            priceCents.toString()
        ]);

        let outputData = '';
        let errorData = '';

        pythonProcess.stdout.on('data', (data) => {
            outputData += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorData += data.toString();
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                console.error(`[Agent 5] Python Process Error: ${errorData}`);
                // Fallback to basic calculation if python fails
                const simWinRate = baseProb; // Assume Analyst is right
                // EV = (WinProb * Profit) - (LossProb * Loss)
                // Profit = 100 - Cost. Loss = Cost.
                const profit = 100 - priceCents;
                const loss = priceCents;

                // EV in cents
                const evCents = (simWinRate * profit) - ((1 - simWinRate) * loss);
                // Convert to decimal (per dollar staked)
                const ev = evCents / 100.0; // Rough approx to match Sim scale which was per contract

                resolve({
                    ev,
                    variance: 0.25, // Max variance for binary
                    status: 'WARNING',
                    report: { error: 'Python process failed, using fallback.', rawError: errorData }
                });
                return;
            }

            try {
                const results = JSON.parse(outputData);
                if (results.error) {
                    throw new Error(results.error);
                }

                console.log(`[Agent 5] Sim Results: Win% ${(results.win_rate * 100).toFixed(1)}%, EV: ${results.ev}, Status: ${results.status}`);

                resolve({
                    ev: results.ev,
                    variance: results.variance,
                    status: results.status,
                    report: results
                });
            } catch (err) {
                console.error("[Agent 5] JSON Parse Failed:", outputData);
                resolve({
                    ev: 0,
                    variance: 0,
                    status: 'ERROR',
                    report: { error: 'Invalid JSON from Sim', raw: outputData }
                });
            }
        });
    });
};

