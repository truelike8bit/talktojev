#!/usr/bin/env python3
"""Interactive terminal chat client for talktojev SSE stream endpoint."""

import argparse
import json
import os
import sys
import time
import uuid
import httpx


def main():
    parser = argparse.ArgumentParser(description="Chat interactively with Jev in the terminal")
    parser.add_argument("--url", default="http://localhost:8787", help="Base URL of talktojev server")
    parser.add_argument("--session", default=None, help="Custom session ID (defaults to random)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print debug/telemetry streaming events")
    args = parser.parse_args()

    session_id = args.session or f"cli_{uuid.uuid4().hex[:8]}"
    print("=" * 60)
    print("  Talk to Jev — Interactive Terminal Session")
    print(f"  Endpoint: {args.url}")
    print(f"  Session ID: {session_id}")
    print("  Type your message and press Enter. (Commands: /new, /exit)")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        if not user_input:
            continue

        if user_input in ("/exit", "/quit"):
            print("Session ended.")
            break

        if user_input == "/new":
            session_id = f"cli_{uuid.uuid4().hex[:8]}"
            print(f"\n[Reset] Started new session: {session_id}")
            continue

        if user_input == "/help":
            print("\nAvailable commands:\n  /new  - Start a new conversation turn session\n  /exit - Quit")
            continue

        if len(user_input) > 100:
            print("[Warning] Message exceeds 100 chars; server rate gate may reject or truncate.")

        payload = {
            "session_id": session_id,
            "message": user_input,
            "local_time": time.strftime("%A, %d %B, %H:%M"),
        }

        print("\nJev > ", end="", flush=True)
        t0 = time.time()
        text = ""

        try:
            with httpx.stream("POST", f"{args.url}/api/chat", json=payload, timeout=120.0) as resp:
                if resp.status_code != 200:
                    err_msg = resp.read().decode("utf-8", errors="ignore")
                    print(f"\n[Server Error {resp.status_code}]: {err_msg}")
                    continue

                for line in resp.iter_lines():
                    if line.startswith(": thinking"):
                        if args.verbose:
                            print("·", end="", flush=True)
                        continue
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[6:])
                            if "replace" in ev:
                                text = ev["replace"]
                                print(f"\rJev > {text}", end="", flush=True)
                            elif "interrupted" in ev:
                                pass
                            else:
                                chunk = ev.get("text", ev.get("char", ""))
                                text += chunk
                                print(chunk, end="", flush=True)
                        except Exception:
                            pass
            dt = time.time() - t0
            print(f"  \x1b[90m({dt:.1f}s)\x1b[0m")
        except Exception as e:
            print(f"\n[Connection Error]: Could not reach server at {args.url}. Is server running?")
            print(f"Details: {e}")


if __name__ == "__main__":
    main()
