"""PyInstaller hook for requests library."""

from PyInstaller.utils.hooks import collect_all  # type: ignore[import-untyped]

datas, binaries, hiddenimports = collect_all("requests")

hiddenimports += [
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
    "certifi",
    "charset_normalizer",
    "idna",
]
