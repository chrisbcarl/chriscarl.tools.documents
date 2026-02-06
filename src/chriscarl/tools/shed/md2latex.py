#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.shed.md2latex is individual funcs that support the larger tool that COULD be used independently
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

TODO:
    test and refactor

Updates:
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
import re
import string
from typing import Tuple, List, Optional, Dict

# third party imports
import markdown2

# project imports
from chriscarl.core.lib.stdlib.os import is_file
from chriscarl.core.lib.stdlib.subprocess import which
from chriscarl.core.lib.stdlib.io import read_text_file_try
from chriscarl.core.types.str import indent
from chriscarl.core.functors.parse import latex
from chriscarl.core.functors.parse import bibtex

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


def analyze_sections(md_content, regex_dict):
    # type: (str, Dict[str, re.Pattern]) -> List[Tuple[str, str, Optional[re.Match]]]
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
