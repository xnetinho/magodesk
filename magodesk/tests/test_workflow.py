"""The generated build workflow and the warm-up workflow. Run: python3 -m unittest discover -s magodesk/tests"""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILD = (ROOT / ".github/workflows/magodesk-build.yml").read_text(encoding="utf-8")
WARM = (ROOT / ".github/workflows/magodesk-warm.yml").read_text(encoding="utf-8")
RELEASE = (ROOT / ".github/workflows/magodesk-release.yml").read_text(encoding="utf-8")
JOBS = yaml.safe_load(BUILD)["jobs"]


def names(job):
    return [s.get("name") or s.get("uses", "")[:30] for s in JOBS[job]["steps"]]


class VcpkgCache(unittest.TestCase):
    def test_the_removed_x_gha_provider_is_gone(self):
        self.assertNotIn("x-gha", BUILD)
        # `runner` is not a context of the workflow-level env, so the value is exported by a step of each job
        self.assertNotIn("runner.temp }}/vcpkg-binary-cache,readwrite", BUILD)
        self.assertEqual(BUILD.count('echo "VCPKG_BINARY_SOURCES=clear;files,${dir},readwrite" >> "$GITHUB_ENV"'), 2)
        self.assertNotRegex(BUILD, r"(?m)^  VCPKG_BINARY_SOURCES:")

    def test_every_vcpkg_job_restores_the_cache_between_setup_and_install(self):
        for job in ("build-for-windows-flutter", "build-rustdesk-android"):
            n = names(job)
            a, p, b, c = (n.index(x) for x in ("Setup vcpkg with Github Actions binary cache",
                                                "Point vcpkg at the binary cache folder",
                                                "Restore the vcpkg binary cache", "Install vcpkg dependencies"))
            self.assertTrue(a < p < b < c, job)

    def test_the_cache_key_changes_with_the_vcpkg_commit_and_the_target(self):
        keys = re.findall(r"key: (vcpkg-bin-[^\n]+)", BUILD)
        self.assertEqual(len(keys), 2)
        for k in keys:
            self.assertIn("env.VCPKG_COMMIT_ID", k)
        # the Android matrix has no vcpkg-triplet, so it keys on the cargo target
        self.assertEqual(sorted(re.findall(r"matrix\.job\.(vcpkg-triplet|target)\b", "\n".join(keys))),
                         ["target", "vcpkg-triplet"])

    def test_the_cache_action_is_pinned_to_a_commit(self):
        for ref in re.findall(r"uses: actions/cache@(\S+)", BUILD):
            self.assertRegex(ref, r"^[0-9a-f]{40}$")


class CacheScope(unittest.TestCase):
    def test_macos_uses_no_cache_at_all(self):
        # its caches (~1.5 GB each) pushed the repository over the 10 GB limit and its time is flutter/Xcode, not Rust
        mac = yaml.dump(JOBS["build-for-macOS"])
        self.assertNotIn("rust-cache", mac)
        self.assertNotIn("vcpkg-binary-cache", mac)
        self.assertNotIn("actions/cache", mac)

    def test_only_the_default_branch_saves_the_compiler_cache(self):
        # a release is a new tag: a cache saved in its scope is 1.4-2.2 GB that nobody can read again
        self.assertEqual(BUILD.count("Swatinem/rust-cache"), 2)
        self.assertEqual(BUILD.count("save-if: ${{ github.ref == format('refs/heads/{0}', github.event.repository.default_branch) }}"), 2)


class UpstreamTests(unittest.TestCase):
    def test_its_own_test_steps_have_a_switch_and_are_off_by_default(self):
        # With the captive settings applied, upstream's network/key-exchange tests fail or hang; a warm-up must not run them.
        self.assertNotIn("!inputs.upload-artifact", BUILD)
        self.assertEqual(BUILD.count("inputs.run-tests"), 3)
        spec = yaml.safe_load(BUILD)[True]["workflow_call"]["inputs"]["run-tests"]
        self.assertEqual((spec["type"], spec["default"]), ("boolean", False))

    def test_neither_the_warm_up_nor_the_release_turns_them_on(self):
        self.assertNotIn("run-tests", WARM)
        self.assertNotIn("run-tests", RELEASE)


class WarmUp(unittest.TestCase):
    def setUp(self):
        self.d = yaml.safe_load(WARM)

    def test_it_publishes_nothing(self):
        self.assertIs(self.d["jobs"]["build"]["with"]["upload-artifact"], False)

    def test_it_only_runs_on_the_default_branch(self):
        self.assertIn("default_branch", yaml.dump(self.d["jobs"]["guard"]))
        self.assertEqual(self.d["jobs"]["build"]["needs"], ["preflight"])
        self.assertEqual(self.d["jobs"]["preflight"]["needs"], ["guard"])

    def test_the_jobs_that_could_write_are_skipped_by_the_warm_up_flag(self):
        # the caller must grant what the called workflow declares (contents: write), so the safety is the skip
        self.assertEqual(self.d["permissions"], {"contents": "write"})
        for job, body in JOBS.items():
            if (body.get("permissions") or {}).get("contents") == "write":
                self.assertIn("inputs.upload-artifact", str(body.get("if")), job)

    def test_every_publishing_step_of_the_build_has_the_upload_guard(self):
        for job, body in JOBS.items():
            for s in body.get("steps", []) or []:
                uses = s.get("uses") or ""
                if "action-gh-release" in uses:
                    self.assertIn("UPLOAD_ARTIFACT", str(s.get("if")), f"{job}: {s.get('name')}")

    def test_the_release_workflow_is_not_the_warm_up(self):
        self.assertIn("upload-artifact: true", RELEASE)
        self.assertNotIn("upload-artifact: false", RELEASE)


class SignUpdate(unittest.TestCase):
    job = JOBS["sign-update-metadata"]
    text = BUILD[BUILD.index("\n  sign-update-metadata:"):]

    def test_it_only_runs_for_a_stable_tag_that_was_published(self):
        cond = self.job["if"]
        self.assertIn("inputs.upload-artifact", cond)
        self.assertIn("!contains(inputs.upload-tag, '-')", cond)
        self.assertIn("build-for-windows-flutter", self.job["needs"])

    def test_it_signs_only_the_windows_installable_packages_of_our_repository(self):
        self.assertEqual(self.text.count("--artifact windows"), 4)
        self.assertNotIn("macos", self.text)
        self.assertNotIn("rustdesk/rustdesk", self.text)
        self.assertIn('https://github.com/${GITHUB_REPOSITORY}/releases/download', self.text)
        self.assertIn("--package-id rustdesk", self.text)

    def test_it_verifies_before_it_publishes_and_the_metadata_goes_last(self):
        n = [s.get("name") for s in self.job["steps"]]
        self.assertLess(n.index("Verify update metadata"), n.index("Attach the signature, then the metadata"))
        run = self.job["steps"][-1]["run"]
        self.assertLess(run.index("rustdesk-update.json.sig"), run.index("rustdesk-update.json "))

    def test_only_the_signing_step_reads_the_seed(self):
        self.assertEqual(BUILD.count("secrets.RUSTDESK_UPDATE_ED25519_SEED"), 2)  # validate-keys (upstream) + signing
        for s in self.job["steps"]:
            if "RUSTDESK_UPDATE_ED25519_SEED" in str(s.get("env")):
                self.assertEqual(s["name"], "Sign update metadata")

    def test_the_public_key_reaches_the_build_the_preflight_and_the_warm_up(self):
        self.assertIn('RUSTDESK_UPDATE_ED25519_PUBLIC_KEY: "${{ vars.RUSTDESK_UPDATE_ED25519_PUBLIC_KEY }}"', BUILD)
        for text in (RELEASE, WARM):
            self.assertIn("RUSTDESK_UPDATE_ED25519_PUBLIC_KEY: ${{ vars.RUSTDESK_UPDATE_ED25519_PUBLIC_KEY }}", text)

    def test_a_build_without_the_public_key_stops_before_compiling(self):
        self.assertIn("RUSTDESK_UPDATE_ED25519_PUBLIC_KEY is required", BUILD)


if __name__ == "__main__":
    unittest.main()
