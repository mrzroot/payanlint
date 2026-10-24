import json
import os
import subprocess
import sys
import zipfile

import pytest

from payanlint import checks, sample
from payanlint.checks import Options
from payanlint.cli import main
from payanlint.docxbuild import Doc, run_xml, field_runs
from payanlint.docxio import load, read_docx
from payanlint.fixer import fix_docx

ZW = "\u200c"


@pytest.fixture(scope="module")
def flawed(tmp_path_factory):
    return sample.thesis(str(tmp_path_factory.mktemp("s") / "flawed.docx"), True)


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    return sample.thesis(str(tmp_path_factory.mktemp("s") / "clean.docx"), False)


def codes(path, **kw):
    return {f.code for f in checks.analyse(read_docx(path), Options(**kw))}


def mini(tmp_path, build, name="m.docx"):
    d = Doc()
    d.add_footer()
    build(d)
    return d.save(str(tmp_path / name))


BODY = "این یک بند نمونه برای آزمون است و باید به‌اندازه‌ی کافی بلند باشد تا بدنه حساب شود."


# ------------------------------------------------------------------ the sample documents
def test_flawed_sample_triggers_the_expected_rules(flawed):
    got = codes(flawed)
    assert {"P101", "P102", "P103", "P110", "P111", "P120", "P121", "P122", "P124", "P125", "P126", "P113",
            "F203", "F206", "F207", "F209", "F304", "F401", "F403", "F404", "F501", "F502", "F504", "F505", "F601"} <= got


def test_clean_sample_has_no_findings(clean):
    assert checks.analyse(read_docx(clean)) == []
    assert checks.analyse(read_docx(clean), Options(digits="fa", body_font="B Nazanin", body_size=14, line=1.5)) == []


def test_profile_reports_what_the_document_uses(flawed):
    pf = checks.summarize(read_docx(flawed), [])["profile"]
    assert pf["persian_font"] == "B Nazanin" and pf["persian_size_pt"] == 14 and pf["latin_font"] == "Times New Roman"
    assert pf["line"] == 1.5 and pf["alignment"] == "both"


# ------------------------------------------------------------------ format rules, one by one
def test_missing_complex_script_font_is_an_error(tmp_path):
    d = Doc(cs_font=None)
    d.p(BODY)
    d.save(str(tmp_path / "x.docx"))
    f = [x for x in checks.analyse(read_docx(str(tmp_path / "x.docx"))) if x.code == "F201"]
    assert f and f[0].severity == "error"


def test_missing_szcs(tmp_path):
    d = Doc(szcs=None)
    d.p(BODY)
    p = d.save(str(tmp_path / "x.docx"))
    assert "F204" in codes(p)


def test_expected_font_size_line_and_margins(tmp_path):
    p = mini(tmp_path, lambda d: d.p(BODY))
    assert codes(p, body_font="B Titr") >= {"F202"}
    assert "F205" in codes(p, body_size=13)
    assert "F210" in codes(p, line=2.0)
    got = codes(p, margins={"top": 2.0, "left": 4.0})
    assert "F302" in got
    assert "F302" not in codes(p, margins={"top": 3.0, "bottom": 3.0})      # 1701 twips = 3.0 cm


def test_page_number_field_missing(tmp_path):
    d = Doc()
    d.p(BODY)
    assert "F303" in codes(d.save(str(tmp_path / "x.docx")))


def test_lettered_front_matter_and_restart(tmp_path):
    def b(d):
        d.p(BODY)
        d.end_section(fmt="arabicAbjad", footer=1)
        d.p(BODY)
        d.default_sect = d.sectpr(footer=1)           # decimal, no restart
    p = mini(tmp_path, b)
    got = codes(p)
    assert "F305" in got and "F304" not in got


def test_sections_with_different_margins(tmp_path):
    def b(d):
        d.p(BODY)
        d.end_section(margins=(1000, 1000, 1000, 1000), footer=1)
        d.p(BODY)
    assert "F301" in codes(mini(tmp_path, b))


def test_odd_line_spacing_and_alignment(tmp_path):
    def b(d):
        for _ in range(4):
            d.p(BODY)
        d.p(BODY, ppr_extra='<w:spacing w:line="480" w:lineRule="auto"/>', jc="left")
    got = codes(mini(tmp_path, b))
    assert {"F211", "F212"} <= got


def test_bold_slots(tmp_path):
    def b(d):
        d.p([("مهم: ", {"bold": True}), (BODY, {})])
        d.p([("مهم: ", {"bcs": True}), (BODY, {})])
    assert {"F207", "F208"} <= codes(mini(tmp_path, b))


def test_heading_rules(tmp_path):
    def b(d):
        d.heading("فصل اول", 1)
        d.heading("بخش ریز", 3)
        d.heading("", 2)
        d.heading("نتیجه.", 2)
    assert {"F401", "F402", "F403"} <= codes(mini(tmp_path, b))


def test_caption_rules(tmp_path):
    def b(d):
        d.picture()
        d.p(style="Caption", raw=run_xml("شکل ۲-") + field_runs("SEQ Figure \\* ARABIC", "۱") + run_xml(": الف"))
        d.p(style="Caption", raw=run_xml("تصویر ۲.۲: ب"))
        d.p("بعد از تصویر می‌آید و متن عادی است و ادامه دارد.")
    got = codes(mini(tmp_path, b))
    assert {"F501", "F503", "F504"} <= got and "F505" not in got      # figure caption below the picture is the convention


def test_caption_mentions_inside_sentences_are_not_captions(tmp_path):
    p = mini(tmp_path, lambda d: d.p("شکل ۲-۱ نشان می‌دهد که خطا کاهش یافته است و این به‌معنی بهبود روش است."))
    assert not ({"F501", "F502", "F503", "F504", "F505"} & codes(p))


def test_text_input(tmp_path):
    t = tmp_path / "a.txt"
    t.write_text("كتاب ها و می شود\n\nThe end ي\n", encoding="utf-8")
    fs = checks.analyse(load(str(t)))
    assert {"P101", "P111", "P110"} <= {f.code for f in fs} and not any(f.code.startswith("F") for f in fs)


# ------------------------------------------------------------------ fixer
def test_fix_only_changes_document_xml_text(flawed, tmp_path):
    dst = str(tmp_path / "f.docx")
    st = fix_docx(flawed, dst, digits="fa")
    assert st["arabic-letters"] > 0 and st["zwnj"] > 0
    a, b = zipfile.ZipFile(flawed), zipfile.ZipFile(dst)
    assert a.namelist() == b.namelist()
    for n in a.namelist():
        if n != "word/document.xml":
            assert a.read(n) == b.read(n), n
    import re
    strip = lambda s: re.sub(r"<w:t(?:\s[^>]*)?>.*?</w:t>", "<w:t/>", s.decode("utf-8"), flags=re.S)
    assert strip(a.read("word/document.xml")) == strip(b.read("word/document.xml"))
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


# ------------------------------------------------------------------ CLI
def run_cli(*args):
    return main(list(args))


def test_cli_json_and_exit_codes(flawed, clean, capsys):
    assert run_cli(flawed, "--json") == 1                   # has an error
    data = json.loads(capsys.readouterr().out)
    assert data["tool"] == "payanlint" and data["summary"]["errors"] >= 1 and data["findings"][0]["code"]
    assert run_cli(clean, "--json", "--strict") == 0
    capsys.readouterr()


def test_cli_strict_turns_warnings_into_failure(tmp_path, capsys):
    p = mini(tmp_path, lambda d: d.p("داده ها در جدول آمده است و این بند به‌اندازه‌ی کافی بلند است."))
    assert run_cli(p) == 0
    assert run_cli(p, "--strict") == 1
    capsys.readouterr()


def test_cli_fix_writes_a_copy_and_reports_recheck(flawed, tmp_path, capsys):
    out = str(tmp_path / "o.docx")
    assert run_cli(flawed, "--fix", "-o", out, "--digits", "fa") == 1       # exit code reflects the ORIGINAL file
    txt = capsys.readouterr().out
    assert "fixed copy" in txt and "re-check of the copy" in txt and os.path.exists(out)


def test_cli_refuses_to_overwrite_input(flawed, capsys):
    assert run_cli(flawed, "--fix", "-o", flawed) == 2


def test_cli_demo_and_sample(tmp_path, capsys):
    assert run_cli("--demo", "--no-color") == 1
    assert "P101" in capsys.readouterr().out
    assert run_cli("--demo", "--json") == 1
    assert json.loads(capsys.readouterr().out)["summary"]["errors"] >= 1
    p = str(tmp_path / "c.docx")
    assert run_cli("--make-sample", p, "--clean") == 0 and run_cli(p, "--strict") == 0
    capsys.readouterr()
    with pytest.raises(SystemExit):
        run_cli("--demo", "--fix")


def test_cli_missing_and_broken_files(tmp_path, capsys):
    assert run_cli(str(tmp_path / "nope.docx")) == 2
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"not a zip")
    assert run_cli(str(bad)) == 2
    capsys.readouterr()


def test_cli_text_fix(tmp_path, capsys):
    t = tmp_path / "a.txt"
    t.write_text("كتاب ها ،می شود\n", encoding="utf-8")
    out = tmp_path / "b.txt"
    run_cli(str(t), "--fix", "-o", str(out))
    assert out.read_text(encoding="utf-8") == f"کتاب{ZW}ها، می{ZW}شود\n"
    capsys.readouterr()


def test_module_entry_point():
    r = subprocess.run([sys.executable, "-m", "payanlint", "--version"], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.join(os.path.dirname(__file__), "..", "src")})
    assert r.returncode == 0 and "payanlint 0.1.0" in r.stdout
