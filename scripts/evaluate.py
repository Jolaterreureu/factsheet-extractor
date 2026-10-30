import argparse
import json
from pathlib import Path

import pandas as pd

from factsheet.evaluate import outcome

parser = argparse.ArgumentParser()
parser.add_argument("run", nargs="?", default="qwen3.5-9b-v2", help="folder name in results/")
args = parser.parse_args()
run_dir = Path("results") / args.run

rows = []
for truth_path in sorted(Path("ground_truth").glob("*.json")):
    truth = json.loads(truth_path.read_text())
    pred_path = run_dir / truth_path.name
    pred = json.loads(pred_path.read_text()) if pred_path.exists() else {}
    for field, true_value in truth.items():
        rows.append({
            "isin": truth_path.stem,
            "issuer": truth["issuer"],
            "field": field,
            "truth": true_value,
            "pred": pred.get(field),
            "outcome": outcome(field, pred.get(field), true_value),
        })

df = pd.DataFrame(rows)
df.to_csv(run_dir / "eval.csv", index=False)
df["correct"] = df["outcome"] == "correct"

by_field = pd.crosstab(df["field"], df["outcome"])
by_field["accuracy"] = df.groupby("field")["correct"].mean().round(2)
print(by_field.sort_values("accuracy").to_string(), "\n")
print(df.groupby("issuer")["correct"].mean().round(2).to_string(), "\n")
print(df["outcome"].value_counts().to_string(), "\n")
print(f"overall accuracy: {df['correct'].mean():.1%} ({df['correct'].sum()}/{len(df)} fields)")

by_field.to_csv(run_dir / "by_field.csv")

counts = df["outcome"].value_counts()
runs = pd.read_csv(run_dir / "runs.csv") if (run_dir / "runs.csv").exists() else None
row = {
    "run": args.run,
    "accuracy": round(df["correct"].mean(), 3),
    "missed": counts.get("missed", 0),
    "wrong": counts.get("wrong", 0),
    "hallucinated": counts.get("hallucinated", 0),
    "avg_seconds": round(runs["seconds"].mean(), 1) if runs is not None else None,
}
summary_path = Path("results/summary.csv")
summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
if not summary.empty:
    summary = summary[summary["run"] != args.run]
summary = pd.concat([summary, pd.DataFrame([row])], ignore_index=True)
summary.to_csv(summary_path, index=False)
print(f"saved to {summary_path}")
