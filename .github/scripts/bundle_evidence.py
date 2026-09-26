"""
Package one collector run's artifacts into a single evidence folder.
COPY ONLY: every file is copied byte-for-byte (shutil.copy2); nothing that
was downloaded is modified, renamed in place or deleted.

  python bundle_evidence.py <downloaded_artifacts_dir> <out_dir> <bundle_name>
         <source_run_id> <source_run_url> <source_conclusion> <head_sha>
         <scraper_sha256_at_head_sha>

<downloaded_artifacts_dir> holds one sub-folder per artifact (as written by
actions/download-artifact without merge-multiple).
"""

from pathlib import Path
import csv
import hashlib
import json
import shutil
import sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def copytree(src, dst):
    for f in sorted(p for p in Path(src).rglob("*") if p.is_file()):
        target = Path(dst) / f.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)


def csv_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    (src, out, name, run_id, run_url, conclusion, head_sha, head_scraper_sha) = sys.argv[1:9]
    src, out = Path(src), Path(out) / name
    out.mkdir(parents=True, exist_ok=True)
    arts = sorted(p for p in src.iterdir() if p.is_dir())
    finals = [a for a in arts if "-FINAL-" in a.name]
    chunks = [a for a in arts if a.name.startswith("results-")]
    exports = [a for a in arts if "-after-chunk" in a.name]

    # 1. originals, copied unchanged
    for a in finals:
        copytree(a, out / "final_export" / a.name)
    for a in chunks:
        copytree(a, out / "chunks" / a.name)
    for a in exports:
        copytree(a, out / "exports_after_each_chunk" / a.name)

    # 2. the complete raw dataset = the cumulative results.csv/JSONL with the
    #    most rows (normally the last chunk's), copied unchanged to raw/
    best = None
    for a in chunks:
        for r in a.rglob("results.csv"):
            n = len(csv_rows(r))
            if best is None or n > best[0] or (n == best[0] and a.name > best[1].name):
                best = (n, a, r)
    raw_note = "no raw results.csv found"
    raw_rows, jsonl_n = 0, 0
    if best:
        raw_rows, art, rcsv = best
        (out / "raw").mkdir(exist_ok=True)
        shutil.copy2(rcsv, out / "raw" / "results.csv")
        rj = rcsv.parent / "raw_observations.jsonl"
        if rj.exists():
            shutil.copy2(rj, out / "raw" / "raw_observations.jsonl")
            jsonl_n = sum(1 for _ in rj.open(encoding="utf-8"))
        raw_note = f"copied from {art.name}/{rcsv.relative_to(art).as_posix()}"

    # 3. manifests (copies) and collector identity
    mans = []
    (out / "manifests").mkdir(exist_ok=True)
    for a in chunks:
        for m in sorted(a.rglob("manifest_*.json")):
            dst = out / "manifests" / f"{a.name}__{m.name}"
            shutil.copy2(m, dst)
            d = json.loads(m.read_text(encoding="utf-8"))
            mans.append((a.name, m.name, d.get("run_id"), d.get("collector_version"),
                         d.get("collector_sha256"), d.get("started"),
                         (d.get("github_run") or {}).get("GITHUB_SHA")))
    versions = sorted({m[3] for m in mans if m[3]})
    shas = sorted({m[4] for m in mans if m[4]})

    # 4. checks (read-only)
    clean_rows = None
    complete = []
    for a in finals:
        for f in a.rglob("results_clean.csv"):
            clean_rows = len(csv_rows(f))
        complete += [c.read_text(encoding="utf-8").strip() for c in a.rglob("CYCLE_COMPLETE.txt")]
    keys = set()
    if best:
        keys = {(r["run_id"], r["slot"], r["product_key"], r["postcode"]) for r in csv_rows(best[2])}
    panels = sum(1 for a in chunks for _ in a.rglob("screenshots/panels/*.png"))
    fulls = sum(1 for a in chunks for p in a.rglob("screenshots/*.png") if p.parent.name == "screenshots")
    errors = sum(1 for a in chunks for p in a.rglob("screenshots/*_ERROR.png"))

    checks = [
        ("raw JSONL records == raw CSV rows", jsonl_n == raw_rows, f"{jsonl_n} vs {raw_rows}"),
        ("raw CSV has no duplicate observation keys", len(keys) == raw_rows, f"{len(keys)} unique of {raw_rows}"),
        ("results_clean.csv rows == raw rows", clean_rows == raw_rows, f"{clean_rows} vs {raw_rows}"),
        ("CYCLE_COMPLETE.txt present", bool(complete), "yes" if complete else "NO"),
        ("single collector version", len(versions) == 1, ", ".join(versions) or "-"),
        ("manifest SHA-256 == scraper.py at run commit",
         shas == [head_scraper_sha], f"manifest {shas} / commit {head_scraper_sha}"),
    ]

    # 5. index + checksums
    lines = [f"# {name}", "",
             "Evidence bundle for PRIMARY CYCLE 1 (Sat 26 Sep 2026 12:00 -> Sun 27 Sep 11:30, "
             "Australia/Adelaide). Built automatically on GitHub Actions after the collection "
             "run finished. **Copy only** - every file below is an unmodified copy of a file "
             "from the collection run's artifacts; SHA256SUMS.txt lists every file.", "",
             "| Item | Value |", "|---|---|",
             f"| Source run | {run_url} (id {run_id}) |",
             f"| Source run conclusion | {conclusion} |",
             f"| Source commit | {head_sha} |",
             f"| Collector version | {', '.join(versions) or '-'} |",
             f"| Collector SHA-256 (manifests) | {', '.join(shas) or '-'} |",
             f"| scraper.py SHA-256 at source commit | {head_scraper_sha} |",
             f"| Raw rows (raw/results.csv) | {raw_rows} ({raw_note}) |",
             f"| Raw JSONL records | {jsonl_n} |",
             f"| results_clean.csv rows | {clean_rows} |",
             f"| Panel-clip screenshots | {panels} |",
             f"| Full-page screenshots (all) / of which _ERROR | {fulls} / {errors} |",
             f"| CYCLE_COMPLETE.txt | {' | '.join(complete) or 'NOT PRESENT'} |",
             "", "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {c} | {'PASS' if ok else 'CHECK'} | {d} |" for c, ok, d in checks]
    lines += ["", "## Layout", "",
              "- `final_export/<artifact>/ASSIGNMENT_DATASET_cycle1_20260926/` - results_clean.csv, "
              "results_measured.csv, failed.csv, data_quality.md/.json, STATUS.txt, CYCLE_COMPLETE.txt",
              "- `raw/results.csv`, `raw/raw_observations.jsonl` - the complete raw cycle (cumulative copy)",
              "- `chunks/results-primary-chunkN-attemptM/` - each chunk artifact unchanged: its raw "
              "files, scraper.log, checkpoint.json, failed_postcodes.csv, manifest and `screenshots/` "
              "(`panels/` = one clip per rendered observation; `*_ERROR.png` = failed attempts)",
              "- `exports_after_each_chunk/` - the assignment export as it stood after each chunk",
              "- `manifests/` - copies of every manifest (collector version, SHA-256, GitHub run)",
              "", "## Tracing one observation", "",
              "CSV key (run_id, slot, product_key, postcode) -> the JSONL record with the same four "
              "fields (its `row` repeats the CSV row) -> its `screenshots` list -> the file under "
              "`chunks/<chunk covering that slot>/.../screenshots/`. Chunk slots: 1 = 12:00-16:00, "
              "2 = 16:30-21:00, 3 = 21:30-02:00, 4 = 03:00-07:00, 5 = 07:30-11:30.",
              "", "## Manifests", "", "| Artifact | File | run_id | version | SHA-256 | started | commit |",
              "|---|---|---|---|---|---|---|"]
    lines += [f"| {' | '.join(str(x) for x in m)} |" for m in mans]
    (out / "README_EVIDENCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sums = [f"{sha256(p)}  {p.relative_to(out).as_posix()}"
            for p in sorted(out.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.txt"]
    (out / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print("\n".join(lines[:22]))
    print(f"{len(sums)} files checksummed")


if __name__ == "__main__":
    main()
