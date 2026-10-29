# factsheet-extractor

Extracting fund data from ETF factsheets (PDF) with a local LLM via Ollama, and checking how accurate it is against hand-labelled data.

39 UCITS ETFs from iShares, Vanguard, Xtrackers, Amundi and UBS, listed in `data/manifest.csv`. Factsheets are as of end of September 2026. PDFs are not in the repo, put them in `data/pdfs/` named `<ISIN>.pdf`.

## Setup

```
uv sync
ollama pull qwen3.5:9b
uv run python scripts/check_setup.py
```

WIP
