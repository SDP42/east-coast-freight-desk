"""Rule overrides that sit in front of the intent classifier."""

from app.services.assistant import FORECAST_RE, OFF_MAP, PORT_CHOICE_RE, VERDICT_RE


def test_port_choice_question_is_recognised():
    assert PORT_CHOICE_RE.search("for the next 15 days, which port should i use for trades with singapore")
    assert not PORT_CHOICE_RE.search("what will the ocean freight rate do")


def test_buy_now_questions_go_to_the_verdict():
    assert VERDICT_RE.search("should i buy coal now")
    assert VERDICT_RE.search("is it a good time to book")
    assert not VERDICT_RE.search("how risky is australia to haldia")


def test_short_forecast_wording_is_recognised():
    assert FORECAST_RE.search("what is the freight forecast")
    assert FORECAST_RE.search("freight outlook")


def test_unmodelled_places_are_flagged():
    assert OFF_MAP.search("trades with singapore")
    assert not OFF_MAP.search("australia to paradip")
