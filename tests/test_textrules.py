import random

import pytest

from payanlint import textrules as tr

ZW = "\u200c"


def fixed(T, digits="keep"):
    for _ in range(5):
        fx = [f for f in tr.scan(T, digits=digits) if f.auto]
        if not fx:
            break
        T = tr.apply(T, fx)
    return T


def codes(T, digits="keep"):
    return {f.code for f in tr.scan(T, digits=digits)}


def test_arabic_letters_are_replaced():
    assert fixed("این كتاب درباره‌ي علي است و همین") == "این کتاب درباره‌ی علی است و همین"


def test_vocalised_arabic_text_is_left_alone():
    t = "قال الله تعالى: إِنَّ مَعَ الْعُسْرِ يُسْرًا و این جمله فارسی است"
    assert "P101" not in codes(t)


def test_latin_paragraph_is_never_touched():
    t = "The model ي uses 12 sensors , and ك works ."
    assert tr.scan(t) == []


def test_arabic_indic_digits_become_persian_not_latin():
    assert fixed("سپس ٤٥ نمونه و ٦ حسگر") == "سپس ۴۵ نمونه و ۶ حسگر"
    assert "٤" not in fixed("حدود ٤٥٦ مورد در این بخش دیده شد")


def test_digit_policy_fa_converts_only_persian_context():
    t = "در ۱۲ ایستگاه و 34 حسگر؛ طبق Smith 2020 و در Fig. 2 و COVID-19 و ISO9001 دیده شد"
    out = fixed(t, "fa")
    assert "۳۴" in out
    for keep in ("Smith 2020", "Fig. 2", "COVID-19", "ISO9001"):
        assert keep in out


def test_digit_policy_en():
    assert fixed("در ۱۲ ایستگاه و ٣٤ حسگر انجام شد", "en") == "در 12 ایستگاه و 34 حسگر انجام شد"


def test_default_policy_does_not_touch_latin_or_persian_digits():
    t = "در ۱۲ ایستگاه و 34 حسگر انجام شد"
    assert fixed(t) == t


@pytest.mark.parametrize("bad,good", [
    ("نتایج نشان می دهد", f"نتایج نشان می{ZW}دهد"),
    ("این کار نمی شود", f"این کار نمی{ZW}شود"),
    ("کتاب ها و مقاله ها", f"کتاب{ZW}ها و مقاله{ZW}ها"),
    ("روش های پیشنهادی", f"روش{ZW}های پیشنهادی"),
    ("دانشجو ها در کلاس بودند", "دانشجوها در کلاس بودند"),          # non-joining letter: no half-space needed
])
def test_zwnj_rules(bad, good):
    assert fixed(bad) == good


@pytest.mark.parametrize("ok", [
    "نمی از آب در خاک ماند و بعد خشک شد",          # «نمی» = a little moisture; next word is a stop word
    f"داده{ZW}ها و DNA{ZW}ها در جدول آمده است",     # half-space between a Latin word and a suffix is legitimate
    "او گفت: ها؟ و بعد خنده‌ی بلندی شنیده شد",
])
def test_zwnj_false_positives_are_avoided(ok):
    assert not ({"P110", "P111", "P112"} & codes(ok)), ok


def test_stray_zwnj_at_edges_and_doubled():
    t = f"{ZW}کتاب{ZW} و {ZW}داده خوشه{ZW}{ZW}بندی"
    out = fixed(t)
    assert out == f"کتاب و داده خوشه{ZW}بندی"


@pytest.mark.parametrize("bad,good", [
    ("سلام ، خوبی ؟", "سلام، خوبی؟"),
    ("آمد،رفت و گفت:سلام", "آمد، رفت و گفت: سلام"),
    ("متن اول ، متن دوم", "متن اول، متن دوم"),
    ("است.این", "است. این"),
    ("داده, روش و نتیجه", "داده، روش و نتیجه"),
    ("چرا آمد? نمی دانم;", f"چرا آمد؟ نمی{ZW}دانم؛"),
    ("نتیجه ( خوب ) بود", "نتیجه (خوب) بود"),
    ("از «  متن » استفاده شد", "از «متن» استفاده شد"),
    ("دو  فاصله   پشت هم", "دو فاصله پشت هم"),
    ('او گفت "سلام دنیا" و رفت', "او گفت «سلام دنیا» و رفت"),
])
def test_punctuation_and_spacing(bad, good):
    assert fixed(bad) == good


@pytest.mark.parametrize("ok", [
    "در ه.ق و ص.ب و م.م آمده است و این درست است",
    "نسبت ۱ : ۲ و ۱:۲ و ساعت ۱۰:۳۰ در متن آمده است",
    "جمع ۱،۲ و (۱،۲) در فهرست آمده و این است",
    "طبق (Smith, 2020) و Rossman, 2000 در متن آمده است",
])
def test_punctuation_false_positives_are_avoided(ok):
    assert not ({"P120", "P121", "P122"} & codes(ok)), ok


def test_indentation_with_spaces_is_reported_not_fixed():
    fx = tr.scan("      این بند با فاصله شروع شده است و باید جور دیگری باشد")
    assert [f.code for f in fx if f.code == "P125"] and not [f for f in fx if f.code == "P125" and f.auto]


def test_tatweel_removed():
    assert fixed("پاک‌ســازی و الگــوریتم در این متن") == "پاک‌سازی و الگوریتم در این متن"


def test_fixing_is_idempotent_on_random_messy_text():
    rnd = random.Random(7)
    vocab = ["كتاب", "ها", "می", "شود", "،", "؛", "؟", ".", ",", "(", ")", "«", "»", '"', "٤٥", "12", "۱۲", "Smith", "داده", "های",
             ZW, "  ", "ي", "روش", "نمی", "دهد", "!", ":", "ــ", "Fig.", "ایستگاه"]
    for _ in range(300):
        T = " ".join(rnd.choice(vocab) for _ in range(rnd.randint(3, 14)))
        for dg in ("keep", "fa"):
            once = fixed(T, dg)
            assert fixed(once, dg) == once, (T, once)
