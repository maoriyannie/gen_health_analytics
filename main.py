#!/usr/bin/env python3
# main.py
# CLI entry point for the Gen-Health Analytics risk engine.
# Usage:
#   python main.py input.json
#   cat input.json | python main.py

import json
import sys

from engine.risk_scorer import score


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            with open(path) as f:
                raw = json.load(f)
        except FileNotFoundError:
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            raw = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        result = score(raw)
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
