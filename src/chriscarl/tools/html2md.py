#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-31
Description:

tools.html2md is a tool which really just wraps markdownify and its CLI script.

Updates:
    2026-08-30 - tools.html2md - html2md supports multiple filepaths
    2026-01-31 - tools.html2md - initial commit
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
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, dirpath
from chriscarl.core.lib.stdlib.io import write_text_file
from chriscarl.core.types.str import indent
from chriscarl.tools.shed import html2md

SCRIPT_RELPATH = 'chriscarl/tools/html2md.py'
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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.html2md')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.html2md.log')

# tool constants


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    input_filepaths: List[str] = field(default_factory=lambda: [])
    output_filepaths: List[str] = field(default_factory=lambda: [])
    # non-app
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH
    no_pretty: bool = False

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('input_filepaths', type=str, nargs='*', help='original html to deal with')
        app.add_argument('--output-filepaths', '-o', type=str, nargs='*', default=[], help='if provided, store somewhere other than right next door')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        misc.add_argument('--no-pretty', action='store_true', help='keep tables un-prettified (rows are variable length)')
        return parser

    def process(self):
        if not self.output_filepaths:
            self.output_filepaths = [''] * len(self.input_filepaths)
            for i, input_filepath in enumerate(self.input_filepaths):
                filename = os.path.splitext(input_filepath)[0]
                self.output_filepaths[i] = f'{filename}.md'
                make_dirpath(dirpath(self.output_filepaths[i]))
        elif len(self.input_filepaths) != len(self.output_filepaths):
            raise RuntimeError(f'Amount of --output-filepaths are provided does not match --input-filepaths! Must provide 0 output filepaths or ALL output filepaths.')

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


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    for _, tpl in enumerate(zip(args.input_filepaths, args.output_filepaths)):
        # NOTE: may want to do progress, not sure.
        input_filepath, output_filepath = tpl
        markdown = html2md.html_to_markdown(input_filepath, pretty=not args.no_pretty)
        LOGGER.info('reading from "%s"', input_filepath)
        print(indent(markdown))
        write_text_file(output_filepath, markdown)
        LOGGER.info('wrote to "%s"', output_filepath)

    return 0


if __name__ == '__main__':
    sys.exit(main())
