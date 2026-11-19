#!/usr/bin/env python3
"""Brand the macOS app for a build and check that the captive wiring is still in the tree.

    branding.py [--check] [--prefix br.com.diomedes] NAME     (NAME = RD_APP_NAME, e.g. MagoDesk)

Every rule replaces a literal string. A rule that matches nothing fails the build, unless its
replacement is already there (the script can run twice): a rule that did nothing silently would
ship an app that still carries the identity of the stock RustDesk. --check writes nothing.
The launchd plists need no edit: the program rewrites them at run time (correct_app_name in
src/platform/macos.rs).
"""
import argparse
import re
import sys
from pathlib import Path

XC = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
# upstream merges can move these lines: a miss here is the signal to update the rule
WIRING = [
    ("src/lib.rs", "mod captive;"),
    ("src/common.rs", "crate::captive::apply();"),
    ("src/flutter_ffi.rs", "crate::captive::apply();"),
    ("src/captive.rs", "pub fn is_captive"),
    ("flutter/android/app/build.gradle", 'applicationId "br.com.diomedes.magodesk"'),
]


def rules(name, prefix):
    low, bundle = name.lower(), f"{prefix}.{name.lower()}"
    return [
        (XC, "PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {name}"),
        (XC, "RD_BUNDLE_ID = com.carriez.rustdesk", f"RD_BUNDLE_ID = {bundle}"),
        (XC, "RD_URL_SCHEME = rustdesk", f"RD_URL_SCHEME = {low}"),
        (XC, "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb", f"PRODUCT_BUNDLE_IDENTIFIER = {bundle}"),
        ("Cargo.toml", '[package.metadata.bundle]\nname = "RustDesk"\nidentifier = "com.carriez.rustdesk"',
         f'[package.metadata.bundle]\nname = "{name}"\nidentifier = "{bundle}"'),
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--prefix", default="br.com.diomedes")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", args.name):
        sys.exit(f"branding: invalid app name '{args.name}': letters and digits only")

    bad = 0
    for f, old, new in rules(args.name, args.prefix):
        p = Path(f)
        text = p.read_text(encoding="utf-8")
        if old in text:
            status = "would change" if args.check else "changed"
            if not args.check:
                p.write_text(text.replace(old, new), encoding="utf-8")
        elif new in text:
            status = "already applied"
        else:
            status, bad = "NO MATCH", bad + 1
        print(f"{status:>16}  {old.splitlines()[-1][:48]!r} in {f}")
    for f, needle in WIRING:
        if needle not in Path(f).read_text(encoding="utf-8"):
            print(f"{'MISSING':>16}  {needle!r} in {f}")
            bad += 1
    if bad:
        sys.exit(f"\nbranding: {bad} problem(s). The tree no longer matches; fix the rule or the wiring before building.")
    print(f"\nbranding: ok app={args.name} bundle_id={args.prefix}.{args.name.lower()}")


if __name__ == "__main__":
    main()
