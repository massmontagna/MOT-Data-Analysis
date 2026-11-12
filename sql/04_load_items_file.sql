-- One monthly item file: drop repeated headers and exact copies. {path} is filled in by src/load_db.py.
INSERT INTO items_dedup BY NAME
SELECT DISTINCT
    test_id,
    rfr_id,
    rfr_type_code,
    mot_test_rfr_location_type_id AS location_id,
    dangerous_mark,
    filename
FROM read_csv('{path}', all_varchar=true, quote='"', escape='\', filename=true)
WHERE test_id <> 'test_id';
