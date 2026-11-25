from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import baselines
import verify_baseline


class BaselinesTest(unittest.TestCase):
    fixture = json.loads((Path(__file__).parent / "fixtures" / "baseline-v2-contract.json").read_bytes())
    nest = "nest.snapshot.basic.standard"

    def test_materialize_recomputes_the_published_median(self):
        initial = deepcopy(self.fixture["initial"])
        group = initial["cases"][self.nest]["current"]["arms"]["single"]["metrics"]["startup.rss_peak_bytes"][0]
        group["summary"]["median"] = 1
        candidate = baselines.materialize(initial)
        self.assertEqual(self.fixture["initial"], candidate)
        self.assertEqual(1, group["summary"]["median"])

    def test_nest_update_retains_first_and_untouched_provenance(self):
        first = self.fixture["initial"]
        candidate = baselines.accepted_update(first, self.fixture["update"])
        for case_id in self.fixture["expected"]["unchanged"]:
            self.assertEqual(first["cases"][case_id], candidate["cases"][case_id])
        nest = candidate["cases"][self.nest]
        self.assertEqual(first["cases"][self.nest]["current"], nest["first"])
        self.assertEqual(self.fixture["update"]["measurements"][self.nest], nest["current"])
        self.assertEqual("current", first["cases"][self.nest]["first"])

    def test_incompatible_update_leaves_original_untouched(self):
        first = deepcopy(self.fixture["initial"])
        update = deepcopy(self.fixture["update"])
        update["measurements"][self.nest]["conditions"]["environment_profile"] = "http-cloud"
        with self.assertRaisesRegex(ValueError, "wrong environment"):
            baselines.accepted_update(first, update)
        self.assertEqual(self.fixture["initial"], first)

    def test_invalid_metric_domain_or_unit_is_rejected(self):
        for fault in ("unit", "negative"):
            initial = deepcopy(self.fixture["initial"])
            group = initial["cases"][self.nest]["current"]["arms"]["single"]["metrics"]["startup.rss_peak_bytes"][0]
            if fault == "unit":
                group["unit"] = "ms"
            else:
                group["samples"][0]["value"] = -1
            with self.subTest(fault=fault), self.assertRaisesRegex(ValueError, "Wrong unit|Negative observation"):
                baselines.materialize(initial)

    def test_remote_verification_binds_exact_data_commit_and_bytes(self):
        initial = deepcopy(self.fixture["initial"])
        initial["kind"] = "accepted"
        payload = baselines.encoded(initial)
        commit = "b" * 40
        expected_path = f"baselines/{initial['environment']}/{initial['version']}/baseline.json"
        requested = []

        def fetch(url):
            requested.append(url)
            return payload

        receipt = verify_baseline.verify(payload, commit, fetch=fetch)
        self.assertEqual([f"{verify_baseline.RAW}/{commit}/{expected_path}"], requested)
        self.assertEqual(commit, receipt["commit"])
        self.assertEqual(expected_path, receipt["path"])
        self.assertEqual(hashlib.sha256(payload).hexdigest(), receipt["sha256"])
        with self.assertRaisesRegex(ValueError, "Remote baseline bytes differ"):
            verify_baseline.verify(payload, commit, fetch=lambda _: payload + b" ")
        with self.assertRaisesRegex(ValueError, "full data commit SHA"):
            verify_baseline.verify(payload, "main", fetch=self.fail)
