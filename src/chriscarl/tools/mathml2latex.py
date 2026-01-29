#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-28
Description:

tools.mathml2latex is a tool which takes MathML crap and turns it into LaTeX.

Examples:
    - make a file /temp/mathml.xml
    - Right Click > Copy to Clipboard > "MathML Code"
    $ mathml2latex /temp/mathml.xml

Updates:
    2026-01-28 - tools.mathml2latex - initial commit

TODO:
    - its current conversion is bad, probably owed to the underlying translation from npm to python
    - it may be "worth it" to do something from scratch. otherwise i'll have to bandage forever.
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional
from dataclasses import dataclass, field
from argparse import ArgumentParser
import re

# third party imports
try:
    from mathml_to_latex.converter import MathMLToLaTeX
except ImportError:
    print('pip install mathml-to-latex', file=sys.stderr)
    sys.exit(1)

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, dirpath, as_posix
from chriscarl.core.lib.stdlib.io import read_text_file, write_text_file
import chriscarl.files.manifest_academia as ma
from chriscarl.core.lib.stdlib.subprocess import run

SCRIPT_RELPATH = 'chriscarl/tools/mathml2latex.py'
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
DEFAULT_OUTPUT_FILEPATH = abspath(TEMP_DIRPATH, 'tools.mathml2latex', 'output.tex')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.mathml2latex.log')

# tool constants
REGEX_MATHML = re.compile(r'<math [^>]+?>.+?<\/math>', flags=re.MULTILINE | re.DOTALL)


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    input_filepath: str
    output_filepath: str = DEFAULT_OUTPUT_FILEPATH
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('input_filepath', type=str, help='which one has the file?')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--output-filepath', '-o', type=str, default=DEFAULT_OUTPUT_FILEPATH, help='where do you want to save a text? if omitted, prints to stdout')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        make_dirpath(dirpath(self.output_filepath))
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


BAD_HOMBRES = {
    '⋯': r'\cdots',
    r'\overset{\overline}': r'\bar',
    r'&': r'',  # not worth the headache
}


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    converter = MathMLToLaTeX()
    content = read_text_file(args.input_filepath)
    latexes = []
    for mo in REGEX_MATHML.finditer(content):
        mathml = content[mo.start():mo.end()]
        latex = converter.convert(mathml)
        for k, v in BAD_HOMBRES.items():
            latex = latex.replace(k, v)
        latexes.append(latex)

    if args.output_filepath != DEFAULT_OUTPUT_FILEPATH:
        template = read_text_file(ma.FILEPATH_MATHML2LATEX_TEMPLATE)
        print(type(template))
        output_dirpath = dirpath(args.output_filepath)
        filename = os.path.splitext(args.output_filepath)[0]
        output_pdf_filepath = f'{filename}.pdf'
        compile = f'pdflatex {as_posix(filename)} -output-directory="{as_posix(output_dirpath)}"'
        body = '\n'.join(f'\\begin{{math}}\n    {latex}\n\\end{{math}}\n' for latex in latexes)

        render = template.replace('<COMPILE>', compile)
        render = render.replace('<BODY>', body)
        write_text_file(args.output_filepath, render)
        LOGGER.info('wrote "%s"', args.output_filepath)
        LOGGER.info('compiling with: %s', compile)
        rc, stdout = run(compile)
        if rc != 0:
            LOGGER.error('failed to compile!')
            LOGGER.warning(stdout)
        else:
            LOGGER.info('pdf at "%s"', output_pdf_filepath)
    else:
        for latex in latexes:
            print(f'{latex}\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
