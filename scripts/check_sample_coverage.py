"""Describe sample coverage around candidate universities; do not filter them.

The candidate scope is US 50 states + DC, degree-granting institutions offering
four or more years, with ACT A/N/R. The scope and radius remain subject to team
review. No minimum sample-size threshold is applied to exclude universities.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[1]
EARTH_RADIUS_MILES = 3958.7613
US_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())


def counts(points, queries, radius):
    if not len(points):
        return np.zeros(len(queries), dtype=int)
    return BallTree(np.radians(points), metric="haversine").query_radius(
        np.radians(queries), r=radius / EARTH_RADIUS_MILES, count_only=True,
    )


def run(hd_path, sample_path, report_dir):
    hd = pd.read_csv(hd_path, encoding="cp1252", low_memory=False, dtype={"UNITID": "string"})
    hd.columns = hd.columns.str.strip()
    hd["ACT"] = hd["ACT"].str.strip()
    selected = hd.STABBR.isin(US_STATES) & hd.ICLEVEL.eq(1) & hd.DEGGRANT.eq(1) & hd.ACT.isin(["A", "N", "R"])
    universities = hd.loc[selected, ["UNITID", "INSTNM", "STABBR", "ACT", "LATITUDE", "LONGITUD"]].copy()
    valid = universities.LATITUDE.between(-90, 90) & universities.LONGITUD.between(-180, 180)
    universities = universities.loc[valid].copy()
    vehicles = pd.read_parquet(sample_path)
    queries = universities[["LATITUDE", "LONGITUD"]].to_numpy(dtype=float)
    points = vehicles[["latitude", "longitude"]].to_numpy(dtype=float)
    tables, summaries = [], []
    for radius in [5, 10, 20]:
        table = universities.rename(columns={"UNITID": "unitid", "INSTNM": "institution_name", "STABBR": "state_code"}).copy()
        table["radius_miles"] = radius
        table["n_sample_listings"] = counts(points, queries, radius)
        for column, output in [("manufacturer", "n_known_brand"), ("body_style", "n_known_body_style"), ("vehicle_age", "n_known_vehicle_age")]:
            table[output] = counts(points[vehicles[column].notna().to_numpy()], queries, radius)
        table["nearby_college_count"] = counts(queries, queries, radius)
        table["college_density_per_sq_mile"] = table["nearby_college_count"] / (np.pi * radius**2)
        tables.append(table)
        summaries.append({
            "radius_miles": radius, "candidate_universities": len(table),
            "universities_with_no_sample_listings": int(table.n_sample_listings.eq(0).sum()),
            "universities_with_30plus_sample_listings": int(table.n_sample_listings.ge(30).sum()),
            "universities_with_100plus_sample_listings": int(table.n_sample_listings.ge(100).sum()),
            "universities_with_30plus_known_brand": int(table.n_known_brand.ge(30).sum()),
            "universities_with_100plus_known_brand": int(table.n_known_brand.ge(100).sum()),
            "median_sample_listings_per_university": float(table.n_sample_listings.median()),
            "median_known_brand_per_university": float(table.n_known_brand.median()),
        })
    report_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(tables, ignore_index=True).to_csv(report_dir / "university_sample_coverage.csv", index=False)
    pd.DataFrame(summaries).to_csv(report_dir / "university_sample_coverage_summary.csv", index=False)
    metadata = {"scope": "US 50 states + DC; ICLEVEL=1; DEGGRANT=1; ACT stripped in A/N/R", "candidate_universities": len(universities),
                "sample": str(sample_path.resolve()), "radii_miles": [5, 10, 20],
                "notes": ["30/100 counts are coverage diagnostics, not adopted exclusion thresholds.",
                          "College density uses all candidate universities, not a sample of universities.",
                          "Candidate institution scope remains provisional.",
                          "Campus areas can overlap; summing counts does not produce unique national listings.",
                          "This is a coverage check, not a final IPEDS enrollment join."]}
    (report_dir / "university_sample_coverage_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hd", type=Path, default=ROOT / "data/raw/ipeds_2019/hd2019.csv")
    parser.add_argument("--sample", type=Path, default=ROOT / "data/processed/vehicles_us_2019_sample.parquet")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    run(args.hd, args.sample, args.report_dir)
