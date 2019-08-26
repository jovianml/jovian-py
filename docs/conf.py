import os
import sys

from recommonmark.transform import AutoStructify

sys.path.insert(0, os.path.abspath('../')) # source path to access the module 

project = 'Jovian'
copyright = '2019, SwiftAce Inc'
author = 'Aakash N S, Siddhant Ujjain'

extensions = ['recommonmark', # to use .md along with .rst
              'sphinx.ext.autodoc', # import doc from docstrings
              'sphinx.ext.linkcode', # linking the source code on github
              'sphinxcontrib.napoleon'] # to support Google style docstrings for autdoc

master_doc = 'index'
source_suffix = ['.rst', '.md']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']
html_style = 'css/custom.css' # adding some custom styles on the theme

html_logo = 'jvn_full_logo.png'
html_theme_options = {
    'logo_only' : True # to display only logo on the side nav bar
}

html_icon = 'jovian_favicon.png' # icon next to title on the browser's tab

def setup(app):
    """Enables to embed reStructuredText(rst) in a markdown(.md)
    
    https://recommonmark.readthedocs.io/en/latest/auto_structify.html#embed-restructuredtext
    """

    app.add_config_value('recommonmark_config', {
        'auto_toc_tree_section': 'Contents',
        'enable_math': False,
        'enable_inline_math': False,
        'enable_eval_rst': True
    }, True)
    app.add_transform(AutoStructify)

def linkcode_resolve(domain, info):
    """To provide github source link for the methods
    
    https://www.sphinx-doc.org/en/master/usage/extensions/linkcode.html
    """

    if domain != 'py':
        return None
    if not info['module']:
        return None
    filename = info['module'].replace('.', '/')
    return "https://github.com/jvn-io/jovian-py/tree/master/{}.py".format(filename)