"""payanlint checks: Persian typing rules (text) and Persian-specific Word formatting (complex-script slots, page numbers, captions)."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from . import textrules as tr
from .docxio import Document, Paragraph

SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}
DIG = "0-9۰-۹٠-٩"
CAP_LABELS = "شکل|جدول|نمودار|تصویر|عکس|Figure|Fig\\.?|Table"
CAP_RE = re.compile(rf"^\s*({CAP_LABELS})\s*([{DIG}]+)(?:\s*([-–.:/‑])\s*([{DIG}]+))?\s*(?:[:：\-–]|\s)\s*\S", re.I)
ABJAD = ("arabicAbjad", "arabicAlpha", "hebrew1", "hebrew2", "thaiLetters", "hindiConsonants")   # lettered formats
SKIP_STYLE = ("caption", "title", "heading", "toc", "header", "footer", "footnote", "endnote", "table of")


@dataclass
class Options:
    body_font: Optional[str] = None       # complex-script font expected for Persian body text
    body_size: Optional[float] = None     # points
    line: Optional[float] = None          # line spacing multiple (1.5)
    margins: Optional[Dict[str, float]] = None   # cm: top bottom left right
    digits: str = "keep"                  # keep | fa | en  (what the fixer will do; also what P103 compares against)


@dataclass
class Finding:
    code: str
    severity: str
    title: str
    why: str
    fix: str
    count: int = 1
    paragraphs: List[int] = field(default_factory=list)        # 1-based, capped
    examples: List[Dict[str, str]] = field(default_factory=list)
    fixable: bool = False
    cat: str = ""
    where: str = ""

    def to_dict(self):
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, [], "")}


def snip(t: str, a: int = 0, b: Optional[int] = None, w: int = 22) -> str:
    b = a if b is None else b
    s = t[max(0, a - w):a] + "⟦" + t[a:b] + "⟧" + t[b:b + w]
    return s.replace("\n", " ").replace("\t", "⇥")


def _zw(s: str) -> str:
    """Make half-spaces visible in reports: «کتاب‌ها» → «کتاب⸱ها» (the dot is only a marker)."""
    return s.replace(tr.ZWNJ, "⸱")


def is_body(p: Paragraph) -> bool:
    if p.in_table or p.heading_level or p.is_toc or p.has_drawing or p.list_level is not None:
        return False
    sn = (p.style_name or p.style_id or "").lower()
    if sn.startswith(SKIP_STYLE):
        return False
    return tr.is_persian(p.text) and len(p.text) >= 40


def persian_runs(p: Paragraph):
    return [r for r in p.runs if r.has_cs_chars and re.search(f"[{tr.PL}]", r.text)]


def latin_runs(p: Paragraph):
    return [r for r in p.runs if len(re.findall("[A-Za-z]", r.text)) >= 3]


def _mode(c: Counter):
    return c.most_common(1)[0][0] if c else None


def where(p: Paragraph) -> str:
    return f"¶{p.idx + 1}"


def profile(doc: Document) -> Dict[str, object]:
    body = [p for p in doc.paragraphs if is_body(p)]
    cs, szcs, lat, latsz, line, jc, digs = Counter(), Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    for p in body:
        for r in persian_runs(p):
            n = len(r.text)
            cs[r.rpr.get("cs_font")] += n
            szcs[r.rpr.get("szcs")] += n
        for r in latin_runs(p):
            lat[r.rpr.get("ascii_font")] += len(r.text)
            latsz[r.rpr.get("sz")] += len(r.text)
        line[(p.line, p.line_rule)] += len(p.text)
        jc[p.jc] += len(p.text)
    for p in doc.paragraphs:
        if tr.is_persian(p.text):
            for k, v in tr.digit_counts(p.text).items():
                digs[k] += v
    return {"body_paragraphs": len(body), "cs_font": _mode(cs), "cs_fonts": {str(k): v for k, v in cs.most_common()},
            "szcs": _mode(szcs), "latin_font": _mode(lat), "latin_sz": _mode(latsz), "line": _mode(line), "jc": _mode(jc),
            "digits": dict(digs), "_body": body, "_cs": cs, "_szcs": szcs, "_line": line, "_jc": jc}


def _fmt_pt(hp) -> str:
    return "?" if hp is None else (f"{hp / 2:g} pt")


def analyse(doc: Document, opt: Optional[Options] = None) -> List[Finding]:
    opt = opt or Options()
    out: List[Finding] = []
    P = doc.paragraphs
    prof = profile(doc)

    # ------------------------------------------------------------------ text rules
    groups: Dict[str, Finding] = {}
    PARAS: Dict[str, set] = {}
    META = {
        "P101": ("error", "Arabic ي / ك / ى used instead of Persian ی / ک", "Arabic and Persian letters look alike but are different characters: search, sorting, the TOC index and plagiarism checkers treat them differently, and most universities reject them.", "payanlint --fix replaces them (letters only; vocalised Arabic text is skipped)."),
        "P102": ("warn", "Arabic-Indic digits (٤٥٦ …) in Persian text", "These are a third digit set. ٤ ٥ ٦ differ in shape from Persian ۴ ۵ ۶, so a reader sees a mix.", "payanlint --fix converts them to Persian digits."),
        "P103": ("warn", "Latin digits in Persian text while the document uses Persian digits", "A digit set should be one choice for the whole thesis. This is a policy (Persian text → Persian digits; Latin digits stay in Latin words and citations).", "Choose with --digits fa or --digits en; payanlint then converts only digits in Persian context."),
        "P110": ("warn", "«می / نمی» + space (needs a half-space)", "In Persian orthography the verb prefix is attached with a half-space (ZWNJ): «می‌شود», not «می شود».", "payanlint --fix inserts the half-space (by hand: Insert → Symbol → Special Characters → Zero Width Non-Joiner)."),
        "P111": ("warn", "plural «ها / های» separated by a space", "The plural suffix is written attached, with a half-space after letters that join: «کتاب‌ها», and with no gap after non-joining letters: «دانشجوها».", "payanlint --fix attaches it."),
        "P112": ("info", "stray half-space (ZWNJ) at a word edge or doubled", "Invisible, but breaks search and line breaking.", "payanlint --fix removes it."),
        "P113": ("info", "tatweel (ـ) inside words", "Kashida stretches letters on screen only; the text is changed for search and copy.", "payanlint --fix removes it."),
        "P120": ("warn", "space before «، ؛ ؟ ! : . » ) ]»", "Persian punctuation sticks to the previous word.", "payanlint --fix removes the space."),
        "P121": ("warn", "no space after «، ؛ ؟ ! : .»", "A space follows the mark, never precedes it.", "payanlint --fix inserts it."),
        "P122": ("warn", "Latin , ; ? inside Persian text", "Persian text uses «، ؛ ؟».", "payanlint --fix converts them."),
        "P123": ("info", "space just inside ( ) or « »", "Brackets hug their content: «(متن)».", "payanlint --fix removes the space."),
        "P124": ("info", "several spaces in a row / trailing spaces", "Use paragraph spacing, not repeated spaces.", "payanlint --fix collapses them."),
        "P125": ("info", "paragraph indented with spaces or a tab", "Indents made of spaces move when the font changes; use a first-line indent in the paragraph style.", "Set the indent in the paragraph style (not auto-fixed)."),
        "P126": ("info", 'straight quotes " " around Persian text', "Persian typography uses «guillemets».", "payanlint --fix converts matching pairs."),
    }
    ex_cap = 3
    for p in P:
        T = p.text
        if not tr.is_persian(T) or p.is_toc:
            continue
        has_seq = any(f.strip().upper().startswith("SEQ") for f in p.fields)
        scanned = tr.scan(T, digits=opt.digits, persian=True)
        for fx in scanned:
            if has_seq and fx.code == "P103":
                continue                      # SEQ results are regenerated by Word; see F502
            sev, title, why, fixtxt = META[fx.code]
            g = groups.get(fx.code)
            if g is None:
                g = groups[fx.code] = Finding(fx.code, sev, title, why, fixtxt, count=0, fixable=fx.auto, cat=fx.cat)
                PARAS[fx.code] = set()
            g.count += 1
            first = p.idx + 1 not in PARAS[fx.code]
            if first:
                PARAS[fx.code].add(p.idx + 1)
                if len(g.paragraphs) < 30:
                    g.paragraphs.append(p.idx + 1)
            if first and len(g.examples) < ex_cap:
                a, b = fx.start, fx.end
                lo, hi = max(0, a - 22), b + 22
                near = [tr.Fix(x.code, x.cat, x.start - lo, x.end - lo, x.repl, "") for x in scanned if x.code == fx.code and x.start >= lo and x.end <= hi]
                g.examples.append({"where": where(p), "before": _zw(snip(T, a, b)), "after": _zw(tr.apply(T[lo:hi], near))})
    # P103: also warn about mixing when no policy chosen
    dc = prof["digits"]
    if opt.digits == "keep":
        fa, en = dc.get("fa", 0), dc.get("en", 0)
        if fa and en:
            f = Finding("P103", "warn", "document mixes Persian and Latin digits in Persian context",
                        "A digit set should be one choice for the whole thesis. This is a policy: payanlint does not guess it.",
                        "Choose with --digits fa or --digits en; Latin digits inside Latin words, citations and SEQ field results are left alone.",
                        count=en, fixable=False, cat="digits")
            ex = []
            for p in P:
                if tr.is_persian(p.text) and not p.is_toc:
                    for a, b, kind, latin in tr.digit_context(p.text):
                        if kind == "en" and not latin:
                            ex.append({"where": where(p), "before": _zw(snip(p.text, a, b)), "after": ""})
                            if len(f.paragraphs) < 30 and p.idx + 1 not in f.paragraphs:
                                f.paragraphs.append(p.idx + 1)
                            break
            f.examples = ex[:3]
            f.where = f"Persian digits {fa}×, Latin digits in Persian context {en}×"
            f.count = 1
            groups["P103"] = f
    out.extend(groups.values())
    if doc.kind != "docx":                      # .txt/.md: typing rules only, no Word formatting to inspect
        out.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.code))
        return out

    # ------------------------------------------------------------------ fonts / sizes (complex-script slots)
    body = prof["_body"]
    exp_font = (opt.body_font or prof["cs_font"] or "").strip()
    if body:
        missing = [p for p in body if any(not r.rpr.get("cs_font") for r in persian_runs(p))]
        if missing:
            out.append(Finding("F201", "error", "Persian text without a complex-script font (w:cs)",
                               "Word draws Persian letters with the complex-script font slot, not the Latin one. Without it, Persian text falls back to the theme/default font.",
                               "Set the font for Persian text in the Normal style (Font dialog → «Complex scripts»).",
                               count=len(missing), paragraphs=[p.idx + 1 for p in missing][:30],
                               examples=[{"where": where(p), "before": _zw(p.text[:50]), "after": ""} for p in missing[:3]]))
        if opt.body_font and prof["cs_font"] and prof["cs_font"].lower() != opt.body_font.lower():
            out.append(Finding("F202", "warn", f"body Persian font is «{prof['cs_font']}», expected «{opt.body_font}»",
                               "The expected font was given with --body-font.", "Change the complex-script font of the Normal style.",
                               where=", ".join(f"{k} {v} chars" for k, v in list(prof["cs_fonts"].items())[:4])))
        minority = [p for p in body if any(r.rpr.get("cs_font") and exp_font and r.rpr.get("cs_font").lower() != exp_font.lower() for r in persian_runs(p))]
        if exp_font and minority:
            out.append(Finding("F203", "warn", f"Persian body text in more than one font (not «{exp_font}»)",
                               "Direct formatting from pasted text or an old template. Different Persian fonts in running text are the most visible sign of a patched thesis.",
                               "Select the paragraphs and re-apply the Normal style (Ctrl+Shift+N, then Ctrl+Space).",
                               count=len(minority), paragraphs=[p.idx + 1 for p in minority][:30],
                               examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": "font: " + ", ".join(sorted({r.rpr.get('cs_font') or '-' for r in persian_runs(p)}))} for p in minority[:3]]))
        # sizes
        exp_hp = int(round(opt.body_size * 2)) if opt.body_size else prof["szcs"]
        nosz = [p for p in body if any(r.rpr.get("szcs") is None for r in persian_runs(p))]
        if nosz:
            out.append(Finding("F204", "warn", "Persian text without a complex-script size (w:szCs)",
                               "Persian text takes its size from szCs, not sz. When only the Latin size is set, the size you see in the ribbon is not the size of the Persian text.",
                               "Set the size in the Normal style; in Word the ribbon changes both only when the whole paragraph is selected.",
                               count=len(nosz), paragraphs=[p.idx + 1 for p in nosz][:30]))
        if opt.body_size and prof["szcs"] and prof["szcs"] != exp_hp:
            out.append(Finding("F205", "warn", f"Persian body size is {_fmt_pt(prof['szcs'])}, expected {opt.body_size:g} pt",
                               "The expected size was given with --body-size.", "Change the size of the Normal style (complex scripts).", where="szCs"))
        diff = [p for p in body if any(r.rpr.get("szcs") not in (None, exp_hp) for r in persian_runs(p))]
        if diff:
            out.append(Finding("F206", "warn", f"Persian body paragraphs not at {_fmt_pt(exp_hp)}",
                               "Pasted text keeps its own size; the thesis looks uneven although every paragraph «looks» 14 on the Latin side.",
                               "Re-apply the Normal style to these paragraphs.", count=len(diff), paragraphs=[p.idx + 1 for p in diff][:30],
                               examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": "size: " + ", ".join(sorted({_fmt_pt(r.rpr.get('szcs')) for r in persian_runs(p)}))} for p in diff[:3]]))
        # bold slots
        bad_b = [p for p in P if (p.heading_level or not p.in_table) and any(r.rpr.get("bold") and not r.rpr.get("bold_cs") for r in persian_runs(p))]
        if bad_b:
            out.append(Finding("F207", "warn", "bold set for Latin only (w:b without w:bCs): Persian text stays regular",
                               "Word keeps bold for Persian in its own slot (bCs). A run with only w:b looks bold on the Latin side and plain on the Persian side.",
                               "Select the text again and press Ctrl+B once; or set Bold in the style.", count=len(bad_b),
                               paragraphs=[p.idx + 1 for p in bad_b][:30],
                               examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": ""} for p in bad_b[:3]]))
        bad_l = [p for p in body if any(r.rpr.get("bold_cs") and not r.rpr.get("bold") for r in persian_runs(p))]
        if bad_l:
            out.append(Finding("F208", "info", "bold set for Persian only (w:bCs without w:b)",
                               "Latin words next to it stay regular.", "Re-apply bold to the whole selection.", count=len(bad_l),
                               paragraphs=[p.idx + 1 for p in bad_l][:30]))
        # language
        nolang = [p for p in body if any(not str(r.rpr.get("lang_bidi") or doc.default_lang_bidi or "").lower().startswith("fa") for r in persian_runs(p))]
        if nolang:
            ex = Counter(str(r.rpr.get("lang_bidi") or doc.default_lang_bidi or "none") for p in nolang for r in persian_runs(p))
            out.append(Finding("F209", "info", "proofing language of Persian text is not fa-IR",
                               "Word then spell-checks Persian words as Arabic or English (red squiggles) and hyphenates by the wrong rules.",
                               "Review → Language → set «Persian» for the Normal style.", count=len(nolang),
                               paragraphs=[p.idx + 1 for p in nolang][:30], where=f"{len(nolang)} paragraphs: " + ", ".join(f"{k} ×{v}" for k, v in ex.most_common(3))))
        # line spacing and alignment
        def ln(k):
            return "auto" if k[0] is None else (f"{k[0] / 240:g}× " + (k[1] or "auto") if (k[1] in (None, "auto")) else f"{k[0] / 20:g} pt {k[1]}")
        mode_line = prof["line"]
        if opt.line and mode_line and (mode_line[0] is None or abs(mode_line[0] / 240 - opt.line) > 0.02 or mode_line[1] not in (None, "auto")):
            out.append(Finding("F210", "warn", f"body line spacing is {ln(mode_line)}, expected {opt.line:g}×", "Given with --line.", "Set line spacing in the Normal style.", where="spacing"))
        odd = [p for p in body if (p.line, p.line_rule) != mode_line]
        if odd and mode_line:
            out.append(Finding("F211", "warn", f"line spacing differs from the rest of the body ({ln(mode_line)})", "One-off spacing from pasted text.",
                               "Re-apply the Normal style.", count=len(odd), paragraphs=[p.idx + 1 for p in odd][:30],
                               examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": ln((p.line, p.line_rule))} for p in odd[:3]]))
        mj = prof["jc"]
        oddj = [p for p in body if p.jc != mj]
        if oddj and mj:
            out.append(Finding("F212", "info", f"alignment differs from the rest of the body ({mj})", "Mixed justified/right/left paragraphs.",
                               "Re-apply the Normal style.", count=len(oddj), paragraphs=[p.idx + 1 for p in oddj][:30]))

    # ------------------------------------------------------------------ page setup
    secs = doc.sections
    cm = lambda tw: None if tw is None else tw / 567.0
    if len(secs) > 1:
        shapes = {(s.top, s.bottom, s.left, s.right) for s in secs}
        if len(shapes) > 1:
            out.append(Finding("F301", "warn", "sections have different margins", "Different margins between sections change the text block mid-thesis.",
                               "Layout → Margins; apply to «whole document», or keep the difference deliberate.",
                               count=len(shapes), where="; ".join(f"section {s.index + 1}: top {cm(s.top):.2f} bottom {cm(s.bottom):.2f} left {cm(s.left):.2f} right {cm(s.right):.2f} cm" for s in secs if s.top is not None)))
    if opt.margins:
        bad = []
        for s in secs:
            for k in ("top", "bottom", "left", "right"):
                if k in opt.margins and getattr(s, k) is not None and abs(cm(getattr(s, k)) - opt.margins[k]) > 0.1:
                    bad.append(f"section {s.index + 1} {k} {cm(getattr(s, k)):.2f} cm (expected {opt.margins[k]:g})")
        if bad:
            out.append(Finding("F302", "warn", "margins differ from --margins", "Given with --margins; tolerance 0.1 cm.", "Layout → Margins → Custom.", count=len(bad), where="; ".join(bad[:6])))
    if not any(s.footer_has_page for s in secs):
        out.append(Finding("F303", "warn", "no page number (PAGE field) in any footer", "Nothing numbers the pages.", "Insert → Page Number.", where="footers"))
    if len(secs) >= 2:
        fmts = [s.num_fmt or "decimal" for s in secs]
        if not any(f in ABJAD for f in fmts):
            out.append(Finding("F304", "info", "front-matter pages are not lettered (الف، ب، ج …)",
                               "Many Iranian universities number the preliminary pages with letters and restart at 1 for the body. Word calls this format «Arabic Alphabetical» (arabicAbjad / arabicAlpha). Not every university requires it.",
                               "Section break after the front matter → Insert → Page Number → Format → choose the lettered format; body: Start at 1.",
                               where="formats: " + ", ".join(fmts)))
        for k in range(1, len(secs)):
            if fmts[k - 1] in ABJAD and fmts[k] not in ABJAD and secs[k].num_start is None:
                out.append(Finding("F305", "warn", f"section {k + 1} does not restart page numbers after the lettered front matter",
                                   "The body would continue the count of the front matter.", "Page Number → Format → Start at 1.", where=f"section {k + 1}"))
                break
    # ------------------------------------------------------------------ headings
    prev = 0
    skipped, empty, punct, fake = [], [], [], []
    for p in P:
        if p.heading_level:
            if not p.text.strip():
                empty.append(p)
            elif p.text.strip()[-1] in ".:؛،,":
                punct.append(p)
            if prev and p.heading_level > prev + 1:
                skipped.append(p)
            prev = p.heading_level
        elif (not p.in_table and not p.is_toc and p.text.strip() and len(p.text.strip()) <= 80 and tr.is_persian(p.text)
              and p.style_name in (None, "Normal") and p.runs and all((r.rpr.get("bold") or r.rpr.get("bold_cs")) for r in p.runs if r.text.strip())
              and p.text.strip()[-1] not in ".؟،:؛" and not CAP_RE.match(p.text)):
            fake.append(p)
    if skipped:
        out.append(Finding("F401", "warn", "heading levels skipped (e.g. 1 → 3)", "The TOC and the navigation pane show a gap.", "Use the next level down.",
                           count=len(skipped), paragraphs=[p.idx + 1 for p in skipped][:30], examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": f"level {p.heading_level}"} for p in skipped[:3]]))
    if empty:
        out.append(Finding("F402", "warn", "empty heading paragraph", "It shows up as an empty TOC line.", "Delete it or give it a title.", count=len(empty), paragraphs=[p.idx + 1 for p in empty][:30]))
    if punct:
        out.append(Finding("F403", "info", "heading ends with a period/colon", "Headings in Persian theses do not end with punctuation.", "Remove the trailing mark.", count=len(punct),
                           paragraphs=[p.idx + 1 for p in punct][:30], examples=[{"where": where(p), "before": _zw(p.text[:50]), "after": ""} for p in punct[:3]]))
    if fake:
        out.append(Finding("F404", "info", "bold short line that is not a heading style", "It will not appear in the TOC or navigation pane, and cannot be formatted from one place.",
                           "Apply Heading 1/2/3. (Heuristic: it may be a deliberate label.)", count=len(fake), paragraphs=[p.idx + 1 for p in fake][:30],
                           examples=[{"where": where(p), "before": _zw(p.text[:50]), "after": ""} for p in fake[:3]]))
    # ------------------------------------------------------------------ captions
    caps: List[Tuple[Paragraph, re.Match]] = []
    for p in P:
        if p.in_table or p.is_toc:
            continue
        m = CAP_RE.match(p.text)
        sn = (p.style_name or "").lower()
        if m and (sn.startswith("caption") or (len(p.text) <= 160 and re.match(rf"^\s*(?:{CAP_LABELS})\s*[{DIG}]+(?:\s*[-–.‑/]\s*[{DIG}]+)?\s*(?:[:：]|\s[-–]\s)", p.text, re.I))):
            caps.append((p, m))
    if caps:
        def dset(s):
            return "fa" if re.search("[۰-۹]", s) else ("ar" if re.search("[٠-٩]", s) else "en")
        seps = Counter(m.group(3) for _, m in caps if m.group(3))
        if len(seps) > 1:
            out.append(Finding("F501", "warn", "caption numbers use different separators (" + ", ".join(f"«{k}» ×{v}" for k, v in seps.most_common()) + ")",
                               "«شکل ۲-۱» and «شکل ۲.۱» in one thesis look like two numbering schemes; also, the separator changes the drawn order in RTL (see vazhgun).",
                               "Use one separator in the SEQ field template.", count=sum(seps.values()) - seps.most_common(1)[0][1],
                               paragraphs=[p.idx + 1 for p, m in caps if m.group(3) and m.group(3) != seps.most_common(1)[0][0]][:30]))
        mixed = [p for p, m in caps if len({dset(x) for x in (m.group(2), m.group(4) or "")}) > 1 or dset(m.group(2)) != Counter(dset(mm.group(2)) for _, mm in caps).most_common(1)[0][0]]
        if mixed:
            out.append(Finding("F502", "warn", "caption numbers mix digit sets (typed part vs SEQ field result)",
                               "A SEQ field result is regenerated by Word (F9), so retyping it does not stick; typically the typed chapter number is Persian while the field result is Latin («شکل ۲-1»). payanlint never edits field results.",
                               "Make the typed part match the field result, or the other way round, and use one digit set in the whole caption.",
                               count=len(mixed), paragraphs=[p.idx + 1 for p in mixed][:30],
                               examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": ""} for p in mixed[:3]]))
        labels = Counter(m.group(1).lower() for _, m in caps if m.group(1) in ("شکل", "تصویر", "عکس"))
        if len(labels) > 1:
            out.append(Finding("F503", "info", "figures captioned with different words (" + ", ".join(f"«{k}» ×{v}" for k, v in labels.most_common()) + ")", "One label word per kind of object.", "Pick «شکل» (the usual choice).", count=len(labels)))
        manual = [p for p, m in caps if not any(f.strip().upper().startswith("SEQ") for f in p.fields)]
        if manual:
            out.append(Finding("F504", "info", f"{len(manual)} of {len(caps)} captions are typed by hand (no SEQ field)",
                               "Hand-typed numbers do not renumber when a figure is added, and Word cannot build a list of figures from them.",
                               "Insert → Caption (or References → Insert Caption) so the number is a SEQ field.", count=len(manual), paragraphs=[p.idx + 1 for p in manual][:30]))
        tbl_by_last = {t.last_para: t for t in doc.tables}
        wrong = []
        for p, m in caps:
            lab = m.group(1).lower()
            if lab in ("جدول", "table") and (p.idx - 1) in tbl_by_last:
                wrong.append((p, "table caption is below the table"))
            elif lab in ("شکل", "figure", "fig", "fig.", "تصویر", "عکس") and p.idx + 1 < len(P) and P[p.idx + 1].has_drawing and not P[p.idx - 1].has_drawing:
                wrong.append((p, "figure caption is above the figure"))
        if wrong:
            out.append(Finding("F505", "info", "caption position differs from the usual Iranian convention (table caption above, figure caption below)",
                               "Most university guides ask for «جدول» above its table and «شکل» below its figure. Some differ; check yours.", "Move the caption.",
                               count=len(wrong), paragraphs=[p.idx + 1 for p, _ in wrong][:30], examples=[{"where": where(p), "before": _zw(p.text[:40]), "after": why} for p, why in wrong[:3]]))
    # ------------------------------------------------------------------ empty paragraphs
    run, runs = 0, []
    for p in P:
        if not p.text.strip() and not p.has_drawing and not p.in_table and not p.has_page_break_before and not p.fields:
            run += 1
            if run == 3:
                runs.append(p)
        else:
            run = 0
    if runs:
        out.append(Finding("F601", "info", "three or more empty paragraphs in a row", "Used to push text to the next page; it breaks when anything above changes.",
                           "Use «page break before» or a section break.", count=len(runs), paragraphs=[p.idx + 1 for p in runs][:30]))
    out.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.code))
    return out


def summarize(doc: Document, findings: List[Finding]) -> Dict[str, object]:
    prof = profile(doc)
    sm = {"paragraphs": len(doc.paragraphs), "persian_paragraphs": sum(1 for p in doc.paragraphs if tr.is_persian(p.text)),
          "tables": len(doc.tables), "sections": len(doc.sections),
          "errors": sum(1 for f in findings if f.severity == "error"), "warnings": sum(1 for f in findings if f.severity == "warn"),
          "info": sum(1 for f in findings if f.severity == "info"),
          "fixable": sum(f.count for f in findings if f.fixable),
          "not_analysed": {k: v for k, v in doc.unsupported.items() if v}}
    sm["profile"] = {"body_paragraphs": prof["body_paragraphs"], "persian_font": prof["cs_font"], "persian_size_pt": None if prof["szcs"] is None else prof["szcs"] / 2,
                     "latin_font": prof["latin_font"], "latin_size_pt": None if prof["latin_sz"] is None else prof["latin_sz"] / 2,
                     "line": None if not prof["line"] or prof["line"][0] is None else prof["line"][0] / 240, "alignment": prof["jc"], "digits": prof["digits"]}
    return sm
