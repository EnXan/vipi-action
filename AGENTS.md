# Repository working agreement

This repository contains only the GitHub Action for
[VIPI](https://github.com/EnXan/VIPI). Scanner behavior, the CLI and the report
format belong to VIPI; this repository installs a released `vipi-scanner` and
wires it into GitHub workflows. The design is recorded in VIPI's
[ADR 0073](https://github.com/EnXan/VIPI/blob/main/adr-code/0073-github-action-in-its-own-repository.md).

## Working principles

- Use English for communication, UI text, messages, code comments and project
  documentation.
- Apply: **As much as necessary, as little as possible.** This applies equally to
  implementation, answers and documentation.
- Give reasoned pushback on questionable user decisions. Explain the concrete
  concern, supporting evidence and a simpler or better-supported alternative.
  Respect an explicit informed choice within the authorized task.
- Base decisions and factual claims on actual sources: GitHub's Actions
  documentation, VIPI's code and docs, and observed workflow runs. Distinguish
  requirements, observed behavior, proposals and unverified assumptions. Do not
  invent evidence or present inference as validation.
- Choose the simplest solution that meets current, evidenced requirements. Do
  not add speculative inputs, steps or safeguards "just in case".
- Do not introduce arbitrary limits, caps or truncation without a concrete,
  documented use case.
- Answer always in the same language as the user asked his question.

## Scope, planning and review

- Keep temporary plans, checklists and work queues under `.llm-plans/`; it is
  ignored by Git.
- Implement one agreed concept at a time. Verify it, show the result and its
  validation boundary, then stop for joint review before starting the next.
- Before editing, inspect `git status` and the relevant sources. Preserve
  existing work; do not combine unrelated cleanup with the current concept.
- Report what was actually verified and what remains untested. Only Ubuntu
  GitHub-hosted runners are tested; macOS, Windows and self-hosted runners are
  unverified until a run shows otherwise.
- Record important decisions about the Action (installation, defaults,
  compatibility, security) as an ADR in VIPI's `adr-code/` and link it here;
  avoid ADRs for routine edits.

## Action contract

- `action.yml` is the public interface. Within a major version (`v1`), do not
  remove or rename inputs or outputs, change defaults or change exit codes;
  such changes need a new major version.
- Keep the README's input, output and provider key tables in sync with
  `action.yml` in the same pull request.
- Treat every input as untrusted. Pass inputs and GitHub context values to
  scripts through `env:` and quote them; never interpolate `${{ ... }}`
  directly into `run:` scripts.
- Pin third-party actions to a full commit SHA with the version as a comment.
- Install VIPI only as a pinned `vipi-scanner` release from PyPI (`vipi-ref` is
  for testing). Use VIPI's public CLI and report fields only, never its Python
  internals.
- Prepare models only when `vipi scan --list-only` selects images; do not cache
  models (VIPI ADR 0070).
- Steps use `bash`; keep them working on Linux, macOS and Windows runners
  (for example the venv's `bin` or `Scripts` directory).

## Tests

- `.github/workflows/test.yml` must stay free and fast: no secrets, no model
  downloads, no paid requests. Build fixture Git repositories with
  `tests/fixture.sh` and assert on the report with `tests/check_report.py`.
- Add or update a fixture case for every behavior change. Images that should be
  selected run in cloud mode without keys, so they fail before OCR and appear as
  `not_scanned`.
- `scripts/summary.py` and `scripts/comment.py` use the Python standard library only and is tested with
  report fixtures in `tests/test_summary.py` and a fake GitHub API in
  `tests/test_comment.py`. Treat report text (paths,
  messages) as untrusted and escape it.
- Cases that need a non-PR event (such as `full-scan`) run on pushes and
  manual runs only.
- To test an unreleased VIPI change, run the workflow manually with `vipi-ref`.
- The `cloud-scan` job is the only real scan: manual, opt-in and paid. Run it
  only with the maintainer's approval, for example before a release that
  changes installation or the pinned `vipi-scanner` version.

## Contributing

- Work on a feature branch or fork and open a pull request targeting `main`.
- Name branches `feature/`, `fix/`, `doc/`, `refactor/`, `test/`, `ci/` or
  `chore/` followed by a short kebab-case name.
- Reference the GitHub issue in every pull request that addresses one:
  `Closes #N` when it resolves the issue, `Refs #N` for a partial step.
- Commit messages follow `<type>: <description>` with the types above.

## Releases

1. Release `vipi-scanner` to PyPI from the VIPI repository first.
2. Bump the `vipi-version` default in `action.yml` and the README in a pull
   request, and let the tests pass.
3. After merging, tag `vX.Y.Z` (patch: fixes or a new VIPI patch; minor: new
   inputs, outputs or behavior), create the GitHub release, and move `v1`:

```bash
git switch main
git pull --ff-only
git tag -a v1.1.0 -m "Release v1.1.0"
git tag -fa v1 -m "v1 → v1.1.0"
git push origin v1.1.0
git push --force origin v1
```

Moving `v1` is the only allowed force push. Never move a `vX.Y.Z` tag.
