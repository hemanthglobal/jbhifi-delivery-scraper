STATUS: IN PROGRESS - 25 of 40 slots due so far (last 2026-09-27 01:00). Snapshot 2026-09-27 01:19:33. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-26 (primary_20260926_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 1225 |
| rows_after_dedup | 1225 |
| successful_requests | 1225 |
| valid_results_uber_offered | 975 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 125 |
| no_availability_no_store (NO_STORE_REPORTED) | 125 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 7 |
| status | IN PROGRESS - 25 of 40 slots due so far (last 2026-09-27 01:00). Snapshot 2026-09-27 01:19:33. Refresh after the next pass. |
| run_id | primary_20260926_v2.2.0_gha |

## states

- ON_DEMAND_ASAP: 195
- NO_STORE_REPORTED: 125
- ON_DEMAND_SCHEDULED: 780
- ON_DEMAND_UNAVAILABLE: 125

## error_types

- none

## uber_detection_rules

- logo-alt: 975

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 250
- ondemand_price_aud: 250
- standard_promise_text: 125
- standard_price_aud: 125
- notes: 800
- ondemand_detected_by: 250
- error_type: 1225
- review_flag: 1225

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 25
- first_slot: 2026-09-26 12:00
- last_slot: 2026-09-27 01:00
- postcodes: 49
- products: ['s26']
- expected_cells: 1225
- observed_cells: 1225
- coverage_pct: 100.0
- expected_slots_so_far: 25
- missing_cells: 0
- slots_with_no_rows: []

## postcodes_with_errors

- none

## run_ids

- primary_20260926_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
