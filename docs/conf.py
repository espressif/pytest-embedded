# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from datetime import datetime

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pytest-embedded'
project_homepage = 'https://github.com/espressif/pytest-embedded'
copyright = f'2023-{datetime.now().year}, Espressif Systems (Shanghai) Co., Ltd.'  # noqa: A001
author = 'Fu Hanxi'
version = '1.x'
release = '1.x'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_copybutton',
    'sphinx_tabs.tabs',
    'sphinxcontrib.mermaid',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_css_files = ['theme_overrides.css']
html_logo = '_static/espressif-logo.svg'
html_static_path = ['_static']
html_theme = 'sphinx_rtd_theme'

# -- Options for intersphinx extension ---------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pytest': ('https://docs.pytest.org/en/stable', None),
    'pexpect': ('https://pexpect.readthedocs.io/en/stable', None),
}
