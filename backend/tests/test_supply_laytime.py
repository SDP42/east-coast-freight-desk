"""Offline tests for laytime and part-laden berth fit."""

import pytest

from app.services import laytime
from app.services.compatibility import MIN_PARTIAL_FRACTION, part_laden_fraction

def test_laytime_demurrage_and_despatch():
    d = laytime.laytime_statement(75000, 20000, 120, 6, 20000, [laytime.Stoppage("Rain", 10)])
    assert d["on_demurrage"] and d["amount_usd"] == pytest.approx(11666.67, abs=0.01)
    e = laytime.laytime_statement(75000, 20000, 60, 6, 20000, [])
    assert not e["on_demurrage"] and e["amount_usd"] == pytest.approx((90 - 54) / 24 * 20000 * 0.5, abs=0.01)


def test_once_on_demurrage_stoppages_after_laytime_are_not_deducted():
    a = laytime.laytime_statement(60000, 20000, 120, 0, 10000, [laytime.Stoppage("Rain", 8, after_laytime=True)])
    b = laytime.laytime_statement(60000, 20000, 120, 0, 10000, [])
    assert a["amount_usd"] == b["amount_usd"] and a["ignored_after_demurrage_hours"] == 8


def test_part_laden_fraction_matches_paradip_capesize_case():
    f = part_laden_fraction(17.0, 16.5)  # Capesize design draft against Paradip's 16.5 m
    assert f >= MIN_PARTIAL_FRACTION and f < 1.0
    assert part_laden_fraction(17.0, 8.0) < MIN_PARTIAL_FRACTION  # a shallow port is not a part-laden call
