#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.md2bibtex is a tool which can extract all of the BibTex in a file and prettify it.

Examples:
    md2bibtex tests/collateral/md2latex/paper.md `
        --output-dirpath files/examples/md2bibtex `
        --skip-pretty

Updates:
    2026-02-06 - tools.md2bibtex - changed to accept multiple filepaths or combine
    2026-02-04 - tools.md2bibtex - support for the refactors
    2026-01-25 - tools.md2bibtex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional, Dict, Tuple
from dataclasses import dataclass, field, fields
from argparse import ArgumentParser
import json

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, filename, is_file
from chriscarl.core.lib.stdlib.io import write_text_file
from chriscarl.core.functors.parse import bibtex
from chriscarl.tools.shed import md2bibtex

SCRIPT_RELPATH = 'chriscarl/tools/md2bibtex.py'
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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.md2bibtex')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.md2bibtex.log')
DEFAULT_COMBINED_FILENAME = 'bibliography.bib'

# tool constants


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    input_filepaths: List[str]
    skip_pretty: bool = False
    indent: int = 4
    overwrite: bool = False
    output_dirpath: str = DEFAULT_OUTPUT_DIRPATH
    combine: bool = False
    combined_filename: str = DEFAULT_COMBINED_FILENAME
    # debug
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('input_filepaths', type=str, nargs='+', help='what text files do you want to get the bibtex out of?')
        app.add_argument('--skip-pretty', '-sp', action='store_true', help='you want ugly???')
        app.add_argument('--indent', '-i', type=int, default=4, help='if pretty, indent by how many?')
        app.add_argument('--overwrite', action='store_true', help='overwrite the input filepath?')
        app.add_argument('--output-dirpath', '-o', type=str, default=DEFAULT_OUTPUT_DIRPATH, help='where do you want to save a text of the sequence? same filename will be used')
        app.add_argument('--combine', '-c', action='store_true', help='combine them into one --combine-filename?')
        app.add_argument('--combined-filename', type=str, default=DEFAULT_COMBINED_FILENAME, help='if files > 1, combine them all into one filename?')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        for i, input_filepath in enumerate(self.input_filepaths):
            if not is_file(input_filepath):
                raise OSError(f'input filepath {i} "{input_filepath}" does not exist')
        make_dirpath(self.output_dirpath)
        if self.debug:
            self.log_level = 'DEBUG'
        configure_ez(level=self.log_level, filepath=self.log_filepath)

    @classmethod
    def parse(cls, parser=None, argv=None):
        # type: (Optional[ArgumentParser], Optional[List[str]]) -> Arguments
        parser = parser or Arguments.argparser()
        ns = parser.parse_args(argv)
        arguments = Arguments(**(vars(ns)))
        arguments.process()
        return arguments

    def to_dict(self):
        return {fie.name: getattr(self, fie.name) for fie in fields(self)}


def combine(input_filepaths, output_filepath, pretty=True, indent=4):
    # type: (List[str], str, bool, int) -> Tuple[str, Dict[str, str]]
    '''
    Description:
        analyze all files for bibtex, combine into one file, return the content and labels
    Arguments:
        input_filepaths: List[str]
        output_filepath: str
        pretty: bool
        indent: int
            default 4
    Returns:
        Tuple[str, Dict[str, str]]
            bib, labels
    '''
    bibs = []
    labels = {}
    for i, input_filepath in enumerate(input_filepaths):
        LOGGER.info('%d / %d - "%s" parsing', i + 1, len(input_filepaths), input_filepath)
        bib, _ = md2bibtex.text_to_bibtex(input_filepath, pretty=pretty, indent=indent)
        LOGGER.debug('"%s"\n%s', input_filepath, bib)
        bibs.append(bib)

    bib = '\n'.join(bibs)
    labels = bibtex.get_label_citation(bib, parse=False, pretty=True, nulls=False, dedupe=False)
    write_text_file(output_filepath, bib)
    LOGGER.info('wrote "%s"', output_filepath)

    return bib, labels


def convert(input_filepaths, output_dirpath, pretty=True, indent=4, overwrite=False):
    # type: (List[str], str, bool, int, bool) -> Tuple[str, Dict[str, str]]
    '''
    Description:
        analyze all files for bibtex, export them to INDIVIDUAL files, return the combined content and labels
    Arguments:
        input_filepaths: List[str]
        output_dirpath: str
            DIFFERENT from combine
        pretty: bool
        indent: int
            default 4
        overwrite: bool
            default False
            overwrite the files they came from? disregard the dirpath?
            DIFFERENT from combine
    Returns:
        Tuple[str, Dict[str, str]]
            bib, labels
    '''
    bibs = []
    labels = {}
    for i, input_filepath in enumerate(input_filepaths):
        LOGGER.info('%d / %d - "%s" parsing', i + 1, len(input_filepaths), input_filepath)
        output_filepath = input_filepath
        if not overwrite:
            output_filepath = abspath(output_dirpath, f'{filename(input_filepath)}.bib')

        bib, _ = md2bibtex.text_to_bibtex(input_filepath, pretty=pretty, indent=indent)
        these_labels = bibtex.get_label_citation(bib, parse=False, pretty=True, nulls=False, dedupe=False)
        labels.update(these_labels)

        LOGGER.info('%d / %d - "%s" encountered %d labels', i + 1, len(input_filepaths), input_filepath, len(labels))
        LOGGER.debug(list(labels))

        write_text_file(output_filepath, bib)
        LOGGER.info('%d / %d - wrote "%s"', i + 1, len(input_filepaths), output_filepath)

    bib = '\n'.join(bibs)
    return bib, labels


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    try:
        if args.combine:
            LOGGER.info('running combine')
            combined_filepath = abspath(args.output_dirpath, args.combined_filename)
            bib, labels = combine(
                args.input_filepaths,
                combined_filepath,
                pretty=not args.skip_pretty,
                indent=args.indent,
            )
        else:
            LOGGER.info('running convert')
            bib, labels = convert(
                args.input_filepaths,
                args.output_dirpath,
                pretty=not args.skip_pretty,
                indent=args.indent,
                overwrite=args.overwrite,
            )
    except Exception as ex:
        LOGGER.error('%s', ex)
        LOGGER.debug('%s', ex, exc_info=True)
        return 1

    if args.debug:
        LOGGER.debug('bibtex labels: %s', json.dumps(labels))
    if not bib:
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
