import dotenv from 'dotenv';
dotenv.config(); // Must be first, before other imports that use env vars

import express from 'express';
import cors from 'cors';
import { SSEManager } from './middleware/sse';
import { StateManager } from './services/stateManager';
import { EngineBridge } from './services/engineBridge';
import { authRouter } from './routes/auth';
import { setupAPIRoutes } from './routes/api';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: process.env.FRONTEND_URL || 'http://localhost:3000' }));
app.use(express.json());

// Initialize services
const sseManager = new SSEManager();
const stateManager = new StateManager();
const engineBridge = new EngineBridge(sseManager, stateManager);

// Mount routes
app.use('/api', authRouter);
app.use('/api', setupAPIRoutes(sseManager, stateManager, engineBridge));

// Initialize backend
engineBridge.initializeBackend();

if (process.env.NODE_ENV !== 'test') {
  app.listen(Number(PORT), '0.0.0.0', () => {
    console.log(`SENTIENT ALPHA ENGINE online at port ${PORT}`);
  });
}

export { app };
