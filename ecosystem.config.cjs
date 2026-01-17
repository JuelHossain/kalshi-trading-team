module.exports = {
    apps: [{
        name: "kalshi-sentient-alpha",
        script: "npm",
        args: "run preview -- --host --port 8501", // Serving on 8501 to match Blueprint "Streamlit" port convention
        env: {
            NODE_ENV: "production",
        }
    }]
};
