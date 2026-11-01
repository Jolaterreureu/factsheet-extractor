import argparse
import csv
import json
from pathlib import Path

import pandas as pd

from factsheet.pdf import pdf_text
from factsheet.validate import check_record, peer_flags

parser = argparse.ArgumentParser()
parser.add_argument("run", nargs="?", default="qwen3.5-9b-v2-both", help="folder name in results/")
parser.add_argument("--peers", help="other results folder whose funds are used as peers only")
args = parser.parse_args()
run_dir = Path("results") / args.run

clusters = {r["isin"]: r["index_cluster"] for r in csv.DictReader(open("data/manifest.csv"))}
records = {p.stem: json.loads(p.read_text()) for p in sorted(run_dir.glob("*.json")) if not p.stem.endswith(".raw")}

rows = []
for isin, record in records.items():
    text = pdf_text(f"data/pdfs/{isin}.pdf")
    rows += [{"isin": isin, "field": field, "reason": reason} for field, reason in check_record(record, text)]
peers = dict(records)
if args.peers:
    for p in (Path("results") / args.peers).glob("*.json"):
        if not p.stem.endswith(".raw"):
            peers.setdefault(p.stem, json.loads(p.read_text()))
rows += [{"isin": isin, "field": field, "reason": reason}
         for isin, field, reason in peer_flags(peers, clusters) if isin in records]

flags = pd.DataFrame(rows, columns=["isin", "field", "reason"])
flags.to_csv(run_dir / "flags.csv", index=False)
print(f"{len(flags)} flags on {len(records)} factsheets\n")
print(flags["reason"].str.replace(r"[-+]?\d+(\.\d+)?", "#", regex=True).value_counts().to_string(), "\n")

eval_path = run_dir / "eval.csv"
if eval_path.exists():
    ev = pd.read_csv(eval_path)
    flagged = set(zip(flags["isin"], flags["field"]))
    ev["flagged"] = [(i, f) in flagged for i, f in zip(ev["isin"], ev["field"])]
    ev["error"] = ev["outcome"] != "correct"
    caught = (ev["error"] & ev["flagged"]).sum()
    print(f"errors caught: {caught}/{ev['error'].sum()} ({caught / ev['error'].sum():.0%})")
    print(f"false alarms:  {(~ev['error'] & ev['flagged']).sum()}")
    print(f"review load:   {ev['flagged'].mean():.1%} of fields flagged ({ev['flagged'].sum() / ev['isin'].nunique():.1f} per factsheet)")
    print(f"\naccuracy as extracted:          {(~ev['error']).mean():.1%}")
    print(f"accuracy if flags are reviewed: {(~ev['error'] | ev['flagged']).mean():.1%}")
    print(f"accuracy of unflagged fields:   {(~ev.loc[~ev['flagged'], 'error']).mean():.1%}")
    print("\nerrors not caught:")
    print(ev[ev["error"] & ~ev["flagged"]][["isin", "field", "truth", "pred"]].to_string(index=False, max_colwidth=40))
