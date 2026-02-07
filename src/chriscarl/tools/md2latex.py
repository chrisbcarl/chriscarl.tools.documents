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

Examples:
    md2latex tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex/ieee -t ieee -sf
        -ss  # skip spellcheck

    md2latex tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex/chicago -t chicago -sf
        -ss  # skip spellcheck

TODO:
    - support multi-bib files
    - bib ensure the types supported are actually supported "software" is not supported as a bib
    - make a paper-md that really covers every edge case
        - references INSIDE math doesn't really work... better to put it outside.
    - test elipses and cdots behavior
    - ref in table still bad ISE-201/assignments/00-llm/render/paper-md2pdf.pdf
    - "ted to cross-reference whether" was picked up as a ref somehow...
    - table doesnt get picked up if at end C:/Users/chris/OneDrive/_recent/SJSU_2026S/ISE-201/assignments/00-llm/paper-md2pdf.md
        - even IF you add some text at the bottom to clear up the above
        - moving "investigation-findings-tbl" stuff below that table causes massive problem
    - old table missing caption/label doesnt get mentioned
    - errant prints
    - check research-aid-2 for leftovers
    - find bibliography if close by
    - md2pdf vs md2latex, NOT THE SAME
    - default template doesnt work, figure something out import-wise...
    - refactor


Updates:
    2026-02-06 - tools.md2latex - refactored for simplicity and readability, its much improved
    2026-02-04 - tools.md2latex - math template mode enabled, tested with a statistics submission, works, covered MANY edge cases.
    2026-02-01 - tools.md2latex - banged this refactor phase 1 out in about 8 hours. totally worth it.
                 tools.md2latex - added find_bad_citations, markdown_refs_to_latex, markdown_header_to_render_dict, markdown_to_latex
    2026-01-29 - tools.md2latex - got a hankerin to at least start getting the outlines done
    2026-01-25 - tools.md2latex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional, Tuple
from dataclasses import dataclass, field
from argparse import ArgumentParser
import pprint
import json

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, dirpath, filename
from chriscarl.core.lib.stdlib.io import read_text_file_try, write_text_file
from chriscarl.tools.shed import md2latex
from chriscarl.core.functors.parse import latex
from chriscarl.core.functors.parse import bibtex
from chriscarl.core.functors.parse import markdown
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
    'math': mand.FILEPATH_MD2LATEX_CHICAGO_TEMPLATE,  # chicago with some hardcoding
}
DEFAULT_TEMPLATE = list(TEMPLATES)[0]


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    markdown_filepath: str
    output_dirpath: str = ''
    bibliography_filepaths: List[str] = field(default_factory=lambda: [])
    template: str = DEFAULT_TEMPLATE
    spellcheck_fatal: bool = False
    skip_spellcheck: bool = False
    skip_pdf: bool = False
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
        app.add_argument('--bibliography-filepaths', '--bibliographys', '-b', type=str, nargs='+', default=[], help='.md w/ bibtexs?')
        app.add_argument('--output-dirpath', '-o', type=str, default='', help='save outputs to different dir than input?')
        app.add_argument('--template', '-t', type=str, default=DEFAULT_TEMPLATE, choices=TEMPLATES, help='document style, really')
        app.add_argument('--spellcheck-fatal', '-sf', action='store_true', help='spellcheck fail is fatal')
        app.add_argument('--skip-spellcheck', '-ss', action='store_true', help='skip-spellcheck entirely')
        app.add_argument('--skip-pdf', '-sp', action='store_true', help='generate .tex only, no run pdf :(')

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


def md2latex_log_error_warnings(phase, errors, warnings):
    # type: (str, List[str], List[str]) -> None
    if warnings:
        LOGGER.warning('%s - %d warnings!', phase, len(warnings))
        for warning in warnings:
            LOGGER.warning(warning)
    else:
        LOGGER.debug('%s - 0 warnings!', phase)

    if errors:
        LOGGER.error('%s - %d errors!', phase, len(errors))
        for error in errors:
            LOGGER.error(error)
        sys.exit(1)
    else:
        LOGGER.debug('%s - 0 errors!', phase)


def markdown_to_latex(
    md_filepath,
    output_dirpath='',
    bibliography_filepaths=None,
    template=DEFAULT_TEMPLATE,
    wc=False,
    spellcheck_fatal=False,
    skip_spellcheck=False,
    skip_pdf=False,
    debug=False,
):
    # type: (str, str, Optional[List[str]], str, bool, bool, bool, bool, bool) -> int
    if template not in TEMPLATES:
        raise ValueError(f'template {template!r} not in {list(TEMPLATES)}')

    md_relpath = os.path.relpath(abspath(md_filepath), os.getcwd())
    md_dirpath = dirpath(md_filepath)
    md_filename = filename(md_filepath)
    if not output_dirpath:
        output_dirpath = md_dirpath
    output_dirpath = abspath(output_dirpath)
    os.makedirs(output_dirpath, exist_ok=True)
    tex_output_filepath = abspath(output_dirpath, f'{md_filename}.tex')
    bibliography_output_filepath = abspath(output_dirpath, f'{md_filename}.bib')  # latex.latex_remove(md_filename)
    pdf_output_filepath = abspath(output_dirpath, f'{md_filename}.pdf')
    bibliography_filepaths = bibliography_filepaths or []

    # right off the rip
    md_content = read_text_file_try(md_filepath)
    if not md_content.endswith('\n'):
        md_content = f'{md_content}\n'
    md_content = md2latex.REGEX_MARKDOWN_EMPTY_LITERAL.sub('', md_content)

    word_count = md2latex.word_count(md_content)
    LOGGER.info('wc: %d', word_count)
    if wc:
        return 0

    # bibliographies
    phase, errors, warnings = 'bibtex', [], []
    LOGGER.info('running %r', phase)
    bibtex_labels, errors, warnings = md2latex.bibliographies_to_bibtex([md_filepath] + bibliography_filepaths, bibliography_output_filepath)
    md2latex_log_error_warnings(phase, errors, warnings)

    # sections
    phase, errors, warnings = 'sections', [], []
    LOGGER.info('running %r', phase)
    sections = md2latex.analyze_large_sections(md_content)
    md2latex_log_error_warnings(phase, errors, warnings)

    # doclets
    phase, errors, warnings = 'sections2doclets', [], []
    LOGGER.info('running %r', phase)
    doclets, interdoc_labels, download_url_filepaths, errors, warnings = md2latex.sections_to_doclets(sections, md_filepath, output_dirpath)
    md2latex_log_error_warnings(phase, errors, warnings)

    all_labels_lowcase = {}  # low_case: CasEd
    interdoc_label_types = {}
    for k in bibtex_labels:
        all_labels_lowcase[k.lower()] = k
    for key, value in interdoc_labels.items():
        if value.lower() in all_labels_lowcase:
            errors.append(f'duplicate {key} label {value!r}')
        all_labels_lowcase[key.lower()] = key
    if debug:
        pprint.pprint(interdoc_labels, indent=2, width=160)

    # {'quote', 'table', 'latex', 'literal', 'comment', 'yaml', 'code', 'header', 'any', 'img', 'list'}
    if debug:
        LOGGER.debug('sections: %s', [doc.section for doc in doclets])

    # spellcheck
    phase, errors, warnings = 'doclets2spellcheck', [], []
    if skip_spellcheck:
        LOGGER.warning('skipping %r', phase)
    else:
        LOGGER.info('running %r', phase)
        word_count, errors, warnings = md2latex.doclets_spellcheck(doclets, md_filepath)
        LOGGER.info('wc: %d', word_count)
        if not spellcheck_fatal:
            warnings.extend(errors)
            errors.clear()
            md2latex_log_error_warnings(phase, errors, warnings)

    # doclets to body
    phase, errors, warnings = 'doclets2latex', [], []
    LOGGER.info('running %r', phase)
    body, appendix_body, errors, warnings = md2latex.doclets_to_latex(doclets, md_filepath, all_labels_lowcase, interdoc_label_types, template)
    md2latex_log_error_warnings(phase, errors, warnings)

    phase, errors, warnings = 'doclets+latex2texfile', [], []
    LOGGER.info('running %r', phase)
    errors, warnings = md2latex.render_tex_file(doclets, md_filepath, TEMPLATES[template], bibliography_output_filepath, tex_output_filepath, template, body, appendix_body)
    md2latex_log_error_warnings(phase, errors, warnings)

    phase, errors, warnings = 'download', [], []
    LOGGER.info('running %r', phase)
    md2latex.download_copy_files(download_url_filepaths, output_dirpath)
    md2latex_log_error_warnings(phase, errors, warnings)

    phase, errors, warnings = 'tex2pdf', [], []
    if skip_pdf:
        LOGGER.warning('skipping %r', phase)
        return 0
    LOGGER.info('running %r', phase)
    md2latex.run_pdflatex(md_filename, output_dirpath, template)
    md2latex_log_error_warnings(phase, errors, warnings)

    # NOTE: only clean up if everything went well, leave everything behind if it didnt...
    LOGGER.info('deleting unnecessary work files...')
    cleanup_filepaths = [tpl[1] for tpl in download_url_filepaths]
    md2latex.delete_latex_work_files(output_dirpath, md_filename, extra=cleanup_filepaths)

    LOGGER.info('.bib at "%s"', bibliography_output_filepath)
    LOGGER.info('.tex at "%s"', tex_output_filepath)
    LOGGER.info('.pdf at "%s"', pdf_output_filepath)

    LOGGER.info('done!')
    return 0


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    md2latex.assert_executables_exist()

    return markdown_to_latex(
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


if __name__ == '__main__':
    sys.exit(main())
