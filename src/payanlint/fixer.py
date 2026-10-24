"""Write a fixed copy of a .docx. Only the text inside <w:t> is edited (and only the safe categories);
styles, fields (page numbers, SEQ results), headers/footers and every other part are copied byte for byte."""
from __future__ import annotations

import zipfile
from collections import Counter
from typing import Dict, Iterable, Optional

from . import textrules as tr
from .docxedit import edit_paragraph, paragraph_spans
from .docxio import read_docx

DEFAULT_CATS = ("arabic-letters", "arabic-digits", "zwnj", "punct", "spaces", "quotes", "tatweel", "digits")


def fix_docx(src: str, dst: str, digits: str = "keep", skip: Iterable[str] = ()) -> Dict[str, int]:
    cats = set(DEFAULT_CATS) - set(skip)
    doc = read_docx(src)
    zin = zipfile.ZipFile(src)
    xml = zin.read("word/document.xml").decode("utf-8")
    spans = paragraph_spans(xml)
    if len(spans) != len(doc.paragraphs):
        raise RuntimeError(f"internal check failed: {len(spans)} paragraphs in XML vs {len(doc.paragraphs)} parsed; refusing to edit")
    stats: Counter = Counter()
    out, last = [], 0
    for idx, (a, b) in enumerate(spans):
        p = xml[a:b]
        if doc.paragraphs[idx].is_toc:
            out.append(xml[last:b])
            last = b
            continue
        for _ in range(4):
            seen: Counter = Counter()

            def plan(T, protected):
                dels, ins = set(), {}
                for f in tr.scan(T, digits=digits):
                    if not f.auto or f.cat not in cats:
                        continue
                    rng = range(f.start, f.end) if f.end > f.start else [f.start]
                    if any(i in protected for i in rng):
                        continue
                    dels.update(range(f.start, f.end))
                    if f.repl:
                        ins[f.start] = ins.get(f.start, "") + f.repl
                    seen[f.cat] += 1
                return dels, ins
            new = edit_paragraph(p, plan)
            if new == p:
                break
            p = new
            stats.update(seen)
        out.append(xml[last:a])
        out.append(p)
        last = b
    out.append(xml[last:])
    xml2 = "".join(out)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = xml2.encode("utf-8")
            zout.writestr(item, data)
    return dict(stats)
