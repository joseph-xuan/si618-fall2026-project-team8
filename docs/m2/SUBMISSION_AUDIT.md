# M2 submission audit — Team 8

Analysis and exported files verified on November 9, 2026. This is a completed analysis draft; the future Project Studio record and any unprovided Canvas feedback remain outstanding.

## Verified

- Exact required section order: Title and group → Response to feedback → Research questions → Question 1 → Question 2 → Question 3 → Summary of findings → Decision log.
- Each question has Approach, Result and Answer, with actual sample sizes, statistics, p-values, effect estimates, intervals and interpretation.
- Original and revised research questions, columns, area definitions and reasons for revision are present.
- Three genuine decision entries contain Decision, Alternative, Evidence and Consequence. All three alternatives are actually computed.
- Repeated M1 cleaning and live regional aggregation; fixed-source hashes verified.
- Geographic preprocessing independently regenerated: every assignment and county attribute matches the embedded lookup.
- 55 cells executed; 9 embedded figures; no cell errors or console warnings in the final standalone export.
- Summary of findings: 195 words, with one central estimate per question and a concrete final limitation.
- County, CBSA, pure-CBSA, identical-listing-support, threshold, single-state and county CBSA-cluster alternatives computed.
- 442 primary/alternative result rows have finite estimates, statistics, intervals and probabilities.
- Independent regression rerun maximum absolute coefficient difference: 8.2e-15.
- True standalone check: a new directory contained only the .py; the instructor's --sandbox export fetched the original inputs from fixed public URLs and succeeded.
- Final .py is marimo's normalized source from that successful export. Cell computation bodies are identical to the input source, and the HTML embeds the same final source.
- Tiny p-values use significant-digit formatting, preventing small nonzero values from appearing as zero.
- Relevant figures visually checked for legible titles, units, legends and non-clipped labels.
- M1 and original data preserved; no Canvas upload.

- Static result tables fully embed all 20 RQ1 rows, 30 RQ2 rows and 18 threshold rows; no first-page truncation.

- M1 format alignment: title first, horizontal section rules, matching plot typography, nine numbered captions, and separate decision-log entries. Main model estimates remain unchanged.

## Feedback and code-style checks

- Questions address distinct student-composition, body/age and university-density topics.
- Text categories retain the inspected M1 normalization; unknown categories remain missing instead of being silently combined.
- Missing-data, enrollment coverage, denominator, geography and subset decisions are explicit.
- Other-known brands in the descriptive plot preserve the full known-brand denominator, with the loss of brand detail stated by the label. Inferential results retain all ten declared brands.
- Assumption discussion includes measured residual skew, leverage, influence, sample counts and cluster counts.
- Non-overlap is not called proof of independent observations. HC3 and clustering limitations are explicit.
- No claims about actual student purchasing or causal effects.
- AI assistance is disclosed.

## Must be completed from real feedback before final submission

1. Add the full Canvas M1 comments if any beyond the supplied place discussion.
2. After the November 11 Project Studio, record which decisions were discussed, the group's explanations and any changes of view. Do not invent this before the meeting.

The notebook explicitly states both limitations in Response to feedback. Instructor meeting/feedback points cannot be guaranteed complete until these materials exist.

## Main files

- SI618_M2_Team8.py
- SI618_M2_Team8.html

## Fingerprints

- Notebook SHA256: `da5ae075a8c20193158d4247c1508ac4e5d0fc2fad8720e9d66578d2cce982bc`
- HTML SHA256: `42bc4a00b9dada6e3cd642378ede8f89ba2826d4b67823f4d676199387d979b2`
