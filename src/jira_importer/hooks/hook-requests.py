"""PyInstaller hook for requests library."""

from PyInstaller.utils.hooks import collect_all  # type: ignore[import-untyped]

datas, binaries, hiddenimports = collect_all("requests")

# Essential requests and related modules for macOS compatibility
hiddenimports += [
    # Core requests modules
    "requests",
    "requests.adapters",
    "requests.auth",
    "requests.cookies",
    "requests.exceptions",
    "requests.models",
    "requests.sessions",
    "requests.structures",
    "requests.utils",

    # urllib3 modules
    "urllib3",
    "urllib3.util",
    "urllib3.util.retry",
    "urllib3.poolmanager",
    "urllib3.connectionpool",
    "urllib3.response",
    "urllib3.exceptions",

    # Third-party dependencies
    "certifi",
    "charset_normalizer",
    "idna",
]
