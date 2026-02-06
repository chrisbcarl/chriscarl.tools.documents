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
    2026-02-04 - tools.md2bibtex - support for the refactors
    2026-01-25 - tools.md2bibtex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional
from dataclasses import dataclass, field
from argparse import ArgumentParser

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, filename
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

# tool constants


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    input_filepath: str
    skip_pretty: bool = False
    indent: int = 4
    overwrite: bool = False
    output_dirpath: str = DEFAULT_OUTPUT_DIRPATH
    # debug
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('input_filepath', type=str, help='what text file do you want to get the bibtex out of?')
        app.add_argument('--skip-pretty', '-sp', action='store_true', help='you want ugly???')
        app.add_argument('--indent', '-i', type=int, default=4, help='if pretty, indent by how many?')
        app.add_argument('--overwrite', action='store_true', help='overwrite the input filepath?')
        app.add_argument('--output-dirpath', '-o', type=str, default=DEFAULT_OUTPUT_DIRPATH, help='where do you want to save a text of the sequence? same filename will be used')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
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

    output_filepath = args.input_filepath
    if not args.overwrite:
        output_filepath = abspath(args.output_dirpath, f'{filename(args.input_filepath)}.bib')

    try:
        bib, _ = md2bibtex.text_to_bibtex(args.input_filepath, pretty=not args.skip_pretty, indent=args.indent)
        labels = bibtex.get_label_citation(bib, parse=False, pretty=True, nulls=False, dedupe=False)
    except Exception as ex:
        LOGGER.error('%s', ex)
        LOGGER.debug('%s', ex, exc_info=True)
        return 1

    LOGGER.info('encountered %d labels', len(labels))
    LOGGER.debug(list(labels))

    write_text_file(output_filepath, bib)
    LOGGER.info('wrote "%s"', output_filepath)
    return 0


if __name__ == '__main__':
    sys.exit(main())
