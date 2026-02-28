# chriscarl.tools.documents
Since I enrolled in SJSU in 2025F as an MS CMPE student, I have found need for lots of tools like C/C++ compilation and test, Markdown to LaTeX, and others. This project will serve to bundle all of those.


# Features
|version|author|deployed|created|feature-name|description|
|---    |---   |---     |---    |---         |---        |


# Acknowledgements


# Maintenance
```bash
stubgen -o dist/typing/chriscarl --no-analysis ../chriscarl.python/src
stubgen -o dist/typing -m chriscarl.core.lib.third.spellchecker -m chriscarl.files.manifest_documents -m chriscarl.tools.shed.* -m chriscarl.tools.*  --include-docstrings
python -m pytest --cov=chriscarl.tools tests --cov-report term-missing
```


# Chris Carl Isms
```bash
project new chriscarl.tools.documents "tools.documents shall serve for common situations like html2md, md2latex, and others like that." --dirpath ~/src --type python --module-type

dev create tools.documents --tool --namespace
dev create tools.shed.documents --namespace
dev create core.lib.third.spellchecker --namespace
dev create tools.md2bibtex --tool --namespace
dev create tools.html2md --tool --namespace
dev create tools.shed.md2bibtex --namespace
```



```
Definition:
    - label: a name/label for something ON the doc/bib
    - ref: a reference to a label
    - citation: a ref to a bibliography label

Shape of the algorithm:

# clean the bibliography
    bibliography = read bibliography
    bibtex content = extract bibtex content
    bib-labels = extract all keys
    clean the bibtex content so that it will render correctly
    if any cleaning occurred, copy a new bibfile
    else, use current bibfile
    TODO: test that it renders correctly by doing a dummy documenet

# annotate the markdown
    BAD unicode replace

    sections = []
    header_locations = re.find(#+)
        section.append(pre-amble section is before the first mo)
        sections.extend(ranges from each.)

    errors = []
    doclets = [
        ('yaml', '---asdf: whatever---', spellcheck='')
        ('plain', 'asdfasdfasdf', spellcheck='asdfasdf')
        ('comment', '---asdf: whatever---', spellcheck='')
        ('table', '|||', caption='capt', label='asdf', spellcheck='')
        ...
        ('header', 'introduction', label='introduction', spellcheck='introduction')
        ...
        ('header', 'introduction', label='introduction', spellcheck='introduction', appendix=True)
    ]
    appendix = False
    doc-labels-existing = {}
    doc-refs-requested = []
    for section in sections:
        def analyze_section:
            header? add that to the labels
                if appendix
            errors:
                naked hyperlinks? warn that it must be enclosed
            extract and remove and parse:
                yaml?
            note the range:
                # blocks
                    # may also include refs other blocks or inlines...
                        list?
                        image?
                            path exists, downloaded or downloadable?
                        table?
                            properly captioned, reffed?
                    # cannot include refs
                        comments?
                        latex double?
                        code/backticks?
                # inline
                    backticks?
                    latex single?
                    citations?
                        if interdoc, do they have the pref?

    for ref in doc-refs-requested:
        if ref not in doc-labels-existing:
            add to errors
    if errors:
        ref errors

    yaml = extract yaml section

# wordcount the markdown
    markdown = read markdown
    if wordcount:
        print a best word count and return

# spellcheck if asked

# render the content
    according to yaml
    for doc in doclets
        get latex
    append to body/appendix

```