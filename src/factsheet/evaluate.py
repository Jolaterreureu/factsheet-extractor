NUMBER_TOL = 0.011
AUM_TOL = 0.005
PREFIX_FIELDS = {"fund_name", "benchmark"}


def normalize(value) -> str:
    text = str(value).lower().replace("(", " ").replace(")", " ")
    return " ".join(text.split())


def is_empty(value) -> bool:
    return value is None or value == []


def same_holding(pred: dict, truth: dict) -> bool:
    same_name = normalize(pred["name"]).split()[0] == normalize(truth["name"]).split()[0]
    return same_name and abs(pred["weight_pct"] - truth["weight_pct"]) <= NUMBER_TOL


def same_value(field: str, pred, truth) -> bool:
    if field == "top_holdings":
        return len(pred) == len(truth) and all(same_holding(p, t) for p, t in zip(pred, truth))
    if isinstance(truth, bool) or isinstance(pred, bool):
        return pred == truth
    if isinstance(truth, (int, float)) and isinstance(pred, (int, float)):
        if field == "fund_aum_m":
            return abs(pred - truth) <= AUM_TOL * abs(truth)
        return abs(pred - truth) <= NUMBER_TOL
    if field in PREFIX_FIELDS:
        p, t = normalize(pred), normalize(truth)
        return p.startswith(t) or t.startswith(p)
    return normalize(pred) == normalize(truth)


def outcome(field: str, pred, truth) -> str:
    if is_empty(truth) and is_empty(pred):
        return "correct"
    if is_empty(pred):
        return "missed"
    if is_empty(truth):
        return "hallucinated"
    return "correct" if same_value(field, pred, truth) else "wrong"
