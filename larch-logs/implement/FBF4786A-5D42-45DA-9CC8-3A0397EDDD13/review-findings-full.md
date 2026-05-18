### FINDING_1: panel [plan-review/accepted]

## log-phase.sh ownership violated — move scout batch logging to the /review wrapper

- **Concern**: Plan added `log-phase.sh` calls inside `review-core.sh`, violating the canonical contract that run-log batches are wrapper-owned. `review-core.sh` also risks failure when `RUN_ID` is empty since `log-phase.sh` requires `--run-id`.
- **Resolution**: Moved all `review-scout-manifest` `log-phase.sh` calls to `/review` SKILL wrapper Step 4 (guarded by `[[ -n "$RUN_ID" ]]`). `review-core.sh` emits only KVs (`SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, `YIELD_TSV_FILE`). SKILL.md Step 4 updated to enumerate the new batch. `review-core.md` updated to confirm `log-phase.sh` is not called from `review-core.sh`.

### FINDING_2: panel [plan-review/accepted]

## Yield TSV reviewer attribution — score_rows uses output basenames, not manifest slot IDs

- **Concern**: `tally-code-votes.sh --manifest-file` join used manifest `slot` IDs but `score_rows` first column uses output basenames (e.g. `dyn-foo-output.txt`); waterfall fallbacks add `-phase2`/`-phase3` suffixes; simple-panel `codex-generalist-output.txt` was not in the static slug map.
- **Resolution**: `tally-code-votes.sh` now builds `basename_to_archetype` mapping keyed by `basename(manifest.output)`, with phase/retry suffix normalization (strip `-phase2`/`-phase3`/`-retry` before lookup). Added `codex-generalist-output.txt` → `generic` mapping. Static archetype labels derived by stripping `cursor-specialist-`/`codex-specialist-` prefix and `-output.txt` suffix.

### FINDING_3: panel [plan-review/accepted]

## review-scout-manifest batch format — single .json batch cannot contain three files

- **Concern**: Planned `review-scout-manifest .json replace none` batch described as containing three mixed-format artifacts; larch-log publishes one file per slug.
- **Resolution**: Changed to `review-scout-manifest .json replace json-object` in `larch-log-batches.sh`. Wrapper assembles a single JSON object payload with status, dynamic_slots, manifest_path, and yield_tsv_path fields before calling `log-phase.sh`.

### FINDING_4: panel [plan-review/accepted]

## Scout invokes raw claude CLI instead of hardened launch-claude-subprocess.sh

- **Concern**: Plan specified `claude --model claude-sonnet-4-6 --print --no-markdown` directly, bypassing the existing subprocess wrapper's path validation, read-only preamble, context-file size caps, timing, and dirty-tree sidecar.
- **Resolution**: `scout-dynamic-archetypes.sh` invokes `scripts/launch-claude-subprocess.sh` with a temp prompt file and output path. `SCOUT_TOKENS_INPUT`/`SCOUT_TOKENS_OUTPUT` KVs dropped from the contract since `launch-claude-subprocess.sh` does not emit them.

### FINDING_5: panel [plan-review/accepted]

## test-larch-logs-batches.sh expected-list not updated in plan

- **Concern**: `scripts/test-larch-logs-batches.sh` has a hardcoded sorted expected batch list; adding `review-scout-manifest` to `larch-log-batches.sh` without updating this test causes CI drift failure.
- **Resolution**: Added `scripts/test-larch-logs-batches.sh` to the test harness modifications list. The expected sorted batch list must include `review-scout-manifest`.

### FINDING_6: panel [plan-review/accepted]

## DYNAMIC_SLOTS/SCOUT_STATUS not emitted on all review-core.sh exit paths

- **Concern**: Scout KVs planned only for the normal end path; zero-findings, panel-failed, and main-agent-vote-required early exits after dispatch would omit `DYNAMIC_SLOTS`/`SCOUT_STATUS`.
- **Resolution**: `review-core.sh` reads `SCOUT_STATUS`/`DYNAMIC_SLOTS`/`SCOUT_MANIFEST` from `dispatch_out` immediately after dispatch and emits them on all post-dispatch exit paths. Also persists `scout-status.env` in `REVIEW_TMPDIR` after dispatch for sentinel reuse.

### FINDING_7: panel [plan-review/accepted]

## --dynamic-archetypes count validation incomplete — negative/non-numeric values not rejected

- **Concern**: Only `N > 4` rejected; non-numeric, empty, or negative values from flag or `LARCH_DYNAMIC_ARCHETYPES_MAX` env could cause unpredictable arithmetic under `set -euo pipefail`.
- **Resolution**: Both flag and env validated as `^[0-4]$` (digits-only, range 0-4); any other value → exit 2. Tests added for `-1`, `abc`, empty string, `4` (pass), `5` (fail) in `test-dispatch-panel.sh` and `test-review-core.sh`.

### FINDING_8: panel [plan-review/accepted]

## SLOT_COUNT not incremented for dynamic slots in dispatch-panel.sh

- **Concern**: `slot_count` only incremented via `queue_external_slot`/`queue_external_generalist_slot` helpers; dynamic slots appended directly without bumping the counter.
- **Resolution**: Dynamic slot queuing increments a dynamic counter. `dispatch-panel.sh` emits `STATIC_SLOT_COUNT` (pre-dynamic) and `SLOT_COUNT` (static + dynamic total). Test assertions verify `SLOT_COUNT` reflects the full panel size.

### FINDING_10: panel [code-review/accepted]

## code-quality: scripts/scout-dynamic-archetypes.sh:36-37,108-116; scripts/scout-dynamic-archetypes.md:7

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] `--session-env-path` is accepted and documented but never affects the subprocess launch. Operators may assume timing-ledger or session env propagation that never happens. Remove the unused flag/doc bullet or plumb session context only through flags `launch-claude-subprocess.sh` actually supports.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:445-449, scripts/ship-pr.sh:520-524

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: [important] lint-fix-loop.sh non-zero exits are run under set -e command substitutions, bypassing the status handling code. If lint-fix-loop.sh emits LINT_FIX_STATUS=failed and exits 1, ship-pr.sh exits immediately instead of recording the failure and stalling through the intended path. Capture lint-fix-loop.sh with set +e or an explicit non-fatal wrapper, preserve rc, then parse LINT_FIX_STATUS and route failures through the existing case logic.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:32-88 skills/review/scripts/review-core.sh:250-253

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Failure threshold still uses static INTENDED_SLOTS (12/7) while launched_slots and collector results include up to four dynamic reviewers. More outputs can fail without raising the intended denominator; e.g. 12 static + 4 dynamic with seven non-OK slots trips >50%-of-12 even though seven of sixteen slots failed, and THRESHOLD_REASON still says “of 12”. Reconcile INTENDED_SLOTS with DYNAMIC_SLOTS (or exclude dynamic slots from failure accounting) and fix the reason string to match the counted population.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:139-170; skills/review/scripts/collect-findings.sh:359-367

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] Dynamic waterfall fallback outputs use -phase2/-phase3 basenames that collect-findings rejects before tally normalization. When a dynamic Cursor-primary slot falls back to Codex or Claude, findings from dyn-foo-output-phase2.txt are skipped as an invalid reviewer column. Accept and normalize waterfall suffixes in collect-findings label validation before enforcing reviewer filename shape.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:176-206

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sentinel reuse path defaults SCOUT_STATUS to ok when scout-status.env is missing. Stale or injected scout-manifest.json is treated as a successful scout; run logs and wrappers record misleading ok status. Require scout-status.env (or stronger sentinel) before trusting a pre-existing manifest; avoid default ok.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## correctness: skills/review/scripts/review-core.sh:161-179

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Pre-dispatch description zero-scope exit emits no SCOUT_STATUS or DYNAMIC_SLOTS lines. Wrappers that always parse SCOUT_STATUS per round get missing keys on an empty description scope. Emit SCOUT_STATUS=na and DYNAMIC_SLOTS=0 (and empty optional scout keys) before exit.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## risk-integration: Makefile:58 Makefile:671-672

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] test-upgrade-larch.sh no longer has a Makefile target; CI shards only run test-upgrade-larch-prune Core upgrade-larch regression harness never runs in make lint/test-harnesses; stable resolve/idempotency/redaction regressions undetected Restore test-upgrade-larch target and attach it to a harness shard (keep prune alongside)
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## risk-integration: scripts/test-scout-dynamic-archetypes.sh

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] No harness case asserts SCOUT_STATUS=timeout when the launch wrapper reports TIMEOUT. The timeout branch in scout-dynamic-archetypes.sh is untested and could regress without CI signal. Extend the harness with a launch stub that emits STATUS=TIMEOUT and assert SCOUT_STATUS=timeout and empty archetypes output.
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## risk-integration: skills/review/scripts/dispatch-panel.sh:176-205, skills/review/SKILL.md:44

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Standalone review rounds reuse the same scout manifest for the whole review tmpdir instead of scouting once per round. After round 1 applies substantial fixes, round 2 reviews a changed diff but still queues dynamic archetypes chosen for the old diff. Key the scout sentinel by round number or diff hash, or use a per-round review dir for standalone /review.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## risk-integration: skills/review/scripts/test-dispatch-panel.sh:94-132

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No automated test for classify-diff skip paths (docs-only/test-only/generated-only) despite plan and dispatch-panel.md Scout skip/regression in dispatch-panel.sh classifier can ship; dynamic slots or SCOUT_STATUS could silently diverge from spec Add harness cases that stub classify-diff-mode output (or diff fixtures) and assert SCOUT_STATUS=skipped-docs-only etc. and DYNAMIC_SLOTS=0
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## security: scripts/larch-log-batches.md:3010-3021 (review-scout-manifest schema as merged)

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Committed review-scout-manifest JSON carries absolute tmpdir paths in manifest_path and yield_tsv_path. Public larch-logs commits can leak ~/.cache/larch session directory layout and username-bearing absolute paths, aiding correlation or targeted local follow-up. Redact to placeholders or basenames in the JSON payload before commit; align with manifest.json redaction policy in SECURITY.md.
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## security: scripts/scout-dynamic-archetypes.sh:110-116

- **Reviewer**: codex-specialist-security-output.txt
- **Concern**: [important] Scout runs untrusted diff/plan content through a prompt-only read-only Claude subprocess without mechanical tool denial or dirty-tree recovery coverage. A malicious diff can inject scout instructions that cause Claude Code to use Bash/Edit/Write before reviewer dispatch, and review-core only recovers dirty-tree sidecars for reviewer outputs, not the scout. Run the scout with mechanical read-only enforcement or disabled tools, and include the scout subprocess sidecar in review-core dirty-tree recovery before continuing.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## architecture: scripts/scout-dynamic-archetypes.sh:3308-3321 vs launch invocation

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] --session-env-path accepted but not forwarded to launch-claude-subprocess.sh in the shown implementation. Contract drift / dead flag misleads operators or future contributors about session binding for the scout subprocess. Thread the flag into the launcher or remove it from the documented CLI until implemented.
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## security: scripts/scout-dynamic-archetypes.sh:158-183; skills/review/scripts/dispatch-panel.sh:140-149

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] LLM-generated scout prompt_body is inserted as trusted reviewer instructions after only shallow validation. A malicious diff can prompt-inject the scout into emitting instructions that pass validation and are then delivered to Cursor/Codex, which are not mechanically read-only. Return structured scout metadata only, synthesize reviewer prompts from a fixed trusted template, and quote scout rationale as untrusted data.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## architecture: skills/review/SKILL.md:52-59

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 4 documents review-scout-manifest only in prose; implementation plan FINDING_1 specified an explicit jq+log-phase.sh wrapper snippet. Operators may omit the exact JSON assembly and log-phase invocation the plan standardized, so run-log batches diverge from the intended contract. Inline the plan's guarded bash/jq block in Step 4 (or point Step 4 to one canonical script that implements it verbatim).
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## code-quality: .claude-plugin/plugin.json (description field)

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plugin description omits optional dynamic reviewers. Consumers reading only `plugin.json` get an outdated picture of panel topology. Update the description string to mention optional scout-driven slots (cap 4, default off).
- **Suggested revision**: Address the concern above.

