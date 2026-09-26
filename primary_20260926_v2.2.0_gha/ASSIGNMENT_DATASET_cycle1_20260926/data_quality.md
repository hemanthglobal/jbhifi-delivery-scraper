STATUS: IN PROGRESS - 9 of 40 slots due so far (last 2026-09-26 16:00). Snapshot 2026-09-26 16:19:41. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-26 (primary_20260926_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 441 |
| rows_after_dedup | 441 |
| successful_requests | 441 |
| valid_results_uber_offered | 351 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 45 |
| no_availability_no_store (NO_STORE_REPORTED) | 45 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 5 |
| status | IN PROGRESS - 9 of 40 slots due so far (last 2026-09-26 16:00). Snapshot 2026-09-26 16:19:41. Refresh after the next pass. |
| run_id | primary_20260926_v2.2.0_gha |

## states

- ON_DEMAND_ASAP: 195
- NO_STORE_REPORTED: 45
- ON_DEMAND_SCHEDULED: 156
- ON_DEMAND_UNAVAILABLE: 45

## error_types

- none

## uber_detection_rules

- logo-alt: 351

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 90
- ondemand_price_aud: 90
- standard_promise_text: 45
- standard_price_aud: 45
- notes: 288
- ondemand_detected_by: 90
- error_type: 441
- review_flag: 441

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 9
- first_slot: 2026-09-26 12:00
- last_slot: 2026-09-26 16:00
- postcodes: 49
- products: ['s26']
- expected_cells: 441
- observed_cells: 441
- coverage_pct: 100.0
- expected_slots_so_far: 9
- missing_cells: 0
- slots_with_no_rows: []

## postcodes_with_errors

- none

## run_ids

- primary_20260926_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
