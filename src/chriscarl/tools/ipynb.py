#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-02-23
Description:

tools.ipynb is a tool which can format a .ipynb notebook to my taste.
Use this if you recently modified an ipynb but didnt REALLY modify it that much just executed a few new cells, got some new output
    And now the cell execution order is all messed up AND you forgot how to export stuff
Well here you go.
Was `ipynb-toc-export-execute-html.py` in a former life...

Updates:
    2026-02-23 - tools.ipynb - created chriscarl.tools.documents as 'ipynb'
    2025-07-19 - tools.ipynb - selenium print, shifted toc description to this script rather than embedded somehow in the template.
    2025-07-12 - tools.ipynb - even better export processing, light refactor
    2025-06-22 - tools.ipynb - code blocks are ignored for TOC purposes, FIRST TOC cell is used as TOC area, all cells end in a newline
    2025-03-23 - tools.ipynb - initial commit

Examples:
    > # export only (automatically removes navigational aids and sanitizes)
    > ipynb notebook.ipynb

    > # execute, then export
    > ipynb notebook.ipynb --execute

    > # either is equivalent--inplace, remove the navigational aids, sanitize
    > ipynb notebook.ipynb --no-navigational-aids --no-toc --no-export
    > ipynb notebook.ipynb --clean --output-dirpath /tmp


TODO:
    - refactor this so it logically reads easier
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional, Tuple
from dataclasses import dataclass, field, fields
from argparse import ArgumentParser
import subprocess
import shutil
import re

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, is_file, dirpath, filename
from chriscarl.core.lib.stdlib.io import ReadWriteText
from chriscarl.core.lib.stdlib.json import ReadWriteJson
from chriscarl.core.lib.stdlib.subprocess import launch_editor
from chriscarl.core.lib.third import selenium

SCRIPT_RELPATH = 'chriscarl/tools/ipynb.py'
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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.ipynb')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.ipynb.log')

# tool constants
HEADER_DESCRIPTIONS = {
    # # Header
    'Project': 'basic details and bibliography.',
    'Abstract': 'executive summary of this file.',
    'TOC': 'what it says on the tin.',
    'Question': 'the actual question being asked.',
    'Answer': 'the "overall" answer to the question.',
    # ## SubHeaders
    'Background': 'reasonable background academic information that would be good to know.',
    'Solution': 'is the "justification" for providing the answer above.',
    'The Plan': 'is a pseudocode strategy for what the work is likely going to entail.',
    'Code - Environment': 'software notes on how to install the exact environment used in this project.',
    'Code - Setup': 'is ignorable boilerplate code that sets up stdlib, third party, constants, and seeds, acts as a safety valve for dependency checking.',
    'Code - Functions': 'is somewhat ignorable boilerplate functions for things like plotting or visualization that do not directly impact the main logic.',
    'Code - Main': 'is the main beef.',
    # # Header
    'Post Mortem': 'musings about the aftermath. The conclusion is already highlighted in the [Answer](#Answer) section.',
    # ## SubHeaders
    'Caveats': 'warnings or musings about trepidations or doubts encountered during answer development.',
    'Improvements': 'musings about what could be improved on the next attempt with a project like this.',
    'Further Reading': 'what it says on the tin.',
    'Replication': 'instructions for how the reader might replicate the learnings from this project on their own.',
    'Hardware': 'hardware notes if one wanted to replicate things exactly.',
    'Data': 'notes on how to obtain the data(s) used in the project.',
    # # Header
    'Appendix': 'back of the project',
    # ## SubHeaders
    'Reference': 'back of the book style references',
    'Grading Criterion': 'grading criterion for the project if known in advance.',
    'Definitions, Formulae, Theory': 'the actual back of the book.',
    'Changelog': 'proof of work.',
}
EQUAL_HEADERS = {
    'TOC': 'Table of Contents',
    'Grading Criterion': 'Criterion',
    'Grading Criterion': 'Prompt',
    'Grading Criterion': 'Assignment Text',
    'Grading Criterion': 'Instructions',
}
for _header, _equal_header in EQUAL_HEADERS.items():
    HEADER_DESCRIPTIONS[_equal_header] = HEADER_DESCRIPTIONS[_header]


class ReadWriteIpynb(ReadWriteJson):

    @property
    def ipynb(self):
        return self.body

    @ipynb.setter
    def ipynb(self, body):
        self.body = body


TOC_SENTINEL = '<!-- MY TOC GENERATOR -->'
OLD_BOTTOM_CELL = {
    'cell_type': 'markdown',
    'metadata': {},
    'source': [
        '<a id="bottom"></a>\n',
        '<br><a href="#top">Go to Top</a> | <a href="#bottom">Go to bottom</a>\n',
    ]
}
NEW_BOTTOM_CELL = {
    'cell_type': 'markdown',
    'metadata': {},
    'source': [
        '<a id="bottom"></a>\n',
        '<a href="#top">&#x21E7</a> | <a href="#bottom">&#x21E9</a>\n',
    ]
}
NAVIGATIONAL_AID_ANCHOR = '<a href="#top">'
GENERIC_AID_TOKENS = [('&#x21E7', 'top'), ('&#x21E9', 'bottom')]


def create_navigational_aid(header_slug_tokens):
    # type: (List[Tuple[str, str]]) -> str
    aid = ' | '.join(f'<a href="#{slug}">{header}</a>' for header, slug in header_slug_tokens)
    return f'{aid}<br>\n'


def remove_from_list(text, lst):
    # , case=False?
    del_me = []
    for idx, line in enumerate(lst):
        if text.lower() in line.lower():
            del_me.append(idx)
    for idx in reversed(del_me):
        lst.pop(idx)
    return lst


def find_in_lst(text, lst):
    for idx, line in enumerate(lst):
        if text.lower() in line.lower():
            return idx
    return -1


def ipynb_clean(rwi):
    # (ReadWriteIpynb) -> None
    '''
    remove navigational aids
    trim trailing spaces
    '''
    for c, cell in enumerate(rwi.ipynb['cells']):
        if cell['cell_type'] == 'markdown':
            if not cell['source']:  # because empty:
                continue
            try:
                # remove navigational aid
                cell['source'] = remove_from_list(NAVIGATIONAL_AID_ANCHOR, cell['source'])

                # remove trailing spaces
                for idx, line in enumerate(cell['source']):
                    if line.endswith(' '):
                        cell['source'][idx] = re.sub(r'( +)$', '', line)

                # removing anchors
                first_line = cell['source'][0]
                while '<a' in first_line and '/a>' in first_line:
                    cell['source'].pop(0)
                    if not cell['source']:
                        break
                    first_line = cell['source'][0]

                # removing TOC
                found = False
                remove = []
                for i, line in enumerate(cell['source']):
                    if TOC_SENTINEL in line:
                        if found:
                            found = False
                            remove.append(i)
                        else:
                            found = True
                            remove.append(i)
                    elif found:
                        remove.append(i)
                for r in reversed(remove):
                    cell['source'].pop(r)
            except Exception:
                LOGGER.debug(''.join(cell['source']))
                LOGGER.debug('cell %s', c)
                raise


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    # app
    input_filepath: str
    clean: bool = False
    only_remove_toc: bool = False
    execute: bool = False
    no_export: bool = False
    no_navigational_aids: bool = False
    no_toc: bool = False
    no_clean_post: bool = False
    no_pdf: bool = False
    no_open: bool = False
    # misc
    debug: bool = False
    output_dirpath: str = DEFAULT_OUTPUT_DIRPATH
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @classmethod
    def argparser(cls):
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('input_filepath', type=str, help='ipynb?')
        app.add_argument('--clean', action='store_true', help='remove navigational aids, remove the toc contents, dont export, etc.')
        app.add_argument('--only-remove-toc', action='store_true', help='ONLY remove TOC')
        app.add_argument('--execute', '--exec', '-e', action='store_true', help='actually execute the thing? and have it save over itself?')
        app.add_argument('--no-export', action='store_true', help='probably only use during debug?')
        app.add_argument('--no-navigational-aids', '--no-nav-a', action='store_true', help='do not add go to top/go to bottom on every markdown cell?')
        app.add_argument('--no-toc', action='store_true', help='do not add a TOC probably in cell 1?')
        app.add_argument('--no-clean-post', action='store_true', help='after export, DO NOT remove navigational aids, toc contents')
        app.add_argument('--no-pdf', action='store_true', help='do not export pdf?')
        app.add_argument('--no-open', action='store_true', help='do not open files after creation?')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--output-dirpath', '-o', type=str, default=DEFAULT_OUTPUT_DIRPATH, help='where do you want to save a text of the sequence')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        if not is_file(self.input_filepath):
            raise OSError("input_filepath does not exist!")
        if self.clean:
            self.no_navigational_aids = True
            self.no_toc = True
            self.no_export = True
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
        return {fie.name: getattr(self, fie.name) for fie in fields(self)}  # escaped for template reasons


def ipynb(
    input_filepath,
    output_dirpath=DEFAULT_OUTPUT_DIRPATH,
    clean=False,
    no_navigational_aids=False,
    no_toc=False,
    no_export=False,
    only_remove_toc=False,
    execute=True,
    no_pdf=False,
    no_clean_post=False,
    no_open=False,
):
    # type: (str, str, bool, bool, bool, bool, bool, bool, bool, bool, bool) -> List[str]
    results = []
    if clean:
        no_navigational_aids = True
        no_toc = True
        no_export = True

    with ReadWriteIpynb(filepath=input_filepath) as rwi:
        LOGGER.info('undoing any navigational aids...')
        ipynb_clean(rwi)

        LOGGER.info('modifying all cells to include a \\n in the last string')
        for c, cell in enumerate(rwi.ipynb['cells']):
            if not cell['source']:
                continue
            if not cell['source'][-1].endswith('\n'):
                cell['source'][-1] = cell['source'][-1] + '\n'

        LOGGER.info('removing empty markdown cells...')
        empty_markdowns = []
        for c, cell in enumerate(rwi.ipynb['cells']):
            if cell['cell_type'] == 'markdown':
                if not cell['source']:  # because empty:
                    empty_markdowns.append(c)
        for r in reversed(empty_markdowns):
            rwi.ipynb['cells'].pop(r)

        if only_remove_toc:
            LOGGER.info('done')
            return results

        headers = []
        if not no_toc:
            LOGGER.info('analyzing toc...')
            toc_idx = -1
            for c, cell in enumerate(rwi.ipynb['cells']):
                if cell['cell_type'] == 'markdown':
                    source = ''.join(cell['source'])
                    cellow = source.lower()
                    add_slug_id = ''
                    # . matches ALL including spaces, newlines, etc.
                    source = re.sub(r'(```.+```)', '', source, flags=re.S)  # anything in between two ``` should be ignored, like code blocks in markdown.
                    for line in source.splitlines():
                        if 'TOC' in source or 'table of contents' in cellow:
                            # find the first TOC or table of contents cell, and dont modify it again
                            if toc_idx == -1:
                                toc_idx = c
                        mo = re.search(r'^(#+) ?(.+)', line)
                        if not mo:
                            continue
                        # LOGGER.info(line)
                        groups = mo.groups()
                        heading = len(groups[0])
                        header = groups[1]
                        add_slug_id = slug_id = '-'.join(header.split())
                        headers.append((c, heading, header, slug_id))
                    if add_slug_id:
                        cell['source'].insert(0, f'<a id="{add_slug_id}"></a>\n')

            if toc_idx != -1:
                toc = rwi.ipynb['cells'][toc_idx]
                toc_lines = [f'{TOC_SENTINEL}\n']
                for _, heading, header, slug_id in headers:
                    header_description = HEADER_DESCRIPTIONS.get(header, "")
                    if header_description:
                        header_description = f': {header_description}'
                    toc_line = f'{" " * 4 * (heading - 1)}- [{header}](#{slug_id}){header_description}\n'
                    toc_lines.append(toc_line)
                toc_lines.append(f'{TOC_SENTINEL}\n')
                toc['source'] += toc_lines

        # right underneath the header, i populate the subheaders as a helpful navi (after the paragraph text)
        idx = 0
        while idx < len(headers):
            top_c, top_heading, top_header, top_slug_id = headers[idx]
            cell = rwi.ipynb['cells'][top_c]
            toc_lines = []
            for inner_c, inner_heading, inner_header, inner_slug_id in headers[idx + 1:]:
                if inner_heading <= top_heading:
                    break
                toc_lines.append(f'{" " * 4 * (inner_heading - 1 - top_heading)}- [{inner_header}](#{inner_slug_id})\n')
            if toc_lines:
                # first = cell['source'][0:2]  # original header and now the navigational aid <a id=""...
                # last = cell['source'][2:]
                # new_src = first + [f'{TOC_SENTINEL}\n'] + toc_lines + [f'{TOC_SENTINEL}\n'] + last
                new_src = cell['source'] + [f'{TOC_SENTINEL}\n'] + toc_lines + [f'{TOC_SENTINEL}\n']
                # LOGGER.info(''.join(new_src))
                cell['source'] = new_src
            idx += 1

        if not no_navigational_aids:
            LOGGER.info('adding navigational aids for top/bottom per cell...')
            header_next_idx = 0
            header_next_line = 0
            header_prev = []
            header_next = []  # type: List[Tuple[str, str]]
            for c, cell in enumerate(rwi.ipynb['cells']):
                if c == len(rwi.ipynb['cells']) - 1:  # do not add navigational aids to the bottom of the screen...
                    continue
                if cell['cell_type'] == 'markdown':
                    if not cell['source']:
                        continue
                    last_line = cell['source'][-1]

                    # get the next and prev header
                    if c >= header_next_line:
                        header_next_idx += 1
                    if header_next_idx >= len(headers):
                        header_prev = header_next
                        header_next.clear()
                    else:
                        header_next_line, _, header_next_name, header_next_slug = headers[header_next_idx]
                        # header_next = [(f'&#x21E8 (Next) {header_next_name}', header_next_slug)]
                        header_next = [('&#x21E8', header_next_slug)]  # right arrow
                        if header_next_idx > 1:
                            header_prev_line, _, header_prev_name, header_prev_slug = headers[header_next_idx - 2]
                            header_prev = [('&#x21E6', header_prev_slug)]  # left arrow

                    navigational_aid = create_navigational_aid(header_prev + GENERIC_AID_TOKENS + header_next)
                    if find_in_lst(NAVIGATIONAL_AID_ANCHOR, cell['source']) == -1:
                        if len(cell['source']) > 1 and cell['source'][1].startswith('#'):  # a header
                            cell['source'].insert(2, navigational_aid)
                        else:
                            cell['source'].insert(0, navigational_aid)
                    # if NAVIGATIONAL_AID_ANCHOR not in last_line.lower():
                    #     cell['source'].append(navigational_aid)
                    # else:
                    #     cell['source'][-1] = navigational_aid

            LOGGER.info('adding navigational anchors top and bottom...')
            top = '<a id="top"></a><br>\n'
            if rwi.ipynb['cells'][0]['cell_type'] == 'markdown':
                if 'id="top"' not in rwi.ipynb['cells'][0]['source'][0]:
                    rwi.ipynb['cells'][0]['source'].insert(0, top)
            else:
                rwi.ipynb['cells'].insert(
                    0,
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": [top]
                    },
                )
            if rwi.ipynb['cells'][-1] != OLD_BOTTOM_CELL and rwi.ipynb['cells'][-1] != NEW_BOTTOM_CELL:
                rwi.ipynb['cells'].append(NEW_BOTTOM_CELL)
            # bottom = '<br><a id="bottom"></a>\n'
            # if rwi.ipynb['cells'][-1]['cell_type'] == 'markdown':
            #     if not rwi.ipynb['cells'][-1]['source']:
            #         rwi.ipynb['cells'][-1]['source'] = [NAVIGATIONAL_AID_FULL, bottom]
            #     elif 'id="bottom"' not in rwi.ipynb['cells'][-1]['source'][-1]:
            #         rwi.ipynb['cells'][-1]['source'].append(bottom)
            # else:
            #     rwi.ipynb['cells'].append({
            #         "cell_type": "markdown",
            #         "metadata": {},
            #         "source": [NAVIGATIONAL_AID_FULL, bottom],
            #     })

        if not execute:
            LOGGER.info('sanitizing execution count')
            execution_count = 1
            for cell in rwi.ipynb['cells']:
                if cell['cell_type'] == 'code':
                    cell['execution_count'] = execution_count
                    execution_count += 1

    # case correct all slugs
    slugs = {tpl[-1] for tpl in headers}
    LOGGER.info(f'case-correcting {len(slugs)} slugs')
    with ReadWriteText(input_filepath) as rwt:
        for slug in slugs:
            slug_life = f'#{slug}'
            rwt.text = re.sub(re.escape(slug_life), slug_life, rwt.text, flags=re.IGNORECASE)

    fname = filename(input_filepath)
    if output_dirpath == DEFAULT_OUTPUT_DIRPATH:
        output_dirpath = dirpath(input_filepath)
        LOGGER.info('setting output dirpath to "%s"', output_dirpath)

    if execute:
        LOGGER.info('executing...')
        cmd = ['jupyter', 'nbconvert', '--execute', '--to', 'notebook', '--inplace', input_filepath]
        LOGGER.info(subprocess.list2cmdline(cmd))
        subprocess.check_call(cmd)

    if not no_export:
        LOGGER.info('exporting...')
        cmd = ['jupyter', 'nbconvert', '--to', 'html', '--template', 'lab', input_filepath]
        LOGGER.info(subprocess.list2cmdline(cmd))
        subprocess.check_call(cmd)

        # --output-dir output_dirpath doesnt do jack so...
        make_dirpath(output_dirpath)
        input_dirpath = dirpath(input_filepath)
        html_src_filepath = abspath(input_dirpath, f'{fname}.html')
        html_filepath = abspath(output_dirpath, f'{fname}.html')
        shutil.move(html_src_filepath, html_filepath)

        if not no_open:
            launch_editor(html_filepath)

        with ReadWriteText(html_filepath) as rwt:
            # BUG: make sure unicode renders correctly, something between nbconvert and the ampersand
            rwt.text = re.sub(r'&amp;#x', '&#x', rwt.text)

        results.append(html_filepath)

        if not no_pdf:
            # relpath = os.path.relpath(html_filepath, os.getcwd())
            pdf_filepath = abspath(output_dirpath, f'{fname}.pdf')
            if os.path.isfile(pdf_filepath):  # otherwise chromium appends a (1)
                os.remove(pdf_filepath)

            # html = '\n'.join(lines)
            # md_sanitized = []
            # bad_chars = []
            # for char in html:
            #     if char in SPECIAL:
            #         md_sanitized.append(SPECIAL[char])
            #     elif ord(char) == 172:  # ¬
            #         if char not in bad_chars:
            #             bad_chars.append(char)
            #     elif ord(char) > 256:
            #         if char not in bad_chars:
            #             bad_chars.append(char)
            #         # md_sanitized.append(f'&#{ord(char)}')
            #     else:
            #         md_sanitized.append(char)
            # if bad_chars:
            #     raise RuntimeError(f'found bad characters {bad_chars} in the markdown, please replace manually!')

            LOGGER.info('HTML TO PDF VIA EDGE/CHROME...')
            new_pdf_filepath = selenium.print_pdf(html_filepath, dirpath=output_dirpath, margins=False)

            shutil.move(new_pdf_filepath, pdf_filepath)
            LOGGER.info(f'PDF: "{pdf_filepath}"')
            if not no_open:
                launch_editor(pdf_filepath)

            results.append(pdf_filepath)

    if not no_clean_post:
        with ReadWriteIpynb(filepath=input_filepath) as rwi:
            LOGGER.info('final undoing any navigational aids...')
            ipynb_clean(rwi)

    LOGGER.info('done')
    return results


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)

    ipynb(
        args.input_filepath,
        clean=args.clean,
        no_navigational_aids=args.no_navigational_aids,
        no_toc=args.no_toc,
        no_export=args.no_export,
        only_remove_toc=args.only_remove_toc,
        execute=args.execute,
        no_pdf=args.no_pdf,
        no_clean_post=args.no_clean_post,
        no_open=args.no_open,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
