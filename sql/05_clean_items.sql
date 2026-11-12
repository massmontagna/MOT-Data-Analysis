-- Items typed and limited to tests in test_result_clean.
CREATE OR REPLACE TABLE test_item_clean AS
SELECT TRY_CAST(test_id AS BIGINT)      AS test_id,
       TRY_CAST(rfr_id AS INTEGER)      AS rfr_id,
       rfr_type_code,
       TRY_CAST(location_id AS INTEGER) AS location_id,
       dangerous_mark
FROM items_dedup
WHERE TRY_CAST(test_id AS BIGINT) IN (SELECT test_id FROM test_result_clean);
