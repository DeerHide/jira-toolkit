#!/usr/bin/env python
"""Install all project requirements.

Regenerates requirements.lock from requirements.in (if pip-tools available),
then installs all requirements.

Usage:
    python scripts/install_requirements.py

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# constants
PROJECT_ROOT = Path(__file__).parent.parent  # assuming we're in scripts
REQS_IN = "requirements.in"
REQS_LOCK = "requirements.lock"
REQS_TXT = "requirements.txt"


def main() -> int:
    """Install all project requirements."""
    requirements_in = PROJECT_ROOT / REQS_IN
    requirements_lock = PROJECT_ROOT / REQS_LOCK
    requirements_txt = PROJECT_ROOT / REQS_TXT

    # generate lock file if pip-tools is available
    if requirements_in.exists():
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "compile", "--output-file", str(requirements_lock), str(requirements_in)],
                check=True,
                capture_output=True,
            )
            print("✓ Regenerated requirements.lock")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠ Skipping lock file regeneration (pip-tools not available)")

    # installl requirements
    if requirements_lock.exists():
        requirements_file = requirements_lock
    elif requirements_txt.exists():
        requirements_file = requirements_txt
    else:
        print("⚠ No requirements file found (requirements.lock or requirements.txt)")
        return 1

    print(f"📦 Installing requirements from {requirements_file.name}...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], check=True)
        print("✓ Requirements installed successfully")
        return 0
    except subprocess.CalledProcessError:
        print("⚠ Failed to install requirements")
        return 1


if __name__ == "__main__":
    sys.exit(main())
