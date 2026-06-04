# PMO Tool App Web

A web-based wrapper for the PMO Builder application, enabling it to run entirely in the browser using [stlite](https://github.com/whitphx/stlite) (Streamlit in the browser).

## Overview

This repository builds a single-page web application that runs the PMO Builder tool directly in the browser without requiring a server. The PMO Builder is a Streamlit application that helps create and manage PMO (Portable Microhaplotype Object) files from your data, organizing and storing information in a standardized format.

The built site is available at: https://plasmogenepi.github.io/pmotool-app-web/

## Project Structure

```
pmotool-app-web/
├── build_site.py          # Build script that generates the web app
├── template.jinja          # Jinja template for the HTML output
├── simple_server.py        # Local development server
├── docs/                   # Built site output (deployed to gh-pages)
│   ├── index.html
│   ├── assets/
│   └── images/
├── pmotools-app/           # Git submodule containing the PMO Builder app
└── pyproject.toml          # Python project dependencies
```

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (package manager)

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/plasmogenepi/pmotool-app-web.git
   cd pmotool-app-web
   ```

2. Initialize and update the submodule:
   ```bash
   git submodule update --init --remote
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

## Common commands

This repo includes a `Makefile` for routine tasks (requires [uv](https://github.com/astral-sh/uv)):

```bash
make install          # uv sync
make build            # generate docs/index.html
make serve            # local server on port 8000 (PORT=8080 make serve)
make help             # list all targets
```

### Dependencies

**Source of truth:** `pmotools-app/pyproject.toml` (the PMO Builder app submodule).

- **Local Streamlit:** install everything in pyproject, including `streamlit`.
- **Browser (stlite):** `build_site.py` reads the same pyproject list, skips `streamlit`, and resolves pins via `stlite_requirements.py`:
  - `pandas` / `numpy` (and any other Pyodide-built package): version from the Pyodide lockfile for `_PYODIDE_VERSION`
  - Packages with `==` in pyproject: that pin (micropip / PyPI)
  - Packages with only `>=`: version from `pmotools-app/uv.lock` (pin with `==` in pyproject when you want an explicit browser pin)

Add a new dependency in **pmotools-app**, run `uv lock` / `uv sync` there, then `make build`. If the build prints warnings that Pyodide overrides a pin (common for pandas/numpy), that is expected.

### Upgrading @stlite/browser

When bumping the in-browser Streamlit runtime:

```bash
make stlite-check STLITE_VERSION=1.3.0    # preview resolved requirements
make stlite-upgrade STLITE_VERSION=1.3.0  # update Pyodide/stlite versions + build
# or: make stlite-latest
```

This updates `_PYODIDE_VERSION`, CDN URLs, and `pyodide-lock-cache/`. See `scripts/sync_stlite_pins.py` for `--pyodide-version` and other flags.

## Building the Site

To build the web application, run:

```bash
make build
# or: uv run python build_site.py
```

This script will:
- Load the Jinja template
- Parse all Python files from the `pmotools-app` submodule
- Copy images and JSON configuration files
- Generate a single `index.html` file in the `docs/` directory
- Bundle everything needed to run the Streamlit app in the browser

## Local Development

To test the built site locally, you can use the included simple server:

```bash
make serve
# or: uv run python simple_server.py docs
```

This serves the `docs/` directory on port 8000 by default. Use a different port:

```bash
PORT=8080 make serve
```

The server includes CORS headers, making it suitable for local development and testing.

## Deployment

The built site in the `docs/` directory is designed to be deployed to GitHub Pages. Currently, deployment is manual:

1. Build the site: `python build_site.py`
2. Commit and push the changes in the `docs/` directory to the `gh-pages` branch

**Note:** Automated deployment via GitHub Actions is not currently set up. To enable automated deployment, you would need to create a GitHub Actions workflow.

## How It Works

The build process creates a single HTML file that uses stlite to run the Streamlit application in the browser:

1. **Template**: The `template.jinja` file defines the HTML structure and includes the stlite JavaScript library
2. **File Bundling**: All Python files, images, and configuration files from `pmotools-app` are embedded into the HTML
3. **Dependencies**: Python packages (pandas, fuzzywuzzy, openpyxl, and the pmotools_python wheel) are loaded from CDN or the assets directory
4. **Runtime**: stlite runs the Streamlit app client-side, executing Python code in the browser using Pyodide

## Submodule Management

The `pmotools-app` submodule contains the actual PMO Builder application. To update it to the latest version:

```bash
git submodule update --remote pmotools-app
```

After updating, commit the change in the parent repository:

```bash
git add pmotools-app
git commit -m "Update pmotools-app submodule to latest version"
```

## Build tooling

- `jinja2>=3.1.5` - Template engine for generating HTML
- `ruff>=0.9.8` - Python linter and formatter

Runtime Python packages for the web app come from `pmotools-app/pyproject.toml` (see **Dependencies** above).

## License

See the LICENSE file in the `pmotools-app` submodule for license information.

## Contributing

Contributions are welcome! Please ensure that:
1. The submodule is updated if changes are needed in the PMO Builder app
2. The site is rebuilt after making changes
3. Tests pass (if applicable)

## Related Projects

- [pmotools-app](https://github.com/plasmogenepi/pmotools-app) - The main PMO Builder Streamlit application
- [stlite](https://github.com/whitphx/stlite) - Streamlit in the browser

