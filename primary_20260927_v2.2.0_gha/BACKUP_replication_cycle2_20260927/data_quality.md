STATUS: IN PROGRESS - 19 of 40 slots due so far (last 2026-09-27 21:00). Snapshot 2026-09-27 21:18:42. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 343 |
| rows_after_dedup | 343 |
| successful_requests | 343 |
| valid_results_uber_offered | 273 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 35 |
| no_availability_no_store (NO_STORE_REPORTED) | 35 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 15 |
| status | IN PROGRESS - 19 of 40 slots due so far (last 2026-09-27 21:00). Snapshot 2026-09-27 21:18:42. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 273
- NO_STORE_REPORTED: 35
- ON_DEMAND_UNAVAILABLE: 35

## error_types

- none

## uber_detection_rules

- logo-alt: 273

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 70
- ondemand_price_aud: 70
- standard_promise_text: 35
- standard_price_aud: 35
- notes: 224
- ondemand_detected_by: 70
- error_type: 343
- review_flag: 343

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 7
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-27 21:00
- postcodes: 49
- products: ['s26']
- expected_cells: 931
- observed_cells: 343
- coverage_pct: 36.8
- expected_slots_so_far: 19
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
