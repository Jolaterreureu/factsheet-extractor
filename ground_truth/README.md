# Ground truth labels

Hand-labelled values for 20 of the 39 factsheets (4 per issuer). One JSON file per fund, same fields as `src/factsheet/schema.py`.

Labelled by reading the PDF only, before looking at any model output.

## Rules

- Only use what is printed in the factsheet. If a field is not there, leave it `null`, even if the value is known from elsewhere.
- Percentages as printed, without the % sign: `0.20` for 0.20%, `-18.03` for -18.03%.
- Dates as `YYYY-MM-DD`.
- `as_of_date`: the date the performance / portfolio data refers to (usually month end), not the print date.
- `currency`: share class currency.
- `ter_pct`: TER, OCF, all-in fee, flat fee, whatever the issuer calls the total ongoing cost.
- `fund_aum_m`: total fund assets (not share class assets) in millions, in `aum_currency`. "USD 30.97 Billion" becomes `30970`.
- `replication`: `physical` (full or optimised/sampled) or `synthetic` (swap based).
- `distribution`: `accumulating` or `distributing`.
- Performance: 1y, 3y, 5y for fund and benchmark, as printed. If 3y/5y are annualised (% p.a.) set `multi_year_annualised` to `true`, if cumulative `false`. Do not convert.
- `top_holdings`: only the 3 largest, in order, names as printed: `{"name": "NVIDIA", "weight_pct": 5.79}`. Leave `[]` if not listed.
- If something is ambiguous, pick one reading and write it in the notes below.

## Notes

- Xtrackers factsheets (UK and LU editions) have no performance table, only a link to the website. All performance fields are `null` for Xtrackers.
- UBS Core MSCI World and Core S&P 500 factsheets are as of end of August 2026, the others end of September.
- UBS writes "Data as at end-September 2026"; the NAV date on the same page (30.09.2026) is used as `as_of_date`.
- UBS factsheets have no SRI (only in the KID), so `sri` is `null`.
- UBS performance tables have no 1y or 3y column, only calendar years and 5 years (cumulative and "Ø p.a."). Labelled the annualised 5y figure with `multi_year_annualised: true`, 1y/3y `null`.
- UBS top holdings are the index's largest positions ("Index 10 largest equity positions"). Labelled as printed. For swap ETFs (e.g. UBS MSCI EM SF) the fund does not hold these stocks directly.
- iShares shows a 1-7 risk scale as a highlighted box (e.g. 6 for equity funds). This is a different scale than the PRIIPs SRI printed by Vanguard and Amundi (4 for the same kind of fund), so `sri` is not comparable across issuers.
- iShares bond factsheets list "Top issuers" (countries) instead of individual bonds. Labelled these as top holdings.
- Xtrackers prints "Total Shares Outstanding" in millions right below "Total Fund Assets" in billions. Only the second one is `fund_aum_m`.
- Amundi prints both "Share-class inception date" and "Date of the first NAV". The share class was often re-created later (e.g. after the Lyxor merger) while the track record starts at the first NAV. `inception_date` uses the share-class inception date, as defined in the schema.
