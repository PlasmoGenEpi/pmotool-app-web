import jinja2
import os
import shutil

requirements = [
    "pandas",
    "fuzzywuzzy",
    "openpyxl",
    "http://0.0.0.0:8000/assets/pmotools_python-0.1.0-py3-none-any.whl"
]

entrypoint = "PMO_Builder.py"

def build_site():
    # Load the template
    template_path = os.path.join(os.path.dirname(__file__), "template.jinja")
    with open(template_path, "r") as f:
        template = jinja2.Template(f.read())

    # Load the python files in all subdirectories
    parsed_files = []
    for root, dirs, files in os.walk("pmotools-app"):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), "r") as f:
                    file_name = os.path.join(root, file).replace("pmotools-app/", "")
                    parsed_files.append({"name": file_name, "content": f"`{f.read()}`"})

    # Add the images to the parsed files
    for root, dirs, files in os.walk("pmotools-app"):
        for file in files:
            if file.endswith(".png"):
                file_name = os.path.join(root, file).replace("pmotools-app/", "")
                # copy the file to the build directory
                os.makedirs("build/images", exist_ok=True)
                shutil.copy(os.path.join(root, file), os.path.join("build/images", file))
                build_url = f"/images/{file}"
                parsed_files.append({"name": file_name, "content": {"url": build_url}})

    # Add conf files to the parsed files
    for root, dirs, files in os.walk("pmotools-app"):
        for file in files:
            if file.endswith(".json"):
                with open(os.path.join(root, file), "r") as f:
                    file_name = os.path.join(root, file).replace("pmotools-app/", "")
                    parsed_files.append({"name": file_name, "content": f"`{f.read()}`"})


    # Render the template
    rendered = template.render(files=parsed_files, requirements=requirements, entrypoint=entrypoint)

    # Write the rendered template to the output file
    os.makedirs("build", exist_ok=True)
    with open("build/index.html", "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    build_site()
