#!/usr/bin/env python3
"""Rebrand the macOS app for a build: RD_APP_NAME -> bundle name, bundle id and URL scheme.

    set_macos_brand.py MagoDesk [bundle-id-prefix]

Run it before `build.py --flutter` on the macOS runner. It rewrites the Xcode config, the
bundle metadata, so the app can sit next to a stock RustDesk without sharing a bundle id or URL
scheme. The launchd plists need no edit here: the program rewrites them at run time from APP_NAME
and the bundle id (correct_app_name in src/platform/macos.rs).
"""
import re
import sys
from pathlib import Path

DEFAULT_PREFIX = "br.com.diomedes"


def check_name(name):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name):
        raise SystemExit(f"invalid app name '{name}': letters and digits only")


def sub(path, pattern, repl, expect=1, flags=re.M):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, flags=flags)
    if n != expect:
        raise SystemExit(f"{path}: expected {expect} match(es) for {pattern!r}, found {n}")
    p.write_text(new, encoding="utf-8")


def main(name, prefix):
    check_name(name)
    lower = name.lower()
    bundle_id = f"{prefix}.{lower}"

    xc = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
    sub(xc, r"^PRODUCT_NAME = .*$", f"PRODUCT_NAME = {name}")
    sub(xc, r"^PRODUCT_BUNDLE_IDENTIFIER = .*$", f"PRODUCT_BUNDLE_IDENTIFIER = {bundle_id}")
    sub(xc, r"^RD_BUNDLE_ID = .*$", f"RD_BUNDLE_ID = {bundle_id}")
    sub(xc, r"^RD_URL_SCHEME = .*$", f"RD_URL_SCHEME = {lower}")

    # the cargo bundle metadata and the dmg/app names the build script uses
    sub("Cargo.toml", r'^(\[package\.metadata\.bundle\]\nname = )"[^"]*"', rf'\1"{name}"')
    sub("Cargo.toml", r'^(\[package\.metadata\.bundle\]\nname = "[^"]*"\nidentifier = )"[^"]*"', rf'\1"{bundle_id}"')

    print(f"app={name} bundle_id={bundle_id} scheme={lower}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else DEFAULT_PREFIX)
