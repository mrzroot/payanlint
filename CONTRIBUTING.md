# Contributing

Thanks for helping! payanlint is small on purpose: standard library only, no telemetry, no network.

```sh
git clone https://github.com/mrzroot/payanlint && cd payanlint
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest
python -m payanlint --demo
```

Ground rules

- **No new runtime dependencies**, and Python 3.9 must keep working.
- Tests use synthetic, generated `.docx` fixtures only. Never commit a real thesis or any real person's document.
- A rule that auto-fixes must be provably safe: it may change `<w:t>` characters only, never touch field results, and must be idempotent (see `tests/test_textrules.py`). Anything uncertain is reported, not fixed.
- Add your change to `CHANGELOG.md`.
- Found a tool that already does this? Open an issue; it will be linked in the README and NOVELTY.md.
