import json
from pathlib import Path

import pandas as pd

from factsheet.validate import ISIN_COUNTRY, annualised

PERIODS = (1, 3, 5)


def load_run(run_dir, manifest="data/manifest.csv") -> pd.DataFrame:
    """Extracted factsheets as one table. Flagged values are dropped, returns are annualised."""
    run_dir = Path(run_dir)
    records = {p.stem: json.loads(p.read_text()) for p in run_dir.glob("*.json") if not p.stem.endswith(".raw")}

    flags_path = run_dir / "flags.csv"
    flags = pd.read_csv(flags_path) if flags_path.exists() else pd.DataFrame(columns=["isin", "field"])
    for isin, field in zip(flags["isin"], flags["field"]):
        if field == "multi_year_annualised":
            for who in ("fund", "benchmark"):
                for n in (3, 5):
                    records[isin][f"{who}_{n}y_pct"] = None
        elif field == "domicile":
            records[isin]["domicile"] = ISIN_COUNTRY.get(isin[:2])
        else:
            records[isin][field] = [] if field == "top_holdings" else None

    rows = []
    for isin, r in records.items():
        row = {k: v for k, v in r.items() if k != "top_holdings"}
        for who in ("fund", "benchmark"):
            for n in PERIODS:
                row[f"{who}_{n}y_ann"] = annualised(r, f"{who}_{n}y_pct")
        for n in PERIODS:
            f, b = row[f"fund_{n}y_ann"], row[f"benchmark_{n}y_ann"]
            row[f"td_{n}y"] = f - b if f is not None and b is not None else None
        weights = [h["weight_pct"] for h in r.get("top_holdings", [])]
        row["top3_weight"] = sum(weights) if len(weights) == 3 else None
        for i, h in enumerate(r.get("top_holdings", [])[:3], 1):
            row[f"holding_{i}"] = h["name"]
            row[f"weight_{i}"] = h["weight_pct"]
        row["n_flags"] = int((flags["isin"] == isin).sum())
        rows.append(row)

    df = pd.DataFrame(rows)
    man = pd.read_csv(manifest)[["isin", "ticker", "index_cluster", "share_class"]]
    return man.merge(df, on="isin", how="inner")
