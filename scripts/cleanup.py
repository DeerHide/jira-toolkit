#!/usr/bin/env python3
"""
Cleanup utility for the repository.

Note:
- You need to run this script with --just-do-it or -y to actually remove the files.

Removes:
- All __pycache__ directories
- All .pyc/.pyo files
- All .log files
- Empties src/jira_importer/jira_importer_logs directory (keeps the folder)

Usage:
  python scripts/cleanup.py [--dry-run] [--verbose] [--root PATH] [--just-do-it]
  python scripts/cleanup.py -y
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path
from typing import Iterable

def iter_dirs_by_name(root: Path, name: str) -> Iterable[Path]:
    for path in root.rglob(name):
        if path.is_dir() and path.name == name:
            yield path


def iter_files_by_suffixes(root: Path, suffixes: tuple[str, ...]) -> Iterable[Path]:
    for suffix in suffixes:
        for path in root.rglob(f"*{suffix}"):
            if path.is_file():
                yield path


def remove_path(path: Path, dry_run: bool, verbose: bool, vverbose: bool) -> None:
    if not path.exists():
        return
    if verbose:
        action = "DRY-RUN remove" if dry_run else "Removing"
        print(f"{action}: {path}")
    if dry_run:
        return
    try:
        if vverbose:
            print(f"Removing: {path}")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to remove {path}: {exc}")


def empty_directory_contents(dir_path: Path, dry_run: bool, vverbose: bool, verbose: bool) -> None:
    if vverbose:
        print(f"Emptying directory contents: {dir_path}")
    if not dir_path.exists() or not dir_path.is_dir():
        return
    for child in dir_path.iterdir():
        remove_path(child, dry_run=dry_run, vverbose=vverbose, verbose=verbose)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup __pycache__, *.pyc, *.pyo, *.log files and logs directory contents.\nYou need to run this script with --just-do-it to actually remove the files.")
    parser.add_argument("--just-do-it", "-y", action="store_true", default=False, help="Runs the cleanup")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show what would be removed without deleting anything")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each path as it's processed")
    parser.add_argument("--vverbose", "-vv", action="store_true", default=False, help="Print each path as it's processed")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Root directory to clean (defaults to repo root)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root: Path = args.root

    dry_run: bool = args.dry_run
    verbose: bool = args.verbose or args.vverbose
    vverbose: bool = args.vverbose
    just_do_it: bool = args.just_do_it
    if not just_do_it and not dry_run:
        print("You need to run this script with --just-do-it to actually remove the files.")
        return 1
    if just_do_it and dry_run:
        print("You cannot run this script with --just-do-it and --dry-run at the same time.")
        return 1

    if verbose:
        print(f"Cleaning root: {root}")

    for cache_dir in iter_dirs_by_name(root, "__pycache__"):
        remove_path(cache_dir, dry_run=dry_run, vverbose=vverbose, verbose=verbose)

    for file_path in iter_files_by_suffixes(root, (".pyc", ".pyo")):
        remove_path(file_path, dry_run=dry_run, vverbose=vverbose, verbose=verbose)

    for log_file in iter_files_by_suffixes(root, (".log",)):
        remove_path(log_file, dry_run=dry_run, vverbose=vverbose, verbose=verbose)

    logs_dir = root / "src" / "jira_importer" / "jira_importer_logs"
    if logs_dir.exists() and logs_dir.is_dir():
        if verbose:
            print(f"Clearing logs directory contents: {logs_dir}")
        empty_directory_contents(logs_dir, dry_run=dry_run, vverbose=vverbose, verbose=verbose)

    if verbose:
        print("Cleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
