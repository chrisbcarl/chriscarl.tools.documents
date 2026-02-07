#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-31
Description:

tools.shed.html2md really just wraps markdownify
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

Updates:
    2026-01-31 - tools.shed.html2md - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import re
from typing import Union

# third party imports
import markdownify

# project imports
from chriscarl.core.lib.stdlib.io import read_text_file
from chriscarl.core.lib.stdlib.os import is_file

SCRIPT_RELPATH = 'chriscarl/tools/shed/html2md.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


def html_to_markdown(html_or_str):
    # type: (str) -> str
    if is_file(html_or_str):
        html_or_str = read_text_file(html_or_str)

    text = markdownify.markdownify(
        html_or_str,
        heading_style='ATX',  # headers w/ octothorp
        autolinks=True,  # hrefs do [*](https://google.com) instead of [*](https://google.com "https://google.com")
        bullets='---',  # bullet depth order usage, default '*+-'
        # convert=['b', 'strong', 'em', 'a'],  # convert is a LIMITER option
    )
    text = re.sub(r'\n{2,}', '\n', text).strip()
    return text
