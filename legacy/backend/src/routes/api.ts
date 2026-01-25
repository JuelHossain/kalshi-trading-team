import { Router, Request, Response } from 'express';
import { SSEManager } from '../middleware/sse';
import { StateManager } from '../services/stateManager';
import { EngineBridge } from '../services/engineBridge';
import { getPnLHistory, getDailyPnL } from '../services/dbService';
import { CONFIG } from '../config';
import { kalshiService } from '../services/kalshiService';

const router = Router();

export const setupAPIRoutes = (
  sseManager: SSEManager,
  stateManager: StateManager,
  engineBridge: EngineBridge
) => {
  router.get('/stream', (req: Request, res: Response) => {
    sseManager.setupSSE(res, stateManager.getState());
  });

  // router.post('/analyze', async (req: Request, res: Response) => {
  //   const { query } = req.body;
  //   try {
  //     const debate = await runCommitteeDebate(query, CONFIG.DEFAULT_DEBATE_PRICE);
  //     res.json(debate);
  //   } catch (err: any) {
  //     res.status(500).json({ error: err.message });
  //   }
  // });

  router.post('/run', async (req: Request, res: Response) => {
    const state = stateManager.getState();

    // Block if kill switch is active
    if (state.killSwitchActive) {
      return res.status(403).json({ error: 'System locked. Kill switch is active.' });
    }

    if (state.isProcessing) {
      return res.status(400).json({ error: 'System busy. Cycle already in progress.' });
    }

    const { isPaperTrading } = req.body;
    stateManager.updateState({
      cycleCount: state.cycleCount + 1,
      isProcessing: true,
    });
    sseManager.broadcast({
      type: 'STATE',
      state: { isProcessing: true, cycleCount: state.cycleCount + 1 },
    });

    console.log(
      `[BRIDGE] Triggering Python Engine (Cycle ${state.cycleCount + 1}, Paper: ${isPaperTrading})...`
    );

    try {
      const result = await engineBridge.triggerEngine(isPaperTrading);
      console.log(`[BRIDGE] Python engine triggered:`, result);

      res.json({
        message: 'Python Engine cycle initiated.',
        cycleId: state.cycleCount + 1,
        engineResponse: result,
      });
    } catch (err: any) {
      console.error('[BRIDGE] Failed to trigger Python engine:', err.message);
      stateManager.updateState({ isProcessing: false });
      sseManager.broadcast({ type: 'STATE', state: { isProcessing: false } });

      sseManager.broadcast({
        type: 'LOG',
        log: {
          id: 'err-' + Date.now(),
          timestamp: new Date().toISOString(),
          agentId: 0,
          cycleId: state.cycleCount + 1,
          level: 'ERROR',
          message: `BRIDGE ERROR: ${err.message}. Is Python engine running on port 3002?`,
        },
      });

      res.status(500).json({ error: 'Python engine unreachable', details: err.message });
    }
  });

  router.post('/reset', (req: Request, res: Response) => {
    stateManager.reset();
    sseManager.broadcast({ type: 'STATE', state: stateManager.getState() });

    console.log('[BRIDGE] System Reset Requested (Termination)');
    res.json({ message: 'System reset successfully' });
  });

  // Cancel current cycle gracefully (no emergency procedures)
  router.post('/cancel-cycle', async (req: Request, res: Response) => {
    console.log('[BRIDGE] Cancel Cycle Requested');

    const state = stateManager.getState();
    if (!state.isProcessing) {
      return res.json({ message: 'No cycle in progress to cancel' });
    }

    // Update state to stop processing
    stateManager.updateState({ isProcessing: false });
    sseManager.broadcast({
      type: 'LOG',
      log: {
        id: 'cancel-' + Date.now(),
        timestamp: new Date().toISOString(),
        agentId: 0,
        cycleId: state.cycleCount,
        phaseId: 0,
        level: 'WARN',
        message: 'Cycle cancelled by user request.',
      },
    });
    sseManager.broadcast({ type: 'STATE', state: { isProcessing: false } });

    // Tell Python engine to cancel gracefully
    await engineBridge.cancelCycle();

    res.json({ message: 'Cycle cancelled gracefully' });
  });

  // Kill Switch - Activate (Locks the whole system)
  router.post('/kill-switch/activate', async (req: Request, res: Response) => {
    console.log('[BRIDGE] 🚨 KILL SWITCH ACTIVATED 🚨');

    stateManager.activateKillSwitch();
    sseManager.broadcast({
      type: 'LOG',
      log: {
        id: 'kill-' + Date.now(),
        timestamp: new Date().toISOString(),
        agentId: 0,
        cycleId: stateManager.getState().cycleCount,
        phaseId: 0,
        level: 'ERROR',
        message: '🔒 KILL SWITCH ACTIVATED - System Locked',
      },
    });
    sseManager.broadcast({ type: 'STATE', state: stateManager.getState() });

    await engineBridge.triggerKillSwitch();
    res.json({ message: 'Kill switch activated', killSwitchActive: true });
  });

  // Kill Switch - Deactivate (Unlocks the system)
  router.post('/kill-switch/deactivate', async (req: Request, res: Response) => {
    console.log('[BRIDGE] 🟢 KILL SWITCH DEACTIVATED');

    stateManager.deactivateKillSwitch();
    sseManager.broadcast({
      type: 'LOG',
      log: {
        id: 'unlock-' + Date.now(),
        timestamp: new Date().toISOString(),
        agentId: 0,
        cycleId: stateManager.getState().cycleCount,
        phaseId: 0,
        level: 'INFO',
        message: '🟢 KILL SWITCH DEACTIVATED - System Unlocked',
      },
    });
    sseManager.broadcast({ type: 'STATE', state: stateManager.getState() });

    res.json({ message: 'Kill switch deactivated', killSwitchActive: false });
  });

  // Kill Switch - Get Status
  router.get('/kill-switch/status', (req: Request, res: Response) => {
    res.json({ killSwitchActive: stateManager.getState().killSwitchActive });
  });

  // Legacy kill-switch endpoint (kept for backwards compatibility)
  router.post('/kill-switch', async (req: Request, res: Response) => {
    console.log('[BRIDGE] 🚨 LEGACY KILL SWITCH ACTIVATED 🚨');

    stateManager.activateKillSwitch();
    sseManager.broadcast({
      type: 'LOG',
      log: {
        id: 'kill-' + Date.now(),
        timestamp: new Date().toISOString(),
        agentId: 0,
        cycleId: stateManager.getState().cycleCount,
        phaseId: 0,
        level: 'ERROR',
        message: '🔒 EMERGENCY KILL SWITCH ACTIVATED BY USER',
      },
    });
    sseManager.broadcast({ type: 'STATE', state: stateManager.getState() });

    await engineBridge.triggerKillSwitch();
    res.json({ message: 'Kill switch executed' });
  });

  // PnL endpoints - real data from Supabase
  router.get('/pnl', async (req: Request, res: Response) => {
    try {
      const history = await getPnLHistory(24);
      res.json(history);
    } catch (e: any) {
      console.error('[API] PnL fetch error:', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  router.get('/pnl/heatmap', async (req: Request, res: Response) => {
    try {
      const data = await getDailyPnL(365);
      res.json(data);
    } catch (e: any) {
      console.error('[API] Heatmap fetch error:', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  return router;
};
