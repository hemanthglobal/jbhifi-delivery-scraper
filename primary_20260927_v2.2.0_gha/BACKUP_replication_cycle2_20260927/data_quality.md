STATUS: IN PROGRESS - 15 of 40 slots due so far (last 2026-09-27 19:00). Snapshot 2026-09-27 19:19:02. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 147 |
| rows_after_dedup | 147 |
| successful_requests | 147 |
| valid_results_uber_offered | 117 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 15 |
| no_availability_no_store (NO_STORE_REPORTED) | 15 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 5 |
| status | IN PROGRESS - 15 of 40 slots due so far (last 2026-09-27 19:00). Snapshot 2026-09-27 19:19:02. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 117
- NO_STORE_REPORTED: 15
- ON_DEMAND_UNAVAILABLE: 15

## error_types

- none

## uber_detection_rules

- logo-alt: 117

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 30
- ondemand_price_aud: 30
- standard_promise_text: 15
- standard_price_aud: 15
- notes: 96
- ondemand_detected_by: 30
- error_type: 147
- review_flag: 147

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 3
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-27 19:00
- postcodes: 49
- products: ['s26']
- expected_cells: 735
- observed_cells: 147
- coverage_pct: 20.0
- expected_slots_so_far: 15
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
