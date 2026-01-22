import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { LogEntry } from '@shared/types';
import { CONFIG } from '../config';
import { authenticateWithKeys, isAuthenticated } from '../services/kalshiService';
import { startSentinel, auditCodebase } from '../agents/exports';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

interface SystemState {
    isProcessing: boolean;
    cycleCount: number;
    logs: LogEntry[];
    activeAgentId: number | null;
    completedAgents: number[];
}

// In-memory state for demonstration
let systemState: SystemState = {
    isProcessing: false,
    cycleCount: 0,
    logs: [],
    activeAgentId: null,
    completedAgents: []
};

interface SSEClient {
    id: number;
    res: Response;
}

// SSE Clients
let clients: SSEClient[] = [];

// Auto-Authentication on Startup
const initializeBackend = async () => {
    // If PROD keys exist and no DEMO key is explicitly set, assume PROD
    const isProd = !!CONFIG.KALSHI.PROD_KEY_ID && !CONFIG.KALSHI.DEMO_KEY_ID;

    // Fallback to defaults if keys are missing from environment
    const keyId = isProd ? CONFIG.KALSHI.PROD_KEY_ID : (CONFIG.KALSHI.DEMO_KEY_ID || 'demo-key-id');
    const privateKey = isProd ? CONFIG.KALSHI.PROD_PRIVATE_KEY : (CONFIG.KALSHI.DEMO_PRIVATE_KEY || 'DEMO_MODE');

    if (!isAuthenticated()) {
        console.log(`System: Attempting Backend Auto-Authentication (${isProd ? 'PROD' : 'SANDBOX'})...`);
        try {
            // Force demo mode for sandbox if no private key provided
            const pk = (privateKey === 'DEMO_MODE' && !isProd) ?
                `-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH\n-----END RSA PRIVATE KEY-----` :
                privateKey;

            await authenticateWithKeys(keyId, pk, !isProd);
            console.log(`System: Backend Authorized [${isProd ? 'LIVE_NET' : 'SANDBOX'}].`);

            // Agent 14: Start Sentinel for Principal Protection
            await startSentinel(!isProd);

            // Agent 14: Logic Audit
            const auditPassed = auditCodebase();
            if (!auditPassed) {
                console.error("[Agent 14] VETO TRIGGERED: Critical Codebase Violations. Shutting down.");
                process.exit(1);
            }

        } catch (e) {
            console.error("System: Backend Authorization Failed.", e);
        }
    }
};
initializeBackend();

app.get('/api/stream', (req: Request, res: Response) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    const clientId = Date.now();
    const newClient: SSEClient = { id: clientId, res };
    clients.push(newClient);

    // Send initial state
    res.write(`data: ${JSON.stringify({ type: 'INIT', state: systemState })}\n\n`);

    req.on('close', () => {
        clients = clients.filter(c => c.id !== clientId);
    });
});

const broadcast = (data: any) => {
    clients.forEach(c => {
        try {
            c.res.write(`data: ${JSON.stringify(data)}\n\n`);
        } catch (err) {
            // Usually means pipe is broken, handled by 'close' event but extra safety
        }
    });
};

app.post('/api/analyze', async (req: Request, res: Response) => {
    const { query } = req.body;
    try {
        const { runCommitteeDebate } = await import('../agents/exports');
        const debate = await runCommitteeDebate(query, 50); // Default to 50c if no price known
        res.json(debate);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/auth', async (req: Request, res: Response) => {
    const { keyId, privateKey, isPaperTrading } = req.body;
    try {
        await authenticateWithKeys(keyId, privateKey, isPaperTrading);
        res.json({ success: true });
    } catch (err: any) {
        res.status(401).json({ error: err.message });
    }
});

app.post('/api/run', async (req: Request, res: Response) => {
    if (systemState.isProcessing) {
        return res.status(400).json({ error: 'System busy. Cycle already in progress.' });
    }

    const { isPaperTrading } = req.body;
    systemState.cycleCount++;
    systemState.isProcessing = true;
    broadcast({ type: 'STATE', state: { isProcessing: true, cycleCount: systemState.cycleCount } });

    console.log(`[BRIDGE] Triggering Python Engine (Cycle ${systemState.cycleCount}, Paper: ${isPaperTrading})...`);

    try {
        // Trigger Python engine via HTTP
        const response = await fetch('http://localhost:3002/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ isPaperTrading })
        });

        if (!response.ok) {
            throw new Error(`Python engine returned ${response.status}`);
        }

        const result = await response.json();
        console.log(`[BRIDGE] Python engine triggered:`, result);

        // Python will stream logs via Gateway agent, we just acknowledge
        res.json({
            message: 'Python Engine cycle initiated.',
            cycleId: systemState.cycleCount,
            engineResponse: result
        });

    } catch (err: any) {
        console.error("[BRIDGE] Failed to trigger Python engine:", err.message);
        systemState.isProcessing = false;
        broadcast({ type: 'STATE', state: { isProcessing: false } });

        broadcast({
            type: 'LOG',
            log: {
                id: 'err-' + Date.now(),
                timestamp: new Date().toISOString(),
                agentId: 0,
                cycleId: systemState.cycleCount,
                level: 'ERROR',
                message: `BRIDGE ERROR: ${err.message}. Is Python engine running on port 3002?`
            }
        });

        res.status(500).json({ error: 'Python engine unreachable', details: err.message });
    }
});

export { app };

if (process.env.NODE_ENV !== 'test') {
    app.listen(Number(PORT), '0.0.0.0', () => {
        console.log(`SENTIENT ALPHA ENGINE online at port ${PORT}`);
    });
}
