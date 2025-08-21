#!/usr/bin/env python3
"""
merge_340b.py

Merge multiple 340B spreadsheets, filter to active DSH/PED IDs, and deduplicate by root ID.
- Reads all .xlsx files in an input folder (first sheet of each)
- Auto-detects header row by finding the row containing "340B ID"
- Normalizes columns
- Filters:
    * Keep only 340B IDs starting with DSH or PED
    * Drop rows with Contract Term Date earlier than today (NaT is treated as active)
- Deduplicates by root ID (e.g., r'^(DSH|PED)\\d+'), keeping the row with the latest BeginDate (or first if none)
- Writes a single Excel output

Usage:
    python merge_340b.py --input-dir /path/to/folder --output /path/to/cleaned_340B_list.xlsx
Options:
    --prefixes DSH PED        # override which ID prefixes to keep
    --dedupe latest-begin     # or 'first' (default: latest-begin)
    --today YYYY-MM-DD        # override "today" for reproducible runs
"""

import argparse
import os
import re
from datetime import datetime, date
import pandas as pd


# --- Configuration helpers ----------------------------------------------------

POSSIBLE_COLS = {
    "id": ["340B ID", "340BID", "ID"],
    "entity": ["Entity Name", "Covered Entity Name", "Covered Entity", "Entity"],
    "pharmacy": ["Pharmacy Name", "Pharmacy", "Doing Business As", "DBA"],
    "begin": ["Contract Begin Date", "Begin Date", "Contract Start Date", "Start Date"],
    "term": ["Contract Term Date", "Termination Date", "Contract End Date", "End Date", "Term Date"],
    # add more if needed:
    "city": ["City"],
    "state": ["State"],
    "zip": ["Zip", "ZIP", "Zip Code", "Postal Code"],
}

ROOT_ID_REGEX = re.compile(r"^(DSH|PED)\d+", re.IGNORECASE)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def best_match_column(existing_cols, candidates):
    """Return the first column name from existing_cols that matches any candidate (case-insensitive)."""
    norm_map = {normalize(c): c for c in existing_cols}
    for cand in candidates:
        key = normalize(cand)
        if key in norm_map:
            return norm_map[key]
    # Try substring contains if exact not found (last resort)
    for col in existing_cols:
        if any(normalize(cand) in normalize(col) for cand in candidates):
            return col
    return None


def find_header_row(df_like):
    """
    Given a DataFrame read with header=None, find the row index that contains '340B ID'
    (case-insensitive) and return that row index to use as header.
    """
    for i in range(min(15, len(df_like))):  # search first 15 rows just in case
        row_vals = [str(x) for x in df_like.iloc[i].tolist()]
        if any(normalize(v) == "340b id" for v in row_vals):
            return i
    return None


def read_with_auto_header(path):
    """Read first sheet, detect header row, then re-read with that row as header."""
    # Read a small preview with no header to detect
    preview = pd.read_excel(path, header=None, nrows=20)
    hdr_idx = find_header_row(preview)
    if hdr_idx is None:
        # fallback: many exports have the header at row 3 (0-based index)
        hdr_idx = 3
    df = pd.read_excel(path, header=hdr_idx)
    # Drop completely empty columns
    df = df.dropna(axis=1, how="all")
    # Drop completely empty rows
    df = df.dropna(axis=0, how="all")
    return df


def extract_root_id(id_val: str):
    if not isinstance(id_val, str):
        id_val = str(id_val) if pd.notna(id_val) else ""
    m = ROOT_ID_REGEX.match(id_val.strip())
    if m:
        # Normalize to upper-case consistent root key
        return m.group(0).upper()
    return None


def coerce_datetime(series):
    return pd.to_datetime(series, errors="coerce").dt.tz_localize(None)


# --- Main processing ----------------------------------------------------------

# def process_folder(input_dir, prefixes=("DSH", "PED"), dedupe_strategy="latest-begin", today_override=None):
#     files = [os.path.join(input_dir, f)
#              for f in os.listdir(input_dir)
#              if f.lower().endswith(".xlsx") and not f.startswith("~$")]

#     if not files:
#         raise SystemExit(f"No .xlsx files found in: {input_dir}")

#     frames = []
#     for f in files:
#         try:
#             df = read_with_auto_header(f)
#         except Exception as e:
#             print(f"[WARN] Failed to read {f}: {e}")
#             continue

#         # Build a normalized view with the columns we care about
#         cols = list(df.columns)
#         col_id = best_match_column(cols, POSSIBLE_COLS["id"])
#         col_begin = best_match_column(cols, POSSIBLE_COLS["begin"])
#         col_term = best_match_column(cols, POSSIBLE_COLS["term"])
#         col_entity = best_match_column(cols, POSSIBLE_COLS["entity"])
#         col_pharm = best_match_column(cols, POSSIBLE_COLS["pharmacy"])

#         # If mandatory columns missing, skip file
#         if not col_id or not col_begin or not col_term:
#             print(f"[WARN] Missing key columns in {os.path.basename(f)}; found -> "
#                   f"ID:{col_id}, Begin:{col_begin}, Term:{col_term}. Skipping.")
#             continue

#         slim = df[[c for c in [col_id, col_begin, col_term, col_entity, col_pharm] if c in df.columns]].copy()
#         slim.rename(columns={
#             col_id: "ID",
#             col_begin: "BeginDate",
#             col_term: "TermDate",
#             (col_entity or "Entity Name"): "EntityName",
#             (col_pharm or "Pharmacy Name"): "PharmacyName",
#         }, inplace=True)

#         frames.append(slim)

#     if not frames:
#         raise SystemExit("No usable data frames were produced from the input files.")

#     merged = pd.concat(frames, ignore_index=True)

#     # Normalize dates
#     if "BeginDate" in merged:
#         merged["BeginDate"] = coerce_datetime(merged["BeginDate"])
#     if "TermDate" in merged:
#         merged["TermDate"] = coerce_datetime(merged["TermDate"])

#     # Filter by prefixes (DSH/PED) using the root extraction
#     prefixes = tuple(p.upper() for p in prefixes)
#     merged["RootID"] = merged["ID"].astype(str).str.upper().str.strip().apply(extract_root_id)

#     # Keep only rows with desired prefixes AND a valid root pattern
#     keep_mask = merged["RootID"].notna() & merged["RootID"].str.startswith(prefixes)
#     merged = merged[keep_mask].copy()

#     # Compute "today"
#     if today_override:
#         today = pd.to_datetime(today_override).normalize()
#     else:
#         today = pd.Timestamp(date.today())

#     # Active filter: keep if TermDate is NaT (blank) OR TermDate >= today
#     merged = merged[(merged["TermDate"].isna()) | (merged["TermDate"] >= today)].copy()

#     # Deduplicate by RootID
#     if dedupe_strategy == "latest-begin" and "BeginDate" in merged:
#         # Keep the row with the latest BeginDate per RootID
#         merged.sort_values(by=["RootID", "BeginDate"], ascending=[True, False], inplace=True)
#         deduped = merged.drop_duplicates(subset=["RootID"], keep="first").copy()
#     else:
#         # Simple: keep first occurrence
#         deduped = merged.drop_duplicates(subset=["RootID"], keep="first").copy()

#     # Order columns nicely
#     preferred_order = ["RootID", "ID", "EntityName", "PharmacyName", "BeginDate", "TermDate"]
#     other_cols = [c for c in deduped.columns if c not in preferred_order]
#     output_df = deduped[preferred_order + other_cols]

#     # Sort for readability
#     output_df = output_df.sort_values(by=["RootID"]).reset_index(drop=True)

#     return output_df


def process_folder(input_dir, prefixes=("DSH", "PED"), dedupe_strategy="latest-begin",
                   today_override=None, keep_all_columns=False):
    files = [os.path.join(input_dir, f)
             for f in os.listdir(input_dir)
             if f.lower().endswith(".xlsx") and not f.startswith("~$")]

    if not files:
        raise SystemExit(f"No .xlsx files found in: {input_dir}")

    frames = []
    for f in files:
        try:
            df = read_with_auto_header(f)
        except Exception as e:
            print(f"[WARN] Failed to read {f}: {e}")
            continue

        # Keep ALL original columns; just *add* standardized aliases.
        cols = list(df.columns)
        col_id     = best_match_column(cols, POSSIBLE_COLS["id"])
        col_begin  = best_match_column(cols, POSSIBLE_COLS["begin"])
        col_term   = best_match_column(cols, POSSIBLE_COLS["term"])
        col_entity = best_match_column(cols, POSSIBLE_COLS["entity"])
        col_pharm  = best_match_column(cols, POSSIBLE_COLS["pharmacy"])

        # Mandatory for logic
        if not col_id or not col_begin or not col_term:
            print(f"[WARN] Missing key columns in {os.path.basename(f)}; "
                  f"found -> ID:{col_id}, Begin:{col_begin}, Term:{col_term}. Skipping.")
            continue

        df = df.copy()

        # Add alias columns without dropping originals
        df["ID"]          = df[col_id]
        df["BeginDate"]   = df[col_begin]
        df["TermDate"]    = df[col_term]
        if col_entity: df["EntityName"]   = df[col_entity]
        if col_pharm:  df["PharmacyName"] = df[col_pharm]

        df["source_file"] = os.path.basename(f)

        frames.append(df)

    if not frames:
        raise SystemExit("No usable data frames were produced from the input files.")

    merged = pd.concat(frames, ignore_index=True)

    # Normalize dates on the alias columns
    merged["BeginDate"] = coerce_datetime(merged["BeginDate"])
    merged["TermDate"]  = coerce_datetime(merged["TermDate"])

    # Extract RootID and filter by prefixes
    prefixes = tuple(p.upper() for p in prefixes)
    merged["RootID"] = merged["ID"].astype(str).str.upper().str.strip().apply(extract_root_id)
    keep_mask = merged["RootID"].notna() & merged["RootID"].str.startswith(prefixes)
    merged = merged[keep_mask].copy()

    # Active filter: TermDate blank or >= today
    if today_override:
        today = pd.to_datetime(today_override).normalize()
    else:
        today = pd.Timestamp(date.today())
    merged = merged[(merged["TermDate"].isna()) | (merged["TermDate"] >= today)].copy()

    # Deduplicate by RootID
    if dedupe_strategy == "latest-begin":
        merged.sort_values(by=["RootID", "BeginDate"], ascending=[True, False], inplace=True)
    # Get the indices of the rows we keep
    deduped = merged.drop_duplicates(subset=["RootID"], keep="first").copy()

    # If keeping all columns, return every column present in deduped
    if keep_all_columns:
        # Reorder to show the key fields first, then everything else
        key_first = ["RootID", "ID", "EntityName", "PharmacyName", "BeginDate", "TermDate"]
        key_first = [c for c in key_first if c in deduped.columns]
        rest = [c for c in deduped.columns if c not in key_first]
        out = deduped[key_first + rest].reset_index(drop=True)
        return out
    else:
        # Slim version ONLY
        slim_cols = ["RootID", "ID", "EntityName", "PharmacyName", "BeginDate", "TermDate"]
        slim_cols = [c for c in slim_cols if c in deduped.columns]
        out = deduped[slim_cols].reset_index(drop=True)
        return out
    
    # Slim output
    preferred_order = ["RootID", "ID", "EntityName", "PharmacyName", "BeginDate", "TermDate"]
    other_cols = [c for c in deduped.columns if c not in preferred_order]
    out = deduped[[c for c in preferred_order if c in deduped.columns] + other_cols].reset_index(drop=True)
    return out



# def main():
#     ap = argparse.ArgumentParser(description="Merge and clean 340B spreadsheets (DSH/PED, active only, dedup by RootID).")
#     ap.add_argument("--input-dir", required=True, help="Folder containing .xlsx source files")
#     ap.add_argument("--output", required=True, help="Path to write cleaned Excel file")
#     ap.add_argument("--prefixes", nargs="+", default=["DSH", "PED"], help="ID prefixes to keep (default: DSH PED)")
#     ap.add_argument("--dedupe", choices=["first", "latest-begin"], default="latest-begin",
#                     help="Dedup strategy by RootID (default: latest-begin)")
#     ap.add_argument("--today", default=None, help="Override 'today' (YYYY-MM-DD) for testing")
#     ap.add_argument("--keep-all-columns", action="store_true",
#                     help="Keep all original columns instead of slimming to core fields")

#     args = ap.parse_args()

#     clean = process_folder(
#         input_dir=args.input_dir,
#         prefixes=tuple(args.prefixes),
#         dedupe_strategy=args.dedupe,
#         today_override=args.today,
#     )

#     # If not keeping all columns, select the preferred slim set
#     if not args.keep_all_columns:
#         preferred_order = ["RootID", "ID", "EntityName", "PharmacyName", "BeginDate", "TermDate"]
#         other_cols = [c for c in clean.columns if c not in preferred_order]
#         clean = clean[[c for c in preferred_order if c in clean.columns] + other_cols]

#     # Timestamped output folder
#     run_month = datetime.today().strftime("%Y-%m")
#     output_dir = os.path.join(os.path.dirname(args.output), run_month)
#     os.makedirs(output_dir, exist_ok=True)

#     out_path = os.path.join(output_dir, os.path.basename(args.output))
#     clean.to_excel(out_path, index=False)

#     print(f"[OK] Wrote cleaned file -> {out_path}")
#     print(f"[INFO] Rows: {len(clean)} | Columns: {len(clean.columns)}")
def main():
    ap = argparse.ArgumentParser(description="Merge and clean 340B spreadsheets (DSH/PED, active only, dedup by RootID).")
    ap.add_argument("--input-dir", required=True, help="Folder containing .xlsx source files")
    ap.add_argument("--output", required=True, help="Path to write cleaned Excel file")
    ap.add_argument("--prefixes", nargs="+", default=["DSH", "PED"], help="ID prefixes to keep (default: DSH PED)")
    ap.add_argument("--dedupe", choices=["first", "latest-begin"], default="latest-begin",
                    help="Dedup strategy by RootID (default: latest-begin)")
    ap.add_argument("--today", default=None, help="Override 'today' (YYYY-MM-DD) for testing")
    ap.add_argument("--keep-all-columns", action="store_true",
                    help="Keep all original columns instead of slimming to core fields")
    args = ap.parse_args()

    clean = process_folder(
        input_dir=args.input_dir,
        prefixes=tuple(args.prefixes),
        dedupe_strategy=args.dedupe,
        today_override=args.today,
        keep_all_columns=args.keep_all_columns,  # <-- pass through
    )

    # Month-stamped folder
    run_month = datetime.today().strftime("%Y-%m")
    output_dir = os.path.join(os.path.dirname(args.output), run_month)
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, os.path.basename(args.output))

    clean.to_excel(out_path, index=False)
    print(f"[OK] Wrote cleaned file -> {out_path}")
    print(f"[INFO] Rows: {len(clean)} | Columns: {len(clean.columns)}")



if __name__ == "__main__":
    main()
