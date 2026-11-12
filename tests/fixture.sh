#!/usr/bin/env bash
# Build a Git fixture in the current directory: `main` (also as origin/main)
# and a checked-out `feature` branch, shaped by the test case.
set -euo pipefail
case_name="$1"

png() {
  mkdir -p "$(dirname "$1")"
  python3 - "$1" "$2" <<'PY'
import struct, sys, zlib
path, seed = sys.argv[1], int(sys.argv[2])
def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
row = b"\x00" + bytes([seed % 256, 0, 0]) * 8
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
png += chunk(b"IDAT", zlib.compress(row * 8)) + chunk(b"IEND", b"")
open(path, "wb").write(png)
PY
}

commit() {
  git add --all
  git -c user.name="VIPI test" -c user.email=vipi@example.test \
    -c commit.gpgsign=false commit --quiet --allow-empty -m "$1"
}

git init --quiet -b main .
echo "vipi-action/" >> .git/info/exclude
png base.png 1
case "$case_name" in
  base-rules) printf '*.png\n' > .vipiignore ;;
esac
commit base
git switch --quiet -c feature
case "$case_name" in
  empty-diff) echo "no images" > notes.txt ;;
  base-rules) png added.png 2 ;;
  branch-rules) printf '*.png\n' > .vipiignore; png added.png 2 ;;
  exclude-input) png keep.png 2; png generated/skip.png 3 ;;
  # Without a diff, every image in the worktree is selected; the worktree
  # .vipiignore applies, and the Action checkout is excluded from the scan.
  full-scan) png added.png 2; png skip.png 3; printf 'skip.png\nvipi-action/\n' > .vipiignore ;;
  *) echo "Unknown case: $case_name" >&2; exit 2 ;;
esac
commit feature
git update-ref refs/remotes/origin/main main
