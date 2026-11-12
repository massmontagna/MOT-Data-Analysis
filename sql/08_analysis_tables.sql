-- Analysis scope (data dictionary section 8): Class 4, initial tests, results P / F / PRS.
-- age drops impossible first-use years such as 94 or 1012 (data dictionary 7.8).
CREATE OR REPLACE VIEW analysis_scope AS
SELECT *,
       CASE WHEN first_use_year >= 1900 THEN vehicle_age_years END AS age
FROM test_result_clean
WHERE test_class_id = '4'
  AND test_type = 'NT'
  AND test_result IN ('P', 'F', 'PRS');

-- One row per in-scope test and top-level category with at least one F or P item.
CREATE OR REPLACE TABLE scope_test_category AS
SELECT DISTINCT i.test_id, i.section_name
FROM test_item_labelled i
JOIN analysis_scope s ON i.test_id = s.test_id
WHERE i.rfr_type_code IN ('F', 'P')
  AND i.section_name IS NOT NULL;
