#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: fileops.py
Description: This script manages the file operations for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import os
import csv
import pandas as pd
from tqdm import tqdm


class FileManager:
    def __init__(self, artifact_manager=None):
        self.artifact_manager = artifact_manager

    def write_csv_file(self, output_file, csv_file, is_artifact=True):
        with open(output_file, mode='w', newline='', encoding='utf-8', errors='ignore') as f:
            writer = csv.writer(f)
            writer.writerow(csv_file.header)
            for row in tqdm(csv_file.data, desc="Writing items", unit="items", total=len(csv_file.data)):
                writer.writerow(row)
        logging.info(f"CSV file written: {output_file}")
        if self.artifact_manager and is_artifact:
            self.artifact_manager.add(output_file)

    def xlsx_to_csv(self, xlsx_file, csv_file, is_artifact=True):
        excel_content = pd.read_excel(xlsx_file, sheet_name=0, engine='openpyxl')
        for col in excel_content.select_dtypes(include=['float']):
            excel_content[col] = excel_content[col].astype('Int64')
        excel_content.to_csv(csv_file, index=False)
        logging.info(f"Converted XLSX to CSV: {csv_file}")
        if self.artifact_manager and is_artifact:
            self.artifact_manager.add(csv_file)

    def generate_output_filename(self, input_file, file_extension='', suffix=""):
        base_name, ext = os.path.splitext(input_file)
        if file_extension:
            ext = file_extension
        output_file = f"{base_name}{suffix}.{ext.lstrip('.')}"
        logging.debug(f"Output file: {output_file}")
        return output_file

    def delete_file(self, file_path):
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to delete file '{file_path}': {e}")
        else:
            logging.warning(f"File '{file_path}' does not exist.")
