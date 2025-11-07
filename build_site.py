import jinja2
import os
import shutil
import zipfile

requirements = [
    "pandas",
    "fuzzywuzzy",
    "openpyxl",
]

entrypoint = "PMO_Builder.py"
build_dir = "docs"


def _find_latest_pmotools_wheel(wheel_dir: str) -> str | None:
    if not os.path.isdir(wheel_dir):
        return None

    candidates = [
        file
        for file in os.listdir(wheel_dir)
        if file.startswith("pmotools") and file.endswith(".whl")
    ]
    if not candidates:
        return None

    # Pick the most recently modified wheel
    return max(candidates, key=lambda file: os.path.getmtime(os.path.join(wheel_dir, file)))


def _parse_wheel_version(wheel_name: str) -> str:
    try:
        after_prefix = wheel_name.split("pmotools-", 1)[1]
        return after_prefix.split("-", 1)[0]
    except Exception:
        return "0.0.0"


def build_site():
    # Load the template
    template_path = os.path.join(os.path.dirname(__file__), "template.jinja")
    with open(template_path, "r", encoding="utf-8") as f:
        template = jinja2.Template(f.read())

    # Ensure the app directory is clean
    app_dir = os.path.join(build_dir, "app")
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir)

    parsed_files = []

    # Copy Python files from the submodule
    for root, _, files in os.walk("pmotools-app"):
        for file in files:
            if not file.endswith(".py"):
                continue

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, "pmotools-app")
            dst_path = os.path.join(app_dir, rel_path)

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy(src_path, dst_path)

            file_name = rel_path.replace("\\", "/")
            parsed_files.append({"name": file_name, "url": f"app/{file_name}"})

    # Copy JSON files from the submodule
    for root, _, files in os.walk("pmotools-app"):
        for file in files:
            if not file.endswith(".json"):
                continue

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, "pmotools-app")
            dst_path = os.path.join(app_dir, rel_path)

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy(src_path, dst_path)

            file_name = rel_path.replace("\\", "/")
            parsed_files.append({"name": file_name, "url": f"app/{file_name}"})

    # Copy images for static serving and mount them into the stlite filesystem
    for target in (os.path.join(build_dir, "images"), os.path.join(build_dir, "app")):
        if os.path.exists(target):
            # Only remove image subdirectories to avoid wiping the entire app directory
            images_subdir = os.path.join(target, "images")
            if os.path.exists(images_subdir):
                shutil.rmtree(images_subdir)

    for root, _, files in os.walk("pmotools-app"):
        for file in files:
            if not file.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, "pmotools-app")
            rel_path = rel_path.replace("\\", "/")

            # Copy for static serving (e.g., for direct HTTP access)
            static_dst = os.path.join(build_dir, rel_path)
            os.makedirs(os.path.dirname(static_dst), exist_ok=True)
            shutil.copy(src_path, static_dst)

            # Copy into the app directory so it can be mounted into the Pyodide filesystem
            app_dst = os.path.join(app_dir, rel_path)
            os.makedirs(os.path.dirname(app_dst), exist_ok=True)
            shutil.copy(src_path, app_dst)

            parsed_files = [
                file_dict
                for file_dict in parsed_files
                if file_dict["name"] != rel_path
            ]
            parsed_files.append({"name": rel_path, "url": f"app/{rel_path}", "binary": True})

    # Extract the pmotools wheel into site-packages
    wheel_dir = os.path.join(build_dir, "assets")
    wheel_name = _find_latest_pmotools_wheel(wheel_dir)

    if wheel_name is None:
        raise FileNotFoundError("No pmotools wheel found in docs/assets")

    wheel_path = os.path.join(wheel_dir, wheel_name)
    pmotools_version = _parse_wheel_version(wheel_name)

    with zipfile.ZipFile(wheel_path, "r") as wheel:
        for member in wheel.namelist():
            if not member.startswith("pmotools/") or member.endswith("/"):
                continue

            dst_path = os.path.join(app_dir, "site-packages", member)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            with wheel.open(member) as source, open(dst_path, "wb") as target:
                target.write(source.read())

            file_name = member.replace("\\", "/")
            parsed_files.append({"name": file_name, "url": f"app/site-packages/{file_name}"})

    # Ensure site-packages/__init__.py exists
    site_packages_dir = os.path.join(app_dir, "site-packages")
    os.makedirs(site_packages_dir, exist_ok=True)
    site_packages_init = os.path.join(site_packages_dir, "__init__.py")
    if not os.path.exists(site_packages_init):
        with open(site_packages_init, "w", encoding="utf-8") as f:
            f.write("")
    parsed_files = [
        file_dict
        for file_dict in parsed_files
        if file_dict["name"] != "site-packages/__init__.py"
    ]
    parsed_files.append({"name": "site-packages/__init__.py", "url": "app/site-packages/__init__.py"})

    # Force pmotools.__version__ to be the wheel version
    pmotools_init_path = os.path.join(app_dir, "site-packages", "pmotools", "__init__.py")
    if os.path.exists(pmotools_init_path):
        with open(pmotools_init_path, "r", encoding="utf-8") as f:
            init_content = f.read()

        version_line = f'__version__ = "{pmotools_version}"  # Set version for browser environment\n'
        if version_line not in init_content:
            init_content = init_content.rstrip() + "\n" + version_line

        with open(pmotools_init_path, "w", encoding="utf-8") as f:
            f.write(init_content)

        # Update parsed files entry (duplicate entries avoided below)
        parsed_files = [
            file_dict
            for file_dict in parsed_files
            if not (file_dict["name"] == "pmotools/__init__.py")
        ]
        parsed_files.append({"name": "pmotools/__init__.py", "url": "app/site-packages/pmotools/__init__.py"})

    # Create a setup helper to inject site-packages onto sys.path
    setup_file_path = os.path.join(app_dir, "_setup_pmotools.py")
    with open(setup_file_path, "w", encoding="utf-8") as f:
        f.write(
            """import sys
import os

site_packages = os.path.join(os.path.dirname(__file__), 'site-packages')
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
"""
        )

    parsed_files = [
        file_dict
        for file_dict in parsed_files
        if file_dict["name"] != "_setup_pmotools.py"
    ]
    parsed_files.append({"name": "_setup_pmotools.py", "url": "app/_setup_pmotools.py"})

    # Ensure PMO_Builder imports the setup helper first
    pmo_builder_path = os.path.join(app_dir, "PMO_Builder.py")
    if os.path.exists(pmo_builder_path):
        with open(pmo_builder_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "import _setup_pmotools" not in content:
            content = "import _setup_pmotools\n" + content
            with open(pmo_builder_path, "w", encoding="utf-8") as f:
                f.write(content)

    # Render the template
    rendered = template.render(files=parsed_files, requirements=requirements, entrypoint=entrypoint)

    # Write the rendered template to the output file
    os.makedirs(build_dir, exist_ok=True)
    with open(os.path.join(build_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(rendered)

    # Write the GitHub Pages configuration so Jekyll keeps files that start with underscores
    config_path = os.path.join(build_dir, "_config.yml")
    config_contents = """include:
  - "app/_setup_pmotools.py"
  - "app/site-packages/__init__.py"
  - "app/site-packages/pmotools/**/*"
"""
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_contents)


if __name__ == "__main__":
    build_site()
