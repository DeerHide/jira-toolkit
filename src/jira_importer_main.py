#!/usr/bin/env python

"""Entry point script for the Jira Importer application. Used by PyInstaller to create the executable.

Author:
    Julien (@tom4897)
"""

import os
import sys
import traceback


# Set up global exception handling FIRST, before any other imports
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler for uncaught exceptions."""
    sys.tracebacklimit = 5
    print("\n=== UNCAUGHT EXCEPTION ===")
    print(f"Type: {exc_type.__name__}")
    print(f"Message: {exc_value}")
    print("=" * 30)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("=" * 30)
    sys.exit(255)


# Set the global exception handler
sys.excepthook = global_exception_handler

# Set traceback limit globally
sys.tracebacklimit = 5

# Now set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from jira_importer.__main__ import main

if __name__ == "__main__":
    main()
