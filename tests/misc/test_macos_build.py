#!/usr/bin/env python
"""Test script to verify PyInstaller build includes requests dependencies.

This script tests that the PyInstaller build process correctly includes
all necessary third-party dependencies for the requests module on macOS.

Author:
    Julien (@tom4897)
"""

import sys


def test_imports():
    """Test if all required third-party modules can be imported."""
    print("🧪 Testing third-party module imports...")

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

    failed_imports = []

    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)

    if failed_imports:
        print(f"\n❌ Failed to import {len(failed_imports)} modules:")
        for module in failed_imports:
            print(f"  - {module}")
        return False
    print(f"\n✅ All {len(required_modules)} third-party modules imported successfully!")
    return True


def test_requests_functionality():
    """Test basic requests functionality."""
    print("\n🌐 Testing requests functionality...")

    try:
        import requests  # type: ignore[import-untyped] pylint: disable=import-outside-toplevel

        # Test basic session creation
        session = requests.Session()
        print("✅ Session creation successful")

        # Test adapter registration
        from requests.adapters import (  # type: ignore[import-untyped] pylint: disable=import-outside-toplevel
            HTTPAdapter,
        )

        adapter = HTTPAdapter()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        print("✅ Adapter registration successful")

        # Test auth
        from requests.auth import HTTPBasicAuth  # type: ignore[import-untyped] pylint: disable=import-outside-toplevel

        auth = HTTPBasicAuth("test", "test")
        print("✅ Auth creation successful")

        return True

    except Exception as e:
        print(f"❌ Requests functionality test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🔧 Testing PyInstaller build includes requests dependencies\n")

    # Test imports
    imports_ok = test_imports()

    # Test functionality
    functionality_ok = test_requests_functionality()

    if imports_ok and functionality_ok:
        print("\n🎉 All tests passed! The PyInstaller build correctly includes requests dependencies.")
        return 0
    print("\n❌ Some tests failed. Check the PyInstaller build configuration.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
