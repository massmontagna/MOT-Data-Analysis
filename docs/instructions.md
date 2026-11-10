# MOT analysis project: my step-by-step process

This is my own record of how I'm building this project: what I do, in what order, and why. It covers what I've done so far and what I'm going to do next. If I follow it from top to bottom on a fresh machine, I should end up with the same database and the same numbers.

## 0. What this project is

- **Goal:** a portfolio project for my move into a data analyst role. It should show that I can handle a large, messy, real-world dataset with SQL and Python, and explain what I found.
- **Data:** the DVSA anonymised MOT test results for 2024 (about 42 million tests, 92 million defect and advisory items).
- **Tools:** Python, DuckDB (SQL), pandas, Plotly or matplotlib, scikit-learn, Git and GitHub, VS Code with Jupyter notebooks.
- **My edge:** I'm a mechanical engineer, so I can ask engineering questions of the data (which systems fail as cars age, how failure differs by fuel type) rather than generic ones.
- **Reference document:** `docs/data_dictionary.md` records what the data contains and every cleaning decision. I update it every time I learn something.

## 1. How I work

1. **I go one small piece at a time.** I write the code myself and make sure I understand each line before moving on.
2. **I don't trust the documentation over the data.** The user guide was wrong about several things for 2024, so I check every assumption against the real files.
3. **I load everything as text first,** then convert types deliberately. Nothing should be able to fail because of a bad value.
4. **Every new table gets a reconciliation check:** a count that must match a number I already trust. If it doesn't match, I stop and find out why.
5. **Every cleaning rule is a decision I write down,** with the number of rows it affects, in the data dictionary.
6. **Notebook cells that build a table start with `CREATE OR REPLACE`,** so I can re-run them safely. For loops that insert data, I always re-run the table-creation cell first.
7. **I commit to Git after each finished piece,** with a clear message.

## 2. Where I am

| Step | What | Status |
|---|---|---|
| 1 | Set up the project (repo, folders, environment) | Done |
| 2 | Get the data and write the data dictionary | Done, and kept up to date |
| 3a | Load and clean the results files | Done |
| 3b | Load and clean the item files | Items loaded. Clean item table is next |
| 4 | Lookup tables (turn defect codes into readable categories) | Planned |
| 5 | Analysis in SQL | Planned |
| 6 | Charts | Planned |
| 7 | Modelling | Planned |
| 8 | Scripts, README, portfolio page | Planned |

## 3. Step 1: set up the project (done)

1. Install Python 3.12 or later, Git and VS Code (with the Python and Jupyter extensions). I use my personal machine, not my work laptop.
2. On GitHub, create a **public** repo called `mot-analysis`, with a README, the Python `.gitignore` template and an MIT licence.
3. Clone it and open it:
   ```
   git clone https://github.com/YOUR-USERNAME/mot-analysis.git
   cd mot-analysis
   code .
   ```
4. Create the folders: `data/raw`, `data/processed`, `data/sample`, `sql`, `src`, `notebooks`, `reports/figures`, `docs`.
5. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```
6. Install the packages and record them:
   ```
   pip install pandas duckdb jupyter plotly matplotlib scikit-learn
   pip freeze > requirements.txt
   ```
7. Add these lines to `.gitignore` so the huge files are never committed:
   ```
   data/raw/
   data/processed/
   data/mot.duckdb
   .venv/
   ```
8. Commit and push:
   ```
   git add .
   git commit -m "Set up project structure"
   git push
   ```

## 4. Step 2: get the data and understand it (done)

1. From data.gov.uk ("Anonymised MOT tests and results"), download into `data/raw/`:
   - the 2024 test results (12 monthly files)
   - the 2024 failure items (12 monthly files)
   - the lookup tables
   - the user guide (`.odt`)
2. Unzip everything. The result folders are `MOT testing data results (2024)` and `MOT Testing data failure item (2024)`, plus `lookup`. (Note the capital T in "Testing" in the item folder name.)
3. Read the user guide before touching the data, and note what each column means, the codes, and the known quirks.
4. Write `docs/data_dictionary.md` in my own words.
5. Look at the first rows of each file. I don't open these in Excel, because they're far too big.

## 5. Step 3: load and clean

I work in `notebooks/02_load_and_clean.ipynb`. Cells run top to bottom.

### 5.1 Connect to DuckDB

```python
import duckdb
import os
import time

con = duckdb.connect("../data/mot.duckdb")
```

`duckdb.connect` creates the database file on the first run and reopens it afterwards. `..` goes up one folder from `notebooks/` to the repo root. Later I use `con.sql(...)` to run a query and show the result, and `con.execute(...)` to run commands such as creating tables.

### 5.2 Peek at a file

```python
con.sql("""
    SELECT *
    FROM read_csv('../data/raw/MOT testing data results (2024)/test_result_202401.csv')
    LIMIT 5
""").show()
```

I let DuckDB detect the delimiter. This showed me the files are **comma-separated**, not pipe-separated as the guide says, and that there's an extra `completed_date` column.

### 5.3 Read as text, and define reusable readers

DuckDB's automatic type detection only samples the first 20,480 rows, so it failed on things further down. I fixed that by reading everything as text and telling it the quoting rules. I store the reader in a Python variable so I don't retype it.

```python
RESULTS = r"""read_csv(
    '../data/raw/MOT testing data results (2024)/*.csv',
    all_varchar=true,
    quote='"',
    escape='\',
    filename=true
)"""

JAN = r"""read_csv(
    '../data/raw/MOT testing data results (2024)/test_result_202401.csv',
    all_varchar=true,
    quote='"',
    escape='\'
)"""

ITEM_JAN = r"""read_csv(
    '../data/raw/MOT Testing data failure item (2024)/test_item_202401.csv',
    all_varchar=true,
    quote='"',
    escape='\'
)"""
```

- `all_varchar=true` reads every column as text.
- `quote='"'` is needed because values containing commas are wrapped in double quotes (for example `"IVECO ,MOTORHOME"`).
- `escape='\'` is needed because a quote inside a value is written as `\"` (for example a 12-inch wheel written `12\"`).
- The leading `r` makes it a raw string, so Python keeps the backslash as typed.
- `filename=true` adds a column saying which file each row came from.
- I run queries with an `f` in front of the quotes, so `{RESULTS}` is swapped for this text.

### 5.4 Diagnose the results files

**How many rows, repeated headers and distinct tests across all 12 files?**

```python
con.sql(f"""
    SELECT COUNT(*) AS total_rows,
           COUNT(*) FILTER (WHERE test_id = 'test_id') AS header_rows,
           COUNT(DISTINCT test_id) FILTER (WHERE test_id <> 'test_id') AS distinct_tests
    FROM {RESULTS}
""").show()
```

Result: 66,857,535 rows, 180 of them repeated headers, and 42,598,624 distinct tests. So `test_id` is **not** unique.

**Repeated headers per file** (I haven't run this one yet; I only have the total of 180):

```python
con.sql(f"""
    SELECT filename,
           COUNT(*) AS total_rows,
           COUNT(*) FILTER (WHERE test_id = 'test_id') AS header_rows
    FROM {RESULTS}
    GROUP BY filename
    ORDER BY filename
""").show()
```

**For January: are the repeats exact copies?**

```python
con.sql(f"""
    WITH t AS (
        SELECT * FROM {JAN} WHERE test_id <> 'test_id'
    )
    SELECT COUNT(*) AS data_rows,
           COUNT(DISTINCT test_id) AS distinct_tests,
           (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM t)) AS distinct_full_rows
    FROM t
""").show()
```

Result: 6,140,788 data rows, 3,783,238 distinct tests, 3,848,449 distinct full rows. About 2.29 million rows are exact copies, and about 65,000 extra rows differ in some column.

**How many copies does each test have?**

```python
con.sql(f"""
    WITH t AS (
        SELECT * FROM {JAN} WHERE test_id <> 'test_id'
    )
    SELECT copies, COUNT(*) AS n_tests
    FROM (
        SELECT test_id, COUNT(*) AS copies
        FROM t
        GROUP BY test_id
    )
    GROUP BY copies
    ORDER BY copies
""").show()
```

There's no simple pattern (many tests with 1 copy, then 2, 3, 4, 6, 8 and so on, up to 1,517).

**Is it caused by defect items?** I looked at the worst test and compared its row counts across both files:

```python
con.sql(f"""
    WITH t AS (
        SELECT * FROM {JAN} WHERE test_id <> 'test_id'
    )
    SELECT test_id,
           COUNT(*)                   AS row_count,
           COUNT(DISTINCT vehicle_id) AS vehicles,
           COUNT(DISTINCT make)       AS makes
    FROM t
    GROUP BY test_id
    ORDER BY row_count DESC
    LIMIT 10
""").show()
```

```python
con.sql(f"""
    SELECT COUNT(*) AS total_rows,
           (SELECT COUNT(*) FROM (
                SELECT DISTINCT * FROM {JAN} WHERE test_id = '1586552547'
           )) AS distinct_rows
    FROM {JAN}
    WHERE test_id = '1586552547'
""").show()
```

```python
con.sql(f"""
    SELECT 'results file' AS source, COUNT(*) AS n
    FROM {JAN} WHERE test_id = '886090729'
    UNION ALL
    SELECT 'items file', COUNT(*)
    FROM {ITEM_JAN} WHERE test_id = '886090729'
""").show()
```

Findings: the worst tests belong to one vehicle each. The worst test has 1,517 rows but only 1 distinct row. The item file has the same problem (9,583 rows but 6 distinct for the same test). A passing test had 12 results rows and no items, so the repeats are **not** caused by defect items. I don't know the real cause.

### 5.5 Normalise, then measure the real conflicts

After removing exact copies, some tests still had more than one row. I first ran a per-column conflict check on the raw data (all 15 columns: 64,159 conflicting tests). Many conflicts turned out to be the same fact written two ways, so I normalised and measured again.

```python
con.execute(f"""
    CREATE OR REPLACE TEMP VIEW jan_norm AS
    SELECT DISTINCT
        * EXCLUDE (fuel_type, first_use_date, cylinder_capacity, colour, completed_date),
        CASE fuel_type
            WHEN 'Hybrid Electric (Clean)' THEN 'HY'
            WHEN 'Electric' THEN 'EL'
            ELSE fuel_type
        END AS fuel_type,
        NULLIF(NULLIF(cylinder_capacity, '0'), 'NULL') AS cylinder_capacity,
        TRY_CAST(LEFT(first_use_date, 4) AS INTEGER) AS first_use_year
    FROM {JAN}
    WHERE test_id <> 'test_id'
""")
```

- `* EXCLUDE (...)` means all columns except those, so I can rewrite the ones I list.
- Fuel appears as both codes and descriptions, so I convert the descriptions to codes.
- Cylinder capacity is `NULL` or `0` for electric cars, so I treat both as missing.
- First-use date differs between copies (often a 30 or 31 December value in the same year), so I keep only the year.
- `colour` and `completed_date` are dropped (colour isn't needed, and `completed_date` never differs).
- `SELECT DISTINCT` runs after these changes, which is the point.

```python
con.sql("""
    SELECT
        COUNT(*) AS conflicting_tests,
        COUNT(*) FILTER (WHERE n_vehicle > 1)  AS vehicle_id,
        COUNT(*) FILTER (WHERE n_class > 1)    AS test_class_id,
        COUNT(*) FILTER (WHERE n_mileage > 1)  AS test_mileage,
        COUNT(*) FILTER (WHERE n_postcode > 1) AS postcode_area,
        COUNT(*) FILTER (WHERE n_make > 1)     AS make,
        COUNT(*) FILTER (WHERE n_model > 1)    AS model,
        COUNT(*) FILTER (WHERE n_fuel > 1)     AS fuel_type,
        COUNT(*) FILTER (WHERE n_cc > 1)       AS cylinder_capacity,
        COUNT(*) FILTER (WHERE n_first > 1)    AS first_use_year
    FROM (
        SELECT test_id,
               COUNT(DISTINCT vehicle_id)        AS n_vehicle,
               COUNT(DISTINCT test_class_id)     AS n_class,
               COUNT(DISTINCT test_mileage)      AS n_mileage,
               COUNT(DISTINCT postcode_area)     AS n_postcode,
               COUNT(DISTINCT make)              AS n_make,
               COUNT(DISTINCT model)             AS n_model,
               COUNT(DISTINCT fuel_type)         AS n_fuel,
               COUNT(DISTINCT cylinder_capacity) AS n_cc,
               COUNT(DISTINCT first_use_year)    AS n_first
        FROM jan_norm
        GROUP BY test_id
        HAVING COUNT(*) > 1
    )
""").show(max_width=300)
```

Result: conflicting tests dropped from 64,159 to 16,270 (0.43% of January's tests). Test result, test type, test date and `completed_date` never conflict. What remains is mostly `test_class_id`, `fuel_type`, `model`, `test_mileage`, `cylinder_capacity` and `vehicle_id`.

### 5.6 Decision: exclude conflicting tests (after a bias check)

I considered excluding the conflicting tests, keeping one arbitrary row, or resolving each column separately. Since the result never conflicts, I chose **to exclude them** and keep their IDs in a table. First I checked that excluding them wouldn't bias the failure rate:

```python
con.sql("""
    WITH t AS (
        SELECT test_id,
               COUNT(*)               AS versions,
               ANY_VALUE(test_type)   AS test_type,
               ANY_VALUE(test_result) AS test_result
        FROM jan_norm
        GROUP BY test_id
    )
    SELECT versions > 1 AS has_conflict,
           COUNT(*) AS tests,
           ROUND(100.0 * COUNT(*) FILTER (WHERE test_result IN ('F', 'PRS')) / COUNT(*), 1)
               AS pct_initial_fail
    FROM t
    WHERE test_type = 'NT' AND test_result IN ('P', 'F', 'PRS')
    GROUP BY has_conflict
    ORDER BY has_conflict
""").show()
```

Result: 30.0% initial fail rate for single-row tests vs 29.4% for conflicting ones, which is close enough to exclude them safely. (I only checked the overall rate.)

### 5.7 Load all 12 months of results into `results_dedup`

I load month by month, because removing duplicates from 67 million rows at once could exhaust my memory.

**Create the empty table.** I always run this cell immediately before the loop:

```python
con.execute("""
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
    )
""")
```

**Define the function that loads one month:**

```python
def load_month(path):
    con.execute(rf"""
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
        WHERE test_id <> 'test_id'
    """)
```

**List the files and loop over them:**

```python
results_folder = "../data/raw/MOT testing data results (2024)"
files = sorted(f for f in os.listdir(results_folder) if f.endswith(".csv"))

for f in files:
    start = time.time()
    load_month(f"{results_folder}/{f}")
    n = con.sql("SELECT COUNT(*) FROM results_dedup").fetchall()[0][0]
    print(f"{f}: table now has {n:,} rows ({time.time() - start:.0f}s)")
```

Check the first printed line: January should be 3,799,673 rows, not double that.

**Checks:**

```python
con.sql("""
    SELECT COUNT(*) AS table_rows,
           COUNT(DISTINCT test_id) AS distinct_tests,
           COUNT(DISTINCT filename) AS files
    FROM results_dedup
""").show()
```

```python
con.sql("""
    SELECT filename, COUNT(*) AS n
    FROM results_dedup
    GROUP BY filename
    ORDER BY filename
""").show()
```

```python
con.sql("""
    SELECT COUNT(*) AS tests_in_multiple_files
    FROM (
        SELECT test_id
        FROM results_dedup
        GROUP BY test_id
        HAVING COUNT(DISTINCT filename) > 1
    )
""").show()
```

Expected: 42,767,586 rows, 42,598,624 distinct tests, 12 files, and 0 tests in more than one file (so loading month by month is safe).

### 5.8 Record the conflicts

```python
con.execute("""
    CREATE OR REPLACE TABLE test_conflicts AS
    SELECT test_id, COUNT(*) AS versions
    FROM results_dedup
    GROUP BY test_id
    HAVING COUNT(*) > 1
""")
```

```python
con.sql("""
    SELECT COUNT(*)                    AS conflicting_tests,
           SUM(versions)               AS rows_involved,
           SUM(versions) - COUNT(*)    AS extra_rows
    FROM test_conflicts
""").show()
```

Expected: 167,725 conflicting tests (0.39%), 336,687 rows involved, 168,962 extra rows (which equals 42,767,586 minus 42,598,624).

### 5.9 Look at the odd values, then build the clean results table

**Which codes appear?** (I compare with the guide.)

```python
con.sql("""
    SELECT 'test_result' AS col, test_result AS value, COUNT(*) AS n
    FROM test_result_clean GROUP BY test_result
    UNION ALL
    SELECT 'test_type', test_type, COUNT(*) FROM test_result_clean GROUP BY test_type
    UNION ALL
    SELECT 'test_class_id', test_class_id, COUNT(*) FROM test_result_clean GROUP BY test_class_id
    UNION ALL
    SELECT 'fuel_type', fuel_type, COUNT(*) FROM test_result_clean GROUP BY fuel_type
    ORDER BY col, n DESC
""").show(max_rows=100)
```

(I ran this on a first, simpler version of `test_result_clean`, which only converted types and excluded the conflicting tests. The final build is below.)

**The edge cases from the guide:**

```python
con.sql("""
    SELECT
        COUNT(*) FILTER (WHERE test_mileage = 0)                  AS zero_mileage,
        COUNT(*) FILTER (WHERE test_mileage > 500000)             AS over_500k,
        COUNT(*) FILTER (WHERE test_mileage > 1000000)            AS over_1m,
        MEDIAN(test_mileage) FILTER (WHERE test_mileage > 0)      AS median_mileage,
        COUNT(*) FILTER (WHERE first_use_year = 1971)             AS year_1971,
        COUNT(*) FILTER (WHERE first_use_year IS NULL)            AS null_first_use_year,
        COUNT(*) FILTER (WHERE first_use_year > YEAR(test_date))  AS first_use_after_test,
        COUNT(*) FILTER (WHERE postcode_area = 'XX')              AS postcode_xx,
        COUNT(*) FILTER (WHERE postcode_area IS NULL)             AS postcode_null,
        COUNT(*) FILTER (WHERE make = 'UNCLASSIFIED'
                            OR model = 'UNCLASSIFIED')            AS unclassified,
        MIN(test_date)                                            AS earliest_test,
        MAX(test_date)                                            AS latest_test
    FROM test_result_clean
""").show(max_width=300)
```

**Mileage investigation.** The top of the range, and the most common values:

```python
con.sql("""
    SELECT test_id, make, model, test_mileage, first_use_year
    FROM test_result_clean
    WHERE test_class_id = '4' AND test_mileage IS NOT NULL
    ORDER BY test_mileage DESC
    LIMIT 10
""").show()
```

```python
con.sql("""
    SELECT test_mileage, COUNT(*) AS n
    FROM test_result_clean
    WHERE test_class_id = '4' AND test_mileage >= 990000
    GROUP BY test_mileage
    ORDER BY n DESC
    LIMIT 15
""").show()
```

```python
con.sql("""
    SELECT test_mileage, COUNT(*) AS n
    FROM test_result_clean
    WHERE test_mileage IS NOT NULL
    GROUP BY test_mileage
    ORDER BY n DESC
    LIMIT 15
""").show()
```

The ten highest mileages were all exactly 999,999. A value that appears far more often than its neighbours is a filler. Two stood out: 248,601 (687 tests) and 1 (498 tests). I investigated each:

```python
con.sql("""
    SELECT make, model, test_class_id,
           COUNT(*)                   AS tests,
           COUNT(DISTINCT vehicle_id) AS vehicles,
           MIN(test_date)             AS first_test,
           MAX(test_date)             AS last_test
    FROM test_result_clean
    WHERE test_mileage = 248601
    GROUP BY make, model, test_class_id
    ORDER BY tests DESC
    LIMIT 10
""").show()
```

```python
con.sql("""
    SELECT make, model,
           COUNT(*)                   AS tests,
           COUNT(DISTINCT vehicle_id) AS vehicles,
           MEDIAN(vehicle_age_years)  AS median_age
    FROM test_result_clean
    WHERE test_mileage = 1
    GROUP BY make, model
    ORDER BY tests DESC
    LIMIT 10
""").show()
```

```python
con.sql("""
    SELECT CASE WHEN test_mileage < 10  THEN '1-9'
                WHEN test_mileage < 100 THEN '10-99'
                ELSE '100-999' END AS band,
           COUNT(*) AS tests
    FROM test_result_clean
    WHERE test_mileage BETWEEN 1 AND 999 AND vehicle_age_years >= 3
    GROUP BY band
    ORDER BY band
""").show()
```

Findings: 248,601 is almost entirely Fiat, Peugeot and Citroën vans across many different vehicles (an apparent odometer cap). A mileage of 1 is on old or unusual vehicles (a placeholder). Under 100 miles on a vehicle three or more years old isn't believable.

**The rule:** set mileage to missing if it is under 100, exactly 248,601 or exactly 999,999.

**Before rebuilding, count what the rule will remove:**

```python
con.sql("""
    SELECT COUNT(*) FILTER (WHERE test_mileage < 100)      AS under_100,
           COUNT(*) FILTER (WHERE test_mileage = 248601)   AS spike_248601,
           COUNT(*) FILTER (WHERE test_mileage = 999999)   AS filler_999999
    FROM test_result_clean
""").show()
```

**The final build of the clean results table.** Every cleaning rule from the data dictionary is applied here, from `results_dedup`:

```python
con.execute("""
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
    FROM typed
""")
```

- The `WITH typed AS (...)` part does the type conversions once and also applies the exclusion of conflicting tests.
- `TRY_CAST` gives NULL instead of crashing when a value can't be converted.
- Vehicle age comes from the year only, because the exact first-use date is unreliable.

**Check it:**

```python
con.sql("""
    SELECT COUNT(*)                                          AS rows_now,
           COUNT(DISTINCT test_id)                           AS distinct_tests,
           COUNT(*) FILTER (WHERE test_mileage IS NULL)      AS null_mileage,
           COUNT(*) FILTER (WHERE vehicle_age_years IS NULL) AS null_age,
           COUNT(*) FILTER (WHERE is_unclassified)           AS unclassified,
           COUNT(*) FILTER (WHERE postcode_area IS NULL)     AS null_postcode
    FROM test_result_clean
""").show()
```

Expected: 42,430,899 rows (equal to distinct tests), 330,098 missing mileages (321,853 + 7,421 + 687 + 137), 3,051 missing ages, 108,292 unclassified, 2,839 missing postcodes.

### 5.10 Load all 12 months of items into `items_dedup`

Same pattern as results. I keep only the columns I need and rename the location column.

```python
con.execute("""
    CREATE OR REPLACE TABLE items_dedup (
        test_id        VARCHAR,
        rfr_id         VARCHAR,
        rfr_type_code  VARCHAR,
        location_id    VARCHAR,
        dangerous_mark VARCHAR,
        filename       VARCHAR
    )
""")
```

```python
def load_item_month(path):
    con.execute(rf"""
        INSERT INTO items_dedup BY NAME
        SELECT DISTINCT
            test_id,
            rfr_id,
            rfr_type_code,
            mot_test_rfr_location_type_id AS location_id,
            dangerous_mark,
            filename
        FROM read_csv('{path}', all_varchar=true, quote='"', escape='\', filename=true)
        WHERE test_id <> 'test_id'
    """)
```

```python
items_folder = "../data/raw/MOT Testing data failure item (2024)"
item_files = sorted(f for f in os.listdir(items_folder) if f.endswith(".csv"))

for f in item_files:
    start = time.time()
    load_item_month(f"{items_folder}/{f}")
    n = con.sql("SELECT COUNT(*) FROM items_dedup").fetchall()[0][0]
    print(f"{f}: table now has {n:,} rows ({time.time() - start:.0f}s)")
```

Run the table-creation cell immediately before the loop. Then check:

```python
con.sql("""
    SELECT COUNT(*)                  AS item_rows,
           COUNT(DISTINCT test_id)   AS tests_with_items,
           COUNT(DISTINCT filename)  AS files
    FROM items_dedup
""").show()
```

```python
con.sql("""
    SELECT 'rfr_type_code' AS col, rfr_type_code AS value, COUNT(*) AS n
    FROM items_dedup GROUP BY rfr_type_code
    UNION ALL
    SELECT 'dangerous_mark', dangerous_mark, COUNT(*)
    FROM items_dedup GROUP BY dangerous_mark
    ORDER BY col, n DESC
""").show()
```

Result: 91,829,954 rows covering 25,983,976 tests. Item types A (advisory), F (fail), M (minor) and P (PRS) all appear as in the guide. But `dangerous_mark` is NOT empty, even though the guide says it should be: 3,885,070 items carry `D`.

### 5.11 Relate items to the clean results and build `test_item_clean` (next)

**Do the items match up with my tests?** Each item should fall into exactly one group: a clean test, an excluded (conflicting) test, or an orphan whose test doesn't exist.

```python
con.sql("""
    SELECT COUNT(*)                                                       AS item_rows,
           COUNT(*) FILTER (WHERE c.test_id IS NOT NULL)                  AS in_clean_tests,
           COUNT(*) FILTER (WHERE x.test_id IS NOT NULL)                  AS in_excluded_tests,
           COUNT(*) FILTER (WHERE c.test_id IS NULL AND x.test_id IS NULL) AS orphans
    FROM items_dedup i
    LEFT JOIN test_result_clean c ON TRY_CAST(i.test_id AS BIGINT) = c.test_id
    LEFT JOIN test_conflicts x    ON i.test_id = x.test_id
""").show()
```

The three groups must add up to 91,829,954. I expect few or no orphans.

**Where does the D mark appear?**

```python
con.sql("""
    SELECT rfr_type_code, dangerous_mark, COUNT(*) AS n
    FROM items_dedup
    GROUP BY rfr_type_code, dangerous_mark
    ORDER BY rfr_type_code, n DESC
""").show()
```

If `D` appears only on fail items, it's probably a dangerous-defect flag. I'll confirm this against the lookup tables later.

**Build the clean item table:**

```python
con.execute("""
    CREATE OR REPLACE TABLE test_item_clean AS
    SELECT TRY_CAST(test_id AS BIGINT)      AS test_id,
           TRY_CAST(rfr_id AS INTEGER)      AS rfr_id,
           rfr_type_code,
           TRY_CAST(location_id AS INTEGER) AS location_id,
           dangerous_mark
    FROM items_dedup
    WHERE TRY_CAST(test_id AS BIGINT) IN (SELECT test_id FROM test_result_clean)
""")
```

```python
con.sql("""
    SELECT COUNT(*)                AS item_rows,
           COUNT(DISTINCT test_id) AS tests_with_items
    FROM test_item_clean
""").show()
```

`item_rows` should equal `in_clean_tests` from the join check.

## 6. Step 4: lookup tables (planned)

The goal is to turn a defect ID like 31361 into a readable category such as "Brakes" or "Suspension".

1. List the files in `data/raw/lookup` and peek at each one, using the same approach as before (let DuckDB detect the delimiter first, then read as text with the quoting settings if there are problems).
2. Load each lookup file into its own table, named `lookup_<filename>`, as text.
3. Fill in section 6 of the data dictionary with the file names, columns and relationships.
4. Join in the order the guide describes: **item** → **item detail** (on `rfr_id` and `test_class_id`, where the class comes from the results table) → **item group** (the hierarchy) → **top-level category**.
5. Check the join coverage: how many items fail to find a description? Record the number.
6. Compare the lookup's defect category (dangerous, major, minor) with `dangerous_mark`, to settle what `D` means.
7. Build a table that gives each item its readable top-level category, so analysis queries stay short.

## 7. Step 5: analysis in SQL (planned)

I'll put the finished queries in `sql/04_analysis.sql`.

1. Define the analysis scope once, as a view: Class 4, `test_type = 'NT'`, results P, F or PRS, and (for make and model questions) not `is_unclassified`.
2. Write queries that build in difficulty:
   - **Initial failure rate** by vehicle age, mileage band, fuel type, make and model (`GROUP BY`, `CASE`)
   - **Top-level defect categories** by vehicle age band (`JOIN`s through the lookup hierarchy)
   - **Top defects per make** using window functions such as `RANK()`
   - **Multi-step comparisons** using CTEs
3. Use the guide's definitions to compute failure rates (section 8 of the data dictionary), and check that the overall rate looks sensible against DVSA's published figures.
4. Keep an eye on the caveats: hybrid fuel types, excluded tests, and anything related to the unknown cause of the duplicates.
5. Write the results and my interpretation in the notebook `notebooks/02_analysis.ipynb`.

## 8. Step 6: charts (planned)

1. Pull the small, aggregated query results into pandas.
2. Build 5 to 8 clear charts with Plotly or matplotlib, saved in `reports/figures/`.
3. Give each chart a title that states its finding, such as "Suspension defects overtake brakes after 8 years", not a bare label. (This is only an example of the style; the real titles come from what the data shows.)

## 9. Step 7: modelling (planned)

1. Target: `is_initial_fail`. Features: vehicle age, mileage, make, fuel type, and possibly engine size.
2. Split into training and test sets in a way that keeps all tests of the same vehicle on one side, so the model can't see the same car in both.
3. Start with a simple baseline (predicting the overall failure rate), then logistic regression, then a tree-based model.
4. Evaluate honestly with sensible metrics, and write up the limitations. I'll note that vehicle details I don't have (service history, driving conditions) limit what's predictable.
5. Save the work in `notebooks/03_modelling.ipynb`.

## 10. Step 8: make it reproducible and finish (planned)

1. Turn the notebook's loading and cleaning cells into scripts (`src/load_db.py` and the SQL files in `sql/`), so the whole pipeline reruns with one command. I'll build this myself, then compare it with the version I was given earlier to see what I'd improve.
2. Write `src/download_data.py` to fetch the files, and put a small sample in `data/sample/` so others can run the code without the full download.
3. Update `requirements.txt` with `pip freeze`.
4. Finish `docs/data_dictionary.md`: fill in the lookup section, the meaning of `dangerous_mark`, and the date downloaded.
5. Write the README. It should **lead with the findings**, then give a short method overview and reproduction steps. Skimmers should see the insights first.
6. Test that a fresh clone of the repo runs from start to finish.
7. Add the project to my portfolio site, with a short write-up framed around what the analysis shows.
8. Commit often, with clear messages.

## 11. Numbers I should get when I re-run everything

| Check | Expected |
|---|---|
| Rows in all 12 results files, including repeated headers | 66,857,535 |
| Repeated header rows | 180 |
| Distinct `test_id` across all files | 42,598,624 |
| January: data rows / distinct tests / distinct full rows | 6,140,788 / 3,783,238 / 3,848,449 |
| January after normalising: rows in `results_dedup` | 3,799,673 |
| January conflicting tests after normalising | 16,270 (0.43%) |
| Rows in `results_dedup` | 42,767,586 |
| Tests that appear in more than one monthly file | 0 |
| Conflicting tests in `test_conflicts` | 167,725 |
| Rows involved / extra rows | 336,687 / 168,962 |
| Rows in `test_result_clean` (= distinct tests) | 42,430,899 |
| Missing mileage after the rule | 330,098 |
| Missing vehicle age | 3,051 |
| `UNCLASSIFIED` make or model | 108,292 |
| Missing postcode (`XX`) | 2,839 |
| Mileage rule: under 100 / exactly 248,601 / exactly 999,999 | 7,421 / 687 / 137 |
| Rows in `items_dedup` | 91,829,954 |
| Tests with at least one item | 25,983,976 |
| Items by type: A / F / M / P | 60,423,134 / 21,455,761 / 6,996,403 / 2,954,656 |
| Items with `dangerous_mark = 'D'` | 3,885,070 |
| January initial fail rate: single-row tests vs conflicting tests | 30.0% vs 29.4% |

## 12. Problems and fixes (things that went wrong, or that I need to watch for)

| Problem | Cause | Fix |
|---|---|---|
| `Could not convert string "test_id" to BIGINT` | The header row is repeated inside the file, and DuckDB guessed the column type from the first 20,480 rows | Read everything as text (`all_varchar=true`) and drop rows where `test_id = 'test_id'` |
| `Expected Number of Columns: 15 Found: 16` | A value containing a comma (`"IVECO ,MOTORHOME"`), and DuckDB guessed there were no quotes | Set `quote='"'` explicitly |
| `Value with unterminated quote found` | Quotes inside values are escaped with a backslash (`12\"`), not doubled | Set `escape='\'` (in a raw string, so Python keeps the backslash) |
| Everything in one column | I used `delim='\|'`, but these files are comma-separated | Let DuckDB detect the delimiter |
| `connection has an unfinished result` (one to watch for in newer DuckDB versions) | Using `fetchone()` can leave the result open | Use `.fetchall()[0][0]` |
| January loaded twice (7,599,346 rows after the first file) | I ran the loop without re-running the table-creation cell | Re-run the `CREATE OR REPLACE TABLE` cell first, every time |
| Possible text `'NULL'` versus a true missing value (not an error I hit, but one to watch for) | `cylinder_capacity` and other columns can contain the text `NULL` | `NULLIF(NULLIF(cylinder_capacity, '0'), 'NULL')` handles both |

## 13. Habits I'm keeping

- Commit often, with clear messages, and never commit the raw data.
- Update the data dictionary whenever I learn something about the data.
- Reconcile every new table against a number I trust.
- Make every cleaning rule a documented decision, with its row count.
- Lead with the insight, not the code, in the README and the portfolio write-up.
