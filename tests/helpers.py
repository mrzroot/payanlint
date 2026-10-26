"""Shared helpers for the payanlint tests: build tiny .docx files and list the finding codes they raise."""
from payanlint import checks
from payanlint.checks import Options
from payanlint.docxbuild import Doc
from payanlint.docxio import read_docx

ZW = "\u200c"  # zero-width non-joiner (the Persian half-space)

# A paragraph long enough to count as body text (short lines are treated as headings or captions).
BODY = "این یک بند نمونه برای آزمون است و باید به‌اندازه‌ی کافی بلند باشد تا بدنه حساب شود."


def codes(path, **options):
    """Return the set of finding codes payanlint reports for the .docx at *path*."""
    return {f.code for f in checks.analyse(read_docx(path), Options(**options))}


def mini(tmp_path, build, name="m.docx"):
    """Build a one-off document: call ``build(doc)`` to fill it, save it under *tmp_path*, return the path."""
    doc = Doc()
    doc.add_footer()  # a page-number footer, so F303 does not fire in tests about something else
    build(doc)
    return doc.save(str(tmp_path / name))
