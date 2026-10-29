from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Holding(BaseModel):
    name: str
    weight_pct: float = Field(ge=0, le=100)


class Factsheet(BaseModel):
    # identity
    fund_name: str = Field(description="Full fund name including share class, e.g. 'iShares Core MSCI World UCITS ETF USD (Acc)'")
    isin: str = Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    issuer: str = Field(description="ETF brand, e.g. iShares, Vanguard, Xtrackers, Amundi, UBS")
    as_of_date: date = Field(description="Reference date of the factsheet data (usually month end)")
    currency: str = Field(description="Share class currency, 3-letter code")
    domicile: str | None = None
    inception_date: date | None = Field(default=None, description="Share class launch date")
    benchmark: str | None = Field(default=None, description="Name of the index the fund tracks")
    replication: Literal["physical", "synthetic"] | None = None
    distribution: Literal["accumulating", "distributing"] | None = None

    # costs and size
    ter_pct: float | None = Field(default=None, ge=0, le=5, description="TER / OCF / all-in fee in percent, e.g. 0.20 for 0.20%")
    fund_aum_m: float | None = Field(default=None, ge=0, description="Total fund assets in millions")
    aum_currency: str | None = None
    sri: int | None = Field(default=None, ge=1, le=7, description="Summary risk indicator, 1 to 7")

    # performance in percent, as reported in the factsheet
    fund_1y_pct: float | None = None
    fund_3y_pct: float | None = None
    fund_5y_pct: float | None = None
    benchmark_1y_pct: float | None = None
    benchmark_3y_pct: float | None = None
    benchmark_5y_pct: float | None = None
    multi_year_annualised: bool | None = Field(
        default=None,
        description="True if the 3y/5y figures are annualised (% p.a.), False if they are cumulative",
    )

    top_holdings: list[Holding] = Field(default_factory=list, description="Top 10 holdings with weights in percent")
