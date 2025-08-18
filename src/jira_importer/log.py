#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: log.py
Description: This script contains the logging configuration for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import os
import colorlog
from utils import resource_path


def is_debug_mode():
        debug_file_path = resource_path('.debug')
        debug_mode = os.path.isfile(debug_file_path)
        return debug_mode

def setup_logger():
    if is_debug_mode():
        logginglevel = logging.DEBUG
    else:
        logginglevel = logging.INFO
    if not logging.getLogger().hasHandlers():
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            "%(log_color)s %(levelname)s: %(message)s",
            datefmt="",
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        ))
        logging.basicConfig(level=logginglevel, handlers=[handler])