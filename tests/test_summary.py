"""Tests for scripts/summary.py with saved report shapes (no VIPI install needed)."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "summary", Path(__file__).parents[1] / "scripts" / "summary.py"
)
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def scanned(name, verdict, probability, **extra):
    return {
        "path": f"/work/repo/{name}",
        "status": "completed",
        "verdict": verdict,
        "injection_probability": probability,
        "threshold": 0.8,
        "ocr_incomplete": False,
        **extra,
    }


def report(files, *, exit_code, skipped=(), errors=()):
    counts = {
        "selected": len(files),
        "completed": sum(f["status"] == "completed" for f in files),
        "detections": sum(f.get("verdict") == "injection_detected" for f in files),
        "ocr_incomplete": sum(f.get("ocr_incomplete") is True for f in files),
        "failed": sum(f["status"] == "error" for f in files),
        "not_scanned": sum(f["status"] == "not_scanned" for f in files),
        "skipped": len(skipped),
    }
    return {
        "files": files,
        "skipped": list(skipped),
        "errors": list(errors),
        "summary": counts,
        "exit_code": exit_code,
    }


def render(data, **kwargs):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "report.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return summary.main(["summary.py", str(path)], **kwargs)


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(summary.os.environ.pop, "GITHUB_WORKSPACE", None)
        summary.os.environ["GITHUB_WORKSPACE"] = "/work/repo"

    def test_clean_scan(self):
        output = render(report([scanned("logo.png", "no_injection_detected", 0.02)], exit_code=0))
        self.assertIn("## VIPI scan: ✅ No injection detected", output)
        self.assertIn("| logo\\.png | ✅ No injection detected | 2 | 80 |  |", output)
        self.assertNotIn("### Findings", output)

    def test_finding_is_listed_and_ocr_incomplete_is_marked(self):
        files = [
            scanned("bad.png", "injection_detected", 1.0),
            scanned("doubt.png", "no_injection_detected", 0.1, ocr_incomplete=True),
        ]
        output = render(report(files, exit_code=1))
        self.assertIn("## VIPI scan: 🚨 Injection detected", output)
        findings = output.split("### Findings")[1].split("###")[0]
        self.assertIn("bad\\.png", findings)
        self.assertNotIn("doubt", findings)
        self.assertIn("text may be missing from OCR", output)

    def test_errors_and_not_scanned_files(self):
        files = [{"path": "/work/repo/a.png", "status": "not_scanned"},
                 {"path": "/work/repo/b.png", "status": "error", "verdict": None,
                  "errors": ["Detector refused"]}]
        output = render(report(files, exit_code=2, errors=[{"error": "Set OPENAI_API_KEY"}]))
        self.assertIn("## VIPI scan: ⚠️ Scan incomplete", output)
        self.assertIn("- Set OPENAI\\_API\\_KEY", output)
        self.assertIn("not scanned", output)
        self.assertIn("Detector refused", output)

    def test_empty_selection_and_skipped_inputs(self):
        skipped = [{"path": "/work/repo/gen/x.png", "reason": "excluded_by_user", "rule": "gen/"}]
        output = render(report([], exit_code=0, skipped=skipped))
        self.assertIn("## VIPI scan: ✅ No images to scan", output)
        self.assertIn("<summary>Skipped inputs (1)</summary>", output)
        self.assertIn("gen/x\\.png: excluded\\_by\\_user (rule gen/)", output)

    def test_missing_report(self):
        output = summary.main(["summary.py", "/nonexistent/vipi-report.json"])
        self.assertIn("## VIPI scan: ⚠️ No report", output)

    def test_untrusted_paths_cannot_break_markdown_or_inject_html(self):
        name = "a|b*c`d\n## heading <img src=x onerror=alert(1)>.png"
        output = render(report([scanned(name, "injection_detected", 1.0)], exit_code=1))
        row = next(line for line in output.splitlines() if "onerror" in line)
        self.assertEqual(row.count(" | "), 4)
        self.assertNotIn("<img", output)
        self.assertNotIn("\n## heading", output)
        self.assertIn("a\\|b\\*c\\`d ⏎ \\#\\# heading &lt;img", row)

    def test_large_report_falls_back_to_shorter_views(self):
        files = [scanned(f"image-{index}.png", "no_injection_detected", 0.0) for index in range(200)]
        files.append(scanned("bad.png", "injection_detected", 1.0))
        full = render(report(files, exit_code=1))
        compact = render(report(files, exit_code=1), limit=len(full.encode()) - 1)
        self.assertNotIn("### Selected images", compact)
        self.assertIn("bad\\.png", compact)
        self.assertIn("too long for a job summary", compact)
        counts = render(report(files, exit_code=1), limit=300)
        self.assertNotIn("### Findings", counts)


if __name__ == "__main__":
    unittest.main()
