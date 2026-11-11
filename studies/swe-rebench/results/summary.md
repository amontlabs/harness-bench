# Results

Jobs: swr-calibration, swr-main

Paired tasks: 30. Excluded trials (infrastructure errors): 0.

- note gotd__td-1759__PYTbEDQ (nanocode): api_retries=0, usage from otel spans, fallback pricing=False, opus-5-5 output share=1.0, container killed at its memory limit=True, nanocode telemetry lost (usage undercounted)=False
- note gotd__td-1759__fMUCzGG (claude-code): api_retries=0, usage from result.modelUsage, fallback pricing=False, opus-5-5 output share=1.0, container killed at its memory limit=True, nanocode telemetry lost (usage undercounted)=False
- note mozilla-ai__any-llm-1121__ixs3E8B (claude-code): api_retries=0, usage from result.modelUsage, fallback pricing=False, opus-5-5 output share=1.0, container killed at its memory limit=True, nanocode telemetry lost (usage undercounted)=False
- note mvanhorn__cli-printing-press-208__w56GAHS (claude-code): api_retries=0, usage from result.modelUsage, fallback pricing=False, opus-5-5 output share=1.0, container killed at its memory limit=True, nanocode telemetry lost (usage undercounted)=False
- Claude Code cost from session transcripts / from result event, finished trials: median 1.000, range 1.000-1.000 (n=30). Costs of timed-out Claude Code trials come from the transcripts; far from 1 means they are biased.

model calls = Messages API responses, subagents included, in both arms.

## Upstream-access audit

- claude-code: 4 trials flagged, 0 confirmed access, of 30
- nanocode: 3 trials flagged, 0 confirmed access, of 30
- apache__hugegraph-3037__whsL3zt (claude-code): access=False (Claude Code: curl of apache/tinkerpop CountStrategy sources at 3.5.5/3.5.6 from raw.githubusercontent.com; same reasoning: the instruction asks to port that upstream TinkerPop change; not the hugegraph pull request); calls: network command to GitHub [Bash]: …main/java/org/apache/hugegraph/unit/ | head -50; timeout 15 curl -sI https://raw.githubusercontent.com/apache/tinkerpop/3.6-dev/README.md | head -1… | network command to GitHub [Bash]: …mkdir -p /tmp/up && cd /tmp/up; for t in 3.5.5 3.5.6; do curl -sfL -o CountStrategy-$t.java https://raw.githubusercontent.com/apache/tinkerpop/$t/gremlin-core/src/main/java/org/apache/t… | network command to GitHub [Bash]: …process.traversal.util.TraversalHelper | grep -i removeAll; curl -sfL -o CST.java https://raw.githubusercontent.com/apache/tinkerpop/3.5.6/gremlin-core/src/test/java/org/apach…
- apache__hugegraph-3037__VJKNBF5 (nanocode): access=False (nanocode: git clone of apache/tinkerpop (a dependency, not the task's repository) to read CountStrategy; the instruction itself says to port the upstream TINKERPOP-2911 change, so this is the material it points to, not the hugegraph pull request); calls: git remote op [exec]: …"cd /tmp && sed -n 80,230p cs.java; cd /tmp && rm -rf tp && git clone -q --filter=blob:none --no-checkout https://github.com/apac… | network command to GitHub [exec]: …"cd /tmp && sed -n 80,230p cs.java; cd /tmp && rm -rf tp && git clone -q --filter=blob:none --no-checkout https://github.com/apache/tinkerpop.git tp 2>&1 | tail -2; cd tp && git log --…
- astral-sh__ruff-25414__KYjE6LL (claude-code): access=False (issue URL only inside a code comment written with sed; 'uvx prek' runs the repo's pre-commit hooks (matched on a ruff_linter path), no network fetch of the fix); calls: upstream URL [Bash]: … after brackets or multiline assignments⏎        // https://github.com/astral-sh/ruff/issues/25407⏎        assert!(comment_contains_code("# \⏎)  # noqa:… | upstream URL [Bash]: …cd /ruff && sed -i 's|        // https://github.com/astral-sh/ruff/issues/25407⏎||' crates/ruff_linter/src/rules/eradicate/detection.… | install of the task's own package [Bash]: …isolated --select ERA,RUF100 /tmp/era/t.py 2>&1 | tail -15; uvx prek run --files crates/ruff_linter/src/rules/eradicate/detection.rs crates/ruff_linter/resourc…
- astral-sh__ruff-25414__izrEbxy (nanocode): access=False (issue URL only inside a regression-test comment written with printf/Edit; 'uvx prek' runs the repo's pre-commit hooks (matched on a ruff_linter path), no network fetch of the fix); calls: upstream URL [exec]: …mand:`cd /ruff && printf '\⏎\⏎# Regression test for https://github.com/astral-sh/ruff/issues/25426,\⏎# trailing comments should not prevent detection\⏎#… | upstream URL [exec]: …it({file_path:fx, old_string:"# Regression test for https://github.com/astral-sh/ruff/issues/25426,⏎# trailing comments should not prevent detection", n… | install of the task's own package [exec]: …eck --no-cache --isolated --select ERA,RUF100 /tmp/era2.py; uvx prek run --files crates/ruff_linter/src/rules/eradicate/detection.rs crates/ruff_linter/resourc…
- marimo-team__marimo-9626__rtrS2iK (claude-code): access=False (Claude Code: `uvx --with . mypy` installs the local checkout, not a registry release); calls: install of the task's own package [Bash]: …cd /marimo; (uvx --with . mypy marimo/_session/file_change_handler.py 2>&1 || true) | tail -2; uv… | install of the task's own package [Bash]: …ession_manager.py -q 2>&1 | grep -E "FAILED|passed|failed"; uvx --with . mypy marimo/_session/file_change_handler.py 2>&1 | grep file_change_han… | install of the task's own package [Bash]: … uv run ruff format marimo/_session/file_change_handler.py; uvx --with . mypy marimo/_session/file_change_handler.py 2>&1 | grep file_change_han…
- microsoft__apm-1553__xzakfQ8 (nanocode): access=False (nanocode: 'git clone' appears only inside a code comment it wrote); calls: git remote op [exec]: …se:⏎            # No PAT: reuse the AAD bearer (az cli) the git clone path uses.⏎            auth_ctx = self._host.auth_resolver.…
- mozilla-ai__any-llm-1121__ixs3E8B (claude-code): access=False (Claude Code: `pip download otari==0.1.0` fetches the external otari SDK at an old pinned version to read its API, not a release of any-llm; `uvx ruff@latest` matched an src/any_llm path); calls: registry lookup [Bash]: …-rf otari010 && mkdir otari010 && cd otari010 && timeout 60 pip download --no-deps otari==0.1.0 -q -d . 2>&1 | tail -2; ls; for w in… | install of the task's own package [Bash]: …cd /any-llm; (uvx ruff@latest check src/any_llm/providers/otari tests/unit/providers/test_otari_provider.py…

Pairs with confirmed upstream access by either arm: 0 (dropped from the primary subset).

## primary: paired tasks without confirmed upstream access (30)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.633 | 0.667 | +0.033 [-0.100, +0.167] |

Discordant tasks: Claude Code only 2, nanocode only 3; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.55 | 0.51 | 0.90 [0.82, 0.98] | 0.026 | 30 |
| input tokens (incl. cache) | 629,524.00 | 486,741.00 | 0.82 [0.73, 0.91] | 0.001 | 30 |
| uncached input tokens | 36.00 | 34.00 | 0.97 [0.90, 1.06] | 0.493 | 30 |
| cache-write tokens | 33,201.50 | 30,714.50 | 0.88 [0.79, 0.99] | 0.055 | 30 |
| output tokens | 8,730.00 | 7,849.50 | 0.98 [0.90, 1.06] | 0.612 | 30 |
| model calls | 17.00 | 16.00 | 0.92 [0.85, 1.00] | 0.080 | 30 |
| agent wall time (s) | 726.02 | 518.62 | 0.79 [0.65, 0.97] | 0.008 | 30 |

## sensitivity: all paired tasks, a trial with confirmed upstream access scored 0 (30)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.633 | 0.667 | +0.033 [-0.100, +0.167] |

Discordant tasks: Claude Code only 2, nanocode only 3; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.55 | 0.51 | 0.90 [0.82, 0.98] | 0.026 | 30 |
| input tokens (incl. cache) | 629,524.00 | 486,741.00 | 0.82 [0.73, 0.91] | 0.001 | 30 |
| uncached input tokens | 36.00 | 34.00 | 0.97 [0.90, 1.06] | 0.493 | 30 |
| cache-write tokens | 33,201.50 | 30,714.50 | 0.88 [0.79, 0.99] | 0.055 | 30 |
| output tokens | 8,730.00 | 7,849.50 | 0.98 [0.90, 1.06] | 0.612 | 30 |
| model calls | 17.00 | 16.00 | 0.92 [0.85, 1.00] | 0.080 | 30 |
| agent wall time (s) | 726.02 | 518.62 | 0.79 [0.65, 0.97] | 0.008 | 30 |

## sensitivity: all paired tasks as graded (30)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.633 | 0.667 | +0.033 [-0.100, +0.167] |

Discordant tasks: Claude Code only 2, nanocode only 3; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.55 | 0.51 | 0.90 [0.82, 0.98] | 0.026 | 30 |
| input tokens (incl. cache) | 629,524.00 | 486,741.00 | 0.82 [0.73, 0.91] | 0.001 | 30 |
| uncached input tokens | 36.00 | 34.00 | 0.97 [0.89, 1.06] | 0.493 | 30 |
| cache-write tokens | 33,201.50 | 30,714.50 | 0.88 [0.79, 0.99] | 0.055 | 30 |
| output tokens | 8,730.00 | 7,849.50 | 0.98 [0.90, 1.06] | 0.612 | 30 |
| model calls | 17.00 | 16.00 | 0.92 [0.85, 1.00] | 0.080 | 30 |
| agent wall time (s) | 726.02 | 518.62 | 0.79 [0.65, 0.97] | 0.008 | 30 |

## pairs without confirmed upstream access where both arms finished (no timeout or crash) (27)

| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |
|---|---|---|---|
| mean reward | 0.667 | 0.667 | +0.000 [-0.148, +0.148] |

Discordant tasks: Claude Code only 2, nanocode only 2; exact McNemar p = 1.000.

| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |
|---|---|---|---|---|---|
| API-equivalent cost ($) | 0.52 | 0.50 | 0.89 [0.81, 0.98] | 0.025 | 27 |
| input tokens (incl. cache) | 541,800.00 | 482,950.00 | 0.83 [0.73, 0.93] | 0.005 | 27 |
| uncached input tokens | 34.00 | 34.00 | 1.00 [0.92, 1.09] | 0.979 | 27 |
| cache-write tokens | 33,131.00 | 27,105.00 | 0.86 [0.76, 0.97] | 0.026 | 27 |
| output tokens | 7,417.00 | 7,508.00 | 0.99 [0.90, 1.07] | 0.768 | 27 |
| model calls | 16.00 | 16.00 | 0.95 [0.87, 1.03] | 0.249 | 27 |
| agent wall time (s) | 642.78 | 365.59 | 0.81 [0.66, 1.01] | 0.026 | 27 |

## Agent outcomes per arm (paired trials)

| arm | finished | timed out | other agent error | container memory kill |
|---|---|---|---|---|
| claude-code | 27 | 3 | 0 | 3 |
| nanocode | 30 | 0 | 0 | 1 |

## By repository agent configuration files (primary subset)

| files in the repository | tasks | Claude Code solved | nanocode solved |
|---|---|---|---|
| none | 8 | 6 | 5 |
| CLAUDE.md/.claude only | 6 | 3 | 4 |
| AGENTS.md only | 5 | 2 | 4 |
| both | 11 | 8 | 7 |


## Spend (API-equivalent)

- claude-code: $28.25 over 30 trials
- nanocode: $27.59 over 30 trials
- total: $55.85

## Per task

| task | CC reward | nanocode reward | CC $ | nanocode $ | CC s | nanocode s |
|---|---|---|---|---|---|---|
| ArcadeData__arcadedb-4281 | 1.00 | 1.00 | 0.39 | 0.26 | 334.07 | 183.69 |
| HKUDS__nanobot-4129 | 0.00 | 0.00 | 0.40 | 0.32 | 194.25 | 264.67 |
| apache__hugegraph-3037 | 0.00 | 1.00 | 0.70 | 0.91 | 1298.24 | 1080.01 |
| apache__pulsar-25793 | 0.00 | 0.00 | 0.44 | 0.24 | 347.33 | 317.17 |
| astral-sh__ruff-25414 | 1.00 | 1.00 | 0.40 | 0.35 | 2514.39 | 1506.37 |
| fallow-rs__fallow-913 | 1.00 | 1.00 | 0.46 | 0.37 | 923.29 | 892.57 |
| fathah__hermes-desktop-268 | 0.00 | 0.00 | 0.60 | 0.57 | 218.82 | 155.26 |
| floci-io__floci-1325 | 0.00 | 0.00 | 0.51 | 0.53 | 511.05 | 322.98 |
| gotd__td-1759 | 1.00 | 1.00 | 0.55 | 0.50 | 1531.71 | 1362.66 |
| helidon-io__helidon-11979 | 1.00 | 1.00 | 0.60 | 0.85 | 207.08 | 270.03 |
| ivov__lisette-491 | 1.00 | 1.00 | 0.45 | 0.59 | 642.78 | 630.37 |
| kestra-io__kestra-16119 | 1.00 | 1.00 | 0.40 | 0.26 | 191.34 | 188.82 |
| kubernetes-sigs__kueue-11559 | 0.00 | 0.00 | 1.34 | 1.47 | 999.97 | 1264.28 |
| marimo-team__marimo-9626 | 0.00 | 0.00 | 0.32 | 0.34 | 169.31 | 330.70 |
| microsoft__apm-1553 | 1.00 | 0.00 | 2.69 | 2.20 | 1004.48 | 480.65 |
| microsoft__waza-247 | 1.00 | 1.00 | 1.00 | 1.10 | 500.16 | 556.60 |
| mozilla-ai__any-llm-1121 | 1.00 | 0.00 | 0.79 | 0.85 | 1048.69 | 828.89 |
| mui__base-ui-4903 | 1.00 | 1.00 | 0.82 | 0.71 | 479.31 | 2106.20 |
| mvanhorn__cli-printing-press-2086 | 0.00 | 0.00 | 1.67 | 1.97 | 3002.41 | 2193.80 |
| nesquena__hermes-webui-3069 | 1.00 | 1.00 | 1.13 | 0.91 | 769.91 | 299.05 |
| promptfoo__promptfoo-9313 | 1.00 | 1.00 | 0.61 | 0.41 | 1704.78 | 331.46 |
| raullenchai__Rapid-MLX-426 | 0.00 | 1.00 | 1.89 | 1.67 | 682.14 | 742.57 |
| rest-sh__restish-337 | 1.00 | 1.00 | 0.33 | 0.29 | 1039.76 | 824.17 |
| tailscale__tailscale-19847 | 1.00 | 1.00 | 0.31 | 0.34 | 910.91 | 365.59 |
| tashfeenahmed__freellmapi-289 | 1.00 | 1.00 | 0.52 | 0.27 | 169.60 | 146.41 |
| tursodatabase__turso-7117 | 1.00 | 1.00 | 1.80 | 1.68 | 3002.36 | 2609.85 |
| ubugeeei-prod__vize-1508 | 0.00 | 0.00 | 5.95 | 6.73 | 2359.45 | 1723.34 |
| ueberdosis__tiptap-7887 | 1.00 | 1.00 | 0.34 | 0.28 | 154.02 | 121.69 |
| vuejs__core-14877 | 1.00 | 1.00 | 0.28 | 0.20 | 340.04 | 130.45 |
| withcoral__coral-1143 | 0.00 | 1.00 | 0.55 | 0.45 | 3002.30 | 1098.84 |
