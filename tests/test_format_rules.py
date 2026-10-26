"""Word-formatting rules (F-codes): fonts, sizes, margins, page numbers, headings and captions.

Each test builds the smallest document that should trigger one rule and asserts on the codes raised.
"""
from payanlint import checks
from payanlint.checks import Options
from payanlint.docxbuild import Doc, run_xml, field_runs
from payanlint.docxio import load, read_docx

from helpers import BODY, codes, mini


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
