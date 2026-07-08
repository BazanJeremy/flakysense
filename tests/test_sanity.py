"""Scaffold sanity check — replaced by real suites in S1/S2."""
from flakysense import __version__


def test_package_importable():
    assert __version__ == "0.1.0"
