"""Paragraph-level XML editing shared by the fixer: find paragraphs in document.xml and edit <w:t> text by character."""
from __future__ import annotations

import re
from typing import List, Set, Tuple
from xml.sax.saxutils import escape, unescape

P_TOKEN = re.compile(r"<w:p(?=[\s>/])[^>]*?(/?)>|</w:p>|<w:txbxContent[\s>]|</w:txbxContent>")


def paragraph_spans(xml: str) -> List[Tuple[int, int]]:
    """(start, end) offsets of every block-level paragraph, in the same order docxio reports them."""
    spans, stack, tx = [], [], 0
    for m in P_TOKEN.finditer(xml):
        tok = m.group(0)
        if tok.startswith("<w:txbxContent"):
            tx += 1
        elif tok == "</w:txbxContent>":
            tx -= 1
        elif tok.startswith("<w:p"):
            if m.group(1) == "/":          # <w:p/>
                if tx == 0:
                    spans.append((m.start(), m.end()))
                continue
            stack.append((m.start(), tx))
        else:
            s, t = stack.pop()
            if t == 0:
                spans.append((s, m.end()))
    spans.sort()
    return spans


_WT = re.compile(r"(<w:t(?=[\s>])[^>]*>)(.*?)(</w:t>)", re.S)


def edit_paragraph(pxml: str, plan) -> str:
    """Apply character-level edits to the concatenated <w:t> text of one paragraph.

    plan(T, protected) -> (deletions: set of positions, insertions: {position: text inserted before that character});
    ``protected`` holds the positions of text that is a field result (page numbers, SEQ numbers): Word regenerates it, so it is never edited.
    Because the edits are per character they work across run boundaries (e.g. «شکل 2-» + a SEQ field result «1»)."""
    nodes = list(_WT.finditer(pxml))
    texts = [unescape(m.group(2)) for m in nodes]
    T = "".join(texts)
    dels, ins = plan(T, _protected(pxml, nodes, texts))
    if not dels and not ins:
        return pxml
    out, last, pos = [], 0, 0
    for k, (m, t) in enumerate(zip(nodes, texts)):
        piece = []
        for j, ch in enumerate(t):
            i = pos + j
            if i in ins:
                piece.append(ins[i])
            if i not in dels:
                piece.append(ch)
        if k == len(nodes) - 1 and len(T) in ins:
            piece.append(ins[len(T)])
        pos += len(t)
        new = "".join(piece)
        head = pxml[last:m.start(2)]
        if new != t and new != new.strip(" ") and "xml:space" not in m.group(1):
            head = head[:len(head) - len(m.group(1))] + m.group(1)[:-1] + ' xml:space="preserve">'
        out.append(head)
        out.append(escape(new) if new != t else m.group(2))
        last = m.end(2)
    out.append(pxml[last:])
    return "".join(out)




_FLD = re.compile(r'<w:fldChar\b[^>]*w:fldCharType="(begin|separate|end)"[^>]*/>|<w:fldSimple\b[^>]*>|</w:fldSimple>|<w:t(?=[\s>])[^>]*>(.*?)</w:t>', re.S)


def _protected(pxml: str, nodes, texts) -> Set[int]:
    """Positions (in the concatenated <w:t> text) that belong to a field result or a w:fldSimple."""
    starts, pos = {}, 0
    for m, t in zip(nodes, texts):
        starts[m.start()] = (pos, len(t))
        pos += len(t)
    prot: Set[int] = set()
    stack: List[str] = []
    simple = 0
    for m in _FLD.finditer(pxml):
        tok = m.group(0)
        if tok.startswith("<w:fldChar"):
            kind = m.group(1)
            if kind == "begin":
                stack.append("instr")
            elif kind == "separate" and stack:
                stack[-1] = "result"
            elif kind == "end" and stack:
                stack.pop()
        elif tok.startswith("<w:fldSimple"):
            simple += 1
        elif tok == "</w:fldSimple>":
            simple = max(0, simple - 1)
        else:
            if (stack and stack[-1] == "result") or simple:
                p, n = starts.get(m.start(), (None, 0))
                if p is not None:
                    prot.update(range(p, p + n))
    return prot
