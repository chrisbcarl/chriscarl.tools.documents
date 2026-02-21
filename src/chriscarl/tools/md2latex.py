#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.md2latex is a tool which converts Markdown to LaTeX WITH a Markdown bibliography!

Examples:
    # note that the output is a .tex file, not a .pdf
    md2latex tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex/ieee -t ieee -sf
        -ss  # skip spellcheck

    md2latex tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex/chicago -t chicago -sf
        -ss  # skip spellcheck

Updates:
    2026-02-20 - tools.md2latex - supporting markdown specific function movement
    2026-02-15 - tools.md2latex - added --auto-label-caption
    2026-02-10 - tools.md2latex - FIX: template was not being passed along from md2latex to md2pdf
    2026-02-08 - tools.md2latex - FIX: spellcheck wasnt triggering on fatal, quotes picked up correctly now
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
from typing import List, Generator, Optional, Tuple, Dict
from dataclasses import dataclass, field, fields
from argparse import ArgumentParser
import pprint

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, dirpath, filename, is_file
from chriscarl.core.lib.stdlib.io import read_text_file
from chriscarl.core.functors.parse import markdown
from chriscarl.tools.shed import md2latex

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


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    markdown_filepath: str
    output_dirpath: str = ''
    bibliography_filepaths: List[str] = field(default_factory=lambda: [])
    template: str = md2latex.DEFAULT_TEMPLATE
    spellcheck_fatal: bool = False
    skip_spellcheck: bool = False
    auto_label_caption: bool = False
    # wc-applet
    word_count: bool = False
    # non-app
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('md2latex')
        app.add_argument('markdown_filepath', type=str, help='.md?')
        app.add_argument('--bibliography-filepaths', '--bibliographys', '-b', type=str, nargs='+', default=[], help='.md w/ bibtexs?')
        app.add_argument('--output-dirpath', '-o', type=str, default='', help='save outputs to different dir than input?')
        app.add_argument('--template', '-t', type=str, default=md2latex.DEFAULT_TEMPLATE, choices=md2latex.TEMPLATES, help='document style, really')
        app.add_argument('--spellcheck-fatal', '-sf', action='store_true', help='spellcheck fail is fatal')
        app.add_argument('--skip-spellcheck', '-ss', action='store_true', help='skip-spellcheck entirely')
        app.add_argument('--auto-label-caption', '-alc', action='store_true', help='auto label and auto caption if stuff is missing?')

        wc = parser.add_argument_group('word-count')
        wc.add_argument('--word-count', '-wc', action='store_true', help='get the word count, exit')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        if not is_file(self.markdown_filepath):
            raise OSError(f'markdown filepath "{self.markdown_filepath}" does not exist')
        for i, bibliography_filepath in enumerate(self.bibliography_filepaths):
            if not is_file(bibliography_filepath):
                raise OSError(f'bibliography filepath {i} "{bibliography_filepath}" does not exist')
        if self.output_dirpath:
            make_dirpath(self.output_dirpath)
        if self.debug:
            self.log_level = 'DEBUG'
        configure_ez(level=self.log_level, filepath=self.log_filepath)

    @classmethod
    def parse(cls, parser=None, argv=None):
        # type: (Optional[ArgumentParser], Optional[List[str]]) -> Arguments
        parser = parser or cls.argparser()
        ns = parser.parse_args(argv)
        arguments = cls(**(vars(ns)))
        arguments.process()
        return arguments

    def to_dict(self):
        return {fie.name: getattr(self, fie.name) for fie in fields(self)}


def log_error_warnings(phase, errors, warnings):
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
    template=md2latex.DEFAULT_TEMPLATE,
    wc=False,
    spellcheck_fatal=False,
    skip_spellcheck=False,
    auto_label_caption=False,
    debug=False,
):
    # type: (str, str, Optional[List[str]], str, bool, bool, bool, bool, bool) -> Tuple[str, str, List[Tuple[str, str]], Dict[str, str]]
    if template not in md2latex.TEMPLATES:
        raise ValueError(f'template {template!r} not in {list(md2latex.TEMPLATES)}')
    md2latex.assert_executables_exist()

    md_dirpath = dirpath(md_filepath)
    md_filename = filename(md_filepath)
    if not output_dirpath:
        output_dirpath = md_dirpath
    output_dirpath = abspath(output_dirpath)
    os.makedirs(output_dirpath, exist_ok=True)
    tex_output_filepath = abspath(output_dirpath, f'{md_filename}.tex')
    bibliography_output_filepath = abspath(output_dirpath, f'{md_filename}.bib')  # f'{latex.latex_remove(md_filename)}.bib'
    bibliography_filepaths = bibliography_filepaths or []

    # right off the rip
    md_content = read_text_file(md_filepath)
    if not md_content.endswith('\n'):
        md_content = f'{md_content}\n'
    md_content = md2latex.REGEX_MARKDOWN_EMPTY_LITERAL.sub('', md_content)

    word_count = md2latex.word_count(md_content)
    LOGGER.info('wc: %d', word_count)
    if wc:
        return '', '', [], {}

    # bibliographies
    phase, errors, warnings = 'bibtex', [], []
    LOGGER.info('running %r', phase)
    bibtex_labels, errors, warnings = md2latex.bibliographies_to_bibtex([md_filepath] + bibliography_filepaths, bibliography_output_filepath)
    log_error_warnings(phase, errors, warnings)

    # sections
    phase, errors, warnings = 'sections', [], []
    LOGGER.info('running %r', phase)
    sections, md_content = markdown.analyze_extract_sections(md_content)
    sections += markdown.analyze_large_sections(md_content)
    log_error_warnings(phase, errors, warnings)

    # doclets
    phase, errors, warnings = 'sections2doclets', [], []
    LOGGER.info('running %r', phase)
    doclets, interdoc_labels, download_url_filepaths, errors, warnings = markdown.sections_to_doclets(
        sections, md_filepath, output_dirpath=output_dirpath, auto_label_caption=auto_label_caption, use_angle_citations=True
    )
    log_error_warnings(phase, errors, warnings)

    phase, errors, warnings = 'labels', [], []
    LOGGER.info('running %r', phase)
    labels, errors, warnings = md2latex.process_labels(bibtex_labels, interdoc_labels)
    log_error_warnings(phase, errors, warnings)
    if debug:
        LOGGER.debug('labels: %s', pprint.pformat(labels, indent=2, width=160))

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
        log_error_warnings(phase, errors, warnings)

    # doclets to body
    phase, errors, warnings = 'doclets2latex', [], []
    LOGGER.info('running %r', phase)
    headers, renders, errors, warnings = md2latex.doclets_to_latex(doclets, md_filepath, bibliography_output_filepath, labels, template)
    if debug:
        LOGGER.debug('headers: %s', pprint.pformat(headers, indent=2, width=160))
        LOGGER.debug('renders: %s', pprint.pformat(renders, indent=2, width=160))
    log_error_warnings(phase, errors, warnings)

    # render
    phase, errors, warnings = 'doclets+latex2texfile', [], []
    LOGGER.info('running %r', phase)
    errors, warnings = md2latex.render_tex_file(headers, renders, tex_output_filepath)
    log_error_warnings(phase, errors, warnings)

    return bibliography_output_filepath, tex_output_filepath, download_url_filepaths, headers


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    bibliography_output_filepath, tex_output_filepath, _, _ = markdown_to_latex(
        args.markdown_filepath,
        args.output_dirpath,
        bibliography_filepaths=args.bibliography_filepaths,
        template=args.template,
        wc=args.word_count,
        spellcheck_fatal=args.spellcheck_fatal,
        skip_spellcheck=args.skip_spellcheck,
        auto_label_caption=args.auto_label_caption,
        debug=args.debug,
    )
    LOGGER.info('.bib at "%s"', os.path.relpath(bibliography_output_filepath, os.getcwd()))
    LOGGER.info('.tex at "%s"', os.path.relpath(tex_output_filepath, os.getcwd()))

    LOGGER.info('done!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
