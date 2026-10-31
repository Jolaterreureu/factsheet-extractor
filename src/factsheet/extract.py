import io
import json
import os
import textwrap

import pdfplumber
from ollama import chat

from factsheet.schema import Factsheet

MODEL = os.environ.get("FACTSHEET_MODEL", "qwen3.5:9b")
IMAGE_PAGES = 3
IMAGE_DPI = 120

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

RULES_V3 = """You extract data from ETF factsheets into JSON.

General:
- Only use information printed in the factsheet. If a field is not there, return null.
  Do not guess, do not calculate, do not use a value that belongs to a different concept or period.
- Percentages as plain numbers: 0.20 for 0.20%. Dates as YYYY-MM-DD.

Fields:
- issuer: the ETF brand (e.g. iShares), not the legal entity or management company.
- inception_date: the share class launch date. If both fund and share class launch dates are given, use the share class one.
- domicile: the country the fund is domiciled in (e.g. "Ireland", or Luxembourg for "SICAV under Luxembourg law").
- distribution: "accumulating" (also called Acc, Accumulation, Capitalizing, Capitalisation, Reinvestment)
  or "distributing" (Dist, Distribution, Distributed, Income).
- replication: "physical" (full, optimised, sampled, direct replication) or "synthetic" (swap based, indirect replication).
- ter_pct: total ongoing cost, called TER, OCF, ongoing charges, all-in fee, flat fee or management fees and other costs.
- fund_aum_m: total assets of the whole fund in millions. Not share class assets, not NAV per share,
  not number of shares outstanding. Convert billions to millions (USD 30.97 billion -> 30970).
- sri: the summary risk indicator (1 to 7) only if the number is written in the text, e.g. in a column "SRI"
  or "classified as 4 out of 7". Otherwise null.

Performance:
- fund_1y_pct, fund_3y_pct, fund_5y_pct are trailing returns over the 1, 3 and 5 years ending at the as-of date,
  from columns labelled like "1 year", "3 years", "5 years". benchmark_* are the same columns in the benchmark/index row.
- Never use YTD, 1 month, 3 months, quarter, since inception or calendar year returns (e.g. "2022"),
  and never use volatility, tracking error or Sharpe ratio. If a period column does not exist, return null.
- Table headers can be split over several lines and rows can contain "-" or "—" for missing periods.
  Match each number to its column header carefully.
- If both a cumulative and an annualised (% p.a.) figure are given for the same period, use the annualised one.
- multi_year_annualised: true if the 3y/5y figures are annualised, false if cumulative, null if there are none.

Holdings:
- top_holdings: the 3 largest positions from the top holdings / largest positions table, names as printed.
  Not sector, country or issuer breakdowns.
"""

SCHEMA = json.dumps(Factsheet.model_json_schema(), indent=2)

PROMPTS = {
    "v1": RULES,
    "v2": RULES + "\nReturn JSON following this schema. Use the field descriptions and allowed values:\n" + SCHEMA,
    "v3": RULES_V3 + "\nReturn JSON following this schema. Use the field descriptions and allowed values:\n" + SCHEMA,
}


def pdf_text(path, layout: bool = False, max_pages: int | None = None) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            text = page.extract_text(layout=layout) or ""
            if layout:
                lines = [line.rstrip() for line in text.splitlines() if line.strip()]
                text = textwrap.dedent("\n".join(lines))
            pages.append(text)
    return "\n\n".join(pages)


def page_images(path, max_pages: int = IMAGE_PAGES, dpi: int = IMAGE_DPI) -> list[bytes]:
    images = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            buffer = io.BytesIO()
            page.to_image(resolution=dpi).original.save(buffer, format="PNG")
            images.append(buffer.getvalue())
    return images


def extract(text: str, model: str = MODEL, prompt: str = "v3", think: bool = False, images=None):
    user = {"role": "user", "content": text or "The factsheet pages are attached as images."}
    if images:
        user["images"] = images
    return chat(
        model=model,
        messages=[{"role": "system", "content": PROMPTS[prompt]}, user],
        format=Factsheet.model_json_schema(),
        options={"temperature": 0, "num_ctx": 16384},
        think=think,
    )
