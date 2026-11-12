# VIPI Visual Prompt Injection Scan

GitHub Action for [VIPI](https://github.com/EnXan/VIPI): scans repository
images for visual prompt injections. It reads the text in each image with OCR,
re-reads unclear images, and checks the final text with an injection detector.
A finding fails the job.

## Usage

Scan the images a pull request adds or changes, in cloud mode:

```yaml
name: VIPI image scan
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: EnXan/vipi-action@v1
        with:
          modus: cloud
        env:
          GOOGLE_CLOUD_API_KEY: ${{ secrets.GOOGLE_CLOUD_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: vipi-report
          path: vipi-report.json
```

`fetch-depth: 0` is required: PR scans compare against the PR's base branch.
Outside PR events the Action scans all images under `paths`, unless `base-ref`
is set. Fork PRs normally get no secrets, so their cloud scans cannot reach the
providers.

The job exits with 0 when nothing was detected, 1 on a detection and 2 when a
scan is incomplete. Upload the report with `if: always()` to keep it in every
case.

> **Local mode on hosted runners:** standard GitHub-hosted runners have no GPU
> and too little memory for the local models. In our test, `balanced` took
> about 9 minutes for two images plus 2 minutes of setup, and `quality` could
> not load its model. Use cloud mode, or self-hosted or larger runners for
> local mode.

## Inputs

| Input | Default | Meaning |
| :-- | :-- | :-- |
| `paths` | `.` | Newline-separated image files or directories to scan |
| `base-ref` | Unset | Base branch for non-PR diff scans; PRs always use their actual base branch |
| `exclude` | Unset | Newline-separated exclusion rules, applied after `.vipiignore` |
| `modus` | `local` | Full scan execution: `local` or `cloud` |
| `ocr-mode` | `quality` | Local profile: `speed`, `balanced` or `quality`; ignored in cloud mode |
| `ocr-provider` | `google` | Cloud OCR: `google`, `openai` or `mistral`; ignored in local mode |
| `decision-provider` | Unset | Override the mode's decision model (local `clef-flash`/`d1`, cloud `openai`/`jev`) |
| `detector` | `auto` | Final text detector |
| `threshold` | `80` | Finding score on a 0–100 scale |
| `report-path` | `vipi-report.json` | JSON report path, also exposed as an output |
| `vipi-version` | Tested release | `vipi-scanner` version installed from PyPI |
| `vipi-ref` | Unset | Testing only: install VIPI from this Git ref of `EnXan/VIPI` |

Cloud providers need their own keys as environment variables; see
[credentials](https://github.com/EnXan/VIPI/blob/main/docs/cli.md#credentials-and-local-models).

## Outputs

| Output | Meaning |
| :-- | :-- |
| `selected-images` | Number of images selected for scanning |
| `report-path` | Path to the JSON report, including findings and scan errors |

## Excluding images

Put a [`.vipiignore`](https://github.com/EnXan/VIPI/blob/main/.vipiignore.example)
in the repository root, or pass rules with `exclude`. PR scans read
`.vipiignore` from the base branch, so a PR cannot exempt its own images; a
change to the file applies after it is merged. The `exclude` input comes from
the workflow file, which `pull_request` events take from the PR itself. See
[excluding images](https://github.com/EnXan/VIPI/blob/main/docs/cli.md#excluding-images).

## How it works

The Action installs a pinned `vipi-scanner` release from PyPI into an isolated
environment. It runs `vipi scan --list-only` first and prepares models only
when images are selected; models are downloaded each run and not cached.
Local mode installs the CPU builds of PyTorch on Linux and Windows.

## Versions

Use `@v1`; it moves to each compatible release. Each Action release pins one
tested `vipi-scanner` version. `vipi-version` lets you choose another release
at your own risk.

## Development

`.github/workflows/test.yml` runs the Action against fixture Git repositories
on every PR, without secrets or model downloads: an empty diff, rules from the
base branch, a rule change on the PR branch, and the `exclude` input. Images
that remain are run in cloud mode without keys, so they fail before OCR and the
test checks the report. Run the workflow manually with `vipi-ref` to test an
unreleased VIPI change.

Release: bump `vipi-version`'s default to the new PyPI release, let the tests
pass, tag `vX.Y.Z` and move `v1`.

## License

[Apache License 2.0](LICENSE)
