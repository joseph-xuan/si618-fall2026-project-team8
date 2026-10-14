# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marimo==0.23.16", "pandas==2.3.3", "numpy==2.4.6",
#   "matplotlib==3.11.2", "scikit-learn==1.9.1", "pyarrow==23.0.1",
#   "fsspec",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Student composition, college density, and nearby used-car markets in the United States

    **SI 618 · Milestone 1 · Team 8 · October 14, 2026**

    Yingjie Wang (**jennywyj**) · Shuxuan Liu (**shuxuan**) · Xiaoxuan Huang (**xixixuan**)

    This notebook uses a reproducible national sample of 500,000 listings. Milestone 1
    prepares and describes the merged data; statistical tests and models are left for later
    milestones.
    """)
    return


@app.cell
def _():
    import re

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from sklearn.neighbors import BallTree

    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 120})
    return BallTree, mo, np, pd, plt, re


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Overview

    We examine whether used-car listings near a university differ with its student
    composition or the number of colleges nearby. IPEDS provides 2019 university locations
    and enrollment counts. The automotive source provides 2019 listing locations, brands,
    body styles, and model years. Matching the sources by distance creates a university-level
    table that neither source could produce alone. The table describes nearby advertised
    supply, not completed sales or individual students' preferences, so the results show
    associations rather than causal effects.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Research questions

    **RQ1. Do universities with higher international student shares have different brand
    compositions in nearby used-car listings?**

    Columns: `unitid`, `international_student_share`, `brand_share_<brand>`,
    `n_known_brand`, `brand_identification_share`, and `radius_miles`. We compare average brand shares across ordered
    international-student-share groups. Similar compositions or no ordered pattern would
    support a no-association answer.

    **RQ2. Do universities with higher graduate student shares have different distributions
    of vehicle body styles and vehicle ages nearby?**

    Columns: `unitid`, `graduate_student_share`, `body_style_share_<category>`,
    `vehicle_age_q10`, `vehicle_age_q25`, `vehicle_age_median`, `vehicle_age_q75`,
    `vehicle_age_q90`,
    `n_known_body_style`, `n_known_vehicle_age`, and `radius_miles`. We compare both
    body-style composition and the center and spread of age. Similar shares and strongly
    overlapping age summaries would support a no-association answer.

    **RQ3. Do areas with higher college density have a higher share of Japanese-brand
    vehicles in used-car listings?**

    Columns: `unitid`, `nearby_college_count`, `college_density_per_sq_mile`,
    `japanese_brand_share`, `n_japanese_brand`, `n_known_brand`,
    `brand_identification_share`, and `radius_miles`.
    A consistent increase in Japanese-brand share as college density rises would support the
    question; a flat, decreasing, or irregular pattern would not. Brand origin does not mean
    the country where an individual vehicle was assembled.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Data sources

    | Dataset | Publisher and URL | Download date | License or terms | Role in merge |
    |---|---|---|---|---|
    | HD2019 institutional directory | NCES / U.S. Department of Education; [data ZIP](https://nces.ed.gov/ipeds/datacenter/data/HD2019.zip), [dictionary](https://nces.ed.gov/ipeds/datacenter/data/HD2019_Dict.zip) | 2026-10-14 | Federal public-use data; see the Department of Education [copyright notice](https://www.ed.gov/about/ed-overview/required-notices/website-policies/copyright-status-notice) | Institution identifiers and coordinates |
    | EF2019A Fall Enrollment, revised file | NCES; [data ZIP](https://nces.ed.gov/ipeds/datacenter/data/EF2019A.zip), [dictionary](https://nces.ed.gov/ipeds/datacenter/data/EF2019A_Dict.zip) | 2026-10-14 | Same federal public-use terms | Enrollment counts matched to HD2019 on `UNITID` |
    | *1.5 years Automotive Classified from 2019-2010*, version 1 | winddude; [Kaggle dataset](https://www.kaggle.com/datasets/winddude/15-years-automotive-classified-from-20192010) | 2026-10-14 | Kaggle lists “Other (specified in description)”; the publisher's [release post](https://www.reddit.com/r/datasets/comments/xfwrdf/) says “Use it how you wish” | Listing attributes and coordinates |

    HD2019 and EF2019A are merged on `UNITID`. The automotive data have no common identifier
    with IPEDS, so listing `latitude` and `longitude` are matched to campus `LATITUDE` and
    `LONGITUD` by great-circle distance. The main definition is a 10-mile radius. A listing
    may match more than one university; the matches are summarized to one row per university.

    The 49.53 GB nested automotive JSON is not loaded during grading. A documented script in
    the team's [public repository](https://github.com/joseph-xuan/si618-fall2026-project-team8)
    scans it, filters and deduplicates eligible 2019 U.S. listings, then draws a uniform sample
    without replacement using seed 6182019. This notebook loads that fixed sample and performs
    the visible field cleaning, geographic matching, merging, summaries, and figures below.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Data description

    The first table reports rows, columns, and the meaning of a row before and after merging.
    The tabs compute type, unit, and missingness for every variable used by the research
    questions. They are defined later because marimo resolves notebook dependencies rather
    than relying on top-to-bottom execution order.
    """)
    return


@app.cell
def _(data_shapes):
    data_shapes
    return


@app.cell
def _(variable_tables):
    (
        variable_tables["HD2019"],
        variable_tables["EF2019A"],
        variable_tables["Cleaned automotive sample"],
        variable_tables["Final merged table"],
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Data manipulation

    ### 1. Read the fixed source files from GitHub

    Each table is read directly from a raw URL in a pinned team-repository commit. The code
    does not create local data files or a cache. Using a fixed commit keeps the input version
    reproducible even if the repository's main branch changes later.
    """)
    return


@app.cell
def _(pd):
    commit = "45d2a7a36c9f5e870b9ad0814b4517fe4d586969"
    base_url = f"https://raw.githubusercontent.com/joseph-xuan/si618-fall2026-project-team8/{commit}/"

    sample_metadata = pd.read_json(
        base_url + "outputs/automotive_sample_metadata.json", typ="series")
    hd_raw = pd.read_csv(
        base_url + "data/raw/ipeds_2019/hd2019.csv",
        encoding="cp1252", low_memory=False)
    ef_raw = pd.read_csv(
        base_url + "data/raw/ipeds_2019/ef2019a_rv.csv",
        encoding="cp1252", low_memory=False)
    vehicles_raw = pd.read_parquet(
        base_url + "data/processed/vehicles_us_2019_sample.parquet")

    source_shapes = pd.DataFrame([
        ["HD2019", *hd_raw.shape],
        ["EF2019A revised", *ef_raw.shape],
        ["Automotive sample", *vehicles_raw.shape],
    ], columns=["dataset", "rows", "columns"])
    return base_url, ef_raw, hd_raw, sample_metadata, source_shapes, vehicles_raw


@app.cell
def _(source_shapes, vehicles_raw):
    source_shapes, vehicles_raw.head()
    return


@app.cell
def _(pd, sample_metadata):
    _stages = ["raw_records", "after_us_filter", "after_posting_year_filter",
               "after_valid_coordinates", "after_listing_identity", "after_deduplication"]
    upstream_audit = pd.DataFrame({
        "stage": _stages,
        "rows": [sample_metadata["audit"][stage] for stage in _stages],
    })
    upstream_audit["removed_since_previous"] = -upstream_audit["rows"].diff()
    upstream_audit.loc[len(upstream_audit)] = [
        "uniform random sample",
        sample_metadata["sample_rows"],
        sample_metadata["eligible_unique_listings"] - sample_metadata["sample_rows"],
    ]
    return (upstream_audit,)


@app.cell(hide_code=True)
def _(base_url, mo, sample_metadata):
    mo.md(f"""
    The [sampling script]({base_url}scripts/sample_automotive.py) records every upstream
    step. It drew {sample_metadata['sample_rows']:,} rows from
    {sample_metadata['eligible_unique_listings']:,} eligible unique listings, using seed `{sample_metadata['seed']}`.
    The following table is saved evidence from the full-file scan
    because rerunning a 49.53 GB extraction inside the submitted notebook is impractical.
    """)
    return


@app.cell
def _(upstream_audit):
    upstream_audit
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2. Clean institutions and enrollment, then merge on `UNITID`

    We strip text, keep U.S. four-year degree-granting institutions with usable coordinates,
    reshape three enrollment levels to one row per institution, and use a left merge so that
    unmatched institutions remain visible. A missing graduate count becomes zero only when
    the reported undergraduate count equals a positive total; other missing values stay missing.
    """)
    return


@app.cell
def _(ef_raw, hd_raw, np, pd):
    states = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()

    hd = hd_raw.rename(columns=lambda name: name.strip()).copy()
    hd = hd.assign(
        INSTNM=hd["INSTNM"].astype("string").str.strip(),
        STABBR=hd["STABBR"].astype("string").str.strip(),
        ACT=hd["ACT"].astype("string").str.strip(),
        LATITUDE=pd.to_numeric(hd["LATITUDE"], errors="coerce"),
        LONGITUD=pd.to_numeric(hd["LONGITUD"], errors="coerce"),
    )
    institution_steps = [["HD2019 loaded", len(hd)]]
    hd_us = hd[hd["STABBR"].isin(states)]
    institution_steps.append(["50 states and DC", len(hd_us)])
    hd_active = hd_us[hd_us["ACT"].isin(["A", "N", "R"])]
    institution_steps.append(["Active, new, or restored", len(hd_active)])
    hd_four_year = hd_active[(hd_active["ICLEVEL"] == 1) & (hd_active["DEGGRANT"] == 1)]
    institution_steps.append(["Four-year and degree-granting", len(hd_four_year)])
    hd_clean = hd_four_year[
        hd_four_year["LATITUDE"].between(-90, 90)
        & hd_four_year["LONGITUD"].between(-180, 180)
        & ~((hd_four_year["LATITUDE"] == 0) & (hd_four_year["LONGITUD"] == 0))
    ]
    institution_steps.append(["Usable coordinates", len(hd_clean)])
    institutions = hd_clean[["UNITID", "INSTNM", "STABBR", "LATITUDE", "LONGITUD"]].rename(
        columns={"UNITID": "unitid", "INSTNM": "institution_name", "STABBR": "state",
                 "LATITUDE": "campus_latitude", "LONGITUD": "campus_longitude"})

    ef = ef_raw.rename(columns=lambda name: name.strip()).copy()
    ef_levels = ef[ef["EFALEVEL"].isin([1, 2, 12])][
        ["UNITID", "EFALEVEL", "EFTOTLT", "EFNRALT"]
    ].copy()
    ef_levels["EFTOTLT"] = pd.to_numeric(ef_levels["EFTOTLT"], errors="coerce")
    ef_levels["EFNRALT"] = pd.to_numeric(ef_levels["EFNRALT"], errors="coerce")
    ef_levels.loc[ef_levels["EFTOTLT"] < 0, "EFTOTLT"] = np.nan
    ef_levels.loc[ef_levels["EFNRALT"] < 0, "EFNRALT"] = np.nan

    enrollment = ef_levels.pivot_table(
        index="UNITID", columns="EFALEVEL", values="EFTOTLT", aggfunc="first", dropna=False
    ).rename(columns={1: "total_students", 2: "undergraduate_students",
                      12: "graduate_students_reported"}).reset_index()
    international = ef_levels[ef_levels["EFALEVEL"] == 1][["UNITID", "EFNRALT"]].rename(
        columns={"EFNRALT": "international_students"})
    enrollment = pd.merge(enrollment, international, on="UNITID", how="left")
    enrollment = enrollment.rename(columns={"UNITID": "unitid"})
    enrollment = enrollment.assign(
        graduate_zero_inferred=(enrollment["graduate_students_reported"].isna()
            & enrollment["total_students"].gt(0)
            & enrollment["undergraduate_students"].eq(enrollment["total_students"]))
    )
    enrollment["graduate_students"] = np.where(
        enrollment["graduate_zero_inferred"], 0, enrollment["graduate_students_reported"])
    enrollment["international_student_share"] = (
        enrollment["international_students"] / enrollment["total_students"])
    enrollment["graduate_student_share"] = (
        enrollment["graduate_students"] / enrollment["total_students"])
    enrollment["graduate_share_reported_only"] = (
        enrollment["graduate_students_reported"] / enrollment["total_students"])
    for _column in ["international_student_share", "graduate_student_share",
                    "graduate_share_reported_only"]:
        enrollment.loc[~enrollment[_column].between(0, 1), _column] = np.nan

    campuses = pd.merge(institutions, enrollment, on="unitid", how="left", indicator=True)
    enrollment_audit = pd.DataFrame([
        ["EF2019A rows loaded", len(ef)],
        ["Keep EFALEVEL 1, 2, 12", len(ef_levels)],
        ["Reshape to one row per institution", len(enrollment)],
        ["Selected institutions matched to enrollment", int((campuses["_merge"] == "both").sum())],
        ["Selected institutions without enrollment (kept)", int((campuses["_merge"] == "left_only").sum())],
        ["Enrollment institutions outside the selection (not used)",
         int((~enrollment["unitid"].isin(institutions["unitid"])).sum())],
    ], columns=["stage", "rows"])
    campuses = campuses.drop(columns="_merge")
    institution_audit = pd.DataFrame(institution_steps, columns=["stage", "rows"])
    institution_audit["removed_since_previous"] = -institution_audit["rows"].diff()
    return campuses, ef_levels, enrollment, enrollment_audit, institution_audit, institutions


@app.cell
def _(campuses, enrollment_audit, institution_audit):
    institution_audit, enrollment_audit, campuses.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3. Clean the sampled vehicle listings

    We recheck country, posting year, coordinates, and listing identity. Brand text is
    standardized from the raw make/model field; body-style synonyms are combined with a
    documented mapping. Vehicle age is posting year minus model year. Unknown attributes stay
    missing so a listing can still contribute to the outcomes it does contain.
    """)
    return


@app.cell
def _(np, pd, re, sample_metadata, vehicles_raw):
    vehicles_check = vehicles_raw[vehicles_raw["country"] == "US"].copy()
    _date_text = vehicles_check["date_posted"].astype("string").str.replace(
        r"[+-]\d{2}:?\d{2}$|Z$", "", regex=True)
    vehicles_check["posting_year"] = pd.to_datetime(_date_text, errors="coerce").dt.year
    vehicles_check = vehicles_check[vehicles_check["posting_year"] == 2019]
    vehicles_check["latitude"] = pd.to_numeric(vehicles_check["latitude"], errors="coerce")
    vehicles_check["longitude"] = pd.to_numeric(vehicles_check["longitude"], errors="coerce")
    vehicles_check = vehicles_check[
        vehicles_check["latitude"].between(-90, 90)
        & vehicles_check["longitude"].between(-180, 180)
        & ~((vehicles_check["latitude"] == 0) & (vehicles_check["longitude"] == 0))
        & vehicles_check["listing_key"].notna()
        & vehicles_check["listing_key"].ne("")
    ].drop_duplicates("listing_key")

    brand_aliases = {brand: list(aliases)
                     for brand, aliases in sample_metadata["brand_aliases"].items()}
    brand_aliases.update({"hummer": ["hummer"], "freightliner": ["freightliner"],
                          "peterbilt": ["peterbilt"], "kenworth": ["kenworth"]})
    alias_to_brand = {alias: brand for brand, aliases in brand_aliases.items() for alias in aliases}
    brand_pattern = r"^(" + "|".join(
        re.escape(alias) for alias in sorted(alias_to_brand, key=len, reverse=True)) + r")\b"
    make_model = (vehicles_check["make_model_raw"].fillna("").str.lower()
                  .str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
                  .str.replace(r"^(?:19|20)\d{2}\s+", "", regex=True))
    manufacturer = make_model.str.extract(brand_pattern, expand=False).map(alias_to_brand)

    body_mapping = dict(sample_metadata["body_style_mapping"])
    body_mapping.update({"sport utility": "suv", "4d sport utility": "suv",
        "crew cab pickup": "pickup", "pickup truck": "pickup",
        "extended cab pickup": "pickup", "standard cab pickup": "pickup",
        "regular cab pickup": "pickup", "mini van passenger": "minivan",
        "full size cargo van": "van"})
    body_text = (vehicles_check["body_style_raw"].fillna("").str.lower()
                 .str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip())
    body_style = body_text.map(body_mapping)

    model_year = pd.to_numeric(vehicles_check["model_year"], errors="coerce")
    valid_year = model_year.between(1886, vehicles_check["posting_year"] + 1)
    model_year = model_year.where(valid_year)
    vehicle_age = vehicles_check["posting_year"] - model_year
    vehicle_age = vehicle_age.where(model_year <= vehicles_check["posting_year"])
    japanese_brands = set(sample_metadata["japanese_brand_list"])
    is_japanese = manufacturer.isin(japanese_brands).astype("boolean")
    is_japanese = is_japanese.mask(manufacturer.isna())

    vehicles = vehicles_check.assign(
        manufacturer=manufacturer,
        body_style=body_style,
        model_year=model_year,
        vehicle_age=vehicle_age,
        is_japanese_brand=is_japanese,
    ).reset_index(drop=True)

    vehicle_audit = pd.DataFrame([
        ["Sample loaded", len(vehicles_raw)],
        ["US, 2019, valid coordinates and identity", len(vehicles_check)],
        ["Unique listing keys after cleaning", vehicles["listing_key"].nunique()],
    ], columns=["stage", "rows"])
    vehicle_missing = (vehicles[["manufacturer", "body_style", "vehicle_age"]]
                       .isna().sum().rename("missing_rows").reset_index()
                       .rename(columns={"index": "variable"}))
    vehicle_missing["missing_percent"] = 100 * vehicle_missing["missing_rows"] / len(vehicles)
    return japanese_brands, vehicle_audit, vehicle_missing, vehicles


@app.cell
def _(vehicle_audit, vehicle_missing, vehicles):
    vehicle_audit, vehicle_missing, vehicles.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4. Match listings by distance and create one university-level table

    Ordinary `pd.merge()` cannot connect these sources because they share no key. `BallTree`
    with haversine distance finds listings within 5, 10, and 20 miles without comparing every
    school to all 500,000 listings. This is the only specialized step outside the course's
    pandas workflow. The returned listing rows are summarized with familiar pandas counts,
    `value_counts()`, and quantiles. The primary table uses 10 miles and keeps universities
    with no nearby sampled listing, recording zero counts and missing market shares.
    """)
    return


@app.cell
def _(BallTree, campuses, institutions, np, pd, vehicles):
    earth_miles = 3958.7613
    vehicle_points = np.radians(vehicles[["latitude", "longitude"]].to_numpy())
    campus_points = np.radians(campuses[["campus_latitude", "campus_longitude"]].to_numpy())
    institution_points = np.radians(institutions[["campus_latitude", "campus_longitude"]].to_numpy())
    vehicle_tree = BallTree(vehicle_points, metric="haversine")
    institution_tree = BallTree(institution_points, metric="haversine")
    neighbors_20, distances_20 = vehicle_tree.query_radius(
        campus_points, r=20 / earth_miles, return_distance=True, sort_results=True)

    brand_categories = sorted(vehicles["manufacturer"].dropna().unique())
    body_categories = sorted(vehicles["body_style"].dropna().unique())
    vehicle_fields = vehicles[["manufacturer", "body_style", "vehicle_age", "is_japanese_brand"]]
    summary_rows = []
    merge_rows = []

    for _radius in [5, 10, 20]:
        _college_counts = institution_tree.query_radius(
            campus_points, r=_radius / earth_miles, count_only=True)
        _listing_uses = np.zeros(len(vehicles), dtype=np.int32)
        for _position, (_indices, _distances) in enumerate(zip(neighbors_20, distances_20)):
            _nearby_indices = _indices[_distances <= _radius / earth_miles]
            _listing_uses[_nearby_indices] += 1
            _nearby = vehicle_fields.iloc[_nearby_indices]
            _known_brand = int(_nearby["manufacturer"].count())
            _known_body = int(_nearby["body_style"].count())
            _known_age = int(_nearby["vehicle_age"].count())
            _japanese_count = int(_nearby["is_japanese_brand"].sum())
            _complete = _nearby.dropna(subset=["manufacturer", "body_style", "vehicle_age"])

            _row = {
                "unitid": int(campuses.iloc[_position]["unitid"]),
                "radius_miles": _radius,
                "n_listings": len(_nearby_indices),
                "n_known_brand": _known_brand,
                "n_known_body_style": _known_body,
                "n_known_vehicle_age": _known_age,
                "n_japanese_brand": _japanese_count,
                "brand_identification_share": _known_brand / len(_nearby_indices) if len(_nearby_indices) else np.nan,
                "japanese_brand_share": _japanese_count / _known_brand if _known_brand else np.nan,
                "nearby_college_count": int(_college_counts[_position]),
                "college_density_per_sq_mile": _college_counts[_position] / (np.pi * _radius**2),
                "n_complete_case": len(_complete),
                "japanese_brand_share_complete_case": _complete["is_japanese_brand"].mean(),
            }
            _brand_counts = _nearby["manufacturer"].value_counts().reindex(brand_categories, fill_value=0)
            _body_counts = _nearby["body_style"].value_counts().reindex(body_categories, fill_value=0)
            for _brand in brand_categories:
                _row[f"brand_share_{_brand}"] = _brand_counts[_brand] / _known_brand if _known_brand else np.nan
            for _style in body_categories:
                _row[f"body_style_share_{_style}"] = _body_counts[_style] / _known_body if _known_body else np.nan
            _age_values = _nearby["vehicle_age"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).tolist()
            _row.update(dict(zip(["vehicle_age_q10", "vehicle_age_q25", "vehicle_age_median",
                                  "vehicle_age_q75", "vehicle_age_q90"], _age_values)))
            summary_rows.append(_row)

        merge_rows.append({
            "radius_miles": _radius,
            "universities": len(campuses),
            "universities_matched": int(sum(
                _record["n_listings"] > 0 for _record in summary_rows if _record["radius_miles"] == _radius)),
            "universities_unmatched": int(sum(
                _record["n_listings"] == 0 for _record in summary_rows if _record["radius_miles"] == _radius)),
            "unique_listings_matched": int((_listing_uses > 0).sum()),
            "listings_unmatched": int((_listing_uses == 0).sum()),
            "listings_shared_across_universities": int((_listing_uses > 1).sum()),
            "university_listing_pairs": int(_listing_uses.sum()),
        })

    market_summary = pd.DataFrame(summary_rows)
    radius_results = pd.merge(campuses, market_summary, on="unitid", how="left")
    analysis = radius_results[radius_results["radius_miles"] == 10].reset_index(drop=True)
    merge_audit = pd.DataFrame(merge_rows)
    return analysis, body_categories, brand_categories, merge_audit, radius_results


@app.cell
def _(analysis, merge_audit):
    merge_audit, analysis.head(10)
    return


@app.cell(hide_code=True)
def _(merge_audit, mo):
    _main = merge_audit[merge_audit["radius_miles"] == 10].iloc[0]
    mo.md(f"""
    At 10 miles, **{int(_main.universities_matched):,} universities match** at least one
    sampled listing and **{int(_main.universities_unmatched):,} do not**. Of the 500,000
    sampled listings, **{int(_main.unique_listings_matched):,}** match at least one university
    and **{int(_main.listings_unmatched):,}** do not. Because
    **{int(_main.listings_shared_across_universities):,} listings** match more than one
    university, university markets are not independent and their counts should not be added.
    """)
    return


@app.cell
def _(analysis, campuses, ef_raw, enrollment, hd_raw, institutions, pd, sample_metadata, vehicles, vehicles_raw):
    data_shapes = pd.DataFrame([
        ["HD2019 before cleaning", *hd_raw.shape, "one institution"],
        ["EF2019A before cleaning", *ef_raw.shape, "one institution × enrollment category"],
        ["Automotive original JSON", sample_metadata["audit"]["raw_records"], None, "one crawled listing record"],
        ["Automotive fixed sample", *vehicles_raw.shape, "one sampled listing"],
        ["Selected institutions before enrollment merge", *institutions.shape, "one institution"],
        ["Enrollment before merge", *enrollment.shape, "one institution"],
        ["Cleaned listings before geographic merge", *vehicles.shape, "one sampled listing"],
        ["Final merged table", *analysis.shape, "one university and its 10-mile market"],
    ], columns=["stage", "rows", "columns", "one_row_represents"])

    def describe(frame, definitions):
        return pd.DataFrame([{
            "variable": column,
            "dtype": str(frame[column].dtype),
            "unit_or_definition": definition,
            "missing_rows": int(frame[column].isna().sum()),
            "missing_percent": round(100 * frame[column].isna().mean(), 2),
        } for column, definition in definitions.items()])

    hd_definitions = {
        "UNITID": "institution identifier", "LATITUDE": "decimal degrees north",
        "LONGITUD": "decimal degrees east", "ICLEVEL": "institution-level code",
        "DEGGRANT": "degree-granting code",
    }
    ef_definitions = {
        "UNITID": "institution identifier", "EFALEVEL": "enrollment-level code",
        "EFTOTLT": "students", "EFNRALT": "nonresident alien students",
    }
    vehicle_definitions = {
        "listing_key": "listing identifier", "latitude": "decimal degrees north",
        "longitude": "decimal degrees east", "manufacturer": "normalized brand",
        "body_style": "normalized category", "vehicle_age": "years",
        "is_japanese_brand": "boolean brand-origin classification",
    }
    final_definitions = {
        "unitid": "institution identifier",
        "international_student_share": "nonresident alien students / all students",
        "graduate_student_share": "graduate students / all students",
        "n_known_brand": "sampled listings with a known brand",
        "n_known_body_style": "sampled listings with a known body style",
        "n_known_vehicle_age": "sampled listings with a known age",
        "n_japanese_brand": "known-brand sampled listings classified as Japanese",
        "brand_identification_share": "known-brand / all nearby sampled listings",
        "japanese_brand_share": "Japanese-brand / known-brand listings",
        "vehicle_age_q10": "years; within-market 10th percentile",
        "vehicle_age_q25": "years; within-market 25th percentile",
        "vehicle_age_median": "years; within-market median",
        "vehicle_age_q75": "years; within-market 75th percentile",
        "vehicle_age_q90": "years; within-market 90th percentile",
        "nearby_college_count": "selected institutions within radius, including focal",
        "college_density_per_sq_mile": "selected institutions per nominal square mile",
        "radius_miles": "great-circle miles",
    }
    for _column in analysis.columns:
        if _column.startswith("brand_share_"):
            final_definitions[_column] = "brand / known-brand listings; proportion"
        if _column.startswith("body_style_share_"):
            final_definitions[_column] = "body style / known-body-style listings; proportion"
    variable_tables = {
        "HD2019": describe(hd_raw, hd_definitions),
        "EF2019A": describe(ef_raw, ef_definitions),
        "Cleaned automotive sample": describe(vehicles, vehicle_definitions),
        "Final merged table": describe(analysis, final_definitions),
    }
    return data_shapes, variable_tables


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Data visualisation

    We use the classroom `pd.qcut()` method to form low-to-high groups. Each composition
    plot averages university-level shares, so large listing markets do not automatically
    receive more weight. A university must have at least 100 known listings for the plotted
    outcome. These figures are descriptive and do not contain statistical tests.
    """)
    return


@app.cell
def _(analysis, pd):
    def quartile_group(series):
        groups = pd.qcut(series, q=4, duplicates="drop")
        labels = [f"G{i + 1}" for i in range(len(groups.cat.categories))]
        return groups.cat.rename_categories(labels)

    plot_data = analysis.assign(
        international_group=quartile_group(analysis["international_student_share"]),
        graduate_group=quartile_group(analysis["graduate_student_share"]),
        density_group=quartile_group(analysis["nearby_college_count"]),
    )
    plot_coverage = pd.DataFrame([
        ["RQ1 brand", int((plot_data["n_known_brand"] >= 100).sum())],
        ["RQ2 body style", int((plot_data["n_known_body_style"] >= 100).sum())],
        ["RQ2 vehicle age", int((plot_data["n_known_vehicle_age"] >= 100).sum())],
        ["RQ3 Japanese-brand share", int((plot_data["n_known_brand"] >= 100).sum())],
    ], columns=["plot", "universities_with_100_known_listings"])
    return plot_coverage, plot_data


@app.cell
def _(plot_coverage):
    plot_coverage
    return


@app.cell
def _(brand_categories, plot_data, plt):
    rq1_data = plot_data[(plot_data["n_known_brand"] >= 100)
                         & plot_data["international_group"].notna()]
    _brand_columns = [f"brand_share_{brand}" for brand in brand_categories]
    _top_brands = rq1_data[_brand_columns].mean().nlargest(7).index
    brand_means = rq1_data.groupby("international_group", observed=True)[list(_top_brands)].mean()
    brand_means["Other known brands"] = 1 - brand_means.sum(axis=1)
    brand_means.columns = [name.removeprefix("brand_share_").title() for name in brand_means]
    _counts = rq1_data.groupby("international_group", observed=True).size()
    fig_brand, _ax = plt.subplots(figsize=(10.5, 5.5), layout="constrained")
    (100 * brand_means).plot.bar(stacked=True, ax=_ax, width=0.65)
    _ax.set_title("RQ1: Brand composition across international student shares")
    _ax.set_xlabel("International student share group, low to high")
    _ax.set_ylabel("Mean university brand share (%)")
    _ax.set_ylim(0, 100)
    _ax.set_xticklabels([f"{_group}\nn={_counts[_group]:,}" for _group in brand_means.index], rotation=0)
    _ax.legend(title="Brand", bbox_to_anchor=(1.01, 1), loc="upper left", frameon=False)
    fig_brand
    return brand_means, fig_brand, rq1_data


@app.cell(hide_code=True)
def _(brand_means, mo, rq1_data):
    _change = 100 * (brand_means.iloc[-1] - brand_means.iloc[0])
    _largest = _change.abs().idxmax()
    mo.md(f"""
    **Figure 1.** This comparison uses {len(rq1_data):,} universities. {_largest} has the
    largest low-to-high difference among the displayed categories: {_change[_largest]:+.1f}
    percentage points. The middle groups show whether that change is ordered. “Other” combines
    remaining known brands; unknown brands are excluded from each share denominator.
    """)
    return


@app.cell
def _(body_categories, plot_data, plt):
    rq2_body_data = plot_data[(plot_data["n_known_body_style"] >= 100)
                              & plot_data["graduate_group"].notna()]
    _body_columns = [f"body_style_share_{style}" for style in body_categories]
    _top_styles = rq2_body_data[_body_columns].mean().nlargest(6).index
    body_means = rq2_body_data.groupby("graduate_group", observed=True)[list(_top_styles)].mean()
    body_means["Other known styles"] = 1 - body_means.sum(axis=1)
    body_means.columns = [name.removeprefix("body_style_share_").title().replace("Suv", "SUV") for name in body_means]
    _counts = rq2_body_data.groupby("graduate_group", observed=True).size()
    fig_body, _ax = plt.subplots(figsize=(10.5, 5.5), layout="constrained")
    (100 * body_means).plot.bar(stacked=True, ax=_ax, width=0.65)
    _ax.set_title("RQ2: Body styles across graduate student shares")
    _ax.set_xlabel("Graduate student share group, low to high")
    _ax.set_ylabel("Mean university body-style share (%)")
    _ax.set_ylim(0, 100)
    _ax.set_xticklabels([f"{_group}\nn={_counts[_group]:,}" for _group in body_means.index], rotation=0)
    _ax.legend(title="Body style", bbox_to_anchor=(1.01, 1), loc="upper left", frameon=False)
    fig_body
    return body_means, fig_body, rq2_body_data


@app.cell(hide_code=True)
def _(body_means, mo, rq2_body_data):
    _change = 100 * (body_means.iloc[-1] - body_means.iloc[0])
    _largest = _change.abs().idxmax()
    mo.md(f"""
    **Figure 2.** This comparison uses {len(rq2_body_data):,} universities. {_largest} has the
    largest displayed low-to-high difference: {_change[_largest]:+.1f} percentage points.
    Shares use only listings with a known body style, so nonrandom missing body information
    remains a limitation.
    """)
    return


@app.cell
def _(plot_data, plt):
    rq2_age_data = plot_data[(plot_data["n_known_vehicle_age"] >= 100)
                             & plot_data["graduate_group"].notna()]
    _groups = list(rq2_age_data["graduate_group"].dropna().cat.categories)
    age_summary = rq2_age_data.groupby("graduate_group", observed=True)[
        ["vehicle_age_q10", "vehicle_age_q25", "vehicle_age_median",
         "vehicle_age_q75", "vehicle_age_q90"]
    ].mean()
    _counts = rq2_age_data.groupby("graduate_group", observed=True).size()
    fig_age, _ax = plt.subplots(figsize=(9, 5), layout="constrained")
    _ax.boxplot([
        rq2_age_data.loc[rq2_age_data["graduate_group"] == _group, "vehicle_age_median"]
        for _group in _groups
    ], tick_labels=[f"{_group}\nn={_counts[_group]:,}" for _group in _groups], patch_artist=True)
    _ax.set_title("RQ2: University market median age across graduate student shares")
    _ax.set_xlabel("Graduate student share group, low to high")
    _ax.set_ylabel("University-level median vehicle age (years)")
    fig_age
    return age_summary, fig_age, rq2_age_data


@app.cell(hide_code=True)
def _(age_summary, mo, rq2_age_data):
    mo.md(f"""
    **Figure 3.** The plot uses {len(rq2_age_data):,} universities. The average market
    median is **{age_summary.iloc[0]['vehicle_age_median']:.2f} years** in the lowest group
    and **{age_summary.iloc[-1]['vehicle_age_median']:.2f} years** in the highest. The boxplots
    show variation across universities; the following table adds typical within-market
    quantiles.
    """)
    return


@app.cell
def _(age_summary):
    age_summary
    return


@app.cell
def _(plot_data, plt):
    rq3_data = plot_data[(plot_data["n_known_brand"] >= 100)
                         & plot_data["japanese_brand_share"].notna()]
    density_summary = rq3_data.groupby("density_group", observed=True).agg(
        universities=("unitid", "size"),
        mean_japanese_share=("japanese_brand_share", "mean"),
        median_japanese_share=("japanese_brand_share", "median"),
        minimum_colleges=("nearby_college_count", "min"),
        maximum_colleges=("nearby_college_count", "max"),
    )
    fig_density, _ax = plt.subplots(figsize=(9, 5), layout="constrained")
    _ax.scatter(rq3_data["nearby_college_count"],
                100 * rq3_data["japanese_brand_share"], alpha=0.25, s=14)
    _ax.set_title("RQ3: College concentration and Japanese-brand listings")
    _ax.set_xlabel("Selected universities within 10 miles, including focal university")
    _ax.set_ylabel("Japanese-brand share of known brands (%)")
    _ax.set_ylim(0, 100)
    fig_density
    return density_summary, fig_density, rq3_data


@app.cell(hide_code=True)
def _(density_summary, mo, rq3_data):
    _ordered = density_summary["mean_japanese_share"].diff().dropna().gt(0).all()
    _pattern = "increase at every group transition" if _ordered else "do not increase at every group transition"
    mo.md(f"""
    **Figure 4.** The plot uses {len(rq3_data):,} university neighborhoods. Mean
    Japanese-brand share is **{density_summary.iloc[0]['mean_japanese_share']:.1%}** in the
    lowest density group and **{density_summary.iloc[-1]['mean_japanese_share']:.1%}** in the
    highest; the group means {_pattern}. Geography, urbanization, dealers, and overlapping
    circles may also explain this pattern, so the plot does not establish causation.
    """)
    return


@app.cell
def _(density_summary):
    density_summary
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Decision log

    Each entry gives the decision, a reasonable alternative, live evidence from this notebook,
    and the consequence. The alternatives below are actually calculated rather than only described.
    """)
    return


@app.cell
def _(analysis, campuses, merge_audit, pd, radius_results, vehicles):
    radius_evidence = radius_results.groupby("radius_miles").agg(
        universities_with_listings=("n_listings", lambda values: values.gt(0).sum()),
        median_listings=("n_listings", "median"),
        universities_with_100_brands=("n_known_brand", lambda values: values.ge(100).sum()),
    )
    _main = analysis.set_index("unitid")
    _radius_changes = []
    for _radius in [5, 20]:
        _alternative = radius_results[radius_results["radius_miles"] == _radius].set_index("unitid")
        _both = (_main["n_known_brand"] >= 100) & (_alternative["n_known_brand"] >= 100)
        _change = 100 * (_alternative.loc[_both, "japanese_brand_share"]
                         - _main.loc[_both, "japanese_brand_share"])
        _radius_changes.append([_radius, int(_both.sum()), _change.abs().median()])
    radius_change = pd.DataFrame(_radius_changes, columns=[
        "alternative_radius", "universities_passing_both_rules", "median_absolute_change_pp"])

    complete_rows = vehicles[["manufacturer", "body_style", "vehicle_age"]].notna().all(axis=1)
    common_market = (analysis["n_known_brand"] >= 100) & (analysis["n_complete_case"] >= 100)
    missing_evidence = pd.DataFrame([
        ["Outcome-specific availability", len(vehicles),
         int((analysis["n_known_brand"] >= 100).sum()),
         analysis.loc[common_market, "japanese_brand_share"].mean()],
        ["Complete brand + body + age", int(complete_rows.sum()),
         int((analysis["n_complete_case"] >= 100).sum()),
         analysis.loc[common_market, "japanese_brand_share_complete_case"].mean()],
    ], columns=["policy", "national_rows_retained", "universities_with_100_brands",
                "common_university_mean_japanese_share"])

    graduate_evidence = pd.DataFrame([
        ["Infer supported zeros", int(campuses["graduate_student_share"].notna().sum()),
         int((analysis["graduate_student_share"].notna()
              & (analysis["n_known_body_style"] >= 100)).sum())],
        ["Reported graduate counts only", int(campuses["graduate_share_reported_only"].notna().sum()),
         int((analysis["graduate_share_reported_only"].notna()
              & (analysis["n_known_body_style"] >= 100)).sum())],
    ], columns=["policy", "universities_with_known_share", "universities_eligible_for_body_plot"])

    _merge_10 = merge_audit[merge_audit["radius_miles"] == 10].iloc[0]
    decision_counts = {
        "radius_5": radius_evidence.loc[5], "radius_10": radius_evidence.loc[10],
        "radius_20": radius_evidence.loc[20], "merge_10": _merge_10,
        "inferred_zero": int(campuses["graduate_zero_inferred"].eq(True).sum()),
    }
    return decision_counts, graduate_evidence, missing_evidence, radius_change, radius_evidence


@app.cell(hide_code=True)
def _(decision_counts, mo, radius_change, radius_evidence):
    _d5 = radius_change[radius_change["alternative_radius"] == 5].iloc[0]
    _d20 = radius_change[radius_change["alternative_radius"] == 20].iloc[0]
    mo.md(f"""
    ### 1. Use a 10-mile university market

    **Decision.** Use 10 miles for the main vehicle summaries and college-density measure.

    **Alternative.** Run the same match at 5 and 20 miles.

    **Evidence.** The code actually runs all three radii. At least 100 known-brand listings
    are available for **{int(decision_counts['radius_5'].universities_with_100_brands):,}**,
    **{int(decision_counts['radius_10'].universities_with_100_brands):,}**, and
    **{int(decision_counts['radius_20'].universities_with_100_brands):,}** universities at
    5, 10, and 20 miles, respectively.

    **Consequence.** Among universities passing the threshold under both definitions,
    changing from 10 to 5 miles changes Japanese-brand share by a median absolute
    **{_d5.median_absolute_change_pp:.2f} percentage points**; changing to 20 miles changes it
    by **{_d20.median_absolute_change_pp:.2f} points**. Ten miles improves coverage over five
    without combining as wide a market as twenty.
    """)
    return


@app.cell
def _(radius_change, radius_evidence):
    radius_evidence, radius_change
    return


@app.cell(hide_code=True)
def _(missing_evidence, mo):
    _primary = missing_evidence.iloc[0]
    _alternative = missing_evidence.iloc[1]
    mo.md(f"""
    ### 2. Use each listing's available attributes

    **Decision.** Use a separate known-value denominator for brand, body style, and age.

    **Alternative.** Drop every listing missing any of those three attributes.

    **Evidence.** The executed complete-case alternative keeps
    **{int(_alternative.national_rows_retained):,} of {int(_primary.national_rows_retained):,}**
    listings.

    **Consequence.** It reduces universities with 100 usable brand observations from
    **{int(_primary.universities_with_100_brands):,}** to
    **{int(_alternative.universities_with_100_brands):,}**. For universities passing both
    rules, mean Japanese-brand share changes from
    **{_primary.common_university_mean_japanese_share:.2%}** to
    **{_alternative.common_university_mean_japanese_share:.2%}**. The chosen rule preserves
    valid information for one outcome when another field is missing.
    """)
    return


@app.cell
def _(missing_evidence):
    missing_evidence
    return


@app.cell(hide_code=True)
def _(decision_counts, graduate_evidence, mo):
    _primary = graduate_evidence.iloc[0]
    _alternative = graduate_evidence.iloc[1]
    mo.md(f"""
    ### 3. Infer a graduate count of zero only when counts support it

    **Decision.** Fill a missing graduate count with zero only when undergraduate count
    equals a positive total count; otherwise retain missingness.

    **Alternative.** Use only explicitly reported graduate counts.

    **Evidence.** The count identity supports zero for **{decision_counts['inferred_zero']:,}**
    universities. The executed alternative yields
    **{int(_alternative.universities_with_known_share):,}** known graduate shares, compared
    with **{int(_primary.universities_with_known_share):,}** under the chosen rule.

    **Consequence.** The body-style plot would include
    **{int(_alternative.universities_eligible_for_body_plot):,}** universities instead of
    **{int(_primary.universities_eligible_for_body_plot):,}**. This recovers justified zeros
    without treating every blank as zero.
    """)
    return


@app.cell
def _(graduate_evidence):
    graduate_evidence
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Limitations.** A geocoded point may represent a city center rather than an exact vehicle
    location. University circles can overlap, and circle area is not adjusted at coasts or
    borders. Missing brand and body-style values may not be random. The sample describes
    advertised supply during 2019, not sales, demand, or student purchases.

    **AI assistance disclosure.** The team used OpenAI Codex to help simplify the notebook,
    implement and check geographic matching, and verify execution. The team remains responsible
    for the research questions, decisions, interpretations, and submitted work.
    """)
    return


if __name__ == "__main__":
    app.run()
