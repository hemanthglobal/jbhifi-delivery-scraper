STATUS: IN PROGRESS - 18 of 40 slots due so far (last 2026-09-27 20:30). Snapshot 2026-09-27 20:50:02. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 294 |
| rows_after_dedup | 294 |
| successful_requests | 294 |
| valid_results_uber_offered | 234 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 30 |
| no_availability_no_store (NO_STORE_REPORTED) | 30 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 15 |
| status | IN PROGRESS - 18 of 40 slots due so far (last 2026-09-27 20:30). Snapshot 2026-09-27 20:50:02. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 234
- NO_STORE_REPORTED: 30
- ON_DEMAND_UNAVAILABLE: 30

## error_types

- none

## uber_detection_rules

- logo-alt: 234

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 60
- ondemand_price_aud: 60
- standard_promise_text: 30
- standard_price_aud: 30
- notes: 192
- ondemand_detected_by: 60
- error_type: 294
- review_flag: 294

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 6
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-27 20:30
- postcodes: 49
- products: ['s26']
- expected_cells: 882
- observed_cells: 294
- coverage_pct: 33.3
- expected_slots_so_far: 18
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
