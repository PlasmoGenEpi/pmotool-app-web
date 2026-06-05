import json
import jinja2
import os
import shutil
import sys

from stlite_requirements import (
    pmotools_app_commit_hash,
    resolve_stlite_requirements,
    submodule_commit_log_snippet,
)

# Must match template.jinja (@stlite/browser version).
# Upgrade: make stlite-upgrade STLITE_VERSION=<version>
_STLITE_BROWSER_VERSION = "1.2.0"
# @stlite/browser@1.2.0 loads this Pyodide release (stlite packages/kernel/src/worker.ts).
_PYODIDE_VERSION = "0.28.2"

requirements, _requirement_warnings = resolve_stlite_requirements(_PYODIDE_VERSION)
_PMOTOOLS_APP_COMMIT = pmotools_app_commit_hash()
_COMMIT_LOG_SNIPPET = submodule_commit_log_snippet(pmotools_app_commit=_PMOTOOLS_APP_COMMIT)

entrypoint = "PMO_Builder.py"
build_dir = "docs"

# GitHub Pages serves 404.html for unknown paths (e.g. Streamlit page URLs).
_404_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Redirecting…</title>
    <script>
      (function () {
        var base = "/";
        if (location.hostname.endsWith("github.io")) {
          var segment = location.pathname.split("/").filter(Boolean)[0];
          if (segment) {
            base = "/" + segment + "/";
          }
        }
        location.replace(base);
      })();
    </script>
  </head>
  <body></body>
</html>
"""

_STATIC_ASSET_SKIP_PREFIXES = (".", "~$")


def _should_skip_static_asset(filename: str) -> bool:
    return any(filename.startswith(prefix) for prefix in _STATIC_ASSET_SKIP_PREFIXES)


def _add_url_mounted_assets(
    parsed_files: list[dict],
    *,
    source_dir: str,
    virtual_prefix: str,
    build_subdir: str,
) -> None:
    """Copy files into docs/ and register them for stlite URL mounting."""
    if not os.path.isdir(source_dir):
        return

    dest_dir = os.path.join(build_dir, build_subdir)
    os.makedirs(dest_dir, exist_ok=True)

    for filename in sorted(os.listdir(source_dir)):
        if _should_skip_static_asset(filename):
            continue
        source_path = os.path.join(source_dir, filename)
        if not os.path.isfile(source_path):
            continue

        shutil.copy(source_path, os.path.join(dest_dir, filename))
        virtual_path = f"{virtual_prefix}/{filename}"
        parsed_files.append(
            {"name": virtual_path, "content": {"url": virtual_path}}
        )


def build_site():
    # Load the template
    template_path = os.path.join(os.path.dirname(__file__), "template.jinja")
    with open(template_path, "r") as f:
        template = jinja2.Template(f.read())

    # Load the python files in all subdirectories
    parsed_files = []
    ignored_dirs = [".venv", ".github", "tests"]
    for root, dirs, files in os.walk("pmotools-app"):
        if any(dir in root for dir in ignored_dirs):
            continue
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), "r") as f:
                    file_name = os.path.join(root, file).replace("pmotools-app/", "")
                    content = f.read()
                    if file_name == "PMO_Builder.py":
                        content = _COMMIT_LOG_SNIPPET + content
                    parsed_files.append({"name": file_name, "content": json.dumps(content)})

    # Add static image assets
    _add_url_mounted_assets(
        parsed_files,
        source_dir=os.path.join("pmotools-app", "images"),
        virtual_prefix="images",
        build_subdir="images",
    )

    # Add example data files used by the app (e.g. PMO template download)
    _add_url_mounted_assets(
        parsed_files,
        source_dir=os.path.join("pmotools-app", "example_data"),
        virtual_prefix="example_data",
        build_subdir="example_data",
    )

    # Add conf files to the parsed files
    for root, dirs, files in os.walk("pmotools-app"):
        if any(dir in root for dir in ignored_dirs):
            continue
        for file in files:
            if file.endswith(".json"):
                with open(os.path.join(root, file), "r") as f:
                    file_name = os.path.join(root, file).replace("pmotools-app/", "")
                    parsed_files.append({"name": file_name, "content": json.dumps(f.read())})


    parsed_files.sort(key=lambda item: item["name"])

    # Render the template
    rendered = template.render(files=parsed_files, requirements=requirements, entrypoint=entrypoint)

    # Write the rendered template to the output file
    os.makedirs(build_dir, exist_ok=True)
    with open(os.path.join(build_dir, "index.html"), "w") as f:
        f.write(rendered)

    with open(os.path.join(build_dir, "404.html"), "w") as f:
        f.write(_404_HTML)


if __name__ == "__main__":
    print(f"pmotools-app: {_PMOTOOLS_APP_COMMIT}")
    for warning in _requirement_warnings:
        print(f"warning: {warning}", file=sys.stderr)
    build_site()
