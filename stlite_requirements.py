"""
Resolve stlite/micropip requirements from pmotools-app/pyproject.toml.

pmotools-app/pyproject.toml is the source of truth for which packages the app needs.
Versions are chosen as follows:

- streamlit: excluded (provided by @stlite/browser)
- Package in the active Pyodide lockfile: use the lock version (WASM wheel)
- Package with ``==`` in pyproject: use that pin (PyPI / micropip)
- Package with only ``>=`` / ``>``: use the version resolved in pmotools-app/uv.lock
- Otherwise: pass through unpinned (package name only)

Run ``make stlite-upgrade`` after bumping @stlite/browser to refresh _PYODIDE_VERSION and
the cached lockfile under pyodide-lock-cache/.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PMOTOOLS_APP = REPO_ROOT / "pmotools-app"
PYPROJECT = PMOTOOLS_APP / "pyproject.toml"
UV_LOCK = REPO_ROOT / "pmotools-app" / "uv.lock"
LOCK_CACHE_DIR = REPO_ROOT / "pyodide-lock-cache"

# Bundled by stlite; not installed via micropip requirements.
STLITE_EXCLUDED = frozenset({"streamlit"})


def package_name(requirement: str) -> str:
    return re.split(r"[<>=!~\[]", requirement.strip())[0].strip().lower()


def read_pyproject_dependencies() -> list[tuple[str, str]]:
    """Return (name, original_spec) in pyproject declaration order."""
    data = tomllib.loads(PYPROJECT.read_text())
    deps: list[tuple[str, str]] = []
    for spec in data["project"]["dependencies"]:
        name = package_name(spec)
        deps.append((name, spec.strip()))
    return deps


def stlite_package_names() -> list[str]:
    return [name for name, _ in read_pyproject_dependencies() if name not in STLITE_EXCLUDED]


def version_from_uv_lock(package: str) -> str | None:
    if not UV_LOCK.exists():
        return None
    text = UV_LOCK.read_text()
    pattern = (
        rf'^name = "{re.escape(package)}"\s*\n'
        r"(?:.*\n)*?"
        r'^version = "([^"]+)"'
    )
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def pyodide_lock_url(version: str) -> str:
    return f"https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json"


def fetch_pyodide_lock(
    pyodide_version: str,
    *,
    use_cache: bool = True,
    write_cache: bool = True,
) -> dict:
    cache_path = LOCK_CACHE_DIR / f"v{pyodide_version}.json"
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text())
    with urllib.request.urlopen(pyodide_lock_url(pyodide_version), timeout=60) as resp:
        data = json.loads(resp.read())
    if write_cache:
        LOCK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def pyodide_lock_versions(lock: dict) -> dict[str, str]:
    return {
        pkg["name"]: pkg["version"]
        for pkg in lock.get("packages", {}).values()
        if "name" in pkg and "version" in pkg
    }


def resolve_stlite_requirements(
    pyodide_version: str,
    *,
    lock: dict | None = None,
) -> tuple[list[str], list[str]]:
    """
    Return (requirements, warnings) for micropip.

    warnings note when Pyodide overrides a pyproject ``==`` pin.
    """
    if lock is None:
        lock = fetch_pyodide_lock(pyodide_version)
    lock_versions = pyodide_lock_versions(lock)

    requirements: list[str] = []
    warnings: list[str] = []

    for name, spec in read_pyproject_dependencies():
        if name in STLITE_EXCLUDED:
            continue

        if name in lock_versions:
            pyodide_ver = lock_versions[name]
            requirements.append(f"{name}=={pyodide_ver}")
            if "==" in spec:
                local_ver = spec.split("==", 1)[1].strip()
                if local_ver != pyodide_ver:
                    warnings.append(
                        f"{name}: pyproject pins {local_ver}, stlite uses Pyodide {pyodide_ver}"
                    )
            continue

        if "==" in spec:
            requirements.append(f"{name}=={spec.split('==', 1)[1].strip()}")
            continue

        if re.search(r"[><=]", spec):
            resolved = version_from_uv_lock(name)
            if not resolved:
                raise ValueError(
                    f"{name!r} has {spec!r} in pyproject.toml but no entry in "
                    f"{UV_LOCK.relative_to(REPO_ROOT)}. Pin with == or run `uv lock` in pmotools-app."
                )
            requirements.append(f"{name}=={resolved}")
            continue

        requirements.append(name)

    return requirements, warnings


def pmotools_app_commit_hash() -> str:
    """Return the checked-out pmotools-app submodule commit, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PMOTOOLS_APP), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def version_log_snippet(*, pmotools_app_commit: str) -> str:
    names = stlite_package_names()
    pkg_tuple = ", ".join(repr(n) for n in names)
    return f'''\
print("[pmo-build] pmotools-app={pmotools_app_commit}", flush=True)

import importlib.metadata

def _log_installed_package_versions():
    for pkg in ({pkg_tuple}):
        try:
            print(f"[pmo-deps] {{pkg}}=={{importlib.metadata.version(pkg)}}", flush=True)
        except importlib.metadata.PackageNotFoundError:
            print(f"[pmo-deps] {{pkg}}: not installed", flush=True)

_log_installed_package_versions()

'''
