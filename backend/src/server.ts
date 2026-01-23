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
                `-----BEGIN PRIVATE KEY-----\n` +
                `MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCy4+svoBnAlVym\n` +
                `TTotzW6M8OvLMcbMbmx6nLUz/ZCEaDJa5ObjKljMv+IxYAlYcRUqB7eUiEWabDqd\n` +
                `LgRrgNCgnedE8l2XfhJGzaRKYr5jlndX8BAwOWEARAz+LaagqlR517OP5aCzXpDf\n` +
                `PHVJLep2d3wLKw+izImVRZSRC/3GzNBZtSZfec/OaNM1kxfoqHQyIsz0jPw4Oj/w\n` +
                `J6xf6pQFhCsxM9UwBpjFvb/DUA56GJqlfAgvqmgqCbwxcPL/bZ9aPoSMR0ielRcl\n` +
                `mMGNDKtHiavgfKDac9l+XffVgznBJnSEJUtIYG2ZDtFZt9ldQ/LxQ6TsyvWwloJM\n` +
                `i20ZAYzlAgMBAAECggEAFtC/0aqrLic+kk0+MtJFG7+saxV1o+QffMHY0IEx+dkq\n` +
                `NvKDygxAGBkO+bokZv3BM8OZM93vdqMAFMTmNmnO8fVBpkb9DdG79gDLR9txKdVq\n` +
                `cjJBdk0TJIwJVi+vVUV0EbgjhCJGzSmt83LMCKHNCf/yN6Bt1ZcdowalTJyJaN3G\n` +
                `eVkfC4HZIcoLJAeR7g5C8zh0Hurlh+c4eGF8fbaiUYpjMlOgeGEo/Ms/oS9bBACh\n` +
                `lIMGujLRfFW8RjFj/+5A3OSaZBDILKh0zf6cmcpduSUiGnp+ss1NjNzt6JUDobdO\n` +
                `czydghkhB4vVp9RywxvKTVXzoYsMFV1Iz5t4Fu/JUQKBgQDuquc12TwlcdTB1EaK\n` +
                `dMEE74uS5DG+beRgM9vjAoHsGn9Vx4jpdAjQEKzR3ek3LXqeag366nBAEwqeiYop\n` +
                `ZXjL9FGjTEJymnFsXuJHy9ma1b1+DnrfuaRDleLcnLe+lhnySzAjErRlPWBfoxKY\n` +
                `I0nG66p9bUE9Db+aBJjF5yDwWQKBgQC/4bBq/AmcGa67NRTvKnvqpME8v2w16PCf\n` +
                `kVuMYSBQErDE6c2gxfjPpVTozHTBTDrTgi0ZUMHM2IZk6bcIh/R27eHA3yOIYJWe\n` +
                `LKygPbtfHGWtKoRvwdHTbwc0Gznyr1ikwPEXZ2gofw9zXMAogiJP4gBW4Qzs81kR\n` +
                `oamdpFYPbQKBgGfNvTIWgapnj/mdsfCWRz02UqZYyanhcerFo2VgudFO1QMh/dJL\n` +
                `vWmBVykQM1bkWOh9iAcR4DB+F6hMeeL3V0qdwMQdbukZcyuHOTOw3bwSKpChC6Ay\n` +
                `xdb/YeRB5UjnT/Gp8g3PHNbLkxcFfhjdgEEcTtKuqik7yZHbXfb1R8ZBAoGBALsv\n` +
                `cwfbGZDTqRZtwR9TxZDw6qXVY73voRU5GyMF+RzELvfZ0cRefMwsUHnOQrPzJowB\n` +
                `OPeyRW0NaYX2TZ0f7Ac9Jvcddy9qcWrd0AV+U1SEglf82zeez4/Ahzl4uf4aupH2\n` +
                `uvsG4KBo22zB9Z9O3CQrqAMZBp/9AU3m9G2ZzG69AoGARNU0/DnjAavtveY8/AN2\n` +
                `C2O1xo8UxFq4bhU8+rWsC1En5RhTuA0RuxlTL1VuCRW4Z1ywDNayavCJ/NlHRahH\n` +
                `eF1TbOZC1gP0aAxrJ6vnIP62/tQVDngmWDNOa4Yb6+ByOYJhSSGzXzCekI6khY7R\n` +
                `yNtFuEM5HGR1PRPrjugeYYo=\n` +
                `-----END PRIVATE KEY-----` :
                privateKey;

            await authenticateWithKeys(keyId, pk, !isProd);
            console.log(`System: Backend Authorized [${isProd ? 'LIVE_NET' : 'SANDBOX'}].`);

            // Agent 14: Start Sentinel for Principal Protection
            // console.log("[DEBUG] Starting Sentinel...");
            // await startSentinel(!isProd);
            // console.log("[DEBUG] Sentinel Started.");

            // Agent 14: Logic Audit
            // console.log("[DEBUG] Starting Audit...");
            // const auditPassed = auditCodebase();
            // console.log("[DEBUG] Audit Complete.");
            // if (!auditPassed) {
            //    console.error("[Agent 14] VETO TRIGGERED: Critical Codebase Violations. Shutting down.");
            //    process.exit(1);
            // }

            // --- ENGINE LOG BRIDGE ---
            console.log("System: Connecting to Python Engine Link...");
            connectToEngine();

        } catch (e) {
            console.error("System: Backend Authorization Failed.", e);
        }
    }
};

const connectToEngine = () => {
    // Attempt to connect to Python Engine SSE
    const connect = async () => {
        try {
            const response = await fetch('http://127.0.0.1:3002/stream');
            if (!response.ok) throw new Error(`Engine stream offline: ${response.status}`);

            console.log("[BRIDGE] Connected to Python Engine Stream.");
            const reader = response.body?.getReader();
            if (!reader) return;

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                console.log(`[BRIDGE] Received chunk: ${value.length} bytes`);
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            // Rebroadcast to frontend clients
                            broadcast(data);

                            // Keep in-memory state updated for INIT events
                            if (data.type === 'LOG') {
                                systemState.logs = [...systemState.logs.slice(-499), data.log];
                            } else if (data.type === 'STATE') {
                                systemState = { ...systemState, ...data.state };
                            }
                        } catch (e) {
                            // Skip malformed JSON
                        }
                    }
                }
            }
        } catch (err: any) {
            console.log(`[BRIDGE] Engine Link failed (${err.message}). Retrying in 5s...`);
            setTimeout(connect, 5000);
        }
    };
    connect();
};

initializeBackend();

app.get('/api/stream', (req: Request, res: Response) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no'); // Disable Nginx buffering
    req.socket.setTimeout(0); // Disable timeouts
    res.flushHeaders();

    const clientId = Date.now();
    const newClient: SSEClient = { id: clientId, res };
    clients.push(newClient);

    // Send initial state
    res.write(`data: ${JSON.stringify({ type: 'INIT', state: systemState })}\n\n`);

    // Heartbeat to keep connection alive (prevent timeout)
    const heartbeat = setInterval(() => {
        try {
            res.write(': keepalive\n\n');
        } catch (e) {
            // Connection likely closed
        }
    }, 15000);

    req.on('close', () => {
        clearInterval(heartbeat);
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
    const { keyId, privateKey, isPaperTrading, useSystemAuth } = req.body;
    try {
        if (useSystemAuth) {
            if (isAuthenticated()) {
                return res.json({ success: true, message: 'Authenticated via System Session' });
            }

            // If not authenticated, try to auth with system keys now
            const isProd = !isPaperTrading;
            const sysKeyId = isProd ? CONFIG.KALSHI.PROD_KEY_ID : CONFIG.KALSHI.DEMO_KEY_ID;
            const sysPrivateKey = isProd ? CONFIG.KALSHI.PROD_PRIVATE_KEY : CONFIG.KALSHI.DEMO_PRIVATE_KEY;

            if (sysKeyId && sysPrivateKey) {
                await authenticateWithKeys(sysKeyId, sysPrivateKey, isPaperTrading);
                return res.json({ success: true, message: 'Authenticated via System Environment' });
            } else {
                throw new Error("System authentication failed: Credentials missing from environment.");
            }
        }

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
        const response = await fetch('http://127.0.0.1:3002/trigger', {
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

app.post('/api/reset', (req: Request, res: Response) => {
    // Forcefully reset system state
    systemState.isProcessing = false;
    systemState.activeAgentId = null;
    broadcast({ type: 'STATE', state: systemState });

    console.log("[BRIDGE] System Reset Requested (Termination)");
    res.json({ message: 'System reset successfully' });
});


app.get('/api/pnl', async (req: Request, res: Response) => {
    try {
        const { getPnLHistory } = await import('../services/dbService');
        const history = await getPnLHistory(24);
        res.json(history);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

app.get('/api/pnl/heatmap', async (req: Request, res: Response) => {
    try {
        const { getDailyPnL } = await import('../services/dbService');
        const data = await getDailyPnL(365);
        res.json(data);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

export { app };

if (process.env.NODE_ENV !== 'test') {
    app.listen(Number(PORT), '0.0.0.0', () => {
        console.log(`SENTIENT ALPHA ENGINE online at port ${PORT}`);
    });
}
