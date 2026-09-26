"""
LIVE checks (real site, headless) for states a normal pass cannot trigger
on demand. Ported from validate_v2_states.py (v2.0.0) to scraper.py.

  1. 5290 Mount Gambier    -> ON_DEMAND_UNAVAILABLE (non-Uber options only)
  2. 6030 Clarkson, logos  -> Uber still found by label+wording
     stripped before extraction (reproduces the 23 Sep render failure)
  3. nonexistent locality  -> COLLECTION_ERROR, error_type not_offered,
                              nothing clicked, not retried

  python tests/live_states.py <out_dir>
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scraper as sc  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
sc.SHOT_DIR = OUT / "screenshots"
sc.RUN.update({"run_id": "live_states_v" + sc.COLLECTOR_VERSION, "slot": "live-states",
               "study": "validation-check", "product_key": "s26"})
CSV, JSONL = OUT / "results.csv", OUT / "raw_observations.jsonl"

STRIP_LOGOS = """() => {
  const imgs = document.querySelectorAll(
    '[data-testid="delivery-availability-location-search-result"] img');
  imgs.forEach(i => i.remove());
  return imgs.length;
}"""
real_extract = sc.extract_delivery_options


def stripped(page):
    sc.log(f"  removed {page.evaluate(STRIP_LOGOS)} carrier logo(s) before extraction")
    return real_extract(page)


results = []
with sync_playwright() as p:
    session = sc.BrowserSession(p)
    try:
        for label, pc, patch in (("unavailable", "5290", None),
                                 ("logo-stripped", "6030", stripped)):
            sc.extract_delivery_options = patch or real_extract
            sc.log(f"{label.upper()} {pc}")
            row, _ = sc.observe_postcode(session, pc, True, JSONL)
            sc.append_csv(row, CSV)
            results.append((label, row))
            sc.time.sleep(7)
        sc.extract_delivery_options = real_extract
        sc.LOCATIONS["9999"] = ("Nowhereville Xyz", "SA", "test", 2)
        sc.log("NONEXISTENT LOCALITY 9999")
        row, _ = sc.observe_postcode(session, "9999", False, JSONL)
        sc.append_csv(row, CSV)
        results.append(("forced-error", row))
    finally:
        sc.extract_delivery_options = real_extract
        session.close()

print("\nRESULTS")
for kind, r in results:
    print(f"  {kind:14} {r['postcode']} state={r['observation_state']:22} "
          f"by={r['ondemand_detected_by'] or '-':14} attempts={r['attempts']} "
          f"err={r['error_type'] or '-':11} promise={r['promise_text_verbatim']!r} "
          f"notes={r['notes'][:100]!r}")
