#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

chriscarl.tools.shed.md2latex unit test.

Updates:
    2026-01-25 - tests.chriscarl.tools.shed.md2latex - initial commit
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
from chriscarl.core.lib.stdlib.io import write_text_file

# test imports
import chriscarl.tools.shed.md2latex as lib

SCRIPT_RELPATH = 'tests/chriscarl/tools/shed/test_md2latex.py'
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
        self.citations = '''<arendt>
<patient4>
<elon-extinct>
<foucault, 198>
<weber, 119-120>
<kimmel, 18:00>
<alt-right, 10:40>
<alt-right, 11:18-11:35>
<marx, Estranged Labour XXIV, s10-12>
<du-bois, CHAPTER II: THE SOULS OF WHITE FOLK, 29>'''
        self.citations_md = abspath(self.tempdir, 'citations.md')
        write_text_file(self.citations_md, self.citations)
        return super().setUp()

    def tearDown(self):
        return super().tearDown()

    # TODO: this isnt really testable... bit of an idictment of the software design and maintainability.
    # # @unittest.skip('lorem ipsum')
    # def test_case_0(self):
    #     sections = lib.analyze_large_sections(self.citations)
    #     doclets, interdoc_labels, download_url_filepaths, errors, warnings = lib.sections_to_doclets(
    #         sections,
    #         self.citations_md,
    #         self.tempdir,
    #     )
    #     labels, errors, warnings = lib.process_labels({}, interdoc_labels)
    #     headers, renders, errors, warnings = lib.doclets_to_latex(doclets, self.citations_md, abspath(self.tempdir, 'whateve.bib'), labels, 'default')

    #     variables = [
    #         (self.assertEqual, (len(self.citations_md.splitlines()), len(labels))),
    #     ]
    #     controls = [
    #         True,
    #     ]
    #     self.assert_null_hypothesis(variables, controls)

    def test_case_1(self):
        variables = [
            (lib.process_labels, ({
                'software-label': '''@software{software-label,
  author   = "P. J. Cohen",
}'''
            }, {})),
        ]
        controls = [
            ({}, ["label 'software-label' has unknown article type 'software'"], []),
        ]
        self.assert_null_hypothesis(variables, controls)


if __name__ == '__main__':
    tc = TestCase()
    tc.setUp()

    try:
        # tc.test_case_0()
        tc.test_case_1()
    finally:
        tc.tearDown()
