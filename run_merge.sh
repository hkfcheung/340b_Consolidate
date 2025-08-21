#!/bin/bash
PROJ="/Users/ethancheung/Documents/AI/340b_Consolidate"
PYEXE="$PROJ/.venv/bin/python"

cd "$PROJ"

mkdir -p logs

ts=$(date +"%Y-%m-%d_%H%M%S")
LOG="logs/merge_$ts.log"

echo "Running merge_340b.py..." > "$LOG" 2>&1
"$PYEXE" merge_340b.py --input-dir "./input" --output "./output/cleaned_340B_list.xlsx" --keep-all-columns >> "$LOG" 2>&1

echo "Done. See $LOG for details."
