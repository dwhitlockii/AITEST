#!/usr/bin/env python3
"""
AI Agent System Server Control Script
Supports: start, stop, restart, status, diagnostics
"""

import argparse
import subprocess
import sys
import os
import signal
import time
import platform
from pathlib import Path
import logging

PID_FILE = Path("debug_output/system.pid")
REQUIRED_FILES = ["web_interface.py"]
DEFAULT_PORT = 8000

# Setup logging
LOG_FILE = Path("debug_output/start_server.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("start_server")

def is_process_running(pid):
    try:
        if platform.system() == "Windows":
            import psutil
            p = psutil.Process(pid)
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def start_server(port):
    if PID_FILE.exists():
        try:
            with PID_FILE.open() as f:
                pid = int(f.read().strip())
            if is_process_running(pid):
                logger.info(f"Server already running (PID {pid}) on port {port}")
                print(f"🟢 Server already running (PID {pid}) on port {port}")
                return
        except Exception:
            pass
        PID_FILE.unlink(missing_ok=True)
    logger.info(f"Starting web interface on http://127.0.0.1:{port}")
    print(f"🌐 Starting web interface on http://127.0.0.1:{port}")
    print(f"📊 Dashboard: http://127.0.0.1:{port}/")
    print(f"🔧 API Docs: http://127.0.0.1:{port}/docs")
    try:
        proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "web_interface:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"
        ])
        with PID_FILE.open("w") as f:
            f.write(str(proc.pid))
        logger.info(f"Server started (PID {proc.pid})")
        print(f"✅ Server started (PID {proc.pid})")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"❌ Failed to start server: {e}")

def stop_server():
    if not PID_FILE.exists():
        logger.warning("Stop requested but no PID file found.")
        print("🔴 Server is not running (no PID file)")
        return
    try:
        with PID_FILE.open() as f:
            pid = int(f.read().strip())
        if not is_process_running(pid):
            logger.warning(f"No running process with PID {pid} (stale PID file)")
            print(f"🔴 No running process with PID {pid}")
            PID_FILE.unlink(missing_ok=True)
            return
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"])
        else:
            os.kill(pid, signal.SIGTERM)
        logger.info(f"Server stopped (PID {pid})")
        print(f"🛑 Server stopped (PID {pid})")
        time.sleep(1)
        PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        print(f"❌ Error stopping server: {e}")

def status_server():
    if not PID_FILE.exists():
        logger.info("Status checked: server not running (no PID file)")
        print("🔴 Server is not running (no PID file)")
        return
    try:
        with PID_FILE.open() as f:
            pid = int(f.read().strip())
        if is_process_running(pid):
            logger.info(f"Server is running (PID {pid})")
            print(f"🟢 Server is running (PID {pid})")
        else:
            logger.warning(f"Server is not running (stale PID {pid})")
            print(f"🔴 Server is not running (stale PID {pid})")
            PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        print(f"❌ Error checking status: {e}")

def diagnostics(port):
    logger.info("Running diagnostics...")
    print("🔍 Running diagnostics...")
    # Python version and executable
    print(f"🐍 Python: {sys.version}")
    print(f"🐍 Python Executable: {sys.executable}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Python Executable: {sys.executable}")
    # Check required files and directories
    for file in REQUIRED_FILES:
        exists = Path(file).exists()
        logger.info(f"Required file {file}: {'FOUND' if exists else 'MISSING'}")
        if not exists:
            print(f"❌ Required file missing: {file}")
        else:
            print(f"✅ Found: {file}")
    # Check debug_output directory and permissions
    debug_dir = Path("debug_output")
    if not debug_dir.exists():
        print(f"❌ Directory missing: {debug_dir}")
        logger.error(f"Directory missing: {debug_dir}")
    else:
        try:
            testfile = debug_dir / "_test_perm.tmp"
            with testfile.open("w") as f:
                f.write("test")
            testfile.unlink()
            print(f"✅ Directory writable: {debug_dir}")
            logger.info(f"Directory writable: {debug_dir}")
        except Exception as e:
            print(f"❌ Directory not writable: {debug_dir} ({e})")
            logger.error(f"Directory not writable: {debug_dir} ({e})")
    # Check environment variables
    for var in ["PYTHONPATH", "PATH"]:
        val = os.environ.get(var)
        logger.info(f"Env {var}: {val if val else 'NOT SET'}")
        print(f"ℹ️  Env {var}: {val if val else 'NOT SET'}")
    # Check required packages
    required_pkgs = ["uvicorn", "psutil"]
    for pkg in required_pkgs:
        try:
            __import__(pkg)
            print(f"✅ Package installed: {pkg}")
            logger.info(f"Package installed: {pkg}")
        except ImportError:
            print(f"❌ Package missing: {pkg}")
            logger.error(f"Package missing: {pkg}")
    # Check port availability
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        print(f"✅ Port {port} is available")
        logger.info(f"Port {port} is available")
    except OSError:
        print(f"❌ Port {port} is in use")
        logger.error(f"Port {port} is in use")
    finally:
        s.close()
    # PID file
    if PID_FILE.exists():
        with PID_FILE.open() as f:
            pid = int(f.read().strip())
        running = is_process_running(pid)
        print(f"ℹ️  PID file exists: {pid} (running: {running})")
        logger.info(f"PID file exists: {pid} (running: {running})")
    else:
        print("ℹ️  No PID file found")
        logger.info("No PID file found")

def main():
    parser = argparse.ArgumentParser(description="AI Agent System Server Control")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "diagnostics"], help="Command to execute")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Web interface port (default: 8000)")
    args = parser.parse_args()

    logger.info(f"Command received: {args.command} (port={args.port})")
    if args.command == "start":
        start_server(args.port)
    elif args.command == "stop":
        stop_server()
    elif args.command == "restart":
        stop_server()
        time.sleep(1)
        start_server(args.port)
    elif args.command == "status":
        status_server()
    elif args.command == "diagnostics":
        diagnostics(args.port)

if __name__ == "__main__":
    main()
