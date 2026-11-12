"""Assert the Action's report for one fixture case (standard library only)."""

import json
import sys
from pathlib import Path

case, report_path, selected_output, scan_outcome = sys.argv[1:5]
report = json.loads(Path(report_path).read_text(encoding="utf-8"))
files = {Path(item["path"]).name: item["status"] for item in report["files"]}
user_skips = [item for item in report["skipped"] if item["reason"] == "excluded_by_user"]

expected = {
    # case: (selected files, user-excluded count, scan outcome)
    "empty-diff": ({}, 0, "success"),
    "base-rules": ({}, 1, "success"),
    # Remaining images run in cloud mode without keys: not scanned, exit 2.
    "branch-rules": ({"added.png": "not_scanned"}, 0, "failure"),
    "exclude-input": ({"keep.png": "not_scanned"}, 1, "failure"),
}[case]

failures = []
if files != expected[0]:
    failures.append(f"files {files} != {expected[0]}")
if len(user_skips) != expected[1]:
    failures.append(f"{len(user_skips)} user exclusions != {expected[1]}")
if int(selected_output) != len(expected[0]):
    failures.append(f"selected-images output {selected_output} != {len(expected[0])}")
if scan_outcome != expected[2]:
    failures.append(f"scan outcome {scan_outcome} != {expected[2]}")
if case == "base-rules" and user_skips[0]["source"] != "origin/main:.vipiignore":
    failures.append(f"rule source {user_skips[0]['source']!r}")
if failures:
    sys.exit(f"{case}: " + "; ".join(failures))
print(f"{case}: ok ({len(files)} selected, {len(user_skips)} excluded)")
