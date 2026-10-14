"""Adapt verified HD2021 + EF2021A to one row per institution.

Supports downloaded CSVs or official ZIPs; prefers EF's revised (_rv) CSV.
Retains US 50 states + DC institutions. Further institution-type selection
is a team decision: the output is not automatically limited to universities.
"""
import argparse
from pathlib import Path
import zipfile

import pandas as pd

US_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())


def read_ipeds(path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            revised = [name for name in files if name.lower().endswith("_rv.csv")]
            selected = revised or files
            if len(selected) != 1:
                raise ValueError(f"Ambiguous CSV selection in {path}: {selected}")
            with archive.open(selected[0]) as stream:
                frame = pd.read_csv(stream, encoding="cp1252", low_memory=False, dtype={"UNITID": "string"})
        member = selected[0]
    else:
        frame = pd.read_csv(path, encoding="cp1252", low_memory=False, dtype={"UNITID": "string"})
        member = path.name
    frame.columns = frame.columns.str.strip().str.upper()
    return frame, member


def prepare(hd_path, ef_path, output_path, report_path):
    hd, hd_member = read_ipeds(hd_path)
    ef, ef_member = read_ipeds(ef_path)
    if Path(hd_member).name.lower() != "hd2021.csv" or Path(ef_member).name.lower() not in {"ef2021a.csv", "ef2021a_rv.csv"}:
        raise ValueError("This adapter is verified only for HD2021 and EF2021A; preserve official filenames.")
    for table, required in [(hd, ["UNITID", "INSTNM", "STABBR", "LATITUDE", "LONGITUD"]),
                            (ef, ["UNITID", "EFALEVEL", "EFTOTLT", "EFTOTLW", "EFNRALT"])]:
        absent = set(required) - set(table)
        if absent:
            raise ValueError(f"Missing verified 2021 IPEDS fields: {sorted(absent)}")
    if hd["UNITID"].duplicated().any() or ef.duplicated(["UNITID", "EFALEVEL"]).any():
        raise ValueError("IPEDS keys are not unique; inspect the source before merging.")
    levels = pd.to_numeric(ef["EFALEVEL"], errors="raise")
    totals = ef.loc[levels == 1].copy()
    graduates = ef.loc[levels == 12, ["UNITID", "EFTOTLT"]].rename(columns={"EFTOTLT": "graduate_students"})
    audit = [{"step": "hd_raw", "rows": len(hd), "columns": len(hd.columns), "file_member": hd_member},
             {"step": "ef_raw", "rows": len(ef), "columns": len(ef.columns), "file_member": ef_member},
             {"step": "ef_all_students", "rows": len(totals)},
             {"step": "ef_graduates", "rows": len(graduates)}]
    hd = hd.loc[hd["STABBR"].isin(US_STATES)].copy()
    audit.append({"step": "hd_us50_dc", "rows": len(hd)})
    ids = hd[["UNITID"]].merge(totals[["UNITID"]], how="outer", on="UNITID", indicator=True, validate="one_to_one")
    for status in ["both", "left_only", "right_only"]:
        audit.append({"step": f"hd_ef_{status}", "rows": int((ids["_merge"] == status).sum())})
    keep_hd = ["UNITID", "INSTNM", "STABBR", "LATITUDE", "LONGITUD"] + [c for c in ["SECTOR", "ICLEVEL", "CONTROL", "DEGGRANT"] if c in hd]
    keep_ef = ["UNITID", "EFTOTLT", "EFTOTLW", "EFNRALT"] + [c for c in ["XEFTOTLT", "XEFTOTLW", "XEFNRALT"] if c in totals]
    result = hd[keep_hd].merge(totals[keep_ef], on="UNITID", how="left", validate="one_to_one")
    result = result.merge(graduates, on="UNITID", how="left", validate="one_to_one")
    result = result.rename(columns={"UNITID": "unitid", "INSTNM": "institution_name", "LATITUDE": "latitude",
                                    "LONGITUD": "longitude", "EFTOTLT": "total_students", "EFTOTLW": "female_students",
                                    "EFNRALT": "international_students"})
    result["enrollment_year"] = 2021
    audit.append({"step": "canonical_left_join", "rows": len(result), "columns": len(result.columns)})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    pd.DataFrame(audit).to_csv(report_path, index=False)
    print(f"Prepared {len(result):,} institutions; missing graduate rows remain missing.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hd", type=Path, required=True)
    parser.add_argument("--enrollment", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/raw/colleges.csv"))
    parser.add_argument("--report", type=Path, default=Path("outputs/ipeds_audit.csv"))
    args = parser.parse_args()
    prepare(args.hd, args.enrollment, args.output, args.report)
