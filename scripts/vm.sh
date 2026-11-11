#!/bin/sh
# Create the benchmark microVM on an x86_64 Linux host with KVM (microsandbox), with a
# Docker daemon inside, and install the pinned Harbor in it.
#
#   scripts/vm.sh up      create the VM, mount this repo at /bench, start Docker, install Harbor
#   scripts/vm.sh shell   open a shell in the VM
#   scripts/vm.sh down    remove the VM (and everything Docker pulled inside it)
#
# The VM has internet access (Terminal-Bench verifiers and tasks download packages, as
# in the official runs). It sees nothing of the host except this repository.
set -eu
NAME=${BENCH_VM:-benchvm}
REPO=$(cd "$(dirname "$0")/.." && pwd)
CPUS=${BENCH_VM_CPUS:-12}
MEMORY=${BENCH_VM_MEMORY:-12G}
DISK=${BENCH_VM_DISK:-80G}
# docker:dind (Docker 29.9.3), pinned by index digest.
IMAGE=${BENCH_VM_IMAGE:-docker:dind@sha256:08a98015fce594af7c382883bea080ea206de74402a95da9dc52b6428c8cd121}

case "${1:-}" in
up)
  msb rm -f "$NAME" >/dev/null 2>&1 || true
  msb create --name "$NAME" --cpus "$CPUS" --memory "$MEMORY" --root-disk "flat:$DISK" \
    --mount-dir "$REPO:/bench" \
    --script start="sleep infinity" --entrypoint start "$IMAGE"
  msb exec -d "$NAME" -- sh -c "dockerd >/var/log/dockerd.log 2>&1"
  msb exec "$NAME" -- sh -c 'for i in $(seq 60); do docker info >/dev/null 2>&1 && exit 0; sleep 1; done; cat /var/log/dockerd.log; exit 1'
  msb exec "$NAME" -- sh -c "apk add --no-cache uv python3 bash git curl jq >/dev/null && cd /bench && uv sync --locked --python 3.12 && .venv/bin/harbor --version"
  ;;
shell) msb exec -t "$NAME" -- bash ;;
down) msb rm -f "$NAME" ;;
*) echo "usage: $0 up|shell|down" >&2; exit 2 ;;
esac
