pandoc wrapper

    integrate the pandoc wrapper asap even if it blows

    too deeply nested is a lie.

md2pdf
    - bib ensure the types supported are actually supported "software" is not supported as a bib
    - make a paper-md that really covers every edge case
        - references INSIDE math doesn't really work... better to put it outside.
    - test elipses and cdots behavior
    - ref in table still bad ISE-201/assignments/00-llm/render/paper-md2pdf.pdf
    - "ted to cross-reference whether" was picked up as a ref somehow...
    - table doesnt get picked up if at end C:/Users/chris/OneDrive/_recent/SJSU_2026S/ISE-201/assignments/00-llm/paper-md2pdf.md
        - even IF you add some text at the bottom to clear up the above
        - moving "investigation-findings-tbl" stuff below that table causes massive problem
    - old table missing caption/label doesnt get mentioned
    - errant prints
    - check research-aid-2 for leftovers
    - find bibliography if close by
    - md2pdf vs md2latex, NOT THE SAME
    - default template doesnt work, figure something out import-wise...
    - refactor

    bugs

        interref is being referred to through autocite but should instead be a ~ref...
            md2pdf CMPE-180D/assignments/hw1/2026S-SJSU-CMPE180D-hw_1-chris_carl.md `
                -b CMPE-180D/assignments/bibliography.md `
                -t math `
                -o CMPE-180D/assignments/hw1/render -ss

        emphasis analys can only happen AFTER literals have been processed.
        OR find some way to "attach" literals and other inliners to the previous element in the appended list.

    features

        warn that citation within math mode is dicey...

        fuzzy ref
            if the ref is "good enough", starts with, then its good enough regardless of non-alphanumeric, etc.

        add a cwd command maybe? everything relative to that then... makes finding bibs easier, etc.
            OR autobib just crawls through every file and finds bibtexes... that would be fun.

        allow label anywhere in the math regex

new app
    auto clean-up markdown
        replace Xbar XBar w/ \bar{X} and xbar xBar with \bar{x}
        [^\\]le -> \le
        find latex looking sections and surround with latex so long as it renders?


# Junk Code
```python

# # in a previous attempt I tried to escape everything correctly
#     for char in ['$', '#', '%', '&', '~', '_', '^', '{', '}']:
#         regex = r'[^\\]' + re.escape(char)
#         print(regex)
#         for submo in reversed(
#                 list(re.finditer(regex, bibtex_content[start:end]))):
#             substart, subend = submo.start(), submo.end()
#             bibtex_content = f'{bibtex_content[:start + substart]}\\{char}{bibtex_content[start + subend:]}'
# fixed_bibtex_content = re.sub(r'_', '\\_', bibtex_content)

```