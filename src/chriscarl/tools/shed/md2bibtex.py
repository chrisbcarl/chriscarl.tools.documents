#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.shed.md2bibtex is functions used by the tool that belong in the shed.
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

Updates:
    2026-02-04 - tools.shed.md2bibtex - support for the refactors
    2026-01-29 - tools.shed.md2bibtex - text_to_bibtex now replies with bibtex and non-bibtex
    2026-01-29 - tools.shed.md2bibtex - docs
    2026-01-25 - tools.shed.md2bibtex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import re
from typing import Tuple, Dict

# third party imports

# project imports
from chriscarl.core.lib.stdlib.os import is_file
from chriscarl.core.lib.stdlib.io import read_text_file
from chriscarl.core.functors.parse import bibtex
from chriscarl.core.functors.parse import latex

SCRIPT_RELPATH = 'chriscarl/tools/shed/md2bibtex.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


def text_to_bibtex(text, pretty=True, indent=4):
    # type: (str, bool, int) -> Tuple[str, str]
    '''
    Description:
        Given any text file, extract all of the bibtex and non-bibtex from it.
    Arguments:
        text: str
            filepath or text content
    Returns:
        Tuple[str, str]
            str - bibtex-only content
            str - non-bibtex content
    '''
    if is_file(text):
        text = read_text_file(text)

    bibtex_content, non_bibtex_content = bibtex.extract_from_and_remove(text, pretty=pretty, indent=indent)

    # this is tricky, you only want to analyze stuff INSIDE quotations marks and braces...
    fixed_bibtex_content = bibtex_content[:]  # deep copy
    bad_lines = []

    for mo in reversed(list(re.finditer(r'["{].*?[}"]', fixed_bibtex_content, flags=re.MULTILINE))):
        start, end = mo.start() + 1, mo.end() - 1
        substr = fixed_bibtex_content[start:end]
        if re.search(r'([^\\])([{}])', substr):
            # { .{}. } just causes problems, dont bother dealing with it
            # print(substr)
            bad_lines.append(substr)
            continue

        fixed_bibtex_content = f'{fixed_bibtex_content[:start]}{latex.latex_escape_raw(substr, latex.REGEX_LATEX_NEEDS_ESCAPE_ENCLOSED)}{fixed_bibtex_content[end:]}'

    if bad_lines:
        lines = '\n'.join(f'    - {line}' for line in bad_lines)
        raise RuntimeError(f'bad lines discovered containing "{{}}", replace them at source, not worth the headache:\n{lines}')

    return fixed_bibtex_content, non_bibtex_content
