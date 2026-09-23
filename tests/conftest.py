import pathlib

import pytest
from bs4 import BeautifulSoup

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def soup_of():
    """Parse a captured search page the way the workers do."""

    def load(name):
        return BeautifulSoup((FIXTURES / name).read_text(), "lxml")

    return load
