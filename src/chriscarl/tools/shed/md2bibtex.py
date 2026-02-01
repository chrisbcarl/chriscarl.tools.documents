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
from chriscarl.core.lib.stdlib.io import read_text_file_try
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


def text_to_bibtex(text):
    # type: (str) -> Tuple[str, Dict[str, str]]
    '''
    Description:
        Given any text file, extract all of the bibtex from it.
        Get back a clean bibtex and the labels in the bibtex.
    Arguments:
        text: str
            filepath or text content
    Returns:
        Tuple[str, Dict[str, str]]
            str - bibtex-only content
            Dict[str, str] - {label: citation-type}
    '''
    if is_file(text):
        text = read_text_file_try(text)

    bibtex_content = bibtex.extract_from(text)

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

        fixed_bibtex_content = f'{fixed_bibtex_content[:start]}{latex.latex_escape(substr)}{fixed_bibtex_content[end:]}'

    if bad_lines:
        lines = '\n'.join(f'    - {line}' for line in bad_lines)
        raise RuntimeError(f'bad lines discovered containing "{{}}", replace them at source, not worth the headache:\n{lines}')

    # # in a previous attempt I tried to escape everything correctly
    #     for char in ['$', '#', '%', '&', '~', '_', '^', '{', '}']:
    #         regex = r'[^\\]' + re.escape(char)
    #         print(regex)
    #         for submo in reversed(
    #                 list(re.finditer(regex, bibtex_content[start:end]))):
    #             substart, subend = submo.start(), submo.end()
    #             bibtex_content = f'{bibtex_content[:start + substart]}\\{char}{bibtex_content[start + subend:]}'
    # fixed_bibtex_content = re.sub(r'_', '\\_', bibtex_content)
    labels = bibtex.get_labels(text, raise_on_null=True)
    return fixed_bibtex_content, labels
