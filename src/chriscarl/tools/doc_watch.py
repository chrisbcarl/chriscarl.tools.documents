#!/usr/bin/env python
# -*- coding: utf-8 -*-
r'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-02-15
Description:

tools.doc_watch is a tool which polls a list of files and modifies them according to some heuristic

Examples:
    $ doc-watch dirs    ./          --md-table-pretty --md-auto-latex --exclude known-file.md
    $ doc-watch files   table.md    --md-table-pretty --md-auto-latex

Updates:
    2026-02-27 22:09 - tools.doc_watch - added dirs and files modes, have to rejigger a few projects but thats fine
    2026-02-27 16:42 - tools.doc_watch - finished toolification
                       tools.doc_watch - from a user perspective this works every very well.
    2026-02-15 21:58 - tools.doc_watch - finished first pass, the idea is to have some kind of doc watcher and you invoke it like this:
    2026-02-15 20:45 - tools.doc_watch - started

TODO:
    - add md_table_pivot
    - markdown table regex doesnt work on tables that end the document
    - the service autoload or something?
    - deal with files that arent matcing the regex?
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional, Tuple, Dict, Callable
from dataclasses import dataclass, field, fields
from argparse import ArgumentParser
import re
import time
import enum

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, walk_regex, relpath  # make_dirpath,
from chriscarl.core.lib.stdlib.io import read_text_file, write_text_file
from chriscarl.core.lib.stdlib.hashlib import md5
from chriscarl.core.functors.parse.markdown import table_prettify
from chriscarl.core.types.str import indent, find_lineno_index

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
class Modes(enum.Enum):
    dirs = enum.auto()
    files = enum.auto()

    def __str__(self):
        return f'{self.name}'

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        else:
            return super().__eq__(other)


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    # modes
    mode: str = ''
    # modes - dirs
    dirpaths: List[str] = field(default_factory=lambda: [])
    exclude: List[str] = field(default_factory=lambda: [])
    # modes - files
    filepaths: List[str] = field(default_factory=lambda: [])
    # common
    # common - funcs
    md_table_pretty: bool = False
    md_auto_latex: bool = False
    # common - misc
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @classmethod
    def add_common_arguments(cls, parser):
        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')

    @classmethod
    def add_common_funcs(cls, parser):
        funcs = parser.add_argument_group('funcs')
        funcs.add_argument('--md-table-pretty', action='store_true', help='auto-format markdown tables?')
        funcs.add_argument('--md-auto-latex', action='store_true', help='auto-wrap latex looking stuff?')

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        cls.add_common_arguments(parser)
        subparser_root = parser.add_subparsers(help='which mode do you want?')

        # dirs
        dirs = subparser_root.add_parser(str(Modes.dirs), description='long-running dirs which loops repeatedly on a directory with functions', formatter_class=ArgparseNiceFormat)
        dirs.set_defaults(mode='dirs')
        group = dirs.add_argument_group('core')
        group.add_argument('dirpaths', type=str, nargs='*', help='where do you want to monitor?')
        group.add_argument('--exclude', type=str, nargs='*', default=[], help='auto-wrap latex looking stuff?')
        cls.add_common_funcs(dirs)
        cls.add_common_arguments(dirs)

        # files
        files = subparser_root.add_parser(
            str(Modes.files), description='long-running files which loops repeatedly on a directory with functions', formatter_class=ArgparseNiceFormat
        )
        files.set_defaults(mode='files')
        group = files.add_argument_group('core')
        group.add_argument('filepaths', type=str, nargs='*', help='which files do you want to process?')
        cls.add_common_funcs(files)
        cls.add_common_arguments(files)

        return parser

    def process(self):
        # make_dirpath(self.dirpath)
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
    # type: (List[str]) -> Tuple[List[str], List[str]]
    '''return a list of successfully modified files'''
    modifieds = []
    error_file_msgs = []
    for filepath in filepaths:
        LOGGER.debug('"%s"', filepath)
        try:
            markdown = read_text_file(filepath)
        except Exception as ex:
            LOGGER.info('could not read "%s" bc %s, just ignoring, we might get them on the next pass', filepath, ex)
            continue
        prior_hash = md5(markdown)
        mos = list(REGEX_MARKDOWN_TABLE.finditer(markdown))
        for mo in reversed(mos):
            start, end = mo.span()
            start += 1  # the prepending \n
            groups = mo.groupdict()
            indentation = len(groups['indent'])
            table = f'|{groups["table"]}|'

            try:
                pretty = table_prettify(table)
                replacement = indent(pretty, indent=' ' * indentation)
            except Exception as ex:
                lineno = list(find_lineno_index(table, markdown))[0][0] + 1
                error_file_msgs.append((filepath, f'couldnt prettify! {ex}, "{filepath}", line {lineno}'))
                continue

            markdown = f'{markdown[:start]}{replacement}\n\n{markdown[end:]}'
        replaced_hash = md5(markdown)
        if prior_hash != replaced_hash:
            write_text_file(filepath, markdown)
            modifieds.append(filepath)
    return modifieds, error_file_msgs


KNOWN_FUNCS = {
    md_table_pretty: r'.*\.md$',
}
ERROR_PRINTED = {}  # type: Dict[str, str]
FILEPATHS_MODIFIED = {}  # type: Dict[str, float]


def process_files(filepaths, used_funcs, cwd=os.getcwd()):
    # type: (List[str], List[Callable[[List[str]], Tuple[List[str], List[str]]]], str) -> Tuple[List[str], List[str]]
    actually_modified = set()
    all_successes, all_errors = [], []
    for func in used_funcs:
        successes, failures = func(filepaths)
        error_file_msgs = [(relpath(tpl[0], cwd=cwd, posix=True), tpl[1]) for tpl in failures]
        if successes:
            LOGGER.info('%r succeeded on %d files', func.__name__, len(successes))
            for success in successes:
                # TODO: on better logging levels
                rel = relpath(success, cwd=cwd, posix=True)
                all_successes.append(rel)
                LOGGER.info('    - %r: %s', func.__name__, rel)
                if success in ERROR_PRINTED:
                    del ERROR_PRINTED[success]  # clear the error
        if error_file_msgs:
            topline_printed = False
            for file, msg in error_file_msgs:
                if file not in ERROR_PRINTED:
                    rel = relpath(file, cwd=cwd, posix=True)
                    if not topline_printed:
                        LOGGER.error('%r failed on %d files', func.__name__, len(error_file_msgs))
                        topline_printed = True

                    LOGGER.error('    - %r: "%s" | %s', func.__name__, rel, msg)
                    ERROR_PRINTED[file] = msg
                    all_errors.append(f'{func.__name__!r}: "{rel}" | {msg}')
        actually_modified = actually_modified.union(successes)

    FILEPATHS_MODIFIED.update({filepath: os.path.getmtime(filepath) for filepath in actually_modified})
    return all_successes, all_errors


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    cwd = abspath(os.getcwd())

    # identify what patterns we're interested in
    used_funcs = [func for func in KNOWN_FUNCS if getattr(args, func.__name__) == True]
    used_patterns = set(KNOWN_FUNCS[func] for func in used_funcs)
    used_regexes = [re.compile(pattern) for pattern in used_patterns]

    if not used_funcs:
        raise RuntimeError('no functions passed!')

    # scan for files
    LOGGER.debug('getting mtimes')
    if args.mode == Modes.files:
        for filepath in args.filepaths:
            if not any(regex.search(filepath) for regex in used_regexes):
                raise RuntimeError(f'passed file {filepath!r} does not match any known')
            FILEPATHS_MODIFIED[filepath] = os.path.getmtime(filepath)

    elif args.mode == Modes.dirs:
        for dirpath in args.dirpaths:
            for key in used_patterns:
                for filepath in walk_regex(dirpath, key, ignore=args.exclude, relpath=False):
                    FILEPATHS_MODIFIED[filepath] = os.path.getmtime(filepath)

    LOGGER.debug('FILEPATHS_MODIFIED: %s', FILEPATHS_MODIFIED)

    if not FILEPATHS_MODIFIED:
        raise RuntimeError('not enough files or dirpaths to actually run anything!')

    try:
        if args.mode == Modes.files:
            process_files(list(FILEPATHS_MODIFIED), used_funcs, cwd=cwd)
        elif args.mode == Modes.dirs:
            while True:
                modified_since_last = []
                for filepath in FILEPATHS_MODIFIED:
                    modified = os.path.getmtime(filepath)
                    if (filepath not in FILEPATHS_MODIFIED  # new file created
                        or modified > FILEPATHS_MODIFIED[filepath]  # modified more recently
                        ):
                        modified_since_last.append(filepath)
                if modified_since_last:
                    LOGGER.debug('FILEPATHS_MODIFIED: %s', FILEPATHS_MODIFIED)
                    process_files(modified_since_last, used_funcs, cwd=cwd)
                time.sleep(0.1)

    except KeyboardInterrupt:
        LOGGER.info('ctrl+c detected')

    return 0


if __name__ == '__main__':
    sys.exit(main())
