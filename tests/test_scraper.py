"""
Offline checks for scraper.py (no network, no browser).

  python tests/test_scraper.py

  A  schedule + chunks          E  retries / block handling (fake pages)
  B  Uber evidence rules        F  CSV / resume / checkpoint
  C  real-card regression       G  pass abort, deterministic run ids
  D  row schema
  P  parity with the frozen v2.0.0 collector (only when it is present)
"""

from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import importlib.util
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scraper as sc  # noqa: E402

FAILURES = []


def check(label, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"         got  {got!r}\n         want {want!r}")
        FAILURES.append(label)


# ---------------------------------------------------------------- A
print("A. SCHEDULE + CHUNKS")
DAY = date(2026, 9, 30)
slots = sc.slots_for("primary", DAY)
check("primary: 40 slots", len(slots), 40)
check("primary: first 12:00", slots[0].strftime("%H:%M"), "12:00")
check("primary: idx 22 is 23:00 same day", slots[22], datetime(2026, 9, 30, 23, 0))
check("primary: idx 23 is 00:00 next day", slots[23], datetime(2026, 10, 1, 0, 0))
check("primary: idx 30 is 07:00 next day", slots[30], datetime(2026, 10, 1, 7, 0))
check("primary: last 11:30 next day", slots[-1], datetime(2026, 10, 1, 11, 30))
V21_TIMES = sorted([f"{h:02d}:{m:02d}" for h in range(7, 23) for m in (0, 30)] + ["23:00"]
                   + [f"{h:02d}:00" for h in range(0, 7)])
check("primary: same 40 clock times as v2.1.0, just rotated",
      sorted(s.strftime("%H:%M") for s in slots), V21_TIMES)
check("primary: strictly increasing", all(a < b for a, b in zip(slots, slots[1:])), True)
v = sc.slots_for("validation", DAY)
check("validation: 4 slots", [s.strftime("%H:%M") for s in v],
      ["09:00", "13:00", "17:00", "21:00"])
for study in sc.STUDIES:
    ch = sc.STUDIES[study]["chunks"]
    covered = [i for lo, hi in ch for i in range(lo, hi + 1)]
    n = len(sc.slots_for(study, DAY))
    check(f"{study}: chunks partition 0..{n - 1} in order", covered, list(range(n)))
# Each primary chunk, run back to back, must fit a 6 h job: (gap from the
# previous chunk's last pass end, or 45 min for chunk 1) + span + 30 min pass.
PASS = timedelta(minutes=30)
prev_end = None
for k, (lo, hi) in enumerate(sc.STUDIES["primary"]["chunks"], 1):
    start = slots[lo] - timedelta(minutes=45) if prev_end is None else prev_end
    end = slots[hi] + PASS
    check(f"primary chunk {k} fits in 5.5 h ({(end - start)})",
          end - start <= timedelta(hours=5, minutes=30), True)
    prev_end = end
check("current_cycle_day at 03:00 -> yesterday's cycle",
      sc.current_cycle_day("primary", datetime(2026, 10, 1, 3, 0)), DAY)
check("current_cycle_day at 11:50 (before noon) -> yesterday's cycle still running",
      sc.current_cycle_day("primary", datetime(2026, 10, 1, 11, 30)), DAY)
check("current_cycle_day at 11:55 -> today's noon cycle",
      sc.current_cycle_day("primary", datetime(2026, 10, 1, 11, 55)), date(2026, 10, 1))
check("parse_range 0-9", sc.parse_range("0-9", 40), list(range(10)))
check("parse_range single", sc.parse_range("7", 40), [7])

# ---------------------------------------------------------------- B
print("B. UBER EVIDENCE")
uber_logo = {"carrier": "Scheduled", "carrier_alt": "Uber logo",
             "promise": "Choose a 2 hour window", "price": "$11.99", "tags": []}
asap_logo = {"carrier": "ASAP", "carrier_alt": "Uber logo",
             "promise": "Delivered within 90 minutes", "price": "$11.99", "tags": ["FASTEST"]}
clarkson = {"carrier": "Scheduled", "carrier_alt": None,
            "promise": "Choose a 2 hour window", "price": "$11.99", "tags": ["FASTEST"]}
asap_nologo = {"carrier": "ASAP", "carrier_alt": None,
               "promise": "Delivered within 90 minutes", "price": "$11.99", "tags": []}
two_hours_nologo = {"carrier": "ASAP", "carrier_alt": None,
                    "promise": "Delivered within 2 hours", "price": "$11.99", "tags": []}
sony = {"carrier": "Scheduled", "carrier_alt": None,
        "promise": "Delivery available from 27 September", "price": "$59.00",
        "tags": ["CHEAP + FAST"]}
express = {"carrier": "Express", "carrier_alt": "Toll Priority logo",
           "promise": "Delivered within 3 business days", "price": "$12.99",
           "tags": ["FASTEST"]}
auspost_window = {"carrier": "Scheduled", "carrier_alt": "Australia Post logo",
                  "promise": "Choose a 2 hour window", "price": "$11.99", "tags": []}
wording_only = {"carrier": None, "carrier_alt": None,
                "promise": "Choose a 2 hour window", "price": "$11.99", "tags": []}
src_only = {"carrier": "Scheduled", "carrier_alt": "",
            "carrier_img_src": "https://cdn.example/uber-logo.svg",
            "promise": "Choose a 2 hour window", "price": "$11.99", "tags": []}
check("logo alt -> logo-alt", sc.ondemand_evidence(uber_logo), "logo-alt")
check("ASAP with logo -> logo-alt", sc.ondemand_evidence(asap_logo), "logo-alt")
check("img src only -> logo-src", sc.ondemand_evidence(src_only), "logo-src")
check("6030 Clarkson logo-less window -> label+wording",
      sc.ondemand_evidence(clarkson), "label+wording")
check("logo-less 90 minutes -> label+wording", sc.ondemand_evidence(asap_nologo), "label+wording")
check("logo-less 'within 2 hours' -> label+wording",
      sc.ondemand_evidence(two_hours_nologo), "label+wording")
check("SONY 'Scheduled' $59 card is NOT Uber", sc.ondemand_evidence(sony), None)
check("Sony card gets a review flag", sc.review_flag([sony]),
      "LOGOLESS_SCHEDULED_CARD_NOT_UBER_WORDING")
check("Express FASTEST is not Uber", sc.ondemand_evidence(express), None)
check("non-Uber logo never reclassified by wording", sc.ondemand_evidence(auspost_window), None)
check("wording without label or logo is not Uber", sc.ondemand_evidence(wording_only), None)
check("...but is flagged for review", sc.review_flag([wording_only]),
      "UBER_WORDING_WITHOUT_LOGO_OR_LABEL")
check("real Uber card gets no review flag", sc.review_flag([uber_logo, express]), "")
check("Sony page state = ON_DEMAND_UNAVAILABLE",
      sc.observation_state([sony]), sc.ON_DEMAND_UNAVAILABLE)
check("Clarkson page state = ON_DEMAND_SCHEDULED",
      sc.observation_state([express, clarkson]), sc.ON_DEMAND_SCHEDULED)
check("ASAP page state", sc.observation_state([asap_logo]), sc.ON_DEMAND_ASAP)
check("B3 kept: 'within 2 hours' still classes SCHEDULED (PI unchanged)",
      sc.promise_type("Delivered within 2 hours"), "SCHEDULED")

# ---------------------------------------------------------------- C
print("C. REAL-CARD REGRESSION")
cards = json.loads((ROOT / "tests" / "fixtures_real_cards.json").read_text(encoding="utf-8"))
check("fixture has real card sets", len(cards) >= 10, True)
for c in cards:
    state = sc.observation_state(c["options"])
    promises = " ".join(o["promise"] or "" for o in c["options"])
    has_uber_logo = any("uber" in (o["carrier_alt"] or "").lower() for o in c["options"])
    label = f"{c['postcode']} {(c['product_url'] or '')[-24:]} -> {state}"
    if (c["product_url"] or "").endswith("tv-with-gemini-2026"):
        check(label + " (Sony: not Uber)", state, sc.ON_DEMAND_UNAVAILABLE)
    elif has_uber_logo:
        check(label + " (logo present: Uber found)", state.startswith("ON_DEMAND_") and
              state != sc.ON_DEMAND_UNAVAILABLE, True)
    elif any(o["carrier"] in ("ASAP", "Scheduled") for o in c["options"]):
        check(label + " (logo stripped: Uber still found)",
              state in (sc.ON_DEMAND_ASAP, sc.ON_DEMAND_SCHEDULED), True)
    else:
        check(label + " (no Uber card)", state, sc.ON_DEMAND_UNAVAILABLE)

# ---------------------------------------------------------------- D
print("D. ROW SCHEMA")
sc.RUN.update({"run_id": "primary_20260930_v2.2.0", "slot": "2026-09-30 07:00",
               "study": "primary", "product_key": "s26"})
row = sc.build_csv_row("5022", [express, uber_logo], suggestion="Grange SA 5022")
check("row has every column", sorted(row), sorted(sc.COLUMNS))
check("first 14 columns are v1's", sc.COLUMNS[:14][0:3], ["timestamp", "postcode", "suburb"])
check("v2.0.0 columns kept in order", sc.COLUMNS[14:22],
      ["observation_state", "ondemand_detected_by", "n_options", "suggestion_selected",
       "run_id", "slot", "collector_version", "tz_offset"])
check("row version", row["collector_version"], "2.2.0")
check("row product label", row["product"], "Samsung Galaxy S26 5G 256GB")
check("uber price", row["ondemand_price_aud"], 11.99)
check("standard = the non-Uber card", row["standard_price_aud"], 12.99)
ns = sc.no_serving_store_row("5700", "No available stores found for the given location.")
check("no-store state", ns["observation_state"], sc.NO_STORE_REPORTED)
check("no-store prices empty not zero", (ns["ondemand_price_aud"], ns["standard_price_aud"]), ("", ""))
er = sc.error_row("5022", "Timeout: x", error_type="timeout")
check("error state", er["observation_state"], sc.COLLECTION_ERROR)
check("error type kept", er["error_type"], "timeout")
check("error leaves ondemand_shown empty", er["ondemand_shown"], "")
check("tz offset is Adelaide", er["tz_offset"] in ("+0930", "+1030"), True)
sony_row = sc.build_csv_row("5000", [sony])
check("Sony row: ondemand_shown N", sony_row["ondemand_shown"], "N")
check("Sony row: standard is the $59 card", sony_row["standard_price_aud"], 59.0)
check("Sony row: review flag in notes", "Review:" in sony_row["notes"], True)

# ---------------------------------------------------------------- E
print("E. RETRIES AND BLOCKS (fake attempts)")
real_attempt, real_sleep = sc._attempt, sc.time.sleep
sleeps = []
sc.time.sleep = lambda s: sleeps.append(s)
tmp = Path(tempfile.mkdtemp())
jsonl = tmp / "raw.jsonl"


class FakeSession:
    def get_if_live(self):
        return True


def scripted(*outcomes):
    seq = list(outcomes)

    def fake(session, postcode, full):
        kind, payload = seq.pop(0)
        return kind, payload, "Grange SA 5022", []
    return fake


sc._attempt = scripted(("error", sc.PWTimeout("Timeout 20000ms exceeded")),
                       ("ok", [express, uber_logo]))
sleeps.clear()
row, _ = sc.observe_postcode(FakeSession(), "5022", False, jsonl)
check("timeout then ok -> ok row", row["observation_state"], sc.ON_DEMAND_SCHEDULED)
check("attempts = 2", row["attempts"], 2)
check("backoff 20 s used", sleeps, [20])

sc._attempt = scripted(*[("error", sc.PWTimeout("Timeout"))] * 3)
sleeps.clear()
row, _ = sc.observe_postcode(FakeSession(), "5022", False, jsonl)
check("3 timeouts -> COLLECTION_ERROR", row["observation_state"], sc.COLLECTION_ERROR)
check("error_type timeout", row["error_type"], "timeout")
check("exponential backoff 20, 60", sleeps, [20, 60])
check("attempts capped at 3", row["attempts"], 3)

sc._attempt = scripted(("error", sc.SuggestionNotOffered("wanted 'X'; not offered")))
sleeps.clear()
row, _ = sc.observe_postcode(FakeSession(), "5022", False, jsonl)
check("not offered -> no retry", (row["attempts"], sleeps), (1, []))
check("not offered error_type", row["error_type"], "not_offered")

sc._attempt = scripted(("no_store", "No available stores found for the given location."))
row, _ = sc.observe_postcode(FakeSession(), "5700", False, jsonl)
check("no store -> no retry, NO_STORE_REPORTED",
      (row["observation_state"], row["attempts"]), (sc.NO_STORE_REPORTED, 1))

sc._attempt = scripted(("error", sc.SiteBlocked("HTTP 403 on product page")))
try:
    sc.observe_postcode(FakeSession(), "5022", False, jsonl)
    check("403 raises SiteBlocked", "no exception", "SiteBlocked")
except sc.SiteBlocked as exc:
    check("403 raises SiteBlocked", exc.args[1]["error_type"], "blocked")

sc._attempt = scripted(("error", sc.RateLimited("HTTP 429")), ("ok", [asap_logo]))
sleeps.clear()
row, _ = sc.observe_postcode(FakeSession(), "5022", False, jsonl)
check("429 once -> slows down 120 s then ok", (row["observation_state"], sleeps),
      (sc.ON_DEMAND_ASAP, [120]))

sc._attempt = scripted(*[("error", sc.RateLimited("HTTP 429"))] * 3)
sleeps.clear()
try:
    sc.observe_postcode(FakeSession(), "5022", False, jsonl)
    check("persistent 429 stops run", "no exception", "RateLimited")
except sc.RateLimited:
    check("persistent 429 stops run after 120, 300 s", sleeps, [120, 300])

check("HTTP 5xx is transient", sc._classify_error(sc.TransientHTTP("HTTP 503")), ("http_5xx", True))
check("net::ERR is transient",
      sc._classify_error(RuntimeError("net::ERR_CONNECTION_RESET")), ("network", True))
check("jsonl written for every observation",
      sum(1 for _ in jsonl.open(encoding="utf-8")), 7)

# ---------------------------------------------------------------- F / G
print("F. CSV / RESUME / CHECKPOINT   G. PASS ABORT")
out = Path(tempfile.mkdtemp())
paths = {"csv": out / "results.csv", "jsonl": out / "raw.jsonl",
         "failed": out / "failed_postcodes.csv"}
sc.RUN.update({"run_id": "primary_20260930_v2.2.0", "slot": "2026-09-30 07:00",
               "study": "primary"})
calls = []


def fake_observe(session, postcode, full, jsonl_path):
    calls.append(postcode)
    if postcode == "5700":
        return sc.no_serving_store_row(postcode, "No available stores found."), []
    if postcode == "6430":
        return sc.error_row(postcode, "Timeout: x", error_type="timeout"), []
    return sc.build_csv_row(postcode, [express, uber_logo]), [express, uber_logo]


real_observe = sc.observe_postcode
sc.observe_postcode = fake_observe
pcs = ["5022", "5700", "6430", "2000"]
prog = sc.Progress(out, 4, sc.load_done_keys(paths["csv"]))
sc.run_pass(None, "primary", pcs, ["s26"], False, paths, prog)
check("pass wrote 4 rows", len(list(csv.DictReader(paths["csv"].open(encoding="utf-8")))), 4)
check("failed file has the 1 error", [r["postcode"] for r in
      csv.DictReader(paths["failed"].open(encoding="utf-8"))], ["6430"])
cp = json.loads((out / "checkpoint.json").read_text(encoding="utf-8"))
check("checkpoint counts", (cp["counts"]["valid"], cp["counts"]["no_store"],
                            cp["counts"]["failed"]), (2, 1, 1))

calls.clear()
prog2 = sc.Progress(out, 4, sc.load_done_keys(paths["csv"]))
sc.run_pass(None, "primary", pcs, ["s26"], False, paths, prog2)
check("resume: rerun makes no new requests", calls, [])
check("resume: skipped 4", prog2.counts["skipped_resume"], 4)
rows = list(csv.DictReader(paths["csv"].open(encoding="utf-8")))
keys = [(r["run_id"], r["slot"], r["product_key"], r["postcode"]) for r in rows]
check("resume: no duplicate rows", len(keys), len(set(keys)))
z = out / "zero.csv"
sc.append_csv(sc.build_csv_row("0800", [uber_logo]), z)
check("CSV keeps postcode 0800 quoted with leading zero",
      '"0800"' in z.read_text(encoding="utf-8"), True)

sc.RUN["slot"] = "2026-09-30 07:30"


def always_fail(session, postcode, full, jsonl_path):
    calls.append(postcode)
    return sc.error_row(postcode, "Timeout: x", error_type="timeout"), []


sc.observe_postcode = always_fail
calls.clear()
many = list(sc.LOCATIONS)[:10]
prog3 = sc.Progress(out, 10, sc.load_done_keys(paths["csv"]))
try:
    sc.run_pass(None, "primary", many, ["s26"], False, paths, prog3)
    check("consecutive errors abort pass", "completed", "aborted")
except sc.PassAborted:
    check("consecutive errors abort pass after 6", len(calls), sc.MAX_CONSECUTIVE_ERRORS)
    check("aborted remainder counted as skipped", prog3.counts["skipped_aborted"], 4)

# G2. per-cycle export (assignment handoff): simulated 3-slot future cycle
print("G2. CYCLE EXPORT")
sc.observe_postcode = fake_observe          # 6430 -> error, 5700 -> no store
real_sleep_until = sc.sleep_until
sc.sleep_until = lambda target: None        # do not actually wait
out2 = Path(tempfile.mkdtemp())
paths2 = {"csv": out2 / "results.csv", "jsonl": out2 / "raw.jsonl",
          "failed": out2 / "failed_postcodes.csv"}
fday = (datetime.now() + timedelta(days=3)).date()
sc.RUN.update({"run_id": f"primary_{fday:%Y%m%d}_v2.2.0_local", "study": "primary"})
exp_dir = out2 / f"ASSIGNMENT_DATASET_cycle1_{fday:%Y%m%d}"
prog4 = sc.Progress(out2, 12, set())
# partial cycle (slots 0-2 of 40): must NOT be marked complete
part_dir = out2 / "partial"
sc.run_slots(FakeSession(), "primary", fday, [0, 1, 2], pcs, ["s26"],
             {"csv": out2 / "p.csv", "jsonl": out2 / "p.jsonl", "failed": out2 / "pf.csv"},
             sc.Progress(out2, 12, set()), "errors", timedelta(days=5), part_dir)
check("export: partial cycle is NOT marked complete",
      ((part_dir / "CYCLE_COMPLETE.txt").exists(),
       (part_dir / "STATUS.txt").read_text(encoding="utf-8").startswith("IN PROGRESS")), (False, True))
# whole cycle: validation design has 4 slots -> run all 4
sc.RUN.update({"run_id": f"validation_{fday:%Y%m%d}_v2.2.0_local", "study": "validation"})
sc.run_slots(FakeSession(), "validation", fday, [0, 1, 2, 3], pcs, ["s26"], paths2, prog4,
             "errors", timedelta(days=5), exp_dir)
check("export: COMPLETE marker written", (exp_dir / "CYCLE_COMPLETE.txt").exists(), True)
clean = list(csv.DictReader((exp_dir / "results_clean.csv").open(encoding="utf-8")))
meas = list(csv.DictReader((exp_dir / "results_measured.csv").open(encoding="utf-8")))
check("export: all 16 rows in results_clean", len(clean), 16)
check("export: errors excluded from results_measured", len(meas), 12)
check("export: slot_time / slot_index derived", (clean[0]["slot_time"], clean[0]["slot_index"]),
      ("09:00", "0"))
qd = json.loads((exp_dir / "data_quality.json").read_text(encoding="utf-8"))
check("export: coverage 16/16 of expected grid",
      (qd["coverage"]["observed_cells"], qd["coverage"]["expected_cells"]), (16, 16))
check("export: status COMPLETE", qd["status"].startswith("COMPLETE"), True)
check("export: raw results.csv untouched (still 16 rows, no derived columns)",
      (len(list(csv.DictReader(paths2["csv"].open(encoding="utf-8")))),
       "slot_time" in paths2["csv"].read_text(encoding="utf-8").splitlines()[0]), (16, False))
# a missing slot must show up as missing, not disappear
q_missing = __import__("combine").export_run(
    paths2["csv"], sc.RUN["run_id"], out2 / "gapcheck",
    [s.strftime("%Y-%m-%d %H:%M") for s in sc.slots_for("validation", fday)]
    + [(sc.slots_for("validation", fday)[-1] + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")],
    pcs, ["s26"], "test", "gap check")
check("export: never-run slot counted as missing",
      (q_missing["coverage"]["missing_cells"], len(q_missing["coverage"]["slots_with_no_rows"])), (4, 1))
sc.sleep_until = real_sleep_until

sc.observe_postcode, sc._attempt, sc.time.sleep = real_observe, real_attempt, real_sleep

# deterministic run id: every chunk of one cycle gets the same id
ids = set()
for chunk in (1, 2, 5):
    d = Path(tempfile.mkdtemp())
    sc.main(["--study", "primary", "--chunk", str(chunk), "--cycle-date", "2020-01-01",
             "--out-dir", str(d)])
    ids.add(sc.RUN["run_id"])
    cpj = json.loads((d / "checkpoint.json").read_text(encoding="utf-8"))
    check(f"past cycle chunk {chunk}: nothing attempted, slots skipped",
          (cpj["counts"]["processed"], cpj["counts"]["skipped_slots"] > 0), (0, True))
check("deterministic run_id across chunks", ids, {"primary_20200101_v2.2.0" + sc.ENV_TAG})
check("validation chunk 5 is a no-op", sc.main(["--study", "validation", "--chunk", "5"]), 0)

# ---------------------------------------------------------------- P
frozen = ROOT.parent / "jbhifi_collect_v2.0.0_FROZEN.py"
if frozen.exists():
    print("P. PARITY WITH FROZEN v2.0.0 (only intended differences)")
    spec = importlib.util.spec_from_file_location("frozen_v200", frozen)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    check("clock times identical to v2.0.0 (rotated to noon)",
          sorted(s.strftime("%H:%M") for s in sc.slots_for("primary", DAY)),
          sorted(s.strftime("%H:%M") for s in old.slots_for(DAY)))
    check("LOCATIONS identical", sc.LOCATIONS, old.LOCATIONS)
    check("v2.0.0 columns are a prefix", sc.COLUMNS[:len(old.COLUMNS)], old.COLUMNS)
    for c in cards:
        a, b = old.observation_state(c["options"]), sc.observation_state(c["options"])
        tail = (c["product_url"] or "")[-22:]
        if tail.endswith("gemini-2026"):
            check(f"Sony: v2.0.0 {a} -> v2.1.0 {b} (intended fix)",
                  (a, b), (old.ON_DEMAND_UNCLASSIFIED, sc.ON_DEMAND_UNAVAILABLE))
        else:
            check(f"{c['postcode']} {tail}: same state as v2.0.0 ({b})", a, b)
    for t in ["Delivered within 2 hours", "Delivered within 90 minutes",
              "Choose a 2 hour window", "Delivery available from 27 September"]:
        check(f"promise_type unchanged: {t!r}", sc.promise_type(t), old.promise_type(t))
else:
    print("P. (frozen v2.0.0 not present - parity checks skipped)")

print()
print("=" * 60)
if FAILURES:
    print(f"{len(FAILURES)} CHECK(S) FAILED:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("ALL CHECKS PASSED")
