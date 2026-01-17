import { injectChaos, resetChaos } from '../agents/agent-14-qa-chaos/index';
import { fetchScoutedMarkets, kalshiFetch } from '../services/kalshiService';

const runDrill = async () => {
    console.log("=== AGENT 14: CHAOS DRILL ===");

    // Scenario 1: 500 Error
    console.log("\n[Drill 1] Simulating 500 Error...");
    injectChaos('500_ERROR');
    try {
        await kalshiFetch('/markets', 'GET', undefined, true);
        console.error("FAIL: Market fetch succeeded despite 500 Error flag.");
    } catch (e: any) {
        if (e.message.includes('CHAOS_INJECTED_500')) {
            console.log("PASS: Caught Simulated 500 Error safely.");
        } else {
            console.error("FAIL: Caught unexpected error:", e);
        }
    }
    resetChaos();

    // Scenario 2: Timeout
    console.log("\n[Drill 2] Simulating Timeout (20s)...");
    injectChaos('TIMEOUT_20S');
    const start = Date.now();
    try {
        await kalshiFetch('/markets', 'GET', undefined, true);
        console.error("FAIL: Market fetch succeeded despite Timeout flag.");
    } catch (e: any) {
        const duration = Date.now() - start;
        if (e.message.includes('CHAOS_INJECTED_TIMEOUT') && duration >= 20000) {
            console.log(`PASS: Caught Simulated Timeout after ${(duration / 1000).toFixed(1)}s.`);
        } else {
            console.error("FAIL: Did not timeout correctly or wrong error.", e);
        }
    }
    resetChaos();

    console.log("\n=== DRILL COMPLETE ===");
};

runDrill();
