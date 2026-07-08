#!/bin/bash
# Quick launcher for E11: run_experiment.py + analyze_results.py

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Launching E11 Experiment: Repository Bandwidth Impact ==="
echo

# Run experiment
python3 "$DIR/run_experiment.py"

# Capture result directory from log
RESULT_DIR=$(python3 -c "
import os, time
d = '$DIR'
for entry in sorted(os.listdir(d), reverse=True):
    if entry.startswith('run_'):
        full_path = os.path.join(d, entry)
        if os.path.isdir(full_path):
            print(full_path)
            break
")

if [ -z "$RESULT_DIR" ]; then
    echo "Error: Could not find result directory"
    exit 1
fi

echo
echo "Result directory: $RESULT_DIR"
echo

# Run analysis
python3 "$DIR/analyze_results.py" "$RESULT_DIR"

echo
echo "=== E11 Complete ==="

