#!/usr/bin/env python
# -*- coding: utf-8 -*-
r'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-02-06
Description:

tools.shed.tex2pdf is functions that takes LaTeX and converts them to PDF
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

Updates:
    2026-04-03 - tools.shed.tex2pdf - if no bibliography contents, dont bother rendering...
    2026-02-06 - tools.shed.tex2pdf - initial commit

TODO:
    - figure out a way to read the upside down question mark, BIG_BAD. it needs to show up as text, not in the pdf data itself.
        - re.findall(r'[\u0000-\u00FF]¿[\u0000-\u00FF]', content)
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import subprocess
import tempfile

# third party imports

# project imports
from chriscarl.core.lib.stdlib.os import abspath, is_file
from chriscarl.core.lib.stdlib.io import read_text_file
from chriscarl.core.lib.stdlib.subprocess import kill
from chriscarl.tools.shed import md2latex

SCRIPT_RELPATH = 'chriscarl/tools/shed/tex2pdf.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

BIG_BAD = '¿'


def run_pdflatex(md_filename, output_dirpath, template):
    # run pdflatex 4 times...
    LOGGER.debug('deleting previous work files...')
    md2latex.delete_latex_work_files(output_dirpath, md_filename)

    if template == 'ieee':
        bibtex_cmd = 'bibtex'
    else:
        bibtex_cmd = 'biber'

    bibtex_contents = ''
    bibtex_filepath = abspath(output_dirpath, f'{md_filename}.bib')
    if is_file(bibtex_filepath):
        bibtex_contents = read_text_file(bibtex_filepath).strip()
    if not bibtex_contents:
        LOGGER.info('no bibliographical content detected, skipping the 4x commands')
        cmds = [
            ['pdflatex', md_filename],
        ]
    else:
        cmds = [
            # ['latexmk', '-C'],  # clean all aux files
            ['pdflatex', md_filename],
            [bibtex_cmd, md_filename],
            ['pdflatex', md_filename],
            ['pdflatex', md_filename],
        ]
    timeout = 60
    for c, cmd in enumerate(cmds):
        pid = -1
        fd, stdout = tempfile.mkstemp()
        os.close(fd)
        try:
            LOGGER.info('%d / %d - %s', c + 1, len(cmds), subprocess.list2cmdline(cmd))
            with open(stdout, 'w', encoding='utf-8') as w:
                p = subprocess.Popen(cmd, cwd=output_dirpath, stdout=w, stderr=w, universal_newlines=True)
                pid = p.pid
                res = p.wait(timeout=timeout)  # NOTE: biber can actually take like 20 seconds or so
            if res != 0:
                with open(stdout, 'r', encoding='utf-8') as r:
                    print(r.read())
                LOGGER.error('%d / %d - %s, ERROR!', c + 1, len(cmds), subprocess.list2cmdline(cmd))
                sys.exit(res)
        except subprocess.TimeoutExpired:
            kill(pid)
            LOGGER.error('%d / %d - %s, TIMEOUT %0.2f sec!\n%s', c + 1, len(cmds), subprocess.list2cmdline(cmd), timeout, read_text_file(stdout))
            sys.exit(2)
        finally:
            os.remove(stdout)

    # from chriscarl.core.lib.stdlib.os import abspath
    # from chriscarl.core.lib.stdlib.io import read_text_file_try
    # pdf_filepath = abspath(output_dirpath, md_filename)
    # try:
    #     pdf_content = read_text_file_try(pdf_filepath)
    #     instances = pdf_content.count(BIG_BAD)
    #     if instances > 0:
    #         LOGGER.error('%r detected, %d instances! Perhaps bad references?', BIG_BAD, instances)
    # except Exception:
    #     pass
