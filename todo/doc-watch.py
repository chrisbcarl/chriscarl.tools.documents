'''
pretty rough outline of an applet
2026-02-15 21:58 - finished first pass, the idea is to have some kind of doc watcher and you invoke it like this:
    the service can autoload on pc
    took too long fiddling with novel markdown regexes, decided to just work around what works.
    also double-barrier on last modified and hash value
        doc-watch
            tables.md   md-table-pretty
            latex.md   md-auto-latex
2026-02-15 20:45 - started
'''
import re
import os
import time
import hashlib
from chriscarl.core.lib.stdlib.io import read_text_file, write_text_file
from chriscarl.core.functors.parse.markdown import table_prettify
from chriscarl.core.types.str import indent


def get_hash(content):
    # type: (str) -> str
    md5 = hashlib.md5(content.encode())
    return md5.hexdigest()


REGEX_MARKDOWN_TABLE = re.compile(r'(?P<indent>[ \t]*)\|(?P<table>.+?)\|\n\n', flags=re.DOTALL | re.MULTILINE)
filepaths = [
    r'ignoreme\tables.md',
    r'C:\Users\chris\OneDrive\_recent\SJSU_2026S\CMPE-180D\notes\ch3\ch3.md',
]
filepaths_modified = {filepath: 0.0 for filepath in filepaths}
try:
    while True:
        for filepath, prior in filepaths_modified.items():
            modified = os.path.getmtime(filepath)
            if modified > prior:
                markdown = read_text_file(filepath)
                prior_hash = get_hash(markdown)
                mos = list(REGEX_MARKDOWN_TABLE.finditer(markdown))
                for mo in reversed(mos):
                    start, end = mo.span()
                    groups = mo.groupdict()
                    indentation = len(groups['indent'])
                    table = f'|{groups["table"]}|'
                    replacement = indent(table_prettify(table), indent=' ' * indentation)
                    markdown = f'{markdown[:start]}{replacement}\n\n{markdown[end:]}'
                replaced_hash = get_hash(markdown)
                if prior_hash != replaced_hash:
                    write_text_file(filepath, markdown)
                    print('replaced', filepath, modified, '>', prior)
                filepaths_modified[filepath] = modified
        time.sleep(0.1)

except KeyboardInterrupt:
    print('ctrl+c detected')
