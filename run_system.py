"""Cross-platform orchestrator to launch both FastAPI backend and Vite frontend concurrently."""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def kill_port_owner(port: int) -> None:
    """Terminates any zombie process holding the specified port on Windows."""
    if os.name != "nt":
        return
    try:
        cmd = f"netstat -ano | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in output.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and (f":{port}" in parts[1]):
                pid = parts[-1]
                if pid.isdigit() and int(pid) > 0 and int(pid) != os.getpid():
                    print(f"  Freeing port {port} (stopping PID {pid})...")
                    subprocess.call(["taskkill", "/F", "/T", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    print("=" * 70)
    print("  CONFIDENCE-AWARE RAG SYSTEM - SYSTEM LAUNCHER")
    print("  Indian Legal & Government Document Intelligence")
    print("=" * 70)

    # Pre-flight: ensure ports 8000 and 5173 are free
    kill_port_owner(8000)
    kill_port_owner(5173)
    time.sleep(0.5)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    # Load .env into env dict if present
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    env[k] = v

    # 1. Start FastAPI Backend
    print("[1/2] Starting FastAPI Backend on http://localhost:8000 ...")
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
    ]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
        env=env,
    )

    # Allow backend 2 seconds to initialize and pre-warm
    time.sleep(2.0)

    # 2. Start Vite Frontend
    print("[2/2] Starting Vite React Frontend on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    print("\n" + "-" * 70)
    print("  System is live!")
    print("  - Backend API & Swagger Docs: http://localhost:8000/docs")
    print("  - React User Interface:       http://localhost:5173")
    print("  Press Ctrl+C to terminate both servers.")
    print("-" * 70 + "\n")

    try:
        while True:
            time.sleep(1.0)
            if backend_proc.poll() is not None:
                print("Backend process terminated.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend process terminated.")
                break
    except KeyboardInterrupt:
        print("\nGracefully shutting down services...")
    finally:
        for proc, name in [(backend_proc, "Backend"), (frontend_proc, "Frontend")]:
            if proc and proc.poll() is None:
                try:
                    if os.name == "nt":
                        subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        proc.terminate()
                    print(f"  Stopped {name} process.")
                except Exception as e:
                    print(f"  Error stopping {name}: {e}")
        print("System shutdown complete.")


if __name__ == "__main__":
    main()
