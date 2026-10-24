from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Optional

from . import __version__, checks, render, textrules
from .docxio import load


def _margins(s: str) -> Dict[str, float]:
    out = {}
    for part in s.split(","):
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if k not in ("top", "bottom", "left", "right") or not v:
            raise argparse.ArgumentTypeError("use --margins top=3.5,bottom=3,right=3.5,left=2.5 (cm)")
        out[k] = float(v)
    return out


def _fix_text_file(src: str, dst: str, digits: str, skip) -> int:
    raw = open(src, encoding="utf-8").read()
    cats = set(("arabic-letters", "arabic-digits", "zwnj", "punct", "spaces", "quotes", "tatweel", "digits")) - set(skip)
    n, out = 0, []
    for line in raw.split("\n"):
        for _ in range(4):
            fx = [f for f in textrules.scan(line, digits=digits) if f.auto and f.cat in cats]
            if not fx:
                break
            line = textrules.apply(line, fx)
            n += len(fx)
        out.append(line)
    open(dst, "w", encoding="utf-8").write("\n".join(out))
    return n


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="payanlint", description=(
        "Lint a Persian thesis (.docx) for Persian typing rules (half-space, ي/ك, digits, punctuation) and Persian-specific Word "
        "formatting (complex-script font and size, bold, page-number letters, captions). Offline; never edits your file."))
    ap.add_argument("file", nargs="?", help=".docx (or .txt/.md: typing rules only)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too (default: only on errors)")
    ap.add_argument("--fix", action="store_true", help="write a fixed COPY with the safe text fixes (never overwrites the input)")
    ap.add_argument("--digits", choices=["keep", "fa", "en"], default="keep", help="digit policy: fa = Persian digits in Persian text, en = Latin (default: keep; only Arabic-Indic digits are always fixed)")
    ap.add_argument("--skip", default="", help="with --fix: comma-separated categories not to touch: " + ",".join(textrules.CATEGORIES))
    ap.add_argument("-o", "--output", help="path of the fixed copy (default: <name>.payanlint.<ext>)")
    ap.add_argument("--body-font", help="expected complex-script font of Persian body text, e.g. \"B Nazanin\"")
    ap.add_argument("--body-size", type=float, help="expected size of Persian body text in points, e.g. 14")
    ap.add_argument("--line", type=float, help="expected body line spacing as a multiple, e.g. 1.5")
    ap.add_argument("--margins", type=_margins, help="expected margins in cm: top=3.5,bottom=3,right=3.5,left=2.5")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--demo", action="store_true", help="offline: generate a sample thesis chapter and lint it")
    ap.add_argument("--make-sample", metavar="PATH", help="write the synthetic demo chapter (.docx) to PATH and exit (with --clean: the clean version)")
    ap.add_argument("--clean", action="store_true", help="with --make-sample: write the clean version")
    ap.add_argument("--version", action="version", version=f"payanlint {__version__}")
    a = ap.parse_args(argv)
    skip = [x.strip() for x in a.skip.split(",") if x.strip()]
    bad_skip = [x for x in skip if x not in textrules.CATEGORIES]
    if bad_skip:
        ap.error("unknown category: " + ", ".join(bad_skip))
    if a.demo:
        if a.fix:
            ap.error("--fix needs your own file; use --make-sample PATH to get a sample .docx and fix that")
        import tempfile
        from . import sample
        with tempfile.TemporaryDirectory() as td:
            a.demo = False
            a.file = sample.thesis(os.path.join(td, "chapter2.docx"))
            return main([a.file] + [x for x in (argv if argv is not None else sys.argv[1:]) if x != "--demo"])
    if a.make_sample:
        from . import sample
        print(sample.thesis(a.make_sample, flawed=not a.clean))
        return 0
    if not a.file:
        ap.error("give a .docx file (or use --demo)")
    if not os.path.exists(a.file):
        print(f"payanlint: no such file: {a.file}", file=sys.stderr)
        return 2
    try:
        doc = load(a.file)
    except Exception as e:
        print(f"payanlint: cannot read {a.file}: {e}", file=sys.stderr)
        return 2
    opt = checks.Options(body_font=a.body_font, body_size=a.body_size, line=a.line, margins=a.margins, digits=a.digits)
    findings = checks.analyse(doc, opt)
    extra = ""
    if a.fix:
        ext = os.path.splitext(a.file)[1]
        dst = a.output or os.path.splitext(a.file)[0] + ".payanlint" + ext
        if os.path.abspath(dst) == os.path.abspath(a.file):
            print("payanlint: refusing to overwrite the input file", file=sys.stderr)
            return 2
        if doc.kind == "docx":
            from . import fixer
            st = fixer.fix_docx(a.file, dst, digits=a.digits, skip=skip)
            extra = f"fixed copy: {dst}  (edits: " + (", ".join(f"{k} {v}" for k, v in sorted(st.items())) or "none") + "). Fonts, sizes, captions and page setup are never changed automatically."
        else:
            n = _fix_text_file(a.file, dst, a.digits, skip)
            extra = f"fixed copy: {dst}  ({n} edits)"
        after = checks.analyse(load(dst), opt)
        extra += f"\nre-check of the copy: {sum(1 for f in after if f.severity == 'error')} error(s), {sum(1 for f in after if f.severity == 'warn')} warning(s), {sum(1 for f in after if f.severity == 'info')} note(s) left."
    sys.stdout.write((render.as_json(doc, findings) + "\n") if a.json else render.text(doc, findings, color=sys.stdout.isatty() and not a.no_color, fixed=extra))
    bad = sum(1 for f in findings if f.severity == "error") + (sum(1 for f in findings if f.severity == "warn") if a.strict else 0)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
