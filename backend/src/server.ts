import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { runOrchestratorCycle } from './orchestrator';
import { LogEntry } from '../types';
import { CONFIG } from '../config';
import { authenticateWithKeys, isAuthenticated } from '../services/kalshiService';

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

app.post('/api/run', async (req: Request, res: Response) => {
    if (systemState.isProcessing) {
        return res.status(400).json({ error: 'System busy. Cycle already in progress.' });
    }

    const { isPaperTrading } = req.body;
    systemState.cycleCount++;

    // Trigger the cycle in the background
    runOrchestratorCycle(isPaperTrading, systemState.cycleCount, (update: any) => {
        // Update local state
        if (update.type === 'LOG') {
            systemState.logs = [...systemState.logs.slice(-499), update.log];
        } else if (update.type === 'STATE') {
            systemState = { ...systemState, ...update.state };
        }
        // Broadcast to all connected frontends
        broadcast(update);
    }).catch(err => {
        console.error("Background cycle crashed:", err);
        broadcast({
            type: 'LOG',
            log: {
                id: 'err-' + Date.now(),
                timestamp: new Date().toISOString(),
                agentId: 0,
                cycleId: systemState.cycleCount,
                level: 'ERROR',
                message: `CRITICAL PROCESS CRASH: ${err.message}`
            }
        });
        systemState.isProcessing = false;
        broadcast({ type: 'STATE', state: { isProcessing: false } });
    });

    res.json({ message: 'Engine cycle initiated.', cycleId: systemState.cycleCount });
});

app.listen(Number(PORT), '0.0.0.0', () => {
    console.log(`SENTIENT ALPHA ENGINE online at port ${PORT}`);
});
