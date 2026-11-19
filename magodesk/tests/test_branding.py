"""Run: python3 -m unittest discover -s magodesk/tests   (from the repository root, on a clean upstream tree).

The tests copy only the files the rules touch into a temporary directory, so they do not change the
working tree and need no build tools.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "magodesk"))
from rules import RULES  # noqa: E402

BRANDING = ROOT / "magodesk" / "branding.py"
ENV = {"RD_HOST": "rd.example.com", "RD_KEY": "A" * 43 + "=", "RD_APP_NAME": "MagoDesk"}


def run(tree, *args, env=None):
    e = {**os.environ, **{k: v for k, v in ENV.items()}, **(env or {})}
    for k in [k for k, v in e.items() if v is None]:
        del e[k]
    return subprocess.run([sys.executable, str(BRANDING), "--root", str(tree), *args],
                          capture_output=True, text=True, env=e)


def snapshot(tree):
    return {str(p.relative_to(tree)): p.read_bytes() for p in sorted(tree.rglob("*")) if p.is_file()}


class Branding(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tree = self.tmp / "tree"
        for f in {r[0] for r in RULES} | {"Cargo.toml", "src/lib.rs"}:
            dst = self.tree / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / f, dst)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_check_writes_nothing(self):
        before = snapshot(self.tree)
        r = run(self.tree, "--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(before, snapshot(self.tree))
        self.assertIn(f"{len(RULES)} rule(s) would change", r.stdout)

    def test_apply_then_apply_again_changes_nothing(self):
        self.assertEqual(run(self.tree).returncode, 0)
        after_first = snapshot(self.tree)
        r = run(self.tree)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 rule(s) changed", r.stdout)
        self.assertEqual(after_first, snapshot(self.tree))

    def test_app_name_reaches_the_files(self):
        run(self.tree, env={"RD_APP_NAME": "Zed"})
        gradle = (self.tree / "flutter/android/app/build.gradle").read_text()
        self.assertIn("'Zed'", gradle)
        self.assertIn('applicationId "br.com.diomedes.zed"', gradle)
        self.assertIn('name = "Zed"', (self.tree / "Cargo.toml").read_text())

    def test_android_id_and_bundle_prefix_come_from_variables(self):
        run(self.tree, env={"RD_ANDROID_ID": "org.example.app", "RD_BUNDLE_PREFIX": "org.example"})
        self.assertIn('applicationId "org.example.app"', (self.tree / "flutter/android/app/build.gradle").read_text())
        self.assertIn('identifier = "org.example.magodesk"', (self.tree / "Cargo.toml").read_text())

    def test_a_rule_that_matches_nothing_fails_and_names_the_file(self):
        p = self.tree / "libs/portable/build.rs"
        p.write_text(p.read_text().replace("set_manifest_file", "set_manifest_file_x"))
        r = run(self.tree)
        self.assertEqual(r.returncode, 1)
        self.assertIn("libs/portable/build.rs", r.stderr)

    def test_an_anchor_that_appears_twice_fails(self):
        p = self.tree / "src/lib.rs"
        p.write_text(p.read_text() + "\n" + p.read_text())
        r = run(self.tree)
        self.assertEqual(r.returncode, 1)
        self.assertIn("2x", r.stderr)

    def test_missing_secret_fails_before_touching_anything(self):
        before = snapshot(self.tree)
        for var in ("RD_HOST", "RD_KEY", "RD_APP_NAME"):
            r = run(self.tree, env={var: ""})
            self.assertEqual(r.returncode, 1, var)
            self.assertIn(var, r.stderr)
        self.assertEqual(before, snapshot(self.tree))

    def test_bad_values_are_rejected(self):
        for env in ({"RD_APP_NAME": "Mago Desk"}, {"RD_HOST": "bad host!"}, {"RD_KEY": "short"},
                    {"RD_ANDROID_ID": "NoDots"}, {"RD_BUNDLE_PREFIX": "nodots"}):
            self.assertEqual(run(self.tree, env=env).returncode, 1, env)

    def test_secrets_are_never_printed(self):
        r = run(self.tree)
        self.assertNotIn(ENV["RD_HOST"], r.stdout + r.stderr)
        self.assertNotIn(ENV["RD_KEY"], r.stdout + r.stderr)

    def test_not_an_upstream_tree(self):
        r = run(self.tmp / "nothing")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
