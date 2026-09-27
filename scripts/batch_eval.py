#!/usr/bin/env python3
"""Batch scenario runner and run comparison tool for talktojev."""

import argparse
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_scenario import run_scenario


def load_budget():
    budget_file = "data/budget_ts.json"
    if os.path.exists(budget_file):
        try:
            with open(budget_file) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def run_batch(scenario_files, server_url="http://localhost:8787"):
    if not scenario_files:
        scenario_files = sorted(glob.glob("scenarios/*.json"))

    if not scenario_files:
        print("[Error] No scenario JSON files found in scenarios/ directory.")
        return

    ts_start = time.strftime("%Y%m%d_%H%M%S")
    budget_before = load_budget()

    print("=" * 70)
    print("  TALK TO JEV — BATCH EVALUATION SUITE")
    print(f"  Scenarios to run: {len(scenario_files)}")
    if budget_before:
        print(f"  Initial Budget Tracker: ${budget_before.get('usd', 0.0):.4f} ({budget_before.get('date')})")
    print("=" * 70)

    all_results = []
    total_turns = 0
    total_completed = 0
    total_errors = 0
    pass_count = 0

    for sc_file in scenario_files:
        res = run_scenario(sc_file, server_url=server_url)
        all_results.append(res)
        total_turns += res.get("turns_total", 0)
        total_completed += res.get("turns_completed", 0)
        total_errors += res.get("errors", 0)
        if res.get("verdict") == "PASS":
            pass_count += 1
        time.sleep(2.0)

    budget_after = load_budget()
    budget_diff = 0.0
    if budget_before and budget_after and budget_before.get("date") == budget_after.get("date"):
        budget_diff = budget_after.get("usd", 0.0) - budget_before.get("usd", 0.0)

    batch_summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenarios_run": len(scenario_files),
        "scenarios_passed": pass_count,
        "scenarios_failed": len(scenario_files) - pass_count,
        "pass_rate": round((pass_count / len(scenario_files)) * 100, 1),
        "total_turns": total_turns,
        "turns_completed": total_completed,
        "total_errors": total_errors,
        "estimated_budget_usd_change": round(budget_diff, 4),
        "runs": all_results
    }

    os.makedirs("data/eval_runs", exist_ok=True)
    out_json = f"data/eval_runs/batch_{ts_start}.json"
    with open(out_json, "w") as f:
        json.dump(batch_summary, f, indent=2)

    # Print summary table
    print("\n" + "=" * 70)
    print("  BATCH EVALUATION COMPLETE")
    print("=" * 70)
    print(f"  Scenarios Passed: {pass_count} / {len(scenario_files)} ({batch_summary['pass_rate']}%)")
    print(f"  Total Turns:      {total_completed} / {total_turns}")
    print(f"  Total Errors:     {total_errors}")
    print(f"  Saved Batch Data: {out_json}")
    print("=" * 70)


def compare_runs(file_a, file_b):
    with open(file_a) as f:
        data_a = json.load(f)
    with open(file_b) as f:
        data_b = json.load(f)

    print("=" * 70)
    print(f"  RUN COMPARISON: {os.path.basename(file_a)} vs {os.path.basename(file_b)}")
    print("=" * 70)
    print(f"  Metric                     | Run A                | Run B")
    print(f"  ---------------------------+----------------------+---------------------")
    print(f"  Date                       | {data_a.get('timestamp','-')[:16]}     | {data_b.get('timestamp','-')[:16]}")
    print(f"  Pass Rate                  | {data_a.get('pass_rate','-')}%                | {data_b.get('pass_rate','-')}%")
    print(f"  Total Errors               | {data_a.get('total_errors','-')}                    | {data_b.get('total_errors','-')}")
    print(f"  Scenarios Passed           | {data_a.get('scenarios_passed','-')}/{data_a.get('scenarios_run','-')}              | {data_b.get('scenarios_passed','-')}/{data_b.get('scenarios_run','-')}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Batch Evaluation for Talk to Jev")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    run_parser = subparsers.add_parser("run", help="Run a batch of scenarios")
    run_parser.add_argument("--scenarios", nargs="*", default=None, help="List of scenario files to run")
    run_parser.add_argument("--url", default="http://localhost:8787", help="Base URL of server")

    comp_parser = subparsers.add_parser("compare", help="Compare two batch runs")
    comp_parser.add_argument("file_a", help="First batch JSON file")
    comp_parser.add_argument("file_b", help="Second batch JSON file")

    args = parser.parse_args()
    if args.subcommand == "run":
        run_batch(args.scenarios, server_url=args.url)
    elif args.subcommand == "compare":
        compare_runs(args.file_a, args.file_b)


if __name__ == "__main__":
    main()
