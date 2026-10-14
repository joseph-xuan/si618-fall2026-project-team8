"""Prepare college/vehicle tables after the IPEDS dictionary has been checked.

Input colleges.csv is a canonical one-row-per-UNITID table documented in
docs/data_plan.md. This script intentionally does not guess raw EF level codes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

EARTH_RADIUS_MILES = 3958.7613
COLLEGE_COLUMNS = [
    "unitid", "institution_name", "latitude", "longitude", "enrollment_year",
    "total_students", "international_students", "female_students", "graduate_students",
]
VEHICLE_COLUMNS = [
    "id", "price", "year", "odometer", "transmission", "manufacturer",
    "paint_color", "lat", "long", "posting_date",
]


def coordinates_valid(frame, latitude, longitude):
    lat, lon = frame[latitude], frame[longitude]
    return lat.between(-90, 90) & lon.between(-180, 180) & ~((lat == 0) & (lon == 0))


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def missingness(frame, source):
    return pd.DataFrame({
        "source": source, "column": frame.columns,
        "dtype": [str(dtype) for dtype in frame.dtypes],
        "rows": len(frame), "missing_count": frame.isna().sum().to_numpy(),
        "missing_share": frame.isna().mean().to_numpy(),
    })


def prepare_colleges(frame, audit, notes):
    frame = frame.copy()
    audit.append({"dataset": "colleges", "step": "input", "rows": len(frame)})
    for column in COLLEGE_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["unitid"] = frame["unitid"].str.strip().replace("", pd.NA)
    if frame["unitid"].dropna().duplicated().any():
        raise ValueError("Duplicate UNITID: validate the HD/EF join before continuing.")
    keep = frame["unitid"].notna() & coordinates_valid(frame, "latitude", "longitude")
    frame = frame.loc[keep].copy()
    audit.append({"dataset": "colleges", "step": "valid_id_and_coordinates", "rows": len(frame)})
    for column in ["total_students", "international_students", "female_students", "graduate_students"]:
        bad = (frame[column] < 0) | (frame[column].notna() & (frame[column] % 1 != 0))
        notes[f"invalid_{column}"] = int(bad.sum())
        frame.loc[bad, column] = np.nan
    frame = frame.loc[frame["total_students"] > 0].copy()
    audit.append({"dataset": "colleges", "step": "positive_total_enrollment", "rows": len(frame)})
    if frame.empty:
        raise ValueError("No eligible colleges remain.")
    valid_year = frame["enrollment_year"].between(1900, 2100) & (frame["enrollment_year"] % 1 == 0)
    if not valid_year.all() or frame["enrollment_year"].nunique() != 1:
        raise ValueError("Use one verified enrollment year with valid integer year values.")
    for group in ["international", "female", "graduate"]:
        count = f"{group}_students"
        bad = frame[count] > frame["total_students"]
        notes[f"{group}_count_exceeds_total"] = int(bad.sum())
        frame.loc[bad, count] = np.nan
        frame[f"{group}_student_share"] = frame[count] / frame["total_students"]
    return frame


def prepare_vehicles(frame, audit, notes):
    frame = frame.copy()
    audit.append({"dataset": "vehicles", "step": "input", "rows": len(frame)})
    frame["id"] = frame["id"].str.strip().replace("", pd.NA)
    frame = frame.loc[frame["id"].notna()].copy()
    audit.append({"dataset": "vehicles", "step": "nonmissing_listing_id", "rows": len(frame)})
    notes["duplicate_id_rows"] = int(frame["id"].duplicated().sum())
    distinct = frame.drop_duplicates()
    if distinct["id"].duplicated().any():
        raise ValueError("Conflicting records for a listing id; inspect them before deduplicating.")
    frame = distinct.copy()
    audit.append({"dataset": "vehicles", "step": "deduplicated_core_records", "rows": len(frame)})
    for column in ["price", "year", "odometer", "lat", "long"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.loc[coordinates_valid(frame, "lat", "long")].copy()
    audit.append({"dataset": "vehicles", "step": "valid_coordinates", "rows": len(frame)})
    for column in ["transmission", "manufacturer", "paint_color"]:
        frame[column] = frame[column].astype("string").str.strip().str.lower().replace("", pd.NA)
    dates = pd.to_datetime(frame["posting_date"], errors="coerce", utc=True)
    frame["posting_year"] = pd.to_numeric(frame["posting_date"].str[:4], errors="coerce").where(dates.notna())
    notes["posting_date_min_utc"] = None if dates.notna().sum() == 0 else dates.min().isoformat()
    notes["posting_date_max_utc"] = None if dates.notna().sum() == 0 else dates.max().isoformat()
    notes["posting_year_counts"] = {str(k): int(v) for k, v in frame["posting_year"].value_counts().items()}
    notes["missing_or_invalid_posting_date"] = int(dates.isna().sum())
    bad_price = frame["price"] <= 0
    bad_odometer = frame["odometer"] < 0
    bad_year = (frame["year"] < 1886) | (frame["year"] % 1 != 0) | (frame["year"] > frame["posting_year"])
    for column, mask in [("price", bad_price), ("odometer", bad_odometer), ("year", bad_year)]:
        notes[f"invalid_vehicle_{column}"] = int(mask.sum())
        frame.loc[mask, column] = np.nan
    frame["vehicle_age"] = frame["posting_year"] - frame["year"]
    audit.append({"dataset": "vehicles", "step": "invalid_attributes_set_missing_rows_retained", "rows": len(frame)})
    return frame.reset_index(drop=True)


def match_vehicles(colleges, vehicles, max_radius):
    if vehicles.empty:
        return pd.DataFrame(columns=["unitid", "id", "distance_miles"])
    tree = BallTree(np.radians(vehicles[["lat", "long"]].to_numpy(dtype=float)), metric="haversine")
    neighbors, distances = tree.query_radius(
        np.radians(colleges[["latitude", "longitude"]].to_numpy(dtype=float)),
        r=max_radius / EARTH_RADIUS_MILES, return_distance=True, sort_results=True,
    )
    records = []
    for unitid, indices, values in zip(colleges["unitid"], neighbors, distances):
        records.extend((unitid, vehicles.iloc[int(index)]["id"], float(value * EARTH_RADIUS_MILES))
                       for index, value in zip(indices, values))
    return pd.DataFrame(records, columns=["unitid", "id", "distance_miles"])


def summarize(colleges, vehicles, links, radius):
    links = links.loc[links["distance_miles"] <= radius].copy()
    nearby = links.merge(vehicles, on="id", how="left", validate="many_to_one")
    group = nearby.groupby("unitid")
    metrics = group.agg(
        n_listings=("id", "size"), n_known_color=("paint_color", "count"),
        n_known_brand=("manufacturer", "count"), n_known_price=("price", "count"),
        median_price=("price", "median"), median_vehicle_age=("vehicle_age", "median"),
        median_odometer=("odometer", "median"),
    )
    recognized = nearby["transmission"].isin(["manual", "automatic"])
    nearby["known_transmission"] = recognized.astype(int)
    nearby["manual"] = (nearby["transmission"] == "manual").fillna(False).astype(int)
    metrics["n_known_transmission"] = nearby.groupby("unitid")["known_transmission"].sum()
    metrics["n_manual"] = nearby.groupby("unitid")["manual"].sum()
    metrics["manual_share"] = metrics["n_manual"] / metrics["n_known_transmission"].replace(0, np.nan)
    for column, prefix, denominator in [
        ("paint_color", "color_share_", "n_known_color"),
        ("manufacturer", "brand_share_", "n_known_brand"),
    ]:
        counts = nearby.groupby(["unitid", column]).size().unstack(fill_value=0)
        shares = counts.div(metrics[denominator].replace(0, np.nan), axis=0).add_prefix(prefix)
        metrics = metrics.join(shares)
    result = colleges.merge(metrics.reset_index(), on="unitid", how="left", validate="one_to_one")
    count_columns = [column for column in result if column.startswith("n_")]
    result[count_columns] = result[count_columns].fillna(0).astype(int)
    for suffix in ["color", "brand", "price", "transmission"]:
        result[f"{suffix}_coverage"] = result[f"n_known_{suffix}"] / result["n_listings"].replace(0, np.nan)
    result["radius_miles"] = radius
    multiplicity = links.groupby("id")["unitid"].nunique()
    summary = {
        "radius_miles": radius, "college_count": len(colleges),
        "matched_colleges": int((result["n_listings"] > 0).sum()),
        "unmatched_colleges": int((result["n_listings"] == 0).sum()),
        "matched_unique_listings": len(multiplicity),
        "unmatched_clean_listings": len(vehicles) - len(multiplicity),
        "college_listing_pairs": len(links),
        "listings_near_multiple_colleges": int((multiplicity > 1).sum()),
    }
    return result, summary


def run(college_path, vehicle_path, output_dir, report_dir):
    colleges = pd.read_csv(college_path, dtype={"unitid": "string"})
    raw_college_column_count = len(colleges.columns)
    missing_columns = sorted(set(COLLEGE_COLUMNS) - set(colleges))
    if missing_columns:
        raise ValueError(f"Missing canonical college columns: {missing_columns}; see docs/data_plan.md")
    header = pd.read_csv(vehicle_path, nrows=0)
    missing_columns = sorted(set(VEHICLE_COLUMNS) - set(header))
    if missing_columns:
        raise ValueError(f"Vehicle version lacks required fields: {missing_columns}")
    vehicles = pd.read_csv(vehicle_path, usecols=VEHICLE_COLUMNS, dtype="string")
    missing = pd.concat([missingness(colleges, "colleges_raw"), missingness(vehicles, "vehicles_raw_selected_columns")])
    audit, notes = [], {}
    colleges = prepare_colleges(colleges, audit, notes)
    vehicles = prepare_vehicles(vehicles, audit, notes)
    links = match_vehicles(colleges, vehicles, 20)
    tables, summaries = [], []
    for radius in [5, 10, 20]:
        table, summary = summarize(colleges, vehicles, links, radius)
        tables.append((radius, table))
        summaries.append(summary)
        missing = pd.concat([missing, missingness(table, f"college_market_{radius}mi")])
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    colleges.to_csv(output_dir / "colleges_clean.csv", index=False)
    vehicles.to_csv(output_dir / "vehicles_clean.csv", index=False)
    links.to_csv(output_dir / "college_vehicle_links.csv", index=False)
    for radius, table in tables:
        table.to_csv(output_dir / f"college_market_{radius}mi.csv", index=False)
    pd.DataFrame(audit).to_csv(report_dir / "audit.csv", index=False)
    missing.to_csv(report_dir / "missingness.csv", index=False)
    pd.DataFrame(summaries).to_csv(report_dir / "matching_summary.csv", index=False)
    notes["inputs"] = [fingerprint(college_path), fingerprint(vehicle_path)]
    notes["enrollment_year"] = int(colleges["enrollment_year"].iloc[0])
    notes["generated_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    notes["raw_vehicle_column_count"] = len(header.columns)
    notes["raw_college_column_count"] = raw_college_column_count
    (report_dir / "run_metadata.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--colleges", type=Path, required=True)
    parser.add_argument("--vehicles", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--report-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    run(args.colleges, args.vehicles, args.output_dir, args.report_dir)
