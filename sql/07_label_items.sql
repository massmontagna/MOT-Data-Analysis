-- Each item gets its defect category and top-level section (data dictionary section 6).
-- The test class comes from the results table; test_item_set_section_id points straight at the top-level group.
CREATE OR REPLACE TABLE test_item_labelled AS
SELECT i.test_id,
       i.rfr_id,
       i.rfr_type_code,
       i.location_id,
       i.dangerous_mark,
       r.test_class_id,
       d.rfr_deficiency_category,
       TRY_CAST(d.test_item_set_section_id AS INTEGER) AS section_id,
       g.item_name                                     AS section_name
FROM test_item_clean i
JOIN test_result_clean r
  ON i.test_id = r.test_id
LEFT JOIN lookup_item_detail d
  ON i.rfr_id = TRY_CAST(d.rfr_id AS INTEGER)
 AND r.test_class_id = d.test_class_id
LEFT JOIN lookup_item_group g
  ON d.test_item_set_section_id = g.test_item_id
 AND d.test_class_id = g.test_class_id;
