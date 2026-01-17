import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { spawn } from 'child_process';
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

// Auto-Authentication on Startup (Sandbox by default)
const initializeBackend = async () => {
    const isProd = !!CONFIG.KALSHI.PROD_KEY_ID && !CONFIG.KALSHI.DEMO_KEY_ID;
    const keyId = isProd ? CONFIG.KALSHI.PROD_KEY_ID : CONFIG.KALSHI.DEMO_KEY_ID;
    const privateKey = isProd ? CONFIG.KALSHI.PROD_PRIVATE_KEY : CONFIG.KALSHI.DEMO_PRIVATE_KEY;

    if (!isAuthenticated() && keyId && privateKey) {
        console.log(`System: Attempting Backend Auto-Authentication (${isProd ? 'PROD' : 'SANDBOX'})...`);
        try {
            await authenticateWithKeys(keyId, privateKey, !isProd);
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

    systemState.isProcessing = true;
    systemState.cycleCount++;
    broadcast({ type: 'STATE', state: { isProcessing: true, cycleCount: systemState.cycleCount } });

    console.log("[BRIDGE] Spawning Python Ghost Engine...");
    const isPaperTrading = req.body.isPaperTrading;

    const pyProcess = spawn('python3', ['engine/main.py'], {
        env: {
            ...process.env,
            JSON_LOGS: 'true',
            IS_PAPER_TRADING: isPaperTrading ? 'true' : 'false'
        },
        cwd: process.cwd()
    });

    // Cleanup: Kill Python if Node exits
    const cleanup = () => pyProcess.kill();
    process.on('exit', cleanup);
    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

    pyProcess.stdout.on('data', (data) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
            if (!line.trim()) continue;
            try {
                const event = JSON.parse(line);
                if (event.type === 'LOG') {
                    const log = {
                        id: Math.random().toString(36).substring(7),
                        timestamp: new Date().toISOString(),
                        ...event.log
                    };
                    systemState.logs = [...systemState.logs.slice(-499), log];
                    broadcast({ type: 'LOG', log });
                } else {
                    // STATE, VAULT, SIMULATION, HEALTH
                    broadcast(event);
                }
            } catch (e) {
                // Not JSON, just regular log
                console.log(`[PY] ${line}`);
            }
        }
    });

    pyProcess.stderr.on('data', (data) => {
        console.error(`[PY_ERR] ${data}`);
    });

    pyProcess.on('close', (code) => {
        console.log(`[BRIDGE] Python Engine exited with code ${code}`);
        systemState.isProcessing = false;
        broadcast({ type: 'STATE', state: { isProcessing: false } });
    });

    res.json({ message: 'Python Engine cycle initiated.', cycleId: systemState.cycleCount });
});

export { app };

if (process.env.NODE_ENV !== 'test') {
    app.listen(Number(PORT), '0.0.0.0', () => {
        console.log(`SENTIENT ALPHA ENGINE online at port ${PORT}`);
    });
}
