#!/usr/bin/env python3
"""
Update @stlite/browser and Pyodide version pins for the static site build.

Package list and versions come from pmotools-app/pyproject.toml (see stlite_requirements.py).
This script updates:
  - build_site.py: _STLITE_BROWSER_VERSION, _PYODIDE_VERSION
  - template.jinja: @stlite/browser CDN URLs
  - pyodide-lock-cache/v<pyodide>.json: cached lockfile for offline builds

Usage:
  uv run python scripts/sync_stlite_pins.py 1.3.0
  uv run python scripts/sync_stlite_pins.py latest --build
  uv run python scripts/sync_stlite_pins.py --pyodide-version 0.29.3 --dry-run

Requires network access. Optional: GITHUB_TOKEN for higher GitHub API rate limits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SITE = REPO_ROOT / "build_site.py"
TEMPLATE = REPO_ROOT / "template.jinja"

sys.path.insert(0, str(REPO_ROOT))
from stlite_requirements import (  # noqa: E402
    fetch_pyodide_lock,
    pyodide_lock_url,
    resolve_stlite_requirements,
)

STLITE_REPO = "whitphx/stlite"

PYODIDE_URL_RE = re.compile(
    r"https://cdn\.jsdelivr\.net/pyodide/v([\d.]+)/"
)
STLITE_CDN_RE = re.compile(
    r"https://cdn\.jsdelivr\.net/npm/@stlite/browser@[\d.]+/"
)


def http_get(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e


def github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_latest_stlite_browser_version() -> str:
    data = json.loads(
        http_get("https://registry.npmjs.org/@stlite%2fbrowser/latest")
    )
    return data["version"]


def find_stlite_commit_for_browser_version(version: str, max_pages: int = 10) -> str:
    """Return a git SHA where packages/browser/package.json matches version."""
    headers = github_headers()
    for page in range(1, max_pages + 1):
        url = (
            f"https://api.github.com/repos/{STLITE_REPO}/commits"
            f"?path=packages/browser/package.json&per_page=100&page={page}"
        )
        commits = json.loads(http_get(url, headers))
        if not commits:
            break
        for commit in commits:
            sha = commit["sha"]
            raw_url = (
                f"https://raw.githubusercontent.com/{STLITE_REPO}/"
                f"{sha}/packages/browser/package.json"
            )
            try:
                pkg = json.loads(http_get(raw_url))
            except RuntimeError:
                continue
            if pkg.get("version") == version:
                return sha
    raise LookupError(
        f"Could not find stlite commit for @stlite/browser@{version} "
        f"(searched {max_pages} pages of commits). "
        "Pass --pyodide-version manually after checking "
        "https://github.com/whitphx/stlite/blob/main/packages/kernel/src/worker.ts"
    )


def pyodide_version_from_stlite_commit(sha: str) -> str:
    raw_url = (
        f"https://raw.githubusercontent.com/{STLITE_REPO}/"
        f"{sha}/packages/kernel/src/worker.ts"
    )
    text = http_get(raw_url).decode("utf-8")
    match = PYODIDE_URL_RE.search(text)
    if not match:
        raise LookupError(f"No Pyodide CDN URL in worker.ts at commit {sha}")
    return match.group(1)


def read_current_stlite_version() -> str | None:
    text = BUILD_SITE.read_text()
    match = re.search(r'_STLITE_BROWSER_VERSION\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def update_build_site_versions(stlite_version: str, pyodide_version: str) -> str:
    text = BUILD_SITE.read_text()
    text = re.sub(
        r'_STLITE_BROWSER_VERSION\s*=\s*"[^"]*"',
        f'_STLITE_BROWSER_VERSION = "{stlite_version}"',
        text,
        count=1,
    )
    text = re.sub(
        r'_PYODIDE_VERSION\s*=\s*"[^"]*"',
        f'_PYODIDE_VERSION = "{pyodide_version}"',
        text,
        count=1,
    )
    return text


def update_template(stlite_version: str) -> str:
    text = TEMPLATE.read_text()
    replacement = f"https://cdn.jsdelivr.net/npm/@stlite/browser@{stlite_version}/"
    new_text, n = STLITE_CDN_RE.subn(replacement, text)
    if n == 0:
        raise RuntimeError("No @stlite/browser CDN URLs found in template.jinja")
    return new_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "stlite_version",
        nargs="?",
        help="@stlite/browser version (e.g. 1.3.0). Omit to use current build_site.py pin.",
    )
    parser.add_argument(
        "--stlite-version",
        dest="stlite_version_flag",
        help='Same as positional arg; use "latest" for npm latest.',
    )
    parser.add_argument(
        "--pyodide-version",
        help="Pyodide version (e.g. 0.29.3). Skips GitHub lookup for stlite worker.ts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files.",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Run build_site.py after updating pins.",
    )
    return parser.parse_args()


def resolve_stlite_version(args: argparse.Namespace) -> str:
    version = args.stlite_version_flag or args.stlite_version
    if version is None:
        current = read_current_stlite_version()
        if not current:
            raise SystemExit("No version given and _STLITE_BROWSER_VERSION not found.")
        version = current
        print(f"Using current @stlite/browser version: {version}")
    if version == "latest":
        version = fetch_latest_stlite_browser_version()
        print(f"Latest @stlite/browser on npm: {version}")
    return version


def main() -> int:
    args = parse_args()
    stlite_version = resolve_stlite_version(args)

    if args.pyodide_version:
        pyodide_version = args.pyodide_version
        print(f"Using Pyodide v{pyodide_version} (--pyodide-version)")
    else:
        print(f"Looking up stlite commit for @stlite/browser@{stlite_version}...")
        stlite_commit = find_stlite_commit_for_browser_version(stlite_version)
        print(f"  commit: {stlite_commit}")
        pyodide_version = pyodide_version_from_stlite_commit(stlite_commit)
        print(f"  Pyodide: v{pyodide_version}")

    lock_url = pyodide_lock_url(pyodide_version)
    print(f"Fetching {lock_url}")
    pyodide_lock = fetch_pyodide_lock(
        pyodide_version, use_cache=True, write_cache=not args.dry_run
    )

    requirements, warnings = resolve_stlite_requirements(
        pyodide_version, lock=pyodide_lock
    )

    print("\nResolved requirements (pmotools-app/pyproject.toml):")
    for req in requirements:
        print(f"  {req}")
    for warning in warnings:
        print(f"  warning: {warning}")

    print(f"\nUpdate {BUILD_SITE.relative_to(REPO_ROOT)} (_STLITE_* versions)")
    print(f"Update {TEMPLATE.relative_to(REPO_ROOT)}")
    print(f"Cache pyodide-lock-cache/v{pyodide_version}.json")

    if args.dry_run:
        print("\nDry run — no files written.")
        return 0

    BUILD_SITE.write_text(update_build_site_versions(stlite_version, pyodide_version))
    TEMPLATE.write_text(update_template(stlite_version))
    print("\nWrote build_site.py and template.jinja.")

    if args.build:
        print("Running build_site.py...")
        import subprocess

        subprocess.run(
            [sys.executable, str(BUILD_SITE)],
            cwd=REPO_ROOT,
            check=True,
        )

    print(
        "\nNext: load the app and confirm [pmo-deps] lines in the browser console."
    )
    if warnings:
        print(
            "Pyodide overrides some pyproject pins — expected for pandas/numpy; "
            "update pmotools-app only if you need matching native dev versions."
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LookupError, RuntimeError, ValueError, urllib.error.URLError) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from e
