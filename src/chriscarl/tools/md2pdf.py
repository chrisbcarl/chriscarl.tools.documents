#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-02-06
Description:

tools.md2pdf is a tool which converts Markdown to PDF via LaTeX WITH a bibliography!
I've found throughout 3 semesters of grad school that working in Markdown is the obvious choice
    but citations are a pain in the ass and research collation is a pain in the ass
    so my current solution is the following:
    markdown essay file + markdown/bibtex "research" file with certain -isms that lock the 2 together.

Examples:
    # note that the output is a .tex file, not a .pdf
    md2pdf tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex/ieee -t ieee -sf
        -ss  # skip spellcheck

    md2pdf tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex/chicago -t chicago -sf
        -ss  # skip spellcheck

Updates:
    2026-02-06 - tools.md2pdf - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional, Tuple
from dataclasses import dataclass, field
from argparse import ArgumentParser

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, filename
from chriscarl.tools import md2latex as md2latex_tool
from chriscarl.tools.shed import md2latex, tex2pdf

SCRIPT_RELPATH = 'chriscarl/tools/md2pdf.py'
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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.md2pdf')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.md2pdf.log')

# tool constants


@dataclass
class Arguments(md2latex_tool.Arguments):
    '''
    Document this class with any specifics for the process function.
    '''
    skip_pdf: bool = False

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = super().argparser()
        app = parser.add_argument_group('md2pdf')
        app.add_argument('--skip-pdf', '-sp', action='store_true', help='generate .tex only, no run pdf :(')

        return parser


def md2pdf(
    md_filepath,
    output_dirpath='',
    bibliography_filepaths=None,
    template=md2latex.DEFAULT_TEMPLATE,
    wc=False,
    spellcheck_fatal=False,
    skip_spellcheck=False,
    skip_pdf=False,
    debug=False,
):
    # type: (str, str, Optional[List[str]], str, bool, bool, bool, bool, bool) -> Tuple[str, str, str]
    bibliography_output_filepath, tex_output_filepath, download_url_filepaths, headers = md2latex_tool.markdown_to_latex(
        md_filepath,
        output_dirpath,
        bibliography_filepaths=bibliography_filepaths,
        template=template,
        wc=wc,
        spellcheck_fatal=spellcheck_fatal,
        skip_spellcheck=skip_spellcheck,
        debug=debug,
    )

    md_filename = filename(md_filepath)
    pdf_output_filepath = abspath(output_dirpath, f'{md_filename}.pdf')

    phase, errors, warnings = 'download', [], []
    LOGGER.info('running %r', phase)
    md2latex.download_copy_files(download_url_filepaths, output_dirpath)
    md2latex_tool.log_error_warnings(phase, errors, warnings)

    template = headers.get('template', template)
    phase, errors, warnings = 'tex2pdf', [], []
    if skip_pdf:
        LOGGER.warning('skipping %r', phase)
        return bibliography_output_filepath, tex_output_filepath, ''
    LOGGER.info('running %r', phase)
    tex2pdf.run_pdflatex(md_filename, output_dirpath, template)
    md2latex_tool.log_error_warnings(phase, errors, warnings)

    # NOTE: only clean up if everything went well, leave everything behind if it didnt...
    LOGGER.info('deleting unnecessary work files...')
    cleanup_filepaths = [tpl[1] for tpl in download_url_filepaths]
    md2latex.delete_latex_work_files(output_dirpath, md_filename, extra=cleanup_filepaths)

    return bibliography_output_filepath, tex_output_filepath, pdf_output_filepath


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    bibliography_output_filepath, tex_output_filepath, pdf_output_filepath = md2pdf(
        args.markdown_filepath,
        args.output_dirpath,
        bibliography_filepaths=args.bibliography_filepaths,
        template=args.template,
        wc=args.word_count,
        spellcheck_fatal=args.spellcheck_fatal,
        skip_spellcheck=args.skip_spellcheck,
        skip_pdf=args.skip_pdf,
        debug=args.debug,
    )
    LOGGER.info('.bib at "%s"', os.path.relpath(bibliography_output_filepath, os.getcwd()))
    LOGGER.info('.tex at "%s"', os.path.relpath(tex_output_filepath, os.getcwd()))
    LOGGER.info('.pdf at "%s"', os.path.relpath(pdf_output_filepath, os.getcwd()))
    LOGGER.info('done!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
