"""Offline tests for laytime, part-laden berth fit and the Newcastle feed parser."""

import pytest

from app.services import laytime, supply
from app.services.compatibility import MIN_PARTIAL_FRACTION, part_laden_fraction

SAMPLE_HTML = """
<table><tr><th>Date &amp; Time</th><th>Expected</th><th>ARR / DEP</th><th>Vessel</th><th>Vessel type</th><th>Agent</th><th>From</th><th>To</th><th>In port</th></tr>
<tr><td>Sat 19 Sep 20:00</td><td>N/A</td><td>Arrival</td><td>Weaver Arrow</td><td>Open Hatch Cargo Ship</td><td>MON</td><td>Melbourne</td><td>Dyke 2 (D2)</td><td>No</td></tr>
<tr><td>Sun 20 Sep 00:01</td><td>N/A</td><td>Arrival</td><td>Shine Jade</td><td>Bulk Carrier</td><td>WSS</td><td>Taichung</td><td>Kooragang 8 (K8)</td><td>No</td></tr>
<tr><td>Sun 20 Sep 03:45</td><td>N/A</td><td>Departure</td><td>Eastern Zinnia</td><td>Bulk Carrier</td><td>WSA</td><td>Kooragang 4 (K4)</td><td>China, People&#039;s Republic Of</td><td>Yes</td></tr>
<tr><td>Sun 20 Sep 05:15</td><td>N/A</td><td>Arrival</td><td>Maritime Guardian</td><td>Chemical/Products Tanker</td><td>GAC</td><td>Hongkou</td><td>Mayfield 7 (M7)</td><td>No</td></tr>
</table>"""


def test_feed_parser_reads_rows_and_unescapes():
    rows = supply._parse(SAMPLE_HTML)
    assert len(rows) == 4 and rows[2]["to"] == "China, People's Republic Of" and rows[2]["in_port"] is True


def test_supply_counts_only_coal_berths(monkeypatch):
    monkeypatch.setattr(supply, "movements", lambda force=False: {"rows": supply._parse(SAMPLE_HTML), "fetched_at": 1.0, "error": None, "stale": False})
    s = supply.newcastle_supply()
    assert s["open_ships_arriving"] == 1  # Shine Jade to Kooragang; the Dyke arrival and the tanker are not coal berths
    assert s["coal_cargoes_loaded"] == 1


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
