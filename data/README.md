# Data provenance

`food_inspections_2010_2018.csv.gz` is a bounded snapshot of the City of Chicago [Food Inspections dataset](https://data.cityofchicago.org/Health-Human-Services/Food-Inspections/4ijn-s7e5), dataset identifier `4ijn-s7e5`.

## Scope

- Retrieved: July 19, 2026
- Unit: one food-inspection record
- ZIP codes: 60607, 60610, and 60622
- Date filter: `inspection_date >= 2010-01-05T00:00:00.000` and `inspection_date < 2018-06-14T00:00:00.000`
- Sort order: `inspection_id`
- Rows: 13,333
- Selected fields: `inspection_id`, `facility_type`, `risk`, `zip`, `inspection_date`, `inspection_type`, `results`
- SHA-256 of the uncompressed CSV: `fa83366082b4605aff809c788b72e8b00e5f33fa585baddf1c40510dea48e4e0`

The date boundary preserves the original project's last observed inspection date. The source may revise historical records; the 2018 notebook reported 12,971 rows, while this snapshot contains 13,333. Because the original CSV is absent, the exact revisions cannot be reconstructed.

The City notes that duplicate inspection reports may remain in the public dataset. This bounded snapshot has unique inspection identifiers, but no establishment-level deduplication is applied across separate inspection records.

## Retrieval

Run the deterministic retrieval script from the repository root:

```bash
python scripts/fetch_data.py
```

The script validates the header, row identifiers, ZIP-code scope, and both date boundaries before replacing the snapshot. Offline regression tests also confirm the exact Socrata query and inclusive-start/exclusive-end behavior. It prints the row count and SHA-256 checksum needed to update this file.

## Refresh validation and failure behavior

The helper now limits a response to 16 MiB before CSV decoding and rejects extra or
missing row fields, malformed quoted records, duplicate identifiers, and timestamps
that introduce a timezone into the study's floating-date comparisons. Existing
selection, ordering, inclusive-start/exclusive-end bounds, and result categories are
unchanged. A socket timeout must be an integer from 1 through 300 seconds; it is not
a guaranteed wall-clock deadline for the whole transfer.

The default snapshot path is relative to the script's repository, not the shell's
working directory. An explicit `--output` remains a user-selected destination.
`--check-only` still performs a live request, but never replaces the local snapshot.
Handled fetch, validation, and write errors return exit code 2. Validation completes
before publication, and failed atomic replacement preserves the previous file.

These changes were tested with synthetic responses only. They do not refresh the
snapshot or re-execute the notebook; the historical rows and checksum above are
retained provenance, not a new data verification. Live-source changes require a
separate, deliberate refresh and review.

Copyright © 2026 Gateway Information Group LLC. All rights reserved.

The City of Chicago's terms apply to the source data. This repository does not grant a separate license for the snapshot.
