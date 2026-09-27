STATUS: IN PROGRESS - 31 of 40 slots due so far (last 2026-09-28 07:00). Snapshot 2026-09-28 07:19:24. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

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
| rows_needing_retry | 17 |
| status | IN PROGRESS - 31 of 40 slots due so far (last 2026-09-28 07:00). Snapshot 2026-09-28 07:19:24. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 741
- NO_STORE_REPORTED: 95
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
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-28 07:00
- postcodes: 49
- products: ['s26']
- expected_cells: 1519
- observed_cells: 931
- coverage_pct: 61.3
- expected_slots_so_far: 31
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
