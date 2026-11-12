-- Tests that still have more than one row after normalising are excluded (data dictionary 7.3).
CREATE OR REPLACE TABLE test_conflicts AS
SELECT test_id, COUNT(*) AS versions
FROM results_dedup
GROUP BY test_id
HAVING COUNT(*) > 1;

-- Typed, one row per test, cleaning rules from data dictionary 7.5.
CREATE OR REPLACE TABLE test_result_clean AS
WITH typed AS (
    SELECT *,
           TRY_CAST(test_date AS DATE)                          AS test_date_d,
           TRY_CAST(TRY_CAST(test_mileage AS DOUBLE) AS BIGINT) AS mileage_num
    FROM results_dedup
    WHERE test_id NOT IN (SELECT test_id FROM test_conflicts)
)
SELECT
    TRY_CAST(test_id AS BIGINT)                          AS test_id,
    TRY_CAST(vehicle_id AS BIGINT)                       AS vehicle_id,
    test_date_d                                          AS test_date,
    test_class_id,
    test_type,
    test_result,
    CASE WHEN test_result IN ('P', 'F', 'PRS')
         THEN test_result IN ('F', 'PRS') END            AS is_initial_fail,
    CASE WHEN mileage_num >= 100
          AND mileage_num NOT IN (248601, 999999)
         THEN mileage_num END                            AS test_mileage,
    NULLIF(postcode_area, 'XX')                          AS postcode_area,
    UPPER(TRIM(make))                                    AS make,
    UPPER(TRIM(model))                                   AS model,
    (UPPER(TRIM(make)) = 'UNCLASSIFIED'
     OR UPPER(TRIM(model)) = 'UNCLASSIFIED')             AS is_unclassified,
    fuel_type,
    CASE fuel_type
        WHEN 'PE' THEN 'Petrol'
        WHEN 'DI' THEN 'Diesel'
        WHEN 'HY' THEN 'Hybrid'
        WHEN 'EL' THEN 'Electric'
        WHEN 'ED' THEN 'Electric Diesel'
        WHEN 'LP' THEN 'LPG'
        WHEN 'GB' THEN 'Gas Bi-Fuel'
        WHEN 'GA' THEN 'Gas'
        WHEN 'GD' THEN 'Gas Diesel'
        WHEN 'FC' THEN 'Fuel Cell'
        WHEN 'CN' THEN 'CNG'
        WHEN 'LN' THEN 'LNG'
        WHEN 'ST' THEN 'Steam'
        ELSE 'Other'
    END                                                  AS fuel_type_desc,
    TRY_CAST(cylinder_capacity AS INTEGER)               AS cylinder_capacity,
    NULLIF(first_use_year, 1971)                         AS first_use_year,
    CASE WHEN first_use_year <> 1971
          AND first_use_year <= YEAR(test_date_d)
         THEN YEAR(test_date_d) - first_use_year
    END                                                  AS vehicle_age_years
FROM typed;
