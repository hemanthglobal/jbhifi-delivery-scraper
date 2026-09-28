STATUS: IN PROGRESS - 37 of 40 slots due so far (last 2026-09-28 10:00). Snapshot 2026-09-28 10:18:39. Refresh after the next pass.

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

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
| rows_needing_retry | 19 |
| status | IN PROGRESS - 37 of 40 slots due so far (last 2026-09-28 10:00). Snapshot 2026-09-28 10:18:39. Refresh after the next pass. |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 848
- NO_STORE_REPORTED: 125
- ON_DEMAND_UNAVAILABLE: 125
- ON_DEMAND_ASAP: 127

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
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-28 10:00
- postcodes: 49
- products: ['s26']
- expected_cells: 1813
- observed_cells: 1225
- coverage_pct: 67.6
- expected_slots_so_far: 37
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
