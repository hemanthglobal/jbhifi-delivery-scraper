"""
Combine collector outputs (chunk folders, unzipped GitHub artifacts, local
run folders) into one clean CSV per (study, collector_version), plus a data
quality summary. Raw files are only READ - nothing is modified or deleted.

  python combine.py <folder-or-results.csv> [more ...] --out combined

Finds every results.csv under the given paths. Writes, per group:

  combined/<study>_v<version>/results_combined.csv   deduplicated rows
  combined/<study>_v<version>/failed_combined.csv    every COLLECTION_ERROR row
  combined/<study>_v<version>/data_quality.md        human-readable summary
  combined/<study>_v<version>/data_quality.json      same, machine-readable
  combined/<study>_v<version>/sources.txt            which files were used

Studies and collector versions are NEVER mixed in one output: the primary
study feeds the PIs; the validation study and other versions are separate.

Deduplication key: (run_id, slot, product_key, postcode). Identical copies
(e.g. the same artifact downloaded twice) are dropped. If two DIFFERENT rows
share a key (should not happen), a measured row is preferred over a
COLLECTION_ERROR row, otherwise the earliest timestamp is kept; every such
conflict is listed in the summary.
"""

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import csv
import json
import os
import sys

KEY = ("run_id", "slot", "product_key", "postcode")
ON_DEMAND = ("ON_DEMAND_ASAP", "ON_DEMAND_SCHEDULED", "ON_DEMAND_UNCLASSIFIED")
MEASURE_COLUMNS = ("ondemand_shown", "promise_type", "standard_promise_text",
                   "standard_price_aud", "labelled_fastest")


def find_results(paths):
    out = []
    for p in map(Path, paths):
        if p.is_file() and p.name.endswith(".csv"):
            out.append(p)
        elif p.is_dir():
            out += sorted(p.rglob("results.csv"))
    return out


def read_rows(files):
    rows = []
    for f in files:
        with f.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                r["_source"] = str(f)
                rows.append(r)
    return rows


def dedupe(rows):
    by_key = defaultdict(list)
    for r in rows:
        by_key[tuple(r[k] for k in KEY)].append(r)
    kept, exact, conflicts = [], 0, []
    for key, group in by_key.items():
        uniq = {json.dumps({k: v for k, v in r.items() if k != "_source"},
                           sort_keys=True): r for r in group}
        exact += len(group) - len(uniq)
        cands = list(uniq.values())
        if len(cands) > 1:
            conflicts.append({"key": "|".join(key),
                              "states": [c["observation_state"] for c in cands],
                              "sources": [c["_source"] for c in cands]})
            measured = [c for c in cands if c["observation_state"] != "COLLECTION_ERROR"]
            cands = sorted(measured or cands, key=lambda c: c["timestamp"])
        kept.append(cands[0])
    kept.sort(key=lambda r: (r["slot"], r["postcode"], r["product_key"]))
    return kept, exact, conflicts


def quality(rows, exact_dups, conflicts, columns):
    states = Counter(r["observation_state"] for r in rows)
    errors = [r for r in rows if r["observation_state"] == "COLLECTION_ERROR"]
    measured = [r for r in rows if r["observation_state"] != "COLLECTION_ERROR"]
    err_types = Counter(r.get("error_type") or "unrecorded" for r in errors)
    slots = sorted({r["slot"] for r in rows})
    postcodes = sorted({r["postcode"] for r in rows})
    products = sorted({r["product_key"] for r in rows})
    cells = Counter((r["slot"], r["postcode"], r["product_key"]) for r in rows)
    expected = len(slots) * len(postcodes) * len(products)

    missing = {}
    for col in columns:
        n = sum(1 for r in measured if (r.get(col) or "") == "")
        if n:
            missing[col] = n
    # Empty is EXPECTED for some columns in some states; report the ones
    # that are not explained by the state.
    unexpected_missing = {
        "ondemand_price_aud (Uber shown)": sum(
            1 for r in measured if r["ondemand_shown"] == "Y"
            and r["ondemand_price_aud"] == ""),
        "standard_price_aud (options rendered)": sum(
            1 for r in measured if r["observation_state"] != "NO_STORE_REPORTED"
            and r["standard_price_aud"] == ""),
        "promise_text_verbatim (Uber shown)": sum(
            1 for r in measured if r["ondemand_shown"] == "Y"
            and r["promise_text_verbatim"] == ""),
    }
    per_pc_err = Counter(r["postcode"] for r in errors)
    return {
        "total_observations_attempted": len(rows) + exact_dups,
        "rows_after_dedup": len(rows),
        "successful_requests": len(measured),
        "valid_results_uber_offered": sum(states[s] for s in ON_DEMAND),
        "no_uber_but_other_delivery (ON_DEMAND_UNAVAILABLE)": states["ON_DEMAND_UNAVAILABLE"],
        "no_availability_no_store (NO_STORE_REPORTED)": states["NO_STORE_REPORTED"],
        "failed_requests (COLLECTION_ERROR)": len(errors),
        "duplicate_records_removed": exact_dups,
        "conflicting_duplicates": len(conflicts),
        "http_errors (5xx/403/429)": sum(err_types[t] for t in
                                         ("http_5xx", "blocked", "rate_limited")),
        "timeouts": err_types["timeout"],
        "error_types": dict(err_types),
        "states": dict(states),
        "rows_needing_retry": sum(1 for r in rows if str(r.get("attempts") or "1") not in ("1", "1.0")),
        "review_flags": dict(Counter(r["review_flag"] for r in rows if r.get("review_flag"))),
        "uber_detection_rules": dict(Counter(r["ondemand_detected_by"] for r in rows
                                             if r.get("ondemand_detected_by"))),
        "missing_values_in_measured_rows": missing,
        "unexpected_missing": unexpected_missing,
        "coverage": {
            "slots": len(slots), "first_slot": slots[0] if slots else None,
            "last_slot": slots[-1] if slots else None,
            "postcodes": len(postcodes), "products": products,
            "expected_cells": expected, "observed_cells": len(cells),
            "coverage_pct": round(100 * len(cells) / expected, 1) if expected else 0,
        },
        "postcodes_with_errors": dict(per_pc_err.most_common()),
        "run_ids": sorted({r["run_id"] for r in rows}),
        "conflicts": conflicts,
    }


def write_md(path, study, version, q):
    lines = [f"# Data quality: {study} ({version})", ""]
    rows = [(k, v) for k, v in q.items() if not isinstance(v, (dict, list))]
    lines += ["| Measure | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows]
    for k in ("states", "error_types", "uber_detection_rules", "review_flags",
              "missing_values_in_measured_rows", "unexpected_missing",
              "coverage", "postcodes_with_errors"):
        lines += ["", f"## {k}", ""]
        if q[k]:
            lines += [f"- {a}: {b}" for a, b in q[k].items()]
        else:
            lines.append("- none")
    lines += ["", "## run_ids", ""] + [f"- {r}" for r in q["run_ids"]]
    if q["conflicts"]:
        lines += ["", "## conflicting duplicates", ""] + [
            f"- {c['key']}: {c['states']}" for c in q["conflicts"]]
    lines += ["", "Notes: NO_STORE_REPORTED and ON_DEMAND_UNAVAILABLE are real site "
              "answers, not failures. COLLECTION_ERROR rows are kept (not discarded) "
              "and listed in failed_combined.csv; exclude them from rate "
              "denominators and report them as a limitation."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _atomic_write_text(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except PermissionError:
        # target open in Excel/Tableau on Windows: leave it, write beside it
        alt = path.with_name(path.stem + "_NEW" + path.suffix)
        os.replace(tmp, alt)


def _atomic_write_csv(path, columns, rows):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore",
                           quoting=csv.QUOTE_NONNUMERIC)
        w.writeheader()
        for r in rows:
            w.writerow({k: _num(k, r.get(k, "")) for k in columns})
    try:
        os.replace(tmp, path)
    except PermissionError:
        os.replace(tmp, path.with_name(path.stem + "_NEW" + path.suffix))


def export_run(results_csv, run_id, out_dir, expected_slots, postcodes,
               products, status, title):
    """Analysis-ready export of ONE run (= one cycle) from a raw results.csv.

    Reads only. Writes (atomically, so Tableau can re-read mid-run):
      results_clean.csv     every row of this run, deduplicated, sorted,
                            + slot_index / slot_time (derived from `slot`)
      results_measured.csv  same, COLLECTION_ERROR rows excluded (PI
                            denominators); errors stay in results_clean.csv
      failed.csv            the COLLECTION_ERROR rows
      data_quality.md/.json counts, states, coverage vs the EXPECTED grid,
                            missing cells listed (skipped slots show up here)
      STATUS.txt            `status` + timestamp

    expected_slots: "YYYY-MM-DD HH:MM" strings that should exist by now.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in read_rows([Path(results_csv)]) if r["run_id"] == run_id]
    kept, exact, conflicts = dedupe(rows)
    columns = list(csv.DictReader(Path(results_csv).open(encoding="utf-8")).fieldnames)
    slot_pos = {s: i for i, s in enumerate(expected_slots)}
    for r in kept:
        r["slot_index"] = slot_pos.get(r["slot"], "")
        r["slot_time"] = r["slot"][-5:]
    ext_cols = columns + ["slot_index", "slot_time"]
    _atomic_write_csv(out_dir / "results_clean.csv", ext_cols, kept)
    _atomic_write_csv(out_dir / "results_measured.csv", ext_cols,
                      [r for r in kept if r["observation_state"] != "COLLECTION_ERROR"])
    _atomic_write_csv(out_dir / "failed.csv", ext_cols,
                      [r for r in kept if r["observation_state"] == "COLLECTION_ERROR"])

    q = quality(kept, exact, conflicts, columns)
    seen = {(r["slot"], r["postcode"], r["product_key"]) for r in kept}
    expected = [(s, pc, pk) for s in expected_slots for pc in postcodes for pk in products]
    missing = [c for c in expected if c not in seen]
    q["coverage"].update({
        "expected_slots_so_far": len(expected_slots),
        "expected_cells": len(expected),
        "observed_cells": len(expected) - len(missing),
        "coverage_pct": round(100 * (len(expected) - len(missing)) / len(expected), 1)
        if expected else 0,
        "missing_cells": len(missing),
        "slots_with_no_rows": [s for s in expected_slots
                               if not any(c[0] == s for c in seen)],
    })
    q["missing_cell_list"] = [" ".join(c) for c in missing[:500]]
    q["status"] = status
    q["run_id"] = run_id
    _atomic_write_text(out_dir / "data_quality.json", json.dumps(q, indent=2))
    tmp_md = out_dir / "data_quality.md.build"
    write_md(tmp_md, title, run_id, q)
    body = f"STATUS: {status}\n\n" + tmp_md.read_text(encoding="utf-8")
    tmp_md.unlink()
    _atomic_write_text(out_dir / "data_quality.md", body)
    _atomic_write_text(out_dir / "STATUS.txt", status + "\n")
    return q


def _obs_key(r):
    return "|".join(str(r.get(k, "")) for k in KEY)


def seed(src, dest, run_id):
    """Copy (never move) earlier chunks' raw rows of `run_id` into `dest`,
    so a CI chunk continues the cycle's results.csv / raw JSONL. Duplicates
    are dropped by observation key. Returns the number of rows seeded."""
    src, dest = Path(src), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    rows, seen = [], set()
    files = [f for f in find_results([src]) if dest not in f.parents]
    columns = None
    for f in files:
        with f.open(newline="", encoding="utf-8") as fh:
            rd = csv.DictReader(fh)
            columns = columns or rd.fieldnames
            for r in rd:
                if r["run_id"] == run_id and _obs_key(r) not in seen:
                    seen.add(_obs_key(r))
                    rows.append(r)
    if rows:
        rows.sort(key=lambda r: r["timestamp"])
        with (dest / "results.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=columns, quoting=csv.QUOTE_NONNUMERIC)
            w.writeheader()
            for r in rows:
                w.writerow({k: _num(k, r[k]) for k in columns})
    jseen, jlines = set(), []
    for f in sorted(src.rglob("raw_observations.jsonl")):
        if dest in f.parents:
            continue
        for line in f.open(encoding="utf-8"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            k = "|".join(str(d.get(x, "")) for x in ("run_id", "slot", "product_key", "postcode"))
            if d.get("run_id") == run_id and k not in jseen:
                jseen.add(k)
                jlines.append(line if line.endswith("\n") else line + "\n")
    if jlines:
        (dest / "raw_observations.jsonl").write_text("".join(jlines), encoding="utf-8")
    return len(rows)


def export_cycle(src, study, cycle_date, run_id, name, out):
    """Final whole-cycle export from every results.csv under `src`."""
    from datetime import datetime
    import scraper
    day = datetime.strptime(cycle_date, "%Y-%m-%d").date()
    slots = scraper.slots_for(study, day)
    cfg = scraper.STUDIES[study]
    merged = Path(out) / f"_merged_{run_id}"
    n = seed(src, merged, run_id)
    exp_dir = Path(out) / f"{name}_{day:%Y%m%d}"
    last_done = datetime.now() > slots[-1]
    status = ("COMPLETE" if last_done else "PARTIAL") + (
        f" - cycle {cycle_date} ({study}), final export built "
        f"{datetime.now():%Y-%m-%d %H:%M:%S}, {n} raw rows, run {run_id}")
    if n == 0:
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "STATUS.txt").write_text("NO DATA - " + status + "\n", encoding="utf-8")
        print(f"no rows for {run_id}")
        return None
    q = export_run(merged / "results.csv", run_id, exp_dir,
                   [s.strftime("%Y-%m-%d %H:%M") for s in slots],
                   cfg["postcodes"], cfg["products"], status,
                   f"{study} study, cycle {cycle_date}")
    if last_done:
        (exp_dir / "CYCLE_COMPLETE.txt").write_text(
            status + f"\ncoverage {q['coverage']['observed_cells']}/"
                     f"{q['coverage']['expected_cells']} "
                     f"({q['coverage']['coverage_pct']}%)\n", encoding="utf-8")
    print(f"{exp_dir}: {q['rows_after_dedup']} rows, coverage "
          f"{q['coverage']['observed_cells']}/{q['coverage']['expected_cells']}, "
          f"states {q['states']}")
    return q


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ["--seed"]:
        # combine.py --seed <src> <dest> <run_id>
        n = seed(argv[1], argv[2], argv[3])
        print(f"seeded {n} earlier row(s) of {argv[3]} into {argv[2]}")
        return 0
    if argv[:1] == ["--export-cycle"]:
        # combine.py --export-cycle <src> <study> <cycle_date> <run_id> <name> <out>
        export_cycle(*argv[1:7])
        return 0
    ap = argparse.ArgumentParser(description="Combine collector outputs.")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", type=Path, default=Path("combined"))
    args = ap.parse_args(argv)

    files = find_results(args.paths)
    if not files:
        sys.exit("no results.csv found under the given paths")
    rows = read_rows(files)
    columns = [c for c in csv.DictReader(files[0].open(encoding="utf-8")).fieldnames]

    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("study") or "unknown", r.get("collector_version") or "unknown")].append(r)
    if len(groups) > 1:
        print(f"NOTE: {len(groups)} study/version groups found - written separately, "
              f"never mixed: {sorted(groups)}")

    for (study, version), grp in sorted(groups.items()):
        kept, exact, conflicts = dedupe(grp)
        out = args.out / f"{study}_v{version}"
        out.mkdir(parents=True, exist_ok=True)
        with (out / "results_combined.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore",
                               quoting=csv.QUOTE_NONNUMERIC)
            w.writeheader()
            for r in kept:
                w.writerow({k: _num(k, r.get(k, "")) for k in columns})
        with (out / "failed_combined.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore",
                               quoting=csv.QUOTE_NONNUMERIC)
            w.writeheader()
            for r in kept:
                if r["observation_state"] == "COLLECTION_ERROR":
                    w.writerow({k: _num(k, r.get(k, "")) for k in columns})
        q = quality(kept, exact, conflicts, columns)
        (out / "data_quality.json").write_text(json.dumps(q, indent=2), encoding="utf-8")
        write_md(out / "data_quality.md", study, version, q)
        (out / "sources.txt").write_text(
            "\n".join(sorted({r["_source"] for r in grp})) + "\n", encoding="utf-8")
        print(f"{study} v{version}: {len(grp)} rows read, {exact} exact duplicate(s) "
              f"removed, {len(conflicts)} conflict(s), {len(kept)} written -> {out}")
    return 0


def _num(col, v):
    """Keep prices / counts numeric (unquoted) so Tableau reads measures;
    everything else - postcode included - stays a quoted string."""
    if col in ("ondemand_price_aud", "standard_price_aud", "n_options", "attempts") and v != "":
        try:
            return float(v) if "." in v else int(v)
        except ValueError:
            return v
    return v


if __name__ == "__main__":
    sys.exit(main())
