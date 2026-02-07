#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.shed.md2latex is individual funcs that support the larger tool that COULD be used independently
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

Updates:
    2026-02-06 - tools.shed.md2latex - refactor such that most of the functions are hosted here
    2026-02-04 - tools.shed.md2latex - list conversion edge cases
    2026-02-01 - tools.shed.md2latex - added analyze_sections, markdown_emphasis_to_latex, markdown_list_to_latex, delete_latex_work_files
    2026-01-31 - tools.shed.md2latex - added get_word_count, word_count
    2026-01-25 - tools.shed.md2latex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import dataclasses
import subprocess
import datetime
import tempfile
import pathlib
import shutil
import string
import re
from typing import Tuple, List, Optional, Dict

# third party imports
import markdown2
import yaml

# project imports
from chriscarl.core.lib.stdlib.os import is_file, dirpath
from chriscarl.core.lib.stdlib.subprocess import which
from chriscarl.core.lib.stdlib.io import read_text_file_try, write_text_file
from chriscarl.core.lib.stdlib.urllib import download
from chriscarl.core.lib.stdlib.subprocess import kill
from chriscarl.core.lib.third.spellchecker import spellcheck
from chriscarl.core.types.str import indent, dedent, find_lineno_index
from chriscarl.core.functors.parse.str import unicode_replace
from chriscarl.core.functors.parse import latex
from chriscarl.core.functors.parse import bibtex
from chriscarl.core.functors.parse import markdown
from chriscarl.tools import md2bibtex

SCRIPT_RELPATH = 'chriscarl/tools/shed/md2latex.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

WIN32 = sys.platform == 'win32'
EXECUTABLES = ['wkhtmltopdf', 'miktex', 'rsvg-convert'] if WIN32 else [] + ['pandoc']


def assert_executables_exist():
    # type: () -> None
    for exe in EXECUTABLES:
        assert which(exe), f'choco install {exe} -y' if WIN32 else 'apt install {} -y'


# early extract sections of markdown

# BIG sections of markdown potentially
REGEX_CAPTION_LABEL_COMMON = re.compile(r'(?P<caption>(?:caption: *)[^\n]+(?:\n+))?(?P<label>(?:label: *)[^\n]+(?:\n+))?', flags=re.DOTALL | re.MULTILINE)
REGEX_HTML_COMMENT = re.compile(r'\<\!--(.*?)--\>', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_YAML = re.compile(r'---\n(.*?)\n---', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_TABLE = re.compile(r'(?:caption: *)?(?P<caption>[^\n]+)?\n+?(?:label: *)?(?P<label>[^\n]+)?\n+?\|(?P<content>.+?)\|\n\n', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_LATEX = re.compile(r'\$\$\n\s*(%?\\label\{)?(?P<label>[A-Za-z0-9\-_\.]+)?(\}\n)?(?P<content>.*?)\$\$', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_MULTILINE_LITERAL = re.compile(r'```\n(?P<content>.*?)```', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_CODE = re.compile(
    r'(?:caption: *)?(?P<caption>[^\n]+)?\n+?(?:label: *)?(?P<label>[^\n]+)?\n+?```(?P<language>[a-z\-\+\# ]+?)\n(?P<content>.*?)```', flags=re.DOTALL | re.MULTILINE
)
# NOTE: THIS ONE IS WEIRD, doing groups[content] will only give you the last quote, but it DOES pick all of them up...
REGEX_MARKDOWN_QUOTE = re.compile(r'(?P<caption>(?:caption: *)[^\n]+(?:\n+))?(?P<label>(?:label: *)[^\n]+(?:\n+))?(?P<content>^>.*\n){2,}', flags=re.MULTILINE)
# NOTE: special unfortunately...
# old - (?:[ \t\n]*(?:[\d+]\.|[-\*]+)\s*(?:.+)\n){2,}
REGEX_MARKDOWN_LIST = re.compile(r'(?:^[ \t\n]*(?:[\d+]\. |[-\*]+) ?(?:.*)\n){1,}', flags=re.MULTILINE)

REGEX_LARGE_SECTIONS = {
    'comment': REGEX_HTML_COMMENT,
    'yaml': REGEX_MARKDOWN_YAML,
    # can have other stuff embedded
    'table': REGEX_MARKDOWN_TABLE,
    'latex': REGEX_MARKDOWN_LATEX,
    'literal': REGEX_MARKDOWN_MULTILINE_LITERAL,
    'code': REGEX_MARKDOWN_CODE,
    'quote': REGEX_MARKDOWN_QUOTE,
    'list': REGEX_MARKDOWN_LIST,
    # implicit ('any': '')
}

REGEX_MARKDOWN_HEADER = re.compile(r'(?P<octothorps>#+) (?P<title>.+)')
REGEX_MARKDOWN_IMG = re.compile(r'!\[(?P<alt>.*?)\]\((?P<path>.*?\))')

REGEX_SMALL_SECTIONS = {
    'header': REGEX_MARKDOWN_HEADER,
    'img': REGEX_MARKDOWN_IMG,
}

# https://www.freecodecamp.org/news/how-to-write-a-regular-expression-for-a-url/
REGEX_URL = re.compile(
    r'(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?'
)
# REGEX_URL = re.compile(r'(https?:\/\/)[a-z0-9\-\_\.]{3,}\/?[A-Za-z0-9\-\_\.\/\?\=\&]*')
REGEX_MARKDOWN_URL = re.compile(r'\[(?P<alt>.*?)\]\((?P<path>.*?\))')
REGEX_MARKDOWN_LITERAL_INLINE = re.compile(r'`(?P<content>[^`]+)`')
REGEX_MARKDOWN_LATEX_INLINE = re.compile(r'(?:(?!\$\d[\d\.\,]+ \b))\$(?P<content>.+?)\$')  # , flags=re.DOTALL

REGEX_CITATION_CONTENT = re.compile(r'[A-Za-z0-9\-_\.]+')

REGEX_CITATION = re.compile(r'<(?P<ref>[^>\n]+)>')
REGEX_CITATION_WRONG = re.compile(r'\[([^\]]+)\]')
REGEX_CITATION_PAGE = re.compile(r'<(?P<ref>[A-Za-z0-9\-_\.]+)(,\s+)?(?P<section_or_pages_or_timestamp>[sSpP])?(?P<pages_or_timestamp>[-:\d]+)?>')
REGEX_CITATION_FULL = re.compile(
    # [du-bois, Chapter 4, s08]deleting previous work files
    r'<(?P<ref>[A-Za-z0-9\-_\.]+)(,\s+)(?P<chapter>[A-Za-z0-9\-_\. ]+)(,\s+)(?P<section_or_pages_or_timestamp>[sSpP])?(?P<pages_or_timestamp>[-:\d]+)>'
)
REGEX_CITATION_INTERDOC_EQ = re.compile(r'(?P<pref>Eq\s*)?<eq-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_TBL = re.compile(r'(?P<pref>Table\s*)?<tbl-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_CODE = re.compile(r'(?P<pref>Listing\s*)?<code-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_HREF = re.compile(r'(?P<pref>Section\s*|Chapter\s*)?<href-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_FIG = re.compile(r'(?P<pref>Fig\.\s*)?<fig-(?P<ref>[^>]+?)>')

# REGEX_MARKDOWN_TABLE = re.compile(r'\|(.+?)\|\n\n', flags=re.DOTALL | re.MULTILINE)
REGEX_SIC = re.compile(r'([\w])\[(sic)\]')

PUNCTUATION_EXCEPT = string.punctuation.replace("'", "").replace('-', '')
REGEX_PUNCTUATION_EXCEPT = re.compile(f'[{PUNCTUATION_EXCEPT}]')
REGEX_PUNCTUATION_HYPHEN_NON = re.compile(r'\s*?-\s+?')
REGEX_PUNCTUATION_HYPHEN_DOUBLE = re.compile(r'-{2,}')

REGEX_MARKDOWN_DOUBLE_QUOTE = re.compile(r'"(.*?)"', flags=re.MULTILINE)  # double quotes, *? is ungreedy
REGEX_MARKDOWN_BOLD_ITALIC = re.compile(r'\*{3,}(.+?)\*{3,}', flags=re.MULTILINE)  # bold-italic, *? is ungreedy
REGEX_MARKDOWN_BOLD = re.compile(r'\*{2,}(.+?)\*{2,}', flags=re.MULTILINE)  # bold, *? is ungreedy
REGEX_MARKDOWN_ITALIC = re.compile(r'\*{1,}(.+?)\*{1,}', flags=re.MULTILINE)  # italics, *? is ungreedy

# TODO: strikethrough, underline
REGEX_LATEX_LABEL = re.compile(r'%\s*?\\label\{(?P<label>[A-Za-z0-9\-_\.]+)\}')
# BUG: content is not correctly captured, has to be massaged...
REGEX_MARKDOWN_BIBLIOGRAPHY_SECTION = re.compile(r'\#+\s+(bibliography|references|citations)\n(?P<content>[^#].*\n)+(#+\s+[A-z])?', flags=re.IGNORECASE)
REGEX_MARKDOWN_EMPTY_LITERAL = re.compile(r'```\s*```', flags=re.MULTILINE)


def get_words_only(text):
    # type: (str) -> str
    text = REGEX_SIC.sub(r'\g<1>', text)
    for regex in REGEX_LARGE_SECTIONS.values():
        text = regex.sub(' ', text)
    for regex in REGEX_SMALL_SECTIONS.values():
        text = regex.sub(' ', text)
    regexes = [
        REGEX_MARKDOWN_URL,
        REGEX_MARKDOWN_LITERAL_INLINE,
        #
        REGEX_CITATION_INTERDOC_EQ,
        REGEX_CITATION_INTERDOC_TBL,
        REGEX_CITATION_INTERDOC_HREF,
        REGEX_CITATION_INTERDOC_FIG,
        REGEX_MARKDOWN_LATEX_INLINE,
        #
        REGEX_CITATION_WRONG,
        #
        REGEX_CITATION_FULL,
        REGEX_CITATION_PAGE,
        REGEX_CITATION,
        #
        REGEX_MARKDOWN_DOUBLE_QUOTE,
        REGEX_MARKDOWN_BOLD_ITALIC,
        REGEX_MARKDOWN_BOLD,
        REGEX_MARKDOWN_ITALIC,
        #
        REGEX_MARKDOWN_EMPTY_LITERAL,
    ]
    for regex in regexes:
        text = regex.sub(' ', text)

    text = REGEX_CITATION_WRONG.sub(r'\g<1>', text)
    lines = text.splitlines()
    for l, line in enumerate(lines):
        line = re.sub(r' ?<.+?>', ' ', line)
        # line = re.sub(r'[^\w ]', ' ', line)
        line = REGEX_PUNCTUATION_EXCEPT.sub(' ', line)
        line = REGEX_PUNCTUATION_HYPHEN_DOUBLE.sub(' ', line)
        line = REGEX_PUNCTUATION_HYPHEN_NON.sub(' ', line)
        line = re.sub(r'[\d]', ' ', line)
        lines[l] = line
    text = '\n'.join(lines)

    return text


def get_word_count(text):
    # type: (str) -> int
    text = re.sub(r'<!--(.+?)-->', r'\g<1>', text)  # comment
    text = re.sub(r'---(.+?)---', r'\g<1>', text)  # yaml
    text = re.sub(r' ?<.+?>', ' ', text)
    # text = re.sub(r'[^\w ]', ' ', text)
    text = REGEX_PUNCTUATION_HYPHEN_DOUBLE.sub(' ', text)
    text = REGEX_PUNCTUATION_HYPHEN_NON.sub(' ', text)
    text = REGEX_PUNCTUATION_EXCEPT.sub(' ', text)
    text = re.sub(r'[\d]', ' ', text)
    return len(re.split(r'\s+', text))


def word_count(filepath_or_content):
    # type: (str) -> int
    if is_file(filepath_or_content):
        content = read_text_file_try(filepath_or_content)
    else:
        content = filepath_or_content
    words = get_words_only(content)
    wc = get_word_count(words)
    return wc


T_SECTION = Tuple[str, str, Optional[re.Match]]


def analyze_sections(md_content, regex_dict):
    # type: (str, Dict[str, re.Pattern]) -> List[T_SECTION]
    # find large sections then smaller sections and so on.
    sections = [
        # ('yaml', 'whatever', mo)
        # ('code', 'whatever', mo)
        # ('latex', 'whatever', mo)
    ]
    # these regexes define entire sections at a time and everything else in between is peanuts
    while md_content:
        md_content = md_content.strip()
        mos = [(k, regex.search(md_content)) for k, regex in regex_dict.items()]
        mos = sorted(mos, key=lambda tpl: 999999 if not tpl[1] else tpl[1].start())
        section, first_mo = mos[0]
        if first_mo:
            start, end = first_mo.span()
            if start == 0:
                content = md_content[:end]
                sections.append((section, content, first_mo))
            else:
                content = md_content[:start]
                sections.append(('any', content, None))
                content = md_content[start:end]
                sections.append((section, content, first_mo))
            md_content = md_content[end:]
        else:
            content = md_content
            sections.append(('any', content, None))
            md_content = ''
        # if section in ['latex']:
        #     print('breakpoint')
    return sections


def analyze_large_sections(md_content):
    return analyze_sections(md_content, REGEX_LARGE_SECTIONS)


def analyze_small_sections(md_content):
    return analyze_sections(md_content, REGEX_SMALL_SECTIONS)


def markdown_emphasis_to_latex(text):
    # final latexisms like quotation replacement
    text = REGEX_MARKDOWN_DOUBLE_QUOTE.sub(r'``\1"', text)
    text = REGEX_MARKDOWN_BOLD_ITALIC.sub(r'\\textbf{\\emph{\1}}', text)
    text = REGEX_MARKDOWN_BOLD.sub(r'\\textbf{\1}', text)
    text = REGEX_MARKDOWN_ITALIC.sub(r'\\emph{\1}', text)
    return text


def markdown_list_to_latex(content):
    # hack to avoid the latex to mathml conversion...
    _old_run = markdown2.Latex.run
    markdown2.Latex.run = (lambda self, text: text)
    # NOTE: BUG: markdown2 will treat \( strangely, I can't figure out why just now, so escape it and deal with it later
    latex_inline = {}
    for m, mo in enumerate(reversed(list(re.finditer(r'\\\(.+\\\)', content)))):
        start, end = mo.span()
        key = f'/LATEX_INLINE{m}/'
        latex_inline[key] = content[start:end]
        content = f'{content[:start]}{key}{content[end:]}'
    html = markdown2.markdown(
        content,
        extras={
            'tables': None,
            'footnotes': None,
            'headerids': None,
            'strike': None,
            'middle-word-em': False,  # so urls that have MIT_technology_ wont become MIT<em>technology</em>
        }
    )
    markdown2.Latex.run = _old_run
    while '<pre><code>' in html:
        mo = re.search(r'<pre><code>(.+)</code></pre>', html, flags=re.DOTALL | re.MULTILINE)
        if not mo:
            raise RuntimeError('this cannot happen at this stage')
        start, end = mo.span()
        inner_latex_list = indent(markdown_list_to_latex(mo.groups()[0]))
        html = f'{html[:start]}\n{inner_latex_list}\n{html[end:]}'
        print('fuck')
    html = re.sub(r'(<p>|<\/p>)', '', html)  # markdown2 injects <p> into its html lists

    latex_list = html[:]
    latex_list = latex_list.replace('<ol>', r'\begin{enumerate}')
    latex_list = latex_list.replace('</ol>', r'\end{enumerate}')
    latex_list = latex_list.replace('<ul>', r'\begin{itemize}')
    latex_list = latex_list.replace('</ul>', r'\end{itemize}')
    latex_list = latex_list.replace('<li>', r'\item ')
    latex_list = latex_list.replace('</li>', r'')

    for key, value in latex_inline.items():
        latex_list = latex_list.replace(key, value)

    return latex_list


LATEX_EXTS_TO_CLEAN = ['.aux', '.bbl', '.bcf', '.blg', '.lof', '.log', '.lot', '.out', '.synctex(busy)', '.synctex.gz', '.run.xml', '.toc']


def delete_latex_work_files(dirpath, filename, extra=None):
    extra = extra or []
    for ext in LATEX_EXTS_TO_CLEAN:
        clean_me_filepath = os.path.join(dirpath, f'{filename}{ext}')
        if os.path.isfile(clean_me_filepath):
            os.remove(clean_me_filepath)
    for filepath in extra:
        os.remove(filepath)


def find_bad_citations(content):
    # type: (str) -> Tuple[List[str], List[str]]
    errors, warnings = [], []
    for mo in REGEX_CITATION_WRONG.finditer(content):
        start, end = mo.span()
        citation = content[start:end]
        if not REGEX_CITATION_CONTENT.match(citation):
            continue
        if '-' in citation:
            errors.append(f'BAD [] citation style {citation}, use <> style instead')
        else:
            warnings.append(f'possible bad [] citation style {citation}, use <> style instead')
    return errors, warnings


def bibliographies_to_bibtex(bibliography_filepaths, bibliography_output_filepath):
    # type: (List[str], str) -> Tuple[Dict[str, str], List[str], List[str]]
    errors, warnings = [], []
    labels = {}
    try:
        bib, labels = md2bibtex.combine(bibliography_filepaths, bibliography_output_filepath)
        write_text_file(bibliography_output_filepath, bib)
        LOGGER.debug('wrote "%s"', bibliography_output_filepath)
    except (ValueError, KeyError) as ex:
        errors.append(f'{ex} - there is a duplicate or null among the markdown or bibliographies!')

    return labels, errors, warnings


@dataclasses.dataclass
class Doclet(object):
    section: str
    label: str = ''
    caption: str = ''
    content: str = ''
    appendix: bool = False
    mo: Optional[re.Match] = None
    data: dict = dataclasses.field(default_factory=lambda: {})


def sections_to_doclets(sections, md_filepath, output_dirpath):
    # type: (List[T_SECTION], str, str) -> Tuple[List[Doclet], Dict[str, str], List[Tuple[str, str]], List[str], List[str]]
    '''
    Description:
        - given the list of discovered big sections and the original markdown file
        - break them up into Doclets (interdoc_labels, captions, other data)
            - download any images
    Returns:
        Tuple[List[Doclet], Dict[str, str], List[str], List[str], List[str]]
            doclets, interdoc_labels, download_url_filepaths, errors, warnings
    '''
    original_md_content = read_text_file_try(md_filepath)
    md_relpath = os.path.relpath(md_filepath, os.getcwd())
    md_dirpath = pathlib.Path(dirpath(md_filepath))
    output_dirpath_pl = pathlib.Path(output_dirpath)

    errors, warnings = [], []
    doclets = [
        # ('yaml', '---asdf: whatever---', spellcheck='')
        # ('plain', 'asdfasdfasdf', spellcheck='asdfasdf')
        # ('comment', '---asdf: whatever---', spellcheck='')
        # ('table', '|||', caption='capt', label='asdf', spellcheck='')
        # ...
        # ('header', 'introduction', label='introduction', spellcheck='introduction')
        # ...
        # ('header', 'introduction', label='introduction', spellcheck='introduction', appendix=True)
    ]
    appendix = False
    interdoc_labels = {}
    download_url_filepaths = []
    while sections:
        section, md_content, mo = sections.pop(0)

        if section != 'comment':
            for url_mo in REGEX_URL.finditer(md_content):
                start = url_mo.start()
                if md_content[start - 1] != '(':
                    end = start + 64
                    endline = md_content.find('\n', start) - 1
                    end = min([end, endline])
                    lineno = list(find_lineno_index(md_content[start:end], original_md_content))[0][0]
                    errors.append(f'naked url! enclose with []()! lineno {lineno} {md_content[start:end]}...')

        if appendix:
            appendix = False  # switch it back off, we JUST turned it on for someone else
        data = {}
        content = md_content
        label = ''
        caption = ''
        groups = []
        groupdict = {}
        if mo is not None:
            groups = mo.groups()
            groupdict = mo.groupdict()
        if section != 'any':
            if section in set(['table', 'code', 'latex', 'quote', 'literal']):
                caption = groupdict.get('caption', '')
                label = groupdict.get('label', '')
                content = groupdict.get('content', '')

                if section in set(['quote']):
                    # NOTE: starting from the very first > to the last...
                    content = REGEX_CAPTION_LABEL_COMMON.sub('', md_content)
                elif section in set(['latex']):
                    # $$  # 301 gets caught as the label...
                    # 301 = 03~ 00~ 01 = 0000~0011, 0000~0000, 0000~0001
                    # $$
                    if r'\label' not in md_content:
                        label = ''
                        content = f'{label}{content}'

                if not content:
                    raise RuntimeError('could not determine content?!')
                lineno = list(find_lineno_index(md_content, original_md_content))[0][0] + 1

                if not label and section not in set(['literal', 'quote']):
                    example = 'label: something-or-other'
                    if section in set(['latex']):
                        example = '%\\label{something-or-other}, note the % comment is for markdown purposes.'
                    errors.append(f'{section} missing "{example}" at "{md_relpath}", lineno {lineno}!\n{indent(md_content[:64])}...')
                if not caption and section not in set(['latex', 'literal', 'quote']):
                    # caption is also required for these
                    errors.append(f'{section} missing "caption: Something or Other" at "{md_relpath}", lineno {lineno}!\n{indent(md_content[:64])}...')

                if label:
                    if label.startswith('label:'):
                        label = label[6:].strip()
                if caption:
                    if caption.startswith('caption:'):
                        caption = caption[8:].strip()

                if section == 'code':
                    data['language'] = groupdict.get('language') or ''
                elif section == 'table':
                    content = f'|{content}|'  # NOTE: it omits the first and last pipe unfortunately

            # elif section in set(['list']):
            #     content = md_content

            elif section in set(['yaml']):
                content = groups[0]

            if section not in set(['yaml', 'comment']):
                # i know ahead of time that bad usage of citations is a bad look.
                cite_errors, cite_warnings = find_bad_citations(md_content)
                errors.extend(cite_errors)
                warnings.extend(cite_warnings)

            if label:
                if label in interdoc_labels:
                    errors.append(f'duplicate {section} label {label!r}')
                interdoc_labels[label] = section

            doclets.append(Doclet(
                section=section,
                label=label,
                caption=caption,
                content=content,
                appendix=appendix,
                mo=mo,
                data=data,
            ))
        else:
            small_sections = analyze_small_sections(md_content)
            for section_sub, md_content_sub, mo_sub in small_sections:
                if appendix:
                    appendix = False  # switch it back off, we JUST turned it on for someone else
                label = ''
                caption = ''
                data = {}
                lineno = list(find_lineno_index(md_content_sub, original_md_content))[0][0] + 1
                groupdict_sub = {}
                if mo_sub is not None:
                    groupdict_sub = mo_sub.groupdict()
                if section_sub == 'header':
                    octothorps = groupdict_sub.get('octothorps') or ''
                    title = groupdict_sub.get('title', '')

                    data['octothorps'] = octothorps
                    data['title'] = title

                    label = title[:]
                    if len(octothorps) > 4:
                        errors.append(f'headings > 4 not supported at "{md_relpath}", lineno {lineno}, {label!r}')
                        continue

                    if title.lower() == 'appendix':
                        appendix = True
                    label = '-'.join(label.split())
                elif section_sub == 'img':
                    caption = groupdict_sub.get('alt', '')
                    path = groupdict_sub.get('path', ')')[:-1]
                    if not path:
                        errors.append(f'img missing path\n{indent(md_content_sub)}')
                        continue
                    label = os.path.basename(path)
                    # label = re.sub(r'[^\w]', '', os.path.splitext(label)[0])
                    # label = '-'.join(label.split())

                    if output_dirpath:
                        if path.startswith('http'):
                            basename = path.split('/')[-1].split('?')[0]
                            dst_filepath = output_dirpath_pl / basename
                            download_url_filepaths.append((path, dst_filepath))
                        else:
                            src_filepath = md_dirpath / path
                            dst_filepath = output_dirpath_pl / os.path.basename(path)
                            download_url_filepaths.append((src_filepath, dst_filepath))

                        path = dst_filepath.name
                        data['path'] = path

                    path, ext = os.path.splitext(path)  # doesnt like extensions???
                    if ext.lower() in ['.svg']:
                        raise RuntimeError(f'image src at "{path}" is using a forbidden extension, cannot proceed')

                elif section_sub == 'any':
                    # i know ahead of time that bad usage of citations is a bad look.
                    cite_errors, cite_warnings = find_bad_citations(md_content_sub)
                    errors.extend(cite_errors)
                    warnings.extend(cite_warnings)

                else:
                    raise NotImplementedError(f'subsection {section_sub!r} not anticipated')

                if label:
                    if label in interdoc_labels:
                        errors.append(f'duplicate {section} label {label!r}')
                    interdoc_labels[label] = section

                doclets.append(Doclet(
                    section=section_sub,
                    label=label,
                    caption=caption,
                    content=md_content_sub,
                    appendix=appendix,
                    mo=mo_sub,
                    data=data,
                ))

    return doclets, interdoc_labels, download_url_filepaths, errors, warnings


def doclets_spellcheck(doclets, md_filepath):
    # type: (List[Doclet], str) -> Tuple[int, List[str], List[str]]
    '''
    Description:
        given a list of doclets, analyze just the spellcheckable words
    Arguments:
        fatal: bool
            promote mispelled words to errors instead of warnings
    Returns:
        Tuple[List[str], List[str]]
            errors, warnings
    '''
    errors, warnings = [], []
    original_md_content = read_text_file_try(md_filepath)

    spellcheckable_sections = set(['header', 'any', 'list'])
    spellcheckable_words = ''
    for doclet in doclets:
        if doclet.section in spellcheckable_sections:
            spellcheckable_words += get_words_only(doclet.content)

    # if debug:
    # write_text_file('./ignoreme/spellcheckable_words.txt', spellcheckable_words)

    error_words, warning_words, word_count = spellcheck(spellcheckable_words)
    if warning_words:
        warnings.append(f'{len(warning_words)} warning words discovered!')
        for word in sorted(warning_words):
            warnings.append(f'    - {word}')
            for lineno, idx in find_lineno_index(word, original_md_content):
                warnings.append(f'        - lineno {lineno + 1}, ...{original_md_content[idx-8:idx+len(word)+8]!r}...')
    if error_words:
        errors.append(f'{len(error_words)} error words discovered!')
        for word in sorted(error_words):
            correctword = error_words[word][0][2]
            errors.append(f'    - {word} -> {correctword}')
            for lineno, idx in find_lineno_index(word, original_md_content):
                errors.append(f'        - lineno {lineno + 1}, ...{original_md_content[idx-8:idx+len(word)+8]!r}...')
    else:
        LOGGER.info('no misspelled words! (probably)')

    return word_count, errors, warnings


def markdown_refs_to_latex(content, original_md_content, all_labels_lowcase, interdoc_label_types, errors, template):
    # type: (str, str, dict, dict, list, str) -> str
    citation_mos = list(REGEX_CITATION.finditer(content))
    for c, citation_mo in enumerate(reversed(citation_mos)):
        start, end = citation_mo.span()
        citation = content[start:end]

        mo2 = REGEX_CITATION_FULL.match(citation)
        if not mo2:
            mo3 = REGEX_CITATION_PAGE.match(citation)
            if not mo3:
                lineno = list(find_lineno_index(citation, original_md_content))[0][0] + 1
                raise RuntimeError(f'citation at lineno {lineno} is completely baffling to me: {citation!r}')
            citation_mo = mo3
        else:
            citation_mo = mo2
        groups = citation_mo.groupdict()
        original_ref = groups.get('ref', '')
        ref = all_labels_lowcase.get(original_ref.lower())

        if not ref:
            errors.append(f'ref {original_ref!r} not found in bibilography or interdoc!')
            return ''

        chapter = groups.get('chapter', '')
        section_or_pages_or_timestamp = groups.get('section_or_pages_or_timestamp', '')
        pages_or_timestamp = groups.get('pages_or_timestamp', '')

        if ref in interdoc_label_types:
            cite_command = '~\\ref'
            if interdoc_label_types[ref] == 'latex':
                cite_command = '~\\eqref'
        else:
            if template in ['chicago', 'math']:
                cite_command = '\\autocite'
            else:
                cite_command = '\\cite'
        if not pages_or_timestamp:
            # \autocite{marx}
            replacement = f'{cite_command}{{{ref}}}'
        else:
            # \autocite[Estranged Labour, \S 324-34]{marx}
            # \autocite[\S 324-34]{marx}
            tokens = []
            if chapter:
                tokens.append(chapter)
            if section_or_pages_or_timestamp:  # is section
                tokens.append(f'\\S {pages_or_timestamp}')
            else:
                # \autocite[Estranged Labour, 324-34]{marx}
                # \autocite[324-34]{marx}
                if template == 'ieee':
                    if '-' in pages_or_timestamp:
                        tokens.append(f'pp. {pages_or_timestamp}')
                    else:
                        tokens.append(f'p. {pages_or_timestamp}')
                else:
                    tokens.append(pages_or_timestamp)
            replacement = f'{cite_command}[{", ".join(tokens)}]{{{ref}}}'

        content = f'{content[0:start]}{replacement}{content[end:]}'

    return content


def doclets_to_latex(doclets, md_filepath, all_labels_lowcase, interdoc_label_types, template):
    # type: (List[Doclet], str, Dict[str, str], Dict[str, str], str) -> Tuple[List[str], List[str], List[str], List[str]]
    '''
    Description:
        doclets to latexified body and appendix body
    Returns
        Tuple[List[str], List[str], List[str], List[str]]
            body, appendix_body, errors, warnings
    '''
    # render time
    # {'quote', 'table', 'latex', 'literal', 'code', 'header', 'any', 'img', 'list'}
    body, appendix_body = [], []
    errors, warnings = [], []
    original_md_content = read_text_file_try(md_filepath)

    appendix = False
    append_appendix = False
    # prev_section = ''
    for doclet in doclets:
        section, content, label, caption, data = (doclet.section, doclet.content, doclet.label, doclet.caption, doclet.data)
        if section in set(['yaml']):
            continue  # will be analyzed later

        if doclet.appendix is True:
            appendix = True

        if caption:
            # are there refs IN THE CAPTION?
            caption = markdown_refs_to_latex(caption, original_md_content, all_labels_lowcase, interdoc_label_types, errors, template=template)

        # TODO: auto Fig. Table. Code. etc.
        if section in set(['comment']):
            content = '\n'.join(f'% {line}' for line in content.splitlines())
        elif section == 'header':
            MD_HEADER_TO_LATEX = {
                '#': '\\section',
                '##': '\\subsection',
                '###': '\\subsubsection',
                '####': '\\paragraph',
            }
            title = data['title']
            octothorps = data['octothorps']
            if appendix:
                content = f'\\newpage\n\\appendix\n\\label{{appendix}}'  # NOTE: NOT a usual title
                # TODO: only works on the book / report class...
                # if appendix:
                #     replacement = f'\\chapter{{{title}}}\\label{{href-{anchor}}}'
                appendix = False  # turn off
                append_appendix = True
            else:
                content = f'{MD_HEADER_TO_LATEX[octothorps]}{{{title}}}\\label{{{label}}}'
        elif section == 'img':
            IMG_REPLACEMENT = r'''
            \begin{figure}[htbp]
                \centerline{\includegraphics[width=<WIDTH>]{<PATH>}}
                \caption{<ALT>}
                \label{<LABEL>}
            \end{figure}
            '''
            path = data['path']
            replacement = IMG_REPLACEMENT.replace('<PATH>', path).replace('<ALT>', caption).replace('<LABEL>', label)
            if template == 'ieee':
                replacement = replacement.replace('<WIDTH>', '\\linewidth')
            else:
                replacement = replacement.replace('<WIDTH>', '0.66\\linewidth')
            content = replacement
        elif section == 'latex':
            content = dedent(content).strip()  # NOTE: the .strip() is CRITICAL. if you have \begin{math}\n\n\begin{aligned} you're TOAST
            aligned = content.startswith('\\begin{align')
            if aligned:
                # convert it to an equation anyway. regardless if sense or not. \begin{math}\end{math} aint working
                content = f'\\begin{{equation}}\n{content}\n\\end{{equation}}'
            content = REGEX_LATEX_LABEL.sub('', content)  # just remove the label and stick where it needs to go below:
            content = content.replace(r'\begin{equation}', f'\\begin{{equation}}\n\\label{{{label}}}')
            content = '\n'.join(line for line in content.splitlines() if line.strip())
        elif section == 'literal':
            content = f'\\begin{{verbatim}}\n{content}\n\\end{{verbatim}}'
        elif section == 'code':
            language = data['language']
            content = f'\\begin{{lstlisting}}[language={language.capitalize()}, caption={{{caption}}}, label={{{label}}}]\n{content}\n\\end{{lstlisting}}'
        elif section == 'table':
            rows = markdown.table_to_rows(content)
            content = latex.rows_to_latex(rows, caption=caption, label=label, aligned='left')
        else:
            # are there any URL's in the content?
            for url_mo in reversed(list(REGEX_MARKDOWN_URL.finditer(content))):
                url = url_mo.groups()[-1][:-1]  # lop off last )
                content = f'{content[:url_mo.start()]}\\url{{{url}}}{content[url_mo.end():]}'
            content = REGEX_MARKDOWN_URL.sub(r'\\url{\g<2>}', content)
            # are there `literal` in the content?
            content = REGEX_MARKDOWN_LITERAL_INLINE.sub(r'\\lstinline{\g<1>}', content)
            # are there $latex$ in the content?
            content = REGEX_MARKDOWN_LATEX_INLINE.sub(r'\\(\g<1>\\)', content)
            # if postcontent != content:
            #     content = postcontent
            # are there any emphasis like bold, italic, underline, etc?
            # TODO: underline/strikethrough
            content = markdown_emphasis_to_latex(content)

            if section == 'quote':
                # TODO: currently sane washing all > beginnings
                content = '\n'.join(line[line.rindex('>') + 1:].strip() for line in content.splitlines())
                content = f'\\begin{{quotation}}\n{content}\n\\end{{quotation}}'
            elif section == 'list':
                postcontent = markdown_list_to_latex(content)
                content = postcontent

        # are there refs IN THE CONTENT?
        if section not in set(['code', 'literal']):
            content = markdown_refs_to_latex(content, original_md_content, all_labels_lowcase, interdoc_label_types, errors, template=template)
        if section in set(['any']):
            content = latex.latex_escape(content)

        content = unicode_replace(content)
        content = latex.latex_replace(content)
        content.count('\n')
        if content.count('\n') > 1:
            content = dedent(content).strip()

        if section in ['latex', 'list', 'header']:
            content = f'\n\n{content}\n\n'
        if append_appendix:
            appendix_body.append(content)
        else:
            body.append(content)
        prev_section = section

    return body, appendix_body, errors, warnings


def markdown_header_to_render_dict(text, bibliography_filepath, template):
    # type: (str, str, str) -> dict
    bibliography_filepath = bibliography_filepath.replace('\\', '/')

    header = yaml.load(text, Loader=yaml.Loader)

    header_title = header.get('title', 'Untitled').strip()
    header_toc = header.get('toc', False)
    header_doublespaced = header.get('doublespaced', False)
    if template in ['math']:
        header_doublespaced = False  # hard low
    header_date = header.get('date', datetime.datetime.now().strftime('%B %d, %Y'))
    default_margin = 'margin=1in'
    header_geometry = header.get('geometry', default_margin)
    if template in ['math']:
        header_geometry = 'margin=1.5in' if header_geometry == default_margin else header_geometry
    header_course = header.get('course', '')
    header_abstract = header.get('abstract', '')
    header_keywords_lst = [ele.strip() for ele in header.get('keywords', '').split(',')]
    header_keywords_low = set()
    for ele in header_keywords_lst:
        if ele.lower() in header_keywords_low:
            raise RuntimeError(f'keywords duplicate word {ele!r}')
        header_keywords_low.add(ele.lower())
    header_keywords = ', '.join(sorted(header_keywords_lst, key=lambda x: x.lower()))
    header_author_texts = ''
    for header_author in header.get('authors', []):
        name = header_author.get('name', '').strip()
        email = header_author.get('email', '').strip()
        institution = header_author.get('institution', '').strip()
        location = header_author.get('location', '').strip()
        occupation = header_author.get('occupation', '').strip()

        if template in ['chicago', 'math']:
            # \author{John C. Neu
            #     \thanks{Electronic address: \texttt{neu@math.berkeley.edu}}
            # }
            # \affil{Department of Mathematics, University of California, Berkeley}
            if email:
                email = '\n    \\thanks{email: \\texttt{' + email + '}}\n'
            header_author_text = '\\author{' + name + email + '}'
            if institution:
                header_author_text += '\n\\affil{' + institution + '}'
            header_author_texts = f'{header_author_texts}\n{header_author_text}'
        elif template == 'ieee':
            # \IEEEauthorblockN{Chris Carl}
            # \IEEEauthorblockA{
            #     \textit{San Jose State University} \\
            #     \textit{Masters of Science in Computer Engineering Student}\\
            #     San Jose, USA \\
            #     chris.carl@sjsu.edu
            # }

            tokenN = f'\\IEEEauthorblockN{{{name}}}'
            tokensA = []
            if institution:
                tokensA += [f'\\textit{{{institution}}}']
            if occupation:
                tokensA += [f'\\textit{{{occupation}}}']
            if location:
                tokensA += [location]
            if email:
                tokensA += [email]
            blockA = ' \n'.join(f'    {token} \\\\' for token in tokensA)
            header_author_text = f'{tokenN}\n\\IEEEauthorblockA{{\n{blockA}\n}}'
            header_author_texts = f'{header_author_texts}\n{header_author_text}'
        else:
            header_author_texts = name

    render_dict = {}

    if template in ['chicago', 'math']:
        render_dict['<TITLE>'] = f'\\textbf{{{header_title}}}'
        render_dict['<ADDBIBRESOURCE>'] = f'\\addbibresource{{{bibliography_filepath}}}' if bibliography_filepath else ''
    elif template == 'ieee':
        render_dict['<TITLE>'] = header_title
        render_dict['<BIBLIOGRAPHY>'] = f'\\bibliography{{{bibliography_filepath}}}' if bibliography_filepath else ''
        # render_dict['<DOUBLESPACING>'] = ''
    else:
        render_dict['<TITLE>'] = header_title

    render_dict['<AUTHORS>'] = header_author_texts
    render_dict['<COURSE>'] = header_course
    render_dict['<DATE>'] = header_date
    render_dict['<GEOMETRY>'] = header_geometry
    render_dict['<TABLEOFCONTENTS>'] = f'\\clearpage\n\\tableofcontents' if header_toc else ''
    render_dict['<DOUBLESPACING>'] = f'\\usepackage{{setspace}}\n\\doublespacing' if header_doublespaced else ''

    render_dict['<ABSTRACT>'] = header_abstract
    render_dict['<KEYWORDS>'] = header_keywords

    return render_dict


def render_tex_file(doclets, md_filepath, template_filepath, bibliography_output_filepath, tex_output_filepath, template, body, appendix_body):
    # type: (List[Doclet], str, str, str, str, str, List[str], List[str]) -> Tuple[List[str], List[str]]
    original_md_content = read_text_file_try(md_filepath)
    md_relpath = os.path.relpath(md_filepath, os.getcwd())

    errors, warnings = [], []
    render_dict = {}
    for doclet in doclets:
        if doclet.section == 'yaml':
            if render_dict:
                lineno = list(find_lineno_index(doclet.content, original_md_content))[0][0]
                warnings.append(f'multiple yamls detected at "{md_relpath}", lineno {lineno}!')
            render_dict.update(markdown_header_to_render_dict(doclet.content, bibliography_output_filepath, template=template))
    render_dict['<BODY>'] = ''.join(body)
    render_dict['<APPENDIX>'] = ''.join(appendix_body)

    with open(template_filepath, 'r', encoding='utf-8') as r:
        template_content = r.read()

    rendered_content = template_content[:]
    for k, v in render_dict.items():
        rendered_content = rendered_content.replace(k, v)
    rendered_content = re.sub(r'([^\n ]) {2,}', r'\g<1> ', rendered_content)
    rendered_content = re.sub(r'\n{3,},', '\n\n', rendered_content)
    write_text_file(tex_output_filepath, rendered_content)
    LOGGER.debug('wrote "%s"', tex_output_filepath)

    # if debug:
    # pprint.pprint(render_dict, indent=4, width=160)

    return errors, warnings


def download_copy_files(url_filepaths, output_dirpath):
    # type: (List[Tuple[str, str]], str) -> Tuple[List[str], List[str]]
    errors, warnings = [], []
    for t, tpl in enumerate(url_filepaths):
        url, filepath = tpl
        if is_file(url):
            LOGGER.debug('copying     %d / %d - "%s"', t + 1, len(url_filepaths), filepath)
            shutil.copy2(url, output_dirpath)
        else:
            LOGGER.debug('downloading %d / %d - "%s"', t + 1, len(url_filepaths), filepath)
            try:
                download(url, filepath=filepath, skip_exist=True)
            except Exception as exe:
                errors.append(f'bad url {url}, resulted in {exe}')
    return errors, warnings


def run_pdflatex(md_filename, output_dirpath, template):
    # run pdflatex 4 times...
    LOGGER.warning('deleting previous work files...')
    delete_latex_work_files(output_dirpath, md_filename)

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
