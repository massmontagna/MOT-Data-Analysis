-- One monthly results file: drop repeated headers, normalise fuel / cc / first-use year,
-- then remove exact copies (data dictionary 7.2-7.4). {path} is filled in by src/load_db.py.
INSERT INTO results_dedup BY NAME
SELECT DISTINCT
    * EXCLUDE (fuel_type, first_use_date, cylinder_capacity, colour, completed_date),
    CASE fuel_type
        WHEN 'Hybrid Electric (Clean)' THEN 'HY'
        WHEN 'Electric' THEN 'EL'
        ELSE fuel_type
    END AS fuel_type,
    NULLIF(NULLIF(cylinder_capacity, '0'), 'NULL') AS cylinder_capacity,
    TRY_CAST(LEFT(first_use_date, 4) AS INTEGER) AS first_use_year
FROM read_csv('{path}', all_varchar=true, quote='"', escape='\', filename=true)
WHERE test_id <> 'test_id';
