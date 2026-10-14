# Automotive preprocessing results

Run completed on October 14, 2026. The original source and archives were retained. This report summarizes initial cleaning and sampling, not the final university analysis.

## Rows and sampling

| Stage | Rows retained |
|---|---:|
| Original JSON records | 20,131,746 |
| Explicitly US listings | 14,675,606 |
| Posted in 2019 | 8,904,012 |
| Valid coordinate ranges and nonzero coordinates | 8,799,791 |
| Valid listing identity | 8,799,791 |
| Unique URL/ID-based listing keys | 8,799,791 |
| Uniform random sample | 500,000 |

No duplicate eligible URL/ID keys were found under the documented rule. This does not establish that every record represents a different physical vehicle or eliminate reposts using different URLs.

The sample has 22 columns and occupies approximately 43.0 MiB as Zstandard-compressed Parquet. Reservoir sampling used seed `6182019`, without replacement, over the entire eligible unique listing population. Each eligible listing had an inclusion probability of approximately 5.682%. This is a random national listing sample; IPEDS universities were not sampled.

Maximum absolute sample-versus-population differences were approximately 0.077 percentage points for recorded state shares and 0.070 percentage points for brand shares, including unknown categories. These are descriptive checks, not a guarantee of representativeness for every university neighborhood.

## Missingness retained in the sample

| Field | Missing count | Missing share |
|---|---:|---:|
| Recorded state code | 9,543 | 1.9086% |
| Recognized manufacturer | 34,893 | 6.9786% |
| Mapped body style | 174,167 | 34.8334% |
| Vehicle age | 1,756 | 0.3512% |

Unknown brands remain missing, including the Japanese-brand indicator; they are not classified as non-Japanese. Raw make/model and body-style text is preserved for review. The brand and body-style dictionaries are provisional. For example, unknown brand strings include Hummer and some commercial-truck brands, while some body styles use alternative labels such as "Sport Utility" and "Crew Cab Pickup". Review these mappings before treating them as final categories.

Of the 174,167 missing mapped body styles, 169,028 have no raw body-style value and 5,139 contain an unmapped label. Most of this missingness therefore originates in the source, rather than the mapping dictionary. At 10 miles, 2,022 candidate institutions have at least 100 known-body-style listings; 2,163 have at least 100 known-age listings.

There were 27,142 eligible pre-deduplication records with next-model-year vehicles and 44 with invalid model years. Next-model-year records retain their model year and an explicit flag but have missing vehicle age. This treatment should be evaluated in the notebook's decision log.

## Initial university-neighborhood coverage

The provisional scope contains 2,781 US four-year degree-granting institutions with active/new/restored status. No minimum listing count was used to remove institutions.

| Radius | Universities with no sampled listings | Universities with at least 100 known-brand listings | Median sampled listings per university |
|---|---:|---:|---:|
| 5 miles | 38 | 1,800 | 218 |
| 10 miles | 18 | 2,140 | 592 |
| 20 miles | 7 | 2,400 | 1,368 |

At 10 miles, 2,431 institutions have at least 30 known-brand listings. The 30/100 thresholds are coverage diagnostics, not adopted exclusions or statistical sufficiency criteria. Neighborhoods overlap, so these university counts do not describe independent markets. College density was computed from the full candidate institution set.

## Saved files

- `scripts/sample_automotive.py`: complete streaming, filtering, cleaning, deduplication, sampling, and audit code.
- `scripts/check_sample_coverage.py`: provisional university coverage and density checks.
- `docs/automotive_sampling.md`: processing rules, limitations, commands, and notebook integration.
- `data/processed/vehicles_us_2019_sample.parquet`: sampled notebook input.
- `data/processed/automotive_us_2019.sqlite`: reusable complete eligible-listing intermediate.
- `outputs/automotive_*.csv` and `outputs/automotive_sample_metadata.json`: stage counts, missingness, state/brand comparisons, parameters, and checksums.
- `outputs/university_sample_coverage*.csv` and its metadata JSON: coverage by institution and radius.

## Verification and remaining work

Constructed-input tests passed for eligibility filters, latest-version deduplication, deterministic sampling, retention of missing attributes, and next-model-year handling. The saved sample was checked for its shape, unique keys, eligibility, legal coordinate ranges, nullable Japanese-brand classification, absence of image/description fields, and agreement with the saved script hash.

Next steps are to review classification mappings, validate geography beyond coordinate ranges, prepare and merge IPEDS 2019 enrollment, evaluate coverage by the final school scope, and build the marimo notebook. The sampled data must be made accessible to the grader through a suitable submitted data path or stable URL. The current local sample and preprocessing script alone are not a complete Milestone 1 submission.
