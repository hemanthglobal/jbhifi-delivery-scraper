STATUS: IN PROGRESS - 4 of 40 slots due so far (last 2026-09-26 13:30). Snapshot 2026-09-26 13:49:56. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-26 (primary_20260926_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 196 |
| rows_after_dedup | 196 |
| successful_requests | 196 |
| valid_results_uber_offered | 156 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 20 |
| no_availability_no_store (NO_STORE_REPORTED) | 20 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 3 |
| status | IN PROGRESS - 4 of 40 slots due so far (last 2026-09-26 13:30). Snapshot 2026-09-26 13:49:56. Refresh after the next pass. |
| run_id | primary_20260926_v2.2.0_gha |

## states

- ON_DEMAND_ASAP: 128
- NO_STORE_REPORTED: 20
- ON_DEMAND_SCHEDULED: 28
- ON_DEMAND_UNAVAILABLE: 20

## error_types

- none

## uber_detection_rules

- logo-alt: 156

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 40
- ondemand_price_aud: 40
- standard_promise_text: 20
- standard_price_aud: 20
- notes: 128
- ondemand_detected_by: 40
- error_type: 196
- review_flag: 196

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 4
- first_slot: 2026-09-26 12:00
- last_slot: 2026-09-26 13:30
- postcodes: 49
- products: ['s26']
- expected_cells: 196
- observed_cells: 196
- coverage_pct: 100.0
- expected_slots_so_far: 4
- missing_cells: 0
- slots_with_no_rows: []

## postcodes_with_errors

- none

## run_ids

- primary_20260926_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
