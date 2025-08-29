#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Entry point script for the Jira Importer application.
Used by PyInstaller to create the executable.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from jira_importer.__main__ import main

if __name__ == "__main__":
    main()
