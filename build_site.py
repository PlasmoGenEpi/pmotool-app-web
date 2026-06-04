import jinja2
import os
import shutil
import tokenize
import io

from stlite_requirements import (
    pmotools_app_commit_hash,
    pyodide_lock_url,
    resolve_stlite_requirements,
    version_log_snippet,
)

# Must match template.jinja (@stlite/browser version).
# Upgrade: make stlite-upgrade STLITE_VERSION=<version>
_STLITE_BROWSER_VERSION = "1.2.0"
# @stlite/browser@1.2.0 loads this Pyodide release (stlite packages/kernel/src/worker.ts).
_PYODIDE_VERSION = "0.28.2"
_PYODIDE_LOCK_URL = pyodide_lock_url(_PYODIDE_VERSION)

requirements, _requirement_warnings = resolve_stlite_requirements(_PYODIDE_VERSION)
_PMOTOOLS_APP_COMMIT = pmotools_app_commit_hash()
_VERSION_LOG_SNIPPET = version_log_snippet(pmotools_app_commit=_PMOTOOLS_APP_COMMIT)

entrypoint = "PMO_Builder.py"
build_dir = "docs"

def escape_python_strings(content):
    """Replace literal "\n" (backslash+n) with "\\n" (backslash+backslash+n) inside string literals.
    
    Only replaces the two-character sequence \n (and \t) that appear inside
    Python string literals, converting them to \\n (and \\t).
    Does not modify structural newlines (line breaks) in the source code.
    """
    try:
        # Tokenize the Python code to identify string literals
        tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
        
        # Convert content to list of lines for easier manipulation
        lines = content.split('\n')
        
        # Process tokens in reverse order to maintain positions
        # (reverse order so earlier replacements don't affect later positions)
        for token in reversed(tokens):
            token_type, token_string, start, end, _ = token
            
            # Only process string literals
            if token_type == tokenize.STRING:
                # Extract the raw string content from source (between the quotes)
                # Get the exact substring from the source code
                if start[0] == end[0]:
                    # Single line string
                    line = lines[start[0] - 1]
                    raw_string = line[start[1]:end[1]]
                else:
                    # Multi-line string
                    raw_string = lines[start[0] - 1][start[1]:]
                    for i in range(start[0], end[0] - 1):
                        raw_string += '\n' + lines[i]
                    raw_string += '\n' + lines[end[0] - 1][:end[1]]
                
                # Replace \n with \\n and \t with \\t within the string literal content
                # We need to replace the literal two-character sequences
                modified_string = raw_string.replace('\\n', '\\\\n').replace('\\t', '\\\\t')
                
                # Replace the original string in the content
                if start[0] == end[0]:
                    # Single line string
                    lines[start[0] - 1] = line[:start[1]] + modified_string + line[end[1]:]
                else:
                    # Multi-line string
                    modified_lines = modified_string.split('\n')
                    # Replace first line
                    lines[start[0] - 1] = lines[start[0] - 1][:start[1]] + modified_lines[0]
                    # Replace middle lines
                    for i in range(1, len(modified_lines) - 1):
                        if start[0] - 1 + i < len(lines):
                            lines[start[0] - 1 + i] = modified_lines[i]
                    # Replace last line
                    if len(modified_lines) > 1:
                        lines[end[0] - 1] = modified_lines[-1] + lines[end[0] - 1][end[1]:]
        
        return '\n'.join(lines)
    
    except (tokenize.TokenError, SyntaxError):
        # If tokenization fails (e.g., incomplete code), fall back to no replacement
        # This shouldn't happen for valid Python files, but provides a safety net
        return content

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
                        content = _VERSION_LOG_SNIPPET + content
                    content = escape_python_strings(content)
                    parsed_files.append({"name": file_name, "content": f"`{content}`"})

    # Add the images to the parsed files
    for root, dirs, files in os.walk("pmotools-app"):
        if any(dir in root for dir in ignored_dirs):
            continue
        for file in files:
            if file.endswith(".png"):
                file_name = os.path.join(root, file).replace("pmotools-app/", "")
                # copy the file to the build directory
                os.makedirs(os.path.join(build_dir, "images"), exist_ok=True)
                shutil.copy(os.path.join(root, file), os.path.join(build_dir, "images", file))
                build_url = f"images/{file}"
                parsed_files.append({"name": file_name, "content": {"url": build_url}})

    # Add conf files to the parsed files
    for root, dirs, files in os.walk("pmotools-app"):
        if any(dir in root for dir in ignored_dirs):
            continue
        for file in files:
            if file.endswith(".json"):
                with open(os.path.join(root, file), "r") as f:
                    file_name = os.path.join(root, file).replace("pmotools-app/", "")
                    parsed_files.append({"name": file_name, "content": f"`{f.read()}`"})


    # Render the template
    rendered = template.render(files=parsed_files, requirements=requirements, entrypoint=entrypoint)

    # Write the rendered template to the output file
    os.makedirs(build_dir, exist_ok=True)
    with open(os.path.join(build_dir, "index.html"), "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    print(f"Stlite @{_STLITE_BROWSER_VERSION} / Pyodide v{_PYODIDE_VERSION}")
    print(f"pmotools-app: {_PMOTOOLS_APP_COMMIT}")
    print(f"Lockfile: {_PYODIDE_LOCK_URL}")
    print("Requirements (from pmotools-app/pyproject.toml):")
    for req in requirements:
        print(f"  {req}")
    for warning in _requirement_warnings:
        print(f"  warning: {warning}")
    build_site()
