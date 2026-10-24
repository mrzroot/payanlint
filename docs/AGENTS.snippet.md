<!-- Paste into AGENTS.md, CLAUDE.md, .cursorrules or your agent's rules file. Requires `pipx install git+https://github.com/mrzroot/payanlint`. -->

## Persian (Farsi) Word theses: typing and formatting

When asked to edit, format or "clean up" a Persian `.docx` (thesis, report), do not retype it and do not trust what python-docx reports for Persian text:
`run.font.size` / `run.bold` set the Latin slots only; Persian text takes its font, size and bold from `w:cs`, `w:szCs`, `w:bCs`. Lint first:

```sh
payanlint thesis.docx                  # typing (half-space, ي/ك, digits, punctuation) + formatting (fonts, margins, captions, page numbers)
payanlint thesis.docx --json           # machine-readable
payanlint thesis.docx --fix            # writes thesis.payanlint.docx with safe TEXT fixes only; never overwrites
```

- Report the findings; do not "fix" formatting findings (F-codes) yourself unless the user gives the university's values (`--body-font`, `--body-size`, `--line`, `--margins`).
- Never edit the result of a SEQ / PAGE field by hand: Word regenerates it. `--fix` already skips field results.
- Digits are a policy: ask whether the thesis uses Persian digits (`--digits fa`) before converting.
- It is heuristic and not an official university validator. Tell the user to open the result in Word and look at the flagged lines.
- It runs offline and reads/writes only the files you give it.
