"""The --fix engine: it may only change text in word/document.xml, never touch fields, and be idempotent."""
import re
import zipfile

import pytest

from payanlint.docxbuild import run_xml, field_runs
from payanlint.docxio import read_docx
from payanlint.fixer import fix_docx

from helpers import ZW, codes, mini


def without_text(xml_bytes):
    """document.xml with every <w:t> element emptied, to compare structure while ignoring edited text."""
    return re.sub(r"<w:t(?:\s[^>]*)?>.*?</w:t>", "<w:t/>", xml_bytes.decode("utf-8"), flags=re.S)


def test_fix_only_changes_document_xml_text(flawed, tmp_path):
    dst = str(tmp_path / "f.docx")
    st = fix_docx(flawed, dst, digits="fa")
    assert st["arabic-letters"] > 0 and st["zwnj"] > 0
    a, b = zipfile.ZipFile(flawed), zipfile.ZipFile(dst)
    assert a.namelist() == b.namelist()
    for n in a.namelist():
        if n != "word/document.xml":
            assert a.read(n) == b.read(n), n
    # Blank out the text of every <w:t>: what is left (the XML structure) must be identical.
    assert without_text(a.read("word/document.xml")) == without_text(b.read("word/document.xml"))
    assert len(read_docx(dst).paragraphs) == len(read_docx(flawed).paragraphs)


def test_fixed_copy_is_clean_for_text_rules(flawed, tmp_path):
    dst = str(tmp_path / "f.docx")
    fix_docx(flawed, dst, digits="fa")
    left = codes(dst, digits="fa")
    assert not {c for c in left if c.startswith("P") and c != "P125"}, left
    again = str(tmp_path / "f2.docx")
    assert fix_docx(dst, again, digits="fa") == {}
    assert zipfile.ZipFile(dst).read("word/document.xml") == zipfile.ZipFile(again).read("word/document.xml")


def test_field_results_are_never_edited(tmp_path):
    def b(d):
        d.p(style="Caption", raw=run_xml("شکل ۲-") + field_runs("SEQ Figure \\* ARABIC", "1") + run_xml(": نمودار كتاب ها"))
    p = mini(tmp_path, b)
    dst = str(tmp_path / "f.docx")
    fix_docx(p, dst, digits="fa")
    x = zipfile.ZipFile(dst).read("word/document.xml").decode()
    assert ">1</w:t>" in x and "۱</w:t>" not in x          # the SEQ result keeps its Latin digit
    assert "کتاب" in x and f"کتاب{ZW}ها" in x


def test_inserted_space_gets_xml_space_preserve(tmp_path):
    def b(d):
        d.p([("سلام،", {}), ("خوب هستید و این بند به‌اندازه‌ی کافی بلند است", {})])
    p = mini(tmp_path, b)
    dst = str(tmp_path / "f.docx")
    fix_docx(p, dst)
    x = zipfile.ZipFile(dst).read("word/document.xml").decode()
    assert 'xml:space="preserve"' in x
    assert read_docx(dst).paragraphs[0].text.startswith("سلام، خوب")


def test_skip_categories(flawed, tmp_path):
    dst = str(tmp_path / "f.docx")
    st = fix_docx(flawed, dst, skip=["zwnj", "arabic-letters"])
    assert "zwnj" not in st and "arabic-letters" not in st and st["punct"] > 0


def test_fixed_docx_opens_in_python_docx(flawed, tmp_path):
    docx = pytest.importorskip("docx")
    dst = str(tmp_path / "f.docx")
    fix_docx(flawed, dst, digits="fa")
    assert len(docx.Document(dst).paragraphs) > 20
