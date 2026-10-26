"""Command-line behaviour: output formats, exit codes (0 ok, 1 findings, 2 usage/IO error), --fix and --demo."""
import json
import os
import subprocess
import sys

import pytest

from payanlint.cli import main

from helpers import ZW, mini


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
