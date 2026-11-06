"""Reference run with a hosted model (Gemini API), same prompt and inputs as the local model.

Needs a Gemini API key from Google AI Studio in the environment: export GEMINI_API_KEY=...
"""

import argparse
import csv
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from factsheet.extract import PROMPTS
from factsheet.pdf import IMAGE_PAGES, page_images, pdf_text
from factsheet.schema import Factsheet

parser = argparse.ArgumentParser()
parser.add_argument("--model", help="exact model name, see --list-models")
parser.add_argument("--holdout", action="store_true")
parser.add_argument("--only")
parser.add_argument("--list-models", action="store_true")
parser.add_argument("--pause", type=float, default=4, help="seconds between requests")
parser.add_argument("--plain", action="store_true", help="no system instruction / JSON mode (for models that do not support them)")
args = parser.parse_args()

client = genai.Client()
if not args.model and not args.list_models:
    parser.error("--model is required (see --list-models)")

if args.list_models:
    for m in client.models.list():
        if "generateContent" in (m.supported_actions or []):
            print(m.name)
    raise SystemExit

if args.only:
    isins = [args.only]
elif args.holdout:
    isins = [r["isin"] for r in csv.DictReader(open("data/holdout.csv"))]
else:
    isins = sorted(p.stem for p in Path("ground_truth").glob("*.json"))

out_dir = Path("results") / (f"{args.model}-v2-both" + ("-holdout" if args.holdout else ""))
out_dir.mkdir(parents=True, exist_ok=True)

if args.plain:
    config = types.GenerateContentConfig(temperature=0)
else:
    config = types.GenerateContentConfig(
        system_instruction=PROMPTS["v2"],
        response_mime_type="application/json",
        response_json_schema=Factsheet.model_json_schema(),
        temperature=0,
    )


def call(contents):
    for attempt in range(5):
        try:
            return client.models.generate_content(model=args.model, contents=contents, config=config)
        except errors.APIError as e:
            if e.code not in (429, 500, 503) or attempt == 4:
                raise
            wait = 30 * (attempt + 1)
            print(f"    {e.code}, waiting {wait}s")
            time.sleep(wait)


log = []
for i, isin in enumerate(isins, 1):
    if (out_dir / f"{isin}.json").exists():
        print(f"[{i}/{len(isins)}] {isin}  already done, skipping")
        continue
    pdf_path = f"data/pdfs/{isin}.pdf"
    contents = [pdf_text(pdf_path, max_pages=IMAGE_PAGES)]
    if args.plain:
        contents.insert(0, PROMPTS["v2"] + "\nAnswer with the JSON object only.\n\nFactsheet:")
    contents += [types.Part.from_bytes(data=img, mime_type="image/png") for img in page_images(pdf_path)]

    start = time.time()
    try:
        response = call(contents)
    except errors.APIError as e:
        print(f"[{i}/{len(isins)}] {isin}  API error {e.code}, skipped (run again later to retry)")
        continue
    seconds = round(time.time() - start, 1)
    raw = response.text or ""
    if "{" in raw:
        raw = raw[raw.find("{"):raw.rfind("}") + 1]

    try:
        result = Factsheet.model_validate_json(raw)
        (out_dir / f"{isin}.json").write_text(result.model_dump_json(indent=2) + "\n")
        status = "ok"
    except ValidationError as e:
        (out_dir / f"{isin}.raw.json").write_text(raw)
        status = f"invalid ({e.error_count()} errors)"

    usage = response.usage_metadata
    print(f"[{i}/{len(isins)}] {isin}  {status}  {seconds}s  ({usage.prompt_token_count} + {usage.candidates_token_count} tokens)")
    log.append({
        "isin": isin,
        "status": status,
        "seconds": seconds,
        "prompt_tokens": usage.prompt_token_count,
        "output_tokens": usage.candidates_token_count,
        "thinking_tokens": usage.thoughts_token_count,
    })
    time.sleep(args.pause)

if log:
    runs_path = out_dir / "runs.csv"
    new_file = not runs_path.exists()
    with open(runs_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=log[0].keys())
        if new_file:
            writer.writeheader()
        writer.writerows(log)

done = sum((out_dir / f"{isin}.json").exists() for isin in isins)
print(f"\n{done}/{len(isins)} factsheets done")
if done < len(isins):
    raise SystemExit("some factsheets failed, run the same command again later to finish them")
