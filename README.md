# SBA 7(a) competing-risk survival

This is a narrow, reproducible estimate of the cumulative incidence of SBA 7(a) charge-off and paid-in-full outcomes by NAICS sector and approval-fiscal-year cohort. It uses an Aalen–Johansen estimator so a paid-in-full loan is not incorrectly treated as ordinary independent censoring when estimating charge-off incidence.

## Skill demonstrated

- Nonparametric competing-risks survival estimation with right-censoring.
- Loan-record hygiene: the public source contains borrower-identifying fields; only approved dates, outcome dates, and NAICS sector labels enter the output.

## Run

Download the current 7(a) FY2020-present file from the [SBA 7(a) & 504 FOIA dataset](https://web.data.sba.gov/en/dataset/7-a-504-foia), then run:

```bash
pip install -e '.[test]'
sba-survival --csv /path/to/FOIA_7a.csv --out output --minimum-loans 100
```

The output is aggregated by two-digit NAICS sector and contains the number of observed loans plus estimated charge-off and paid-in-full cumulative incidence at 1, 3, and 5 years. The input file is never copied into the repository or output directory. The command fails if required outcome/date fields are missing.

## Interpretation

This estimates outcomes among SBA-approved loans in the selected cohorts. It is not an acquisition success rate, a business survival rate, or a causal estimate of industry quality. SBA programs, underwriting, and observation windows change over time; cohort composition and loan maturity matter. Borrower-level inputs are processed in memory and excluded from all outputs.

## Source

The SBA states the FOIA dataset provides loan-level 7(a) and 504 records and is updated quarterly. See the dataset's data dictionary for definitions of status and date fields. Public source file last refreshed by SBA at the time of download.

## Validation

```bash
pytest
```
