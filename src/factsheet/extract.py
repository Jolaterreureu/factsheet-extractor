import json
import os

import pdfplumber
from ollama import chat

from factsheet.schema import Factsheet

MODEL = os.environ.get("FACTSHEET_MODEL", "qwen3.5:9b")

RULES = """You extract data from ETF factsheets into JSON.

Rules:
- Only use information printed in the factsheet. If a field is not there, return null.
- Percentages as plain numbers: 0.20 for 0.20%.
- Dates as YYYY-MM-DD.
- ter_pct: the total ongoing cost (TER, OCF, all-in fee, flat fee).
- fund_aum_m: total fund assets (not share class assets, not number of shares) in millions.
- Performance: 1, 3 and 5 year returns as printed, do not convert. multi_year_annualised is true if
  the 3y/5y figures are annualised (% p.a.), false if they are cumulative.
- top_holdings: the 3 largest holdings with their weights, largest first.
"""

SCHEMA = json.dumps(Factsheet.model_json_schema(), indent=2)

PROMPTS = {
    "v1": RULES,
    "v2": RULES + "\nReturn JSON following this schema. Use the field descriptions and allowed values:\n" + SCHEMA,
}


def pdf_text(path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def extract(text: str, model: str = MODEL, prompt: str = "v2", think: bool = False) -> str:
    response = chat(
        model=model,
        messages=[
            {"role": "system", "content": PROMPTS[prompt]},
            {"role": "user", "content": text},
        ],
        format=Factsheet.model_json_schema(),
        options={"temperature": 0, "num_ctx": 16384},
        think=think,
    )
    return response.message.content
