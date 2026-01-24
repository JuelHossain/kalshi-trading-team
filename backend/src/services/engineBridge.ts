import { CONFIG } from '../../config';
import { authenticateWithKeys, isAuthenticated, kalshiFetch } from '../../services/kalshiService';
import { startSentinel, auditCodebase } from '../../agents/agent-14-qa-chaos/index';
import { SSEManager, SystemState } from '../middleware/sse';
import { StateManager } from './stateManager';
import { runCommitteeDebate } from '../../agents/agent-4-analyst/index';
import { logToDb } from '../../services/dbService';

export class EngineBridge {
  private sseManager: SSEManager;
  private stateManager: StateManager;

  constructor(sseManager: SSEManager, stateManager: StateManager) {
    this.sseManager = sseManager;
    this.stateManager = stateManager;
  }

  async initializeBackend(): Promise<void> {
    const isProd = !!CONFIG.KALSHI.PROD_KEY_ID && !CONFIG.KALSHI.DEMO_KEY_ID;
    const keyId = isProd ? CONFIG.KALSHI.PROD_KEY_ID : CONFIG.KALSHI.DEMO_KEY_ID || 'demo-key-id';
    const privateKey = isProd
      ? CONFIG.KALSHI.PROD_PRIVATE_KEY
      : CONFIG.KALSHI.DEMO_PRIVATE_KEY || 'DEMO_MODE';

    if (!isAuthenticated()) {
      console.log(
        `System: Attempting Backend Auto-Authentication (${isProd ? 'PROD' : 'SANDBOX'})...`
      );
      try {
        const pk =
          privateKey === 'DEMO_MODE' && !isProd
            ? `-----BEGIN PRIVATE KEY-----\n` +
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
            `-----END PRIVATE KEY-----`
            : privateKey;

        await authenticateWithKeys(keyId, pk, !isProd);
        console.log(`System: Backend Authorized [${isProd ? 'LIVE_NET' : 'SANDBOX'}].`);

        console.log('System: Starting Sentinel...');
        await startSentinel(!isProd);
        console.log('System: Sentinel Started.');

        console.log('System: Starting Audit...');
        const auditPassed = auditCodebase();
        console.log('System: Audit Complete.');
        if (!auditPassed) {
          console.warn(
            '[Agent 14] AUDIT WARNING: Potential issues detected but continuing startup.'
          );
        }

        console.log('System: Synchronizing Engine State...');
        try {
          const healthRes = await fetch('http://127.0.0.1:3002/health');
          if (healthRes.ok) {
            const healthData = await healthRes.json();
            this.stateManager.updateState({
              cycleCount: healthData.cycleCount,
              isProcessing: healthData.isProcessing,
            });
            console.log(
              `System: Engine Synced (Cycle ${this.stateManager.getState().cycleCount}).`
            );
          }
        } catch (e) {
          console.log('System: Engine Health Check Failed (Pre-Sync).');
        }

        console.log('System: Connecting to Python Engine Link...');
        this.connectToEngine();
      } catch (e) {
        console.error('System: Backend Authorization Failed.', e);
      }
    }
  }

  private connectToEngine(): void {
    const connect = async () => {
      try {
        const response = await fetch('http://127.0.0.1:3002/stream');
        if (!response.ok) throw new Error(`Engine stream offline: ${response.status}`);

        console.log('[BRIDGE] Connected to Python Engine Stream.');
        const reader = response.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine || trimmedLine.startsWith(':')) continue;

            if (trimmedLine.startsWith('data: ')) {
              try {
                const data = JSON.parse(trimmedLine.slice(6));
                this.sseManager.broadcast(data);
                if (data.type === 'LOG') {
                  this.stateManager.addLog(data.log);
                } else if (data.type === 'STATE') {
                  this.stateManager.updateState(data.state);
                } else if (data.type === 'AGENT_DATA') {
                  this.stateManager.setAgentData(data.agentId, data.data);
                } else if (data.type === 'VAULT') {
                  // Log balance to Supabase for PnL tracking
                  const vaultData = data.data;
                  if (vaultData?.total) {
                    logToDb('balance_history', {
                      balance_cents: vaultData.total,
                      cycle_id: this.stateManager.getState().cycleCount,
                    });
                  }
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
      } catch (err: any) {
        console.log(
          `[BRIDGE] Engine Link failed (${err.message}). Retrying in ${CONFIG.ENGINE_RETRY_DELAY / 1000}s...`
        );
        setTimeout(connect, CONFIG.ENGINE_RETRY_DELAY);
      }
    };
    connect();
  }

  async triggerEngine(isPaperTrading: boolean): Promise<any> {
    const response = await fetch('http://127.0.0.1:3002/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ isPaperTrading }),
    });

    if (!response.ok) {
      throw new Error(`Python engine returned ${response.status}`);
    }

    return response.json();
  }

  async triggerKillSwitch(): Promise<void> {
    try {
      const response = await fetch('http://127.0.0.1:3002/kill-switch', {
        method: 'POST',
      });

      if (!response.ok) {
        console.error('[BRIDGE] Failed to trigger Python Kill Switch. Status:', response.status);
      } else {
        console.log('[BRIDGE] Python Engine Kill Switch Triggered Successfully.');
      }
    } catch (e: any) {
      console.error('[BRIDGE] Failed to reach Python Engine during Kill Switch:', e.message);
    }
  }
}
