#!/usr/bin/env python3
# test_anthropic_key.py - v1.0
# Loads .env from repo root and calls Anthropic API once to validate ANTHROPIC_API_KEY.
# Deps: anthropic. Run from repo root: python backend/scripts/test_anthropic_key.py. Port: N/A.

import os
import sys

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
ENV_PATH = os.path.join(REPO_ROOT, ".env")

def main():
    if not os.path.exists(ENV_PATH):
        print("ERROR: .env not found at", ENV_PATH)
        sys.exit(1)
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not found in .env")
        sys.exit(1)
    print("Key loaded (sk-ant-..." + key[-8:] + ")")
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic not installed. Run: pip install anthropic")
        sys.exit(1)
    client = anthropic.Anthropic()
    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=64,
        messages=[{"role": "user", "content": "Reply with exactly: API key works."}],
    )
    reply = r.content[0].text if r.content else ""
    print("Response:", reply.strip())
    print("OK - ANTHROPIC_API_KEY is valid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
