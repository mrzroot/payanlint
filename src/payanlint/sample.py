"""Synthetic thesis chapter for --demo and the tests (invented text on an invented topic; not from any real thesis).

``thesis(path, flawed=True)`` writes a two-section .docx: lettered front matter and a body chapter. The flawed
version contains the usual problems of a thesis written over several years in Word; the clean one fixes each of them.
"""
from __future__ import annotations

from .docxbuild import Doc, run_xml, field_runs

AR = str.maketrans("ی ک".replace(" ", ""), "يك")        # Persian → Arabic letters (for the flawed text)
FONT, SZ = "B Nazanin", 28


def ar(s: str) -> str:
    return s.translate(AR)


def seq_caption(d: Doc, label: str, chapter: str, n: str, title: str, sep: str = "-", seq: str = "Figure", typed: bool = False):
    if typed:
        raw = run_xml(f"{label} {chapter}{sep}{n}: {title}")
    else:
        raw = run_xml(f"{label} {chapter}{sep}") + field_runs(f"SEQ {seq} \\* ARABIC", n) + run_xml(f": {title}")
    d.p(style="Caption", raw=raw)


def thesis(path: str, flawed: bool = True) -> str:
    F = flawed
    d = Doc(cs_font=FONT, szcs=SZ, lang_bidi="fa-IR" if not F else "ar-SA")
    foot = d.add_footer()
    # ---------------------------------------------------------------- front matter (section 1)
    d.heading("چکیده", 1)
    abstract = ("در این پژوهش عملکرد چند الگوریتم خوشه‌بندی برای داده‌های حسگرهای محیطی بررسی شده است. "
                "نتایج نشان می‌دهد که روش پیشنهادی در مقایسه با روش‌های پایه، دقت بیشتری دارد.")
    if F:
        abstract = ("در این پژوهش عملکرد چند الگوريتم خوشه‌بندي برای داده های حسگرهای محیطی بررسی شده است . "
                    "نتایج نشان می دهد كه روش پیشنهادی در مقایسه با روش های پایه، دقت بیشتری دارد.")
    d.p(abstract)
    d.p("کلیدواژه‌ها: خوشه‌بندی، حسگر، داده‌کاوی" if not F else "کلیدواژه ها:خوشه‌بندی، حسگر، داده‌کاوی")
    d.end_section(fmt=None if F else "arabicAbjad", start=None if F else 1, footer=foot)
    foot2 = d.add_footer()
    # ---------------------------------------------------------------- chapter 2 (section 2)
    d.heading("فصل دوم: مبانی نظری و پیشینه پژوهش", 1)
    if F:
        d.heading("۲-۱-۱ خوشه‌بندی سلسله‌مراتبی", 3)           # level 1 → 3
    else:
        d.heading("۲-۱ خوشه‌بندی داده‌ها", 2)
    p1 = "در این فصل مفاهیم پایه‌ی خوشه‌بندی داده‌ها مرور می‌شود و نتایج مطالعات پیشین با یکدیگر مقایسه می‌گردد."
    d.p(ar(p1.replace("پایه‌ی", "پایه‌ي")) if F else p1)
    p2 = "پژوهش‌های پیشین نشان می‌دهد که الگوریتم‌ها در برابر داده‌های پرت حساس هستند و دقت آن‌ها به‌ازای ۱۲۰ حسگر کاهش می‌یابد."
    d.p(("پژوهش هاي پيشين نشان می شود كه الگوريتم ها در برابر داده های پرت حساس هستند و دقت آنها به‌ازای 120 حسگر كاهش می‌یابد.") if F else p2)
    p3 = "داده‌ها پس از پاک‌سازی، نرمال شدند. سپس ۴۵ نمونه برای «آزمون» کنار گذاشته شد، طبق (Smith, 2020)."
    d.p("داده ها ،پس از پاک‌ســازی ، نرمال شدند .   سپس ٤٥ نمونه برای \"آزمون\" کنار گذاشته شد, طبق (Smith, 2020)." if F else p3)
    d.p("اندازه‌گیری‌ها در بازه‌ی سال‌های ۱۳۹۸ تا ۱۴۰۱ در ۳۲ ایستگاه انجام شد و نتیجه‌ی هر ایستگاه جداگانه ثبت گردید." if not F else
        "اندازه‌گیری‌ها در بازه‌ی سال‌های ۱۳۹۸ تا 1401 در 32 ایستگاه انجام شد و نتیجه‌ی هر ایستگاه جداگانه ثبت گردید.")
    d.p("همان‌طور که در شکل ۲-۱ دیده می‌شود، خوشه‌های میانی بیشترین پراکندگی را دارند و دقت آن‌ها پایین‌تر است.")
    # figure + caption (flawed: caption above the picture, typed by hand, Latin SEQ result)
    if F:
        seq_caption(d, "شکل", "۲", "1", "نمودار پراکندگی خوشه‌ها", typed=False)
        d.picture()
    else:
        d.picture()
        seq_caption(d, "شکل", "۲", "۱", "نمودار پراکندگی خوشه‌ها")
    # pasted paragraph with other font / size, and a bold run that only has w:b
    pasted = "این بند از یک فایل قدیمی کپی شده است و قلم و اندازه‌ی آن با بقیه‌ی متن فرق دارد، هرچند در نوار ابزار یکسان دیده می‌شود."
    if F:
        d.p([(pasted, {"cs_font": "B Mitra", "szcs": 24})])
        d.p([("نکته‌ی مهم: ", {"bold": True}), ("برای مقایسه‌ی منصفانه، همه‌ی الگوریتم‌ها با پارامترهای یکسان اجرا شدند و نتایج میانگین گرفته شد.", {})])
    else:
        d.p(pasted.replace("این بند از یک فایل قدیمی کپی شده است و قلم و اندازه‌ی آن با بقیه‌ی متن فرق دارد، هرچند در نوار ابزار یکسان دیده می‌شود.",
                           "این بند به‌درستی با سبک عادی قالب‌بندی شده است و قلم و اندازه‌ی آن با بقیه‌ی متن یکسان است، همان‌طور که انتظار می‌رود."))
        d.p([("نکته‌ی مهم: ", {"bold": True, "bcs": True}), ("برای مقایسه‌ی منصفانه، همه‌ی الگوریتم‌ها با پارامترهای یکسان اجرا شدند و نتایج میانگین گرفته شد.", {})])
    if F:
        d.p("      این بند با چند فاصله شروع شده است تا تو رفتگی داشته باشد، اما با تغییر قلم جابه‌جا می‌شود و نباید این‌طور نوشته شود.")
    else:
        d.p("این بند با تورفتگی خط اول در سبک پاراگراف شروع می‌شود و با تغییر قلم جابه‌جا نمی‌شود و همین درست است.")
    d.p("ویژگی‌های حسگرها در جدول ۲-۱ آمده است.")
    d.heading("۲-۲ جمع‌بندی" if not F else "۲-۲ جمع بندی.", 2)
    if not F:
        pass
    d.p("جزئیات روش‌ها در این بخش آمده و در فصل بعد با داده‌های واقعی آزموده می‌شود، تا ارزیابی کامل شود.")
    if F:
        d.p([("روش تحقیق", {"bold": True, "bcs": True})])     # looks like a heading, is not one
        d.p("")
        d.p("")
        d.p("")
    # table with caption above (clean) / below (flawed)
    rows = [["نوع حسگر", "دقت (٪)", "بازه (متر)"], ["دما", "۹۸", "۱۰۰"], ["رطوبت", "۹۵", "۸۰"]]
    if F:
        rows = [["نوع حسگر", "دقت (٪)", "بازه (متر)"], ["دما", "98", "۱۰۰"], ["رطوبت", "۹۵", "۸۰"]]
        d.table(rows, bidi_visual=True)
        seq_caption(d, "جدول", "۲", "۱", "ویژگی‌های حسگرها", sep=".", seq="Table", typed=True)
    else:
        seq_caption(d, "جدول", "۲", "۱", "ویژگی‌های حسگرها", seq="Table")
        d.table(rows, bidi_visual=True)
    d.p("The proposed model follows Rossman (2000), see Fig. 2-3.", bidi=False, jc="both")
    d.default_sect = d.sectpr(fmt=None, start=1, footer=foot2)
    return d.save(path)
