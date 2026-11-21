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
        self.assertIn('VCPKG_BINARY_SOURCES: "clear;files,${{ runner.temp }}/vcpkg-binary-cache,readwrite"', BUILD)

    def test_every_vcpkg_job_restores_the_cache_between_setup_and_install(self):
        for job in ("build-for-windows-flutter", "build-for-macOS", "build-rustdesk-android"):
            n = names(job)
            a, b, c = (n.index(x) for x in ("Setup vcpkg with Github Actions binary cache",
                                             "Restore the vcpkg binary cache", "Install vcpkg dependencies"))
            self.assertTrue(a < b < c, job)

    def test_the_cache_key_changes_with_the_vcpkg_commit_and_the_target(self):
        keys = re.findall(r"key: (vcpkg-bin-[^\n]+)", BUILD)
        self.assertEqual(len(keys), 3)
        for k in keys:
            self.assertIn("env.VCPKG_COMMIT_ID", k)
            self.assertIn("matrix.job.vcpkg-triplet || matrix.job.target", k)

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

    def test_it_cannot_write_to_the_repository(self):
        self.assertEqual(self.d["permissions"], {"contents": "read"})

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
