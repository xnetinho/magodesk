#!/usr/bin/env python3
"""Brand a pristine checkout of upstream RustDesk. Everything that is ours lives in magodesk/.

    python3 magodesk/branding.py [--root DIR] [--check] [--tag vX.Y.Z[-rcN]]

Inputs (GitHub secrets and variables, passed as environment variables):

    RD_HOST           secret    rendezvous server (host or host:port)
    RD_KEY            secret    public key of the server (base64)
    RD_APP_NAME       variable  product name, letters and digits only
    RD_ANDROID_ID     variable  Android applicationId        (default br.com.diomedes.<app lowercase>)
    RD_BUNDLE_PREFIX  variable  macOS bundle id prefix       (default br.com.diomedes)
    RUSTDESK_UPDATE_ED25519_PUBLIC_KEY  variable  public key that verifies the signed update metadata
                      (base64 of 32 bytes; the matching seed is the secret RUSTDESK_UPDATE_ED25519_SEED, used by the
                      release workflow to sign, never read here)
    RD_UPDATE_REPO    variable  owner/repo that publishes the releases (default: GITHUB_REPOSITORY, then xnetinho/magodesk)

What it does, in this order: validate the inputs, check that the tree is upstream's, copy
magodesk/captive.rs, apply magodesk/rules.py, stamp the version of --tag. RD_HOST and RD_KEY are
only checked here; the compiler reads them (option_env!) and they are never printed.

A rule that matches nothing is an ERROR, unless its result is already in the file (the script can
run twice). A block that matches more than once is also an error. --check writes nothing.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rules import RULES  # noqa: E402

DEFAULT_ANDROID_PREFIX = "br.com.diomedes"
import base64

DEFAULT_UPDATE_REPO = "xnetinho/magodesk"
HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:[0-9]{1,5})?$")
KEY_RE = re.compile(r"^[A-Za-z0-9+/]{42,44}={0,2}$")


def fail(msg):
    sys.exit(f"branding: {msg}")


def inputs(env):
    """Validate the environment; returns the values the rules need (never the secrets)."""
    host, key, app = env.get("RD_HOST", ""), env.get("RD_KEY", ""), env.get("RD_APP_NAME", "")
    missing = [n for n, v in (("RD_HOST", host), ("RD_KEY", key), ("RD_APP_NAME", app)) if not v]
    if missing:
        fail(f"missing: {', '.join(missing)}. Set the secrets RD_HOST and RD_KEY and the variable RD_APP_NAME, "
             "otherwise the client would point at the public RustDesk servers")
    if not HOST_RE.match(host):
        fail("RD_HOST is not a host or host:port")
    if not KEY_RE.match(key):
        fail("RD_KEY is not a base64 public key (expected 43 or 44 characters)")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", app):
        fail(f"RD_APP_NAME '{app}': letters and digits only, starting with a letter")
    android_id = env.get("RD_ANDROID_ID") or f"{DEFAULT_ANDROID_PREFIX}.{app.lower()}"
    prefix = env.get("RD_BUNDLE_PREFIX") or DEFAULT_ANDROID_PREFIX
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", android_id):
        fail(f"RD_ANDROID_ID '{android_id}' is not a valid Android application id")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*(\.[A-Za-z][A-Za-z0-9-]*)+", prefix):
        fail(f"RD_BUNDLE_PREFIX '{prefix}' is not a valid reverse-DNS prefix")
    update_key = env.get("RUSTDESK_UPDATE_ED25519_PUBLIC_KEY", "")
    if not update_key:
        fail("missing: RUSTDESK_UPDATE_ED25519_PUBLIC_KEY. Without it the client could not verify an update; "
             "see magodesk/CAPTIVE.md (update signing key)")
    try:
        raw = base64.b64decode(update_key, validate=True)
    except ValueError:
        fail("RUSTDESK_UPDATE_ED25519_PUBLIC_KEY is not valid base64")
    if len(raw) != 32 or base64.b64encode(raw).decode() != update_key:
        fail("RUSTDESK_UPDATE_ED25519_PUBLIC_KEY must be the canonical base64 of exactly 32 bytes")
    repo = env.get("RD_UPDATE_REPO") or env.get("GITHUB_REPOSITORY") or DEFAULT_UPDATE_REPO
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+", repo):
        fail(f"RD_UPDATE_REPO '{repo}' is not owner/repo")
    return dict(app=app, android_id=android_id, bundle=f"{prefix}.{app.lower()}",
                update_key=", ".join(str(b) for b in raw), update_repo=repo)


def fill(text, v):
    return (text.replace("@APP_LOWER@", v["app"].lower()).replace("@APP@", v["app"])
            .replace("@ANDROID_ID@", v["android_id"]).replace("@BUNDLE@", v["bundle"])
            .replace("@UPDATE_KEY@", v["update_key"])
            .replace("@UPDATE_RELEASES@", f"https://github.com/{v['update_repo']}/releases"))


def apply_rules(root, v, check):
    problems, changed, kept = [], 0, 0
    for rule in RULES:
        f, old, new = rule[0], rule[1], fill(rule[2], v)
        count = rule[3] if len(rule) > 3 else 1
        p = root / f
        if not p.is_file():
            problems.append(f"{'NO FILE':>16}  {f}")
            continue
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        # the result is tested first: a rule that inserts text before a line that stays has its
        # anchor inside the result, so "anchor present" does not mean "not applied yet"
        if new != old and text.count(new) >= count:
            kept += 1
        elif n == count:
            if not check:
                p.write_text(text.replace(old, new), encoding="utf-8")
            changed += 1
        else:
            what = "NO MATCH" if n == 0 else f"{n}x (want {count})"
            problems.append(f"{what:>16}  {f}: {old.strip().splitlines()[0][:60]!r}")
    return problems, changed, kept


def copy_ours(root, check):
    problems = []
    for src, dst in (("captive.rs", "magodesk/captive.rs"),):
        if not (HERE / src).is_file():
            problems.append(f"{'MISSING':>16}  magodesk/{src}")
        elif not check and root.resolve() != HERE.parent:
            (root / dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE / src, root / dst)
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--root", default=".", help="upstream checkout to brand (default .)")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--tag", help="release tag: stamps the version (needs a writable tree)")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not (root / "Cargo.toml").is_file() or not (root / "src" / "lib.rs").is_file():
        fail(f"{root} does not look like a RustDesk checkout")

    v = inputs(os.environ)
    problems = copy_ours(root, args.check)
    p2, changed, kept = apply_rules(root, v, args.check)
    problems += p2
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(f"\nbranding: {len(problems)} problem(s). Upstream changed a file this script edits, or a "
                 "file of ours is missing: update magodesk/rules.py before building.")
    verb = "would change" if args.check else "changed"
    print(f"branding: ok, {changed} rule(s) {verb}, {kept} already applied. "
          f"app={v['app']} android_id={v['android_id']} bundle_id={v['bundle']}")

    if args.tag and not args.check:
        import subprocess
        subprocess.run([sys.executable, str(HERE / "set_version.py"), args.tag], cwd=root, check=True)


if __name__ == "__main__":
    main()
