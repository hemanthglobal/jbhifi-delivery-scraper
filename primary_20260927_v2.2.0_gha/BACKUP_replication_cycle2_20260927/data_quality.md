STATUS: COMPLETE - cycle 2026-09-27 finished; all 40 slots due. Exported 2026-09-28 11:48:39 (collector v2.2.0, run primary_20260927_v2.2.0_gha)

# Data quality: primary study, cycle 2026-09-27 (primary_20260927_v2.2.0_gha)

| Measure | Value |
|---|---|
| total_observations_attempted | 1372 |
| rows_after_dedup | 1372 |
| successful_requests | 1372 |
| valid_results_uber_offered | 1092 |
| no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE) | 140 |
| no_availability_no_store (NO_STORE_REPORTED) | 140 |
| failed_requests (COLLECTION_ERROR) | 0 |
| duplicate_records_removed | 0 |
| conflicting_duplicates | 0 |
| http_errors (5xx/403/429) | 0 |
| timeouts | 0 |
| rows_needing_retry | 22 |
| status | COMPLETE - cycle 2026-09-27 finished; all 40 slots due. Exported 2026-09-28 11:48:39 (collector v2.2.0, run primary_20260927_v2.2.0_gha) |
| run_id | primary_20260927_v2.2.0_gha |

## states

- ON_DEMAND_SCHEDULED: 881
- NO_STORE_REPORTED: 140
- ON_DEMAND_UNAVAILABLE: 140
- ON_DEMAND_ASAP: 211

## error_types

- none

## uber_detection_rules

- logo-alt: 1092

## review_flags

- none

## missing_values_in_measured_rows

- promise_text_verbatim: 280
- ondemand_price_aud: 280
- standard_promise_text: 140
- standard_price_aud: 140
- notes: 896
- ondemand_detected_by: 280
- error_type: 1372
- review_flag: 1372

## unexpected_missing

- ondemand_price_aud (Uber shown): 0
- standard_price_aud (options rendered): 0
- promise_text_verbatim (Uber shown): 0

## coverage

- slots: 28
- first_slot: 2026-09-27 18:00
- last_slot: 2026-09-28 11:30
- postcodes: 49
- products: ['s26']
- expected_cells: 1960
- observed_cells: 1372
- coverage_pct: 70.0
- expected_slots_so_far: 40
- missing_cells: 588
- slots_with_no_rows: ['2026-09-27 12:00', '2026-09-27 12:30', '2026-09-27 13:00', '2026-09-27 13:30', '2026-09-27 14:00', '2026-09-27 14:30', '2026-09-27 15:00', '2026-09-27 15:30', '2026-09-27 16:00', '2026-09-27 16:30', '2026-09-27 17:00', '2026-09-27 17:30']

## postcodes_with_errors

- none

## run_ids

- primary_20260927_v2.2.0_gha

Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site answers, not failures. COLLECTION_ERROR rows are kept (not discarded) and listed in failed_combined.csv; exclude them from rate denominators and report them as a limitation.
