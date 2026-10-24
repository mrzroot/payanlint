# Novelty check: payanlint

Done 2026-10-24 before publishing. Wording is deliberately modest. **The individual Persian typing rules in payanlint are not new**
(Virastyar, Virastar and others have had them for years); what I found no tool for, as of October 2026, is the *combination*:
an offline command-line linter for a Persian Word thesis that checks typing conventions **and** Word's real formatting properties
(including the complex-script slots `w:cs` / `w:szCs` / `w:bCs` that carry Persian text's font, size and bold), caption numbering and page
numbering, with exit codes for scripts and a `--fix` that provably touches only characters in `<w:t>` text. That is not a claim that no such
tool exists anywhere; if you know one, please open an issue and it will be linked here.

## Searches

GitHub repository search (API, total results; AND-of-terms and noisy):

| query | total |
|---|---|
| `persian docx linter` | 0 |
| `farsi thesis docx check` | 0 |
| `persian zwnj checker` | 1 |
| `نیم‌فاصله ورد` | 0 |
| `persian half-space checker` | 1 |
| `persian arabic yeh kaf docx` | 0 |
| `persian digits docx converter` | 0 |
| `پایان‌نامه فرمت ورد` | 0 |
| `docx szCs complex script size` | 0 |
| `docx bCs bold complex script` | 0 |
| `persian word document formatting` | 4 |
| `thesis formatting checker university docx` | 1 |
| `virastar docx` | 1 |
| `persian proofreading docx python` | 0 |
| `docx persian typography` | 6 |
| `farsi docx python` | 1 |

Also searched (2026-10-24): npm registry (`persian-docx`, `virastar`, `thesis-lint`, `persian typography`, `half-space persian`, `persian thesis`, `farsi docx`, `docx lint`, `persian zwnj`:
text libraries and generic DOCX libraries only), PyPI JSON lookups for the names `payanlint`, `docxlint` (a Jinja2-template validator, unrelated), `persian-docx-lint`, `thesis-lint`, `farsi-docx`
(free or unrelated), and web searches (`ابزار بررسی فرمت پایان‌نامه ورد نیم‌فاصله ی ک عربی`, `Persian thesis Word document format checker tool half-space ZWNJ Arabic yeh kaf lint docx`).

## Closest existing work

| project | what it is | difference |
|---|---|---|
| [Virastyar / ویراستیار](https://virastyar.ir/) | free, open-source **Word add-in** (Windows + Word + VBA): spell checking, character fixing (ک/ی, Arabic digits, half-space), می/ها spacing, punctuation, number and date conversion | overlaps with the typing rules (P1xx). Interactive, needs Word on Windows; its own FAQ says development stopped and there is no official release for Word 2016/2019. It does not look at fonts, margins, captions or page numbers. |
| [Virastar](https://github.com/octoberfa/virastar) (npm `virastar`, `@nekofar/virastar`) | JavaScript library that cleans Persian *text* | text in, text out; does not read a `.docx` |
| `persian-normalize`, `@persian-tools/persian-tools`, `hazm`, `parsivar` | Persian text and NLP libraries | libraries for strings, not Word files |
| [ali-m07/virastar-tanbel](https://github.com/ali-m07/virastar-tanbel) (PyPI `virastar-tanbel`, created 2026-08) | closest: a `.docx` **fixer** for Persian: RTL on paragraphs, runs and tables, `fa-IR`, punctuation, ي/ك, Latin tokens wrapped in LRM | it rewrites; I did not find a report-first mode, thesis formatting rules (fonts/sizes/margins/captions), or half-space rules in its README. payanlint does not change direction at all (that is [vazhgun](https://github.com/mrzroot/vazhgun)'s job). |
| [Auctory thesis format checker](https://auctoryai.com/thesis-format-checker/) | in-browser `.docx` checker: margins, line spacing, font and size, heading styles, page-number field; per-university presets | generic (not Persian orthography); its description lists `w:rFonts` and `w:sz`, and I found no mention of the complex-script slots that decide how Persian text looks. Reports only, by design. |
| [sasanvhn/Word-Document-Formatting-Checker](https://github.com/sasanvhn/Word-Document-Formatting-Checker) (2023) | small python-docx script comparing fonts, sizes and spacing of Persian and English paragraphs with a JSON file | reads `run.font.name` / `run.font.size`; python-docx's `size` writes and reads `w:sz`, the Latin slot (see sadeghr64/persian-docx below), so Persian size and bold are not what it sees. No typing rules. |
| [samanmehrani/word-formatter](https://github.com/samanmehrani/word-formatter) | script that re-formats Word files from a reference template (B Nazanin, RTL, 1.5 spacing, tables) | a formatter, not a checker; no report |
| [sadeghr64/persian-docx](https://github.com/sadeghr64/persian-docx) | agent skill for *producing* Persian `.docx` that renders correctly; documents the `szCs` and RTL pitfalls | generation guidance, not a linter for an existing thesis; its findings are why payanlint reads the complex-script slots |
| [wksudud/format-thesis-docx](https://github.com/wksudud/format-thesis-docx) | DOCX thesis formatting automation (extract requirements, audit, corrected copy) | I could read only its one-line description; no Persian/Iranian focus visible |
| [mohammad-abbasi-sh/bidi-skills](https://github.com/mohammad-abbasi-sh/bidi-skills) | skills plus a checker for how AI agents write RTL text (ZWNJ, bidi) | about text an agent produces; I did not find a Word-file linter in it |

## Verdict

Distinct combination: **Persian typing rules + Word complex-script formatting checks + caption/page-number checks, offline and scriptable, with a conservative
`--fix` that edits only text and never field results**. Pieces of it are well covered elsewhere (typing rules by Virastyar, bidi/RTL fixing by virastar-tanbel,
generic margin/font checks by Auctory). What I could not find is one tool that does the Persian-specific *formatting* checks for a thesis file. I did not test Virastyar or virastar-tanbel
myself; the descriptions above come from their own pages.
