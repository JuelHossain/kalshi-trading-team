module.exports = {
    apps: [
        {
            name: "kalshi-alpha-backend",
            cwd: "./backend",
            script: "npm",
            args: "start",
            env: {
                NODE_ENV: "production",
            }
        },
        {
            name: "kalshi-alpha-frontend",
            cwd: "./frontend",
            script: "npm",
            args: "run preview -- --host --port 3000",
            env: {
                NODE_ENV: "production",
            }
        },
        {
            name: "sentient-alpha-engine",
            script: "python3",
            args: "engine/main.py",
            autorestart: true,
            max_memory_restart: "500M",
            env: {
                PYTHONPATH: ".",
                JSON_LOGS: "true",
                IS_PAPER_TRADING: "true"  // Default to paper trading
            }
        }
    ]
};


