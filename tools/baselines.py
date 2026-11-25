"""Build complete baseline candidates from selected measurements."""

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
from statistics import median


MAX_BASELINE_BYTES = 25_000_000
INCOMPLETE = ("failed", "measurement-incomplete", "invalid", "timed-out", "not-run", "out-of-memory", "skipped")


def measurement_references(case):
    if case["status"] in INCOMPLETE:
        if {"current", "first", "arms", "metrics"}.intersection(case):
            raise ValueError(f"Incomplete case {case['case_id']} carries numeric references")
        if not case.get("reason") or not case.get("evidence"):
            raise ValueError(f"Incomplete case {case['case_id']} needs a reason and evidence")
        return ()
    if case["status"] != "completed":
        raise ValueError(f"Unrecognized case status for {case['case_id']}")
    first = case["first"]
    return (case["current"],) if first == "current" else (case["current"], first)


def measurement_groups(reference):
    return ((metric, group) for arm in reference["arms"].values()
            for metric, groups in arm["metrics"].items() for group in groups)


def metric_unit(metric):
    units = (("_bytes_per_hour", "B/h"), ("_bytes", "B"), ("_ms", "ms"))
    return next((unit for ending, unit in units if metric.endswith(ending)), None)


def summarize(samples, metric):
    repeats = set()
    values = []
    for sample in samples:
        repeat, value = sample["repeat"], sample["value"]
        if type(repeat) is not int or repeat < 1 or repeat in repeats:
            raise ValueError("Each eligible sample requires a distinct repeat")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Eligible sample value must be finite")
        if metric_unit(metric) and not metric.endswith("_bytes_per_hour") and value < 0:
            raise ValueError(f"Negative observation for {metric}")
        if not sample["evidence"]:
            raise ValueError("An eligible sample needs retained evidence")
        repeats.add(repeat)
        values.append(value)
    if not values:
        raise ValueError("A measured group needs at least one eligible sample")
    low, high = min(values), max(values)
    result = {"count": len(values), "median": median(values), "min": low, "max": high, "range": high - low}
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("The sample summary must be finite")
    return result


def refresh_summaries(reference):
    for metric, group in measurement_groups(reference):
        availability = group["availability"]
        if availability == "measured":
            unit = metric_unit(metric)
            if unit and group["unit"] != unit:
                raise ValueError(f"Wrong unit for {metric}")
            group["summary"] = summarize(group["samples"], metric)
        elif availability not in ("unavailable", "not_applicable") or not group.get("reason"):
            raise ValueError("Unmeasured metrics need a status and a reason")
        elif {"summary", "value", "samples"}.intersection(group):
            raise ValueError("Unmeasured metrics cannot carry a numeric reference")


def materialize(selection):
    candidate = deepcopy(selection)
    if candidate.get("schema_version") != 2 or candidate.get("kind") not in ("accepted", "fixture"):
        raise ValueError("Unsupported baseline candidate format")
    if not candidate["cases"]:
        raise ValueError("A baseline needs a complete case selection")
    for case_id, case in candidate["cases"].items():
        if case["case_id"] != case_id:
            raise ValueError(f"Case identity mismatch for {case_id}")
        for reference in measurement_references(case):
            if reference["conditions"]["environment_profile"] != candidate["environment"]:
                raise ValueError(f"Reference has the wrong environment for {case_id}")
            refresh_summaries(reference)
    return candidate


def accepted_update(active, update):
    """Replace only selected accepted cases in a new complete version."""
    candidate = materialize(active)
    if candidate != active:
        raise ValueError("The active baseline does not match its retained measurements")
    if not update["version"] or update["version"] == active["version"] or not update["measurements"]:
        raise ValueError("An update requires a new version and at least one measurement")
    candidate.update(version=update["version"], code_sha=update["code_sha"])
    for case_id, selected in update["measurements"].items():
        case = candidate["cases"].get(case_id)
        if not case:
            raise ValueError(f"Update targets a case outside the initial selection: {case_id}")
        if selected["conditions"]["environment_profile"] != candidate["environment"]:
            raise ValueError(f"Update has the wrong environment for {case_id}")
        if selected["measurement"]["code_sha"] != update["code_sha"]:
            raise ValueError(f"Update measurement code identity mismatch for {case_id}")
        previous = case["current"]["measurement"] if case["status"] == "completed" else case["measurement"]
        if selected["measurement"]["measured_on"] < previous["measured_on"]:
            raise ValueError(f"Update predates the current measurement for {case_id}")
        if case["status"] != "completed":
            case = {"case_id": case_id, "operators": case.get("operators", []), "status": "completed", "first": "current"}
            candidate["cases"][case_id] = case
        elif case["first"] == "current":
            case["first"] = case["current"]
        case["current"] = deepcopy(selected)
        case["case_version"] = selected["conditions"]["case_version"]
        refresh_summaries(case["current"])
    return candidate


def encoded(candidate):
    payload = (json.dumps(candidate, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if len(payload) > MAX_BASELINE_BYTES:
        raise ValueError("Baseline exceeds the supported read size")
    return payload


def read_json(path):
    with path.open("rb") as stream:
        contents = stream.read(MAX_BASELINE_BYTES + 1)
    if len(contents) > MAX_BASELINE_BYTES:
        raise ValueError(f"Input exceeds the supported size: {path}")
    return json.loads(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--update", type=Path, help="A reviewed replacement for selected cases")
    args = parser.parse_args()
    try:
        selection = read_json(args.selection)
        candidate = accepted_update(selection, read_json(args.update)) if args.update else materialize(selection)
        payload = encoded(candidate)
        with args.output.open("xb") as stream:
            stream.write(payload)
    except (KeyError, TypeError, ValueError, OSError, OverflowError) as error:
        parser.exit(1, f"Cannot generate candidate: {error}\n")


if __name__ == "__main__":
    main()
