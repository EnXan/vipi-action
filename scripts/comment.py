"""Post or update the scan summary as a pull request comment (standard library only).

Usage: python comment.py REPORT_PATH
Environment: GITHUB_TOKEN, GITHUB_API_URL, GITHUB_REPOSITORY, GITHUB_EVENT_PATH.
A failure only prints a workflow warning; it never changes the scan result.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import summary  # noqa: E402

MARKER = "<!-- vipi-action-report -->"
# Reported limit for comment bodies: 65,536 characters; bytes bound characters.
COMMENT_LIMIT_BYTES = 65536 - len(MARKER) - 2


def github_api(method, url, token, payload=None):
    request = urllib.request.Request(
        url,
        method=method,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "vipi-action",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"null")


def pull_request_number(event_path):
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return (event.get("pull_request") or {}).get("number")


def has_results(report_path):
    """False only for a readable report without selected images or errors."""
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    return bool(report.get("files") or report.get("errors"))


def marked_comments(api, base, number, token):
    """Marked comments, bot-authored first (the Action's own come from a bot)."""
    found, page = [], 1
    while True:
        comments = api("GET", f"{base}/issues/{number}/comments?per_page=100&page={page}", token)
        found += [c for c in comments if c.get("body", "").startswith(MARKER)]
        if len(comments) < 100:
            break
        page += 1
    found.sort(key=lambda c: (c.get("user") or {}).get("type") != "Bot")
    return [c["id"] for c in found]


def update_own_comment(api, base, number, token, body):
    """Update the first marked comment this token may edit; others are skipped."""
    for comment_id in marked_comments(api, base, number, token):
        try:
            api("PATCH", f"{base}/issues/comments/{comment_id}", token, {"body": body})
            return True
        except urllib.error.HTTPError as error:
            # Anyone can copy the marker; comments by other users are not ours.
            if error.code not in (403, 404):
                raise
    return False


def post(report_path, environ, api=github_api):
    """Return a message for the log; raise urllib errors to the caller."""
    number = pull_request_number(environ["GITHUB_EVENT_PATH"])
    if number is None:
        return "notice", "pr-comment only applies to pull request events."
    token = environ["GITHUB_TOKEN"]
    base = f"{environ.get('GITHUB_API_URL', 'https://api.github.com')}/repos/{environ['GITHUB_REPOSITORY']}"
    body = f"{MARKER}\n{summary.main(['summary.py', report_path], limit=COMMENT_LIMIT_BYTES)}"
    if update_own_comment(api, base, number, token, body):
        return "notice", f"Updated the VIPI comment on pull request #{number}."
    if not has_results(report_path):
        return "notice", "No images selected; no comment posted."
    api("POST", f"{base}/issues/{number}/comments", token, {"body": body})
    return "notice", f"Posted the VIPI comment on pull request #{number}."


def main(argv, environ=os.environ, api=github_api):
    try:
        level, message = post(argv[1], environ, api)
    except urllib.error.HTTPError as error:
        hint = (
            " The workflow needs 'permissions: pull-requests: write'; pull requests"
            " from forks only get a read-only token."
            if error.code in (401, 403, 404)
            else ""
        )
        level, message = "warning", f"Could not post the PR comment (HTTP {error.code}).{hint}"
    except (OSError, ValueError, KeyError) as error:
        level, message = "warning", f"Could not post the PR comment: {error}"
    print(f"::{level} title=VIPI::{message}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
