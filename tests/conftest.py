from __future__ import annotations

from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


def public_resolver(host: str, port: int) -> list[str]:
    return ["93.184.216.34"]


@pytest.fixture
def resolver():
    return public_resolver


@pytest.fixture
def fixture_html():
    def read(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    return read
