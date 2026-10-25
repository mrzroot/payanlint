## What and why

## Checklist
- [ ] `pytest` passes; new behaviour has a test (invented or generated fixtures only)
- [ ] No new runtime dependency; Python 3.9 still works
- [ ] An auto-fix rule changes `<w:t>` characters only, never a field result, and is idempotent (see `tests/test_textrules.py`)
- [ ] A rule that is uncertain is reported, not fixed
- [ ] `CHANGELOG.md` updated
