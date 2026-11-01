"""
STEP 1: Coverage check for Indian products on Open Food Facts.

Downloads a sample of products sold in India and reports how many have
allergen / ingredient information, so we know if the project is worth building.

Run:  python coverage_check.py
Data source: Open Food Facts (https://world.openfoodfacts.org), licensed under ODbL.
"""
import os
import time

import pandas as pd
import requests

BASE = "https://world.openfoodfacts.org/api/v2/search"
HEADERS = {"User-Agent": "AllergenAnalysis/1.0 (student portfolio project)"}
FIELDS = "code,product_name,brands,categories_tags,allergens_tags,traces_tags,ingredients_text,states_tags"
PAGE_SIZE = 100
MAX_PAGES = 20            # 20 pages x 100 = up to 2,000 products
PAUSE = 7                 # seconds between requests (Open Food Facts asks for gentle use)


def fetch_page(page):
    params = {"countries_tags_en": "india", "fields": FIELDS, "page_size": PAGE_SIZE, "page": page}
    for attempt in range(4):
        try:
            r = requests.get(BASE, params=params, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.json().get("products", [])
            print(f"  page {page}: HTTP {r.status_code}, retrying...")
        except requests.RequestException as e:
            print(f"  page {page}: {str(e)[:80]}, retrying...")
        time.sleep(10)
    return None


def collect():
    rows = []
    for page in range(1, MAX_PAGES + 1):
        products = fetch_page(page)
        if products is None:
            print("Stopping early because the API kept failing.")
            break
        if not products:
            break
        rows.extend(products)
        print(f"  page {page}: total {len(rows)} products")
        time.sleep(PAUSE)
    return rows


def summarize(rows):
    df = pd.DataFrame(rows)
    for col in ("allergens_tags", "traces_tags", "categories_tags", "states_tags"):
        df[col] = df[col].apply(lambda v: v if isinstance(v, list) else []) if col in df else [[] for _ in range(len(df))]
    df["ingredients_text"] = df["ingredients_text"].fillna("") if "ingredients_text" in df else ""

    n = len(df)
    has_ing = (df["ingredients_text"].str.strip() != "").sum()
    has_all = (df["allergens_tags"].str.len() > 0).sum()
    has_tr = (df["traces_tags"].str.len() > 0).sum()
    ing_done = df["states_tags"].apply(lambda s: "en:ingredients-completed" in s).sum()

    print("\n================ COVERAGE REPORT ================")
    print(f"Products downloaded:                 {n}")
    print(f"With ingredients text:               {has_ing} ({100*has_ing/n:.0f}%)")
    print(f"With ingredients marked completed:   {ing_done} ({100*ing_done/n:.0f}%)")
    print(f"With at least one allergen listed:   {has_all} ({100*has_all/n:.0f}%)")
    print(f"With 'may contain' (traces) listed:  {has_tr} ({100*has_tr/n:.0f}%)")

    top = df.explode("allergens_tags")["allergens_tags"].dropna().str.replace("en:", "", regex=False).value_counts().head(10)
    print("\nTop 10 allergens found:")
    print(top.to_string())

    verdict = "GOOD ENOUGH to build the project." if (n >= 1000 and has_all / n >= 0.25) else \
              "THIN. We may need a different topic or a smaller scope."
    print(f"\nVerdict (my rule of thumb: 1,000+ products and 25%+ with allergens): {verdict}")

    out = df.copy()
    for col in ("allergens_tags", "traces_tags", "categories_tags", "states_tags"):
        out[col] = out[col].apply(lambda v: ";".join(v))
    os.makedirs("data", exist_ok=True)
    out.to_csv("data/india_sample.csv", index=False)
    print("\nSaved sample to data/india_sample.csv")


if __name__ == "__main__":
    print("Downloading a sample of Indian products (takes about 2-3 minutes)...")
    data = collect()
    if not data:
        print("No data downloaded. Check your internet connection and try again.")
    else:
        summarize(data)
