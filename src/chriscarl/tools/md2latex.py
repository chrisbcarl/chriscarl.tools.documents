#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.md2latex is a tool which converts Markdown to LaTeX WITH a Markdown bibliography!
I've found throughout 3 semesters of grad school that working in Markdown is the obvious choice
    but citations are a pain in the ass and research collation is a pain in the ass
    so my current solution is the following:
    markdown essay file + markdown/bibtex "research" file with certain -isms that lock the 2 together.

Updates:
    2026-01-29 - tools.md2latex - got a hankerin to at least start getting the outlines done
    2026-01-25 - tools.md2latex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional
from dataclasses import dataclass, field
from argparse import ArgumentParser
import json

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath
from chriscarl.core.lib.stdlib.io import read_text_file_try
from chriscarl.tools.shed import md2latex
from chriscarl.tools.shed import md2bibtex
import chriscarl.files.manifest_documents as mand

SCRIPT_RELPATH = 'chriscarl/tools/md2latex.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

# argument defaults
DEFAULT_FIB_INIT = [0, 1]
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.md2latex')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.md2latex.log')

# tool constants
TEMPLATES = {
    'default': mand.FILEPATH_MD2LATEX_DEFAULT_TEMPLATE,
    'chicago': mand.FILEPATH_MD2LATEX_CHICAGO_TEMPLATE,
    'ieee': mand.FILEPATH_MD2LATEX_IEEE_TEMPLATE,
}
DEFAULT_TEMPLATE = list(TEMPLATES)[0]


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    markdown_filepath: str
    bibliography: Optional[str] = None
    output_dirpath: Optional[str] = None
    template: str = DEFAULT_TEMPLATE
    spellcheck_fatal: bool = False
    skip_spellcheck: bool = False
    # wc-applet
    word_count: bool = False
    # non-app
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('main applet')
        app.add_argument('markdown_filepath', type=str, help='.md?')
        app.add_argument('--bibliography', '-b', type=str, help='.md w/ bibtex?')
        app.add_argument('--output-dirpath', '-o', type=str, help='save outputs to different dir than input?')
        app.add_argument('--template', '-t', type=str, default=DEFAULT_TEMPLATE, choices=TEMPLATES, help='document style, really')
        app.add_argument('--spellcheck-fatal', '-sf', action='store_true', help='spellcheck fail is fatal')
        app.add_argument('--skip-spellcheck', '-ss', action='store_true', help='skip-spellcheck entirely')

        wc = parser.add_argument_group('word-count applet')
        wc.add_argument('--word-count', '-wc', action='store_true', help='get the word count, exit')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        if self.output_dirpath:
            make_dirpath(self.output_dirpath)
        if self.debug:
            self.log_level = 'DEBUG'
        configure_ez(level=self.log_level, filepath=self.log_filepath)

    @staticmethod
    def parse(parser=None, argv=None):
        # type: (Optional[ArgumentParser], Optional[List[str]]) -> Arguments
        parser = parser or Arguments.argparser()
        ns = parser.parse_args(argv)
        arguments = Arguments(**(vars(ns)))
        arguments.process()
        return arguments


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    md2latex.assert_executables_exist()

    md_content = read_text_file_try(args.markdown_filepath)
    if not md_content.endswith('\n'):
        md_content = f'{md_content}\n'

    word_count = md2latex.word_count(md_content)
    LOGGER.info('wc: %d', word_count)
    if args.word_count:
        return 0

    bibtex_content, bibtex_labels = '', {}
    if args.bibliography:
        bibtex_content, bibtex_labels = md2bibtex.text_to_bibtex(args.bibliography)
        if args.debug:
            LOGGER.debug('bibtex labels: %s', json.dumps(bibtex_labels))

    return 0


if __name__ == '__main__':
    sys.exit(main())
'''
Definition:
    - label: a name/label for something ON the doc/bib
    - ref: a reference to a label
    - citation: a ref to a bibliography label

Shape of the algorithm:

# clean the bibliography
    bibliography = read bibliography
    bibtex content = extract bibtex content
    bib-labels = extract all keys
    clean the bibtex content so that it will render correctly
    if any cleaning occurred, copy a new bibfile
    else, use current bibfile
    TODO: test that it renders correctly by doing a dummy documenet

# annotate the markdown
    BAD unicode replace

    sections = []
    header_locations = re.find(#+)
        section.append(pre-amble section is before the first mo)
        sections.extend(ranges from each.)

    errors = []
    doclets = [
        ('yaml', '---asdf: whatever---', spellcheck='')
        ('plain', 'asdfasdfasdf', spellcheck='asdfasdf')
        ('comment', '---asdf: whatever---', spellcheck='')
        ('table', '|||', caption='capt', label='asdf', spellcheck='')
        ...
        ('header', 'introduction', label='introduction', spellcheck='introduction')
        ...
        ('header', 'introduction', label='introduction', spellcheck='introduction', appendix=True)
    ]
    appendix = False
    doc-labels-existing = {}
    doc-refs-requested = []
    for section in sections:
        def analyze_section:
            header? add that to the labels
                if appendix
            errors:
                naked hyperlinks? warn that it must be enclosed
            extract and remove and parse:
                yaml?
            note the range:
                # blocks
                    # may also include refs other blocks or inlines...
                        list?
                        image?
                            path exists, downloaded or downloadable?
                        table?
                            properly captioned, reffed?
                    # cannot include refs
                        comments?
                        latex double?
                        code/backticks?
                # inline
                    backticks?
                    latex single?
                    citations?
                        if interdoc, do they have the pref?

    for ref in doc-refs-requested:
        if ref not in doc-labels-existing:
            add to errors
    if errors:
        ref errors

    yaml = extract yaml section

# wordcount the markdown
    markdown = read markdown
    if wordcount:
        print a best word count and return

# spellcheck if asked

# render the content
    according to yaml
    for doc in doclets
        get latex
    append to body/appendix
'''
