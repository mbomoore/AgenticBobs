#!/usr/bin/env python3
"""
Development server for The Bobs 2.0 backend.
Run this script to start the FastAPI server with hot reload.
"""

import uvicorn
import sys
import os

# Add the parent directory to the Python path so we can import from core and marvin_scripts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[".", "../core", "../marvin_scripts"],
        log_level="info"
    )
