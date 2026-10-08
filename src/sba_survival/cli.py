from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from .estimator import cumulative_incidence

NAICS_SECTORS = {
    "11": "Agriculture, Forestry, Fishing and Hunting",
    "21": "Mining, Quarrying, and Oil and Gas Extraction",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "32": "Manufacturing",
    "33": "Manufacturing",
    "42": "Wholesale Trade",
    "44": "Retail Trade",
    "45": "Retail Trade",
    "48": "Transportation and Warehousing",
    "49": "Transportation and Warehousing",
    "51": "Information",
    "52": "Finance and Insurance",
    "53": "Real Estate and Rental and Leasing",
    "54": "Professional, Scientific, and Technical Services",
    "55": "Management of Companies and Enterprises",
    "56": "Administrative and Support and Waste Management and Remediation Services",
    "61": "Educational Services",
    "62": "Health Care and Social Assistance",
    "71": "Arts, Entertainment, and Recreation",
    "72": "Accommodation and Food Services",
    "81": "Other Services (except Public Administration)",
    "92": "Public Administration",
}


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate SBA 7(a) charge-off and payoff incidence by NAICS sector.")
    parser.add_argument("--csv", required=True, type=Path, help="Official SBA FY2020-present FOIA CSV")
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--minimum-loans", type=int, default=100)
    args = parser.parse_args()
    if args.minimum_loans < 1:
        parser.error("--minimum-loans must be at least 1")
    groups: dict[tuple[str, str], list[tuple[float, int]]] = defaultdict(list)
    as_of_dates: set[str] = set()
    with args.csv.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"ApprovalDate", "ChargeOffDate", "PaidInFullDate", "AsOfDate", "ApprovalFY", "NaicsCode"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            parser.error(f"CSV must include fields: {', '.join(sorted(required))}")
        for row in reader:
            approved = parse_date(row.get("ApprovalDate", ""))
            cutoff = parse_date(row.get("AsOfDate", ""))
            sector = (row.get("NaicsCode") or "").strip()[:2]
            if not approved or not cutoff or len(sector) != 2 or not sector.isdigit():
                continue
            as_of_dates.add(cutoff.isoformat())
            approval_cohort = (row.get("ApprovalFY") or str(approved.year)).strip()
            charge = parse_date(row.get("ChargeOffDate", ""))
            paid = parse_date(row.get("PaidInFullDate", ""))
            events = [(d, code) for d, code in ((charge, 1), (paid, 2)) if d and approved <= d <= cutoff]
            if len(events) > 1:
                events.sort()
            event_date, code = events[0] if events else (cutoff, 0)
            if event_date < approved:
                continue
            years = (event_date - approved).days / 365.25
            # Only sector label and time/event code are retained; borrower PII is discarded.
            groups[(sector, approval_cohort)].append((years, code))
    horizons = (1.0, 3.0, 5.0)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "sector_cumulative_incidence.csv"
    fields = ["naics_2digit", "sector", "approval_fy", "loan_count", "chargeoff_cif_1y", "chargeoff_cif_3y", "chargeoff_cif_5y", "paid_in_full_cif_1y", "paid_in_full_cif_3y", "paid_in_full_cif_5y"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for (sector, approval_cohort), rows in sorted(groups.items()):
            if len(rows) < args.minimum_loans:
                continue
            estimate = cumulative_incidence([r[0] for r in rows], [r[1] for r in rows], horizons)
            label = NAICS_SECTORS.get(sector, f"NAICS sector {sector}")
            output = {"naics_2digit": sector, "sector": label, "approval_fy": approval_cohort, "loan_count": len(rows)}
            for horizon, suffix in zip(horizons, ("1y", "3y", "5y")):
                output[f"chargeoff_cif_{suffix}"] = estimate[horizon]["chargeoff_cif"]
                output[f"paid_in_full_cif_{suffix}"] = estimate[horizon]["paid_in_full_cif"]
            writer.writerow(output)
    manifest = {
        "source_dataset": "SBA 7(a) & 504 FOIA data",
        "source_url": "https://web.data.sba.gov/en/dataset/7-a-504-foia",
        "input_filename": args.csv.name,
        "rows_in_eligible_groups": sum(len(rows) for rows in groups.values()),
        "minimum_loans_per_sector_cohort": args.minimum_loans,
        "as_of_dates_in_input": sorted(as_of_dates),
        "outcome_definition": "earliest valid ChargeOffDate or PaidInFullDate; otherwise right-censored at AsOfDate",
        "privacy": "borrower names, addresses, and loan identifiers are not exported",
    }
    (args.out / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote sector-level results to {path}; input borrower identifiers were not exported.")
