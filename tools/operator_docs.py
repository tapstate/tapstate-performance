"""Render and validate the operator index from pinned baseline releases."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import quote

import baselines


RELEASES = Path("baselines/releases.json")
DOCS = Path("docs/operators")
BROWSE = "https://github.com/tapstate/tapstate-performance/blob"
PATH_PART = re.compile(r"[a-zA-Z0-9_.-]+")
OPERATOR = re.compile(r"[a-z][a-z0-9-]*")


def pinned_path(value):
    path = PurePosixPath(value)
    if (str(path) != value or len(path.parts) < 4 or path.parts[0] != "baselines"
            or any(part in (".", "..") or not PATH_PART.fullmatch(part) for part in path.parts)):
        raise ValueError(f"Invalid baseline repository path {value!r}")
    return path


def commit_of(release):
    commit = release["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid data commit in the release record")
    return commit


def git_blob(root, path, commit):
    reference = f"{commit}:{path}"
    command = ["git", "-C", str(root), "cat-file"]
    size = subprocess.run([*command, "-s", reference], check=True, capture_output=True, text=True)
    if int(size.stdout) > baselines.MAX_BASELINE_BYTES:
        raise ValueError(f"Baseline exceeds the supported read size at {reference}")
    return subprocess.run([*command, "blob", reference], check=True, capture_output=True).stdout


class Releases:
    def __init__(self, root):
        record = baselines.read_json(root / RELEASES)
        if (type(record.get("schema_version")) is not int or record["schema_version"] != 1
                or not isinstance(record.get("active"), dict) or not isinstance(record.get("versions"), dict)):
            raise ValueError("Invalid baseline release record")
        if not record["active"]:
            raise ValueError("No active baseline releases")
        self.root = root
        self.active = record["active"]
        self.versions = record["versions"]
        self.checked_evidence = set()

    def baseline(self, environment, version):
        release = self.versions[version]
        path = pinned_path(release["path"])
        if path.parts[1:3] != (environment, version) or release["environment"] != environment:
            raise ValueError(f"Wrong environment or version at {path}")
        commit = commit_of(release)
        payload = git_blob(self.root, path, commit)
        if hashlib.sha256(payload).hexdigest() != release["sha256"]:
            raise ValueError(f"Baseline digest mismatch at {path}")
        baseline = json.loads(payload)
        identity = {"id": release["id"], "environment": environment, "version": version,
                    "code_sha": release["code_sha"], "kind": "accepted"}
        if any(baseline.get(key) != expected for key, expected in identity.items()):
            raise ValueError(f"Baseline identity mismatch at {path}")
        if baselines.materialize(baseline) != baseline:
            raise ValueError(f"Baseline summaries differ from retained sample values at {path}")
        return baseline, f"{BROWSE}/{commit}/{quote(str(path))}"

    def evidence(self, environment, paths):
        references = []
        for value in dict.fromkeys(paths):
            path = pinned_path(value)
            version = path.parts[2]
            if path.parts[1] != environment or self.versions[version]["environment"] != environment:
                raise ValueError(f"Evidence has the wrong environment at {path}")
            commit = commit_of(self.versions[version])
            if (commit, path) not in self.checked_evidence:
                command = ["git", "-C", str(self.root), "cat-file", "-t", f"{commit}:{path}"]
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode or result.stdout.strip() != "blob":
                    raise ValueError(f"Missing pinned evidence file at {commit}:{path}")
                self.checked_evidence.add((commit, path))
            references.append(f"{BROWSE}/{commit}/{quote(str(path))}")
        return references


def cell(value):
    return str(value).replace("|", r"\|").replace("\n", " ")


def number(value):
    return str(value) if type(value) is int else format(value, ".12g")


def first_change(current, first, arm, metric, group, rules):
    if current == first:
        return "Same reference"
    if current["conditions"] != first["conditions"]:
        return "Incompatible conditions"
    binding = ("conditions", "scope", "source", "unit", "window_ref")
    previous = first["arms"].get(arm, {}).get("metrics", {}).get(metric, ())
    matches = [old for old in previous if old["availability"] == "measured"
               and all(old[key] == group[key] for key in binding)]
    if len(matches) != 1:
        return "Unavailable"
    origin = matches[0]["summary"]["median"]
    new = group["summary"]["median"]
    absolute = f"{number(new - origin)} {group['unit']}"
    if origin:
        return f"{new / origin - 1:+.2%} ({absolute})"
    return absolute if "zero_reference" in rules.get(metric, {}) else "Zero first value without an absolute rule"


def evidence_links(release, environment, paths, label):
    links = release.evidence(environment, paths)
    return ", ".join(f"[{label} {index}]({link})" for index, link in enumerate(links, 1))


def measured_line(release, environment, current, first, arm, metric, group, rules):
    label = f"`{arm}` / `{metric}`"
    if group["availability"] != "measured":
        return f"| {label} | {cell(group['reason'])} | | | |"
    summary = group["summary"]
    unit = group["unit"]
    bound_rows = group["conditions"].get("effective_input_rows", {})
    conditions = ", ".join(f"{table} {value:,}" for table, value in sorted(bound_rows.items()))
    scope = ", ".join(filter(None, (group["scope"], group["window_ref"], group["source"], conditions)))
    low, high = number(summary["min"]), number(summary["max"])
    spread = f"{low} to {high} {unit} · {summary['count']} repeats"
    change = first_change(current, first, arm, metric, group, rules)
    links = evidence_links(release, environment, (sample["evidence"] for sample in group["samples"]), "Repeat")
    return f"| {label}<br>{cell(scope)} | {number(summary['median'])} {unit} | {spread} | {change} | {links} |"


def provenance(measurement):
    date = measurement["measured_on"]
    run, attempt = measurement["run_id"], measurement["attempt"]
    return f"Measured {date} in run {run}, attempt {attempt}, at `{measurement['code_sha']}`."


def render_case(release, environment, case, rules):
    lines = [f"### `{case['case_id']}@{case['case_version']}`", ""]
    if case["status"] != "completed":
        links = evidence_links(release, environment, case["evidence"], "Evidence")
        return lines + [f"`{case['status']}` · {case['reason']}", "", provenance(case["measurement"]), "", links, ""]

    current = case["current"]
    first = current if case["first"] == "current" else case["first"]
    conditions = current["conditions"]
    runner = conditions["runner"]
    load = conditions["effective_load"]
    mode = conditions["mode"]
    context = [mode, conditions["scale"], f"{load['rows']:,} configured rows"]
    if mode == "live-latency" and "rate" in load and "measurement_seconds" in load:
        context.append(f"{load['rate']} events/s for {load['measurement_seconds']} s")
    if mode == "backlog-throughput" and "backlog_events" in load:
        context.append(f"{load['backlog_events']:,} backlog events")
    context.extend([runner["cpu"], runner["runner_image"], f"JDK {conditions['environment']['jdk']}"])
    lines += [" · ".join(context) + ".", "", provenance(current["measurement"]), ""]
    if first != current:
        paths = [sample["evidence"] for _, group in baselines.measurement_groups(first)
                 if group["availability"] == "measured" for sample in group["samples"]]
        links = evidence_links(release, environment, paths, "First evidence")
        lines.extend([f"First reference. {provenance(first['measurement'])}", "", links, ""])
    lines.extend(["| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |",
                  "|---|---|---|---|---|"])
    for arm, reading in sorted(current["arms"].items()):
        for metric, groups in sorted(reading["metrics"].items()):
            for group in groups:
                lines.append(measured_line(release, environment, current, first, arm, metric, group, rules))
    return lines + [""]


def render(root):
    release = Releases(root)
    by_operator = defaultdict(list)
    for environment, version in sorted(release.active.items()):
        baseline, url = release.baseline(environment, version)
        grouped = defaultdict(list)
        policy = baseline.get("comparison_rules", {})
        rules = policy.get("cases", {})
        for _, case in sorted(baseline["cases"].items()):
            operators = case["operators"]
            if not operators and case["case_id"].startswith("copy."):
                operators = ["copy"]
            if not operators or any(not OPERATOR.fullmatch(operator) for operator in operators):
                raise ValueError(f"Invalid operator names for {case['case_id']}")
            for operator in sorted(set(operators)):
                grouped[operator].append(case)
        for operator, cases in grouped.items():
            lines = [f"## `{environment}`", "", f"Baseline [`{version}`]({url}).", ""]
            if policy:
                lines.extend([f"Comparison rules `{policy['version']}`.", ""])
            for case in cases:
                lines += render_case(release, environment, case, rules.get(case["case_id"], {}))
            by_operator[operator].extend(lines)
    pages = {f"{name}.md": "\n".join([f"# {name.title()} performance", "", *lines])
             for name, lines in sorted(by_operator.items())}
    index = ["# Performance by operator", "", "[Baseline versions by environment](../../baselines/releases.json)", ""]
    index.extend(f"- [{name.title()}]({name}.md)" for name in sorted(by_operator))
    pages["README.md"] = "\n".join(index) + "\n"
    return pages


def apply_pages(root, pages, check):
    directory = root / DOCS
    unexpected = {path.name for path in directory.glob("*.md")} - pages.keys()
    if unexpected:
        raise ValueError(f"Stale operator pages {', '.join(sorted(unexpected))}")
    if not check:
        directory.mkdir(parents=True, exist_ok=True)
    for name, body in pages.items():
        path = directory / name
        if check:
            if path.read_bytes() != body.encode("utf-8"):
                raise ValueError(f"Stale operator documentation at {DOCS / name}")
        else:
            path.write_bytes(body.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Verify that the tracked pages match the release data")
    args = parser.parse_args()
    try:
        apply_pages(args.root, render(args.root), args.check)
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Cannot render operator documentation: {error}\n")


if __name__ == "__main__":
    main()
