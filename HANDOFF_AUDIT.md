# Handoff audit: collector v2.0.0 → v2.1.0

Written 2026-09-26 ~10:55 ACST, before any code change, by the "Python web
scraper GitHub Actions setup" session, on handoff from the
"Data-driven-decision-making" session.

## 1. Baseline

| Item | Value |
|---|---|
| Baseline file | `..\jbhifi_collect.py` (read from disk 2026-09-26 10:5x) |
| Version | `COLLECTOR_VERSION = "2.0.0"` |
| SHA-256 | `f7875da7b8167fb0df46f6e6aad2a554d6153b1d1ed63e8200decec8e5910f01`, identical to `jbhifi_collect_v2.0.0_FROZEN.py` |
| Offline tests | `..\test_edge_cases.py`: ALL EDGE-CASE CHECKS PASSED (run 10:52) |
| Live production run | PID 21840 runs the FROZEN copy, `--schedule --start-day 2026-09-27 --cycles 2`, from 27 Sep 07:00 to 29 Sep 06:00. Output goes to `Desktop\jbhifi_data\main_v2_20260927\`. **Not to be touched.** |

v2.0.0 already provides these, and all are preserved:
- `collector_version`, `run_id`, `slot`, `tz_offset`, `n_options`,
  `suggestion_selected` and `observation_state` columns (v1's 14 columns
  come first, unchanged)
- a raw JSONL record for **every** observation, including no-store and
  errors, with the page message, the screenshot names and the derived row
- panel-clip screenshots for every rendered observation, and full-page
  screenshots on the first pass and on every error
- a run manifest with the source SHA-256
- the exact-suggestion guard, the NoServingStore handling, BrowserSession
  relaunch and the Excel-lock CSV fallback

## 2. Observation-state logic (v2.0.0)

`observation_state(options, error, no_store)` returns exactly one of:

| State | Condition |
|---|---|
| `COLLECTION_ERROR` | exception, timeout, suburb not offered, or empty panel |
| `NO_STORE_REPORTED` | the `location-search-no-results` element is visible (JB's wording goes in `notes`) |
| `ON_DEMAND_UNAVAILABLE` | cards rendered, none passes `ondemand_evidence()` |
| `ON_DEMAND_ASAP` | Uber card and `promise_type()` returns ASAP ("minute" or "asap") |
| `ON_DEMAND_SCHEDULED` | Uber card and `promise_type()` returns SCHEDULED ("window", "schedul" or "hour") |
| `ON_DEMAND_UNCLASSIFIED` | Uber card with any other wording |

`ondemand_evidence()` tries these rules in order:
1. `logo-alt`: the img alt contains "uber"
2. `carrier-text`: the carrier text contains uber or on-demand
3. `service-label`: **no alt**, and the carrier is "scheduled" or "asap"
4. `promise-wording`: **no alt**, and the promise matches
   `\d+ hour window|within \d+ min`

## 3. Known parser bugs

| # | Bug | Evidence | v2.1.0 action |
|---|---|---|---|
| B1 | **Sony false positive.** Rule 3 accepts any logo-less "Scheduled" card. | Sony 65" Bravia 6 at 5000, 26 Sep 10:4x: a single card "Delivery available from 27 September / $59.00 / Scheduled", carrier_alt=None. v2 returns `ON_DEMAND_UNCLASSIFIED`, ondemand_shown=Y. | **Fix.** A logo-less card counts as Uber only if the service label AND Uber-specific promise wording BOTH match. Also add a `logo-src` rule (img src contains "uber"). A label-only or wording-only card is NOT Uber; it is flagged in a new `review_flag` column for manual audit, never dropped. |
| B2 | 6030 Clarkson: logos not rendered. | `jbhifi_screenshots\6030_20260923_004013.png` | v2 fixed this with rule 3. v2.1.0 keeps it detectable ("Scheduled" + "Choose a 2 hour window" satisfies label AND wording). Re-verify live with logos stripped. |
| B3 | **"Delivered within 2 hours" is classed SCHEDULED** because "hour" matches before any ASAP test. It is a delivery promise with no window to choose. | Live at 2000 Sydney, 26 Sep 10:39 (headless probe). `promise_type('Delivered within 2 hours') == 'SCHEDULED'`. | **NOT changed.** This affects the Q1 ASAP/SCHEDULED measure, and the lead said PI definitions stay as they are. The verbatim text is in `promise_text_verbatim`, so it can be reclassified at analysis. **Decision needed from the project lead.** |
| B4 | The promise-wording regex misses "within N hours". | as B3 | Folded into the B1 wording rule: `within \d+ (min|hour)` or `\d+ hour window`. Used only for Uber identification, not for ASAP/SCHEDULED. |
| B5 | Timestamps and slots use the machine's local clock. A GitHub runner is UTC, so slots would fire 9.5 h wrong. | code | Pin the process to `Australia/Adelaide` (`TZ` plus `time.tzset()` on Linux). On Windows, refuse to run if the clock offset isn't +0930 or +1030. |
| B6 | `run_id` is the wall-clock start time, which isn't deterministic across chunked jobs. | code | Change to `run_id = <study>_<cycle date>_v<version>`, which is the same for every chunk of one cycle. |
| B7 | No retry, no 403/429/Cloudflare detection, and nothing stops a failing pass from continuing. | code | Add bounded retries for transient errors only, a block detector that stops the run, and a consecutive-error guard that aborts the pass. |
| B8 | Headed Edge only. | `BrowserSession._launch` | Default to headless bundled Chromium. `--headed` / `--edge` flags reproduce the old behaviour. |
| B9 | Screenshot names don't include the product, so they could collide in a multi-product pass. | code | Add the product key to file names. |
| B10 | `audit_suggestions.py` calls `jc.enter_postcode`, which no longer exists. | code | Leave untouched (outside the new repo), but note it here. |

## 4. Files

**Created**, in the new folder `jbhifi-delivery-scraper\`, which becomes the GitHub repo:
- `scraper.py`: v2.1.0, derived from the v2.0.0 baseline above
- `combine.py`: merges chunk outputs, dedupes, writes the data-quality summary
- `tests\test_scraper.py`: offline checks (ported from `test_edge_cases.py` plus new ones)
- `requirements.txt`, `README.md`, `.gitignore`, `data\.gitkeep`
- `.github\workflows\scraper.yml` and `.github\workflows\collect-chunk.yml`
- `HANDOFF_AUDIT.md` (this file) and later `FREEZE_v2.1.0.md`

**Left untouched**, in `C:\Users\heman\Desktop\JB Hifi\`:
- `jbhifi_collect.py`
- `jbhifi_collect_v2.0.0_FROZEN.py`
- `FREEZE_v2.0.0.md`
- `test_edge_cases.py`
- `validate_v2_states.py`
- `validate_collector.py`
- `diagnose_remote.py`
- `audit_suggestions.py`
- `probe_suburb_typing.py`
- `jbhifi_delivery.py`
- `test_*.py`
- `archive\`
- `jbhifi_env\`

Also untouched: everything under `Desktop\jbhifi_data\`, including the live
run folder, and `Desktop\jbhifi_screenshots\`.

## 5. Data-separation rules

- v2.0.0 data (the local run from 27 to 29 Sep) and v2.1.0 data must never be
  pooled in one KPI calculation. Every row carries `collector_version`.
- Primary study rows (`study=primary`) and validation study rows
  (`study=validation`) go to different folders and CSVs. `combine.py`
  refuses to merge different studies or versions into one output.
- Raw outputs are never modified. `combine.py` writes new files only.
