import { Response } from 'express';
import { LogEntry } from '@shared/types';
import { CONFIG } from '../../config';

export interface SystemState {
  isProcessing: boolean;
  cycleCount: number;
  logs: LogEntry[];
  activeAgentId: number | null;
  completedAgents: number[];
  agentData: Record<number, any>;
}

export interface SSEClient {
  id: number;
  res: Response;
}

export class SSEManager {
  private clients: SSEClient[] = [];

  addClient(res: Response): number {
    const clientId = Date.now();
    const newClient: SSEClient = { id: clientId, res };
    this.clients.push(newClient);

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      try {
        res.write(': keepalive\n\n');
      } catch (e) {
        // Connection likely closed
      }
    }, CONFIG.HEARTBEAT_INTERVAL);

    res.on('close', () => {
      clearInterval(heartbeat);
      this.clients = this.clients.filter((c) => c.id !== clientId);
    });

    return clientId;
  }

  broadcast(data: any): void {
    this.clients.forEach((c) => {
      try {
        c.res.write(`data: ${JSON.stringify(data)}\n\n`);
      } catch (err) {
        // Pipe broken, handled by close event
      }
    });
  }

  setupSSE(res: Response, initialState: SystemState): void {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');
     if (res.socket) res.socket.setTimeout(0);
    res.flushHeaders();

    this.addClient(res);

    // Send initial state
    res.write(`data: ${JSON.stringify({ type: 'INIT', state: initialState })}\n\n`);
  }
}
