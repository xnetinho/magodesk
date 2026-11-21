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
        self.assertEqual(BUILD.count('echo "VCPKG_BINARY_SOURCES=clear;files,${dir},readwrite" >> "$GITHUB_ENV"'), 3)
        self.assertNotRegex(BUILD, r"(?m)^  VCPKG_BINARY_SOURCES:")

    def test_every_vcpkg_job_restores_the_cache_between_setup_and_install(self):
        for job in ("build-for-windows-flutter", "build-for-macOS", "build-rustdesk-android"):
            n = names(job)
            a, p, b, c = (n.index(x) for x in ("Setup vcpkg with Github Actions binary cache",
                                                "Point vcpkg at the binary cache folder",
                                                "Restore the vcpkg binary cache", "Install vcpkg dependencies"))
            self.assertTrue(a < p < b < c, job)

    def test_the_cache_key_changes_with_the_vcpkg_commit_and_the_target(self):
        keys = re.findall(r"key: (vcpkg-bin-[^\n]+)", BUILD)
        self.assertEqual(len(keys), 3)
        for k in keys:
            self.assertIn("env.VCPKG_COMMIT_ID", k)
        # the Android matrix has no vcpkg-triplet, so it keys on the cargo target
        self.assertEqual(sorted(re.findall(r"matrix\.job\.(vcpkg-triplet|target)\b", "\n".join(keys))),
                         ["target", "vcpkg-triplet", "vcpkg-triplet"])

    def test_the_cache_action_is_pinned_to_a_commit(self):
        for ref in re.findall(r"uses: actions/cache@(\S+)", BUILD):
            self.assertRegex(ref, r"^[0-9a-f]{40}$")


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


if __name__ == "__main__":
    unittest.main()
