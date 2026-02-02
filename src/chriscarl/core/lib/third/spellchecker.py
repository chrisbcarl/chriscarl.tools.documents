#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

core.lib.third.spellchecker is thin wrappers around the pyspellchecker module
core.lib are modules that contain code that is about (but does not modify) the library. somewhat referential to core.functor and core.types.

Updates:
    2026-02-01 - core.lib.third.spellchecker - FIX: wasnt auto-loading the dictionary
    2026-01-25 - core.lib.third.spellchecker - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import re
from typing import Dict, Tuple, List

# third party imports
import spellchecker

# project imports
from chriscarl.core.lib.stdlib.io import read_text_file
from chriscarl.files import manifest_documents

SCRIPT_RELPATH = 'chriscarl/core/lib/third/spellchecker.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

NON_WORDS = set()
DICTIONARY = set()
ACRONYMS = set()
NAMES = set()
DICTIONARY_LOW = set()


def load_dictionary():
    # type: () -> None
    if NON_WORDS:
        return
    NON_WORDS.update(set(ele for ele in read_text_file(manifest_documents.FILEPATH_NON_WORDS).splitlines() if ele and not ele.startswith('#')))
    DICTIONARY.update(set(ele for ele in read_text_file(manifest_documents.FILEPATH_DICTIONARY).splitlines() if ele and not ele.startswith('#')))
    ACRONYMS.update(set(ele for ele in read_text_file(manifest_documents.FILEPATH_ACRONYMS).splitlines() if ele and not ele.startswith('#')))
    NAMES.update(set(ele for ele in read_text_file(manifest_documents.FILEPATH_NAMES).splitlines() if ele and not ele.startswith('#')))
    for acronym in list(ACRONYMS):
        if acronym[-1] == 's':
            ACRONYMS.add(f"{acronym}'")
        else:
            ACRONYMS.add(f"{acronym}'s")
            ACRONYMS.add(f"{acronym}s")
    for name in list(NAMES):
        if name[-1] == 's':
            NAMES.add(f"{name}'")
        else:
            NAMES.add(f"{name}'s")
    DICTIONARY_LOW.update(set(ele.lower() for ele in DICTIONARY.union(NAMES).union(ACRONYMS)))


def clean_line(line):
    text = re.sub(r'-{2}', ' ', line)
    text = re.sub(r'[\[\]]', '', text)  # eliminate [sic]
    text = re.sub(r"[^\w\s\-\']", ' ', text)  # non-words punctuation
    text = re.sub(r"(\s+)'(.*?)'(\s*)", r'\1\2\3', text)  # 'asdf', non-greedy
    text = re.sub(r'(1st|2nd|3rd|\d+th)', ' ', text)  # th'd numbers
    text = re.sub(r'(\d+s)', ' ', text)  # 2020s
    text = re.sub(r'\d{1,}[\d.,-]*', ' ', text)  # numbers like 3.14-69,000
    text = re.sub(r'([A-Za-z])- ', r'\1', text)  # late-18th has been replaced to late-
    text = re.sub(r'(\s+)-\s+', r'\1', text)  # asdf - asdf

    return text

T_SPELLCHECK_ERROR = Dict[str, List[Tuple[int, str, str]]]
T_SPELLCHECK_WARN = Dict[str, List[Tuple[int, str]]]


def spellcheck(content):
    # type: (str) -> Tuple[T_SPELLCHECK_ERROR, T_SPELLCHECK_WARN, int]
    '''
    Description:
        using pyspellcheck, go through the content and make error and warning recommendations
        and get the word count
    Arguments:
        content: str
    Returns:
        Tuple[T_SPELLCHECK_ERROR, T_SPELLCHECK_WARN, int]
            error_words - dict of lists {mispelling: [(lineno, line text, recommended replacement)]}
            warning_words - dict of lists {mispelling: [(lineno, line text)]}
            word_count
    '''
    load_dictionary()
    spell = spellchecker.SpellChecker()
    low_content = content.lower()
    visited = set()
    error_words = {}
    warning_words = {}
    word_count = 0

    for word in DICTIONARY_LOW:
        # find each word but EXACTLY that word that stops and ends
        #   for example, EDU is inside of scheduled, can't have that...
        for mo in reversed(list(re.finditer(r'\b' + re.escape(word) + r'\b', low_content))):
            start, end = mo.start(), mo.end()
            low_content = f'{low_content[:start]}{low_content[end:]}'
            content = f'{content[:start]}{content[end:]}'

    for lineno, line in enumerate(content.splitlines()):
        if not line.strip():
            continue

        text = clean_line(line)
        tokens = [ele for ele in re.split(r'\s+', text) if ele]
        word_count += len(tokens)
        for token in tokens:
            if not token:
                continue
            if token.isupper():  # acronym
                continue

            token_low = token.lower()
            if token_low in visited or token_low in NON_WORDS or token_low in DICTIONARY:
                continue
            visited.add(token_low)
            if token_low in spell:
                continue

            # this word looks like a name, better not penalize it.
            if token_low.capitalize() == token:
                if token not in warning_words:
                    warning_words[token] = []
                warning_words[token].append((lineno, line))
                continue

            # this a word not recognized by spell checker OR by dictionary
            correctwords = spell.correction(token_low)
            if correctwords:
                # a correction was found
                if token not in error_words:
                    error_words[token] = []
                error_words[token].append((lineno, line, correctwords))
            else:
                if token not in warning_words:
                    warning_words[token] = []
                warning_words[token].append((lineno, line))

    return error_words, warning_words, word_count
