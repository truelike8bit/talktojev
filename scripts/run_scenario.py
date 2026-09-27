#!/usr/bin/env python3
"""Scenario execution and metrics reporting tool for talktojev."""

import argparse
import json
import os
import re
import sys
import time
import uuid
import httpx


def calculate_repetition_rate(text: str) -> float:
    """Calculates word bigram repetition rate to detect degenerate looping."""
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if len(words) < 4:
        return 0.0
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    if not bigrams:
        return 0.0
    unique_bigrams = set(bigrams)
    return round(1.0 - (len(unique_bigrams) / len(bigrams)), 3)


def run_scenario(scenario_path: str, server_url: str = "http://localhost:8787", report_path: str = None):
    with open(scenario_path, "r") as f:
        scenario = json.load(f)

    session_id = f"test_{uuid.uuid4().hex[:8]}"
    name = scenario.get("name", "Scenario")
    subject = scenario.get("subject", "General")
    description = scenario.get("description", "")
    turns = scenario.get("turns", [])
    max_rep_threshold = scenario.get("max_repetition_rate", 0.30)

    print("=" * 65)
    print(f"  RUNNING SCENARIO: {name}")
    print(f"  Subject: {subject}")
    print(f"  Session ID: {session_id}")
    print(f"  Turns: {len(turns)}")
    print("=" * 65)

    results = []
    total_latency = 0.0
    total_words = 0
    errors = 0
    max_observed_repetition = 0.0

    for item in turns:
        t_num = item.get("turn")
        user_msg = item.get("user")
        tags = item.get("tags", [])

        print(f"\n[Turn {t_num}] User: {user_msg}")
        t0 = time.time()
        reply = ""
        payload = {
            "session_id": session_id,
            "message": user_msg,
            "local_time": time.strftime("%A, %d %B, %H:%M"),
        }

        try:
            with httpx.stream("POST", f"{server_url}/api/chat", json=payload, timeout=120.0) as resp:
                if resp.status_code != 200:
                    err_msg = resp.read().decode("utf-8", errors="ignore")
                    print(f"  Error {resp.status_code}: {err_msg}")
                    errors += 1
                    results.append({
                        "turn": t_num, "user": user_msg, "jev": None,
                        "error": err_msg, "latency": 0.0, "words": 0, "tags": tags
                    })
                    continue

                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[6:])
                            if "replace" in ev:
                                reply = ev["replace"]
                            elif "interrupted" in ev:
                                pass
                            else:
                                reply += ev.get("text", ev.get("char", ""))
                        except Exception:
                            pass
            dt = round(time.time() - t0, 2)
            clean_reply = reply.strip()
            w_count = len(clean_reply.split())
            rep_rate = calculate_repetition_rate(clean_reply)
            max_observed_repetition = max(max_observed_repetition, rep_rate)
            total_latency += dt
            total_words += w_count

            print(f"  Jev ({dt}s, {w_count}w, rep={rep_rate}): {clean_reply}")
            results.append({
                "turn": t_num,
                "user": user_msg,
                "jev": clean_reply,
                "latency": dt,
                "words": w_count,
                "repetition_rate": rep_rate,
                "tags": tags
            })
        except Exception as e:
            errors += 1
            print(f"  Exception: {e}")
            results.append({
                "turn": t_num, "user": user_msg, "jev": None,
                "error": str(e), "latency": 0.0, "words": 0, "tags": tags
            })
        time.sleep(1.5)

    num_valid = len([r for r in results if r.get("jev")])
    avg_latency = round(total_latency / max(1, num_valid), 2)
    avg_words = round(total_words / max(1, num_valid), 1)

    # Pass/Fail Assessment
    passed = (errors == 0) and (num_valid == len(turns)) and (max_observed_repetition <= max_rep_threshold)
    status_str = "PASS" if passed else "FAIL"

    summary = {
        "scenario": name,
        "subject": subject,
        "description": description,
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": status_str,
        "turns_total": len(turns),
        "turns_completed": num_valid,
        "errors": errors,
        "avg_latency": avg_latency,
        "avg_words": avg_words,
        "max_repetition_rate": max_observed_repetition,
        "turns_data": results
    }

    # Save JSON in data/eval_runs/
    os.makedirs("data/eval_runs", exist_ok=True)
    base_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name.lower())
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = f"data/eval_runs/{base_slug}_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Generate Markdown report
    if not report_path:
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/{base_slug}_{ts}.md"

    md = []
    md.append(f"# Test Report: {name}\n")
    md.append(f"- **Date:** {summary['timestamp']}")
    md.append(f"- **Subject:** {subject}")
    md.append(f"- **Session ID:** `{session_id}`")
    md.append(f"- **Verdict:** **{status_str}**\n")
    md.append("## Overview Metrics\n")
    md.append("| Metric | Value |")
    md.append("|---|---|")
    md.append(f"| **Status** | **{status_str}** |")
    md.append(f"| **Turns Completed** | {num_valid} / {len(turns)} |")
    md.append(f"| **Errors** | {errors} |")
    md.append(f"| **Avg Latency** | {avg_latency}s |")
    md.append(f"| **Avg Words/Turn** | {avg_words} |")
    md.append(f"| **Max Repetition Rate** | {max_observed_repetition} (Threshold: {max_rep_threshold}) |\n")

    md.append("## Transcript & Observations\n")
    for r in results:
        md.append(f"### Turn {r['turn']}")
        md.append(f"- **User:** *\"{r['user']}\"*")
        if r.get("jev"):
            md.append(f"- **Jev ({r['latency']}s, {r['words']}w):** *\"{r['jev']}\"*")
            md.append(f"- **Repetition Metric:** {r['repetition_rate']}")
        else:
            md.append(f"- **Error:** `{r.get('error')}`")
        if r.get("tags"):
            md.append(f"- **Tags:** {', '.join(r['tags'])}\n")

    with open(report_path, "w") as f:
        f.write("\n".join(md))

    print("\n" + "=" * 65)
    print(f"  SCENARIO RESULT: {status_str}")
    print(f"  Saved JSON:   {json_path}")
    print(f"  Saved Report: {report_path}")
    print("=" * 65)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run a conversation test scenario against talktojev")
    parser.add_argument("scenario", help="Path to scenario JSON file")
    parser.add_argument("--url", default="http://localhost:8787", help="Base URL of server")
    parser.add_argument("--out-report", default=None, help="Custom output Markdown report path")
    args = parser.parse_args()

    run_scenario(args.scenario, server_url=args.url, report_path=args.out_report)


if __name__ == "__main__":
    main()
