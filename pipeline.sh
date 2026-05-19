#!/bin/bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate

echo "=== $(date) ===" >> pipeline.log
python loader.py   >> pipeline.log 2>&1
python analysis.py     >> pipeline.log 2>&1
python correlations.py >> pipeline.log 2>&1
python alert.py        >> pipeline.log 2>&1
python plot.py --no-show >> pipeline.log 2>&1
echo "Pipeline complete." >> pipeline.log
