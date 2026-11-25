from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import baselines
import operator_docs


class OperatorDocsTest(unittest.TestCase):
    fixture = json.loads((Path(__file__).parent / "fixtures" / "baseline-v2-contract.json").read_bytes())

    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Baseline Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.initial = deepcopy(self.fixture["initial"])
        self.initial["kind"] = "accepted"
        self.initial["cases"]["copy.live.basic.standard"]["operators"] = []
        self.releases = {"schema_version": 1, "active": {}, "versions": {}}

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def write(self, path, body):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def record(self, baseline, *, missing=None, published_environment=None):
        environment, version = baseline["environment"], baseline["version"]
        for case in baseline["cases"].values():
            if case["status"] == "completed":
                paths = [sample["evidence"] for ref in baselines.measurement_references(case)
                         for _, group in baselines.measurement_groups(ref)
                         if group["availability"] == "measured" for sample in group["samples"]]
            else:
                paths = case["evidence"]
            for path in paths:
                if path != missing and not (self.root / path).exists():
                    self.write(path, b"{}\n")
        path = f"baselines/{environment}/{version}/baseline.json"
        payload = baselines.encoded(baseline)
        self.write(path, payload)
        self.git("add", "baselines")
        self.git("commit", "-qm", f"Add {version}")
        commit = self.git("rev-parse", "HEAD")
        self.releases["versions"][version] = {
            "id": baseline["id"], "environment": environment, "code_sha": baseline["code_sha"],
            "path": path, "sha256": hashlib.sha256(payload).hexdigest(), "commit": commit,
        }
        self.releases["active"][published_environment or environment] = version
        self.write(operator_docs.RELEASES, json.dumps(self.releases).encode())
        return commit

    def test_pinned_update_renders_nest_and_preserves_copy_and_join(self):
        initial_commit = self.record(self.initial)
        update = deepcopy(self.fixture["update"])
        nest_id = "nest.snapshot.basic.standard"
        next_baseline = baselines.accepted_update(self.initial, update)
        next_baseline["cases"][nest_id]["operators"].append("join")
        next_commit = self.record(next_baseline)

        pages = operator_docs.render(self.root)
        self.assertIn("[Nest](nest.md)", pages["README.md"])
        self.assertIn(f"`{nest_id}@1`", pages["nest.md"])
        self.assertIn(f"`{nest_id}@1`", pages["join.md"])
        self.assertIn(f"{next_commit}/baselines/", pages["nest.md"])
        self.assertIn(f"{initial_commit}/baselines/", pages["nest.md"])
        self.assertIn("First reference. Measured 2026-01-01", pages["nest.md"])
        self.assertIn("Measured 2026-01-02", pages["nest.md"])
        self.assertIn("| 402653184 B | 401604608 to 403701760 B", pages["nest.md"])
        self.assertIn("-6.80% (-29360128 B)", pages["nest.md"])
        self.assertIn("Measured 2026-01-01", pages["copy.md"])
        self.assertIn("`measurement-incomplete`", pages["copy.md"])
        self.assertIn("Only an upper bound was observed.", pages["copy.md"])
        operator_docs.apply_pages(self.root, pages, check=False)
        operator_docs.apply_pages(self.root, pages, check=True)
        self.write(operator_docs.DOCS / "nest.md", b"Stale median\n")
        with self.assertRaisesRegex(ValueError, "Stale operator documentation"):
            operator_docs.apply_pages(self.root, operator_docs.render(self.root), check=True)

    def test_zero_first_reference_needs_an_explicit_absolute_rule(self):
        share = self.initial["cases"]["nest.snapshot.basic.standard"]["current"]
        metric = "lifecycle.idle_rss_retained_bytes"
        first = deepcopy(share)
        old = first["arms"]["single"]["metrics"].pop("startup.rss_peak_bytes")
        first["arms"]["single"]["metrics"][metric] = old
        old[0]["summary"]["median"] = 0
        current = deepcopy(first)
        group = current["arms"]["single"]["metrics"][metric][0]
        group["summary"]["median"] = 1024
        rules = {metric: {"zero_reference": {"observe_absolute": 512, "suspect_absolute": 1024}}}
        self.assertIn("without an absolute rule", operator_docs.first_change(current, first, "single", metric,
                                                                            group, {}))
        self.assertEqual("1024 B", operator_docs.first_change(current, first, "single", metric, group, rules))

    def test_missing_blob_is_rejected_even_when_added_after_data_commit(self):
        missing = self.initial["cases"]["copy.live.basic.standard"]["evidence"][0]
        self.record(self.initial, missing=missing)
        self.write(missing, b"{}\n")
        with self.assertRaisesRegex(ValueError, "Missing pinned evidence file"):
            operator_docs.render(self.root)

    def test_wrong_active_environment_is_rejected(self):
        self.record(self.initial, published_environment="http-cloud")
        with self.assertRaisesRegex(ValueError, "Wrong environment"):
            operator_docs.render(self.root)

    def test_wrong_case_version_is_rejected(self):
        nest = self.initial["cases"]["nest.snapshot.basic.standard"]
        nest["case_version"] = 99
        with self.assertRaisesRegex(ValueError, "Current measurement case version mismatch"):
            baselines.materialize(self.initial)

    def test_stale_baseline_value_is_rejected(self):
        nest = self.initial["cases"]["nest.snapshot.basic.standard"]
        nest["current"]["arms"]["single"]["metrics"]["startup.rss_peak_bytes"][0]["summary"]["median"] = 7
        self.record(self.initial)
        with self.assertRaisesRegex(ValueError, "Baseline summaries differ"):
            operator_docs.render(self.root)
