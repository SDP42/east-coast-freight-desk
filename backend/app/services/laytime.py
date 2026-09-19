"""Laytime, demurrage and despatch statement of facts calculator.

The rules used are the common voyage-charter ones, stated so a reader can check them:
- Laytime allowed = cargo tonnes / agreed daily rate (working days, Sundays and holidays included, "SHINC").
- Time counts from notice of readiness (plus the notice period) to completion of cargo work.
- Deductions such as rain stoppages, strikes and shore breakdowns are taken off the time used.
- Once on demurrage, always on demurrage: excluded periods after laytime expires are NOT deducted.
- Demurrage is paid at the daily rate for the excess; despatch for time saved is customarily half the demurrage rate.
This is a working tool for checking a claim, not legal advice; the charter party governs.
"""

from dataclasses import dataclass


@dataclass
class Stoppage:
    label: str
    hours: float
    after_laytime: bool = False  # true if the stoppage happened once the ship was already on demurrage


def laytime_statement(cargo_tonnes: float, rate_tonnes_per_day: float, hours_nor_to_complete: float, notice_hours: float,
                      demurrage_usd_per_day: float, stoppages: list[Stoppage], despatch_share: float = 0.5) -> dict:
    allowed_h = cargo_tonnes / rate_tonnes_per_day * 24
    gross_used = max(0.0, hours_nor_to_complete - notice_hours)
    before = sum(s.hours for s in stoppages if not s.after_laytime)
    after = sum(s.hours for s in stoppages if s.after_laytime)
    used_before_deduction = gross_used
    used = gross_used - before
    on_demurrage = used > allowed_h
    if on_demurrage:
        # Excluded periods after laytime expired are not deducted ("once on demurrage, always on demurrage").
        excess_h = used - allowed_h
        amount = excess_h / 24 * demurrage_usd_per_day
        result, hours = "Demurrage payable by charterer", excess_h
    else:
        saved_h = allowed_h - used
        amount = saved_h / 24 * demurrage_usd_per_day * despatch_share
        result, hours = "Despatch payable by owner", saved_h
    return {
        "result": result, "amount_usd": round(amount, 2), "hours": round(hours, 2), "days": round(hours / 24, 3),
        "laytime_allowed_hours": round(allowed_h, 2), "laytime_allowed_days": round(allowed_h / 24, 3),
        "time_used_hours": round(used, 2), "gross_time_hours": round(used_before_deduction, 2),
        "deducted_hours": round(before, 2), "ignored_after_demurrage_hours": round(after, 2),
        "demurrage_usd_per_day": demurrage_usd_per_day, "despatch_share": despatch_share,
        "on_demurrage": on_demurrage,
        "steps": [
            f"Laytime allowed = {cargo_tonnes:,.0f} t / {rate_tonnes_per_day:,.0f} t per day = {allowed_h / 24:.2f} days ({allowed_h:.1f} h).",
            f"Time from notice of readiness to completion = {hours_nor_to_complete:.1f} h; less {notice_hours:g} h notice period = {gross_used:.1f} h.",
            f"Less {before:.1f} h of excepted periods (weather, strikes, shore breakdowns) = {used:.1f} h counted.",
            (f"{used:.1f} h counted exceeds {allowed_h:.1f} h allowed by {hours:.1f} h, so the ship is on demurrage"
             + (f"; {after:.1f} h of stoppages after that point are not deducted." if after else ".")) if on_demurrage
            else f"{used:.1f} h counted is {hours:.1f} h inside the {allowed_h:.1f} h allowed, so despatch is earned at {despatch_share:.0%} of the demurrage rate.",
            f"{result}: {hours / 24:.3f} days x ${demurrage_usd_per_day:,.0f} per day" + (f" x {despatch_share:.0%}" if not on_demurrage else "") + f" = ${amount:,.2f}.",
        ],
    }
