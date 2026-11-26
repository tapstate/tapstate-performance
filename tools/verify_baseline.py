"""Verify the candidate bytes at a pushed performance data commit."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import urlopen

import baselines


RAW = "https://raw.githubusercontent.com/tapstate/tapstate-performance"


def fetch_bytes(url):
    with urlopen(url, timeout=20) as response:
        contents = response.read(baselines.MAX_BASELINE_BYTES + 1)
    if len(contents) > baselines.MAX_BASELINE_BYTES:
        raise ValueError("Remote baseline exceeds the supported read size")
    return contents


def verify(payload, commit, *, fetch=fetch_bytes):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Use the full data commit SHA")
    if len(payload) > baselines.MAX_BASELINE_BYTES:
        raise ValueError("Local baseline exceeds the supported read size")
    candidate = json.loads(payload)
    if candidate["kind"] != "accepted" or baselines.materialize(candidate) != candidate:
        raise ValueError("Use a complete accepted baseline with verified sample summaries")
    if not isinstance(candidate["id"], str) or not candidate["id"].strip() or not re.fullmatch(
            r"[0-9a-f]{40}", candidate["code_sha"]):
        raise ValueError("Invalid baseline identity or measured code SHA")
    environment, version = candidate["environment"], candidate["version"]
    if any(not re.fullmatch(r"[a-zA-Z0-9_.-]+", value) or value in (".", "..")
           for value in (environment, version)):
        raise ValueError("Invalid baseline environment or version")
    path = f"baselines/{environment}/{version}/baseline.json"
    downloaded = fetch(f"{RAW}/{commit}/{quote(path)}")
    if downloaded != payload:
        raise ValueError(f"Remote baseline bytes differ at {commit}:{path}")
    return {"id": candidate["id"], "environment": environment, "code_sha": candidate["code_sha"],
            "commit": commit, "path": path, "sha256": hashlib.sha256(downloaded).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("commit", help="Full Git commit containing the data")
    args = parser.parse_args()
    try:
        with args.candidate.open("rb") as stream:
            payload = stream.read(baselines.MAX_BASELINE_BYTES + 1)
        print(json.dumps(verify(payload, args.commit), sort_keys=True))
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.exit(1, f"Cannot verify the remote baseline: {error}\n")


if __name__ == "__main__":
    main()
