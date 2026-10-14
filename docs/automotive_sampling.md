# Automotive preprocessing and sampling

## Purpose

Prepare a manageable input for the final marimo notebook from the winddude JSON array. The source JSON and original archives are retained. IPEDS institutions are not sampled.

Source: [winddude, 1.5 years Automotive Classified from 2019–2020](https://www.kaggle.com/datasets/winddude/15-years-automotive-classified-from-20192010), dataset version 1, downloaded on October 14, 2026. The publisher's displayed title contains "2019-2010"; the analysis year is determined from `date_posted`, not the title. The Kaggle API reports the license as "Other (specified in description)"; the detailed terms still need to be recorded before submission. Download and extraction metadata are beside the original local files.

The saved script is `scripts/sample_automotive.py`. It streams the whole JSON using ijson, so the full 49.53 GB file is never loaded into memory. Images, image links, descriptions, and other unrelated fields are omitted from the intermediate and sample.

## Eligibility and cleaning

1. Count all source records and country values.
2. Retain records explicitly identified as US listings.
3. Parse `date_posted`; retain listings posted in 2019, using the year in the original local timestamp. Count other years and invalid dates.
4. Require numeric finite coordinates in the legal latitude/longitude ranges; reject (0, 0). These are range checks, not a US boundary validation.
5. Require a valid HTTP(S) listing URL or, if unavailable, an original `_id`.
6. Flatten only the research fields. Missing brand, body style, price, or mileage does not remove a listing. Set nonpositive prices and negative mileage values to missing. No arbitrary high-price cutoff is applied.
7. Retain plausible model years from 1886 through 2020. For 2020 model-year vehicles posted in 2019, retain the year and a `next_model_year` flag, but leave vehicle age missing rather than producing a negative age. Other valid ages equal posting year minus model year.
8. Match brands conservatively at the beginning of the make/model text, optionally after a leading year, using documented aliases. Unknown or ambiguous brands remain missing; the raw make/model text is retained for review. The alias dictionary and Japanese-brand list are saved in the metadata. These classifications are provisional and need review before final analysis. Missing brand does not mean non-Japanese.
9. Preserve original body style and a mapped category. Preserve mileage as `mileage_raw`; its unit has not been verified and it is not used in the current research questions.

## Deduplication

Canonicalize a valid listing URL by normalizing the scheme and host and dropping query strings, fragments, and a trailing slash. Use its SHA256 as the listing key; fall back to a hash of `_id` only if no valid URL is available. Among eligible records sharing a key, retain the latest `date_last_crawled` version; use the posting timestamp if crawl date is invalid or missing. Naive crawl timestamps are treated as UTC for ordering. For exact time ties, the later record in file order wins.

This removes repeated captures of the same URL, not necessarily all reposts of the same physical vehicle. Listings with different URLs are retained. No VIN-based deduplication is claimed. SQLite stores the intermediate on disk, so the list of all unique eligible records need not fit in memory.

## Sampling

Use uniform reservoir sampling without replacement over unique eligible listings, in deterministic SQLite insertion order (the first eligible appearance of each listing key in the source). Default seed: `6182019`; target: 500,000 listings. If fewer eligible listings exist, retain all of them. With N unique eligible listings and sample size n, every listing has inclusion probability n/N. This is a national listing sample, not an equal-size sample per state or university.

The 500,000-row target is a starting size. Before using the sample for the research questions, check university-neighborhood coverage, effective known-brand/body-style/age counts, and overlap between neighborhoods. Low coverage may require a larger sample, which can be generated from the reusable SQLite intermediate. National sampling does not ensure adequate local coverage. Sample listing counts do not represent complete market inventory.

Run `python scripts/check_sample_coverage.py` after sampling to compute 5/10/20-mile coverage around a provisional set of active US four-year degree-granting institutions from HD2019. This saved script writes per-university counts and summary diagnostics under `outputs/`. Its 30/100-listing thresholds describe coverage only; they do not exclude institutions or declare the sample sufficient for statistical analysis. School density is computed from the full candidate institution set.

## Commands

```powershell
python -m pip install -r requirements.txt
python scripts/sample_automotive.py --sample-size 500000 --seed 6182019
```

To reuse a completed scan for a larger sample while retaining the first output:

```powershell
python scripts/sample_automotive.py --reuse-intermediate --sample-size 1000000 --seed 6182019 --output-dir data/processed/sample_1m --report-dir outputs/sample_1m
```

The script refuses to overwrite an existing sample or start a new scan over an existing intermediate. An interrupted scan is not marked complete and cannot be reused for sampling. To restart after an interrupted scan, choose a new `--database` path or explicitly manage the incomplete file. Source size and modification time must match the completed intermediate.

## Outputs

- `data/processed/automotive_us_2019.sqlite`: all unique eligible flattened listings, plus completed-scan metadata.
- `data/processed/vehicles_us_2019_sample.parquet`: the sampled notebook input, compressed with Zstandard.
- `outputs/automotive_processing_audit.csv`: rows surviving each eligibility, deduplication, and sampling step.
- `outputs/automotive_missingness.csv`: missingness in the unique eligible population and sample.
- `outputs/automotive_state_coverage.csv`: original versus sample shares by recorded state; missing state remains a separate category.
- `outputs/automotive_brand_coverage.csv`: original versus sample brand shares, including unknown brands.
- `outputs/automotive_sample_metadata.json`: parameters, counters, inclusion probability, classification dictionaries, package versions, timestamps, and hashes of the script and sample.

Attribute-cleaning diagnostics are counted before deduplication; final missingness is separately calculated after deduplication. Eligibility-stage losses and random subsampling are reported separately.

## Notebook integration

Load the sample with `pd.read_parquet(...)`, and show the audit and sampling metadata in Data description / Data manipulation. Include the preprocessing code or a transparent reference to the saved script and its reconstruction command. Distinguish the original source, eligible unique listing population, sampled input, and merged university table in the row counts. Provide the sample through a stable accessible data path or URL so the submitted notebook can run without the 49.53 GB source; embedding preprocessing code alone does not make an unavailable data file accessible.

The sample is a local intermediate, not a completed Milestone 1 submission. Brand review, geographic validation, university matching, local sample-size evaluation, final plots, and evidence-based decision log entries remain necessary.
