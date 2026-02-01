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

# third party imports

# project imports
from chriscarl.core.lib.stdlib.os import is_file
from chriscarl.core.lib.stdlib.subprocess import which
from chriscarl.core.lib.stdlib.io import read_text_file_try
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

REGEX_MARKDOWN_YAML = re.compile(r'---\n(.*?)\n---', flags=re.DOTALL | re.MULTILINE)
REGEX_HTML_COMMENT = re.compile(r'\<\!--(.*?)--\>', flags=re.DOTALL | re.MULTILINE)

REGEX_CITATION = re.compile(r'<(?P<key>[^>\n]+)>')
REGEX_CITATION_WRONG = re.compile(r'\[([^\]]+)\]')
REGEX_CITATION_PAGE = re.compile(r'<(?P<key>[A-Za-z0-9\-_\.]+)(,\s+)?(?P<section_or_pages_or_timestamp>[sSpP])?(?P<pages_or_timestamp>[-:\d]+)?>')
REGEX_CITATION_FULL = re.compile(
    # [du-bois, Chapter 4, s08]deleting previous work files
    r'<(?P<key>[A-Za-z0-9\-_\.]+)(,\s+)(?P<chapter>[A-Za-z0-9\-_\. ]+)(,\s+)(?P<section_or_pages_or_timestamp>[sSpP])?(?P<pages_or_timestamp>[-:\d]+)>'
)
REGEX_CITATION_INTERDOC_EQ = re.compile(r'(?P<pref>Eq\s*)?<eq-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_TBL = re.compile(r'(?P<pref>Table\s*)?<tbl-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_CODE = re.compile(r'(?P<pref>Listing\s*)?<code-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_HREF = re.compile(r'(?P<pref>Section\s*|Chapter\s*)?<href-(?P<ref>[A-Za-z0-9\-_\.]+)>')
REGEX_CITATION_INTERDOC_FIG = re.compile(r'(?P<pref>Fig\.\s*)?<fig-(?P<ref>[^>]+?)>')
CITATION_PREFACES = ['eq', 'tbl', 'code', 'href', 'fig']
REGEX_HEADER = re.compile(r'(?P<octothorps>#+) (?P<title>.+)')
REGEX_MARKDOWN_IMG = re.compile(r'!\[(?P<alt>.*?)\]\((?P<path>.*?\))')
REGEX_MARKDOWN_URL = re.compile(r'\[(?P<alt>.*?)\]\((?P<path>.*?\))')
REGEX_MARKDOWN_INLINE_LATEX_DOUBLE = re.compile(r'\$\$(?P<content>.*?)\$\$', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_INLINE_LATEX_SINGLE = re.compile(r'(?:(?!\$\d[\d\.\,]+ \b))\$(?P<content>.+?)\$')  # , flags=re.DOTALL
REGEX_CODE = re.compile(r'(?:caption: *)?(?P<caption>[^\n]+)?\n?(?:ref: *)?(?P<reference>[^\n]+)?\n?```(?P<language>[a-z\-\+\# ]+?)\n(?P<content>.*?)```', flags=re.DOTALL | re.MULTILINE)
# https://www.freecodecamp.org/news/how-to-write-a-regular-expression-for-a-url/
REGEX_URL = re.compile(r'(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?')

REGEX_MARKDOWN_TABLE_CAPT_REF = re.compile(r'\|(?P<table>.+?)\|\n\n*caption: *(?P<caption>[^\n]+)\nref: *(?P<reference>[^\n]+)\n', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_TABLE = re.compile(r'\|(.+?)\|\n\n', flags=re.DOTALL | re.MULTILINE)
REGEX_MARKDOWN_LIST = re.compile(r'(?:[ \t]*(?:[\d+]\.|[-\*]+)\s*(?:.+)\n){2,}', flags=re.MULTILINE)
REGEX_SIC = re.compile(r'([\w])\[(sic)\]')

PUNCTUATION_EXCEPT = string.punctuation.replace("'", "").replace('-', '')
REGEX_PUNCTUATION_EXCEPT = re.compile(f'[{PUNCTUATION_EXCEPT}]')
REGEX_PUNCTUATION_HYPHEN_NON = re.compile(r'\s*?-\s+?')
REGEX_PUNCTUATION_HYPHEN_DOUBLE = re.compile(r'-{2,}')


def get_words_only(text):
    # type: (str) -> str
    text = REGEX_SIC.sub(r'\g<1>', text)
    regexes = [
        REGEX_MARKDOWN_YAML,
        REGEX_HTML_COMMENT,
        #
        REGEX_CITATION_INTERDOC_EQ,
        REGEX_CITATION_INTERDOC_TBL,
        REGEX_CITATION_INTERDOC_HREF,
        REGEX_CITATION_INTERDOC_FIG,
        REGEX_HEADER,
        REGEX_MARKDOWN_IMG,
        REGEX_MARKDOWN_URL,
        REGEX_MARKDOWN_INLINE_LATEX_DOUBLE,
        REGEX_MARKDOWN_INLINE_LATEX_SINGLE,
        REGEX_CODE,
        #
        REGEX_MARKDOWN_TABLE_CAPT_REF,
        REGEX_MARKDOWN_TABLE,
        #
        REGEX_CITATION_FULL,
        REGEX_CITATION_PAGE,
        REGEX_CITATION,
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
