STATUS: IN PROGRESS - 28 of 40 slots due so far (last 2026-09-28 04:00). Snapshot 2026-09-28 04:19:14. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 784 |
| rows_after_dedup | 784 |
| successful_requests | 784 |
| valid_results_uber_offered | 624 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 80 |
| no_availability_no_store (NO_STORE_REPORTED) | 80 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 17 |
| status | IN PROGRESS - 28 of 40 slots due so far (last 2026-09-28 04:00). Snapshot 2026-09-28 04:19:14. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 624
- NO_STORE_REPORTED: 80
- ON_DEMAND_UNAVAILABLE: 80

## error_types

- none

## uber_detection_rules

- logo-alt: 624

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 160
- ondemand_price_aud: 160
- standard_promise_text: 80
- standard_price_aud: 80
- notes: 512
- ondemand_detected_by: 160
- error_type: 784
- review_flag: 784

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 16
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-28 04:00
- postcodes: 49
- products: ['s26']
- expected_cells: 1372
- observed_cells: 784
- coverage_pct: 57.1
- expected_slots_so_far: 28
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
