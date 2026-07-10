# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import pathlib
import re
import sys

# Make the package importable for autodoc without installing it.
_repo_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))

# -- Project information ------------------------------------------------------

project   = "cosmic-crunch"
author    = "Erick Edward Shepherd"
copyright = "2020-2026, Erick Edward Shepherd"

# Single-source the version from the package without importing it (its
# C-extension dependencies are not installed in the docs build).
_init   = (_repo_root / "cosmic_crunch" / "__init__.py").read_text(encoding="utf-8")
release = re.search(r'__version__\s*=\s*"([^"]+)"', _init).group(1)
version = release

# -- General configuration ----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

# Heavy dependencies mocked so the docs build needs no netCDF/system libraries;
# autodoc only imports the package to read its docstrings.
autodoc_mock_imports = ["netCDF4", "pandas", "requests", "tqdm", "numpy"]

autodoc_member_order = "bysource"
autodoc_typehints    = "description"

# Resolve in-README anchor links such as [Compression](#compression).
myst_heading_anchors = 3

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

templates_path   = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "design",
    "plans",
    "release-checklist.md",
    "site-notes.md",
]

# -- HTML output --------------------------------------------------------------

html_theme = "furo"
html_title = f"cosmic-crunch {release}"
