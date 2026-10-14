"""Stream, flatten, deduplicate and reproducibly sample winddude listings.

Run from the repository root. Original data is never modified. SQLite keeps
deduplication on disk; reservoir sampling operates on unique eligible listings.
The SQLite intermediate is reusable for a different sample size or seed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import re
import shutil
import sqlite3
import sys
import time
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".pipeline_deps").exists():
    sys.path.insert(0, str(ROOT / ".pipeline_deps"))
import ijson
import pandas as pd

FIELDS = [
    "listing_key", "source_record_id", "date_posted", "date_last_crawled",
    "posting_year", "country", "state_code", "latitude", "longitude",
    "make_model_raw", "model_year", "manufacturer", "body_style_raw",
    "body_style", "transmission", "price_usd", "currency_code", "mileage_raw",
    "vehicle_age", "next_model_year", "is_japanese_brand", "brand_match_status",
]
BRANDS = {
    "acura": ["acura"], "alfa-romeo": ["alfa romeo"], "aston-martin": ["aston martin"],
    "audi": ["audi"], "bentley": ["bentley"], "bmw": ["bmw"], "buick": ["buick"],
    "cadillac": ["cadillac"], "chevrolet": ["chevrolet", "chevy"], "chrysler": ["chrysler"],
    "dodge": ["dodge"], "ferrari": ["ferrari"], "fiat": ["fiat"], "ford": ["ford"],
    "genesis": ["genesis"], "gmc": ["gmc"], "honda": ["honda"], "hyundai": ["hyundai"],
    "infiniti": ["infiniti"], "isuzu": ["isuzu"], "jaguar": ["jaguar"], "jeep": ["jeep"],
    "kia": ["kia"], "lamborghini": ["lamborghini"], "land-rover": ["land rover", "range rover"],
    "lexus": ["lexus"], "lincoln": ["lincoln"], "lotus": ["lotus"], "maserati": ["maserati"],
    "mazda": ["mazda"], "mercedes-benz": ["mercedes benz", "mercedes"], "mercury": ["mercury"],
    "mini": ["mini cooper", "mini"], "mitsubishi": ["mitsubishi"], "nissan": ["nissan", "datsun"],
    "oldsmobile": ["oldsmobile"], "plymouth": ["plymouth"], "pontiac": ["pontiac"],
    "porsche": ["porsche"], "ram": ["ram"], "rolls-royce": ["rolls royce"], "saab": ["saab"],
    "saturn": ["saturn"], "scion": ["scion"], "smart": ["smart"], "subaru": ["subaru"],
    "suzuki": ["suzuki"], "tesla": ["tesla"], "toyota": ["toyota"],
    "volkswagen": ["volkswagen", "vw"], "volvo": ["volvo"],
}
JAPANESE = {"acura", "honda", "infiniti", "isuzu", "lexus", "mazda", "mitsubishi", "nissan", "scion", "subaru", "suzuki", "toyota"}
PATTERNS = [(name, re.compile(r"\b(?:" + "|".join(re.escape(a) for a in aliases) + r")\b"))
            for name, aliases in BRANDS.items()]
BODY_STYLES = {
    "sedan": "sedan", "suv": "suv", "pickup": "pickup", "truck": "truck",
    "coupe": "coupe", "convertible": "convertible", "hatchback": "hatchback",
    "wagon": "wagon", "van": "van", "mini van": "minivan", "minivan": "minivan",
    "offroad": "offroad", "off road": "offroad", "bus": "bus", "other": "other",
}


def mapping(value):
    return value if isinstance(value, dict) else {}


def text(value):
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def number(value):
    try:
        if isinstance(value, bool):
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def parse_date(value):
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def normalize_words(value):
    return re.sub(r"[^a-z0-9]+", " ", (text(value) or "").lower()).strip()


def brand_from_model(value):
    words = normalize_words(value)
    # Remove a leading year; match a brand at the start to avoid brand names
    # mentioned in descriptive comparisons later in a make/model string.
    words = re.sub(r"^(?:19|20)\d{2}\s+", "", words)
    candidates = [brand for brand, pattern in PATTERNS if pattern.match(words)]
    if "dodge" in candidates and re.match(r"dodge ram\b", words):
        return "dodge", "matched"
    if len(candidates) == 1:
        return candidates[0], "matched"
    return None, "ambiguous" if candidates else ("missing" if not words else "unrecognized")


def identity(record, source):
    url = text(source.get("url"))
    if url:
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            canonical = urlunsplit(("https", parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))
            return hashlib.sha256(("url:" + canonical).encode()).hexdigest()
    record_id = text(record.get("_id"))
    return hashlib.sha256(("id:" + record_id).encode()).hexdigest() if record_id else None


def flatten(record, year, audit, diagnostics):
    audit["raw_records"] += 1
    if not isinstance(record, dict):
        audit["invalid_record_object"] += 1
        return None
    source = mapping(record.get("_source"))
    location = mapping(source.get("location"))
    country = (text(location.get("country")) or "").upper()
    diagnostics["raw_country_counts"][country or "missing"] += 1
    if country != "US":
        return None
    audit["after_us_filter"] += 1
    posted = parse_date(source.get("date_posted"))
    diagnostics["us_posting_year_counts"][str(posted.year) if posted else "invalid_or_missing"] += 1
    if posted is None or posted.year != year:
        return None
    audit["after_posting_year_filter"] += 1
    coords = mapping(location.get("lat_long"))
    latitude, longitude = number(coords.get("lat")), number(coords.get("lon"))
    if latitude is None or longitude is None or not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or (latitude == 0 and longitude == 0):
        return None
    audit["after_valid_coordinates"] += 1
    key = identity(record, source)
    if key is None:
        return None
    audit["after_listing_identity"] += 1
    vehicle, specifications, price = (mapping(source.get(k)) for k in ["vehicle", "specifications", "price"])
    model = text(vehicle.get("make_model"))
    manufacturer, brand_status = brand_from_model(model)
    diagnostics["eligible_brand_match_counts"][brand_status] += 1
    model_year = number(vehicle.get("year"))
    if model_year is not None and (not model_year.is_integer() or not 1886 <= model_year <= year + 1):
        audit["invalid_model_year_set_missing"] += 1
        model_year = None
    model_year = int(model_year) if model_year is not None else None
    next_model = model_year == year + 1
    if next_model:
        audit["next_model_year_age_missing"] += 1
    age = year - model_year if model_year is not None and not next_model else None
    amount = number(price.get("usd_price"))
    if amount is not None and amount <= 0:
        audit["nonpositive_price_set_missing"] += 1
        amount = None
    mileage = number(source.get("mileage"))
    if mileage is not None and mileage < 0:
        audit["negative_mileage_set_missing"] += 1
        mileage = None
    raw_body = text(specifications.get("body_style"))
    body = BODY_STYLES.get(normalize_words(raw_body))
    transmission = (text(specifications.get("transmission")) or "").lower() or None
    region = text(mapping(location.get("source")).get("region"))
    state = region[3:].upper() if region and re.fullmatch(r"US-[A-Za-z]{2}", region) else None
    crawled = parse_date(source.get("date_last_crawled"))
    ranked = crawled or posted
    rank = ranked.replace(tzinfo=timezone.utc) if ranked.tzinfo is None else ranked.astimezone(timezone.utc)
    result = dict(zip(FIELDS, [
        key, text(record.get("_id")), text(source.get("date_posted")), text(source.get("date_last_crawled")),
        year, country, state, latitude, longitude, model, model_year, manufacturer,
        raw_body, body, transmission, amount, text(price.get("currency_code")), mileage,
        age, next_model, manufacturer in JAPANESE if manufacturer else None, brand_status,
    ]))
    for column, value in result.items():
        if value is None:
            diagnostics["eligible_missing_counts_before_dedup"][column] += 1
    return result, rank.isoformat()


def scan(source_path, database, year, batch_size, progress_seconds):
    if database.exists():
        raise FileExistsError(f"Intermediate exists: {database}; use --reuse-intermediate after a completed scan.")
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA cache_size=-1048576")
    # Keep large payloads in append-oriented table pages, with a separate narrow
    # key index. A WITHOUT ROWID table would random-write the entire payload
    # B-tree on each hash key and become much slower as the table grows.
    connection.execute("CREATE TABLE listings (listing_key TEXT UNIQUE NOT NULL, crawl_rank TEXT, state_code TEXT, payload TEXT)")
    connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
    audit = Counter()
    diagnostics = {name: Counter() for name in ["raw_country_counts", "us_posting_year_counts", "eligible_brand_match_counts", "eligible_missing_counts_before_dedup"]}
    sql = """INSERT INTO listings VALUES (?,?,?,?) ON CONFLICT(listing_key) DO UPDATE SET
             crawl_rank=excluded.crawl_rank, state_code=excluded.state_code, payload=excluded.payload
             WHERE excluded.crawl_rank >= listings.crawl_rank"""
    batch = []
    start = last = time.monotonic()
    try:
        with source_path.open("rb") as stream:
            for record in ijson.items(stream, "item", use_float=True):
                flattened = flatten(record, year, audit, diagnostics)
                if flattened:
                    row, rank = flattened
                    batch.append((row["listing_key"], rank, row["state_code"], json.dumps(row, separators=(",", ":"), ensure_ascii=False)))
                if len(batch) >= batch_size:
                    connection.executemany(sql, batch)
                    connection.commit()
                    batch.clear()
                now = time.monotonic()
                if now - last >= progress_seconds:
                    print(f"Scan {stream.tell()/source_path.stat().st_size:.1%}: {audit['raw_records']:,} records read; {audit['after_listing_identity']:,} eligible before dedup; elapsed {int(now-start)}s", flush=True)
                    if shutil.disk_usage(database.parent).free < 1024**3:
                        raise RuntimeError("Less than 1 GiB free; partial intermediate retained, scan not marked complete.")
                    last = now
        if batch:
            connection.executemany(sql, batch)
            connection.commit()
        unique = connection.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        audit["after_deduplication"] = unique
        audit["duplicate_eligible_records_removed"] = audit["after_listing_identity"] - unique
        metadata = {
            "scan_complete": True, "source_path": str(source_path.resolve()),
            "source_bytes": source_path.stat().st_size, "source_mtime_ns": source_path.stat().st_mtime_ns,
            "posting_year": year, "audit": dict(audit), "diagnostics": {k: dict(v) for k, v in diagnostics.items()},
            "scan_seconds": round(time.monotonic() - start, 1),
        }
        connection.execute("INSERT INTO metadata VALUES (?,?)", ("scan", json.dumps(metadata)))
        connection.commit()
        print(f"Scan complete: {unique:,} unique eligible listings", flush=True)
        return metadata
    finally:
        connection.close()


def sample(database, source_path, output_dir, report_dir, size, seed, year):
    connection = sqlite3.connect(database)
    metadata_row = connection.execute("SELECT value FROM metadata WHERE key='scan'").fetchone()
    if not metadata_row:
        raise RuntimeError("Intermediate scan is incomplete; cannot use it for sampling.")
    metadata = json.loads(metadata_row[0])
    if metadata["posting_year"] != year:
        raise RuntimeError("Intermediate does not match the requested source/year.")
    if source_path.exists() and (metadata["source_bytes"] != source_path.stat().st_size or metadata["source_mtime_ns"] != source_path.stat().st_mtime_ns):
        raise RuntimeError("Intermediate does not match the requested source/year.")
    metadata["source_available_during_sampling"] = source_path.exists()
    if not source_path.exists():
        print("Original JSON is unavailable; reusing the completed intermediate and its recorded source provenance.", flush=True)
    generator = random.Random(seed)
    reservoir = []
    total = metadata["audit"]["after_deduplication"]
    population_missing = Counter()
    population_brand = Counter()
    start = last = time.monotonic()
    # Deterministic insertion order avoids random disk reads of every payload.
    # Rebuilding from the same input and rules produces the same rowid order.
    for seen, (payload,) in enumerate(connection.execute("SELECT payload FROM listings ORDER BY rowid"), 1):
        row = json.loads(payload)
        population_missing.update(k for k, v in row.items() if v is None)
        population_brand[row["manufacturer"] or "unknown"] += 1
        if seen <= size:
            reservoir.append(row)
        else:
            position = generator.randrange(seen)
            if position < size:
                reservoir[position] = row
        now = time.monotonic()
        if now - last >= 20:
            print(f"Sampling {seen/total:.1%}: {seen:,}/{total:,} unique records", flush=True)
            last = now
    frame = pd.DataFrame(reservoir, columns=FIELDS)
    for col in ["model_year", "posting_year", "vehicle_age"]:
        frame[col] = pd.array(frame[col], dtype="Int64")
    for col in ["next_model_year", "is_japanese_brand"]:
        frame[col] = pd.array(frame[col], dtype="boolean")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "vehicles_us_2019_sample.parquet"
    frame.to_parquet(destination, index=False, compression="zstd")
    audit = metadata["audit"]
    stages = ["raw_records", "after_us_filter", "after_posting_year_filter", "after_valid_coordinates", "after_listing_identity", "after_deduplication"]
    previous = None
    records = []
    for stage in stages:
        count = audit.get(stage, 0)
        records.append({"step": stage, "rows": count, "removed_since_previous": None if previous is None else previous - count})
        previous = count
    records.append({"step": "random_sample", "rows": len(frame), "removed_since_previous": total - len(frame)})
    pd.DataFrame(records).to_csv(report_dir / "automotive_processing_audit.csv", index=False)
    pd.DataFrame([{"column": col, "population_missing": population_missing[col], "population_missing_share": population_missing[col]/total if total else None,
                   "sample_missing": int(frame[col].isna().sum()), "sample_missing_share": float(frame[col].isna().mean())} for col in FIELDS]).to_csv(report_dir / "automotive_missingness.csv", index=False)
    population_state = dict(connection.execute("SELECT COALESCE(state_code,'unknown'), COUNT(*) FROM listings GROUP BY COALESCE(state_code,'unknown')"))
    sample_state = frame["state_code"].fillna("unknown").value_counts().to_dict()
    pd.DataFrame([{"state_code": state, "population_listings": count, "sample_listings": sample_state.get(state,0), "population_share": count/total,
                   "sample_share": sample_state.get(state,0)/len(frame) if len(frame) else None} for state,count in sorted(population_state.items())]).to_csv(report_dir / "automotive_state_coverage.csv", index=False)
    sample_brand = frame["manufacturer"].fillna("unknown").value_counts().to_dict()
    pd.DataFrame([{"manufacturer": brand, "population_listings": count, "sample_listings": sample_brand.get(brand,0), "population_share": count/total,
                   "sample_share": sample_brand.get(brand,0)/len(frame) if len(frame) else None} for brand,count in sorted(population_brand.items())]).to_csv(report_dir / "automotive_brand_coverage.csv", index=False)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    metadata.update({"sample_method": "uniform reservoir sample without replacement after deduplication; deterministic SQLite insertion order",
                     "seed": seed, "requested_sample_size": size, "sample_rows": len(frame), "sample_columns": len(frame.columns),
                     "eligible_unique_listings": total, "inclusion_probability": min(size/total,1) if total else None,
                     "sample_path": str(destination.resolve()), "sample_bytes": destination.stat().st_size, "sample_sha256": digest,
                     "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                     "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     "libraries": {name: importlib.metadata.version(name) for name in ["ijson", "pandas", "pyarrow"]},
                     "brand_aliases": BRANDS, "japanese_brand_list": sorted(JAPANESE), "body_style_mapping": BODY_STYLES,
                     "limitations": ["Mileage unit has not been verified; mileage_raw is not used in the research questions.",
                                     "Coordinates are range-checked, not verified against US boundaries.",
                                     "Brand extraction is conservative and provisional; unknown/ambiguous models remain missing.",
                                     "Simple random sampling does not ensure sufficient listings near every university.",
                                     "Next-model-year listings retain model year but have missing vehicle_age."]})
    (report_dir / "automotive_sample_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    connection.close()
    print(f"Saved {len(frame):,} rows, {len(frame.columns)} columns; {destination.stat().st_size/1024**2:.1f} MiB to {destination}", flush=True)
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/winddude_automotive_2019_2020/extracted/dump1.json")
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/automotive_us_2019.sqlite")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--sample-size", type=int, default=500000)
    parser.add_argument("--seed", type=int, default=6182019)
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--progress-seconds", type=int, default=20)
    parser.add_argument("--reuse-intermediate", action="store_true")
    args = parser.parse_args()
    if args.sample_size <= 0 or args.batch_size <= 0:
        parser.error("sample-size and batch-size must be positive")
    destination = args.output_dir / "vehicles_us_2019_sample.parquet"
    if destination.exists():
        raise FileExistsError(f"Sample exists: {destination}; choose a different --output-dir to retain it.")
    args.database.parent.mkdir(parents=True, exist_ok=True)
    if not args.reuse_intermediate:
        scan(args.source, args.database, args.year, args.batch_size, args.progress_seconds)
    sample(args.database, args.source, args.output_dir, args.report_dir, args.sample_size, args.seed, args.year)


if __name__ == "__main__":
    main()
