#!/usr/bin/env python3
"""Stamp the version of a release tag into every file the build reads.

    set_version.py v1.0.0        -> 1.0.0   (versionCode 1000099)
    set_version.py v1.0.0-rc2    -> 1.0.0   (versionCode 1000002)

The binary, the MSI and Flutter need a numeric X.Y.Z, so the -rcN suffix lives only in
the tag and in the file names. The Android versionCode keeps rcN < final, so a test
build can be updated by the next candidate and by the final release.
Cargo.lock is patched too because the build runs with --locked.
"""
import re
import sys
from pathlib import Path

TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?$")


def parse(tag):
    m = TAG.match(tag)
    if not m:
        raise SystemExit(f"invalid tag '{tag}': expected vX.Y.Z or vX.Y.Z-rcN")
    major, minor, patch = (int(m[i]) for i in (1, 2, 3))
    rc = int(m[4]) if m[4] else None
    if max(minor, patch) > 99 or major > 2000 or (rc is not None and not 1 <= rc <= 98):
        raise SystemExit(f"tag '{tag}' is out of range (minor/patch <= 99, rc 1..98)")
    code = major * 1_000_000 + minor * 10_000 + patch * 100 + (rc if rc else 99)
    return f"{major}.{minor}.{patch}", code


def sub(path, pattern, repl, count=1):
    p = Path(path)
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
    if n == 0:
        raise SystemExit(f"{path}: pattern not found: {pattern}")
    p.write_text(new, encoding="utf-8")


def main(tag):
    version, code = parse(tag)
    sub("Cargo.toml", r'^version = "[^"]*"', f'version = "{version}"')
    sub("libs/portable/Cargo.toml", r'^version = "[^"]*"', f'version = "{version}"')
    sub("flutter/pubspec.yaml", r"^version: .*", f"version: {version}+{code}")
    # libs/portable is a workspace member: the root lock is the one --locked checks
    for pkg in ("rustdesk", "rustdesk-portable-packer"):
        sub("Cargo.lock", rf'(name = "{pkg}"\nversion = )"[^"]*"', rf'\1"{version}"')
    print(f"version={version} versionCode={code}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
