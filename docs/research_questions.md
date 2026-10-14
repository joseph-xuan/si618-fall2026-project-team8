# Research questions — Working draft

This draft records the team's three research questions agreed on October 14, 2026, for the Research questions section of the final marimo notebook. The questions examine associations between used-car listing supply, student composition, and college density. They do not establish individual purchasing preferences or causal effects. Column names below are proposed names for the final analysis table; that table has not yet been generated.

## RQ1

**Question.** Do universities with higher international student shares have different brand compositions in nearby used-car listings?

**Columns.** `unitid`, `international_student_share`, `brand_share_<brand>`, `n_known_brand`, and `radius_miles`. Retain `manufacturer`, `price_usd`, and `listing_id` in the listing-level data for more detailed comparisons.

**Operational definition.** `international_student_share = EFNRALT / EFTOTLT`, using the all-students row in EF2019A for both counts. EFNRALT represents the IPEDS nonresident alien category and serves as a proxy for international students. Each university's share of a brand equals the number of eligible nearby listings for that brand divided by the number of eligible nearby listings with an identifiable brand. Report unknown-brand counts and brand identification coverage.

**What would answer it.** Compare nearby brand shares across universities with different international student shares and examine whether brand composition changes consistently with student composition. Brand composition charts grouped by international student share should also report the number of universities and listing coverage. Define any threshold for a "higher" share after describing the data. Comparisons within price ranges may supplement the main question.

**If the answer is no.** Brand shares show no consistent pattern as international student share changes, and brand compositions are broadly similar across groups. A difference at a single university is insufficient to establish a general pattern.

## RQ2

**Question.** Do universities with higher graduate student shares have different distributions of vehicle body styles and vehicle ages in nearby used-car listings?

**Columns.** `unitid`, `graduate_student_share`, `body_style_share_<category>`, `vehicle_age_median`, `vehicle_age_q25`, `vehicle_age_q75`, `n_known_body_style`, `n_known_vehicle_age`, and `radius_miles`. Retain `body_style`, `model_year`, `date_posted`, and `vehicle_age` in the listing-level data to examine the full distributions.

**Operational definition.** Graduate student share equals `EFTOTLT` from the EF2019A row where `EFALEVEL=12`, divided by `EFTOTLT` from the row where `EFALEVEL=1`. Vehicle type refers to `specifications.body_style`, such as sedan, SUV, or pickup, rather than make or model. Calculate vehicle age using the listing date and model year, rather than the current year. A model year one year after the listing year may represent a next-model-year vehicle and should be reviewed rather than automatically deleted. Handle missing graduate enrollment rows, unknown body styles, and invalid model years separately.

**What would answer it.** Compare both body-style composition and the center, spread, and tails of vehicle-age distributions across universities with different graduate student shares. Show the two outcomes separately; mean vehicle age alone does not describe the full distribution. Comparisons of vehicle age within the same body style may provide additional context.

**If the answer is no.** Body-style compositions are similar, vehicle-age distributions overlap substantially across graduate student share groups, and neither outcome shows a consistent pattern.

## RQ3

**Question.** Do areas with higher college density have a higher share of Japanese-brand vehicles in used-car listings?

**Columns.** `unitid`, `radius_miles`, `nearby_college_count`, `college_density_per_sq_mile`, `n_known_brand`, `n_japanese_brand`, and `japanese_brand_share`.

**Operational definition (proposed).** Define an area as the neighborhood within the same radius of each university, consistent with the nearby-market definition used in RQ1 and RQ2. `nearby_college_count` counts unique UNITIDs meeting the common institution selection criteria within that radius, including the focal university. Calculate `college_density_per_sq_mile = nearby_college_count / (pi * radius_miles**2)` using the nominal circular area. With a fixed radius, count and density differ only by a constant, so the main figure can use the more interpretable nearby college count. If states or counties with different areas are used instead, calculate density per unit area rather than comparing raw counts. Document the institution selection criteria, radius, and limitations of circular areas near coastlines or geographic boundaries during data manipulation.

This definition uses the existing HD2019 institution coordinates and vehicle coordinates and does not require a regional population denominator.

Classify Japanese brands using a fixed, documented brand list, including explicit rules for luxury sub-brands and discontinued brands. The classification refers to brand origin, not the country where a vehicle was manufactured. `japanese_brand_share` equals the number of deduplicated eligible Japanese-brand listings in the area divided by the number of deduplicated eligible listings with an identifiable brand. Report the unknown-brand share alongside this measure.

**What would answer it.** Japanese-brand share increases consistently with nearby college count or density. Use a scatter plot and comparisons across density groups, reporting brand identification coverage and listing sample sizes. An increasing pattern supports the question's directional expectation.

**If the answer is no.** Areas with higher college density do not consistently have higher Japanese-brand shares. Similar shares, no consistent trend, or a decreasing pattern would not support the expectation of a higher share.

**Aggregation caution.** Under the proposed campus-neighborhood definition, all three questions can use a unified analysis table with one row per university. Deduplicate listings within each area; do not sum the listing counts already assigned to nearby universities. Neighborhoods around different universities may overlap. Report shared listings and overlapping areas, and account for this overlap in later analysis rather than treating the markets as fully independent.

## Notebook workflow

1. **Title and group:** Suggested working title: "Student Composition, College Density, and Nearby Used-Car Markets in the United States." Add each member's name and uniqname.
2. **Overview:** Explain what linking university student composition and college locations to nearby listing supply makes possible.
3. **Research questions:** Present the three questions above, their columns, the patterns that would answer them, and what a negative answer would look like.
4. **Data sources:** Describe the downloaded IPEDS 2019 institution and enrollment data and winddude automotive listings. Determine institution scope, matching radius, and listing time window using the data description and coverage checks.
5. **Data description → Data manipulation → Data visualisation → Decision log:** Use observed coverage, distributions, and comparisons with reasonable alternatives to support the processing decisions.

At this stage, only the research directions have been established. Full-data cleaning, merging, and statistical testing have not been performed.
