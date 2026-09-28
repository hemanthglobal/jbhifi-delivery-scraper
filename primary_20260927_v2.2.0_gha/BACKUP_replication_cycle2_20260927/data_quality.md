STATUS: IN PROGRESS - 39 of 40 slots due so far (last 2026-09-28 11:00). Snapshot 2026-09-28 11:18:22. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 1323 |
| rows_after_dedup | 1323 |
| successful_requests | 1323 |
| valid_results_uber_offered | 1053 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 135 |
| no_availability_no_store (NO_STORE_REPORTED) | 135 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 21 |
| status | IN PROGRESS - 39 of 40 slots due so far (last 2026-09-28 11:00). Snapshot 2026-09-28 11:18:22. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 870
- NO_STORE_REPORTED: 135
- ON_DEMAND_UNAVAILABLE: 135
- ON_DEMAND_ASAP: 183

## error_types

- none

## uber_detection_rules

- logo-alt: 1053

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 270
- ondemand_price_aud: 270
- standard_promise_text: 135
- standard_price_aud: 135
- notes: 864
- ondemand_detected_by: 270
- error_type: 1323
- review_flag: 1323

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 27
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-28 11:00
- postcodes: 49
- products: ['s26']
- expected_cells: 1911
- observed_cells: 1323
- coverage_pct: 69.2
- expected_slots_so_far: 39
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
