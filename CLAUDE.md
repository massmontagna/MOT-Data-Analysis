# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A portfolio data-analysis project on the DVSA anonymised MOT test results for 2024 (~42M tests, ~92M defect/advisory items), using DuckDB SQL from Jupyter notebooks. The owner is a mechanical engineer moving into data analysis and **writes the code themselves to learn it**. Explain and suggest; don't take over whole steps unless asked.

Two docs are the source of truth. Read them before changing anything:
- `docs/instructions.md`: the step-by-step plan, current status table (section 2), expected reconciliation numbers (section 11) and a table of known errors and fixes (section 12).
- `docs/data_dictionary.md`: columns, codes, how the tables relate, and every cleaning decision with its row counts.

## Environment

- Virtual env is `.mot/` (Python 3.14), not `.venv`: `source .mot/bin/activate`, `pip install -r requirements.txt`.
- There is no lint or test suite. The checks are the reconciliation counts.
- `python src/download_data.py` fetches and unzips the raw data into `data/raw/`.
- `python src/load_db.py` rebuilds `data/mot.duckdb` by running `sql/01…08_*.sql` in order, then prints the reconciliation counts. They must match `docs/instructions.md` section 11. `--raw data/sample --db <file>` builds from the small committed sample in seconds, which is the quick way to test a pipeline change.
- Notebooks run top to bottom with the working directory set to `notebooks/`. Paths are relative to it (`../data/mot.duckdb`). Run one headless with `../.mot/bin/jupyter nbconvert --to notebook --execute --inplace 04_analysis.ipynb`. Notebooks 02 and 03 are the step-by-step working; the `sql/` files are the finished pipeline, so a cleaning change goes in both places.

## Data and database

- Raw CSVs live in `data/raw/` (gitignored): `MOT testing data results (2024)/`, `MOT Testing data failure item (2024)/` (capital T), `lookup/`, and the user guide `.odt`.
- Everything is in one DuckDB file, `data/mot.duckdb` (~21 GB, gitignored). DuckDB allows only one writing process, so close other notebook connections (`con.close()`) before opening it from a script or a second kernel.
- Pipeline of tables, built in `02_load_and_clean.ipynb`:
  `results_dedup` (text, deduplicated, normalised) → `test_conflicts` (tests whose rows still disagree, excluded) → `test_result_clean` (typed, one row per test) and `items_dedup` (text) → `test_item_clean` (typed, limited to clean tests). `03_lookups.ipynb` loads `lookup_*` and builds `test_item_labelled` (adds the defect category and the top-level `section_name` via `test_item_set_section_id`). `04_analysis.ipynb` defines the `analysis_scope` view and `scope_test_category`, and writes the charts to `reports/figures/`.

## Conventions that matter

- **Read raw CSVs as text**, with exactly these options: `read_csv(path, all_varchar=true, quote='"', escape='\', filename=true)` inside a Python raw string (`rf"""..."""`), and drop repeated header rows with `WHERE test_id <> 'test_id'`. Let DuckDB detect the delimiter (comma, not pipe). Cast types afterwards with `TRY_CAST`.
- Table-building cells use `CREATE OR REPLACE` so they can be re-run. Monthly load loops `INSERT` into a table, so **re-run the create cell right before the loop** or the data gets loaded twice.
- Use `.fetchall()[0][0]`, not `fetchone()`, for scalar results.
- Every new table gets a reconciliation count against a trusted number (see `docs/instructions.md` section 11). Every cleaning rule is recorded in `docs/data_dictionary.md` with the rows it affects. Update both docs when a step is finished or a new fact is learned.
- Don't trust the user guide over the data. Known differences: `test_id` isn't unique, `dangerous_mark` isn't empty (3,885,070 `D`), and `cylinder_capacity` and other columns contain the text `'NULL'`.
- Analysis scope (applied in queries, not baked into tables): Class 4, `test_type = 'NT'`, `test_result IN ('P','F','PRS')`, and `NOT is_unclassified` for make/model questions. Failure-rate definitions are in data dictionary section 8.
