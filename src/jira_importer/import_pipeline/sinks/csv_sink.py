"""
script name: csv_sink.py
description: CSV sink: write Jira-ready CSV output.
author: Julien (@tom4897)
license: MIT
date: 2025
"""
from __future__ import annotations

# NOTE, Jira CLoud: Some Jira Cloud users are affected by the historical "divide by 60" behavior. The fix (*60) will be implemented in this sink.
#   if config.get("jira.cloud.estimate.multiply_by_60", False):
#       row[estimate_index] = str(int(row[estimate_index]) * 60)

import csv
from pathlib import Path
from typing import Any

from ..models import ProcessorResult
from ..config_view import ConfigView


def write_csv(
    result: ProcessorResult,
    out_path: str | Path,
    config: object | None = None,
    *,
    encoding: str = "utf-8",
    newline: str = "",
) -> Path:
    """
    Write the processed rows as a CSV with the given header.

    Notes:
      - Estimates are written in canonical SECONDS as produced by the pipeline.
      - If your target (e.g., Jira Cloud CSV import) needs the historical '×60' quirk,
        make it config-driven here (NOT in rules/fixes):

            if cfg.get("jira.cloud.estimate.multiply_by_60", False):
                _times60_estimates_inplace(result)

    """
    out_path = Path(out_path)
    #out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = ConfigView(config) if config is not None else None

    # Optional: apply Jira Cloud quirk here, not in rules/fixes.
    if cfg and cfg.get("jira.cloud.estimate.multiply_by_60", False):
        _times60_estimates_inplace(result)

    with out_path.open("w", encoding=encoding, newline=newline) as fh:
        w = csv.writer(fh)
        w.writerow(result.header)
        for row in result.rows:
            w.writerow(row)

    return out_path

# TODO: Create sink helpers and move this there
def _times60_estimates_inplace(result: ProcessorResult) -> None:
    """
    Multiply estimate/original estimate columns by 60 in-place for compatibility
    with Jira Cloud CSV import behavior. Config-driven; called from write_csv().
    """
    idx = result.indices
    if not idx:
        return

    cols = []
    if idx.estimate is not None:
        cols.append(idx.estimate)
    if idx.origest is not None:
        cols.append(idx.origest)

    if not cols:
        return

    for r in result.rows:
        for c in cols:
            try:
                if r[c] is None or str(r[c]).strip() == "":
                    continue
                r[c] = str(int(float(str(r[c]))) * 60)
            except Exception:
                # Leave as-is if non-numeric
                pass
