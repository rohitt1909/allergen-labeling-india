"""
STEP 2: Download more Indian products and add them to data/india_sample.csv.
(No pandas needed: uses only Python's built-in csv module and requests.)

- Picks up where coverage_check.py stopped (no need to start over)
- Saves after every page, so an error never loses data
- Waits longer between retries when the server returns 503 (overloaded)

Run:  python download_more.py
Data source: Open Food Facts (https://world.openfoodfacts.org), licensed under ODbL.
"""
import csv
import os
import time

import requests

BASE = "https://world.openfoodfacts.org/api/v2/search"
HEADERS = {"User-Agent": "AllergenAnalysis/1.0 (student portfolio project)"}
FIELDS = ["code", "product_name", "brands", "categories_tags", "allergens_tags",
          "traces_tags", "ingredients_text", "states_tags"]
LIST_FIELDS = ["categories_tags", "allergens_tags", "traces_tags", "states_tags"]
PAGE_SIZE = 100
LAST_PAGE = 30            # up to 3,000 products in total
PAUSE = 8
FILE = "data/india_sample.csv"


def fetch_page(page):
    params = {"countries_tags_en": "india", "fields": ",".join(FIELDS),
              "page_size": PAGE_SIZE, "page": page}
    for attempt in range(1, 6):
        wait = 15 * attempt
        try:
            r = requests.get(BASE, params=params, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.json().get("products", [])
            print(f"  page {page}: HTTP {r.status_code}, waiting {wait}s (try {attempt}/5)")
        except requests.RequestException as e:
            print(f"  page {page}: {str(e)[:70]}, waiting {wait}s (try {attempt}/5)")
        time.sleep(wait)
    return None


def flatten(p):
    row = {}
    for f in FIELDS:
        v = p.get(f, "")
        if f in LIST_FIELDS and isinstance(v, list):
            v = ";".join(v)
        row[f] = "" if v is None else str(v)
    return row


def load_existing():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, newline="", encoding="utf-8") as f:
        rows = {}
        for r in csv.DictReader(f):
            rows[r.get("code", "")] = {k: (r.get(k) or "") for k in FIELDS}
        return rows


def save(rows):
    with open(FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows.values())


def main():
    os.makedirs("data", exist_ok=True)
    rows = load_existing()
    print(f"Already have {len(rows)} products.")
    page = len(rows) // PAGE_SIZE + 1
    failures = 0

    while page <= LAST_PAGE and failures < 2:
        products = fetch_page(page)
        if products is None:
            failures += 1
            print(f"  page {page} failed. Skipping to the next page.")
            page += 1
            continue
        failures = 0
        if not products:
            print("No more products available.")
            break
        for p in products:
            r = flatten(p)
            rows[r["code"]] = r
        save(rows)
        print(f"  page {page} done. Total saved: {len(rows)}")
        page += 1
        time.sleep(PAUSE)

    print(f"\nFinished. {len(rows)} products saved in {FILE}")
    if failures >= 2:
        print("The server kept failing. Wait 15-30 minutes and run this script again; it will continue from here.")


if __name__ == "__main__":
    main()