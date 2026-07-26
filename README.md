# Chicago Food Inspection Outcomes in Three ZIP Codes, 2010–2018

[![Notebook validation](https://github.com/Jnapier2/chicago-food-inspections-analysis/actions/workflows/notebook.yml/badge.svg)](https://github.com/Jnapier2/chicago-food-inspections-analysis/actions/workflows/notebook.yml)

[Portfolio](https://jerry-napier-portfolio.netlify.app/) · [GitHub profile](https://github.com/Jnapier2)

## Abstract

This descriptive study compares recorded food-inspection outcomes and facility-risk classifications in Chicago ZIP codes 60607, 60610, and 60622 from January 5, 2010, through June 13, 2018. Across 13,333 inspection records, 60622 has the highest recorded failure share, while 60607 has the highest share classified as `Risk 1 (High)`. The divergence within this extract shows why outcome and facility-risk measures should be evaluated separately when framing follow-up analysis. Each row represents an inspection, not a unique establishment.

This analysis originated as a 2018 course project. The 2026 revision updates the documentation and reproducibility workflow while retaining the original study period and descriptive scope. The original notebook reported 12,971 records. The bundled extract, retrieved from the same public dataset on July 19, 2026, contains 13,333 records for that period. The City dataset can be revised after publication, and the original CSV is no longer available, so the source of that difference cannot be established from the surviving files.

## Research questions

1. How are inspection outcomes distributed within each selected ZIP code?
2. What share of inspections in each ZIP code carries each recognized facility-risk classification?
3. How did the recorded failure share vary by year within the study period?

The questions are descriptive. They do not support a ranking of restaurant safety or a causal interpretation.

## Data and provenance

The source is the City of Chicago's [Food Inspections dataset](https://data.cityofchicago.org/Health-Human-Services/Food-Inspections/4ijn-s7e5), maintained by the Chicago Department of Public Health. The repository includes a compressed, analysis-specific snapshot so the notebook can run without network access. The exact query, selected fields, validation checks, and refresh procedure are documented in [`data/README.md`](data/README.md).

The snapshot retains only these fields:

- inspection identifier;
- facility type and risk classification;
- ZIP code;
- inspection date and type; and
- recorded result.

The City of Chicago's terms apply to the source data. No separate license is asserted here for the data.

## Methods

- The unit of analysis is an inspection record. An establishment may appear more than once.
- Outcome shares use all inspection records in a ZIP code as the denominator, including statuses other than `Pass`, `Fail`, and `Pass w/ Conditions`.
- Risk shares use records classified as `Risk 1 (High)`, `Risk 2 (Medium)`, or `Risk 3 (Low)` as the denominator. Unclassified values are reported separately and excluded from those percentages.
- Annual failure share is the number of `Fail` records divided by all inspection records in the same ZIP code and calendar year.
- Study scope and category order are centralized in one visible notebook parameter block (`ZIP_CODES`, `EXPECTED_ROWS`, `START_DATE`, `END_DATE`, `RISK_ORDER`, and `RESULT_ORDER`) so changes to the analytical frame are explicit and reviewable.
- Inspection identifiers, dates, ZIP-code scope, category coverage, missingness, and percentage totals are checked before results are produced.

## Results

The executed notebook is the authoritative record of the calculations. The principal results from the bundled snapshot are:

| ZIP code | Inspections | Pass | Fail | Pass with conditions | Risk 1 among classified records |
|---|---:|---:|---:|---:|---:|
| 60607 | 4,442 | 60.15% | 20.53% | 10.47% | 82.70% |
| 60610 | 3,553 | 54.35% | 18.77% | 14.89% | 81.48% |
| 60622 | 5,338 | 57.76% | 21.54% | 8.77% | 76.85% |

The leading ZIP differs by measure: 60622 has the highest recorded failure share, while 60607 has the highest share of inspections classified as `Risk 1 (High)`. For program managers, that divergence is the central finding because inspection outcome and facility-risk classification answer different questions. The results can focus the next analytical review, but they are not a basis for ranking ZIP codes or allocating resources without establishment-level linkage and adjustment for inspection type, repeat visits, and risk-based inspection frequency.

## Limitations

- Inspections are repeated observations, and facilities are not sampled at equal rates.
- The City notes that duplicate inspection reports may remain in the public dataset; this snapshot has unique inspection identifiers, but the analysis does not attempt establishment-level deduplication across separate inspection records.
- Inspection frequency depends partly on facility risk and inspection history.
- Inspection-type composition differs across place and time.
- The selected ZIP codes reflect the scope of the original course project and are not representative of Chicago as a whole.
- Historical records may be corrected or added by the source agency after the initial extract.
- The study period ends before the City's July 1, 2018 change in food-inspection procedures.

## Reproducibility

The notebook is tested with Python 3.12. Its exact dependency pins were reviewed on July 26, 2026 and intentionally remain within the validated major-version lines. CI installs binary distributions only, checks the resolved environment with `pip check`, runs the offline retrieval tests, and then executes the notebook from the bundled snapshot.

```bash
python -m venv .venv
python -m pip install --only-binary=:all: -r requirements.txt
python -m pip check
python -m jupyter nbconvert --execute --to notebook --inplace notebooks/chicago_food_inspections.ipynb
```

To refresh the snapshot from the official API:

```bash
python scripts/fetch_data.py
```

A refresh may change the record count or calculated shares if the City has revised historical records. Commit a refreshed snapshot only with an updated retrieval date, checksum, and executed notebook.

## Repository structure

- `notebooks/chicago_food_inspections.ipynb` — methods, checks, results, figures, and interpretation;
- `data/food_inspections_2010_2018.csv.gz` — bounded source snapshot used by the notebook;
- `data/README.md` — provenance, query definition, and integrity metadata;
- `scripts/fetch_data.py` — deterministic retrieval and validation;
- `tests/test_fetch_data.py` — offline query and date-boundary regression tests; and
- `.github/workflows/notebook.yml` — clean-environment contract tests and notebook execution.

## Citation and acknowledgment

Napier, Jerry R. *Chicago Food Inspection Outcomes in Three ZIP Codes, 2010–2018*. Revised 2026.

Source data: City of Chicago, Chicago Department of Public Health, *Food Inspections*, dataset `4ijn-s7e5`.

## Rights and data licensing

Copyright © 2026 Gateway Information Group LLC. All rights reserved. See [LICENSE.md](LICENSE.md) for terms covering the original notebook, retrieval script, documentation, and other original work.

The bundled data snapshot is excluded from that notice and remains subject to the City of Chicago source terms described above.
