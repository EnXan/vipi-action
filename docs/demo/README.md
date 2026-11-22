# README demo

The screenshots in the main README come from a real run, not a mock:
[pull request #1](https://github.com/EnXan/vipi-action-demo/pull/1) in
[`EnXan/vipi-action-demo`](https://github.com/EnXan/vipi-action-demo), whose
workflow is the README example with `pr-comment: true` (default cloud mode,
Google Cloud Vision and OpenAI). The PR adds three images:
`visible-injection.png` and `hidden-injection.png` from VIPI's
[sample images](https://github.com/EnXan/VIPI/tree/main/examples) and
`benign.png` from this repository's [test images](../../tests/images).

Captured on 2026-11-22 from workflow run
[45006825163](https://github.com/EnXan/vipi-action-demo/actions/runs/45006825163):

- `pr-scroll.gif`: a scripted scroll through the PR page, signed out, from the
  top to the VIPI comment (11 screenshots, about 6 seconds; not a screen
  recording, so nothing is cut);
- `pr-checks.png`: the PR's checks with the failing VIPI scan (first attempt,
  vipi-action v2.0.0);
- `pr-comment.png`: the comment the Action posted on the PR (second attempt,
  re-run with vipi-action v2.1.0, which leaves images without findings out of
  the comment).

Both attempts used vipi-scanner 0.14.1 and gave the same verdicts.
The PR first added VIPI's `clean.png`, which the first run
([45006701016](https://github.com/EnXan/vipi-action-demo/actions/runs/45006701016))
reported as an injection (score 89, threshold 80); it was replaced with
`benign.png` and the run repeated. Screenshots are cropped, not edited.

To reproduce: push a commit to the demo PR or re-run its latest workflow run (needs the repository secrets
`GOOGLE_CLOUD_API_KEY` and `OPENAI_API_KEY`; about $0.01 per run), wait for
the run, then:

- `pr-checks.png`: signed in, light theme, a macOS screenshot (Cmd+Shift+4)
  of the PR's check box, cropped below the GitGuardian row (GitHub only shows
  this box to signed-in users);
- `pr-comment.png` and `pr-scroll.gif`: signed out, with Chrome and ffmpeg
  installed:

```bash
npm i playwright-core
node docs/demo/capture.js /tmp/vipi-demo
cp /tmp/vipi-demo/pr-comment.png docs/demo/
cd /tmp/vipi-demo/frames
{ echo "file 'f000.png'"; echo "duration 1.5"
  for i in 001 002 003 004 005 006 007 008 009; do echo "file 'f$i.png'"; echo "duration 0.08"; done
  echo "file 'f010.png'"; echo "duration 3.5"; echo "file 'f010.png'"; } > list.txt
ffmpeg -f concat -safe 0 -i list.txt -loop 0 -vf "scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" pr-scroll.gif
```
