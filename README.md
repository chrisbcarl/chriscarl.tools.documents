# chriscarl.tools.documents
Since I enrolled in SJSU in 2025F as an MS CMPE student, I have found need for lots of tools like C/C++ compilation and test, Markdown to LaTeX, and others. This project will serve to bundle all of those.


# Features
|version    |author     |deployed   |created    |feature-name                           |description        |
|---        | ---       | ---       | ---       | ---                                   | ---               |


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
