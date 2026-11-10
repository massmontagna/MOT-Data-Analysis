# Data dictionary: DVSA anonymised MOT tests and results (2024)

This is my working reference for the MOT data I'm using in this project. I started it from the DVSA user guide, then corrected it wherever the real 2024 files turned out to be different. Where the files disagree with the guide, the files win, and I've noted it.

## 1. Source

| Item | Detail |
|---|---|
| Publisher | Driver and Vehicle Standards Agency (DVSA) |
| Dataset | Anonymised MOT tests and results |
| Where from | data.gov.uk, "Anonymised MOT tests and results" |
| Licence | UK Open Government Licence v3.0 |
| Year used | 2024 (12 monthly files per table). I may add 2023 later |
| Date downloaded | TODO |
| Documentation | MOT testing data user guide v5.1 (post-May 2018) and the lookup tables |

The user guide (v5.1) describes data up to the end of 2023, so some of what it says doesn't match the 2024 files. The differences are listed in section 7.1.

**Scope per the guide:** all tests where a valid MOT pass could have been a possible outcome. The guide advises against using Excel or Access for analysis, which is why I'm using DuckDB.

## 2. Files and format

**Two main tables, each split into 12 monthly files:**

| Table | Folder | Files | Rows |
|---|---|---|---|
| Results (one row per test) | `MOT testing data results (2024)` | `test_result_202401.csv` to `test_result_202412.csv` | 66,857,355 data rows in the files. 42,767,586 after removing exact copies. 42,430,899 after excluding conflicting tests |
| Failure items (one row per defect or advisory) | `MOT Testing data failure item (2024)` | `test_item_202401.csv` to `test_item_202412.csv` | 91,829,954 after removing exact copies (I didn't count the raw rows) |
| Lookup tables | `lookup` | Not inspected yet | n/a |

**Format (differs from the guide):**
- **Comma-separated**, not pipe-separated as the guide says.
- Values containing commas are wrapped in double quotes, e.g. `"IVECO ,MOTORHOME"`.
- A literal double quote inside a value is escaped with a backslash, e.g. `"STREETZONE 50 2T 12\""`, not by doubling it.
- The header row is repeated partway through the files. There are 180 repeated header rows across the 12 results files. I haven't broken this down by file, and I haven't counted them in the item files.
- Dates are ISO format (`2024-01-02`). `completed_date` is a full timestamp (`2024-01-02T10:19:28.000Z`). Mileage is stored with a decimal point (`71614.0`).
- Missing values appear as `NULL`.

**Reading the files:** I load everything as text first (`all_varchar=true`), because DuckDB's automatic type detection only samples the first 20,480 rows and failed on the repeated headers further down. I convert types afterwards, once I know what's in the columns.

## 3. How the tables relate

- One test (results) has zero or more items (failure items). They join on `test_id`.
- `test_id` is meant to be the primary key of the results table, but it isn't unique in the 2024 files (see section 7.2).
- In the guide, an item links to a description through `RfR ID` plus `Test Class ID`, and the descriptions sit in a hierarchy of item groups (this is how I'll get readable categories such as brakes or suspension). I haven't inspected the lookup files yet.

### Tables I build in DuckDB

| Table | What it is | Rows |
|---|---|---|
| `results_dedup` | All 12 months of results as text, header rows removed, fuel/first-use values normalised, exact copies removed. Still includes conflicting tests | 42,767,586 |
| `test_conflicts` | Tests that still have more than one row after the step above (excluded from analysis) | 167,725 tests (336,687 rows) |
| `test_result_clean` | Analysis table for results: typed, one row per test, conflicting tests excluded, cleaning rules applied (section 7.5) | 42,430,899 |
| `items_dedup` | All 12 months of items as text, header rows removed, exact copies removed | 91,829,954 |
| `test_item_clean` | Items typed and limited to tests in `test_result_clean` | Not built yet |

Columns in `test_result_clean`: `test_id`, `vehicle_id`, `test_date`, `test_class_id`, `test_type`, `test_result`, `is_initial_fail`, `test_mileage`, `postcode_area`, `make`, `model`, `is_unclassified`, `fuel_type`, `fuel_type_desc`, `cylinder_capacity`, `first_use_year`, `vehicle_age_years`.

## 4. Results table

One intended row per test. All 15 columns below are present in the 2024 files.

| Column | Meaning | Notes |
|---|---|---|
| `test_id` | Unique ID for the test | Not actually unique in the files (section 7.2) |
| `vehicle_id` | Anonymised vehicle ID | Lets me follow a vehicle across tests |
| `test_date` | Date of the test | ISO format. All 2024 tests fall between 1 Jan and 30 Dec |
| `test_class_id` | Vehicle class tested | Class 4 = cars (see below) |
| `test_type` | Type of MOT test | See below |
| `test_result` | Outcome | See below |
| `test_mileage` | Odometer reading | Stored like `71614.0`. Blank means no reading. Some values are fillers (section 7.7) |
| `postcode_area` | Area where the test took place | Small areas are merged into `XX` |
| `make` | Vehicle make | Can contain commas, e.g. `IVECO ,MOTORHOME` |
| `model` | Vehicle model | Can contain quote marks, e.g. `12"` |
| `colour` | Vehicle colour | Not needed for my questions, so I drop it |
| `fuel_type` | Fuel type | Mixes codes and full descriptions in the raw files (section 7.4) |
| `cylinder_capacity` | Engine size | `NULL` and `0` both appear for electric cars |
| `first_use_date` | Date the vehicle was first used | Inconsistent between copies of the same test (section 7.3) |
| `completed_date` | When the test was completed | Not in the guide. Never differs between copies of a test |

### Codes and row counts in `test_result_clean` (42,430,899 tests, all classes and types)

**Test result**

| Code | Meaning (guide) | Rows |
|---|---|---|
| P | Pass | 32,310,599 |
| F | Fail | 7,935,366 |
| PRS | Pass with rectification at station: defects fixed within an hour, before the result was recorded | 1,937,814 |
| ABR | Aborted: test could not be completed because of an equipment or tester problem | 219,925 |
| ABA | Abandoned: test could not be completed safely | 27,174 |
| ABRVE | **Not in the guide** | 21 |

**Test type**

| Code | Meaning (guide) | Rows |
|---|---|---|
| NT | Normal test | 35,233,661 |
| RT | Re-test | 7,196,878 |
| EI | **Not in the guide** | 300 |
| ES | Statutory appeal | 60 |
| PL, PV | Partial retests. **None appear in 2024**: all retests are `RT` | 0 |

**Test class**

| Class | Description (guide) | Rows |
|---|---|---|
| 4 | Cars and passenger vehicles up to 8 seats, motor caravans, dual-purpose vehicles, goods vehicles up to 3,000 kg | 40,025,025 |
| 7 | Goods vehicles over 3,000 kg up to 3,500 kg | 1,299,625 |
| 2 | All motorbikes | 811,592 |
| 1 | Motorbikes up to 200cc | 235,913 |
| 5 | Larger passenger vehicles, 13+ seats | 48,870 |
| 3 | 3-wheeled vehicles up to 450 kg | 9,874 |
| 0 | Legacy records from before computerisation. None in 2024 | 0 |

I'm filtering to **Class 4** (cars), which is 94% of tests, for the analysis.

**Fuel type** (after normalising the spellings)

| Code | Fuel | Rows | Code | Fuel | Rows |
|---|---|---|---|---|---|
| PE | Petrol | 22,300,120 | OT | Other | 8,352 |
| DI | Diesel | 18,066,134 | LP | Liquefied petroleum gas | 8,103 |
| HY | Hybrid electric (clean) | 1,459,511 | GB | Gas bi-fuel | 4,429 |
| EL | Electric | 507,420 | GA | Gas | 222 |
| ED | Electric diesel | 76,215 | FC | Fuel cells | 166 |
| GD | Gas diesel | 129 | CN | Compressed natural gas | 68 |
| LN | Liquefied natural gas | 22 | ST | Steam | 8 |

## 5. Failure items table

One row per defect, advisory or minor defect recorded against a test.

| Column | Meaning | Notes |
|---|---|---|
| `test_id` | Links to the results table | |
| `rfr_id` | Reason for rejection ID | Joins to the lookup tables (with the test class) |
| `rfr_type_code` | Type of item | A, F, M and P all appear, as in the guide |
| `mot_test_rfr_location_type_id` | Where on the vehicle | The guide calls this `Location ID`. I rename it `location_id`. The guide says location IDs were wrong before 2022 |
| `dangerous_mark` | Dangerous marker | **Not empty in 2024, contrary to the guide** (see below) |
| `completed_date` | When the test was completed | Not in the guide. I drop it from the item table |

### Item counts in `items_dedup` (91,829,954 rows covering 25,983,976 tests)

| `rfr_type_code` | Meaning (guide) | Rows |
|---|---|---|
| A | Advisory | 60,423,134 |
| F | Fail item | 21,455,761 |
| M | Minor defect | 6,996,403 |
| P | PRS: item failing at the point of test, repaired within the hour | 2,954,656 |

| `dangerous_mark` | Rows |
|---|---|
| NULL | 87,944,884 |
| D | 3,885,070 |

The guide says this marker was only populated up to May 2018 and isn't comparable with the post-2018 Dangerous category. But 4.2% of 2024 items carry a `D`. I don't yet know what it means now. To work out, I'll check which item types it appears on and compare it with the defect category in the lookup tables.

### Defect categories (post-May 2018)

| Category | Effect on the test outcome |
|---|---|
| Dangerous | Causes a fail |
| Major | Causes a fail |
| Minor | Does not cause a fail |
| Advisory | Recorded, but the test can still pass |

## 6. Lookup tables

I haven't opened the lookup files yet. From the guide, I expect:
- **Item detail:** a description for each defect (`rfr_id` plus test class), including its category (dangerous, major, minor) and a link to its group. The defect category column is only available from 2022 onward.
- **Item group:** the hierarchy of groups, which I'll use to turn defects into readable top-level categories such as brakes or suspension.
- **Failure location:** lateral, longitudinal and vertical position on the vehicle.

I'll fill in the exact file names and columns when I load them.

## 7. Known quirks and cleaning decisions

### 7.1 Where the files differ from the guide

| What | Guide says | 2024 files |
|---|---|---|
| Delimiter | Pipe `\|` | Comma |
| Files | Annual | Monthly (12 per table) |
| Extra column | n/a | `completed_date` in both tables |
| Item location column | `Location ID` | `mot_test_rfr_location_type_id` |
| `test_id` | Unique per test | Repeated many times |
| `dangerous_mark` | Empty after May 2018 | `D` on 3,885,070 items |
| Result codes | P, F, PRS, ABA, ABR | Also `ABRVE` (21 rows) |
| Test types | Includes PL and PV partial retests | None. Retests are all `RT`. Also `EI` (300 rows) |
| Test class 0 | Legacy records | None in 2024 |
| Zero mileage | Means no reading | None. No reading is stored as blank |

### 7.2 Repeated rows

`test_id` is not unique. Across all 12 results files there are 66,857,355 data rows but only 42,598,624 distinct test IDs.

I investigated this on January first (6,140,788 data rows, 3,783,238 distinct tests):

- **Exact copies are common.** Removing them leaves 3,848,449 rows, so about 2.29 million rows (37%) were identical copies of another row.
- **The repetition is uneven.** 2.6 million tests appear once, then there's a long tail of 2, 3, 4, 6, 8 or more copies. The worst test has 1,517 copies, and its rows are all identical.
- **It isn't caused by defect items.** One passing test (`886090729`) has 12 rows in the results file and no items at all.
- **The item file has the same problem.** One test has 9,583 item rows, but only 6 distinct ones.
- **I don't know why this happens.** I haven't found an explanation in the guide or the data.
- **No test appears in more than one monthly file**, so removing duplicates one month at a time is safe.

### 7.3 Rows for the same test that disagree

After removing exact copies, 64,159 January tests (1.7%) still had more than one row. Result, test type, test date and `completed_date` **never** differed between copies. The differences were all in vehicle details:

| Column | Tests with a conflict | After normalising (see below) |
|---|---|---|
| `first_use_date` / year | 41,274 | 1,224 |
| `colour` | 8,181 | dropped |
| `test_class_id` | 7,952 | 7,952 |
| `fuel_type` | 2,267 | 2,249 |
| `model` | 2,224 | 2,224 |
| `test_mileage` | 2,038 | 2,038 |
| `cylinder_capacity` | 811 | 811 |
| `vehicle_id` | 777 | 777 |
| `postcode_area` | 343 | 343 |
| `make` | 288 | 288 |
| **Tests with any conflict** | **64,159** | **16,270 (0.43%)** |

Patterns I noticed: one copy of `first_use_date` is often 30 or 31 December of the same year as the other, which looks like a year-only value; the same vehicle can appear in two test classes (4 and 7 for a van, 1 and 2 for a motorbike); and the same car can have two colours.

**Normalising first.** Many of the conflicts were the same fact written two ways, so I normalise before removing duplicates:
- `fuel_type`: `Hybrid Electric (Clean)` becomes `HY`, and `Electric` becomes `EL`.
- `cylinder_capacity`: `0` and `NULL` are both treated as missing.
- `first_use_date` becomes `first_use_year` (the first four characters), which is the same across copies.
- `colour` and `completed_date` are dropped.

**Full year:** after normalising and removing exact copies, `results_dedup` has 42,767,586 rows. 167,725 tests (0.39%) still have more than one row (336,687 rows, so 168,962 extra). Nearly all have exactly two versions.

### 7.4 Fuel type spellings

In the raw files the same fuel appears both as a code and as a description (January counts):

| Code | Rows | Description | Rows |
|---|---|---|---|
| HY | 132,557 | Hybrid Electric (Clean) | 44,898 |
| EL | 39,317 | Electric | 8,701 |

Without normalising, hybrids and electric cars would each be split into two groups. The descriptions look like they came from the fuel type lookup table. After normalising, only the 14 two-letter codes remain.

### 7.5 My rules for the clean results table

1. Drop the repeated header rows.
2. Normalise as in 7.3, then remove exact duplicate rows (month by month).
3. **Exclude tests that still have conflicting rows**, and keep their IDs in `test_conflicts` so the choice is visible and reversible.
4. Vehicle age is calculated from the **year** of first use (test year minus first-use year), because the exact first-use date is unreliable.
5. The 1971 placeholder first-use year is treated as unknown.
6. Postcode `XX` is set to missing.
7. Make or model `UNCLASSIFIED` is flagged (`is_unclassified`), not removed. I exclude those only from make and model analysis.
8. Mileage is set to missing if it is under 100, exactly 248,601 or exactly 999,999 (section 7.7).
9. `is_initial_fail` is true for F or PRS, false for P, and missing for aborted or abandoned tests.
10. Scope for the analysis: Class 4, initial tests (`NT`), results P, F or PRS. I apply this in the analysis queries, not in the table.

**Bias check:** among January initial tests, the initial fail rate was 30.0% for tests with a single row (3,098,266 tests) and 29.4% for the 12,862 tests with conflicting rows. That gap is small enough that excluding them shouldn't noticeably change the overall failure rate. I only checked the overall rate, not rates by vehicle type, which is a limitation to mention in the write-up.

### 7.6 Edge cases from the guide, checked in `test_result_clean`

| Quirk | Count | What I did |
|---|---|---|
| First-use year is the 1971 placeholder | 3,049 | Set to missing |
| First-use year is after the test year | 2 | No vehicle age |
| Total tests with no vehicle age | 3,051 | |
| Postcode `XX` | 2,839 | Set to missing |
| `UNCLASSIFIED` make or model | 108,292 (0.26%) | Flagged |
| Zero mileage | 0 | Nothing to do |
| Blank mileage (before the mileage rule) | 321,853 (0.76%) | Stays missing |
| Mileage over 1,000,000 | 0 | Nothing to do |
| Hybrids recorded under the wrong fuel type before 2022 (guide) | Not checked | Caveat any hybrid or EV conclusions |

### 7.7 Mileage oddities

- **999,999** appears 137 times (133 among cars). The next highest values appear at most 3 times, so I treat it as a filler value.
- **248,601** appears 687 times, almost entirely Fiat, Peugeot and Citroën vans (Relay, Ducato, Boxer, Bipper, Nemo, Fiorino, Doblo) across 100+ different vehicles. I read it as an odometer cap. It is near 400,000 km, but not an exact match.
- **A mileage of 1** appears 498 times, mostly on old or unusual vehicles (Ford Escort, Lambretta, Honda C90, Land Rover Defender), so it's a placeholder.
- **Under 100 miles on a vehicle at least three years old:** 2,015 tests at 1 to 9 miles and 4,451 at 10 to 99.
- **Rule:** mileage under 100 (7,421 tests), exactly 248,601 (687) or exactly 999,999 (137) is set to missing. Total missing mileage went from 321,853 to 330,098.
- **Median mileage** of valid readings is 68,681. 5,393 are over 500,000.
- **Limitation:** I found these values from the top of the frequency list, so smaller spikes may remain.

## 8. Metric definitions (from the guide)

To compare fairly with DVSA's published statistics, I use **initial tests only**: `test_type = 'NT'` and `test_result` in `P`, `F` or `PRS`.

- **Initial failure rate** = (Fail results + the initial fail from PRS results) / total tests
- **Final failure rate** = Fail results / total tests
- **Initial failures by defect category** = count of distinct tests with one or more `F` or `P` type items, grouped by top-level item in the hierarchy

## 9. Questions to answer with this data

1. How does the initial failure rate change with vehicle age and mileage?
2. Which top-level defect groups (brakes, suspension, tyres, lights...) drive failures as vehicles age?
3. How do failure patterns differ by fuel type? (Mind the hybrid misclassification caveat.)
4. Which makes and models fail most and least, after controlling for age and mileage?
5. Can failure be predicted from age, mileage, make and fuel type?
6. TODO: add your own
