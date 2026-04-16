latex watch
    \bmatrix -> \begin{bmatrix}
    xbar -> \bar{x}
    yhat -> \yhat
    xyhat -> \overline{xy}

latex alignment indentation


        m\hat{p_1}      &= 633 \times 0.2970        &&= 1234 > 10 ? \checkmark \\
        m(1-\hat{p_1})  &= 633 \times (1 - 0.2970)  &&= 1234 > 10 ? \checkmark \\
        n\hat{p_2}      &= 166 \times 0.2892        &&= 1234 > 10 ? \checkmark \\
        n(1-\hat{p_2})  &= 166 \times (1 - 0.2892)  &&= 1234 > 10 ? \checkmark \\


> empty is good for markdown preview, not good for latex. eliminate > empties



pandoc wrapper

    integrate the pandoc wrapper asap even if it blows

        pandoc CMPE-180C/notes/midterm-notes.md `
        --from=gfm --to=pdf --standalone --mathjax `
        --output CMPE-180C/notes/midterm-notes.pdf

    too deeply nested is a lie.

ipynb
    test what kind of header the ipynb thinks for headers example:
        "## 5) Trend : 'EV Prices Over Time'" -> "#5-trend--ev-prices-over-time"



md2pdf

    pandoc:
        search for
        "                -" for deeply nested stuff

        pandoc guard find unicode first and deal with it

    bugs
        support list in yaml geometry:
            - "margin=0.25in"
            # - landscape
        etc.

        ```
        - inline `markdown` in a list
        - bulleted `inline` is a problem
        ```

        having 1 literal in the open like `hello` and another in the open like ```asdfasdf``` and -alc causes lit-1 to appear twice...

        problem with it thinking that these are tables...

            ```
            ## 45
            Show which JMP instruction assembles (short, near, or far) if the JMP THERE instruction is stored at memory address 10000H and the address of THERE is:


            - (a) `l0020H`

            short - location is within 1 bytes. $| 10020H - 10000H | = 20H < FFH$

            - (b) `11000H`
            ```


        arrow citation within a > quote...

        biber no output / no output biber
            happens when no citations used!
            create the .bib ONLY WHEN CITATIONS ARE USED...

        better lineno messages, its supposed to be "file", line 69

        - caption label redo, do not scan for it (in the same regex), its not worth it, look for it immediately before OR immediately after a section
            - NOTE this will cut into the previous doclet

        interref is being referred to through autocite but should instead be a ~ref...
            md2pdf CMPE-180D/assignments/hw1/2026S-SJSU-CMPE180D-hw_1-chris_carl.md `
                -b CMPE-180D/assignments/bibliography.md `
                -t math `
                -o CMPE-180D/assignments/hw1/render -ss

        [https://gss.norc.org/](https://gss.norc.org/) is not "naked"...

        confirm if order matters:

            ```diff
            -        # can have other stuff embedded
            -        ('table', REGEX_MARKDOWN_TABLE),
            -        ('latex', REGEX_MARKDOWN_LATEX),
            +        # can have other stuff embedded, ORDER MATTERS because of who is considered a literal and who isnt
                    ('literal', REGEX_MARKDOWN_MULTILINE_LITERAL),
                    ('code', REGEX_MARKDOWN_CODE),
            +        ('list', REGEX_MARKDOWN_LIST),  # lists can contain latex, tables, quotes, etc, so it is supreme
            +        ('latex', REGEX_MARKDOWN_LATEX),
            +        ('table', REGEX_MARKDOWN_TABLE),
                    ('quote', REGEX_MARKDOWN_QUOTE),
            -        ('list', REGEX_MARKDOWN_LIST),
            ```

            above order failed for the following

            ```
            4. calculate confidence interval, rejection region, p-value

                $$
                \begin{aligned}
                \rm{CI} (1 - \alpha)\%  &= \hat{\delta} \pm \rm{CV} \times \widehat{SE}(\hat{\delta}) \\
                                        &= 0.0078 \pm 1.96 \times 0.03789 \\
                                        &= (0.0078 - 1.96 \times 0.03789, 0.0078 + 1.96 \times 0.03789) \\
                                        &= (-0.0665, 0.0821) \\
                \end{aligned}
                $$

                Two-tailed test: if test statistic > abs(critical value), then the test statistic is in the rejection region.

                $$
                \vert z \vert > Z_{\alpha/2} ? \\
                \vert 0.02056 \vert > 1.96 ? \times \\
                $$

                The test statistic is not in the rejection region.
            ```

            maybe something to do with the way begin aligned occurs while it doesnt for the others?

        latex cases need to be handled:
            - inline
            - doubleine
                - equation
                - aligned
                - nothing
                - label provided somewhere, or not (out of order, or not)

        inline bibliography doesnt work if it's not at the bottom???

        emphasis analys can only happen AFTER literals have been processed.
        OR find some way to "attach" literals and other inliners to the previous element in the appended list.

    find naked math and prompt user to deal with it, or better handling probably within lists...
        both of these fail:

            ```
            2. Save Script to > Data Table whatever
            ```

            ```
            2. `Save Script to > Data Table` whatever
            ```

    stick to whether the bibilography should be finelname or filepath....

    tables need to be indented or shit happens?!

        ```
        Participants were asked if they ($\rm{Agree}$ or $\rm{Disagree}$) with the following statement: “I have confidence in the public education system.” The responses collected between the the years 2014-2018 are shown below for both full time time and part time workers:

            |        |Full Time|Part Time|
            |--      |--       |--       |
            |Agree   |188      |48       |
            |Disagree|445      |118      |

        Use this data to test the following hypothesis: “For the years 2014-2018, was the proportion of full time workers who agree with this statement is different from the proportion of part time worker
        ```


    support bibtex with bad types like ARTICLE or Article -> article

    if a reference is given like this <hello...>, only then autosearch, OR if the ref is outright missing, then attempt a diff that fits above a certain threshold.

    RIS to bibtex
        https://link.springer.com/article/10.1007/s11098-024-02273-w#citeas
        - also looks like used in search terms... (SO (The accounting review.))AND(DT 2020)AND(TI how calibration committees can mitigate performance evaluation bias)
        - https://research-ebsco-com.libaccess.sjlibrary.org/c/wm4vue/search/details/eycssiw2ej?db=bth&limiters=&q=%28SO%20%28The%20accounting%20review.%29%29AND%28DT%202020%29AND%28TI%20how%20calibration%20committees%20can%20mitigate%20performance%20evaluation%20bias%29

    python C:\Users\chris\src\pgp-aiml\scripts\ipynb\ipynb-toc-export-execute-html.py `
        ISE-201\assignments\02-ipynb-critique\2026S-SJSU-ISE201-hw_03-chris_carl.ipynb

    - might be able to do the Table/Code thing by just searching for those occurances and confirming that 'Table ' is exactly before the citation match...
    - if there are tables or figures and theyre are NOT referenced, should error out. thats not a good thing.

    - code colors
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