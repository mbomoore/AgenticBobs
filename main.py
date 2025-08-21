#!/usr/bin/env python3
"""Main entry point for Agentic Process Automation.

This is a convenience script that launches the Streamlit application.
"""

import sys
import subprocess

def main():
    """Launch the Streamlit application."""
    try:
        # Launch the Streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "src/agentic_process_automation/app/main.py"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
