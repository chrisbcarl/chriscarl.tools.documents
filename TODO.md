pandoc wrapper

    integrate the pandoc wrapper asap even if it blows

    too deeply nested is a lie.

ipynb
    test what kind of header the ipynb thinks for headers example:
        "## 5) Trend : 'EV Prices Over Time'" -> "#5-trend--ev-prices-over-time"



md2pdf
    stick to whether the bibilography should be finelname or filepath....

    BUG:
        # BUG: LIST CITATION list is getting rendered as html..., then picked up as citations...
            '<ol start="2">' is being picked up as a citation...

    support bibtex with bad types like ARTICLE or Article -> article

    if a reference is given like this <hello...>, only then autosearch, OR if the ref is outright missing, then attempt a diff that fits above a certain threshold.

    RIS to bibtex
        https://link.springer.com/article/10.1007/s11098-024-02273-w#citeas
        - also looks like used in search terms... (SO (The accounting review.))AND(DT 2020)AND(TI how calibration committees can mitigate performance evaluation bias)
        - https://research-ebsco-com.libaccess.sjlibrary.org/c/wm4vue/search/details/eycssiw2ej?db=bth&limiters=&q=%28SO%20%28The%20accounting%20review.%29%29AND%28DT%202020%29AND%28TI%20how%20calibration%20committees%20can%20mitigate%20performance%20evaluation%20bias%29

    python C:\Users\chris\src\pgp-aiml\scripts\ipynb\ipynb-toc-export-execute-html.py `
        ISE-201\assignments\02-ipynb-critique\2026S-SJSU-ISE201-hw_03-chris_carl.ipynb

    - might be able to do the Table/Code thing by just searching for those occurances and confirming that 'Table ' is exactly before the citation match...
    - code colors
    - if there are tables or figures and theyre are NOT referenced, should error out. thats not a good thing.
    - you're triggers spellcheck because i'm getting rid of all ' in words... maybe solution is to get rid of all ' words and append them in the end or something?
    - a naked ^ in the middle of text is interpreted as math... or perhaps a 2^2 is but ^ naked isnt?
    - invocations that sfail:
        md2pdf ISE-201\assignments\00-llm\paper-md2pdf.md `
            -b ISE-201\assignments\00-llm\bibliography.md `
            -o ISE-201\assignments\00-llm\render-2 -ss
        md2pdf ISE-201\assignments\00-llm\paper.md `
            -b ISE-201\assignments\00-llm\bibliography.md `
            -o ISE-201\assignments\00-llm\render-2 -ss

    - make a paper-md that really covers every edge case
        - references INSIDE math doesn't really work... better to put it outside.
        - ref in table still bad ISE-201/assignments/00-llm/render/paper-md2pdf.pdf
    - test elipses and cdots behavior
        - you may want to replace something different in the code or literal section...
        - CMPE-180D\assignments\hw1\2026S-SJSU-CMPE180D-hw_1-chris_carl.md
    - "ted to cross-reference whether" was picked up as a ref somehow...
    - table doesnt get picked up if at end C:/Users/chris/OneDrive/_recent/SJSU_2026S/ISE-201/assignments/00-llm/paper-md2pdf.md
        - even IF you add some text at the bottom to clear up the above
        - moving "investigation-findings-tbl" stuff below that table causes massive problem
    - old table missing caption/label doesnt get mentioned
    - check research-aid-2 for leftovers
    - default template doesnt work, figure something out package wise...

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
            - OR autobib just crawls through every file and finds bibtexes... that would be fun.
            - find bibliography if close by

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