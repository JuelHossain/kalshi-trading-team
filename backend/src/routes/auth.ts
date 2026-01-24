import { Router, Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import { CONFIG } from '../../config';
import { authenticateWithKeys, isAuthenticated } from '../services/kalshiService';

const router = Router();
const JWT_SECRET = process.env.JWT_SECRET || 'fallback_secret';

const authenticateToken = (req: Request, res: Response, next: Function) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    if (!token) return res.sendStatus(401);
    jwt.verify(token, JWT_SECRET, (err: any, user: any) => {
        if (err) return res.sendStatus(403);
        (req as any).user = user;
        next();
    });
};

router.post('/login', (req: Request, res: Response) => {
    const { username, password } = req.body;
    if (username === 'admin' && password === 'password') {
        const token = jwt.sign({ username }, JWT_SECRET, { expiresIn: '1h' });
        res.json({ token });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});

router.post('/auth', async (req: Request, res: Response) => {
    const { keyId, privateKey, isPaperTrading, useSystemAuth } = req.body;
    try {
        if (useSystemAuth) {
            if (isAuthenticated()) {
                return res.json({ success: true, message: 'Authenticated via System Session' });
            }

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

export { router as authRouter, authenticateToken };