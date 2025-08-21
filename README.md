
Overview

This utility merges multiple 340B spreadsheet exports into a single, cleaned dataset. It pulls all .xlsx files in input/, normalizes headers, filters to the IDs you care about, removes expired contracts, deduplicates by ID, and writes results into a month-named folder under output/ (e.g., output/2025-08/).

Example: An entry like PED453310-00 with Contract Term Date = 2020-11-13 is excluded because it’s expired (per rules below).

Rules (Filter & Dedup Logic)

Header detection

Auto-detect the header row by searching for “340B ID”; fallback to row 4 if not found.

Prefixes of interest

Keep only IDs whose root starts with DSH or PED (e.g., DSH30062, PED453310).

Active contracts only (default)

Keep rows where Contract Term Date is blank (treated as active) or ≥ today.

Deduplication

Deduplicate by RootID (e.g., DSH30062 or PED453310), ignoring pharmacy/location differences.

By default, keep the row with the latest BeginDate; option to keep first.

Column set

Default output includes: RootID, ID, EntityName, PharmacyName, BeginDate, TermDate plus any pass-through columns from the input if present.

You can switch to keep all original columns (see Options).

Folder Structure
340B-Merger/
├── input/                  # Drop raw spreadsheets here (.xlsx)
│   ├── file1.xlsx
│   ├── file2.xlsx
│   └── ...
├── output/
│   └── YYYY-MM/            # Auto-created per run (e.g., 2025-08)
│       ├── cleaned_340B_list.xlsx
│       ├── merge_summary.csv
│       ├── diff_only_in_provided.csv   (optional; only when validating)
│       └── diff_only_in_ours.csv       (optional; only when validating)
├── merge_340b.py
├── requirements.txt
└── README.md

Requirements

requirements.txt:

pandas>=2.2.0
openpyxl>=3.1.0

Setup (venv + install)

Windows (PowerShell/CMD):

cd C:\path\to\340B-Merger
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt


macOS / Linux:

cd /path/to/340B-Merger
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt


How to Run
Basic run (recommended)

Windows (one line):

python merge_340b.py --input-dir ./input --output ./output/cleaned_340B_list.xlsx


./run_merge.sh


--keep-all-columns
--prefixes DSH
