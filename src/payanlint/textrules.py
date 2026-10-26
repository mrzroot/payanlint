"""Persian typing conventions as small, explainable rules over one paragraph's text.

``scan(T)`` returns Fix objects (start, end, replacement). The checker reports them, the fixer applies the
ones that are safe to apply automatically. Every rule is conservative: when a case could be legitimate
(Arabic quotations, Latin abbreviations, ratios, citations) it is left alone.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Set

ZWNJ = "\u200c"
PL = "\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC"       # Persian/Arabic-script letters
NONJOIN = "اآأإدذرزژوؤء"                                                     # letters that never join to the next one
FA_DIG, AR_DIG = "۰۱۲۳۴۵۶۷۸۹", "٠١٢٣٤٥٦٧٨٩"
TO_FA = {**{a: f for a, f in zip("0123456789", FA_DIG)}, **{a: f for a, f in zip(AR_DIG, FA_DIG)}}
TO_EN = {**{f: a for a, f in zip("0123456789", FA_DIG)}, **{ar: a for a, ar in zip("0123456789", AR_DIG)}}
HARAKAT = re.compile("[\u064B-\u065F\u0670]")
STOP_AFTER_MI = {"از", "را", "به", "در", "که", "با", "تا", "بر", "یا", "هم", "و", "این", "آن", "ها", "های"}

CATEGORIES = ("arabic-letters", "arabic-digits", "digits", "zwnj", "punct", "spaces", "quotes", "tatweel")


@dataclass
class Fix:
    code: str
    cat: str
    start: int
    end: int
    repl: str
    msg: str
    auto: bool = True


def _letters(text: str):
    r = l = 0
    for ch in text:
        if ch.isalpha():
            c = unicodedata.bidirectional(ch)
            if c in ("R", "AL"):
                r += 1
            elif c == "L":
                l += 1
    return r, l


def is_persian(text: str) -> bool:
    r, l = _letters(text)
    return r >= 3 and r >= l


def digit_context(T: str) -> List[tuple]:
    """(start, end, kind, in_latin_context) for every run of digits; kind is 'fa', 'en' or 'ar'."""
    toks = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", T)]
    where = {}
    for k, (a, b, t) in enumerate(toks):
        latin = bool(re.search("[A-Za-z]", t))
        if not latin and re.fullmatch(r"[\W\d_]*", t) and k > 0:
            pt = toks[k - 1][2]
            if re.search("[A-Za-z]", pt) and not re.search(f"[{PL}]", pt):
                latin = True
        where[k] = latin
    out = []
    for k, (a, b, t) in enumerate(toks):
        for m in re.finditer(r"[0-9]+|[۰-۹]+|[٠-٩]+", t):
            ch = m.group(0)[0]
            kind = "en" if ch in "0123456789" else ("fa" if ch in FA_DIG else "ar")
            out.append((a + m.start(), a + m.end(), kind, where[k]))
    return out


def digit_counts(T: str) -> Dict[str, int]:
    c = {"fa": 0, "en": 0, "ar": 0, "en_latin_ctx": 0}
    for _a, _b, kind, latin in digit_context(T):
        if kind == "en" and latin:
            c["en_latin_ctx"] += 1
        else:
            c[kind] += 1
    return c


def _skip_arabic_text(T: str) -> bool:
    return bool(HARAKAT.search(T))     # vocalised (Quranic / Arabic) text: leave letters alone


def scan(T: str, digits: str = "keep", persian: Optional[bool] = None) -> List[Fix]:
    if persian is None:
        persian = is_persian(T)
    if not persian:
        return []
    fx: List[Fix] = []
    add = lambda *a, **k: fx.append(Fix(*a, **k))

    # --- Arabic letters
    if not _skip_arabic_text(T):
        for m in re.finditer("[يىك]", T):
            add("P101", "arabic-letters", m.start(), m.end(), "ک" if m.group(0) == "ك" else "ی", f"Arabic «{m.group(0)}» → Persian")
    # --- digits
    for a, b, kind, latin in digit_context(T):
        s = T[a:b]
        if kind == "ar":
            if digits == "en":
                add("P102", "arabic-digits", a, b, "".join(TO_EN[c] for c in s), "Arabic-Indic digits → Latin")
            else:
                add("P102", "arabic-digits", a, b, "".join(TO_FA[c] for c in s), "Arabic-Indic digits → Persian digits")
        elif kind == "en" and not latin and digits == "fa":
            add("P103", "digits", a, b, "".join(TO_FA[c] for c in s), "Latin digits in Persian text → Persian digits", True)
        elif kind == "fa" and not latin and digits == "en":
            add("P103", "digits", a, b, "".join(TO_EN[c] for c in s), "Persian digits → Latin digits", True)
    # --- ZWNJ
    for m in re.finditer(rf"(?<![{PL}{ZWNJ}])(نمی|می) (?=([{PL}]{{2,}}))", T):
        nxt = re.match(f"[{PL}]+", T[m.end():]).group(0)
        if nxt in STOP_AFTER_MI:
            continue
        add("P110", "zwnj", m.end() - 1, m.end(), ZWNJ, f"«{m.group(1)} …» needs a half-space")
    for m in re.finditer(rf"(?<=[{PL}]) (ها|های|هایی|هایم|هایت|هایش|هایمان|هایتان|هایشان)(?![{PL}])", T):
        prev = T[m.start() - 1]
        add("P111", "zwnj", m.start(), m.start() + 1, "" if prev in NONJOIN else ZWNJ,
            f"plural «{m.group(1)}» is written attached" + ("" if prev in NONJOIN else " with a half-space"))
    for m in re.finditer(f"{ZWNJ}+", T):
        a, b = m.span()
        edge = a == 0 or T[a - 1].isspace() or b >= len(T) or T[b].isspace()
        if edge:
            add("P112", "zwnj", a, b, "", "stray half-space at a word edge")
        elif b - a > 1:
            add("P112", "zwnj", a, b, ZWNJ, "doubled half-space")
    for m in re.finditer("\u0640+", T):
        add("P113", "tatweel", m.start(), m.end(), "", "tatweel (kashida) inside text")
    # --- punctuation
    for m in re.finditer(rf"(?<=[{PL}۰-۹]) +(?=[،؛؟!»)\]])|(?<=[{PL}]) +(?=[:.](?:\s|$))", T):
        add("P120", "punct", m.start(), m.end(), "", "space before punctuation")
    for m in re.finditer(rf"(?<=[{PL}])[،؛؟!:](?=[{PL}])|(?<=[{PL}۰-۹])[،؛؟!](?=[0-9A-Za-z۰-۹])", T):
        if T[m.start() - 1] in FA_DIG and T[m.end()] in FA_DIG:
            continue
        add("P121", "punct", m.end(), m.end(), " ", "missing space after punctuation")
    for m in re.finditer(rf"(?<=[{PL}]{{2}})\.(?=[{PL}]{{2}})", T):
        add("P121", "punct", m.end(), m.end(), " ", "missing space after full stop")
    for m in re.finditer(rf"(?<=[{PL}]),(?=\s*[{PL}])|(?<=[{PL}]);(?=\s|$)|(?<=[{PL}])\?(?=\s|$)", T):
        add("P122", "punct", m.start(), m.end(), {",": "،", ";": "؛", "?": "؟"}[m.group(0)], "Latin punctuation inside Persian text")
    for m in re.finditer(rf"(?<=\() +(?=[{PL}۰-۹])|(?<=[{PL}۰-۹]) +(?=\))|(?<=«) +(?=[{PL}])|(?<=[{PL}۰-۹.،؟!]) +(?=»)", T):
        add("P123", "punct", m.start(), m.end(), "", "space just inside brackets/quotes")
    # --- spaces
    for m in re.finditer(r"(?<=\S)[ ]{2,}(?=\S)", T):
        add("P124", "spaces", m.start(), m.end(), " ", "several spaces in a row")
    m = re.search(r"[ \t]+$", T)
    if m and m.start() > 0:
        add("P124", "spaces", m.start(), m.end(), "", "trailing spaces")
    m = re.match(r"([ \t\u00a0]{2,}|\t)", T)
    if m:
        add("P125", "spaces", m.start(), m.end(), "", "paragraph indented with spaces/tabs (use a first-line indent)", auto=False)
    # --- quotes
    for m in re.finditer(rf'"(?=\S)([^"\n]{{2,}}?)(?<=\S)"', T):
        if re.search(f"[{PL}]", m.group(1)):
            add("P126", "quotes", m.start(), m.start() + 1, "«", "straight quote around Persian text")
            add("P126", "quotes", m.end() - 1, m.end(), "»", "straight quote around Persian text")
    # resolve overlaps (earlier start wins)
    fx.sort(key=lambda f: (f.start, f.end))
    out: List[Fix] = []
    last = -1
    for f in fx:
        if f.start < last:
            continue
        out.append(f)
        last = max(last, f.end, f.start)
    return out


def apply(T: str, fixes: Iterable[Fix]) -> str:
    out, pos = [], 0
    for f in sorted(fixes, key=lambda f: (f.start, f.end)):
        out.append(T[pos:f.start])
        out.append(f.repl)
        pos = f.end
    out.append(T[pos:])
    return "".join(out)
