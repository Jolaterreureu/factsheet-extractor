import argparse
import csv
import time
from pathlib import Path

from pydantic import ValidationError

from factsheet.extract import MODEL, PROMPTS, extract
from factsheet.pdf import IMAGE_PAGES, page_images, pdf_text
from factsheet.schema import Factsheet

parser = argparse.ArgumentParser()
parser.add_argument("--model", default=MODEL)
parser.add_argument("--all", action="store_true", help="all funds in the manifest, not only the labelled ones")
parser.add_argument("--only", help="run a single ISIN")
parser.add_argument("--holdout", action="store_true", help="the 5 held-out funds, saved in a separate folder")
parser.add_argument("--prompt", default="v3", choices=PROMPTS)
parser.add_argument("--input", default="text", choices=["text", "image", "both"])
parser.add_argument("--layout", action="store_true", help="keep the page layout when extracting text")
parser.add_argument("--think", action="store_true", help="let the model reason before answering")
args = parser.parse_args()

if args.only:
    isins = [args.only]
elif args.holdout:
    isins = [r["isin"] for r in csv.DictReader(open("data/holdout.csv"))]
elif args.all:
    isins = [r["isin"] for r in csv.DictReader(open("data/manifest.csv"))]
else:
    isins = sorted(p.stem for p in Path("ground_truth").glob("*.json"))

run_name = f"{args.model.replace(':', '-')}-{args.prompt}" + ("" if args.input == "text" else f"-{args.input}") + ("-layout" if args.layout else "") + ("-think" if args.think else "") + ("-holdout" if args.holdout else "") + ("-all" if args.all else "")
out_dir = Path("results") / run_name
out_dir.mkdir(parents=True, exist_ok=True)

log = []
for i, isin in enumerate(isins, 1):
    pdf_path = f"data/pdfs/{isin}.pdf"
    text, images = "", None
    if args.input == "text":
        text = pdf_text(pdf_path, layout=args.layout)
    if args.input == "both":
        text = pdf_text(pdf_path, layout=args.layout, max_pages=IMAGE_PAGES)
    if args.input in ("image", "both"):
        images = page_images(pdf_path)

    start = time.time()
    response = extract(text, args.model, prompt=args.prompt, think=args.think, images=images)
    seconds = round(time.time() - start, 1)
    raw = response.message.content

    try:
        result = Factsheet.model_validate_json(raw)
        (out_dir / f"{isin}.json").write_text(result.model_dump_json(indent=2) + "\n")
        status = "ok"
    except ValidationError as e:
        (out_dir / f"{isin}.raw.json").write_text(raw)
        status = f"invalid ({e.error_count()} errors)"

    print(f"[{i}/{len(isins)}] {isin}  {status}  {seconds}s  ({response.prompt_eval_count} + {response.eval_count} tokens)")
    log.append({
        "isin": isin,
        "status": status,
        "seconds": seconds,
        "chars": len(text),
        "prompt_tokens": response.prompt_eval_count,
        "output_tokens": response.eval_count,
    })

with open(out_dir / "runs.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=log[0].keys())
    writer.writeheader()
    writer.writerows(log)

ok = sum(r["status"] == "ok" for r in log)
print(f"\n{ok}/{len(log)} valid, avg {sum(r['seconds'] for r in log) / len(log):.0f}s per factsheet")
