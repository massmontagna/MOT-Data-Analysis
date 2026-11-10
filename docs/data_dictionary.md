# Data dictionary: DVSA anonymised MOT tests and results

> **Status:** populated from the DVSA *MOT testing data user guide v5.1* (post-May 2018). Everything marked **Guide** comes from that document. Items marked `TODO` or with an unticked **Check** box need confirming against the real files (`df.head()`, `df.dtypes`) or filling in with your own observations. The guide gives "suggested" column names, so the actual file headers may be styled differently (e.g. `test_id`).

## 1. Source

| Item | Detail |
|---|---|
| Publisher | Driver and Vehicle Standards Agency (DVSA) |
| Dataset name | Anonymised MOT tests and results |
| Where from | data.gov.uk, "Anonymised MOT tests and results" |
| Licence | UK Open Government Licence v3.0 |
| Years used | 2023 (add 2024 later) |
| Coverage per guide v5.1 | Tests from 01/01/2005 to 31/12/2023 across all annual releases |
| Date downloaded | TODO |
| Documentation | MOT testing data user guide v5.1, lookup tables |

**Coverage caveat (Guide):** MOT computerisation was not fully rolled out across Great Britain until 01/04/2006, so tests between 01/01/2005 and 31/03/2006 are incomplete. Not relevant for 2023/2024 but worth knowing.

**Scope (Guide):** includes all tests for which a valid MOT pass could have been a potential outcome. Excel and Access are explicitly **not recommended** for analysis. The guide says to use a proper database, which is why we use DuckDB.

## 2. File format and structure

- **Delimiter:** pipe character `|` (not a comma). In pandas use `sep="|"`; in DuckDB, `delim='|'`.
- **Header row:** yes (the guide's MySQL import skips 1 line).
- **Two main groups of data (Guide):**
  - **Results**: time, place and final outcome of each MOT test, plus information about the vehicle tested.
  - **Failure items**: individual Reasons for Rejection (RfRs) found during a test.
- **Lookup tables:** decode RfR IDs into descriptions and hierarchy, failure locations, and so on.

| File | Filename on disk | Rows (approx.) | Size | Check |
|---|---|---|---|---|
| Results 2023 | TODO | TODO | TODO | [ ] |
| Failure items 2023 | TODO | TODO | TODO | [ ] |
| Lookup tables | TODO (see zip contents) | n/a | n/a | [ ] |

## 3. Entity relationships (Guide)

```
Test Result (1) ──< (many) Test Item >── (0..1) Failure Location
                              │
                              └── RfR ID + Test Class ID ──> Test Item Detail
                                                                  │
                                              Test Item ID ───────┴──> Test Item Group (parent/child hierarchy)
```

- A **Test Result** may have one or more **Test Items**. A test item always belongs to exactly one test result. Join on `Test ID`.
- A **Test Item** may have one **Failure Location**. Join on `Location ID`.
- A Test Item is defined by a **Test Item Detail**. Join on `RfR ID` **and** `Test Class ID` (the test class comes from the results table).
- Test Item Detail belongs to a **Test Item Group**, which forms a hierarchy: `Vehicle` (ID 0) → top-level item → test item → up to 3 further levels.

**Join key to confirm:** `Test ID` is the primary key in results and repeats in failure items (one test, many items). [ ] Verify by checking for duplicates in each file.

## 4. Results table: "Vehicle Test Result"

One row per MOT test. Primary key: `Test ID`.

| Column (guide name) | Description | Type | Notes | Check |
|---|---|---|---|---|
| Test ID | Unique ID for a test | Integer | Primary key | [ ] |
| Vehicle ID | Unique ID for a vehicle | Integer | Based on registration and VIN; lets you track one vehicle across tests and years | [ ] |
| Test Date | Date of test | Date | Guide says format DD-MM-YYYY | [ ] |
| Test Class ID | Class of vehicle tested | Character (2) | See test classes below. Class 4 = cars | [ ] |
| Test Type | Type of MOT test | Character (2) | See test types below | [ ] |
| Test Result | Test outcome | Character (5) | See result codes below | [ ] |
| Test Mileage | Odometer at test | Integer | **Zero or blank = no reading** (e.g. aborted test). See mileage quirk below | [ ] |
| Postcode Area | Test location | Character (2) | High-level region. Regions with fewer than 5 active sites are merged into `XX` | [ ] |
| Make | Vehicle make | Character | From DVSA's vehicle dataset. Unmatched = `UNCLASSIFIED` | [ ] |
| Model | Vehicle model | Character | As above | [ ] |
| Colour | Vehicle colour | Character (16) | As entered or validated by the tester | [ ] |
| Fuel Type | Fuel type code | Character (2) | See fuel type codes below | [ ] |
| Cylinder Capacity | Engine size | Integer | As entered or validated by the tester | [ ] |
| First use Date | Date of first use | Date | `01/01/1971` is a placeholder for unknown manufacture date | [ ] |

### Test result codes

| Code | Meaning | Notes |
|---|---|---|
| P | Pass | |
| F | Fail | |
| PRS | Pass with Rectification at Station | Defects fixed within one hour of the test, before the result is recorded. The vehicle starts the test failing but passes by the time the result is entered |
| ABA | Abandon | Test could not be completed because the tester judged it unsafe to continue, or items could not be inspected. A fee may be charged |
| ABR | Abort | Test could not be completed due to equipment or tester problem. No fee |

### Test type codes

| Code | Meaning | Notes |
|---|---|---|
| NT | Normal test | Full initial test |
| ES | Statutory appeal | |
| PL | Partial retest, left the test station | Half-fee retest if the vehicle left for repair and returned by close of the next working day |
| PV | Partial retest, repaired at station | Free partial retest |
| RT | Re-test | Full retest, derived by the system |

### Fuel type codes

| Code | Fuel | Code | Fuel |
|---|---|---|---|
| PE | Petrol | EL | Electric |
| DI | Diesel | HY | Hybrid Electric (Clean) |
| ED | Electric Diesel | FC | Fuel Cells |
| CN | Compressed Natural Gas | LN | Liquefied Natural Gas |
| LP | Liquefied Petroleum Gas | GA | Gas |
| GB | Gas Bi-Fuel | GD | Gas Diesel |
| ST | Steam | OT | Other |

### Test classes (Guide)

| Class | Description | First test at (years) |
|---|---|---|
| 0 | Records from before MOT computerisation, created when a duplicate/replacement certificate was requested | n/a |
| 1 | Motorbikes up to 200cc | 3 |
| 2 | All motorbikes | 3 |
| 3 | 3-wheeled vehicles up to 450 kg | 3 |
| 4 | Cars and passenger vehicles up to 8 seats, motor caravans, dual-purpose vehicles, goods vehicles up to 3,000 kg DGW (3 years); taxis, ambulances and some 9-12 seat vehicles (1 year) | 3 (some 1) |
| 5 | Larger private passenger vehicles, 13+ seats | 1 |
| 7 | Goods vehicles over 3,000 kg up to 3,500 kg DGW | 3 |

For a first project, **filter to Class 4** (cars) to keep the analysis clean.

## 5. Failure items table: "Vehicle Test Item"

One row per reason for rejection, advisory or minor defect recorded against a test.

| Column (guide name) | Description | Type | Notes | Check |
|---|---|---|---|---|
| Test ID | Links to results | Integer | Join key to results | [ ] |
| RfR ID | Reason for Rejection ID | Integer | Join to Test Item Detail (with Test Class ID) | [ ] |
| RfR Type | Type of item | Character (1) | `F` fail, `P` PRS, `A` advisory, `M` minor | [ ] |
| Location ID | Failure location | Integer | Join to Failure Location. **Wrong in files before 2022** (see quirks) | [ ] |
| D Mark | Dangerous marker | Character (1) | Only populated up to 19 May 2018. Not comparable with the post-2018 Dangerous category | [ ] |

### RfR type codes

| Code | Meaning |
|---|---|
| F | A test failure item |
| P | PRS: item failing at the point of test, repaired within an hour and before the result was entered |
| A | Advisory |
| M | Minor defect |

## 6. Lookup tables

Confirm exact filenames and headers once you unzip the lookup file.

### Test Item Detail (one row per RfR and test class)

| Column | Description | Notes |
|---|---|---|
| RfR ID + Test Class ID | Primary key | |
| Test Item ID | Parent test item | Links to Test Item Group |
| rfr_deficiency_category | EU defect category | `PE` (pre-19 May 2018), `MI` minor, `MA` major, `D` dangerous. **Only available from the 2022 data onward** |
| Minor Item | Y/N | Whether it qualifies for a free partial retest |
| RfR Description | Short description | Text printed on the failure document (VT30) |
| RfR Location Marker | Y/N | Whether further location detail is required |
| RfR Insp Man Description | Inspection manual description | |
| RfR Advisory Text | Advisory wording | |
| Test Item Set Section ID | Top-level item | Links to the top-level group, which is what you group by for "brakes", "suspension", etc. |

### Test Item Group (the hierarchy)

| Column | Description |
|---|---|
| Test Item ID + Test Class ID | Primary key |
| Parent ID | Parent in the hierarchy |
| Test Item Set Section ID | Top-level item |
| Item Name | Name of the group (e.g. top-level categories) |

The top level for each class is `Vehicle` (ID 0). Resolving a defect to a readable top-level category means joining item → detail → group, and this is the key SQL skill the project will show off.

### Failure Location

| Column | Description |
|---|---|
| Failure Location ID | Primary key |
| Lateral | Offside / nearside etc. |
| Longitudinal | Front / rear etc. |
| Vertical | Inner / outer etc. |

Example from the guide: location ID 10 = offside, rear, outer.

### Defect categories (post-20 May 2018)

| Category | Effect on test outcome |
|---|---|
| Dangerous | Causes a fail |
| Major | Causes a fail |
| Minor | Does not cause a fail |
| Advisory | TODO: describe in your own words (RfR type A; pass is unaffected) |

## 7. Known quirks and cleaning decisions

All from the guide unless noted.

| # | Quirk | Affects | How I'll handle it |
|---|---|---|---|
| 1 | Unknown manufacture date is set to `01/01/1971`, so 1971 first-use data is anomalous | Vehicle age | TODO: exclude or flag when computing age |
| 2 | Mileage of 0 or blank means no reading | Mileage analysis | TODO: treat as null |
| 3 | Before 2022, some mileage values are actually **kilometres** (2022 onward is converted to miles) | Mileage, comparisons across years | TODO: note for any multi-year work; 2023/2024 are post-fix |
| 4 | Before 2022, hybrids are often recorded under the wrong fuel type (e.g. early Priuses). 2022 onward attempts a correction but is not perfect | Fuel type analysis | TODO: caveat any hybrid/EV conclusions |
| 5 | Failure `Location ID` is in error in data up to 2021; fixed from 2022 | Location analysis | Fine for 2023/2024 |
| 6 | Defect category (`rfr_deficiency_category`) only in the 2022+ data | Defect severity analysis | Fine for 2023/2024 |
| 7 | `D Mark` (dangerous marker, to May 2018) is not comparable to the post-2018 Dangerous category | Defect severity | Ignore for 2023/2024 |
| 8 | Postcode areas with fewer than 5 test sites are merged into `XX` | Regional analysis | Exclude `XX` from regional comparisons |
| 9 | Make/model not found in DVSA's vehicle dataset are labelled `UNCLASSIFIED` | Make/model analysis | TODO: exclude or report separately |
| 10 | Test Class 0 records are legacy duplicate-certificate tests | Everything | Filter to the class you analyse |
| 11 | Retests, partial retests, aborted and abandoned tests are all in the data | Pass-rate calculations | See pass rate definition below |
| 12 | The same vehicle appears across tests and years (via Vehicle ID) | Double counting | TODO: decide whether the unit of analysis is the test or the vehicle |
| 13 | Guide v5.1 describes data to end-2023; check the 2024 file notes before combining years | Multi-year work | TODO: re-read the guidance when adding 2024 |

Issues I find in the actual files (add as you go):

| # | Issue | Where | How I'll handle it |
|---|---|---|---|
| 1 | TODO | TODO | TODO |

## 8. Metric definitions (Guide)

To compare fairly with DVSA's published statistics, use **initial tests only**: `Test Type = 'NT'` and `Test Result IN ('P', 'F', 'PRS')`.

- **Initial failure rate** = (Fail results + the initial fail from PRS results) / total tests
- **Final failure rate** = Fail results / total tests
- **Initial failures by defect category** = count of *distinct tests* with one or more `F` or `P` type test items, grouped by top-level item in the hierarchy

## 9. Questions to answer with this data

1. How does the initial failure rate change with vehicle age and mileage?
2. Which top-level defect groups (brakes, suspension, tyres, lights...) drive failures as vehicles age?
3. How do failure patterns differ by fuel type? (Mind the hybrid misclassification caveat.)
4. Which makes and models fail most and least, after controlling for age and mileage?
5. Can failure be predicted from age, mileage, make and fuel type?
6. TODO: add your own
