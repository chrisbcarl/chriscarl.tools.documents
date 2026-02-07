#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-02-06
Description:

tools.shed.tex2pdf is functions that takes LaTeX and converts them to PDF
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

Updates:
    2026-02-06 - tools.shed.tex2pdf - initial commit
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
from chriscarl.core.lib.stdlib.io import read_text_file_try
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


def run_pdflatex(md_filename, output_dirpath, template):
    # run pdflatex 4 times...
    LOGGER.debug('deleting previous work files...')
    md2latex.delete_latex_work_files(output_dirpath, md_filename)

    if template == 'ieee':
        bibtex_cmd = 'bibtex'
    else:
        bibtex_cmd = 'biber'
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
            LOGGER.error('%d / %d - %s, TIMEOUT %0.2f sec!\n%s', c + 1, len(cmds), subprocess.list2cmdline(cmd), timeout, read_text_file_try(stdout))
            sys.exit(2)
        finally:
            os.remove(stdout)
