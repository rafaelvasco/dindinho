#!/usr/bin/env python3
"""
Script to run both backend and frontend simultaneously.

This script starts the FastAPI backend and Streamlit frontend
in separate processes and manages their lifecycle.
"""

import subprocess
import sys
import signal
import time
import requests
from pathlib import Path

from backend.config import settings


def run_backend():
    """Start the FastAPI backend server."""
    print(f"Starting backend on {settings.BACKEND_HOST}:{settings.BACKEND_PORT}...")
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", settings.BACKEND_HOST,
        "--port", str(settings.BACKEND_PORT)
    ])


def run_frontend():
    """Start the Streamlit frontend server."""
    print(f"Starting frontend on port {settings.FRONTEND_PORT}...")
    return subprocess.Popen([
        sys.executable, "-m", "streamlit",
        "run",
        "frontend/app.py",
        "--server.port", str(settings.FRONTEND_PORT),
        "--server.address", "0.0.0.0"
    ])


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down gracefully...")
    sys.exit(0)


def main():
    """Main function to run both services."""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("Finance Analysis Application")
    print("=" * 60)
    print()

    # Start both services
    backend = None
    frontend = None

    try:
        # Start backend first
        backend = run_backend()

        # Wait for backend to be ready
        print("Waiting for backend to be ready...")
        backend_ready = False
        for i in range(30):  # Try for 30 seconds
            try:
                response = requests.get(f"http://localhost:{settings.BACKEND_PORT}/health", timeout=1)
                if response.status_code == 200:
                    backend_ready = True
                    print("✓ Backend is ready!")
                    break
            except:
                pass
            time.sleep(1)

        if not backend_ready:
            print("ERROR: Backend failed to start in time")
            raise Exception("Backend startup timeout")

        # Now start frontend
        frontend = run_frontend()

        print()
        print("=" * 60)
        print("Application started successfully!")
        print("=" * 60)
        print(f"Backend API: http://localhost:{settings.BACKEND_PORT}")
        print(f"API Docs: http://localhost:{settings.BACKEND_PORT}/docs")
        print(f"Frontend: http://localhost:{settings.FRONTEND_PORT}")
        print()
        print("Press Ctrl+C to stop the application")
        print("=" * 60)
        print()

        # Wait for both processes
        backend.wait()
        frontend.wait()

    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"\nError starting application: {e}")
    finally:
        # Terminate both processes
        if backend:
            print("Stopping backend...")
            backend.terminate()
            backend.wait()
        if frontend:
            print("Stopping frontend...")
            frontend.terminate()
            frontend.wait()

        print("Application stopped.")


if __name__ == "__main__":
    # Check if we're in the project root directory
    if not Path("backend").exists() or not Path("frontend").exists():
        print("Error: Please run this script from the project root directory.")
        sys.exit(1)

    main()
