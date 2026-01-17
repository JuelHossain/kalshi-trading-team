import { describe, it, expect, vi } from 'vitest';
import request from 'supertest';
import { app } from '../server';

// Mock Kalshi Service to prevent real API calls
vi.mock('../../services/kalshiService', () => ({
    authenticateWithKeys: vi.fn(async (keyId: string) => {
        if (keyId === 'valid-key') return true;
        throw new Error('Invalid Credentials');
    }),
    isAuthenticated: vi.fn(() => false)
}));

describe('API Integration Tests', () => {
    it('POST /api/auth established session with valid keys', async () => {
        const response = await (request(app)
            .post('/api/auth')
            .send({
                keyId: 'valid-key',
                privateKey: 'mock-private-key',
                isPaperTrading: true
            }) as any);

        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);
    });

    it('POST /api/auth returns 401 on invalid keys', async () => {
        const response = await (request(app)
            .post('/api/auth')
            .send({
                keyId: 'wrong-key',
                privateKey: 'mock-private-key',
                isPaperTrading: true
            }) as any);

        expect(response.status).toBe(401);
        expect(response.body.error).toBe('Invalid Credentials');
    });
});
