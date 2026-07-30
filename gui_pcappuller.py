#!/usr/bin/env python3
"""PyInstaller entry point for the PCAPpuller GUI.

The implementation lives in pcappuller/gui.py; this shim exists so the
packaging scripts (packaging/*/build_pyinstaller.*) keep a stable target.
"""
from pcappuller.gui import main

if __name__ == "__main__":
    main()
