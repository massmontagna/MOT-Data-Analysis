"""Rebuild the DuckDB database from the raw CSV files.

    python src/load_db.py                                  # full data in data/raw -> data/mot.duckdb
    python src/load_db.py --raw data/sample --db data/sample.duckdb

Runs the SQL files in sql/ in order, then prints the reconciliation counts to compare
with docs/instructions.md section 11.
"""
import argparse
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "sql"

RESULTS_DIR = "MOT testing data results (2024)"
ITEMS_DIR = "MOT Testing data failure item (2024)"
LOOKUPS = {
    "dft_item_detail_extract.csv": "lookup_item_detail",
    "dft_item_group_extract.csv": "lookup_item_group",
    "dft_mdr_fuel_type_extract.csv": "lookup_fuel_type",
    "dft_mdr_rfr_location_extract.csv": "lookup_location",
    "dft_mdr_test_outcome_extract.csv": "lookup_test_outcome",
    "dft_mdr_test_type_extract.csv": "lookup_test_type",
}

CHECKS = {
    "results_dedup rows": "SELECT COUNT(*) FROM results_dedup",
    "conflicting tests": "SELECT COUNT(*) FROM test_conflicts",
    "test_result_clean rows": "SELECT COUNT(*) FROM test_result_clean",
    "distinct tests in clean": "SELECT COUNT(DISTINCT test_id) FROM test_result_clean",
    "missing mileage": "SELECT COUNT(*) FROM test_result_clean WHERE test_mileage IS NULL",
    "missing vehicle age": "SELECT COUNT(*) FROM test_result_clean WHERE vehicle_age_years IS NULL",
    "items_dedup rows": "SELECT COUNT(*) FROM items_dedup",
    "test_item_clean rows": "SELECT COUNT(*) FROM test_item_clean",
    "labelled items without description": "SELECT COUNT(*) FROM test_item_labelled WHERE rfr_deficiency_category IS NULL",
    "tests in analysis_scope": "SELECT COUNT(*) FROM analysis_scope",
    "initial fail rate in scope (%)": "SELECT ROUND(100 * AVG(is_initial_fail::INT), 1) FROM analysis_scope",
}


def run_sql(con, name, **params):
    """Run one file from sql/, filling in {placeholders}."""
    con.execute((SQL / name).read_text().format(**params))


def csv_files(folder):
    files = sorted(folder.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files in {folder}. Run src/download_data.py first.")
    return files


def step(label, fn):
    start = time.time()
    fn()
    print(f"{label} ({time.time() - start:.0f}s)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", default=ROOT / "data" / "raw", type=Path, help="folder with the unzipped downloads")
    parser.add_argument("--db", default=ROOT / "data" / "mot.duckdb", type=Path, help="database file to (re)build")
    args = parser.parse_args()

    results = csv_files(args.raw / RESULTS_DIR)
    items = csv_files(args.raw / ITEMS_DIR)
    for f in LOOKUPS:
        if not (args.raw / "lookup" / f).exists():
            raise SystemExit(f"Missing lookup file {args.raw / 'lookup' / f}")

    con = duckdb.connect(str(args.db))
    run_sql(con, "01_create_load_tables.sql")
    for f in results:
        step(f"loaded {f.name}", lambda: run_sql(con, "02_load_results_file.sql", path=f.as_posix()))
    step("built test_conflicts and test_result_clean", lambda: run_sql(con, "03_clean_results.sql"))
    for f in items:
        step(f"loaded {f.name}", lambda: run_sql(con, "04_load_items_file.sql", path=f.as_posix()))
    step("built test_item_clean", lambda: run_sql(con, "05_clean_items.sql"))
    for f, table in LOOKUPS.items():
        run_sql(con, "06_load_lookup.sql", table=table, path=(args.raw / "lookup" / f).as_posix())
    print("loaded lookup tables")
    step("built test_item_labelled", lambda: run_sql(con, "07_label_items.sql"))
    step("built analysis_scope and scope_test_category", lambda: run_sql(con, "08_analysis_tables.sql"))

    print("\nReconciliation (compare with docs/instructions.md section 11):")
    for label, query in CHECKS.items():
        print(f"  {label:<38} {con.sql(query).fetchall()[0][0]:>14,}")
    con.close()


if __name__ == "__main__":
    main()
