"""
script name: sink_utils.py
description: This script contains the utility functions.
author: Julien (@tom4897)
license: MIT
date: 2025
"""

from ..models import ProcessorResult

def times60_estimates_inplace(result: ProcessorResult) -> None:
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
