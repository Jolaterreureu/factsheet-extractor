# factsheet-extractor

Extracting structured data from ETF factsheets (PDF) with a small LLM that runs locally on a laptop, and measuring how accurate it is against hand-labelled data.

The model (`qwen3.5:9b` via Ollama) runs on a MacBook Air (M5, 16 GB). No document leaves the machine, which matters for anyone who wants to do this with non-public documents.

## Results

Accuracy = share of fields that match the hand labels (22 fields per factsheet, a correctly returned "not in the document" counts as correct).

| Setup | Tuning set (20 factsheets) | Held-out (5) |
|---|---|---|
| Baseline: text, short prompt | 52.7% | |
| + JSON schema in the prompt (v2) | 84.3% | |
| + page images (text + images) | **91.6%** | **91.8%** |
| + human review of flagged fields | 97.5% | 97.3% |

The held-out funds were chosen and labelled before the final setup was picked, and were not used for tuning.

Validation checks flag 7.3% of all fields (about 1.6 per factsheet) and catch 70% of the remaining errors. Of the fields that are not flagged, 97.3% are correct.

Reference models with the same prompt and inputs, through the Gemini API:

| Model | Tuning set | Held-out |
|---|---|---|
| qwen3.5:9b (local, open, 9B) | 91.6% | 91.8% |
| gemma-4-31b-it (open, 31B) | 94.8% | 94.5% |
| gemini-3.8-flash (closed) | 99.8% | 98.2% |

Gemini 3.8 Flash only gets benchmark names slightly different from the labels (e.g. "Euro-Aggregate" vs "Euro Aggregate"). Note that it reasons before answering by default (~900 "thinking" tokens per factsheet), the local runs do not.

## Data

- 39 UCITS ETFs from iShares, Vanguard, Xtrackers, Amundi and UBS, grouped by index: MSCI World, S&P 500, Emerging Markets, Europe, EUR government bonds (`data/manifest.csv`, with the source URL of each factsheet).
- English factsheets as of 30 September 2026 (two UBS factsheets are as of end of August).
- PDFs are not in the repo. Put them in `data/pdfs/` named `<ISIN>.pdf`.
- `ground_truth/`: 20 factsheets labelled by hand, labelling rules and edge cases in `ground_truth/README.md`.
- `holdout/`: 5 more labelled factsheets, list fixed in `data/holdout.csv` before tuning.

## How it works

1. `src/factsheet/schema.py`: Pydantic model with the 22 fields (identity, costs, size, SRI, 1/3/5y returns of fund and benchmark, top 3 holdings).
2. `src/factsheet/pdf.py`: text of the PDF (pdfplumber) and images of the first 3 pages.
3. `src/factsheet/extract.py`: prompt + text + images to the local model, output constrained to the schema.
4. `scripts/evaluate.py`: field by field comparison with the labels (numbers within rounding, null handling, results in `results/summary.csv`).
5. `src/factsheet/validate.py`: checks that need no labels: ISIN check digit, domicile vs ISIN prefix, dates, numbers must appear in the PDF text, fund vs share class assets, returns compared to funds tracking the same index.
6. `notebooks/analysis.ipynb`: analysis of the extracted data for all 39 funds.

## What worked and what did not

All runs on the 20 tuning factsheets:

| Experiment | Accuracy | Comment |
|---|---|---|
| v1 baseline | 52.7% | mostly fields returned empty, the model did not see the field descriptions |
| v2: schema in the prompt | 84.3% | Ollama's `format` constrains the output, but apparently does not show the field descriptions to the model |
| v3: more detailed rules | 85.2% | no real gain, twice as slow |
| v3 + layout-preserving text | 85.0% | no gain |
| v3 + thinking mode | 79.3% | no gain on the factsheets that worked, ~5 min per factsheet, empty output on the 3 longest (likely the context window) |
| v2 + images only | 86.8% | fixes tables, but misreads characters (5 ISINs wrong) |
| v2 + text and images | 91.6% | exact characters from the text, layout from the image |

Most remaining errors are in performance tables:

- Vanguard prints "Year to date" over two lines. In extracted text the header is shifted by one column and every text-only run took YTD as the 1y return. Images fixed this.
- UBS factsheets have no 1y and 3y returns. All models except Gemini Flash filled them with other numbers from the table (a calendar year or YTD return). These look plausible and are hard to catch.
- Fund assets vs share class assets: two numbers next to each other on most factsheets.

The labels had errors too: about a dozen were corrected over the project (typos, share class instead of fund assets, a fund date definition for Amundi). Every run was re-scored after each correction.

9 of the 23 Gemma errors are a convention issue: it reported cumulative 5y returns for UBS and marked them as cumulative, the labels use the annualised figure.

## Analysis of the extracted data

From `notebooks/analysis.ipynb` (flagged values dropped):

- Bond ETFs trail their index by about their TER. Equity ETFs often beat their (net) index despite fees, most in Europe (other effects add about 0.38% p.a., more than the fee), likely through withholding tax treatment and securities lending.
- Within equity funds, higher TER goes with lower tracking difference (correlation -0.75). iShares MSCI World Dist costs 0.30% more than iShares Core MSCI World and its 5y tracking difference is 0.34% lower.
- The S&P 500 swap ETF from Amundi has the highest tracking difference in its group (swap ETFs avoid US dividend withholding tax). Only two swap funds, so an observation, not a result.
- FTSE and MSCI emerging market funds hold different portfolios: Samsung and SK Hynix are in the MSCI top 3 but not in the FTSE index (FTSE treats South Korea as developed). The FTSE funds lagged by about 2.3% p.a. over 5 years.
- Top 3 holdings: 28.8% of EM funds, 21.5% of S&P 500, 15.1% of MSCI World, 9.6% of European funds (median).

## Limitations

- 39 funds and one factsheet date. 25 labelled factsheets, 5 of them held-out: the held-out accuracy has an uncertainty of several points.
- The validation checks and thresholds were designed while looking at the local model's errors. They catch its error types better than those of other models (17% of Gemma's errors).
- The peer check groups funds by index family. It flags correct values when FTSE and MSCI or USD and EUR funds are in the same group.
- Gemini runs used the free tier. Times are not comparable (rate limits and server load), and the free tier may use the inputs to improve Google products, fine for public factsheets, not for confidential documents.
- The factsheets themselves were not checked against other sources.

## Future work

- Run a larger mixture-of-experts model fully locally on the same 16 GB machine, e.g. Qwen3.6-35B-A3B with the [Colibri](https://github.com/JustVugg/colibri) engine (streams inactive experts from the SSD), to see the accuracy/speed trade-off without a hosted API.
- Group peers by exact benchmark and currency in the validation.
- More factsheet dates to track funds over time.

## Setup

Python 3.12, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com).

```
uv sync
ollama pull qwen3.5:9b
uv run python scripts/check_setup.py
```

Run and evaluate the final setup:

```
uv run python scripts/run_extraction.py --prompt v2 --input both
uv run python scripts/evaluate.py qwen3.5-9b-v2-both
uv run python scripts/validate.py qwen3.5-9b-v2-both
uv run pytest
```

Reference models (needs a Gemini API key from Google AI Studio):

```
export GEMINI_API_KEY=...
uv run python scripts/run_gemini.py --model gemini-3.8-flash
uv run python scripts/evaluate.py gemini-3.8-flash-v2-both
```
