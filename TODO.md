pandoc wrapper

    integrate the pandoc wrapper asap even if it blows

    too deeply nested is a lie.

md2pdf
    bugs

        md2pdf CMPE-180D\assignments\hw1\2026S-SJSU-CMPE180D-hw_1-chris_carl.md -b .\CMPE-180D\assignments\hw1\bibliography.md -o render --template chicago
            causes bad news???

        emphasis analys can only happen AFTER literals have been processed.
        OR find some way to "attach" literals and other inliners to the previous element in the appended list.

    features

        bibtex in the document needs to be extracted. especially if it has a header or something.

        add a cwd command maybe? everything relative to that then... makes finding bibs easier, etc.
            OR autobib just crawls through every file and finds bibtexes... that would be fun.

new app
    auto clean-up markdown
        replace Xbar XBar w/ \bar{X} and xbar xBar with \bar{x}
        [^\\]le -> \le
        find latex looking sections and surround with latex so long as it renders?
