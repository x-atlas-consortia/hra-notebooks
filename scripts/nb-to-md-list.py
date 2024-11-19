import os
import json
import sys

def extract_title_from_notebook(notebook_path):
    """
    Extracts the title from the first markdown cell of a Jupyter notebook,
    stripping leading '#' marks and whitespace.
    
    Args:
        notebook_path (str): Path to the .ipynb file.
    
    Returns:
        str: Title of the notebook, or None if no title is found.
    """
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
            # Look for the first cell that is a markdown cell
            for cell in notebook.get("cells", []):
                if cell.get("cell_type") == "markdown":
                    # Join the lines of the markdown text
                    raw_title = cell.get("source", [""])[0].strip()
                    # Strip leading '#' characters and whitespace
                    return raw_title.lstrip("#").strip()
    except Exception as e:
        print(f"Error reading {notebook_path}: {e}", file=sys.stderr)
    return None

def generate_markdown_list(directory, github_prefix):
    """
    Generates a markdown list of Jupyter notebooks in a directory,
    sorted alphabetically by title and including links to open them in Google Colab.

    Args:
        directory (str): Path to the directory containing .ipynb files.
        github_prefix (str): GitHub URL prefix for constructing Colab links.
    
    Returns:
        str: Markdown formatted list of notebooks and their titles.
    """
    notebooks = []
    for filename in os.listdir(directory):
        if filename.endswith(".ipynb"):
            filepath = os.path.join(directory, filename)
            title = extract_title_from_notebook(filepath)
            if not title:
                title = "(No Title Found)"
            relative_path = os.path.relpath(filepath, directory).replace("\\", "/")
            notebook_url = f"{directory}/{relative_path}".replace("\\", "/")
            colab_url = f"https://colab.research.google.com/github/{github_prefix}/{relative_path}"
            colab_badge = f'<a target="_blank" href="{colab_url}"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>'
            notebooks.append((title, notebook_url, colab_badge))
    
    # Sort notebooks by title
    notebooks.sort(key=lambda x: x[0].lower())

    # Generate markdown lines
    markdown_lines = [f"* [{title}]({url}) {badge}" for title, url, badge in notebooks]
    return "\n".join(markdown_lines)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python nb-to-md-list.py <directory> <github_prefix>", file=sys.stderr)
        sys.exit(1)
    
    notebooks_directory = sys.argv[1].rstrip("/")
    github_prefix = sys.argv[2].strip().rstrip("/")
    if not os.path.isdir(notebooks_directory):
        print(f"Error: {notebooks_directory} is not a valid directory.", file=sys.stderr)
        sys.exit(1)
    
    markdown_output = generate_markdown_list(notebooks_directory, github_prefix)
    print(markdown_output)
