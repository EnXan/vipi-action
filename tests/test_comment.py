"""Tests for scripts/comment.py with a fake GitHub API (no network)."""

import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path

scripts = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location("comment", scripts / "comment.py")
comment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comment)


class FakeApi:
    def __init__(self, comments=(), refuse=(), status=None):
        self.comments = [dict(c) for c in comments]
        self.refuse, self.status, self.calls = set(refuse), status, []

    def __call__(self, method, url, token, payload=None):
        self.calls.append((method, url))
        if self.status:
            raise urllib.error.HTTPError(url, self.status, "error", None, None)
        if method == "GET":
            page = int(url.rsplit("page=", 1)[1])
            return self.comments[(page - 1) * 100 : page * 100]
        if method == "PATCH":
            comment_id = int(url.rsplit("/", 1)[1])
            if comment_id in self.refuse:
                raise urllib.error.HTTPError(url, 403, "forbidden", None, None)
            next(c for c in self.comments if c["id"] == comment_id)["body"] = payload["body"]
            return {}
        self.comments.append({"id": 999, "body": payload["body"]})
        return {}


class CommentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.event = self.root / "event.json"
        self.event.write_text(json.dumps({"pull_request": {"number": 7}}))
        self.env = {
            "GITHUB_TOKEN": "token",
            "GITHUB_API_URL": "https://api.github.test",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_EVENT_PATH": str(self.event),
        }

    def report(self, files=(), errors=()):
        path = self.root / "report.json"
        path.write_text(json.dumps({
            "files": list(files), "errors": list(errors), "skipped": [],
            "summary": {"selected": len(files)}, "exit_code": 1 if files else 0,
        }))
        return str(path)

    def run_main(self, report, api):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(comment.main(["comment.py", report], self.env, api), 0)
        return output.getvalue()

    def finding(self):
        return [{"path": "bad.png", "status": "completed", "verdict": "injection_detected",
                 "injection_probability": 1.0, "threshold": 0.8}]

    def test_creates_one_marked_comment(self):
        api = FakeApi()
        log = self.run_main(self.report(self.finding()), api)
        self.assertEqual(len(api.comments), 1)
        self.assertTrue(api.comments[0]["body"].startswith(comment.MARKER))
        self.assertIn("Injection detected", api.comments[0]["body"])
        self.assertIn("Posted", log)

    def test_updates_existing_comment_instead_of_adding(self):
        api = FakeApi([{"id": 1, "body": "hello"}, {"id": 2, "body": comment.MARKER + "\nold"}])
        self.run_main(self.report(self.finding()), api)
        self.assertEqual(len(api.comments), 2)
        self.assertIn("Injection detected", api.comments[1]["body"])

    def test_skips_marked_comments_it_may_not_edit(self):
        api = FakeApi([{"id": 1, "body": comment.MARKER + "\nfake"}], refuse={1})
        self.run_main(self.report(self.finding()), api)
        self.assertEqual([c["id"] for c in api.comments], [1, 999])

    def test_finds_comment_on_a_later_page(self):
        comments = [{"id": i, "body": "x"} for i in range(100)]
        api = FakeApi([*comments, {"id": 500, "body": comment.MARKER}])
        self.run_main(self.report(self.finding()), api)
        self.assertIn("Injection detected", api.comments[-1]["body"])

    def test_no_new_comment_without_selected_images(self):
        api = FakeApi()
        log = self.run_main(self.report(), api)
        self.assertEqual(api.comments, [])
        self.assertIn("no comment posted", log)

    def test_existing_comment_is_updated_when_images_are_gone(self):
        api = FakeApi([{"id": 3, "body": comment.MARKER + "\nold finding"}])
        self.run_main(self.report(), api)
        self.assertIn("No images to scan", api.comments[0]["body"])

    def test_non_pull_request_event_is_a_notice(self):
        self.event.write_text(json.dumps({"ref": "refs/heads/main"}))
        api = FakeApi()
        log = self.run_main(self.report(self.finding()), api)
        self.assertEqual(api.calls, [])
        self.assertIn("::notice", log)

    def test_permission_error_is_only_a_warning(self):
        log = self.run_main(self.report(self.finding()), FakeApi(status=403))
        self.assertIn("::warning", log)
        self.assertIn("pull-requests: write", log)

    def test_body_respects_comment_limit(self):
        files = [{"path": f"image-{i}-{'x' * 200}.png", "status": "completed",
                  "verdict": "no_injection_detected", "injection_probability": 0.0,
                  "threshold": 0.8} for i in range(1000)]
        api = FakeApi()
        self.run_main(self.report(files), api)
        self.assertLessEqual(len(api.comments[0]["body"]), 65536)
        self.assertIn("too long to show here", api.comments[0]["body"])


if __name__ == "__main__":
    unittest.main()
