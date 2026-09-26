# JB Hi-Fi delivery availability collector (v2.1.0)

This collects what JB Hi-Fi's public product page shows about delivery
options, including Uber on-demand, for set Australian postcodes at set
times of day. It feeds a university Data-Driven Decision Making
assignment. Data engineering only: no analysis lives here.

| Study | Design | Output | Use |
|---|---|---|---|
| **primary** | Samsung Galaxy S26 5G 256GB × 49 postcodes × 40 slots/day (07:00–23:00 every 30 min, 00:00–06:00 hourly, Adelaide time) | `data/primary/…` | Main analysis and PIs |
| **validation** | 4 products (S26, AirPods 5, HP 15 laptop, Sony 65" TV) × 12 postcodes (6 metro core + 6 regional) × 4 slots (09:00, 13:00, 17:00, 21:00) = 192 rows | `data/validation/…` | Is the pattern product-specific? **Never pooled into the primary PIs.** |

## Files

| File | What it is |
|---|---|
| `scraper.py` | The collector (Playwright, headless Chromium) |
| `combine.py` | Merges chunk outputs, removes duplicates, writes the data-quality summary |
| `tests/test_scraper.py` | Offline checks (no network) |
| `tests/live_states.py` | Live check of the UNAVAILABLE / logo-stripped / ERROR states |
| `.github/workflows/scraper.yml` | The workflow you run from the GitHub Actions tab |
| `.github/workflows/collect-chunk.yml` | One chunk job (called by `scraper.yml`) |
| `HANDOFF_AUDIT.md` | Audit of v2.0.0 and what changed |
| `FREEZE_v2.1.0.md` | Frozen version, hash and validation results |

## Outputs, per run folder

- `results.csv`: one row per observation. It's append-only and the source of truth.
- `raw_observations.jsonl`: every option card verbatim, one record per row, including errors.
- `failed_postcodes.csv`: every `COLLECTION_ERROR` row with its reason.
- `checkpoint.json`: progress and counters, rewritten after every row.
- `scraper.log`: the full log.
- `screenshots/`: panel clips for every rendered observation, plus full-page captures on errors.
- `manifest_*.json`: the exact version, SHA-256 and design used.

### `observation_state` values (one per row)

| State | Meaning |
|---|---|
| `ON_DEMAND_ASAP` | Uber card with minutes/ASAP wording |
| `ON_DEMAND_SCHEDULED` | Uber card with window/hour wording |
| `ON_DEMAND_UNCLASSIFIED` | Uber card with other wording |
| `ON_DEMAND_UNAVAILABLE` | delivery offered, but no Uber |
| `NO_STORE_REPORTED` | JB said "No available stores found…". This is a real answer, not a failure |
| `COLLECTION_ERROR` | nothing could be measured; see `error_type` and `notes` |

## Responsible use

- **One browser, one page at a time**, with 5–10 s random gaps. That's about one page load every 20–25 s.
- **Retries only for temporary faults** (timeouts, network errors, HTTP 5xx, browser crashes), at most 3 attempts with 20 s and 60 s back-off.
- **HTTP 429** makes the collector slow down (2 min, then 5 min) and then stop.
- **HTTP 403, a Cloudflare challenge, a CAPTCHA or "access denied"** stops the run immediately (exit code 3). Nothing is bypassed, rotated or spoofed.
- **Six errors in a row** abort the rest of that pass.
- robots.txt allows `/products/`. JB Hi-Fi's terms allow personal, non-commercial use. Keep the repository **private** and don't publish screenshots.

## Run locally (Windows, PowerShell)

```powershell
cd "$env:USERPROFILE\Desktop\JB Hifi\jbhifi-delivery-scraper"
..\jbhifi_env\Scripts\python.exe -m playwright install chromium
..\jbhifi_env\Scripts\python.exe tests\test_scraper.py
..\jbhifi_env\Scripts\python.exe scraper.py --study primary --test
..\jbhifi_env\Scripts\python.exe scraper.py --study validation --test
```

On Windows the machine clock must be Adelaide time; the script refuses to
run otherwise. If a run stops, re-run the **same command with the same
`--out-dir`**: finished observations are skipped, never duplicated.

---

## GitHub Actions: step by step (Windows + VS Code)

### 1. Install Git (once)

```powershell
winget install --id Git.Git -e
```

Close and reopen PowerShell, then set your name and email:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### 2. Create the repository on GitHub

1. Go to github.com, click **+** (top right), then **New repository**.
2. Name it `jbhifi-delivery-scraper` and choose **Private**.
3. Don't tick "Add a README". Click **Create repository**.

### 3. Push this folder

```powershell
cd "$env:USERPROFILE\Desktop\JB Hifi\jbhifi-delivery-scraper"
git init -b main
git add .
git status
git commit -m "JB Hi-Fi delivery collector v2.1.0"
git remote add origin https://github.com/YOUR-USERNAME/jbhifi-delivery-scraper.git
git push -u origin main
```

Check `git status` before committing: only code, tests, docs and
`data/.gitkeep` should be listed. `.gitignore` keeps collected data out.
The first `git push` opens a browser window to sign in to GitHub.

### 4. Run a test

1. Open the repo on github.com and go to the **Actions** tab.
2. Click **jbhifi-collector** on the left, then **Run workflow**.
3. Set **study** = `primary`, **mode** = `test`, and leave the rest.
4. Click **Run workflow**. It takes about 5 minutes.
5. Click the run, then the **test / collect** job, then **Run collector** to see the live log.

    The log shows each postcode, its state, and a line like
    `Processed: 5 / 8 | Valid: 3 | No store: 2 | Failed: 0 | Elapsed: 00:01:53`.
6. **Check for blocking.** If it says `STOPPED: the site is blocking automated access`,
    JB Hi-Fi is refusing GitHub's servers. Don't work around it; collect locally instead.

### 5. Download results

1. On the run's page, scroll to **Artifacts**.
2. Download `results-…` (the raw folders) and `combined-…` (the merged CSV and quality report).
3. Unzip them.

### 6. Run a full cycle

1. Go to **Run workflow** again and set **mode** = `full`.
2. Leave **cycle_date** blank for today, or enter one like `2026-10-01`.
3. Start it at the right time:
    - primary: **between 06:15 and 06:55 Adelaide time**
    - validation: **between 08:15 and 08:55**
4. Five chained jobs cover the day, each under GitHub's 6-hour limit. Your PC can be off.

### 7. Redo part of a cycle

Set **start_chunk** and **end_chunk**. Chunk times are listed at the top of
`scraper.yml`. Slots already in the past are skipped, so a failed chunk can
only be redone on a later day, at the same times.

### 8. Combine everything

```powershell
cd "$env:USERPROFILE\Desktop\JB Hifi\jbhifi-delivery-scraper"
..\jbhifi_env\Scripts\python.exe combine.py "C:\path\to\unzipped\artifacts" "C:\path\to\local\run" --out combined
```

This gives you one folder per study and version under `combined\`, each with
`results_combined.csv` and `data_quality.md`. Raw files are never changed.

### 9. Open in Tableau

1. **Connect → Text file →** `results_combined.csv`
2. In the data source grid, set **postcode** to **String**, then **Geographic Role → ZIP Code/Postcode**.
    If postcode is left as a number, Tableau sums it and the map breaks.
3. Set `timestamp` to **Date & Time**. Set `slot` to **Date & Time** as well, or keep it as a string for the heatmap.
4. Filter `observation_state` ≠ `COLLECTION_ERROR` for rates, and report the error count as a limitation.
5. **Never union the validation CSV into the primary one.**

### GitHub minutes

A private repo on a free account gets 2,000 Actions minutes a month.

| Run | Approx. minutes |
|---|---|
| Primary full cycle (about 24 h of chained jobs) | 1,450 |
| Validation cycle (08:30 → 21:20) | 800 |
| Test run | 5 each |

The GitHub Student Developer Pack gives 3,000 minutes a month.
