#!/usr/bin/env python3
"""
Sentient Alpha - Central Application Runner
============================================
Unified script to run the application locally in development or production mode.

Usage:
    python scripts/run.py [dev|prod|stop|status]

Commands:
    dev     - Run in development mode (hot reload, verbose logging)
    prod    - Run in production mode (PM2 process manager)
    stop    - Stop all running services
    status  - Check status of services and ports

Examples:
    python scripts/run.py dev       # Start development server
    python scripts/run.py prod      # Start production server
    python scripts/run.py stop      # Stop all services
    python scripts/run.py status    # Check ports and processes
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ENGINE_DIR = PROJECT_ROOT / "engine"
ENGINE_PORT = 3002
FRONTEND_PORT = 3000


def log(msg: str, level: str = "info"):
    """Print formatted log messages."""
    # Disable colors on Windows unless ANSICON or similar is present
    use_colors = not is_windows() or os.environ.get("ANSICON") or os.environ.get("TERM")
    
    colors = {
        "info": "\033[36m" if use_colors else "",     # Cyan
        "success": "\033[32m" if use_colors else "",  # Green
        "warning": "\033[33m" if use_colors else "",  # Yellow
        "error": "\033[31m" if use_colors else "",    # Red
        "header": "\033[35m" if use_colors else "",   # Magenta
    }
    reset = "\033[0m" if use_colors else ""
    color = colors.get(level, "")
    prefix = {
        "info": "[INFO]",
        "success": "[OK]",
        "warning": "[WARN]",
        "error": "[ERROR]",
        "header": "[GHOST]",
    }.get(level, "[INFO]")
    print(f"{color}{prefix} {msg}{reset}")


def run_command(cmd: list[str], cwd: Path = None, check: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        return subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=check,
            shell=(platform.system() == "Windows" and cmd[0] not in ["python", "python3", "npm"])
        )
    except Exception as e:
        log(f"Command failed: {' '.join(cmd)} - {e}", "error")
        raise


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def check_port(port: int) -> int | None:
    """Check if a port is in use and return the process ID if it is."""
    try:
        if is_windows():
            # Windows: use netstat with shell=True for pipe support
            result = subprocess.run(
                f"netstat -ano | findstr :{port}",
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                return int(parts[-1])
                            except ValueError:
                                continue
        else:
            # Unix: use lsof or netstat
            result = run_command(["lsof", "-ti", f":{port}"])
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split("\n")[0])
    except Exception as e:
        log(f"Could not check port {port}: {e}", "warning")
    return None


def kill_process(pid: int) -> bool:
    """Kill a process by PID."""
    try:
        if is_windows():
            run_command(["taskkill", "/PID", str(pid), "/F"], check=False)
        else:
            run_command(["kill", "-9", str(pid)], check=False)
        time.sleep(1)  # Give it time to die
        return True
    except Exception as e:
        log(f"Failed to kill process {pid}: {e}", "warning")
        return False


def clear_port(port: int) -> bool:
    """Clear a port by killing the process using it."""
    pid = check_port(port)
    if pid:
        log(f"Port {port} is in use by PID {pid}. Attempting to free it...", "warning")
        if kill_process(pid):
            log(f"Freed port {port}", "success")
            return True
        return False
    return True


def check_python_deps() -> bool:
    """Check if Python dependencies are installed."""
    req_file = ENGINE_DIR / "requirements.txt"
    if not req_file.exists():
        log("requirements.txt not found", "warning")
        return True

    try:
        # Try importing key dependencies
        subprocess.run(
            [sys.executable, "-c", "import aiohttp, aiohttp_cors"],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        log("Python dependencies not installed", "warning")
        return False


def install_python_deps():
    """Install Python dependencies."""
    log("Installing Python dependencies...")
    req_file = ENGINE_DIR / "requirements.txt"
    result = run_command([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
    if result.returncode == 0:
        log("Python dependencies installed", "success")
    else:
        log("Failed to install Python dependencies", "error")
        print(result.stderr)


def check_node_deps() -> bool:
    """Check if Node dependencies are installed."""
    return (FRONTEND_DIR / "node_modules").exists()


def install_node_deps():
    """Install Node dependencies."""
    log("Installing Node dependencies...")
    result = run_command(["npm", "install"], cwd=FRONTEND_DIR)
    if result.returncode == 0:
        log("Node dependencies installed", "success")
    else:
        log("Failed to install Node dependencies", "error")


def status():
    """Check status of services and ports."""
    log("Checking system status...", "header")
    
    # Check ports
    engine_pid = check_port(ENGINE_PORT)
    frontend_pid = check_port(FRONTEND_PORT)
    
    print(f"\n{'Service':<20} {'Port':<10} {'Status':<15} {'PID':<10}")
    print("-" * 60)
    
    engine_status = f"PID {engine_pid}" if engine_pid else "Not running"
    engine_color = "\033[32m" if engine_pid else "\033[31m"
    print(f"{'Engine (Python)':<20} {ENGINE_PORT:<10} {engine_status:<15} {engine_pid or '-'}")
    
    frontend_status = f"PID {frontend_pid}" if frontend_pid else "Not running"
    print(f"{'Frontend (Vite)':<20} {FRONTEND_PORT:<10} {frontend_status:<15} {frontend_pid or '-'}")
    
    # Check dependencies
    print("\n" + "-" * 60)
    py_deps = check_python_deps()
    node_deps = check_node_deps()
    check = "[OK]" 
    cross = "[X]"
    print(f"Python dependencies: {check if py_deps else cross} {'Installed' if py_deps else 'Missing'}")
    print(f"Node dependencies: {check if node_deps else cross} {'Installed' if node_deps else 'Missing'}")
    print("-" * 60)


def stop():
    """Stop all running services."""
    log("Stopping all services...", "header")
    
    # Stop PM2 if running
    result = run_command(["npx", "pm2", "stop", "all"])
    if result.returncode == 0:
        log("PM2 processes stopped", "success")
    
    # Clear ports
    for port in [ENGINE_PORT, FRONTEND_PORT]:
        pid = check_port(port)
        if pid:
            log(f"Stopping process on port {port} (PID {pid})...")
            kill_process(pid)
    
    log("All services stopped", "success")


def dev():
    """Run in development mode."""
    log("Starting in DEVELOPMENT mode...", "header")
    
    # Check and install dependencies
    if not check_python_deps():
        install_python_deps()
    
    if not check_node_deps():
        install_node_deps()
    
    # Clear ports
    log("Checking ports...")
    for port in [ENGINE_PORT, FRONTEND_PORT]:
        if not clear_port(port):
            log(f"Could not free port {port}. Please stop the conflicting process manually.", "error")
            return
    
    log("Starting services...")
    log(f"Frontend will be available at: http://localhost:{FRONTEND_PORT}", "info")
    log(f"Engine API will be available at: http://localhost:{ENGINE_PORT}", "info")
    log("Press Ctrl+C to stop\n", "warning")
    
    # Use subprocess.Popen for real-time streaming output
    import signal
    
    process = None
    
    def signal_handler(sig, frame):
        log("\nShutting down...", "warning")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Use subprocess.Popen to stream output in real-time
        process = subprocess.Popen(
            [
                "npx", "concurrently",
                "--names", "FRONTEND,ENGINE",
                "--prefix-colors", "cyan,magenta",
                "--kill-others",
                "cd frontend && npm run dev",
                f"{sys.executable} engine/main.py"
            ],
            cwd=PROJECT_ROOT,
            shell=is_windows()
        )
        process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)


def prod():
    """Run in production mode using PM2."""
    log("Starting in PRODUCTION mode...", "header")
    
    # Check PM2
    result = run_command(["npx", "pm2", "--version"])
    if result.returncode != 0:
        log("Installing PM2...")
        run_command(["npm", "install", "-g", "pm2"])
    
    # Build frontend
    log("Building frontend...")
    result = run_command(["npm", "run", "build"])
    if result.returncode != 0:
        log("Build failed", "error")
        return
    
    # Clear ports
    for port in [ENGINE_PORT, FRONTEND_PORT]:
        clear_port(port)
    
    # Start with PM2
    log("Starting services with PM2...")
    result = run_command(["npx", "pm2", "start", "ecosystem.config.cjs"])
    if result.returncode == 0:
        run_command(["npx", "pm2", "save"])
        log("Services started", "success")
        log(f"Frontend: http://localhost:{FRONTEND_PORT}", "info")
        log(f"Engine: http://localhost:{ENGINE_PORT}", "info")
        log("\nUseful commands:", "info")
        log("  npx pm2 logs      - View logs", "info")
        log("  npx pm2 monit     - Monitor processes", "info")
        log("  npx pm2 stop all  - Stop all services", "info")
    else:
        log("Failed to start services", "error")


def main():
    parser = argparse.ArgumentParser(
        description="Sentient Alpha - Application Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run.py dev      # Start development server
  python scripts/run.py prod     # Start production server
  python scripts/run.py stop     # Stop all services
  python scripts/run.py status   # Check status
        """
    )
    parser.add_argument(
        "command",
        choices=["dev", "prod", "stop", "status"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    # Ensure we're in the project root
    os.chdir(PROJECT_ROOT)
    
    if args.command == "dev":
        dev()
    elif args.command == "prod":
        prod()
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
