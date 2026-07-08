#!/bin/bash
# E11 IMPROVED RUN: Increased sample size from 50 to 100 seeds for robust statistics
# This addresses the outlier anomalies found in preliminary run by statistical averaging

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "E11 IMPROVED: Running with 100 seeds/level"
echo "=========================================="
echo "Objective: Generate robust statistics with larger sample size"
echo "Expected duration: ~6-8 hours on modern hardware"
echo "Motivation: Preliminary 50-seed run had outlier anomalies; larger n reduces impact"
echo ""

# Use increased NUM_SEEDS
export E11_NUM_SEEDS=100
export E11_MASTER_SEED=150

echo "Parameters:"
echo "  NUM_SEEDS = $E11_NUM_SEEDS"
echo "  MASTER_SEED = $E11_MASTER_SEED"
echo "  repo_bw levels = [60, 120, 240, 480] MBps"
echo "  Total runs = $E11_NUM_SEEDS × 4 = 400"
echo ""

python3 run_experiment.py

echo ""
echo "=========================================="
echo "E11_IMPROVED run complete!"
echo "=========================================="
echo ""
echo "Analysis steps:"
echo "  1. python3 analyze_results.py <result_folder>"
echo "  2. Review e11_robust_summary.csv for median/trimmed statistics"
echo "  3. Compare boxplot with previous 50-seed run"
echo ""

