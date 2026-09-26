"""
JB Hi-Fi delivery availability collector - v2.1.0.

Derived from jbhifi_collect.py v2.0.0 (see HANDOFF_AUDIT.md). The DOM
contract, parser, row builders and observation states are carried over;
v2.1.0 changes are listed in FREEZE_v2.1.0.md.

Two studies, never mixed:

  primary     Samsung Galaxy S26 5G 256GB x 49 postcodes x 40 fixed slots
              (07:00-23:00 every 30 min, 00:00-06:00 hourly, Adelaide time).
              Feeds the main analysis and PIs.
  validation  4 products x 12 postcodes (6 metro core, 6 regional) x 4
              slots (09:00, 13:00, 17:00, 21:00). Balanced design; tests
              whether patterns are product-specific. Separate dataset.

Usage
-----
  python scraper.py --study primary --test              quick pass, 8 postcodes, now
  python scraper.py --study validation --test           quick pass, 2 postcodes x 4 products
  python scraper.py --study primary --chunk 1           slots of chunk 1 of today's cycle
  python scraper.py --study primary --slots 0-39        whole cycle (local machine)
  python scraper.py --study primary --only 5022 --now   one postcode, one pass, now

Outputs (in --out-dir, default data/<study>/<run_id>/):
  results.csv            one row per observation (append-only)
  raw_observations.jsonl every option seen, verbatim, one record per row
  failed_postcodes.csv   every COLLECTION_ERROR row, with reason
  checkpoint.json        progress + counters, rewritten atomically
  scraper.log            the log
  screenshots/           panel clips for every rendered observation,
                         full-page captures on errors (and in --test)
  manifest_<run_id>.json collector version, hash, design

Exit codes: 0 ok, 2 bad arguments or wrong clock, 3 stopped because the
site blocked / rate limited us, 4 chunk started too early to wait for.

DOM contract (verified live 2026-09-22, re-verified 2026-09-26)
---------------------------------------------------------------
  postcode input   data-testid="jbtextfield-location-search-pdp"
  suggestion       exact visible text "<Suburb> <STATE> <postcode>"
  reveal options   data-testid="localisation-delivery-view-options-button"
  options panel    data-testid="delivery-availability-location-search-results"
  one option card  data-testid="delivery-availability-location-search-result"
  tag (FASTEST)    data-testid="jbtag-container"   (inside a card)
"""

import os
import time

# --- clock: pin to Adelaide BEFORE anything reads the local time ----------
# Slots are Adelaide wall-clock times. A GitHub runner's clock is UTC, so on
# POSIX the process timezone is forced here; on Windows (no tzset) main()
# refuses to run unless the machine clock is already ACST/ACDT.
COLLECTOR_TZ = "Australia/Adelaide"
if hasattr(time, "tzset"):
    os.environ["TZ"] = COLLECTOR_TZ
    time.tzset()

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
import argparse
import csv
import ctypes
import hashlib
import json
import random
import re
import sys

# ---------------------------------------------------------------- config

# Bumped whenever collection behaviour changes. Every row and the run
# manifest carry it, so no two collector behaviours can be silently mixed.
COLLECTOR_VERSION = "2.2.0"

# key -> (label written to the CSV, product URL). The label must describe
# the product actually loaded from the URL.
PRODUCTS = {
    # Focal product. The assignment's originally proposed product (Apple
    # iPhone 17 Pro Max 256GB) was withdrawn from sale; the substitution is
    # explained in the methodology, NOT by mislabelling rows here.
    "s26": ("Samsung Galaxy S26 5G 256GB",
            "https://www.jbhifi.com.au/products/"
            "samsung-galaxy-s26-5g-256gb-cobalt-violet"),
    # Validation products - all in normal sale on 2026-09-26 (Add to cart,
    # no pre-order wording). Chosen to span parcel size.
    "airpods5": ("Apple AirPods 5",
                 "https://www.jbhifi.com.au/products/apple-airpods-5"),
    "hp15": ("HP 15-fd0758TU 15.6\" Laptop (i5-1334U, 256GB)",
             "https://www.jbhifi.com.au/products/"
             "hp-15-fd0758tu-15-6-full-hd-laptop-intel-core-i5-1334u256gb"),
    # Bulky item and parser stress test: renders a logo-less "Scheduled"
    # $59 card that is NOT Uber (see ondemand_evidence).
    "sony65tv": ("Sony 65\" Bravia 6 OLED 4K TV (2026)",
                 "https://www.jbhifi.com.au/products/"
                 "sony-65-bravia-6-oled-4k-hdr-google-tv-with-gemini-2026"),
}

# postcode -> (suburb, state, area_type, priority)
#
# 49 locations across all 8 states/territories. Postcodes are STRING keys:
# the NT codes "0800"/"0810" lose their leading zero the moment anything
# treats them as integers.
#
# priority is analysis metadata only. It is NOT used to order or filter
# collection.
#
# suburb is BOTH the search term typed into JB Hi-Fi and the value written
# to the CSV. Four localities carry JB Hi-Fi's own name rather than the
# common one, because the common name is not in JB Hi-Fi's suggestion data
# (verified by live audit, 2026-09-23):
#
#   4000  Brisbane      -> "Brisbane City"
#   4350  Toowoomba     -> "Toowoomba City"
#   2601  Canberra City -> "Canberra"
#   0800  Darwin        -> "Darwin City"
LOCATIONS = {
    # NSW
    "2000": ("Sydney", "NSW", "metro core", 1),
    "2060": ("North Sydney", "NSW", "metro core", 2),
    "2170": ("Liverpool", "NSW", "metro fringe", 1),
    "2750": ("Penrith", "NSW", "metro fringe", 2),
    "2300": ("Newcastle", "NSW", "regional", 2),
    "2650": ("Wagga Wagga", "NSW", "regional", 1),
    "2480": ("Lismore", "NSW", "regional", 2),
    # VIC
    "3000": ("Melbourne", "VIC", "metro core", 1),
    "3121": ("Richmond", "VIC", "metro core", 2),
    "3030": ("Point Cook", "VIC", "metro fringe", 1),
    "3175": ("Dandenong", "VIC", "metro fringe", 2),
    "3220": ("Geelong", "VIC", "regional", 2),
    "3550": ("Bendigo", "VIC", "regional", 1),
    "3350": ("Ballarat", "VIC", "regional", 2),
    # QLD
    "4000": ("Brisbane City", "QLD", "metro core", 1),      # JB name for Brisbane
    "4006": ("Fortitude Valley", "QLD", "metro core", 2),
    "4300": ("Springfield", "QLD", "metro fringe", 1),
    "4178": ("Wynnum", "QLD", "metro fringe", 2),
    "4350": ("Toowoomba City", "QLD", "regional", 1),       # JB name for Toowoomba
    "4740": ("Mackay", "QLD", "regional", 2),
    "4870": ("Cairns", "QLD", "regional", 2),
    # SA
    "5000": ("Adelaide", "SA", "metro core", 1),
    "5067": ("Norwood", "SA", "metro core", 1),
    "5034": ("Millswood", "SA", "metro core", 2),
    "5022": ("Grange", "SA", "metro fringe", 1),
    "5108": ("Salisbury", "SA", "metro fringe", 1),
    "5162": ("Morphett Vale", "SA", "metro fringe", 2),
    "5095": ("Mawson Lakes", "SA", "metro fringe", 2),
    "5114": ("Smithfield", "SA", "outer metro", 1),
    "5251": ("Mount Barker", "SA", "outer metro", 2),
    "5290": ("Mount Gambier", "SA", "regional", 1),
    "5700": ("Port Augusta", "SA", "regional", 1),
    "5606": ("Port Lincoln", "SA", "regional", 2),
    # WA
    "6000": ("Perth", "WA", "metro core", 1),
    "6008": ("Subiaco", "WA", "metro core", 2),
    "6164": ("Success", "WA", "metro fringe", 1),
    "6030": ("Clarkson", "WA", "metro fringe", 2),
    "6230": ("Bunbury", "WA", "regional", 1),
    "6430": ("Kalgoorlie", "WA", "regional", 2),
    "6530": ("Geraldton", "WA", "regional", 2),
    # TAS
    "7000": ("Hobart", "TAS", "metro core", 1),
    "7010": ("Glenorchy", "TAS", "metro fringe", 2),
    "7250": ("Launceston", "TAS", "regional", 1),
    "7320": ("Burnie", "TAS", "regional", 2),
    # ACT
    "2601": ("Canberra", "ACT", "metro core", 1),           # JB name for Canberra City
    "2900": ("Greenway", "ACT", "metro fringe", 2),
    # NT
    "0800": ("Darwin City", "NT", "metro core", 1),         # JB name for Darwin
    "0810": ("Casuarina", "NT", "metro fringe", 2),
    "0870": ("Alice Springs", "NT", "regional", 2),
}

# ------------------------------------------------------------ study design
#
# Slots are indices into the study's slot list for one cycle. A cycle
# starts on its "cycle date" and, for the primary study, crosses midnight.
#
# Chunks exist only because a GitHub Actions job may run for at most 6 h.
# Each chunk is sized so that (wait for its first slot + its passes) stays
# under ~5.3 h when the chunks run back to back. They do not change what is
# sampled - a local run can do --slots 0-39 in one process.

STUDIES = {
    "primary": {
        "products": ["s26"],
        "postcodes": list(LOCATIONS),
        # v2.2.0: the cycle STARTS AT 12:00 (deadline change, 26 Sep 2026).
        # The 40 clock times are exactly v2.1.0's set (07:00-23:00 every
        # 30 min + 00:00-06:00 hourly), rotated to begin at noon:
        #   day 1  12:00-23:00 every 30 min  (23 slots, idx 0-22)
        #   day 2  00:00-06:00 hourly        ( 7 slots, idx 23-29)
        #   day 2  07:00-11:30 every 30 min  (10 slots, idx 30-39)
        "day_slots": [(dtime(12, 0), dtime(23, 0), 30)],
        "next_day_slots": [(dtime(0, 0), dtime(6, 0), 60),
                           (dtime(7, 0), dtime(11, 30), 30)],
        # 12:00-16:00 | 16:30-21:00 | 21:30-02:00 | 03:00-07:00 | 07:30-11:30
        "chunks": [(0, 8), (9, 18), (19, 25), (26, 30), (31, 39)],
        "test_postcodes": ["5022", "5000", "5700", "2000", "3550",
                           "6030", "6430", "0870"],
    },
    "validation": {
        # s26 is included as the within-study anchor: product effects are
        # estimated inside this balanced design only.
        "products": ["s26", "airpods5", "hp15", "sony65tv"],
        # 6 metro core + 6 regional, all 8 states/territories except ACT
        # (no ACT regional location exists in LOCATIONS).
        "postcodes": ["2000", "3000", "4000", "5000", "6000", "7000",
                      "2650", "3550", "4870", "5700", "6430", "0870"],
        "day_slots": [(dtime(9, 0), dtime(9, 0), 60),
                      (dtime(13, 0), dtime(13, 0), 60),
                      (dtime(17, 0), dtime(17, 0), 60),
                      (dtime(21, 0), dtime(21, 0), 60)],
        "next_day_slots": [],
        "chunks": [(0, 0), (1, 1), (2, 2), (3, 3)],
        "test_postcodes": ["5000", "5700"],
    },
}

# v1's 14 columns first (unchanged), then v2.0.0's, then v2.1.0's.
#   study          primary | validation
#   product_key    key into PRODUCTS
#   attempts       page attempts used for this observation (1 = no retry)
#   error_type     COLLECTION_ERROR category: timeout | not_offered |
#                  empty_panel | network | blocked | rate_limited |
#                  browser | other   (blank for non-errors)
#   review_flag    set when a card LOOKED like Uber but lacked enough
#                  evidence to be counted as Uber - manual audit, not a state
COLUMNS = [
    "timestamp", "postcode", "suburb", "state", "area_type", "product",
    "ondemand_shown", "promise_text_verbatim", "promise_type",
    "ondemand_price_aud", "standard_promise_text", "standard_price_aud",
    "labelled_fastest", "notes",
    "observation_state", "ondemand_detected_by", "n_options",
    "suggestion_selected", "run_id", "slot", "collector_version", "tz_offset",
    "study", "product_key", "attempts", "error_type", "review_flag",
]

# Terminal observation states. Exactly one per row.
ON_DEMAND_ASAP = "ON_DEMAND_ASAP"
ON_DEMAND_SCHEDULED = "ON_DEMAND_SCHEDULED"
ON_DEMAND_UNCLASSIFIED = "ON_DEMAND_UNCLASSIFIED"
ON_DEMAND_UNAVAILABLE = "ON_DEMAND_UNAVAILABLE"
NO_STORE_REPORTED = "NO_STORE_REPORTED"
COLLECTION_ERROR = "COLLECTION_ERROR"

SHOT_DIR = Path("data") / "screenshots"      # replaced in main()

# Where the collector runs, appended to run_id, so a GitHub Actions copy and
# a local copy of the same cycle can never be merged or deduplicated into
# each other.
ENV_TAG = "_gha" if os.environ.get("GITHUB_ACTIONS") == "true" else "_local"

# Identity of the current run / slot / product, stamped onto every row.
RUN = {"run_id": "adhoc", "slot": "adhoc", "study": "adhoc",
       "product_key": "s26"}

PANEL = '[data-testid="delivery-availability-location-search-results"]'
CARD = '[data-testid="delivery-availability-location-search-result"]'
TAG = '[data-testid="jbtag-container"]'
VIEW_BUTTON = '[data-testid="localisation-delivery-view-options-button"]'
# Shown when JB Hi-Fi resolves the location but finds no store able to
# serve it; the delivery component is then never rendered.
NO_RESULTS = '[data-testid="location-search-no-results"]'

# Random, to avoid a metronomic request pattern against the site.
DELAY_MIN_SECONDS = 5.0
DELAY_MAX_SECONDS = 10.0

# Retries: transient failures only (timeout, network, browser crash, empty
# panel, HTTP 5xx). Never for NO_STORE, "suburb not offered", or a block.
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = [20, 60]              # before attempt 2, attempt 3

# HTTP 429: slow down, then give up for the run (never evade).
RATE_LIMIT_BACKOFF_SECONDS = [120, 300]

# This many COLLECTION_ERRORs in a row aborts the rest of the pass (the
# site or network is in trouble; carrying on just adds load). The next
# slot starts fresh.
MAX_CONSECUTIVE_ERRORS = 6

# A pass may start this late after its slot and still count as that slot.
SLOT_GRACE = timedelta(minutes=10)

# Retries when the CSV is locked (e.g. open in Excel) before falling back.
CSV_LOCK_RETRIES = 3
CSV_LOCK_WAIT_SECONDS = 2.0

# ---------------------------------------------------------------- parser
#
# Locates promise / price / carrier WITHOUT relying on CSS-module hashes.
#
#   tags     [data-testid="jbtag-container"]        - semantic, stable
#   carrier  the <span> beside <img alt="... logo"> - structural
#   price    the leaf <span> whose text starts "$"  - content-anchored
#   promise  the first remaining leaf <span>        - structural
#
# Unchanged from v2.0.0.

JS_EXTRACT = """
() => {
  const CARD = '[data-testid="delivery-availability-location-search-result"]';
  const TAG = '[data-testid="jbtag-container"]';
  const txt = el => el ? (el.innerText || '').trim() : null;

  return Array.from(document.querySelectorAll(CARD)).map(card => {
    const sources = {};

    // --- tags: the only semantic hook inside a card ------------------
    const tagEls = Array.from(card.querySelectorAll(TAG));
    const tags = tagEls.map(txt).filter(Boolean);

    // --- carrier: anchored on the carrier logo image -----------------
    const img = card.querySelector('img[alt]');
    let carrierEl = null;
    if (img && img.parentElement) {
      carrierEl = img.parentElement.querySelector('span');
      if (carrierEl) sources.carrier = 'structural:img-sibling';
    }
    if (!carrierEl) {
      carrierEl = card.querySelector('span[class*="carrierText"]');
      if (carrierEl) sources.carrier = 'class-fallback';
    }

    // --- candidate leaf spans, excluding tags and the carrier --------
    const excluded = el =>
      tagEls.some(t => t === el || t.contains(el)) ||
      (carrierEl && (carrierEl === el || carrierEl.contains(el)));

    const leaves = Array.from(card.querySelectorAll('span'))
      .filter(s => !s.querySelector('span'))
      .filter(s => !excluded(s))
      .filter(s => txt(s));

    // --- price: content-anchored on the leading "$" ------------------
    let priceEl = leaves.find(s => /^\\$\\s*\\d/.test(txt(s))) || null;
    if (priceEl) {
      sources.price = 'structural:dollar-prefix';
    } else {
      priceEl = card.querySelector(
        'span[class*="_price__"], span[class*="styles_price"]');
      if (priceEl) sources.price = 'class-fallback';
    }

    // --- promise: first remaining leaf that is not the price ---------
    let promiseEl = leaves.find(
      s => s !== priceEl && !/^\\$/.test(txt(s))) || null;
    if (promiseEl) {
      sources.promise = 'structural:first-non-price-leaf';
    } else {
      promiseEl = Array.from(card.querySelectorAll('span[class*="headingText"]'))
        .filter(el => el !== priceEl)[0] || null;
      if (promiseEl) sources.promise = 'class-fallback';
    }

    // --- last resort: raw innerText lines ----------------------------
    const lines = (card.innerText || '').split('\\n')
      .map(s => s.trim()).filter(Boolean);
    let promise = txt(promiseEl);
    let price = txt(priceEl);
    if (!promise && lines.length) {
      promise = lines[0];
      sources.promise = 'innerText-fallback';
    }
    if (!price) {
      const p = lines.find(l => l.startsWith('$'));
      if (p) { price = p; sources.price = 'innerText-fallback'; }
    }

    const usedFallback = Object.values(sources)
      .some(s => s && s.indexOf('structural') !== 0);

    return {
      promise: promise || null,
      price: price || null,
      carrier: txt(carrierEl),
      carrier_alt: img ? img.getAttribute('alt') : null,
      carrier_img_src: img ? img.getAttribute('src') : null,
      tags: tags,
      raw_lines: lines,
      sources: sources,
      used_fallback: usedFallback
    };
  });
}
"""

# Page-level block signals. Checked on every product page load; any hit
# stops the run - we never retry our way past a block.
JS_BLOCK_SIGNALS = """
() => {
  const t = (document.title || '').toLowerCase();
  const b = ((document.body && document.body.innerText) || '').slice(0, 3000).toLowerCase();
  const hits = [];
  if (t.includes('just a moment') || t.includes('attention required')) hits.push('cloudflare-title');
  if (document.querySelector('#challenge-form, #cf-challenge-running, [id^="cf-chl"], iframe[src*="challenges.cloudflare.com"]')) hits.push('cloudflare-challenge');
  if (b.includes('access denied') || b.includes('you have been blocked')) hits.push('access-denied');
  if (b.includes('verify you are human')) hits.push('captcha');
  return hits;
}
"""


# --------------------------------------------------------------- helpers

class NoServingStore(Exception):
    """JB Hi-Fi found no store able to serve the selected location.

    This is an observation, not a failure: the site rendered a definite
    answer. It carries JB Hi-Fi's exact visible wording.
    """


class SiteBlocked(Exception):
    """403 / Cloudflare challenge / CAPTCHA / access denied. Stops the run."""


class RateLimited(Exception):
    """HTTP 429. Back off; if it persists, stop the run."""


class TransientHTTP(Exception):
    """HTTP 5xx on the product page. Retried like a timeout."""


LOG_FH = None


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    if LOG_FH is not None:
        try:
            LOG_FH.write(line + "\n")
            LOG_FH.flush()
        except Exception:
            pass


# The service label JB Hi-Fi prints beside the Uber logo. Observed live:
# "Scheduled" (2-hour window) and "ASAP" (90-minute / 2-hour promise).
# Non-Uber cards carry "Courier", "Standard" or "Express" - but a bulky-goods
# card (Sony 65" TV, 26 Sep) also says "Scheduled", with no logo at all.
UBER_SERVICE_LABELS = {"scheduled", "asap"}
# Uber-specific promise wording: "Choose a 2 hour window",
# "Delivered within 90 minutes", "Delivered within 2 hours". Does NOT match
# "within 5 business days" or "Delivery available from 27 September".
UBER_PROMISE_WORDING = re.compile(
    r"\b\d+\s*hour window\b|\bwithin\s+\d+\s*(?:min|minute|minutes|hour|hours)\b",
    re.IGNORECASE)


def ondemand_evidence(option):
    """Which rule identifies this card as the Uber / on-demand option, or
    None if it is not one.

    Strongest first; the rule that fired goes to `ondemand_detected_by`:

      logo-alt        img alt contains "uber"                (verified live)
      logo-src        img src contains "uber"
      carrier-text    carrier text itself names Uber / on-demand
      label+wording   NO logo alt, the carrier label is one Uber uses
                      ("Scheduled"/"ASAP") AND the promise uses Uber's own
                      wording. Both are required. This keeps the 6030
                      Clarkson case (logos failed to render: "Scheduled" +
                      "Choose a 2 hour window") and rejects the Sony TV card
                      ("Scheduled" + "Delivery available from 27 September").

    v2.0.0 accepted the label OR the wording alone; v2.1.0 does not. A
    card with only one of them is not counted as Uber - see review_flag().
    A card carrying a non-Uber logo is never reclassified by wording, and
    the FASTEST tag and the price are never used.
    """
    alt = (option.get("carrier_alt") or "").lower()
    src = (option.get("carrier_img_src") or "").lower()
    carrier = (option.get("carrier") or "").strip().lower()
    if "uber" in alt:
        return "logo-alt"
    if "uber" in src:
        return "logo-src"
    if any(k in carrier for k in ("uber", "on demand", "on-demand", "ondemand")):
        return "carrier-text"
    if not alt and carrier in UBER_SERVICE_LABELS \
            and UBER_PROMISE_WORDING.search(option.get("promise") or ""):
        return "label+wording"
    return None


def review_flag(options):
    """Cards that look Uber-like but lack the evidence to count as Uber.

    Returned for manual audit (screenshot + JSONL); never changes the
    observation state. Empty string when nothing needs review."""
    flags = []
    for o in options:
        if ondemand_evidence(o) or (o.get("carrier_alt") or ""):
            continue
        carrier = (o.get("carrier") or "").strip().lower()
        wording = bool(UBER_PROMISE_WORDING.search(o.get("promise") or ""))
        if carrier in UBER_SERVICE_LABELS:
            flags.append(f"LOGOLESS_{carrier.upper()}_CARD_NOT_UBER_WORDING")
        elif wording:
            flags.append("UBER_WORDING_WITHOUT_LOGO_OR_LABEL")
    return ";".join(flags)


def is_ondemand(option):
    """True for the Uber / on-demand card (see ondemand_evidence)."""
    return ondemand_evidence(option) is not None


def observation_state(options, error=False, no_store=False):
    """The single terminal state of one observation. Unchanged from v2.0.0.

      COLLECTION_ERROR        nothing could be measured
      NO_STORE_REPORTED       JB Hi-Fi showed "No available stores found..."
      ON_DEMAND_UNAVAILABLE   delivery options rendered, none is Uber
      ON_DEMAND_ASAP          Uber card with minutes / ASAP wording
      ON_DEMAND_SCHEDULED     Uber card with window / hour wording
      ON_DEMAND_UNCLASSIFIED  Uber card whose wording fits neither
    """
    if error:
        return COLLECTION_ERROR
    if no_store:
        return NO_STORE_REPORTED
    ondemand = next((o for o in options if is_ondemand(o)), None)
    if ondemand is None:
        return ON_DEMAND_UNAVAILABLE
    return {"ASAP": ON_DEMAND_ASAP,
            "SCHEDULED": ON_DEMAND_SCHEDULED}.get(
                promise_type(ondemand.get("promise")), ON_DEMAND_UNCLASSIFIED)


def promise_type(text):
    """Classify the on-demand promise from its verbatim wording alone.

    UNCHANGED from v2.0.0 on purpose (PI definition). Known consequence:
    "Delivered within 2 hours" classifies as SCHEDULED because it contains
    "hour" - see HANDOFF_AUDIT.md B3; promise_text_verbatim keeps the
    wording so analysis can reclassify.
    """
    if not text:
        return "NONE"
    low = text.lower()
    if "minute" in low or "asap" in low:
        return "ASAP"
    if "window" in low or "schedul" in low or "hour" in low:
        return "SCHEDULED"
    return "UNKNOWN"


def price_to_decimal(text):
    """'$11.99' -> 11.99. Returns '' when absent - never 0, never 'N/A'."""
    if not text:
        return ""
    try:
        return float(str(text).replace("$", "").replace(",", "").strip())
    except ValueError:
        return ""


def select_standard(options):
    """Standard delivery = the cheapest NON-Uber option.

    A non-Uber card explicitly tagged CHEAPEST wins outright; otherwise
    the lowest displayed price among non-Uber cards. Unchanged from v2.0.0.
    """
    candidates = [o for o in options if not is_ondemand(o)]
    if not candidates:
        return None, ""

    tagged = [o for o in candidates
              if any("CHEAPEST" in (t or "").upper() for t in o.get("tags", []))]
    if len(tagged) == 1:
        return tagged[0], "CHEAPEST tag"

    def price_value(o):
        v = price_to_decimal(o.get("price"))
        return v if v != "" else float("inf")

    cheapest = min(candidates, key=price_value)
    low = price_value(cheapest)
    tied = [o for o in candidates if price_value(o) == low]

    note = "lowest price" if not tagged else "lowest price (multiple CHEAPEST tags)"
    if len(tied) > 1:
        note = (f"price tie - {len(tied)} non-Uber options at "
                f"{cheapest['price']}, first in DOM order used")
    return cheapest, note


# ------------------------------------------------------------ page steps

def product_label():
    return PRODUCTS[RUN["product_key"]][0]


def product_url():
    return PRODUCTS[RUN["product_key"]][1]


def open_product(page):
    """Load the product page and refuse to continue past any block."""
    response = page.goto(product_url(), wait_until="domcontentloaded",
                         timeout=60_000)
    status = response.status if response else None
    if status == 429:
        raise RateLimited("HTTP 429 on product page")
    if status == 403:
        raise SiteBlocked("HTTP 403 on product page")
    if status is not None and status >= 500:
        raise TransientHTTP(f"HTTP {status} on product page")
    page.wait_for_timeout(4000)
    signals = page.evaluate(JS_BLOCK_SIGNALS)
    if signals:
        raise SiteBlocked(f"block page detected: {', '.join(signals)} "
                          f"(title {page.title()!r})")
    return page.title()


def find_delivery_input(page):
    field = page.get_by_test_id("jbtextfield-location-search-pdp")
    field.wait_for(state="visible", timeout=20_000)
    return field


def enter_search_term(page, field, term):
    """Type the configured SUBURB name (searching by postcode truncates the
    suggestion list - see v2.0.0 notes)."""
    field.click()
    field.fill(term)
    page.wait_for_timeout(2500)


class SuggestionNotOffered(RuntimeError):
    """The exact "<Suburb> <STATE> <postcode>" suggestion never appeared.
    Permanent for this run - not retried."""


def select_postcode(page, postcode, suburb, state):
    """Click the exact "<Suburb> <STATE> <postcode>" suggestion. No fuzzy
    matching, no first-result fallback."""
    wanted = f"{suburb} {state} {postcode}"
    suggestion = page.get_by_text(wanted, exact=True)
    try:
        suggestion.first.wait_for(state="visible", timeout=15_000)
    except PWTimeout:
        offered = []
        try:
            near = page.get_by_text(postcode, exact=False)
            for i in range(min(near.count(), 10)):
                el = near.nth(i)
                if el.is_visible():
                    offered.append(el.inner_text().strip().replace("\n", " / "))
        except Exception:
            pass
        raise SuggestionNotOffered(
            f"searched {suburb!r}; wanted exact {wanted!r}; "
            f"not offered; visible instead: {offered}")
    suggestion.first.click()
    page.wait_for_timeout(4000)
    return wanted


def wait_for_delivery_results(page):
    """Reveal the full option list, or raise NoServingStore with JB's
    wording. Neither appearing within the timeout is a genuine error."""
    page.wait_for_selector(f"{VIEW_BUTTON}, {NO_RESULTS}",
                           state="visible", timeout=20_000)

    button = page.locator(VIEW_BUTTON)
    if button.count() and button.first.is_visible():
        button.first.click()
        page.wait_for_selector(f"{PANEL} {CARD}", state="visible",
                               timeout=25_000)
        page.wait_for_timeout(1500)
        return

    no_results = page.locator(NO_RESULTS)
    if no_results.count() and no_results.first.is_visible():
        raise NoServingStore(no_results.first.inner_text().strip())

    raise RuntimeError(
        "neither the View details button nor a no-results message is visible")


def extract_delivery_options(page):
    return page.evaluate(JS_EXTRACT)


# ------------------------------------------------------------------ rows

def _base_row(postcode, suggestion=""):
    suburb, state, area_type, _priority = LOCATIONS[postcode]
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "postcode": postcode,
        "suburb": suburb,
        "state": state,
        "area_type": area_type,
        "product": product_label(),
        "ondemand_detected_by": "",
        "n_options": 0,
        "suggestion_selected": suggestion or "",
        "run_id": RUN["run_id"],
        "slot": RUN["slot"],
        "collector_version": COLLECTOR_VERSION,
        "tz_offset": time.strftime("%z"),
        "study": RUN["study"],
        "product_key": RUN["product_key"],
        "attempts": 1,
        "error_type": "",
        "review_flag": "",
    }


def build_csv_row(postcode, options, notes="", suggestion=""):
    row = _base_row(postcode, suggestion)

    ondemand = next((o for o in options if is_ondemand(o)), None)
    standard, standard_why = select_standard(options)

    row.update({
        "observation_state": observation_state(options),
        "ondemand_detected_by": ondemand_evidence(ondemand) if ondemand else "",
        "n_options": len(options),
        "ondemand_shown": "Y" if ondemand else "N",
        "promise_text_verbatim": ondemand["promise"] if ondemand else "",
        "promise_type": promise_type(ondemand["promise"]) if ondemand else "NONE",
        "ondemand_price_aud": price_to_decimal(ondemand["price"]) if ondemand else "",
        "standard_promise_text": standard["promise"] if standard else "",
        "standard_price_aud": price_to_decimal(standard["price"]) if standard else "",
        # Only from the on-demand card's own tag - never inferred.
        "labelled_fastest": "Y" if (ondemand and any(
            "FASTEST" in (t or "").upper() for t in ondemand["tags"])) else "N",
        "notes": notes,
        "review_flag": review_flag(options),
    })

    extra = []
    if options and not ondemand:
        extra.append("No on-demand option offered")
    if ondemand and row["promise_type"] == "UNKNOWN":
        extra.append(f"Unclassifiable on-demand wording: {ondemand['promise']!r}")
    if any(o.get("used_fallback") for o in options):
        extra.append("Parsed via fallback selector - verify markup")
    if ondemand and row["ondemand_detected_by"] not in ("logo-alt", "logo-src",
                                                        "carrier-text"):
        extra.append(f"Uber identified without logo ({row['ondemand_detected_by']})")
    if row["review_flag"]:
        extra.append(f"Review: {row['review_flag']}")
    if standard_why.startswith("price tie"):
        extra.append(standard_why)
    if not row["notes"]:
        row["notes"] = "; ".join(extra)
    return row


def no_serving_store_row(postcode, message, suggestion=""):
    """A valid observation: JB Hi-Fi rendered a definite "no serving store"
    answer. Prices stay empty, never zero; notes are JB's exact wording."""
    row = _base_row(postcode, suggestion)
    row.update({
        "observation_state": NO_STORE_REPORTED,
        "ondemand_shown": "N",
        "promise_text_verbatim": "",
        "promise_type": "NONE",
        "ondemand_price_aud": "",
        "standard_promise_text": "",
        "standard_price_aud": "",
        "labelled_fastest": "N",
        "notes": message,
    })
    return row


def error_row(postcode, note, suggestion="", error_type="other"):
    """A failed observation: identity preserved, measured fields empty."""
    row = _base_row(postcode, suggestion)
    row.update({
        "observation_state": COLLECTION_ERROR,
        "ondemand_shown": "",
        "promise_text_verbatim": "",
        "promise_type": "",
        "ondemand_price_aud": "",
        "standard_promise_text": "",
        "standard_price_aud": "",
        "labelled_fastest": "",
        "notes": note,
        "error_type": error_type,
    })
    return row


def _write_row(path, row, columns=COLUMNS):
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns,
                                quoting=csv.QUOTE_NONNUMERIC,
                                extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerow(row)
        fh.flush()
        os.fsync(fh.fileno())


def append_csv(row, csv_path, columns=COLUMNS):
    """Append one row immediately; a crash never costs earlier rows.

    Postcode must be set to String in Tableau (it infers a number
    regardless of quoting). If the file is locked (Excel on Windows) the
    row is retried, then diverted to a sidecar file - never dropped
    silently.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(CSV_LOCK_RETRIES):
        try:
            _write_row(csv_path, row, columns)
            return "ok"
        except PermissionError:
            if attempt < CSV_LOCK_RETRIES - 1:
                log(f"  CSV locked, retrying in {CSV_LOCK_WAIT_SECONDS:.0f}s "
                    f"({attempt + 1}/{CSV_LOCK_RETRIES})")
                time.sleep(CSV_LOCK_WAIT_SECONDS)

    fallback = csv_path.with_name(csv_path.stem + "_locked_fallback.csv")
    try:
        _write_row(fallback, row, columns)
        log(f"  !! CSV LOCKED - row diverted to {fallback.name} "
            f"(close Excel; merge this file afterwards)")
        return "fallback"
    except Exception as exc:
        log(f"  !! ROW LOST - could not write CSV or fallback: {exc}")
        log(f"  !! row was: {row}")
        return "lost"


def append_raw(postcode, options, jsonl_path, suggestion, row=None,
               page_message="", screenshots=(), attempt_log=()):
    """Audit trail: one record for EVERY observation, with every option
    seen verbatim, the site's message, each attempt's outcome and the row
    that was derived. The CSV can always be rebuilt from this file."""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "postcode": postcode,
                "suggestion_selected": suggestion,
                "product": product_label(),
                "product_key": RUN["product_key"],
                "product_url": product_url(),
                "study": RUN["study"],
                "run_id": RUN["run_id"],
                "slot": RUN["slot"],
                "collector_version": COLLECTOR_VERSION,
                "observation_state": (row or {}).get("observation_state", ""),
                "page_message": page_message,
                "screenshots": list(screenshots),
                "attempts": list(attempt_log),
                "options": options,
                "row": row,
            }) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except Exception as exc:
        log(f"  raw JSONL write failed: {exc}")


def _shot_name(postcode, suffix, ext):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{RUN['product_key']}_{postcode}_{stamp}{suffix}.{ext}"


def save_screenshot(page, postcode, suffix=""):
    """Full-page screenshot. Returns the file name, or "" on failure."""
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    name = _shot_name(postcode, suffix, "png")
    try:
        page.screenshot(path=str(SHOT_DIR / name), full_page=True)
        return name
    except Exception as exc:
        log(f"  screenshot failed: {exc}")
        return ""


def save_panel_clip(page, postcode):
    """Small image of the delivery-options panel only (~15 KB), taken on
    EVERY rendered observation. Returns "panels/<name>" or ""."""
    folder = SHOT_DIR / "panels"
    folder.mkdir(parents=True, exist_ok=True)
    name = _shot_name(postcode, "", "png")
    try:
        page.locator(PANEL).first.screenshot(path=str(folder / name))
        return f"panels/{name}"
    except Exception:
        return ""


# ------------------------------------------------------ browser lifetime

class BrowserSession:
    """Holds one browser and relaunches it if it dies.

    Default: headless bundled Chromium (runs on a Linux CI runner). --edge
    and --headed reproduce v2.0.0's visible Edge window. The user agent is
    whatever Playwright's browser reports - never spoofed.
    """

    def __init__(self, playwright, headed=False, edge=False):
        self._playwright = playwright
        self._browser = None
        self._headed = headed
        self._edge = edge
        self.restarts = 0

    def _launch(self):
        kwargs = {"headless": not self._headed}
        if self._edge:
            kwargs["channel"] = "msedge"
        return self._playwright.chromium.launch(**kwargs)

    def get(self):
        """A live browser, launching or relaunching as required."""
        if self._browser is None:
            self._browser = self._launch()
            log(f"browser launched ({'edge' if self._edge else 'chromium'}, "
                f"{'headed' if self._headed else 'headless'})")
        elif not self._browser.is_connected():
            self.restarts += 1
            log(f"!! browser is not connected - relaunching "
                f"(restart #{self.restarts})")
            self._discard()
            self._browser = self._launch()
        return self._browser

    def get_if_live(self):
        """True when the current browser is usable. Never launches."""
        return self._browser is not None and self._browser.is_connected()

    def restart(self, reason):
        self.restarts += 1
        log(f"!! relaunching browser: {reason} (restart #{self.restarts})")
        self._discard()
        return self.get()

    def _discard(self):
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception as exc:
            log(f"   (old browser would not close cleanly: {exc})")
        self._browser = None

    def close(self):
        self._discard()


# ---------------------------------------------------------- one attempt

def _classify_error(exc):
    """(error_type, transient?) for an exception from one attempt."""
    msg = str(exc)
    if isinstance(exc, SiteBlocked):
        return "blocked", False
    if isinstance(exc, RateLimited):
        return "rate_limited", False
    if isinstance(exc, SuggestionNotOffered):
        return "not_offered", False
    if isinstance(exc, TransientHTTP):
        return "http_5xx", True
    if isinstance(exc, PWTimeout):
        return "timeout", True
    if "net::ERR_" in msg:
        return "network", True
    if ("Target page, context or browser has been closed" in msg
            or "Browser has been closed" in msg or "Target closed" in msg):
        return "browser", True
    return "other", True


def _attempt(session, postcode, full_page_shot):
    """One page attempt. Returns (kind, payload, suggestion, shots):

      kind = "ok"        payload = options (non-empty list)
             "no_store"  payload = JB's message
             "error"     payload = exception
    """
    suburb, state, _area_type, _priority = LOCATIONS[postcode]
    browser = session.get()
    # A fresh context per attempt: no cookies/localStorage leak between
    # observations, so the previously selected location cannot carry over.
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    suggestion, shots = "", []
    try:
        open_product(page)
        field = find_delivery_input(page)
        enter_search_term(page, field, suburb)
        suggestion = select_postcode(page, postcode, suburb, state)
        wait_for_delivery_results(page)
        options = extract_delivery_options(page)
        if not options:
            shots.append(save_screenshot(page, postcode, "_ERROR"))
            return "error", RuntimeError("Options panel rendered but empty"), \
                suggestion, shots
        if full_page_shot:
            shots.append(save_screenshot(page, postcode))
        shots.append(save_panel_clip(page, postcode))
        return "ok", options, suggestion, shots
    except NoServingStore as exc:
        if full_page_shot:
            shots.append(save_screenshot(page, postcode))
        return "no_store", str(exc), suggestion, shots
    except Exception as exc:
        shots.append(save_screenshot(page, postcode, "_ERROR"))
        return "error", exc, suggestion, shots
    finally:
        try:
            context.close()
        except Exception:
            pass  # browser already gone; recovery happens on the next get()


def observe_postcode(session, postcode, full_page_shot, jsonl_path):
    """One observation, with bounded retries for TRANSIENT failures only.

    Retried (up to MAX_ATTEMPTS, backoff RETRY_BACKOFF_SECONDS): timeouts,
    network errors, browser crashes, HTTP 5xx, an empty options panel.
    Never retried: NO_STORE (a site answer), suggestion not offered, 403 /
    challenge (raises SiteBlocked out to the run), 429 (backs off with
    RATE_LIMIT_BACKOFF_SECONDS, then raises RateLimited out to the run).
    """
    attempt_log, all_shots = [], []
    rate_limit_waits = list(RATE_LIMIT_BACKOFF_SECONDS)
    attempt = 0
    while True:
        attempt += 1
        kind, payload, suggestion, shots = _attempt(session, postcode,
                                                    full_page_shot)
        all_shots += [s for s in shots if s]
        if kind == "ok":
            row = build_csv_row(postcode, payload, suggestion=suggestion)
            options, message = payload, ""
            attempt_log.append({"attempt": attempt, "result": "ok"})
            break
        if kind == "no_store":
            row = no_serving_store_row(postcode, payload, suggestion)
            options, message = [], payload
            attempt_log.append({"attempt": attempt, "result": "no_store"})
            break

        exc = payload
        err_type, transient = _classify_error(exc)
        first_line = (str(exc).splitlines() or [""])[0]
        attempt_log.append({"attempt": attempt, "result": "error",
                            "error_type": err_type, "error": first_line})
        log(f"  attempt {attempt} failed [{err_type}]: {first_line}")

        if err_type == "rate_limited" and rate_limit_waits:
            wait = rate_limit_waits.pop(0)
            log(f"  !! HTTP 429 - slowing down, waiting {wait}s")
            time.sleep(wait)
            continue
        if err_type in ("blocked", "rate_limited"):
            note = f"{'BLOCKED' if err_type == 'blocked' else 'RATE LIMITED'}: {first_line}"
            row = error_row(postcode, note, suggestion, err_type)
            row["attempts"] = attempt
            append_raw(postcode, [], jsonl_path, suggestion, row=row,
                       screenshots=all_shots, attempt_log=attempt_log)
            raise (SiteBlocked if err_type == "blocked" else RateLimited)(
                first_line, row)
        if transient and attempt < MAX_ATTEMPTS:
            wait = RETRY_BACKOFF_SECONDS[attempt - 1]
            log(f"  retrying in {wait}s")
            time.sleep(wait)
            continue

        prefix = "Timeout: " if err_type == "timeout" else (
            "" if isinstance(exc, SuggestionNotOffered) else f"{type(exc).__name__}: ")
        note = _with_browser_state(session, prefix + first_line)
        row = error_row(postcode, note, suggestion, err_type)
        options, message = [], ""
        break

    row["attempts"] = attempt
    append_raw(postcode, options, jsonl_path, suggestion, row=row,
               page_message=message, screenshots=all_shots,
               attempt_log=attempt_log)
    return row, options


def _with_browser_state(session, note):
    """Record a dead browser in the row itself."""
    try:
        if not session.get_if_live():
            return f"{note} | browser died - will be relaunched"
    except Exception:
        pass
    return note


# ------------------------------------------------- checkpoint / progress

FAILED_COLUMNS = ["timestamp", "run_id", "slot", "product_key", "postcode",
                  "suburb", "state", "error_type", "attempts", "notes"]


def obs_key(run_id, slot, product_key, postcode):
    return f"{run_id}|{slot}|{product_key}|{postcode}"


def load_done_keys(csv_path):
    """Keys of observations already in results.csv (resume)."""
    done = set()
    if not csv_path.exists():
        return done
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            done.add(obs_key(r["run_id"], r["slot"], r["product_key"],
                             r["postcode"]))
    return done


class Progress:
    """Counters, log lines and checkpoint.json for one process."""

    def __init__(self, out_dir, planned, done_keys):
        self.out_dir = out_dir
        self.planned = planned
        self.done_keys = done_keys
        self.started = datetime.now()
        self.counts = {"processed": 0, "valid": 0, "no_store": 0,
                       "failed": 0, "skipped_resume": 0,
                       "skipped_aborted": 0, "skipped_slots": 0}
        self.states = {}
        self.status = "running"
        self.last = None
        self.slots_completed = []

    def elapsed(self):
        s = int((datetime.now() - self.started).total_seconds())
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"

    def record(self, row):
        self.counts["processed"] += 1
        state = row["observation_state"]
        self.states[state] = self.states.get(state, 0) + 1
        if state == COLLECTION_ERROR:
            self.counts["failed"] += 1
        elif state == NO_STORE_REPORTED:
            self.counts["no_store"] += 1
        else:
            self.counts["valid"] += 1
        self.done_keys.add(obs_key(row["run_id"], row["slot"],
                                   row["product_key"], row["postcode"]))
        self.last = {k: row[k] for k in ("slot", "product_key", "postcode",
                                         "observation_state")}
        self.save()

    def line(self):
        c = self.counts
        done = c["processed"] + c["skipped_resume"]
        return (f"Processed: {done} / {self.planned} | Valid: {c['valid']} | "
                f"No store: {c['no_store']} | Failed: {c['failed']} | "
                f"Skipped: {c['skipped_resume'] + c['skipped_aborted']} | "
                f"Elapsed: {self.elapsed()}")

    def save(self):
        data = {
            "collector_version": COLLECTOR_VERSION,
            "run_id": RUN["run_id"],
            "study": RUN["study"],
            "status": self.status,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "started": self.started.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed": self.elapsed(),
            "planned_observations": self.planned,
            "counts": self.counts,
            "states": self.states,
            "slots_completed": self.slots_completed,
            "last_observation": self.last,
            "completed_keys": len(self.done_keys),
        }
        path = self.out_dir / "checkpoint.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)


# --------------------------------------------------------------- the pass

class PassAborted(Exception):
    pass


def run_pass(session, study, postcodes, products, full_page_shots, paths,
             progress):
    """One pass: every postcode x product for the current slot.

    Order is postcode-major, so one postcode's products are observed within
    ~2 minutes of each other (fair product comparison). Already-recorded
    observations (resume) are skipped. Raises SiteBlocked / RateLimited out
    to the caller; aborts the rest of the pass after MAX_CONSECUTIVE_ERRORS.
    """
    started = datetime.now()
    todo = [(pc, pk) for pc in postcodes for pk in products]
    log(f"--- pass: {len(postcodes)} postcode(s) x {len(products)} product(s) "
        f"= {len(todo)} observation(s), slot {RUN['slot']} ---")
    consecutive_errors = 0
    first_request = True
    for i, (postcode, pk) in enumerate(todo):
        RUN["product_key"] = pk
        key = obs_key(RUN["run_id"], RUN["slot"], pk, postcode)
        if key in progress.done_keys:
            progress.counts["skipped_resume"] += 1
            log(f"{postcode} {pk}: already recorded - skipped (resume)")
            continue
        if not first_request:
            time.sleep(random.uniform(DELAY_MIN_SECONDS, DELAY_MAX_SECONDS))
        first_request = False

        log(f"{postcode} {LOCATIONS[postcode][0]} [{pk}] ...")
        try:
            row, _ = observe_postcode(session, postcode, full_page_shots,
                                      paths["jsonl"])
        except (SiteBlocked, RateLimited) as exc:
            row = exc.args[1]
            append_csv(row, paths["csv"])
            append_csv(row, paths["failed"], FAILED_COLUMNS)
            progress.record(row)
            raise

        append_csv(row, paths["csv"])
        progress.record(row)
        if row["observation_state"] == COLLECTION_ERROR:
            append_csv(row, paths["failed"], FAILED_COLUMNS)
            log(f"  Postcode {postcode} -> FAILED  Reason: {row['error_type']}: "
                f"{row['notes'][:160]}")
            consecutive_errors += 1
        else:
            consecutive_errors = 0
            log(f"  {row['observation_state']} | promise={row['promise_text_verbatim']!r} "
                f"uber=${row['ondemand_price_aud']} | standard="
                f"{row['standard_promise_text']!r} ${row['standard_price_aud']}"
                + (f" | notes: {row['notes'][:120]}" if row["notes"] else ""))
        log("  " + progress.line())

        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            remaining = len(todo) - i - 1
            progress.counts["skipped_aborted"] += remaining
            log(f"!! {consecutive_errors} consecutive errors - aborting the "
                f"rest of this pass ({remaining} observation(s) not "
                f"attempted); next slot starts fresh")
            progress.save()
            raise PassAborted()
    mins = (datetime.now() - started).total_seconds() / 60
    log(f"--- pass complete in {mins:.1f} min ---")


# ------------------------------------------------------------- scheduling

def _slot_range(start_dt, end_dt, minutes):
    out = []
    t = start_dt
    while t <= end_dt:
        out.append(t)
        t += timedelta(minutes=minutes)
    return out


def slots_for(study, day):
    """All fixed wall-clock slots of `study`'s cycle starting on `day`.

    primary: 07:00-23:00 every 30 min on `day` (33) + 00:00-06:00 hourly on
    day+1 (7) = 40, identical to v2.0.0's slots_for(). validation: 09:00,
    13:00, 17:00, 21:00 on `day`.
    """
    cfg = STUDIES[study]
    out = []
    for start, end, step in cfg["day_slots"]:
        out += _slot_range(datetime.combine(day, start),
                           datetime.combine(day, end), step)
    nxt = day + timedelta(days=1)
    for start, end, step in cfg["next_day_slots"]:
        out += _slot_range(datetime.combine(nxt, start),
                           datetime.combine(nxt, end), step)
    return out


def current_cycle_day(study, now):
    """The cycle date whose last slot is still ahead of `now` (walks back a
    day to catch the overnight tail of yesterday's cycle)."""
    for offset in (-1, 0, 1):
        day = (now + timedelta(days=offset)).date()
        if now <= slots_for(study, day)[-1] + SLOT_GRACE:
            return day
    return now.date() + timedelta(days=1)


def export_cycle(paths, study, day, slot_indices, postcodes, products,
                 export_dir, complete):
    """Refresh the analysis-ready export of the CURRENT run (one cycle).

    Uses combine.export_run (reads results.csv only; the raw files are
    never modified). Never raises: an export problem is logged and
    collection carries on."""
    if export_dir is None:
        return
    try:
        import combine
        all_slots = slots_for(study, day)
        # The export always describes the WHOLE cycle (a CI chunk runs only
        # some slots, but its results.csv is seeded with earlier chunks').
        # It is COMPLETE only once the cycle's final slot has been run.
        chosen = all_slots
        complete = complete and (len(all_slots) - 1) in slot_indices
        now = datetime.now()
        due = chosen if complete else [s for s in chosen if s <= now]
        due = [s.strftime("%Y-%m-%d %H:%M") for s in due]
        if complete:
            status = (f"COMPLETE - cycle {day} finished; all {len(chosen)} slots "
                      f"due. Exported {now:%Y-%m-%d %H:%M:%S} (collector "
                      f"v{COLLECTOR_VERSION}, run {RUN['run_id']})")
        else:
            status = (f"IN PROGRESS - {len(due)} of {len(chosen)} slots due so far "
                      f"(last {due[-1] if due else '-'}). Snapshot "
                      f"{now:%Y-%m-%d %H:%M:%S}. Refresh after the next pass.")
        q = combine.export_run(paths["csv"], RUN["run_id"], export_dir, due,
                               postcodes, products, status,
                               f"{study} study, cycle {day}")
        if complete:
            (export_dir / "CYCLE_COMPLETE.txt").write_text(status + "\n",
                                                           encoding="utf-8")
        c = q["coverage"]
        log(f"  export -> {export_dir.name}: {q['rows_after_dedup']} rows, "
            f"coverage {c['observed_cells']}/{c['expected_cells']} "
            f"({c['coverage_pct']}%), errors {q['failed_requests (COLLECTION_ERROR)']}"
            f"{' [COMPLETE]' if complete else ''}")
    except Exception as exc:
        log(f"  !! export failed (collection continues): {type(exc).__name__}: {exc}")


def after_pass_hook():
    """Run $JB_PASS_HOOK after every pass (CI: push this pass's files to the
    repo's data branch). Never raises; never blocks longer than 3 min."""
    cmd = os.environ.get("JB_PASS_HOOK")
    if not cmd:
        return
    try:
        import subprocess
        env = dict(os.environ, JB_RUN_ID=RUN["run_id"], JB_SLOT=str(RUN["slot"]),
                   JB_OUT_DIR=str(RUN.get("out_dir", "")))
        r = subprocess.run(cmd, shell=True, env=env, timeout=180,
                           capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        log(f"  pass hook exit {r.returncode}: {' | '.join(tail)}")
    except Exception as exc:
        log(f"  !! pass hook failed (collection continues): {exc}")


def sleep_until(target):
    """Sleep until wall-clock `target` in <= 60 s steps. One long sleep does
    not count time the machine spends suspended, so it could wake hours
    late; re-checking the clock every minute cannot."""
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(60.0, remaining))


def run_slots(session, study, day, slot_indices, postcodes, products, paths,
              progress, full_shots, max_wait, export_dir=None):
    """Run the given slot indices of one cycle, in order, never overlapping.

    Past slots (beyond SLOT_GRACE) are skipped and logged - a historical
    observation cannot be made. If the first slot is more than `max_wait`
    away the run refuses to sit idle (it would burn CI minutes / hit the
    6 h job limit) and exits.
    """
    all_slots = slots_for(study, day)
    chosen = [(i, all_slots[i]) for i in slot_indices]
    log(f"cycle {day} ({study}): running slot index(es) "
        f"{slot_indices[0]}-{slot_indices[-1]}: "
        f"{chosen[0][1]:%d %b %H:%M} .. {chosen[-1][1]:%d %b %H:%M}")

    future = [(i, s) for i, s in chosen if datetime.now() <= s + SLOT_GRACE]
    if future:
        first_wait = (future[0][1] - datetime.now()).total_seconds()
        if first_wait > max_wait.total_seconds():
            log(f"!! first slot {future[0][1]:%d %b %H:%M} is "
                f"{first_wait / 3600:.1f} h away (limit "
                f"{max_wait.total_seconds() / 3600:.1f} h) - not waiting. "
                f"Start this chunk closer to its first slot.")
            progress.status = "too_early"
            progress.save()
            return

    for idx, slot in chosen:
        now = datetime.now()
        if now > slot + SLOT_GRACE:
            progress.counts["skipped_slots"] += 1
            log(f"SKIPPED slot {slot:%d %b %H:%M} - already past "
                f"(now {now:%H:%M:%S})")
            continue
        wait = (slot - now).total_seconds()
        if wait > 0:
            log(f"waiting {wait / 60:.1f} min for slot {slot:%d %b %H:%M}")
            sleep_until(slot)
            if datetime.now() > slot + SLOT_GRACE:
                # e.g. the machine was suspended through the slot
                progress.counts["skipped_slots"] += 1
                log(f"SKIPPED slot {slot:%d %b %H:%M} - woke too late "
                    f"(now {datetime.now():%H:%M:%S})")
                continue
        RUN["slot"] = slot.strftime("%Y-%m-%d %H:%M")
        log(f"=== SLOT {idx} {RUN['slot']} ===")
        if not session.get_if_live():
            session.restart("browser not live at slot start")
        try:
            run_pass(session, study, postcodes, products,
                     full_shots == "all", paths, progress)
        except PassAborted:
            pass
        progress.slots_completed.append(RUN["slot"])
        progress.save()
        export_cycle(paths, study, day, slot_indices, postcodes, products,
                     export_dir, complete=False)
        after_pass_hook()
    if progress.status == "running":
        export_cycle(paths, study, day, slot_indices, postcodes, products,
                     export_dir, complete=True)
        after_pass_hook()
    RUN["slot"] = "adhoc"


# --------------------------------------------------------------- run setup

def keep_awake(on):
    """Ask Windows not to sleep while this process runs. No-op elsewhere."""
    if not sys.platform.startswith("win"):
        return
    try:
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0)
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except Exception as exc:
        log(f"keep-awake unavailable: {exc}")


def check_clock():
    """Slots are Adelaide time. True when this process's clock is."""
    return time.strftime("%z") in ("+0930", "+1030")


def write_manifest(out_dir, args, study, postcodes, products, slot_indices,
                   day):
    """Freeze record: exactly which collector, products and design produced
    this run's data."""
    src = Path(__file__).read_bytes()
    try:
        from importlib.metadata import version
        pw_version = version("playwright")
    except Exception:
        pw_version = "unknown"
    manifest = {
        "run_id": RUN["run_id"],
        "study": study,
        "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": COLLECTOR_TZ,
        "tz_offset": time.strftime("%z"),
        "collector_version": COLLECTOR_VERSION,
        "collector_sha256": hashlib.sha256(src).hexdigest(),
        "python": sys.version.split()[0],
        "playwright": pw_version,
        "platform": sys.platform,
        "github_run": {k: os.environ.get(k) for k in (
            "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "GITHUB_SHA")
            if os.environ.get(k)},
        "mode": "test" if args.test else ("now" if args.now else "schedule"),
        "cycle_date": str(day) if day else None,
        "slot_indices": slot_indices,
        "slots": [s.strftime("%Y-%m-%d %H:%M")
                  for i, s in enumerate(slots_for(study, day))
                  if i in slot_indices] if day else [],
        "products": {k: PRODUCTS[k] for k in products},
        "postcodes": {pc: LOCATIONS[pc] for pc in postcodes},
        "retry": {"max_attempts": MAX_ATTEMPTS, "backoff_s": RETRY_BACKOFF_SECONDS,
                  "rate_limit_backoff_s": RATE_LIMIT_BACKOFF_SECONDS,
                  "max_consecutive_errors": MAX_CONSECUTIVE_ERRORS},
        "delay_s": [DELAY_MIN_SECONDS, DELAY_MAX_SECONDS],
    }
    path = out_dir / f"manifest_{RUN['run_id']}_{datetime.now():%H%M%S}.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def parse_range(text, n):
    """'0-9' -> [0..9]; '5' -> [5]; bounded to [0, n-1]."""
    a, _, b = text.partition("-")
    lo, hi = int(a), int(b or a)
    if not (0 <= lo <= hi < n):
        raise argparse.ArgumentTypeError(f"slot range {text!r} outside 0-{n - 1}")
    return list(range(lo, hi + 1))


# ------------------------------------------------------------------- main

def main(argv=None):
    global SHOT_DIR, LOG_FH
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--study", choices=sorted(STUDIES), default="primary")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true",
                      help="one immediate pass over the study's test postcodes")
    mode.add_argument("--now", action="store_true",
                      help="one immediate pass (use with --only)")
    mode.add_argument("--chunk", type=int,
                      help="run chunk N (1-based) of the cycle's slots")
    mode.add_argument("--slots", metavar="A-B",
                      help="run slot indices A..B of the cycle")
    parser.add_argument("--only", metavar="POSTCODE", nargs="+",
                        help="restrict to these postcodes")
    parser.add_argument("--products", nargs="+", metavar="KEY",
                        help="restrict to these product keys")
    parser.add_argument("--cycle-date", type=lambda s: datetime.strptime(
                            s, "%Y-%m-%d").date(),
                        help="cycle start date (default: current/next cycle)")
    parser.add_argument("--out-dir", type=Path,
                        help="output folder (default data/<study>/<run_id>)")
    parser.add_argument("--full-shots", choices=["all", "errors"],
                        help="full-page screenshots on every observation or "
                             "errors only (default: all in --test/--now, "
                             "errors otherwise); panel clips are always taken")
    parser.add_argument("--max-wait-min", type=float, default=45,
                        help="refuse to idle longer than this before the "
                             "first slot (default 45; chained CI chunks "
                             "pass a larger value)")
    parser.add_argument("--cycles", type=int, default=1,
                        help="consecutive cycles to run (local runs; each "
                             "cycle gets its own run_id)")
    parser.add_argument("--export-names", metavar="NAME[,NAME...]",
                        help="write an analysis-ready export folder per cycle "
                             "into --out-dir, refreshed after every pass; one "
                             "name per cycle, the cycle date is appended")
    parser.add_argument("--print-cycle-date", action="store_true",
                        help="print the cycle date that would be used, exit")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--edge", action="store_true",
                        help="use installed Microsoft Edge instead of Chromium")
    args = parser.parse_args(argv)

    cfg = STUDIES[args.study]

    if not check_clock():
        parser.error(f"clock offset is {time.strftime('%z')}, not Adelaide "
                     f"(+0930/+1030). Slots would be wrong. Run on an "
                     f"Adelaide-time machine or on Linux/macOS (TZ is forced).")

    postcodes = cfg["test_postcodes"] if args.test else cfg["postcodes"]
    if args.only:
        unknown = [pc for pc in args.only if pc not in LOCATIONS]
        if unknown:
            parser.error(f"unknown postcode(s): {', '.join(unknown)}")
        postcodes = args.only
    products = cfg["products"]
    if args.products:
        bad = [k for k in args.products if k not in PRODUCTS]
        if bad:
            parser.error(f"unknown product key(s): {', '.join(bad)}")
        products = args.products

    if args.print_cycle_date:
        print(args.cycle_date or current_cycle_day(args.study, datetime.now()))
        return 0

    immediate = args.test or args.now
    day, slot_indices = None, []
    if not immediate:
        day = args.cycle_date or current_cycle_day(args.study, datetime.now())
        n = len(slots_for(args.study, day))
        if args.chunk is not None:
            chunks = cfg["chunks"]
            if not 1 <= args.chunk <= len(chunks):
                log(f"study {args.study} has {len(chunks)} chunk(s); chunk "
                    f"{args.chunk} has nothing to do")
                return 0
            lo, hi = chunks[args.chunk - 1]
            slot_indices = list(range(lo, hi + 1))
        else:
            try:
                slot_indices = parse_range(args.slots or f"0-{n - 1}", n)
            except argparse.ArgumentTypeError as exc:
                parser.error(str(exc))

    # Deterministic run id: identical for every chunk of one cycle, so the
    # combined dataset groups cleanly and resume keys line up.
    if immediate:
        tag = "test" if args.test else "now"
        RUN["run_id"] = (f"{args.study}_{tag}_{datetime.now():%Y%m%d}"
                         f"_v{COLLECTOR_VERSION}{ENV_TAG}")
    else:
        RUN["run_id"] = f"{args.study}_{day:%Y%m%d}_v{COLLECTOR_VERSION}{ENV_TAG}"
    RUN["study"] = args.study

    out_dir = args.out_dir or Path("data") / args.study / RUN["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    RUN["out_dir"] = out_dir
    SHOT_DIR = out_dir / "screenshots"
    paths = {"csv": out_dir / "results.csv",
             "jsonl": out_dir / "raw_observations.jsonl",
             "failed": out_dir / "failed_postcodes.csv"}
    LOG_FH = (out_dir / "scraper.log").open("a", encoding="utf-8")
    if not paths["failed"].exists():
        # Always present (header only when nothing failed), so every
        # artifact has the same four files.
        with paths["failed"].open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh, quoting=csv.QUOTE_NONNUMERIC).writerow(FAILED_COLUMNS)
    full_shots = args.full_shots or ("all" if immediate else "errors")

    manifest = write_manifest(out_dir, args, args.study, postcodes, products,
                              slot_indices, day)
    done = load_done_keys(paths["csv"])
    planned = (len(postcodes) * len(products) * (len(slot_indices) or 1)
               * (1 if immediate else args.cycles))
    progress = Progress(out_dir, planned, done)

    log(f"collector v{COLLECTOR_VERSION}  run {RUN['run_id']}  study {args.study}")
    log(f"clock  : {COLLECTOR_TZ} ({time.strftime('%z')})")
    log(f"design : {len(postcodes)} postcode(s) x {len(products)} product(s) x "
        f"{len(slot_indices) or 1} slot(s) = {planned} observation(s)")
    log(f"out    : {out_dir}  (resume: {len(done)} already recorded)")
    log(f"manifest: {manifest}")

    exit_code = 0
    with sync_playwright() as p:
        session = BrowserSession(p, headed=args.headed, edge=args.edge)
        keep_awake(True)
        try:
            if immediate:
                # Per-day key: rerunning the same test the same day with the
                # same --out-dir resumes instead of duplicating.
                RUN["slot"] = f"{'test' if args.test else 'now'} {datetime.now():%Y-%m-%d}"
                try:
                    run_pass(session, args.study, postcodes, products,
                             full_shots == "all", paths, progress)
                except PassAborted:
                    pass
                progress.save()
                after_pass_hook()
            else:
                for c in range(args.cycles):
                    cday = day + timedelta(days=c)
                    RUN["run_id"] = f"{args.study}_{cday:%Y%m%d}_v{COLLECTOR_VERSION}{ENV_TAG}"
                    if c:
                        write_manifest(out_dir, args, args.study, postcodes,
                                       products, slot_indices, cday)
                    log(f"##### CYCLE {c + 1}/{args.cycles}: {cday:%A %d %b %Y} "
                        f"run {RUN['run_id']} #####")
                    names = (args.export_names or "").split(",")
                    export_dir = (out_dir / f"{names[c].strip()}_{cday:%Y%m%d}"
                                  if c < len(names) and names[c].strip() else None)
                    run_slots(session, args.study, cday, slot_indices,
                              postcodes, products, paths, progress, full_shots,
                              timedelta(minutes=args.max_wait_min), export_dir)
                    if progress.status != "running":
                        break
            if progress.status == "running":
                progress.status = "completed"
            elif progress.status == "too_early":
                exit_code = 4
        except SiteBlocked as exc:
            progress.status = "blocked"
            log(f"!!! STOPPED: the site is blocking automated access "
                f"({exc.args[0]}). Not retrying or circumventing. Later "
                f"slots in this run are not attempted.")
            exit_code = 3
        except RateLimited as exc:
            progress.status = "rate_limited"
            log(f"!!! STOPPED: HTTP 429 persisted after backing off "
                f"({exc.args[0]}). Not continuing.")
            exit_code = 3
        except KeyboardInterrupt:
            progress.status = "interrupted"
            log("interrupted - progress saved; rerun the same command to resume")
            exit_code = 130
        finally:
            keep_awake(False)
            session.close()
            progress.save()
            log(f"FINISHED status={progress.status} | {progress.line()} | "
                f"states={progress.states} | browser restarts={session.restarts}")
            LOG_FH.close()
            LOG_FH = None
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
