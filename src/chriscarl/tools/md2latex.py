#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-25
Description:

tools.md2latex is a tool which converts Markdown to LaTeX WITH a Markdown bibliography!
I've found throughout 3 semesters of grad school that working in Markdown is the obvious choice
    but citations are a pain in the ass and research collation is a pain in the ass
    so my current solution is the following:
    markdown essay file + markdown/bibtex "research" file with certain -isms that lock the 2 together.

Examples:
    md2latex tests/collateral/md2latex/paper.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex

    md2latex tests/collateral/md2latex/paper-simple.md `
        -b tests/collateral/md2latex/bibliography.md `
        -o files/examples/md2latex

TODO:
    - add spellcheck flags, currently disabled
    - refactor


Updates:
    2026-02-01 - tools.md2latex - banged this refactor phase 1 out in about 8 hours. totally worth it.
                 tools.md2latex - added find_bad_citations, markdown_refs_to_latex, markdown_header_to_render_dict, markdown_to_latex
    2026-01-29 - tools.md2latex - got a hankerin to at least start getting the outlines done
    2026-01-25 - tools.md2latex - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
from typing import List, Generator, Optional, Tuple
from dataclasses import dataclass, field
from argparse import ArgumentParser
import subprocess
import datetime
import tempfile
import pathlib
import shutil
import json
import re

# third party imports
import yaml

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, dirpath, filename
from chriscarl.core.lib.stdlib.io import read_text_file_try, write_text_file
from chriscarl.core.lib.stdlib.urllib import download
from chriscarl.core.lib.stdlib.subprocess import kill
from chriscarl.tools.shed import md2latex
from chriscarl.tools.shed import md2bibtex
from chriscarl.core.functors.parse.str import unicode_replace
from chriscarl.core.functors.parse import latex
from chriscarl.core.functors.parse import markdown
from chriscarl.core.types.str import indent, find_lineno_index
from chriscarl.core.lib.third.spellchecker import spellcheck
import chriscarl.files.manifest_documents as mand

SCRIPT_RELPATH = 'chriscarl/tools/md2latex.py'
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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.md2latex')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.md2latex.log')

# tool constants
TEMPLATES = {
    'default': mand.FILEPATH_MD2LATEX_DEFAULT_TEMPLATE,
    'chicago': mand.FILEPATH_MD2LATEX_CHICAGO_TEMPLATE,
    'ieee': mand.FILEPATH_MD2LATEX_IEEE_TEMPLATE,
}
DEFAULT_TEMPLATE = list(TEMPLATES)[0]


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    markdown_filepath: str
    bibliography_filepath: str = ''
    output_dirpath: str = ''
    template: str = DEFAULT_TEMPLATE
    spellcheck_fatal: bool = False
    skip_spellcheck: bool = False
    # wc-applet
    word_count: bool = False
    # non-app
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('main applet')
        app.add_argument('markdown_filepath', type=str, help='.md?')
        app.add_argument('--bibliography-filepath', '--bibliography', '-b', type=str, default='', help='.md w/ bibtex?')
        app.add_argument('--output-dirpath', '-o', type=str, default='', help='save outputs to different dir than input?')
        app.add_argument('--template', '-t', type=str, default=DEFAULT_TEMPLATE, choices=TEMPLATES, help='document style, really')
        app.add_argument('--spellcheck-fatal', '-sf', action='store_true', help='spellcheck fail is fatal')
        app.add_argument('--skip-spellcheck', '-ss', action='store_true', help='skip-spellcheck entirely')

        wc = parser.add_argument_group('word-count applet')
        wc.add_argument('--word-count', '-wc', action='store_true', help='get the word count, exit')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        if self.output_dirpath:
            make_dirpath(self.output_dirpath)
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


def find_bad_citations(content, errors, warnings):
    # i know ahead of time that bad usage of citations is a bad look.
    for mo in md2latex.REGEX_CITATION_WRONG.finditer(content):
        start, end = mo.span()
        citation = content[start:end]
        if '-' in citation:
            errors.append(f'BAD [] citation style {citation}, use <> style instead')
        else:
            warnings.append(f'possible bad [] citation style {citation}, use <> style instead')


def markdown_refs_to_latex(content, original_md_content, all_labels, interdoc_label_types, errors, template=DEFAULT_TEMPLATE):
    # type: (str, str, dict, dict, list, str) -> str
    citation_mos = list(md2latex.REGEX_CITATION.finditer(content))
    for c, citation_mo in enumerate(reversed(citation_mos)):
        start, end = citation_mo.span()
        citation = content[start:end]

        mo2 = md2latex.REGEX_CITATION_FULL.match(citation)
        if not mo2:
            mo3 = md2latex.REGEX_CITATION_PAGE.match(citation)
            if not mo3:
                linenos = list(find_lineno_index(citation, original_md_content))
                raise RuntimeError(f'citation at lineno {linenos[0][0] + 1} is completely baffling to me: {citation!r}')
            citation_mo = mo3
        else:
            citation_mo = mo2
        groups = citation_mo.groupdict()
        original_ref = groups.get('ref', '')
        ref = all_labels.get(original_ref.lower())

        if not ref:
            errors.append(f'ref {original_ref!r} not found in bibilography or interdoc!')

        chapter = groups.get('chapter', '')
        section_or_pages_or_timestamp = groups.get('section_or_pages_or_timestamp', '')
        pages_or_timestamp = groups.get('pages_or_timestamp', '')

        if ref in interdoc_label_types:
            cite_command = '~\\ref'
            if interdoc_label_types[ref] == 'latex':
                cite_command = '~\\eqref'
        else:
            if template == 'chicago':
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

def markdown_header_to_render_dict(text, bibliography_filepath, template=DEFAULT_TEMPLATE):
    # type: (str, str, str) -> dict
    bibliography_filepath = bibliography_filepath.replace('\\', '/')
    if template not in TEMPLATES:
        raise ValueError(f'template {template!r} not in {list(TEMPLATES)}')

    header = yaml.load(text, Loader=yaml.Loader)

    header_title = header.get('title', 'Untitled').strip()
    header_toc = header.get('toc', False)
    header_doublespaced = header.get('doublespaced', False)
    header_date = header.get('date', datetime.datetime.now().strftime('%B %d, %Y'))
    header_geometry = header.get('geometry', 'margin=1in')
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

        if template == 'chicago':
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

    if template == 'chicago':
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


def markdown_to_latex(md_filepath, output_dirpath='', bibliography_filepath='', template=DEFAULT_TEMPLATE, wc=False, debug=False,):
    # type: (str, str, str, str, bool, bool) -> int
    if template not in TEMPLATES:
        raise ValueError(f'template {template!r} not in {list(TEMPLATES)}')

    md_dirpath = dirpath(md_filepath)
    md_filename = filename(md_filepath)
    if not output_dirpath:
        output_dirpath = md_dirpath
    output_dirpath = abspath(output_dirpath)
    os.makedirs(output_dirpath, exist_ok=True)
    tex_output_filepath = abspath(output_dirpath, f'{md_filename}.tex')
    bibliography_output_filepath = abspath(output_dirpath, f'{md_filename}.bib')
    pdf_output_filepath = abspath(output_dirpath, f'{md_filename}.pdf')

    md_content = read_text_file_try(md_filepath)
    original_md_content = md_content[:]
    if not md_content.endswith('\n'):
        md_content = f'{md_content}\n'

    word_count = md2latex.word_count(md_content)
    LOGGER.info('wc: %d', word_count)
    if wc:
        return 0

    bibtex_content, bibtex_labels = '', {}
    if bibliography_filepath:
        LOGGER.info('analyzing bibliography')
        bibtex_content, bibtex_labels = md2bibtex.text_to_bibtex(bibliography_filepath)
        if debug:
            LOGGER.debug('bibtex labels: %s', json.dumps(bibtex_labels))

    write_text_file(bibliography_output_filepath, bibtex_content)
    LOGGER.info('wrote "%s"', bibliography_output_filepath)

    errors = []
    warnings = []

    # right off the rip I can replace this stuff no problem.
    md_content = unicode_replace(md_content)

    LOGGER.info('analyzing sections')
    sections = md2latex.analyze_large_sections(md_content)

    LOGGER.info('analyzing sections for doclets')
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
    interdoc_labels = dict(table=[], code=[], latex=[], quote=[], fig=[], header=[])
    cleanup_filepaths = []  # TODO: cleanup
    while sections:
        section, md_content, mo = sections.pop(0)

        for url_mo in md2latex.REGEX_URL.finditer(md_content):
            start = url_mo.start()
            if md_content[start-1] != '(':
                end = start+64
                endline = md_content.find('\n', start) - 1
                end = min([end, endline])
                errors.append(f'naked url! enclose with []()! {md_content[start:end]}...')

        if appendix:
            appendix = False  # switch it back off, we JUST turned it on for someone else
        data = {}
        content = md_content
        label = ''
        caption = ''
        groups = []
        groupdict = {}
        start, end = -1, -1
        if mo is not None:
            groups = mo.groups()
            groupdict = mo.groupdict()
            start, end = mo.span()
        if section != 'any':
            if section in set(['table', 'code', 'latex', 'quote', 'literal']):
                caption = groupdict.get('caption', '')
                label = groupdict.get('label', '')
                content = groupdict.get('content', '')

                if section in set(['quote']):
                    # NOTE: starting from the very first > to the last...
                    content = md2latex.REGEX_CAPTION_LABEL_COMMON.sub('', md_content)

                if not content:
                    raise RuntimeError('could not determine content?!')

                if not label and section not in set(['literal']):
                    example = 'label: something-or-other'
                    if section in set(['latex']):
                        example = '%\\label{something-or-other}'
                    errors.append(f'{section} missing "{example}"!\n{indent(md_content[:64])}...')
                if not caption and section not in set(['latex', 'literal']):
                    # caption is also required for these
                    errors.append(f'{section} missing "caption: Something or Other"!\n{indent(md_content[:64])}...')

                if label:
                    if label.startswith('label:'):
                        label = label[6:].strip()
                    interdoc_labels[section].append(label)
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
                find_bad_citations(md_content, errors, warnings)

            doclets.append(dict(section=section, label=label, caption=caption, content=content, appendix=appendix, mo=mo, data=data))
        else:
            small_sections = md2latex.analyze_small_sections(md_content)
            for section_sub, md_content_sub, mo_sub in small_sections:
                if appendix:
                    appendix = False  # switch it back off, we JUST turned it on for someone else
                label = ''
                caption = ''
                data = {}
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
                        linenos = list(find_lineno_index(md_content_sub, original_md_content))
                        errors.append(f'headings > 4 not supported at lineno {linenos[0][0] + 1}, {label!r}')
                        continue

                    if title.lower() == 'appendix':
                        appendix = True
                    label = '-'.join(label.split())
                    interdoc_labels['header'].append(label)
                elif section_sub == 'img':
                    caption = groupdict_sub.get('alt', '')
                    path = groupdict_sub.get('path', ')')[:-1]
                    if not path:
                        errors.append(f'img missing path\n{indent(md_content_sub)}')
                        continue
                    label = os.path.basename(path)
                    # label = re.sub(r'[^\w]', '', os.path.splitext(label)[0])
                    # label = '-'.join(label.split())
                    interdoc_labels['fig'].append(label)

                    if output_dirpath:
                        if path.startswith('http'):
                            filepath = path.split('/')[-1].split('?')[0]
                            img_filepath = pathlib.Path(output_dirpath) / filepath
                            LOGGER.info('downloading "%s"...', path)
                            try:
                                download(path, filepath=img_filepath, skip_exist=True)
                                cleanup_filepaths.append(img_filepath)
                            except Exception as exe:
                                errors.append(f'img bad url, resulted in {exe}\n{indent(md_content_sub)}')
                        else:
                            img_filepath = pathlib.Path(md_dirpath) / path
                            copied_img = shutil.copy2(str(img_filepath), output_dirpath)
                            cleanup_filepaths.append(copied_img)

                        path = img_filepath.name
                        data['path'] = path

                    path, ext = os.path.splitext(path)  # doesnt like extensions???
                    if ext.lower() in ['.svg']:
                        raise RuntimeError(f'image src at "{path}" is using a forbidden extension, cannot proceed')

                elif section_sub == 'any':
                    # i know ahead of time that bad usage of citations is a bad look.
                    find_bad_citations(md_content_sub, errors, warnings)

                else:
                    raise NotImplementedError(f'subsection {section_sub!r} not anticipated')

                doclets.append(dict(section=section_sub, label=label, caption=caption, content=md_content_sub, appendix=appendix, mo=mo_sub, data=data))

    all_labels = {}  # str: StR
    interdoc_label_types = {}
    for k in bibtex_labels.keys():
        all_labels[k.lower()] = k
    for key, values in interdoc_labels.items():
        for value in values:
            if value.lower() in all_labels:
                errors.append(f'duplicate {key} label {value!r}')
            all_labels[value.lower()] = value
            interdoc_label_types[value] = key

    # {'quote', 'table', 'latex', 'literal', 'comment', 'yaml', 'code', 'header', 'any', 'img', 'list'}
    print(set(doc['section'] for doc in doclets))

    spellcheckable_sections = set(['header', 'any', 'list'])
    spellcheckable_words = ''
    for doclet in doclets:
        if doclet['section'] in spellcheckable_sections:
            spellcheckable_words += md2latex.get_words_only(doclet['content'])

    LOGGER.info('spellcheck...')
    write_text_file('./ignoreme/spellcheckable_words.txt', spellcheckable_words)

    error_words, warning_words, word_count = spellcheck(spellcheckable_words)
    LOGGER.info('wc: %d', word_count)
    if warning_words:
        warnings.append(f'{len(warning_words)} warning words discovered!')
        for word in sorted(warning_words):
            warnings.append(f'    - {word}')
            for lineno, idx in find_lineno_index(word, original_md_content):
                warnings.append(f'        - lineno {lineno}, ...{original_md_content[idx-8:idx+len(word)+8]!r}...')
    if error_words:
        errors.append(f'{len(error_words)} error words discovered!')
        for word in sorted(error_words):
            correctword = error_words[word][0][2]
            errors.append(f'    - {word} -> {correctword}')
            for lineno, idx in find_lineno_index(word, original_md_content):
                errors.append(f'        - lineno {lineno}, ...{original_md_content[idx-8:idx+len(word)+8]!r}...')
    else:
        LOGGER.info('no misspelled words! (probably)')


    import pprint
    pprint.pprint(interdoc_labels, indent=2, width=160)

    if warnings:
        LOGGER.warning('%d warnings!', len(warnings))
        for warning in warnings:
            LOGGER.warning(warning)
    else:
        LOGGER.info('warning free!')

    if errors:
        LOGGER.error('%d errors!', len(errors))
        for error in errors:
            LOGGER.error(error)
        sys.exit(1)
    else:
        LOGGER.info('error free!')

    errors.clear()
    warnings.clear()

    # render time
    # {'quote', 'table', 'latex', 'literal', 'code', 'header', 'any', 'img', 'list'}
    header_render = {}
    body = []
    appendix_body = []
    appendix = False
    append_appendix = False
    for doclet in doclets:
        section, content, label, caption, mo, data = (
            doclet['section'], doclet['content'], doclet['label'], doclet['caption'], doclet['mo'], doclet['data'],
        )
        if section in set(['comment']):
            continue
        elif section in set(['yaml']):
            header_render = markdown_header_to_render_dict(content, bibliography_output_filepath, template=template)
            continue

        if doclet['appendix'] is True:
            appendix = True

        if caption:
            # are there refs IN THE CAPTION?
            caption = markdown_refs_to_latex(caption, original_md_content, all_labels, interdoc_label_types, errors, template=template)


        # TODO: auto Fig. Table. Code. etc.
        if section == 'header':
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
            aligned = content.startswith('\\begin{align')
            content = content.strip()  # NOTE: the .strip() is CRITICAL. if you have \begin{math}\n\n\begin{aligned} you're TOAST
            if aligned:
                # convert it to an equation anyway. regardless if sense or not.
                # content = f'\\begin{{math}}\n{content}\n\\end{{math}}'
                content = f'\\begin{{equation}}\n{content}\n\\end{{equation}}'
            content = content.replace(r'\begin{equation}', f'\\begin{{equation}}\n\\label{{{label}}}')
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
            for url_mo in reversed(list(md2latex.REGEX_MARKDOWN_URL.finditer(content))):
                url = url_mo.groups()[-1][:-1]  # lop off last )
                content = f'{content[:url_mo.start()]}\\url{{{url}}}{content[url_mo.end():]}'
            content = md2latex.REGEX_MARKDOWN_URL.sub(r'\\url{\g<2>}', content)
            # are there refs IN THE CONTENT?
            content = markdown_refs_to_latex(content, original_md_content, all_labels, interdoc_label_types, errors, template=template)
            # are there `literal` in the content?
            content = md2latex.REGEX_MARKDOWN_LITERAL_INLINE.sub(r'\\lstinline{\g<1>}', content)
            # are there $latex$ in the content?
            content = md2latex.REGEX_MARKDOWN_LATEX_INLINE.sub(r'\\(\g<1>\\)', content)
            # are there any emphasis like bold, italic, underline, etc?
            # TODO: underline/strikethrough
            content = md2latex.markdown_emphasis_to_latex(content)

            if section == 'quote':
                # TODO: currently sane washing all > beginnings
                content = '\n'.join(line[line.rindex('>')+1:].strip() for line in content.splitlines())
                content = f'\\begin{{quotation}}\n{content}\n\\end{{quotation}}'
            elif section == 'list':
                content = md2latex.markdown_list_to_latex(content)

        # print('caption', caption, 'label', label)
        # body.append(f'caption: {caption}')
        # body.append(f'label: {label}')
        if append_appendix:
            appendix_body.append(content)
        else:
            body.append(content)

    # write_text_file('./ignoreme/output.tex', '\n'.join(body))

    if warnings:
        LOGGER.warning('%d warnings!', len(warnings))
        for warning in warnings:
            LOGGER.warning(warning)
    else:
        LOGGER.info('warning free!')

    if errors:
        LOGGER.error('%d errors!', len(errors))
        for error in errors:
            LOGGER.error(error)
        sys.exit(1)
    else:
        LOGGER.info('error free!')

    errors.clear()
    warnings.clear()

    # ready to render
    LOGGER.info('Rendering. All pre-flight checks passed.')
    LOGGER.info('NOTE: If spellcheck failed, pass --spellcheck to force exit')

    header_render['<BODY>'] = '\n\n'.join(body)
    header_render['<APPENDIX>'] = '\n\n'.join(appendix_body)

    template_filepath = TEMPLATES[template]
    with open(template_filepath, 'r', encoding='utf-8') as r:
        template_content = r.read()

    rendered_content = template_content[:]
    for k, v in header_render.items():
        rendered_content = rendered_content.replace(k, v)
    rendered_content = re.sub(r' {2,}', ' ', rendered_content)
    write_text_file(tex_output_filepath, rendered_content)

    pprint.pprint(header_render, indent=4, width=160)

    # run pdflatex 4 times...
    LOGGER.warning('deleting previous work files...')
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
            LOGGER.error('%d / %d - %s, TIMEOUT %0.2f sec!', c + 1, len(cmds), subprocess.list2cmdline(cmd), timeout)
            LOGGER.debug('%d / %d - %s, TIMEOUT %0.2f sec!\n%s', c + 1, len(cmds), subprocess.list2cmdline(cmd), timeout, read_text_file_try(stdout))
            sys.exit(2)
        finally:
            os.remove(stdout)

    # NOTE: only clean up if everything went well, leave everything behind if it didnt...
    LOGGER.info('deleting unnecessary work files...')
    md2latex.delete_latex_work_files(output_dirpath, md_filename, extra=cleanup_filepaths)
    LOGGER.info('pdf at "%s"', pdf_output_filepath)

    return 0


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    md2latex.assert_executables_exist()

    return markdown_to_latex(
        args.markdown_filepath,
        args.output_dirpath,
        bibliography_filepath=args.bibliography_filepath,
        template=args.template,
        wc=args.word_count,
        debug=args.debug,
    )


if __name__ == '__main__':
    sys.exit(main())
