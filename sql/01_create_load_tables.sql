-- Empty tables that the monthly files are inserted into (everything as text).
CREATE OR REPLACE TABLE results_dedup (
    test_id           VARCHAR,
    vehicle_id        VARCHAR,
    test_date         VARCHAR,
    test_class_id     VARCHAR,
    test_type         VARCHAR,
    test_result       VARCHAR,
    test_mileage      VARCHAR,
    postcode_area     VARCHAR,
    make              VARCHAR,
    model             VARCHAR,
    fuel_type         VARCHAR,
    cylinder_capacity VARCHAR,
    first_use_year    INTEGER,
    filename          VARCHAR
);

CREATE OR REPLACE TABLE items_dedup (
    test_id        VARCHAR,
    rfr_id         VARCHAR,
    rfr_type_code  VARCHAR,
    location_id    VARCHAR,
    dangerous_mark VARCHAR,
    filename       VARCHAR
);
