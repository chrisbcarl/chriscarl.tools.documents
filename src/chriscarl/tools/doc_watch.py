#!/usr/bin/env python
# -*- coding: utf-8 -*-
r'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-02-15
Description:

tools.doc_watch is a tool which polls a list of files and modifies them according to some heuristic

Examples:
    $ doc-watch `
        --md-table-pretty `
        --md-auto-latex `
        --exclude known-file.md

Updates:
    2026-02-27 16:42 - tools.doc_watch - finished toolification
    2026-02-15 21:58 - tools.doc_watch - finished first pass, the idea is to have some kind of doc watcher and you invoke it like this:
    2026-02-15 20:45 - tools.doc_watch - started

TODO:
    - markdown table regex doesnt work on tables that end the document
    - the service autoload or something?
    - deal with files that arent matcing the regex?
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional
from dataclasses import dataclass, field, fields
from argparse import ArgumentParser
import re
import time

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, walk_regex
from chriscarl.core.lib.stdlib.io import read_text_file, write_text_file
from chriscarl.core.lib.stdlib.hashlib import md5
from chriscarl.core.functors.parse.markdown import table_prettify
from chriscarl.core.types.str import indent

SCRIPT_RELPATH = 'chriscarl/tools/doc_watch.py'
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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.doc_watch')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.doc_watch.log')

# tool constants
DEFAULT_DIRPATH = abspath(os.getcwd())


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    # app
    md_table_pretty: List[str] = field(default_factory=lambda: [])
    md_auto_latex: List[str] = field(default_factory=lambda: [])
    exclude: List[str] = field(default_factory=lambda: [])
    # misc
    debug: bool = False
    dirpath: str = DEFAULT_OUTPUT_DIRPATH
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('--md-table-pretty', type=str, nargs='*', default=[], help='auto-format markdown tables?')
        app.add_argument('--md-auto-latex', type=str, nargs='*', default=[], help='auto-wrap latex looking stuff?')
        app.add_argument('--exclude', type=str, nargs='*', default=[], help='auto-wrap latex looking stuff?')
        app.add_argument('--dirpath', '-d', type=str, default=DEFAULT_DIRPATH, help='where do you want to monitor?')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        make_dirpath(self.dirpath)
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
        return {fie.name: getattr(self, fie.name) for fie in fields(self)}  # escaped for template reasons


REGEX_MARKDOWN_TABLE = re.compile(r'\n(?P<indent>[ \t]*)\|(?P<table>.+?)\|\n\n', flags=re.DOTALL | re.MULTILINE)


def md_table_pretty(filepaths):
    # type: (List[str]) -> List[str]
    '''return a list of successfully modified files'''
    modifieds = []
    for filepath in filepaths:
        markdown = read_text_file(filepath)
        prior_hash = md5(markdown)
        mos = list(REGEX_MARKDOWN_TABLE.finditer(markdown))
        for mo in reversed(mos):
            start, end = mo.span()
            start += 1  # the prepending \n
            groups = mo.groupdict()
            indentation = len(groups['indent'])
            table = f'|{groups["table"]}|'
            replacement = indent(table_prettify(table), indent=' ' * indentation)
            markdown = f'{markdown[:start]}{replacement}\n\n{markdown[end:]}'
        replaced_hash = md5(markdown)
        if prior_hash != replaced_hash:
            write_text_file(filepath, markdown)
            modifieds.append(filepath)
    return modifieds


KNOWN_FUNCS = {
    r'.*\.md$': [md_table_pretty, ],
}


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    LOGGER.debug('getting mtimes')
    last_modified_dict = {key: {filepath: os.path.getmtime(filepath) for filepath in walk_regex(args.dirpath, key, ignore=args.exclude)} for key in KNOWN_FUNCS}
    try:
        while True:
            for key, funcs in KNOWN_FUNCS.items():
                key_filepaths = walk_regex(args.dirpath, key, ignore=args.exclude)
                modified_since_last = []
                for filepath in key_filepaths:
                    modified = os.path.getmtime(filepath)
                    if (filepath in last_modified_dict[key]  # new file created
                        or modified > last_modified_dict[key][filepath]  # modified more recently
                        ):
                        modified_since_last.append(filepath)

                actually_modified = set()
                for func in funcs:
                    lst = func(modified_since_last)
                    if lst:
                        LOGGER.info('modified %d files with %r: %s', len(lst), func.__name__, lst)
                    actually_modified = actually_modified.union(lst)

                last_modified_dict[key].update({filepath: os.path.getmtime(filepath) for filepath in actually_modified})
            time.sleep(0.1)

    except KeyboardInterrupt:
        LOGGER.info('ctrl+c detected')

    return 0


if __name__ == '__main__':
    sys.exit(main())
