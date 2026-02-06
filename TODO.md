pandoc wrapper

    integrate the pandoc wrapper asap even if it blows

    too deeply nested is a lie.

md2pdf
    bugs

        quotes are demanding captions and labels, not necessary...
            md2pdf CMPE-180D\assignments\hw1\2026S-SJSU-CMPE180D-hw_1-chris_carl.md `
                -b .\CMPE-180D\assignments\hw1\bibliography.md `
                -o .\CMPE-180D\assignments\hw1\render --template chicago


        md2pdf CMPE-180D\assignments\hw1\2026S-SJSU-CMPE180D-hw_1-chris_carl.md -b .\CMPE-180D\assignments\hw1\bibliography.md -o render --template chicago
            causes bad news???

        emphasis analys can only happen AFTER literals have been processed.
        OR find some way to "attach" literals and other inliners to the previous element in the appended list.

    features

        warn that citation within math mode is dicey...

        fuzzy ref
            if the ref is "good enough", starts with, then its good enough regardless of non-alphanumeric, etc.

        bibtex in the document needs to be extracted. especially if it has a header or something.

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