#!/usr/bin/env python3
"""Evaluate the direct-answering goals of this fork.

Runs a set of prompts through the generation pipeline (in-process, no server
needed) and checks that the replies are clear, accurate, and not padded with
unnecessary elaboration.

Goals under test (from AGENTS.md and the latest criteria changes):
  1. Brief, accurate answers to factual questions.
  2. Neutral critique criteria ("clear and appropriate", not "sounds human").
  3. Completeness: the reply answers what was asked, then stops.
  4. No emotional attractor loops or warmth padding.

Usage:
  python scripts/test_direct_answering.py [--only d1,d3] [--verbose]
"""
import asyncio
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("MEMO_ACROSS_REPLIES", "0")

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(ROOT, ".env"))

# Each prompt is (id, user_message, checks) where checks is a dict of
# assertion names to callables: check(reply_text, metrics) -> (pass, reason).
PROMPTS = [
    ("d1", "how many legs does a dog have?", {
        "answered": lambda t, m: (bool(re.search(r"\bfour\b|\b4\b", t.lower())), "expected 'four' or '4'"),
        "brief": lambda t, m: (m["words"] <= 15, f"too long: {m['words']} words"),
    }),
    ("d2", "is water wet?", {
        "answered": lambda t, m: (bool(re.search(r"\byes\b|\bwet\b", t.lower())), "expected 'yes' or 'wet'"),
        "brief": lambda t, m: (m["words"] <= 20, f"too long: {m['words']} words"),
    }),
    ("d3", "what color is the sky on a clear day?", {
        "answered": lambda t, m: (bool(re.search(r"\bblue\b", t.lower())), "expected 'blue'"),
        "brief": lambda t, m: (m["words"] <= 15, f"too long: {m['words']} words"),
    }),
    ("d4", "how many days are in a week?", {
        "answered": lambda t, m: (bool(re.search(r"\bseven\b|\b7\b", t.lower())), "expected 'seven' or '7'"),
        "brief": lambda t, m: (m["words"] <= 15, f"too long: {m['words']} words"),
    }),
    ("d5", "do you like music?", {
        "non_empty": lambda t, m: (m["words"] >= 2, "reply is too short or empty"),
        "no_loop": lambda t, m: (m["repeated_bigrams"] == 0, f"repeated bigrams: {m['repeated_bigrams']}"),
    }),
    ("d6", "i feel really sad today", {
        "non_empty": lambda t, m: (m["words"] >= 3, "reply is too short or empty"),
        "brief": lambda t, m: (m["words"] <= 30, f"too long: {m['words']} words"),
        "no_loop": lambda t, m: (m["repeated_bigrams"] == 0, f"repeated bigrams: {m['repeated_bigrams']}"),
    }),
    ("d7", "what is the capital of mongolia?", {
        # Jev may not know this — acceptable to admit it or try to answer
        "non_empty": lambda t, m: (m["words"] >= 2, "reply is too short or empty"),
        "brief": lambda t, m: (m["words"] <= 20, f"too long: {m['words']} words"),
    }),
    ("d8", "who are you?", {
        "non_empty": lambda t, m: (m["words"] >= 3, "reply is too short or empty"),
        "brief": lambda t, m: (m["words"] <= 25, f"too long: {m['words']} words"),
        "no_loop": lambda t, m: (m["repeated_bigrams"] == 0, f"repeated bigrams: {m['repeated_bigrams']}"),
    }),
]

FIXED_NOW = "Sunday 27 September 2026 at 15:00"


def basic_metrics(text):
    """Lightweight metrics sufficient for the checks above."""
    toks = text.lower().split()
    from collections import Counter
    bigrams = Counter(zip(toks, toks[1:]))
    return {
        "words": len(toks),
        "sentences": len([s for s in re.split(r"[.!?]+", text) if s.strip()]),
        "repeated_bigrams": sum(1 for c in bigrams.values() if c > 1),
        "empty": not text.strip(),
    }


async def run_one(server, pid, user_msg, checks, verbose=False):
    """Generate a reply and run the checks."""
    msgs = [{"role": "user", "content": user_msg}]
    t0 = time.time()
    try:
        text = await server.collect_reply(
            server.generate_response_tree(msgs, now=FIXED_NOW)
        )
    except Exception as e:
        return {"id": pid, "user": user_msg, "text": "", "error": repr(e),
                "seconds": round(time.time() - t0, 1), "results": {}, "pass": False}

    dt = round(time.time() - t0, 1)
    m = basic_metrics(text)
    results = {}
    all_pass = True
    for name, fn in checks.items():
        ok, reason = fn(text, m)
        results[name] = {"pass": ok, "reason": reason if not ok else ""}
        if not ok:
            all_pass = False

    row = {"id": pid, "user": user_msg, "text": text, "seconds": dt,
           "words": m["words"], "results": results, "pass": all_pass}

    status = "PASS" if all_pass else "FAIL"
    if verbose or not all_pass:
        print(f"  {pid} [{status}] {dt}s {m['words']}w  {user_msg!r}")
        print(f"        -> {text!r}")
        for name, r in results.items():
            mark = "✓" if r["pass"] else "✗"
            extra = f"  ({r['reason']})" if r["reason"] else ""
            print(f"        {mark} {name}{extra}")
    else:
        print(f"  {pid} [{status}] {dt}s {m['words']}w  {text[:60]!r}")

    return row


async def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", help="comma-separated prompt ids to run")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--out", help="write results to this JSONL file")
    args = p.parse_args()

    import server
    import provider as prov
    server._PROVIDER.set(prov.pick_provider(None, server.BUDGET_OR, server.BUDGET_TS))

    only = set(args.only.split(",")) if args.only else None
    rows = []
    passed = 0
    total = 0

    print("direct-answering evaluation")
    print("=" * 50)

    for pid, user_msg, checks in PROMPTS:
        if only and pid not in only:
            continue
        total += 1
        row = await run_one(server, pid, user_msg, checks, verbose=args.verbose)
        rows.append(row)
        if row["pass"]:
            passed += 1

    print("=" * 50)
    print(f"  {passed}/{total} passed")

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"  results written to {args.out}")

    # Exit code: 0 if all passed, 1 otherwise
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
