from __future__ import annotations

from collections import Counter


def cumulative_incidence(
    durations: list[float], event_codes: list[int], horizons: tuple[float, ...]
) -> dict[float, dict[str, float]]:
    """Aalen-Johansen CIF for cause 1 and cause 2.

    Event codes: 0=censored, 1=charge-off, 2=paid in full. Durations share one
    unit (the CLI uses days). Ties are processed as a single event time.
    """
    if len(durations) != len(event_codes) or not durations:
        raise ValueError("durations and event_codes must be non-empty and equal length")
    if any(t < 0 for t in durations) or any(code not in (0, 1, 2) for code in event_codes):
        raise ValueError("durations must be nonnegative and codes must be 0, 1, or 2")
    counts: dict[float, Counter[int]] = {}
    for time, code in zip(durations, event_codes):
        counts.setdefault(time, Counter())[code] += 1
    at_risk = len(durations)
    survival = 1.0
    cif = {1: 0.0, 2: 0.0}
    timeline: list[tuple[float, float, float]] = []
    for time in sorted(counts):
        row = counts[time]
        event1, event2 = row[1], row[2]
        if at_risk <= 0:
            break
        old_survival = survival
        cif[1] += old_survival * event1 / at_risk
        cif[2] += old_survival * event2 / at_risk
        survival = old_survival * (1 - (event1 + event2) / at_risk)
        timeline.append((time, cif[1], cif[2]))
        at_risk -= sum(row.values())
    results: dict[float, dict[str, float]] = {}
    for horizon in horizons:
        charge = paid = 0.0
        for time, f1, f2 in timeline:
            if time > horizon:
                break
            charge, paid = f1, f2
        results[horizon] = {"chargeoff_cif": charge, "paid_in_full_cif": paid}
    return results
