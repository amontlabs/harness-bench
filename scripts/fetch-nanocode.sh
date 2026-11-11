#!/bin/sh
# Download the pinned official nanocode release binary for x86_64 Linux and verify it.
# The rolling `nanocode-cli` release is what `curl https://nanocode.xyz/install | sh`
# installs; this pins the build published 2026-11-06 (tag commit d7a4990).
set -eu
cd "$(dirname "$0")/.."
URL=https://github.com/nanocodexyz/nanocode/releases/download/nanocode-cli/nanocode-x86_64-unknown-linux-gnu.gz
SHA256=a5305c5a052d424d331a6d558c7d7820a0af1ef1c94c27a1c2f1682598bd7754
mkdir -p vendor
curl -fsSL "$URL" -o vendor/nanocode.gz
echo "$SHA256  vendor/nanocode.gz" | sha256sum -c -
gunzip -f vendor/nanocode.gz
chmod 755 vendor/nanocode
sha256sum vendor/nanocode
