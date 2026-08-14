#!/usr/bin/env python
"""Test script to verify PyInstaller build includes requests dependencies.

This script tests that the PyInstaller build process correctly includes
all necessary third-party dependencies for the requests module on macOS.

Author:
    Julien (@tom4897)
"""

import sys


def test_imports() -> None:
    """Test if all required third-party modules can be imported."""
    print("[INFO] Testing third-party module imports...")

    # Focus on third-party modules that PyInstaller might miss
    required_modules = [
        "requests",
        "requests.adapters",
        "requests.auth",
        "requests.cookies",
        "requests.exceptions",
        "requests.models",
        "requests.sessions",
        "requests.structures",
        "requests.utils",
        "urllib3",
        "urllib3.util",
        "urllib3.util.retry",
        "urllib3.poolmanager",
        "urllib3.connectionpool",
        "urllib3.response",
        "urllib3.exceptions",
        "certifi",
        "charset_normalizer",
        "idna",
    ]

    failed_imports: list[str] = []

    for module in required_modules:
        try:
            __import__(module)
            print(f"[OK] {module}")
        except ImportError as e:
            print(f"[ERROR] {module}: {e}")
            failed_imports.append(module)

    if failed_imports:
        print(f"\n[ERROR] Failed to import {len(failed_imports)} modules:")
        for module in failed_imports:
            print(f"  - {module}")

    assert not failed_imports, f"Failed to import modules: {failed_imports}"
    print(f"\n[OK] All {len(required_modules)} third-party modules imported successfully!")


def test_requests_functionality() -> None:
    """Test basic requests functionality."""
    print("\n[INFO] Testing requests functionality...")

    import requests  # type: ignore[import-untyped] pylint: disable=import-outside-toplevel

    # Test basic session creation
    session = requests.Session()
    print("[OK] Session creation successful")

    # Test adapter registration
    from requests.adapters import (  # type: ignore[import-untyped] pylint: disable=import-outside-toplevel
        HTTPAdapter,
    )

    adapter = HTTPAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    print("[OK] Adapter registration successful")

    # Test auth
    from requests.auth import HTTPBasicAuth  # type: ignore[import-untyped] pylint: disable=import-outside-toplevel

    auth = HTTPBasicAuth("test", "test")
    assert auth, "Auth creation failed"
    print("[OK] Auth creation successful")


def main() -> int:
    """Run all tests."""
    print("[INFO] Testing PyInstaller build includes requests dependencies\n")

    try:
        test_imports()
        test_requests_functionality()
    except AssertionError:
        print("\n[ERROR] Some tests failed. Check the PyInstaller build configuration.")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Requests functionality test failed: {e}")
        print("\n[ERROR] Some tests failed. Check the PyInstaller build configuration.")
        return 1

    print("\n[OK] All tests passed! The PyInstaller build correctly includes requests dependencies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
