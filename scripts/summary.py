"""Render a VIPI JSON report as a Markdown job summary (standard library only).

Usage: python summary.py REPORT_PATH >> "$GITHUB_STEP_SUMMARY"
"""

import html
import json
import os
import sys
from pathlib import Path

# GitHub rejects a step summary above 1 MiB; larger reports get shorter views.
SUMMARY_LIMIT_BYTES = 1024 * 1024
MARKDOWN_SPECIAL = set("\\`*_{}[]()#+-.!|~")
RESULTS = {
    "injection_detected": "🚨 Injection detected",
    "no_injection_detected": "✅ No injection detected",
    None: "⚠️ No result",
}
HEADLINES = {
    0: "✅ No injection detected",
    1: "🚨 Injection detected",
    2: "⚠️ Scan incomplete",
}


def text(value):
    """Escape untrusted text (paths, messages) for Markdown and HTML."""
    value = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ⏎ ")
    escaped = "".join("\\" + char if char in MARKDOWN_SPECIAL else char for char in value)
    return html.escape(escaped, quote=False)


def display_path(path):
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if workspace:
        try:
            return Path(path).relative_to(workspace).as_posix()
        except ValueError:
            pass
    return str(path)


def score(value):
    return "–" if value is None else f"{round(value * 100, 1):g}"


def file_note(item):
    notes = []
    if item.get("status") == "not_scanned":
        notes.append("not scanned")
    if item.get("ocr_incomplete") is True:
        notes.append("text may be missing from OCR")
    notes.extend(text(error) for error in item.get("errors", []))
    return "; ".join(notes)


def file_table(files):
    rows = ["| Image | Result | Score | Threshold | Notes |", "| :-- | :-- | --: | --: | :-- |"]
    for item in files:
        rows.append(
            "| {} | {} | {} | {} | {} |".format(
                text(display_path(item["path"])),
                RESULTS.get(item.get("verdict"), RESULTS[None]),
                score(item.get("injection_probability")),
                score(item.get("threshold")),
                file_note(item),
            )
        )
    return rows


def render(report, *, detail="full"):
    summary = report.get("summary", {})
    files = report.get("files", [])
    headline = HEADLINES.get(report.get("exit_code"), "⚠️ Unknown result")
    if not files and report.get("exit_code") == 0:
        headline = "✅ No images to scan"
    lines = [f"## VIPI scan: {headline}", ""]
    # Only user exclusions are shown; non-image files and built-in exclusions
    # (for example .git) stay in the JSON report.
    excluded = [item for item in report.get("skipped", []) if item.get("reason") == "excluded_by_user"]
    lines += [
        "| Selected | Completed | Detections | OCR may be incomplete | Failed | Not scanned | Excluded |",
        "| --: | --: | --: | --: | --: | --: | --: |",
        "| {} | {} | {} | {} | {} | {} | {} |".format(
            *(summary.get(key, 0) for key in (
                "selected", "completed", "detections", "ocr_incomplete",
                "failed", "not_scanned",
            )),
            len(excluded),
        ),
        "",
    ]
    findings = [item for item in files if item.get("verdict") == "injection_detected"]
    if findings and detail != "counts":
        lines += ["### Findings", "", *file_table(findings), ""]
    errors = [text(error.get("error", error) if isinstance(error, dict) else error)
              for error in report.get("errors", [])]
    if errors and detail != "counts":
        lines += ["### Errors", "", *(f"- {error}" for error in errors), ""]
    if files and detail == "full":
        lines += ["### Selected images", "", *file_table(files), ""]
    if excluded and detail == "full":
        lines += [f"<details><summary>Excluded by your rules ({len(excluded)})</summary>", ""]
        for item in excluded:
            lines.append(f"- {text(display_path(item['path']))} (rule {text(item.get('rule', ''))})")
        lines += ["", "</details>", ""]
    if detail != "full":
        lines += ["The full results are too long to show here; see the JSON report.", ""]
    lines += ["OCR text is not shown here; it is in the JSON report.", ""]
    return "\n".join(lines)


def main(argv, *, limit=SUMMARY_LIMIT_BYTES):
    path = Path(argv[1])
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return (
            "## VIPI scan: ⚠️ No report\n\n"
            f"The scan stopped before writing {text(path)}. See the step log.\n"
        )
    for detail in ("full", "compact", "counts"):
        output = render(report, detail=detail)
        if len(output.encode("utf-8")) <= limit:
            return output
    return output


if __name__ == "__main__":
    sys.stdout.write(main(sys.argv))
