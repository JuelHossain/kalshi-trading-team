import React, { useEffect } from 'react';

interface LoginProps {
    apiKeyId: string;
    setApiKeyId: (id: string) => void;
    apiSecret: string;
    setApiSecret: (secret: string) => void;
    isPaperTrading: boolean;
    setIsPaperTrading: (paper: boolean) => void;
    handleLogin: () => void;
    authError: string | null;
}

const Login: React.FC<LoginProps> = ({
    apiKeyId, setApiKeyId, apiSecret, setApiSecret,
    isPaperTrading, setIsPaperTrading, handleLogin, authError
}) => {
    // Auto-login for demo mode
    useEffect(() => {
        if (isPaperTrading && !apiKeyId && !apiSecret) {
            // Set demo credentials
            setApiKeyId('demo-key-id');
            setApiSecret('demo-private-key');
            // Auto-login after a brief delay
            setTimeout(() => {
                handleLogin();
            }, 500);
        }
    }, [isPaperTrading, apiKeyId, apiSecret, setApiKeyId, setApiSecret, handleLogin]);

    return (

        <div className="min-h-screen bg-black flex items-center justify-center p-6 bg-grid-pattern">
            <div className="glass-panel w-full max-w-md p-8 rounded-2xl animate-scale-in border-emerald-500/20 shadow-[0_0_50px_rgba(16,185,129,0.1)]">
                <div className="flex justify-center mb-6">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-700 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.3)]">
                        <span className="text-black font-black font-tech text-3xl">K</span>
                    </div>
                </div>

                <h1 className="text-3xl font-tech font-bold text-center mb-2 tracking-tighter text-gradient-emerald">
                    SENTIENT ALPHA
                </h1>
                <p className="text-gray-500 text-center text-[10px] mb-8 font-mono tracking-[0.3em] uppercase opacity-70">
                    Proprietary v2.0 Command Node
                </p>

                <div className="space-y-5">
                    <div className="group">
                        <label className="text-[10px] font-mono text-emerald-500/70 mb-2 block uppercase tracking-widest">Environment Selection</label>
                        <div className="flex gap-2 p-1 bg-white/5 rounded-xl border border-white/5">
                            <button
                                onClick={() => setIsPaperTrading(true)}
                                className={`flex-1 py-2.5 rounded-lg text-[10px] font-bold transition-all ${isPaperTrading ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' : 'text-gray-500 hover:text-gray-300'}`}
                            >
                                SANDBOX
                            </button>
                            <button
                                onClick={() => setIsPaperTrading(false)}
                                className={`flex-1 py-2.5 rounded-lg text-[10px] font-bold transition-all ${!isPaperTrading ? 'bg-red-500 text-white shadow-lg shadow-red-500/20' : 'text-gray-500 hover:text-gray-300'}`}
                            >
                                LIVE_NET
                            </button>
                        </div>
                    </div>

                    <div className="space-y-1">
                        <label className="text-[10px] font-mono text-gray-500 mb-1 block uppercase tracking-widest">Access Key Identifier</label>
                        <input
                            type="text"
                            value={apiKeyId}
                            onChange={(e) => setApiKeyId(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono transition-all placeholder:text-gray-800"
                            placeholder="e.g. 7f83-..."
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-[10px] font-mono text-gray-500 mb-1 block uppercase tracking-widest">RSA Private Matrix</label>
                        <textarea
                            rows={4}
                            value={apiSecret}
                            onChange={(e) => setApiSecret(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-[9px] font-mono focus:outline-none focus:border-emerald-500/50 transition-all no-scrollbar placeholder:text-gray-800"
                            placeholder="-----BEGIN RSA PRIVATE KEY-----"
                        />
                    </div>

                    {authError && (
                        <div className="text-[10px] text-red-400 bg-red-500/5 p-3 rounded-xl border border-red-500/20 font-mono flex gap-3">
                            <span className="shrink-0">⚠️</span>
                            <span>{authError}</span>
                        </div>
                    )}

                    <button
                        onClick={handleLogin}
                        className="btn-primary w-full py-4 mt-2 group relative overflow-hidden rounded-xl"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite] pointer-events-none"></div>
                        <span className="relative z-10 flex items-center justify-center gap-3 tracking-[0.2em] font-tech text-base">
                            INITIALIZE CORE <span className="group-hover:translate-x-1 transition-transform">→</span>
                        </span>
                    </button>

                    <p className="text-[8px] text-gray-700 text-center font-mono uppercase tracking-widest">
                        Handshake uses RSA-SHA256 Encrypted Session V2
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;
