"""Quick check that Ollama is running and returns valid structured output."""

import os

from ollama import chat
from pydantic import BaseModel

MODEL = os.environ.get("FACTSHEET_MODEL", "qwen3.5:9b")


class MiniFactsheet(BaseModel):
    fund_name: str
    isin: str
    ter_percent: float


SAMPLE_TEXT = """
iShares Core MSCI World UCITS ETF USD (Acc)
ISIN: IE00B4L5Y983 | Share class currency: USD
Total Expense Ratio: 0.20%
"""

response = chat(
    model=MODEL,
    messages=[
        {"role": "system", "content": "Extract the requested fields from the fund factsheet text."},
        {"role": "user", "content": SAMPLE_TEXT},
    ],
    format=MiniFactsheet.model_json_schema(),
    options={"temperature": 0},
)

result = MiniFactsheet.model_validate_json(response.message.content)
print(MODEL, result)
assert result.isin == "IE00B4L5Y983"
assert abs(result.ter_percent - 0.20) < 1e-9
print("Setup OK")
