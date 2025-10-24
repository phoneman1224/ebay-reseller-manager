"""Tests for GUI value helper utilities."""
from gui.value_helpers import resolve_cost, format_currency


class FakeRow:
    def __init__(self, **data):
        self._data = data

    def keys(self):
        return self._data.keys()

    def __getitem__(self, key):
        return self._data[key]


def test_resolve_cost_accepts_row_like_objects():
    row = FakeRow(cost="12.50")
    assert resolve_cost(row) == 12.5


def test_resolve_cost_returns_none_for_invalid_values():
    row = FakeRow(cost="not-a-number")
    assert resolve_cost(row) is None


def test_format_currency_handles_invalid_values():
    assert format_currency("bad", default="-") == "-"
    assert format_currency(None) == "N/A"
    assert format_currency(5) == "$5.00"
