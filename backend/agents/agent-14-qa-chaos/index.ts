import { CONFIG } from "../../config";
import { kalshiFetch } from "../../services/kalshiService";
import * as fs from 'fs';
import * as path from 'path';
import { CHAOS_STATE } from './state';

// Agent 14: QA & Chaos Tester
// Mission: Protect the Capital ($300)
// Specialty: Stress Testing, Edge-Case Auditing, Security Fail-safes

let baselineCapital = 0;
let sentinelActive = false;
const MAX_DRAWDOWN_PERCENT = 0.15; // 15%
const MAX_DRAWDOWN_USD = 45; // $45

/**
 * SENTINEL: Independent monitor that kills all processes if loss limit exceeded.
 * @param isPaperTrading 
 */
export const startSentinel = async (isPaperTrading: boolean) => {
    if (sentinelActive) return;
    sentinelActive = true;

    try {
        console.log("[Agent 14] Sentinel: Initializing baseline capital...");
        const response = await kalshiFetch('/portfolio/balance', 'GET', undefined, isPaperTrading);
        baselineCapital = response.balance;

        console.log(`[Agent 14] Sentinel: Locked Baseline at $${(baselineCapital / 100).toFixed(2)}`);

        // Start polling
        setInterval(async () => {
            await checkPnL(isPaperTrading);
        }, 5000); // Check every 5 seconds

    } catch (e) {
        console.error("[Agent 14] Sentinel Failed to Start!", e);
        // Sentinel failure is a critical failure of the safety system
        process.exit(1);
    }
};

const checkPnL = async (isPaperTrading: boolean) => {
    try {
        const response = await kalshiFetch('/portfolio/balance', 'GET', undefined, isPaperTrading);
        const currentBalance = response.balance;
        const loss = baselineCapital - currentBalance;

        // Calculate percentage loss
        const lossPercent = loss / baselineCapital;
        const lossAmountUsd = loss / 100;

        if (lossPercent >= MAX_DRAWDOWN_PERCENT || lossAmountUsd >= MAX_DRAWDOWN_USD) {
            console.error(`\n[Agent 14] SENTINEL TRIGGERED! LOSS DETECTED: $${lossAmountUsd.toFixed(2)} (${(lossPercent * 100).toFixed(1)}%)`);
            console.error("[Agent 14] INITIATING RAGNAROK EMERGENCY CANCEL...");

            try {
                const { executeEmergencyProtocol } = await import('../agent-12-ragnarok/index');
                await executeEmergencyProtocol(isPaperTrading);
            } catch (ragnarokError) {
                console.error("[Agent 14] RAGNAROK FAILED DURING SENTINEL TRIGGER!", ragnarokError);
            }

            console.error("[Agent 14] KILLING ALL PROCESSES TO PROTECT CAPITAL.");
            process.exit(1);
        }
    } catch (e) {
        console.error("[Agent 14] Sentinel Connection Lost during PnL check.", e);
    }
};

/**
 * CHAOS: Methods to inject failures
 */
export const injectChaos = (scenario: '500_ERROR' | 'STALE_DATA' | 'TIMEOUT_20S') => {
    console.warn(`[Agent 14] INJECTING CHAOS SCENARIO: ${scenario}`);
    switch (scenario) {
        case '500_ERROR':
            CHAOS_STATE.SIMULATE_500 = true;
            break;
        case 'STALE_DATA':
            CHAOS_STATE.SIMULATE_STALE = true;
            break;
        case 'TIMEOUT_20S':
            CHAOS_STATE.SIMULATE_TIMEOUT = true;
            break;
    }
};

export const resetChaos = () => {
    CHAOS_STATE.SIMULATE_500 = false;
    CHAOS_STATE.SIMULATE_STALE = false;
    CHAOS_STATE.SIMULATE_TIMEOUT = false;
    console.log("[Agent 14] Chaos State Reset.");
};

/**
 * SAFETY: Checks if market data is stale.
 * @param lastUpdated ISO timestamp or epoch
 * @param maxAgeMinutes defaults to 5 minutes
 */
export const validateStaleData = (lastUpdated: string | number, maxAgeMinutes: number = 5) => {
    const timestamp = typeof lastUpdated === 'string' ? new Date(lastUpdated).getTime() : lastUpdated;
    const now = Date.now();
    const ageMs = now - timestamp;
    const maxAgeMs = maxAgeMinutes * 60 * 1000;

    if (ageMs > maxAgeMs) {
        throw new Error(`[Agent 14] STALE DATA VETO: Market data is ${(ageMs / 1000 / 60).toFixed(1)} minutes old (Max: ${maxAgeMinutes}m).`);
    }

    // Simulate Chaos 
    if (CHAOS_STATE.SIMULATE_STALE) {
        throw new Error("[Agent 14] CHAOS: Simulating Stale Data Veto.");
    }

    return true;
};

/**
 * SAFETY: Validates Executioner Logic
 */
export const validateExecutionerSafety = (isPaperInput: boolean, intendedEnv: 'DEMO' | 'PROD') => {
    // "Validate that the 'Executioner' module never places an order in 'Prod' while the toggle is set to 'Demo'."

    if (intendedEnv === 'DEMO' && !isPaperInput) {
        throw new Error("[Agent 14] CRITICAL SAFETY VIOLATION: Executioner attempting PROD trade in DEMO mode.");
    }

    if (!isPaperInput && intendedEnv !== 'PROD') {
        throw new Error("[Agent 14] CRITICAL SAFETY VIOLATION: Mismatch between env and isPaperTrading flag.");
    }

    return true;
};

import { fileURLToPath } from 'url';

/**
 * AUDIT: Scans code for loops and potential leaks
 */
export const auditCodebase = () => {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const rootDir = path.resolve(__dirname, '../../'); // backend root
    const agentsDir = path.join(rootDir, 'agents');
    const pyAgentsDir = path.resolve(rootDir, '../engine/agents');

    console.log("[Agent 14] Starting Cross-Platform Static Analysis Audit...");

    const getAllFiles = (dir: string): string[] => {
        let results: string[] = [];
        try {
            const list = fs.readdirSync(dir);
            list.forEach((file) => {
                file = path.join(dir, file);
                const stat = fs.statSync(file);
                if (stat && stat.isDirectory()) {
                    results = results.concat(getAllFiles(file));
                } else {
                    results.push(file);
                }
            });
        } catch (e) {
            console.warn(`[Agent 14] Could not read dir ${dir}`);
        }
        return results;
    };

    const files = [...getAllFiles(agentsDir), ...getAllFiles(pyAgentsDir)];
    let violations = 0;

    files.forEach(file => {
        if (!file.endsWith('.ts') && !file.endsWith('.py')) return;
        const content = fs.readFileSync(file, 'utf-8');

        // Check for infinite loops (basic check)
        if (content.match(/while\s*\(\s*true\s*\)/) && !content.includes('break')) {
            console.warn(`[Agent 14] AUDIT WARNING: Potential infinite loop in ${path.basename(file)}`);
            violations++;
        }

        // Check for risky interval usage
        if (content.includes('setInterval') && content.includes('.push(') && !content.includes('.shift(') && !content.includes('.pop(')) {
            console.warn(`[Agent 14] AUDIT WARNING: Potential unbounded array growth in ${path.basename(file)}`);
            violations++;
        }
    });

    if (violations === 0) {
        console.log("[Agent 14] Audit Passed. No obvious logic loops detected.");
        return true;
    } else {
        console.warn(`[Agent 14] Audit Completed with ${violations} warnings.`);
        return false;
    }
};
