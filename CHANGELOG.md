# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-24

First release.

### Added
- `payanlint FILE.docx`: lint a Persian thesis for typing conventions (P1xx: Arabic ي/ك, three digit sets, half-space before/after می / ها, punctuation, quotes, tatweel) and for Word formatting (F2xx-F6xx: Persian font/size/bold slots, line spacing, margins per section, page numbering, headings, captions, empty paragraphs).
- Each finding shows the line as typed, the line after the fix, why, and the Word-side fix; `--body-font`, `--body-size`, `--line`, `--margins` compare with your university's guide.
- `--fix`: writes a **copy** with only the safe text fixes (works across run boundaries, never edits SEQ/PAGE field results, every other part of the file stays byte-identical); the copy is re-linted and the remainder is reported.
- `--digits fa|en`, `--skip CATEGORIES`, `--json`, `--strict`, `--demo`, `--make-sample`; `.txt`/`.md` input gets the typing rules only.
