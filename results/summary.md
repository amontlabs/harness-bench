# Results

Jobs: tb21-calibration, tb21-main, tb21-main-big, tb21-rerun-qemu1

Paired tasks: 23. Excluded trials (infrastructure errors): 4.

- excluded qemu-startup__Ds8ifXJ (claude-code): NonZeroAgentExitCodeError no verifier reward
- excluded qemu-startup__qBZ6bQQ (nanocode): NonZeroAgentExitCodeError no verifier reward
- excluded qemu-startup__5Fc28xa (nanocode): NonZeroAgentExitCodeError no verifier reward
- excluded qemu-startup__WnHgTBW (claude-code): NonZeroAgentExitCodeError no verifier reward
- pair dropped: qemu-startup in tb21-main (an arm excluded or missing; needs a rerun)
- pair dropped: qemu-startup in tb21-rerun-qemu1 (an arm excluded or missing; needs a rerun)
- note compile-compcert__yYaHHBE (nanocode): api_retries=0, usage from otel spans, fallback pricing=False, opus-5-5 output share=1.0, container killed at its memory limit=True, nanocode telemetry lost (usage undercounted)=False
- note dna-assembly__7RB2oou (claude-code): api_retries=0, usage from result.modelUsage, fallback pricing=False, opus-5-5 output share=0.0, container killed at its memory limit=False, nanocode telemetry lost (usage undercounted)=False
- note qemu-startup__Ds8ifXJ (claude-code): api_retries=None, usage from None, fallback pricing=None, opus-5-5 output share=None, container killed at its memory limit=False, nanocode telemetry lost (usage undercounted)=False
- note qemu-startup__qBZ6bQQ (nanocode): api_retries=None, usage from None, fallback pricing=None, opus-5-5 output share=None, container killed at its memory limit=False, nanocode telemetry lost (usage undercounted)=False
- note mteb-leaderboard__jo5Q7hv (nanocode): api_retries=0, usage from otel spans, fallback pricing=False, opus-5-5 output share=1.0, container killed at its memory limit=True, nanocode telemetry lost (usage undercounted)=False
- note qemu-startup__5Fc28xa (nanocode): api_retries=None, usage from None, fallback pricing=None, opus-5-5 output share=None, container killed at its memory limit=False, nanocode telemetry lost (usage undercounted)=False
- note qemu-startup__WnHgTBW (claude-code): api_retries=None, usage from None, fallback pricing=None, opus-5-5 output share=None, container killed at its memory limit=False, nanocode telemetry lost (usage undercounted)=False
- Claude Code cost from session transcripts / from result event, finished trials: median 1.000, range 0.905-1.000 (n=23). Costs of timed-out Claude Code trials come from the transcripts; far from 1 means they are biased.
- VM-level OOM kills in tb21-calibration.vm-oom.log: affected trials must be excluded by hand and re-run (container-limit OOMs are flagged per trial and count):
```
[ 1095.998532] coqc invoked oom-killer: gfp_mask=0x100cca(GFP_HIGHUSER_MOVABLE), order=0, oom_score_adj=0
[ 1095.999048] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=9cc745b2d25f5059c226618883e2cfb6510cc0090529de8f2cef95cc718ee524,mems_allowed=0,oom_memcg=/docker/9cc745b2d25f5059c226618883e2cfb6510cc0090529de8f2cef95cc718ee524,task_memcg=/docker/9cc745b2d25f5059c226618883e2cfb6510cc0090529de8f2cef95cc718ee524,task=coqc,pid=6614,uid=0
[ 1095.999056] Memory cgroup out of memory: Killed process 6614 (coqc) total-vm:655800kB, anon-rss:423624kB, file-rss:572kB, shmem-rss:0kB, UID:0 pgtables:936kB oom_score_adj:0
```

model calls = Messages API responses, subagents included, in both arms.

## all paired tasks (23)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.826 | 0.783 | -0.043 [-0.217, +0.130] |

Discordant tasks: Claude Code only 3, nanocode only 2; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.18 | 0.14 | 0.74 [0.44, 1.11] | 0.247 | 23 |
| input tokens (incl. cache) | 140,532.00 | 107,711.00 | 0.70 [0.44, 1.04] | 0.142 | 23 |
| uncached input tokens | 14.00 | 16.00 | 0.80 [0.35, 1.35] | 0.327 | 23 |
| cache-write tokens | 11,103.00 | 6,687.00 | 0.73 [0.48, 1.08] | 0.015 | 23 |
| output tokens | 3,523.00 | 3,157.00 | 0.92 [0.66, 1.22] | 0.406 | 22 |
| model calls | 7.00 | 7.00 | 0.89 [0.63, 1.19] | 0.858 | 23 |
| agent wall time (s) | 58.97 | 62.27 | 0.87 [0.46, 1.35] | 0.200 | 23 |

## primary tasks (19)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.789 | 0.789 | +0.000 [-0.211, +0.211] |

Discordant tasks: Claude Code only 2, nanocode only 2; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.24 | 0.15 | 0.75 [0.39, 1.21] | 0.490 | 19 |
| input tokens (incl. cache) | 151,272.00 | 116,577.00 | 0.69 [0.40, 1.11] | 0.225 | 19 |
| uncached input tokens | 14.00 | 18.00 | 0.73 [0.27, 1.37] | 0.552 | 19 |
| cache-write tokens | 14,345.00 | 9,314.00 | 0.75 [0.46, 1.18] | 0.060 | 19 |
| output tokens | 3,749.00 | 3,607.00 | 0.98 [0.69, 1.30] | 0.369 | 18 |
| model calls | 7.00 | 8.00 | 0.86 [0.58, 1.22] | 0.790 | 19 |
| agent wall time (s) | 67.75 | 83.31 | 0.87 [0.41, 1.43] | 0.196 | 19 |

## sanity tasks (4)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 1.000 | 0.750 | -0.250 [-0.750, +0.000] |

Discordant tasks: Claude Code only 1, nanocode only 0; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.16 | 0.12 | 0.70 [0.37, 0.97] | 0.125 | 4 |
| input tokens (incl. cache) | 112,935.00 | 95,964.00 | 0.74 [0.41, 1.17] | 0.625 | 4 |
| uncached input tokens | 12.00 | 15.00 | 1.22 [0.88, 1.66] | 0.375 | 4 |
| cache-write tokens | 8,946.50 | 6,044.00 | 0.65 [0.47, 0.82] | 0.125 | 4 |
| output tokens | 2,860.00 | 2,669.50 | 0.71 [0.25, 1.23] | 0.875 | 4 |
| model calls | 6.00 | 6.50 | 1.01 [0.62, 1.52] | 1.000 | 4 |
| agent wall time (s) | 47.64 | 30.26 | 0.85 [0.34, 1.61] | 0.875 | 4 |

## pairs where both arms finished (no timeout or crash) (20)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.850 | 0.900 | +0.050 [-0.100, +0.200] |

Discordant tasks: Claude Code only 1, nanocode only 2; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.17 | 0.15 | 1.01 [0.77, 1.32] | 0.756 | 20 |
| input tokens (incl. cache) | 140,174.50 | 112,144.00 | 0.90 [0.64, 1.25] | 0.498 | 20 |
| uncached input tokens | 14.00 | 17.00 | 1.23 [0.97, 1.52] | 0.033 | 20 |
| cache-write tokens | 10,089.00 | 6,835.50 | 0.90 [0.68, 1.25] | 0.064 | 20 |
| output tokens | 3,166.50 | 3,478.00 | 1.11 [0.89, 1.34] | 0.076 | 20 |
| model calls | 7.00 | 7.50 | 1.08 [0.84, 1.35] | 0.386 | 20 |
| agent wall time (s) | 53.06 | 72.79 | 1.22 [0.95, 1.52] | 0.030 | 20 |


## Spend (API-equivalent)

- claude-code: $7.90 over 25 trials
- nanocode: $5.70 over 25 trials
- total: $13.61

## Per task

| task | CC reward | nanocode reward | CC $ | nanocode $ | CC s | nanocode s |
|---|---|---|---|---|---|---|
| cancel-async-tasks | 1.00 | 1.00 | 0.12 | 0.14 | 29.50 | 84.40 |
| chess-best-move | 1.00 | 1.00 | 0.12 | 0.51 | 30.02 | 42.14 |
| compile-compcert | 1.00 | 1.00 | 0.44 | 0.29 | 1767.55 | 1844.20 |
| configure-git-webserver | 1.00 | 1.00 | 0.16 | 0.11 | 68.14 | 50.28 |
| custom-memory-heap-crash | 1.00 | 1.00 | 0.57 | 0.13 | 143.16 | 34.54 |
| db-wal-recovery | 1.00 | 1.00 | 0.08 | 0.08 | 15.94 | 18.70 |
| dna-assembly | 0.00 | 0.00 | 1.59 | 0.01 | 438.38 | 1.34 |
| extract-elf | 1.00 | 1.00 | 0.17 | 0.09 | 42.78 | 26.29 |
| extract-moves-from-video | 1.00 | 0.00 | 1.53 | 0.59 | 1760.66 | 1803.75 |
| feal-linear-cryptanalysis | 1.00 | 0.00 | 0.24 | 0.07 | 58.97 | 13.08 |
| git-multibranch | 1.00 | 1.00 | 0.15 | 0.14 | 36.31 | 38.45 |
| gpt2-codegolf | 1.00 | 1.00 | 0.38 | 0.36 | 136.18 | 136.91 |
| install-windows-3.11 | 1.00 | 1.00 | 0.31 | 0.98 | 395.25 | 819.30 |
| llm-inference-batching-scheduler | 1.00 | 1.00 | 0.27 | 0.33 | 67.75 | 83.31 |
| log-summary-date-ranges | 1.00 | 1.00 | 0.11 | 0.10 | 18.32 | 22.07 |
| model-extraction-relu-logits | 0.00 | 1.00 | 0.16 | 0.14 | 54.64 | 164.75 |
| mteb-leaderboard | 1.00 | 1.00 | 0.16 | 0.16 | 606.68 | 1127.17 |
| mteb-retrieve | 1.00 | 0.00 | 0.07 | 0.11 | 43.81 | 84.09 |
| path-tracing | 1.00 | 1.00 | 0.40 | 0.48 | 51.49 | 62.27 |
| pytorch-model-cli | 1.00 | 1.00 | 0.15 | 0.15 | 39.21 | 51.28 |
| query-optimize | 0.00 | 1.00 | 0.18 | 0.13 | 365.13 | 361.75 |
| sanitize-git-repo | 1.00 | 1.00 | 0.24 | 0.33 | 27.56 | 43.96 |
| video-processing | 0.00 | 0.00 | 0.31 | 0.28 | 77.35 | 87.21 |
