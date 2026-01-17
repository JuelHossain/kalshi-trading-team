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
            env: {
                PYTHONPATH: "."
            }
        },
        {
            name: "sentient-alpha-dashboard",
            script: "python3",
            args: "-m streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0",
            env: {
                PYTHONPATH: "."
            }
        }


    ]
};

