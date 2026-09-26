STATUS: IN PROGRESS - 19 of 40 slots due so far (last 2026-09-26 21:00). Snapshot 2026-09-26 21:19:38. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-26 (primary_20260926_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 931 |
| rows_after_dedup | 931 |
| successful_requests | 931 |
| valid_results_uber_offered | 741 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 95 |
| no_availability_no_store (NO_STORE_REPORTED) | 95 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 6 |
| status | IN PROGRESS - 19 of 40 slots due so far (last 2026-09-26 21:00). Snapshot 2026-09-26 21:19:38. Refresh after the next pass. |
| run_id | primary_20260926_v2.2.0_gha |

## states

- ON_DEMAND_ASAP: 195
- NO_STORE_REPORTED: 95
- ON_DEMAND_SCHEDULED: 546
- ON_DEMAND_UNAVAILABLE: 95

## error_types

- none

## uber_detection_rules

- logo-alt: 741

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 190
- ondemand_price_aud: 190
- standard_promise_text: 95
- standard_price_aud: 95
- notes: 608
- ondemand_detected_by: 190
- error_type: 931
- review_flag: 931

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 19
- first_slot: 2026-09-26 12:00
- last_slot: 2026-09-26 21:00
- postcodes: 49
- products: ['s26']
- expected_cells: 931
- observed_cells: 931
- coverage_pct: 100.0
- expected_slots_so_far: 19
- missing_cells: 0
- slots_with_no_rows: []

## postcodes_with_errors

- none

## run_ids

- primary_20260926_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
