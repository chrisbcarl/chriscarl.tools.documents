#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

files.manifest_documents is literally what it says on the tin
files are modules that elevate files so they can be used in python, either registering the path name or actually interacting with them like data cabinets.

Updates:
    2026-01-29 - files.manifest_documents - md2latex
    2026-01-25 - files.manifest_documents - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging

# third party imports

# project imports

SCRIPT_RELPATH = 'chriscarl/files/manifest_documents.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

# ###

# ./
DIRPATH_ROOT = SCRIPT_DIRPATH
FILEPATH_MANIFEST_ACADEMIA_PY = os.path.join(DIRPATH_ROOT, 'manifest_documents.py')

# ./spellchecker
DIRPATH_SPELLCHECKER = os.path.join(SCRIPT_DIRPATH, './spellchecker')
FILEPATH_ACRONYMS = os.path.join(DIRPATH_SPELLCHECKER, 'acronyms.txt')
FILEPATH_DICTIONARY = os.path.join(DIRPATH_SPELLCHECKER, 'dictionary.txt')
FILEPATH_NAMES = os.path.join(DIRPATH_SPELLCHECKER, 'names.txt')
FILEPATH_NON_WORDS = os.path.join(DIRPATH_SPELLCHECKER, 'non-words.txt')

# ./mathml2latex
DIRPATH_MATHML2LATEX = os.path.join(SCRIPT_DIRPATH, './mathml2latex')
FILEPATH_MATHML2LATEX_TEMPLATE = os.path.join(DIRPATH_MATHML2LATEX, 'template.tex')

# ./md2latex
DIRPATH_MD2LATEX = os.path.join(SCRIPT_DIRPATH, './md2latex')
FILEPATH_MD2LATEX_DEFAULT_TEMPLATE = os.path.join(DIRPATH_MD2LATEX, 'default.tex')
FILEPATH_MD2LATEX_IEEE_TEMPLATE = os.path.join(DIRPATH_MD2LATEX, 'ieee.tex')
FILEPATH_MD2LATEX_CHICAGO_TEMPLATE = os.path.join(DIRPATH_MD2LATEX, 'chicago.tex')

# ###
