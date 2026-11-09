# Milestone 2 research questions

These area-level revisions respond to place confounding and overlapping campus markets. They replace the unit of observation rather than selecting questions for more significant answers. The original M1 question document remains unchanged.

## RQ1

**Original.** Do universities with higher international student shares have different brand compositions in nearby used-car listings?

**Revised.** Do areas with higher international student shares across their universities have different brand compositions in local used-car listings?

**Columns.** `area_id`, `international_student_share`, `brand_*`, `n_known_brand`, `n_listings`, `population_density`, `college_density`, `total_students`, `state`.

## RQ2

**Original.** Do universities with higher graduate student shares have different distributions of vehicle body styles and vehicle ages nearby?

**Revised.** Do areas with higher graduate student shares across their universities have different distributions of body styles and vehicle ages in local used-car listings?

**Columns.** `area_id`, `graduate_student_share`, `body_*`, `age_q10`, `age_q25`, `age_median`, `age_q75`, `age_q90`, `age_iqr`, `n_known_body`, `n_known_age`, and the same controls as RQ1.

## RQ3

**Original.** Do areas with higher college density have a higher share of Japanese-brand vehicles in used-car listings? The M1 area was a 10-mile campus circle.

**Revised.** Do areas with higher university density have higher shares of Japanese-brand vehicles in local used-car listings?

**Columns.** `area_id`, `n_colleges`, `land_sqmi`, `college_density`, `japanese_share`, `n_known_brand`, `population`, `population_density`, `total_students`, `state`.

## Common design

- Primary unit: county. Comparison: counties pooled into September 2018 CBSAs, with non-CBSA counties retained separately. Pure CBSAs and identical listing support are additional checks.
- Student shares pool valid counts and their corresponding enrollment denominators; they do not average institution percentages.
- University density is selected institutions per land square mile. Population density is residents per the same land area.
- County/CBSA shares use distinct listing records assigned to exactly one region in each partition. Non-overlap is not evidence of independence.
- Methods: descriptive composition/distribution plots and multiple linear regression. Display unadjusted, state-adjusted, population-adjusted and full estimates on identical outcome-specific rows.
- Full controls: state, log2 population density, log total student enrollment; RQ1/RQ2 also include log2 university density.
- Main known-listing threshold: 100; alternatives: 50 and 200. Enrollment coverage requirements are 90%, explicitly chosen for this study.
- Inference: HC3 intervals plus county CBSA-cluster alternatives; BH within each question/specification/partition. These are exploratory associations, not causal estimates or student purchasing preferences.
- Income and GDP are not included in this version. Cross-state CBSA state controls are approximate and are checked by restricting to entirely single-state regions.
