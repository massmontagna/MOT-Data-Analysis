-- One lookup file as text. {table} and {path} are filled in by src/load_db.py.
CREATE OR REPLACE TABLE {table} AS
SELECT * FROM read_csv('{path}', all_varchar=true);
