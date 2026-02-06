#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

chriscarl.tools.shed.md2bibtex unit test.

Updates:
    2026-01-25 - tests.chriscarl.tools.shed.md2bibtex - initial commit
'''

# stdlib imports (expected to work)
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import unittest

# third party imports

# project imports (expected to work)
from chriscarl.core import constants
from chriscarl.core.lib.stdlib.os import abspath
from chriscarl.core.lib.stdlib.unittest import UnitTest

# test imports
import chriscarl.tools.shed.md2bibtex as lib

SCRIPT_RELPATH = 'tests/tools/shed/test_md2bibtex.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

constants.fix_constants(lib)  # deal with namespace sharding the files across directories


class TestCase(UnitTest):

    def setUp(self):
        return super().setUp()

    def tearDown(self):
        return super().tearDown()

    # @unittest.skip('lorem ipsum')
    def test_case_0(self):
        bibtex_no_point = r'''@article{CitekeyArticle,
        journal  = "\url{Proceedings of the National Academy of Sciences}",
        year     = 1963,
    }'''
        bibtex_no_key = r'''@article{
        year     = 1963,
    }'''
        bibtex = r'''@article{CitekeyArticle,
    author  = "P. J. Cohen",  % inlinecomment
    % comment
    title   = "The independence of the continuum hypothesis",
    journal = "Proceedings of the National Academy of Sciences",
    pages   = "1143--1148",
}'''
        markdown = rf'''
# Some kind of markdown header
- list
- code block
    ```bibtex
    but not actually
    ```
- another list element
'''
        variables = [
            (lib.text_to_bibtex, (bibtex_no_point, ), dict(pretty=False)),
            (lib.text_to_bibtex, (bibtex_no_key, ), dict(pretty=False)),
            (lib.text_to_bibtex, (bibtex, ), dict(pretty=False)),
            (lib.text_to_bibtex, (markdown + bibtex + markdown, ), dict(pretty=False)),
        ]
        controls = [
            RuntimeError,
            (bibtex_no_key, ''),
            (bibtex, ''),
            (bibtex, markdown * 2),
        ]
        self.assert_null_hypothesis(variables, controls)


if __name__ == '__main__':
    tc = TestCase()
    tc.setUp()

    try:
        tc.test_case_0()
    finally:
        tc.tearDown()
