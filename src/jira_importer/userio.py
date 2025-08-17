#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: userio.py
Description: This script manages the user interactions for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import sys
import webbrowser

class UserIO:
    @staticmethod
    def get_yes_no(prompt="Do you want to continue? (yes/no): "):
        while True:
            response = input(prompt).strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                UserIO.show_message("Please enter 'yes' or 'no'.")

    @staticmethod
    def get_input(prompt="Enter value: "):
        return input(prompt)

    @staticmethod
    def show_message(message):
        print(message)

    @staticmethod
    def show_error(message):
        print(f"Error: {message}", file=sys.stderr)

    @staticmethod
    def open_browser(url):
        logging.debug(f"Opening URL in browser: {url}")
        webbrowser.open(url, new=2)
