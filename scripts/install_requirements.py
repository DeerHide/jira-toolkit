#!/usr/bin/env python
"""Install project dependencies via Poetry.

Installs runtime deps, the ``dev`` extra, and the non-optional ``pyinstaller``
group so every developer machine can build binaries.

Usage:
    python scripts/install_requirements.py

Equivalent to:
    poetry install --extras dev

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    """Install dependencies with Poetry."""
    poetry = shutil.which("poetry")
    if poetry is None:
        print("[ERROR] Poetry not found on PATH. Install it from https://python-poetry.org/docs/#installation")
        return 1

    cmd = [poetry, "install", "--extras", "dev"]
    print(f"[INFO] Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    except subprocess.CalledProcessError:
        print("[ERROR] Poetry install failed")
        return 1

    print("[OK] Dependencies installed successfully (includes PyInstaller build tooling)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
