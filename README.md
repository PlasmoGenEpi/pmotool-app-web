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

## Building the Site

To build the web application, run:

```bash
python build_site.py
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
python simple_server.py docs
```

This will serve the `docs/` directory on port 8000 by default. You can specify a different port:

```bash
python simple_server.py docs 8080
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

## Dependencies

- `jinja2>=3.1.5` - Template engine for generating HTML
- `ruff>=0.9.8` - Python linter and formatter

The built application also includes:
- `pandas` - Data manipulation
- `fuzzywuzzy` - Fuzzy string matching
- `openpyxl` - Excel file handling
- `pmotools_python` - PMO tools library (packaged as a wheel)

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

