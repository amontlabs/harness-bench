#!/bin/sh
# Run one phase inside the benchmark VM, under the budget guard.
#
#   scripts/run.sh calibration
#   scripts/run.sh main
#   scripts/run.sh main-big
#   scripts/run.sh rerun <name> <task> [<task>...]    # re-run pairs lost to API/infra errors
#
# Run on the host; executes in the VM made by scripts/vm.sh. The Claude subscription
# token (from `claude setup-token`) is read from ~/.bench-token (mode 600) and copied
# into the VM as a file, so it never appears on a command line. Both arms use it.
#
# BENCH_CONCURRENCY overrides the phase's number of concurrent trials (see PROTOCOL.md).
# BENCH_CAP (default 100) is the total API-equivalent budget across all tb21-* jobs; the
# guard prices every trial (running ones included) and stops Harbor BENCH_MARGIN
# (default 6) dollars below the cap. If the guard itself fails, Harbor is stopped.
set -eu
NAME=${BENCH_VM:-benchvm}
PHASE=${1:?usage: $0 calibration|main|main-big|rerun <name> <task>...}
shift
CAP=${BENCH_CAP:-100}
MARGIN=${BENCH_MARGIN:-6}
TOKEN_FILE=${BENCH_TOKEN_FILE:-$HOME/.bench-token}
case "$PHASE" in
  calibration|main|main-big) JOB=tb21-$PHASE; MAKE_ARGS=$PHASE ;;
  rerun) JOB=tb21-rerun-${1:?rerun needs a name}; shift; MAKE_ARGS="rerun --tasks $*" ;;
  *) echo "unknown phase $PHASE" >&2; exit 2 ;;
esac
test -s "$TOKEN_FILE" || { echo "no token in $TOKEN_FILE (claude setup-token)" >&2; exit 1; }

msb exec "$NAME" -- sh -c 'umask 077; cat > /root/.bench-token' < "$TOKEN_FILE"
msb exec "$NAME" -- sh -c "
  set -u
  cd /bench
  export CLAUDE_CODE_OAUTH_TOKEN=\$(cat /root/.bench-token)
  export PYTHONPATH=/bench NANOCODE_BINARY=/bench/vendor/nanocode CLAUDE_FORCE_OAUTH=1
  unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
  mkdir -p jobs
  # A previous job of the same name must be renamed to jobs/tb21-archived-<...> (still
  # matched by the budget guard, so its spend stays counted), not moved out of jobs/.
  test ! -e jobs/$JOB || { echo 'jobs/$JOB exists; rename it to jobs/tb21-archived-<name> first' >&2; exit 1; }
  .venv/bin/python scripts/make_job.py $MAKE_ARGS ${BENCH_CONCURRENCY:+--concurrency $BENCH_CONCURRENCY} || exit 1
  sed -i 's/\"job_name\": \"tb21-[^\"]*\"/\"job_name\": \"$JOB\"/' configs/job-${MAKE_ARGS%% *}.json
  # Containers killed for memory (cgroup) and kernel OOM kills in the VM are logged.
  dmesg -c >/dev/null 2>&1 || true   # start this job's kernel log clean
  docker events --filter event=oom --format '{{.Time}} {{.Actor.Attributes.name}}' > jobs/$JOB.oom.log 2>&1 &
  EVENTS=\$!
  .venv/bin/harbor run -c configs/job-${MAKE_ARGS%% *}.json > jobs/$JOB.log 2>&1 &
  HARBOR=\$!
  if ! .venv/bin/python scripts/budget_guard.py --pid \$HARBOR --cap $CAP --margin $MARGIN; then
    echo 'budget guard failed: stopping Harbor' >&2
    kill -TERM \$HARBOR 2>/dev/null; sleep 120; kill -KILL \$HARBOR 2>/dev/null
  fi
  wait \$HARBOR
  # Anything Harbor left running (after a SIGKILL) is stopped so no harness keeps spending.
  docker ps -q | xargs -r docker kill >/dev/null
  kill \$EVENTS 2>/dev/null
  # Container-limit OOMs (CONSTRAINT_MEMCG) are agent outcomes and come from docker events;
  # only kernel OOM kills outside a container limit are VM-level.
  dmesg -c 2>/dev/null | grep -E 'oom-kill:constraint=CONSTRAINT_(NONE|CPUSET|MEMORY_POLICY)' > jobs/$JOB.vm-oom.log || true
  tail -40 jobs/$JOB.log
  echo \"OOM events: \$(cat jobs/$JOB.oom.log jobs/$JOB.vm-oom.log | grep -c .)\"
  docker container prune -f >/dev/null; docker image prune -af >/dev/null
"
