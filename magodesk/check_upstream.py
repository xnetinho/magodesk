#!/usr/bin/env python3
"""Check that this tree can still be branded and built. Writes nothing to the repository.

    python3 magodesk/check_upstream.py [--report FILE] [--real-inputs]

Runs, in order, and reports every failure instead of stopping at the first:
  1. branding.py --check          the text rules still match the upstream files
  2. make_workflow.py --check     magodesk-build.yml is what upstream's flutter-build.yml produces today
  3. the unit tests of the engine

Exit code 0 only if all three pass. --report writes a Markdown summary (used for the GitHub issue).
RD_HOST, RD_KEY, RD_APP_NAME and RUSTDESK_UPDATE_ED25519_PUBLIC_KEY are needed by step 1. By default, missing ones are replaced by harmless
stand-ins (the daily check looks at the shape of the files, never at the real server). With --real-inputs
(the release preflight) a missing or invalid one FAILS, so a release stops before compiling anything.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STAND_IN = {"RD_HOST": "check.example.com", "RD_KEY": "A" * 43 + "=", "RD_APP_NAME": "MagoDesk",
            "RUSTDESK_UPDATE_ED25519_PUBLIC_KEY": "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="}


def run(cmd, env):
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--report", help="write a Markdown summary to this file")
    ap.add_argument("--real-inputs", action="store_true", help="do not substitute missing RD_* values")
    args = ap.parse_args()
    env = {**os.environ}
    if not args.real_inputs:
        for k, v in STAND_IN.items():
            if not env.get(k):
                env[k] = v

    py = sys.executable
    steps = [
        ("Branding rules (`branding.py --check`)", [py, "magodesk/branding.py", "--check"]),
        ("Generated workflow (`make_workflow.py --check`)", [py, "magodesk/make_workflow.py", "--check"]),
        ("Engine tests", [py, "-m", "unittest", "discover", "-s", "magodesk/tests"]),
    ]
    results = [(title, *run(cmd, env)) for title, cmd in steps]
    ok = all(rc == 0 for _, rc, _ in results)

    lines = [f"**{'All checks passed' if ok else 'Some checks FAILED'}**", ""]
    for title, rc, out in results:
        lines.append(f"- {'OK' if rc == 0 else 'FAILED'}: {title}")
    for title, rc, out in results:
        if rc != 0:
            tail = "\n".join(out.splitlines()[-25:])
            lines += ["", f"### {title}", "```", tail, "```"]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
