from datetime import date, timedelta
from statistics import median

ISIN_COUNTRY = {"IE": "Ireland", "LU": "Luxembourg", "DE": "Germany", "FR": "France"}
PERF_FIELDS = [f"{who}_{n}y_pct" for who in ("fund", "benchmark") for n in (1, 3, 5)]
TRACKING_TOL = 2.0
PEER_TOL = 5.0


def isin_check_digit_ok(isin: str) -> bool:
    if len(isin) != 12 or not isin[-1].isdigit():
        return False
    digits = "".join(str(int(c, 36)) for c in isin[:-1])
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * 2 if i % 2 == 0 else int(d)
        total += n - 9 if n > 9 else n
    return (10 - total % 10) % 10 == int(isin[-1])


def annualised(record: dict, field: str) -> float | None:
    value = record.get(field)
    years = int(field.split("_")[1][0])
    if value is None or years == 1 or record.get("multi_year_annualised") is not False:
        return value
    return ((1 + value / 100) ** (1 / years) - 1) * 100


def number_variants(x: float) -> set[str]:
    out = set()
    for decimals in (0, 1, 2):
        s = f"{x:.{decimals}f}"
        if abs(float(s) - x) > 1e-9:
            continue
        out |= {s, s.replace(".", ",")}
        if abs(x) >= 1000:
            thousands = f"{x:,.{decimals}f}"
            out |= {thousands, thousands.replace(",", " "), thousands.replace(",", "'")}
    return out


def contexts(text: str, x: float, width: int = 40) -> list[str]:
    found = []
    for s in number_variants(x):
        start = text.find(s)
        while start != -1:
            found.append(text[max(0, start - width):start].lower())
            start = text.find(s, start + 1)
    return found


def check_record(record: dict, text: str) -> list[tuple[str, str]]:
    flags = []
    isin = record.get("isin") or ""

    if not isin_check_digit_ok(isin):
        flags.append(("isin", "check digit fails"))
    expected = ISIN_COUNTRY.get(isin[:2])
    if expected and record.get("domicile") != expected:
        flags.append(("domicile", f"ISIN prefix says {expected}"))

    as_of = date.fromisoformat(record["as_of_date"])
    if (as_of + timedelta(days=4)).month == as_of.month:
        flags.append(("as_of_date", "not a month end"))
    if record.get("inception_date") and date.fromisoformat(record["inception_date"]) >= as_of:
        flags.append(("inception_date", "not before as-of date"))

    ter = record.get("ter_pct")
    if ter is not None and not 0 < ter <= 1.5:
        flags.append(("ter_pct", "outside 0-1.5%"))

    for who in ("fund", "benchmark"):
        values = {n: record.get(f"{who}_{n}y_pct") for n in (1, 3, 5)}
        for a, b in [(1, 3), (3, 5), (1, 5)]:
            if values[a] is not None and values[a] == values[b]:
                flags.append((f"{who}_{b}y_pct", f"same value as {a}y"))

    for n in (1, 3, 5):
        f, b = annualised(record, f"fund_{n}y_pct"), annualised(record, f"benchmark_{n}y_pct")
        if f is not None and b is not None and abs(f - b) > TRACKING_TOL:
            flags.append((f"fund_{n}y_pct", f"{abs(f - b):.1f} pts away from benchmark"))

    numbers = {k: record.get(k) for k in ["ter_pct", "fund_aum_m"] + PERF_FIELDS}
    for k, v in numbers.items():
        if v is None:
            continue
        found = contexts(text, v)
        if k == "fund_aum_m" and not found:
            found = contexts(text, v / 1000)
        if not found:
            flags.append((k, "number not found in text"))
        elif k == "fund_aum_m" and all("share class" in c for c in found):
            flags.append((k, "looks like share class assets"))

    weights = [h["weight_pct"] for h in record.get("top_holdings", [])]
    if weights != sorted(weights, reverse=True):
        flags.append(("top_holdings", "not in descending order"))
    if any(not contexts(text, w) for w in weights):
        flags.append(("top_holdings", "weight not found in text"))

    return flags


def peer_flags(records: dict[str, dict], clusters: dict[str, str]) -> list[tuple[str, str, str]]:
    flags = []
    for field in PERF_FIELDS:
        groups: dict[str, dict[str, float]] = {}
        for isin, record in records.items():
            value = annualised(record, field)
            if value is not None:
                groups.setdefault(clusters[isin], {})[isin] = value
        for values in groups.values():
            if len(values) < 3:
                continue
            mid = median(values.values())
            for isin, value in values.items():
                if abs(value - mid) > PEER_TOL:
                    flags.append((isin, field, f"{value - mid:+.1f} pts from peer median"))
                    if records[isin].get("multi_year_annualised") is False and not field.endswith("1y_pct"):
                        flags.append((isin, "multi_year_annualised", "converted value is off peers"))
    return flags
