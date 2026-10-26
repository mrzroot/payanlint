"""pytest setup: make ``src/`` importable and provide the two sample documents used across test files."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from payanlint import sample  # noqa: E402  (needs the sys.path line above)


@pytest.fixture(scope="module")
def flawed(tmp_path_factory):
    """The synthetic thesis chapter with every kind of defect planted in it."""
    return sample.thesis(str(tmp_path_factory.mktemp("s") / "flawed.docx"), True)


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    """The same chapter with the defects removed; must produce no findings."""
    return sample.thesis(str(tmp_path_factory.mktemp("s") / "clean.docx"), False)
