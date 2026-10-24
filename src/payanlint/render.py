from __future__ import annotations

import json
import os
from typing import Dict, List

from . import __version__
from .checks import Finding, summarize

C = {"error": "\x1b[31m", "warn": "\x1b[33m", "info": "\x1b[36m", "dim": "\x1b[2m", "b": "\x1b[1m", "0": "\x1b[0m"}
SIGN = {"error": "✗", "warn": "!", "info": "·"}
FA = "۰۱۲۳۴۵۶۷۸۹"


def iso(s: str) -> str:
    """Terminals re-order RTL text themselves; fence quoted samples with LRI…PDI so the line layout stays stable."""
    return "\u2066" + s + "\u2069"


def _profile(pf: Dict[str, object]) -> str:
    d = pf.get("digits") or {}
    bits = []
    if pf.get("persian_font"):
        bits.append(f"Persian body: {pf['persian_font']} {pf['persian_size_pt']:g} pt" if pf.get("persian_size_pt") else f"Persian body: {pf['persian_font']}")
    if pf.get("latin_font"):
        bits.append(f"Latin: {pf['latin_font']} {pf['latin_size_pt']:g} pt" if pf.get("latin_size_pt") else f"Latin: {pf['latin_font']}")
    if pf.get("line"):
        bits.append(f"line {pf['line']:g}×")
    if pf.get("alignment"):
        bits.append({"both": "justified"}.get(str(pf["alignment"]), str(pf["alignment"])))
    dg = []
    for k, label in (("fa", "Persian"), ("en", "Latin"), ("ar", "Arabic-Indic")):
        if d.get(k):
            dg.append(f"{label} {d[k]}")
    if dg:
        bits.append("digits: " + ", ".join(dg))
    return " · ".join(bits)


def text(doc, findings: List[Finding], color: bool = False, fixed: str = "") -> str:
    def c(k, s):
        return f"{C[k]}{s}{C['0']}" if color else s
    sm = summarize(doc, findings)
    out = [f"payanlint {__version__} · {os.path.basename(doc.path)} · {sm['paragraphs']} paragraphs ({sm['persian_paragraphs']} Persian), {sm['tables']} tables, {sm['sections']} sections"]
    pr = _profile(sm["profile"]) if doc.kind == "docx" else ""
    if pr:
        out.append(c("dim", "profile: " + pr))
    out.append("")
    if not findings:
        out.append("✓ nothing found by these rules.")
    for f in findings:
        n = f"{f.count}×" if f.count > 1 else ""
        loc = f.where or ("  ".join(f"¶{p}" for p in f.paragraphs[:6]) + (" …" if len(f.paragraphs) > 6 or f.count > len(f.paragraphs) and f.paragraphs else ""))
        tag = f.where if f.where else ((n + " ") if n else "") + loc
        out.append(f"{c(f.severity, SIGN[f.severity])} {f.code} {f.title}   [{tag}]".rstrip())
        for e in f.examples:
            line = f"    {e.get('where', ''):>5}  {iso(e['before'])}"
            if e.get("after"):
                line += "  →  " + iso(e["after"])
            out.append(line)
        out.append(f"    why : {f.why}")
        out.append(f"    fix : {f.fix}")
        out.append("")
    out.append(f"{sm['errors']} error(s), {sm['warnings']} warning(s), {sm['info']} note(s); {sm['fixable']} text edit(s) fixable with --fix.")
    na = sm["not_analysed"]
    if na:
        out.append("not analysed: " + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in na.items()))
    out.append("These are heuristics, not your university's rulebook; ⸱ marks a half-space (ZWNJ) in the examples above. Open the file in Word to confirm.")
    if fixed:
        out.append(fixed)
    return "\n".join(out) + "\n"


def as_json(doc, findings: List[Finding]) -> str:
    return json.dumps({"tool": "payanlint", "version": __version__, "file": os.path.basename(doc.path),
                       "summary": summarize(doc, findings), "findings": [f.to_dict() for f in findings]},
                      ensure_ascii=False, indent=2)
