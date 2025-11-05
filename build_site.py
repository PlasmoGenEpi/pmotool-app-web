import jinja2
import os
import shutil
import zipfile

requirements = [
    "pandas",
    "fuzzywuzzy",
    "openpyxl",
    # pmotools is extracted from wheel and included directly in filesystem
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

    # Extract pmotools package from wheel and add to filesystem
    # This avoids installing dependencies that are already in requirements
    wheel_path = os.path.join(build_dir, "assets", "pmotools-0.1.0-py3-none-any.whl")
    if os.path.exists(wheel_path):
        with zipfile.ZipFile(wheel_path, 'r') as wheel:
            # Extract only pmotools package files (not dist-info)
            for member in wheel.namelist():
                if member.startswith('pmotools/') and not member.endswith('/'):
                    # Extract to app directory (which is in Python path in stlite)
                    # Store as site-packages/pmotools/... for proper Python import
                    relative_path = member  # This is already pmotools/...
                    dst_path = os.path.join(app_dir, "site-packages", relative_path)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # Extract and write the file
                    with wheel.open(member) as source:
                        with open(dst_path, 'wb') as target:
                            target.write(source.read())
                    
                    # Add to parsed files for template
                    file_name = relative_path.replace("\\", "/")
                    parsed_files.append({"name": file_name, "url": f"app/site-packages/{file_name}"})
        
        # Patch pmotools/__init__.py to ensure __version__ is defined
        # Since pmotools isn't installed via pip in stlite, importlib.metadata won't work
        # We need to set __version__ directly
        pmotools_init = os.path.join(app_dir, "site-packages", "pmotools", "__init__.py")
        if os.path.exists(pmotools_init):
            with open(pmotools_init, 'r') as f:
                content = f.read()
            
            # Replace the try/except version lookup block with a simple hardcoded version
            # Find the try block that tries to get version from importlib.metadata
            import re
            
            # Pattern to match: try: ... __version__ = version("pmotools") ... except: __version__ = "0+local"
            # Replace entire block with just: __version__ = "0.1.0"
            pattern = r'try:\s*# Use the installed distribution name.*?__version__ = "0\+local"'
            
            # Try regex replacement first
            new_content = re.sub(
                pattern,
                '__version__ = "0.1.0"  # Set version for browser environment',
                content,
                flags=re.DOTALL
            )
            
            # If regex didn't work, do line-by-line replacement
            if new_content == content:
                lines = content.split('\n')
                new_lines = []
                skip_block = False
                
                for i, line in enumerate(lines):
                    # Detect start of version try block
                    if 'try:' in line and i + 1 < len(lines) and '# Use the installed distribution name' in lines[i + 1]:
                        skip_block = True
                        new_lines.append('__version__ = "0.1.0"  # Set version for browser environment')
                        continue
                    elif skip_block and 'except PackageNotFoundError:' in line:
                        skip_block = False
                        continue
                    elif skip_block:
                        continue
                    else:
                        new_lines.append(line)
                
                new_content = '\n'.join(new_lines)
            
            # Final fallback: replace any remaining "0+local" with "0.1.0"
            new_content = new_content.replace('__version__ = "0+local"', '__version__ = "0.1.0"')
            
            # Ensure __version__ exists somewhere
            if '__version__' not in new_content:
                new_content += '\n__version__ = "0.1.0"  # Set version for browser environment\n'
            
            with open(pmotools_init, 'w') as f:
                f.write(new_content)
        
        # Create __init__.py for site-packages if needed
        site_packages_init = os.path.join(app_dir, "site-packages", "__init__.py")
        if not os.path.exists(site_packages_init):
            os.makedirs(os.path.dirname(site_packages_init), exist_ok=True)
            with open(site_packages_init, 'w') as f:
                f.write("")
        
        # Create a setup file to add site-packages to sys.path
        setup_file = os.path.join(app_dir, "_setup_pmotools.py")
        with open(setup_file, 'w') as f:
            f.write("""import sys
import os
# Add site-packages to Python path so pmotools can be imported
site_packages = os.path.join(os.path.dirname(__file__), 'site-packages')
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
""")
        # Add setup file to parsed files
        parsed_files.append({"name": "_setup_pmotools.py", "url": "app/_setup_pmotools.py"})
        
        # Modify PMO_Builder.py to import setup first
        pmo_builder_path = os.path.join(app_dir, "PMO_Builder.py")
        if os.path.exists(pmo_builder_path):
            with open(pmo_builder_path, 'r') as f:
                content = f.read()
            # Add import at the very beginning if not already present
            if "import _setup_pmotools" not in content:
                content = "import _setup_pmotools\n" + content
                with open(pmo_builder_path, 'w') as f:
                    f.write(content)

    # Render the template
    rendered = template.render(files=parsed_files, requirements=requirements, entrypoint=entrypoint)

    # Write the rendered template to the output file
    os.makedirs(build_dir, exist_ok=True)
    with open(os.path.join(build_dir, "index.html"), "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    build_site()
