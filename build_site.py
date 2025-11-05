import jinja2
import os
import shutil

requirements = [
    "pandas",
    "fuzzywuzzy",
    "openpyxl",
    # TODO: remove this once the package is published
    "https://plasmogenepi.github.io/pmotool-app-web/assets/pmotools_python-0.1.0-py3-none-any.whl"
]

entrypoint = "PMO_Builder.py"
build_dir = "docs"

def build_site():
    # Load the template
    template_path = os.path.join(os.path.dirname(__file__), "template.jinja")
    with open(template_path, "r") as f:
        template = jinja2.Template(f.read())

    # Copy Python and JSON files from submodule to docs/app/ directory
    app_dir = os.path.join(build_dir, "app")
    parsed_files = []
    
    # Copy Python files
    for root, dirs, files in os.walk("pmotools-app"):
        for file in files:
            if file.endswith(".py"):
                src_path = os.path.join(root, file)
                # Preserve directory structure relative to pmotools-app
                rel_path = os.path.relpath(src_path, "pmotools-app")
                dst_path = os.path.join(app_dir, rel_path)
                
                # Create destination directory
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy(src_path, dst_path)
                
                # Store file path for template
                file_name = rel_path.replace("\\", "/")  # Normalize path separators
                parsed_files.append({"name": file_name, "url": f"app/{file_name}"})

    # Copy JSON config files
    for root, dirs, files in os.walk("pmotools-app"):
        for file in files:
            if file.endswith(".json"):
                src_path = os.path.join(root, file)
                # Preserve directory structure relative to pmotools-app
                rel_path = os.path.relpath(src_path, "pmotools-app")
                dst_path = os.path.join(app_dir, rel_path)
                
                # Create destination directory
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy(src_path, dst_path)
                
                # Store file path for template
                file_name = rel_path.replace("\\", "/")  # Normalize path separators
                parsed_files.append({"name": file_name, "url": f"app/{file_name}"})



    # Render the template
    rendered = template.render(files=parsed_files, requirements=requirements, entrypoint=entrypoint)

    # Write the rendered template to the output file
    os.makedirs(build_dir, exist_ok=True)
    with open(os.path.join(build_dir, "index.html"), "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    build_site()
