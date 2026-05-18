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

### FINDING_11: panel [code-review/accepted]

## code-quality: scripts/scout-dynamic-archetypes.sh:162-199

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] jq reduce truncates to max archetypes without emitting WARN. Scout returns more accepted archetypes than N after validation; extras vanish with no operator-visible signal. Emit WARN when filtered length exceeds max before truncation.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## code-quality: skills/review/scripts/test-dispatch-panel.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate env assignment in skip-mode test case Noise only; no runtime impact Remove duplicate SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH=… fragment
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: scripts/scout-dynamic-archetypes.sh:55-63 skills/review/scripts/dispatch-panel.sh:195-196

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Scout subprocess uses exit 2 when diff mode diff-file is missing or not -f; dispatch does not treat this as a soft scout failure. Empty or deleted DIFF_FILE in diff mode aborts dispatch-panel with set -e instead of continuing with a static panel and a scout status. Validate DIFF_FILE before scout or map missing/invalid diff-file to the same non-fatal empty-manifest path used for parse/claude failures.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:887-903; scripts/lint-fix-loop.sh:275-291

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] CI lint-fix recovery can leave required untracked files out of the pushed fix commit. When a vendor CI fix dirties the tree first, lint-fix-loop.sh does not self-commit; local checks can pass using a newly created untracked fixture, but run_ci_fix_vendor later uses git add -u and pushes without that fixture. Commit the full safe delta including untracked files, preferably from an explicit delta file emitted by lint-fix-loop.sh.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: skills/review/SKILL.md:57-82

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] SKILL Step 4 prose requires RUN_ID and SCOUT_STATUS!=na guards for review-scout-manifest, but the fenced canonical bash omits any if-wrapper. Orchestrator copies the block and runs log-phase on every review including SCOUT_STATUS=na (dynamics off), writing an unintended or empty scout batch contrary to the stated contract. Wrap jq+log-phase in if [[ -n "${RUN_ID:-}" && "${SCOUT_STATUS:-na}" != "na" ]]; then … fi matching the prose.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:32-87

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Implementation widens INTENDED_SLOTS to max(static, launched) including dynamic reviewers, conflicting with the plan Edge Case #9 / OOS_4 note that the denominator stays on the static 12/7 baseline with dynamics excluded. Reviewers or operators following the written plan expect failure-rate math anchored to static slots only; actual runs use a larger denominator whenever dynamics launch, changing when panel-failed triggers versus the documented follow-up. Reconcile plan and code: either restore static-only denominator behavior and document it, or update the implementation plan / review docs to state that dynamics expand INTENDED_SLOTS and retire OOS_4’s exclusion wording.
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:445-451; scripts/ship-pr.sh:523-529

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] New lint-fix paths enable errexit in ship-pr.sh despite the script intentionally running without set -e. After lint-fix succeeds, later command-substitution helper failures can abort before record_failure or exit_stall records state. Capture rc without set -e, or save and restore the original shell options.
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## risk-integration: scripts/test-scout-dynamic-archetypes.sh:154-158

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [latent] The plan-required </reviewer_ prompt_body rejection case is untested. A future edit could drop the untrusted-wrapper closing-tag guard while the scout harness still passes. Add a fixture containing </reviewer_ and assert rejection plus unsafe warning.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## risk-integration: skills/review/scripts/dispatch-panel.sh:189-220

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sentinel manifest present without companion scout status env clears SCOUT_MANIFEST and skips synthesis. Crash or partial tmpdir leaves scout-roundN-manifest.json populated but scout-roundN-status.env missing; dynamic archetypes are silently dropped for that round. If manifest is readable JSON with archetypes, synthesize or re-derive status; do not clear manifest path solely on missing env.
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## security: scripts/scout-dynamic-archetypes.sh:162-200 and skills/review/scripts/dispatch-panel.sh:144-161

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Scout rationale/prompt_body are embedded inside a literal <scout_notes> wrapper but validation only blocks </reviewer_ and standalone --- lines, not the real closing tag used in synthesis. A compromised scout can emit </scout_notes> (including via multiline rationale) so following attacker text appears outside the untrusted-labeled region, smuggling instructions to the Cursor reviewer. Extend jq validation (or post-jq checks) to reject or neutralize delimiter substrings that match the synthesis envelope (at minimum literal </scout_notes>, ideally case-insensitive / other mirror tags); alternatively base64-wrap or otherwise structurally encode scout free text so it cannot terminate the wrapper.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## architecture: skills/review/scripts/tally-code-votes.sh:375-417

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Yield TSV END iterates only manifest-derived keys; score_rows basenames not present in the map accrue totals that are never emitted. If a finding’s normalized Reviewer basename is missing from the panel manifest map, accepted/rejected counts for that reviewer disappear from scout-archetype-yield.tsv with no warning. Iterate union of manifest keys and observed reviewers, or WARN on orphan total[base] keys.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## code-quality: scripts/scout-dynamic-archetypes.sh:159-217

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] mktemp validated_tmp path not removed on jq validation failure branch. Repeated parse failures accumulate stray .tmp.* files under REVIEW_TMPDIR. Add rm -f "$validated_tmp" in the parse-failed branches (and on set -e traps if needed).
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## code-quality: skills/review/SKILL.md:61-82

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Canonical log-phase example omits required --run-id (and usual --log-root). Orchestrator copies the fenced block literally; log-phase.sh exits 2 on usage, so review-scout-manifest never lands in larch-logs. Add --run-id "$RUN_ID" and matching --log-root to the example (same as other Step 4 log-phase calls).
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:447-453,527-533

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] New ship-pr lint-fix paths leave errexit disabled by running set +e twice. After lint-fix, a later unchecked command such as advance_phase bump can fail while the function still returns success with stale state. Restore set -e after capturing fix_rc or wrap the non-fatal command substitution in a helper.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:895-914

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] CI fix commits can stage only lint-fix delta paths after a vendor fix plus lint-fix sequence. Vendor changes made before lint-fix-loop remain uncommitted while the Fix CI failure commit includes only lint-fix paths, leaving the tree dirty or pushing an incomplete fix. Stage the union of vendor dirty paths and lint-fix delta paths, or use the broader staging behavior with scope validation.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## correctness: skills/review/SKILL.md:57-83; skills/review/scripts/log-phase.sh:12-32

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: [important] The documented review-scout-manifest log-phase call omits required --run-id. When SCOUT_STATUS is present, the wrapper pattern exits 2 because log-phase.sh requires --run-id. Add --run-id "$RUN_ID" to the Step 4 log-phase invocation.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: skills/review/references/heavy-worker.md:15-21,30-34; skills/review/SKILL.md:27

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Subagent review contract lacks DYNAMIC_ARCHETYPES and scout result propagation. /review --diff --subagent --dynamic-archetypes 4 can run the heavy worker without passing the requested dynamic reviewer count, silently skipping the feature. Pass and consume DYNAMIC_ARCHETYPES in the heavy-worker contract or require the worker to call review-core.sh with the parsed flag and return scout KVs.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:56-61,78-86

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Dynamic fallback output basenames are not recognized as dynamic reviewers. A dynamic reviewer fallback writes dyn-foo-output-phase2.txt or dyn-foo-output-phase3.txt; those failures count against the static 12-slot denominator and can falsely stall review. Normalize phase2/phase3/retry suffixes before excluding dyn-* outputs and add regression coverage.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:90-96

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] NEVER_LAUNCHED uses static INTENDED_SLOTS minus LAUNCHED_SLOTS but LAUNCHED_SLOTS counts static+dynamic outputs from review-core. With dynamic slots enabled, LAUNCHED_SLOTS is often >= static baseline even when total planned slots (static+dynamic) are not all present, so never-launched failures clamp to zero and under-fill FAILED_SLOTS vs the pre-dynamic contract. Align denominators: subtract dynamic planned count, pass static-only launched counts, or compute missing slots from manifest NDJSON vs returned ALL_OUTPUT_FILES instead of STATIC_INTENDED minus total launched.
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## risk-integration: scripts/scout-dynamic-archetypes.sh:83-120

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] scout input files are concatenated before launch-claude-subprocess.sh so launcher context validation and size caps do not apply. A large diff can bypass the intended 256 KB context cap and make the Sonnet scout timeout or consume excessive context. Validate diff/scope/plan files with the same non-symlink/root/size constraints before catting them, or pass them through --context-files; add oversized and symlink fixture tests.
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## risk-integration: scripts/test-scout-dynamic-archetypes.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Prompt-body `</reviewer_` injection guard has no regression test. A future edit could drop or typo the jq `contains("</reviewer_")` check while all harness cases still pass, re-opening frontmatter/wrapper corruption risk the plan called out. Add a fixture whose `prompt_body` includes `</reviewer_` and assert `SCOUT_STATUS`/warnings and empty-or-filtered manifest per the script contract.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## architecture: Branch diff vs feature_description / implementation_plan

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] PR bundles ship-pr lint-fix-loop implement SKILL upgrade-larch SECURITY Makefile and larch-logs flushes beyond listed scout+dispatch files. Reviewers cannot trace a single cohesive plan scope; unrelated regressions risk shipping with the feature. Split unrelated changes into separate PRs or expand the authoritative plan to cover every touched subsystem.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## architecture: skills/review/SKILL.md:5153-5175 (diff)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 4 fenced review-scout-manifest snippet omits required log-phase.sh --run-id/--log-root. log-phase.sh fails argument validation when operators paste the documented exact pattern. Mirror other Step 4 log-phase.sh calls: pass --run-id "$RUN_ID" and the same --log-root as sibling batches.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## architecture: skills/review/scripts/dispatch-panel.sh:197-249

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] derive_scout_status_from_manifest treats any {"archetypes":[]} manifest as SCOUT_STATUS=empty when scout-roundN-status.env is absent. Second dispatch-panel run without the sidecar mis-labels prior parse-failed/claude-failed/timeout runs (all write the same empty JSON) as empty scout success. Persist authoritative SCOUT_STATUS beside the manifest whenever scout runs, or embed status in the manifest JSON so reuse does not collapse failure modes to empty.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:454-470

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] New lint-fix path leaves errexit enabled in ship-pr.sh, which is intentionally written to capture helper failures manually. After LINT_FIX_STATUS=applied, a still-failing run-relevant-checks-captured.sh aborts at out=$(...) before rc capture and stateful stall handling. Restore the original shell options after the lint-fix subprocess or avoid set -e entirely while capturing fix_rc.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:532-555 scripts/ship-pr.sh:915-928

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Only the final successful lint-fix delta file is staged after multi-attempt CI repair. If attempt 1 creates fixture-a.txt and attempt 2 creates fixture-b.txt, only fixture-b.txt is staged, so the pushed commit can omit files required by the local passing check run. Accumulate all lint-fix delta path files across attempts or recapture all dirty paths after the passing verification before git add.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:532-557; scripts/ship-pr.sh:911-931

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: [important] CI lint-fix staging can omit current dirty files. Multiple lint-fix attempts or untracked-only fixes can pass local checks, but earlier deltas or untracked files are not staged before the CI fix commit/push. After checks pass, recapture all current dirty paths including untracked files and stage that complete set.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: skills/review/scripts/collect-findings.sh:330-380

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Fallback retry reviewer labels with combined suffixes are not normalized before validation. A recovered phase2 reviewer output named dyn-foo-output-phase2-retry.txt keeps that label, fails the *-output.txt validation, and all of its findings are silently skipped. Strip repeated -phase2, -phase3, and -retry suffixes before reattaching .txt, matching tally-code-votes.sh normalization.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:227-245; scripts/scout-dynamic-archetypes.sh:69-75

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: [important] Scout invocation is fail-hard for validation failures despite the non-fatal scout contract. Dynamic archetypes on a diff over 256 KB make scout-dynamic-archetypes.sh exit 2, causing dispatch-panel.sh to abort before launching the static panel. Wrap scout execution with set +e, write an empty manifest/status on nonzero scout exits, and continue static dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: skills/review/scripts/review-core.sh:258-263; scripts/dispatch-with-waterfall.sh:316-323

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] Dynamic reviewer waterfall failures still trip global DISPATCH_OK=false and abort the round. A single failed dyn-foo-output-phase3.txt can produce REVIEW_CORE_STATUS=panel-failed even when every static reviewer succeeded. Emit failed slot IDs or static/dynamic dispatch status and only hard-fail for static dispatch failures or static threshold failures.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## correctness: skills/review/scripts/tally-code-votes.sh:400-415

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Yield TSV second pass increments totals for all score_rows rows without filtering kind/terminal outcomes OOS rows and exonerated/neutral in-scope outcomes inflate findings_total while leaving findings_accepted low, so yield_ratio mis-ranks archetypes and misreports “findings” volume Restrict aggregation to kind=finding and align ratio with documented semantics (or add explicit columns for OOS/neutral/exon)
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## risk-integration: scripts/scout-dynamic-archetypes.sh:138-141

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unbounded DESCRIPTION_TEXT is embedded into the scout prompt in description mode. A huge description can balloon memory/CPU/time for the Sonnet scout subprocess and degrade or stall the review host. Apply a byte cap with truncate-or-fail and align with other context size limits.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## risk-integration: scripts/scout-dynamic-archetypes.sh:69-75; skills/review/scripts/dispatch-panel.sh:235-245

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Scout input validation can hard-exit before publishing a non-fatal scout status, and dispatch-panel does not catch that failure. With --dynamic-archetypes enabled on a branch whose diff or plan exceeds 256 KB, the scout exits 2 and the entire review panel aborts before static reviewers run. Catch scout nonzero exits in dispatch-panel, write an empty scout manifest/status, and add an oversized-diff regression harness proving static slots still dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:504-557; scripts/ship-pr.sh:915-928

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] Only the final lint-fix delta is staged after multi-attempt CI repair. Attempt 1 creates an untracked file required for checks, attempt 2 makes the final tracked fix, checks pass locally, but the attempt-1 file is omitted from the commit and CI fails again. Accumulate all applied lint-fix delta files or recapture the full post-success dirty path set, including untracked files, before staging.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## risk-integration: scripts/test-scout-dynamic-archetypes.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Scout harness only exercises --mode diff; description mode is untested despite contract support. A bad change to description-mode argv handling or prompt wrapping could ship with green CI until a real /review description run. Add at least one description-mode success and one validation-failure case mirroring diff-mode coverage.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## risk-integration: skills/review/SKILL.md:59-85

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] review-scout-manifest is logged under $REVIEW_TMPDIR/larch-logs instead of the canonical larch-log root. The scout batch can be deleted during cleanup or never appear under larch-logs/review/<RUN_ID>/ despite the run-log contract. Use the same canonical log root as the other review batches or rely on LARCH_LOG_ROOT instead of overriding with REVIEW_TMPDIR.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## security: scripts/ship-pr.sh:25-33,scripts/ship-pr.sh:903-928

- **Reviewer**: codex-specialist-security-output.txt
- **Concern**: [important] CI-fix commit path stages untracked dirty files from external fixers A CI fixer leaves an untracked .env, debug log, raw test artifact, or token-bearing file; capture_dirty_paths includes it and git add -- commits/pushes it during ship-pr Keep vendor CI commits to tracked modifications by default, or require an explicit allowlist/manifest plus secret/path-deny checks before staging untracked files
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## security: skills/review/scripts/dispatch-panel.sh:144-161,skills/review/scripts/dispatch-panel.sh:197-261

- **Reviewer**: codex-specialist-security-output.txt
- **Concern**: [latent] Cached scout manifests bypass the scout validator before prompt synthesis A resumed or corrupted review tmpdir contains an invalid scout-roundN-manifest.json; dispatch-panel trusts it and writes invalid YAML/frontmatter or prompt content into a dynamic reviewer agent Validate cached manifests with the same schema rules before synthesis and synthesize only validated ok manifests
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## architecture: skills/review/SKILL.md:5314-5315

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Wrapper prose about scout reuse/sentinel is easy to misread vs per-round scout-round<N> filenames Operators may misunderstand whether multi-round standalone /review re-scouts when ROUND_NUM increments Align wording with dispatch-panel.md filenames and per-round semantics
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## correctness: scripts/scout-dynamic-archetypes.sh:70-73

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Scout context validation only allows files under PLUGIN_ROOT or the scout output directory, while /implement passes PLAN_FILE from the parent IMPLEMENT_TMPDIR via skills/review/scripts/dispatch-panel.sh:264-268 and skills/review-and-fix/scripts/review-and-fix.sh:592-610. Opting into dynamic archetypes during /implement causes the scout to fail validation and dispatch no dynamic reviewer slots. Allow the parent session directory derived from SESSION_ENV_PATH or IMPLEMENT_TMPDIR, or copy the plan file into REVIEW_TMPDIR before scout invocation.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/scout-dynamic-archetypes.sh:70-73, skills/review/scripts/dispatch-panel.sh:264-279

- **Reviewer**: codex-specialist-security-output.txt
- **Concern**: [important] Scout context validation rejects plan files outside the scout output directory. In an implement review round, PLAN_FILE is under $IMPLEMENT_TMPDIR/design-export/plan.txt while scout output is under $IMPLEMENT_TMPDIR/round-N, causing SCOUT_STATUS=validation-failed and zero dynamic reviewer slots. Allow the validated caller/session root from --session-env-path, or stage/copy plan context under the round directory before invoking the scout.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:85-99; scripts/ship-pr.sh:950-971

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] Vendor dirty paths are captured but not used when staging the CI-fix commit, so untracked vendor-created files are omitted. A CI fixer adds a new fixture file, checks pass locally, but git add stages only tracked dirty files and lint-fix delta untracked files; the pushed commit lacks the fixture and CI fails again. Stage the union of tracked dirty paths, vendor dirty paths, and lint-fix delta paths after validating untracked paths are intended.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: skills/review/SKILL.md:27; skills/review/references/heavy-worker.md:87-96

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: [important] Subagent review path does not explicitly parse and bind scout KVs returned by the heavy worker. /review --diff --subagent --dynamic-archetypes 4 --run-id X can run the scout in the worker, then Step 4 sees SCOUT_STATUS unset or na and skips the review-scout-manifest batch. Add explicit parent-side parsing and assignment for SCOUT_STATUS, DYNAMIC_SLOTS, SCOUT_MANIFEST, and YIELD_TSV_FILE before Step 4.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:145-161

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] rationale is inlined as a single-line YAML-ish field while prompt_body uses a block scalar; scout validation does not constrain rationale shape. Scout can return multi-line or special rationale text that disrupts the synthesized agent markdown/YAML envelope or weakens delimiter clarity versus prompt_body. Format rationale as a block scalar (mirroring prompt_body) and/or extend scout + scout_manifest_is_valid to reject newlines and standalone --- lines in rationale.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:29-73; skills/review/scripts/review-core.sh:30-62

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: [important] Empty LARCH_DYNAMIC_ARCHETYPES_MAX is treated as unset instead of invalid. LARCH_DYNAMIC_ARCHETYPES_MAX= silently resolves to 0 and disables dynamic reviewers although the plan requires env values to match ^[0-4]$ and fail with exit 2 otherwise. Distinguish unset from set-empty, validate before applying the default, and add the empty-env regression test.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:305-316

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Reuse path derives SCOUT_STATUS from manifest when scout-roundN-status.env is missing; derive maps any valid {"archetypes":[]} to empty. Second dispatch or lost sidecar: prior parse-failed/timeout/claude-failed runs that wrote the same empty JSON as intentional empty scout can be mis-labeled SCOUT_STATUS=empty, corrupting telemetry and operator interpretation. Persist authoritative scout status alongside the manifest (or embed status in manifest JSON) and read that on reuse instead of inferring from empty archetypes alone.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## correctness: skills/review/scripts/tally-code-votes.sh:400-409

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [latent] findings_total ignores neutral and exonerated in-scope findings despite the plan requiring yield grouping over score_rows A reviewer with 1 accepted and 9 exonerated findings is reported as total=1 yield=1.000000 instead of total=10 yield=0.100000 Count every in-scope score_rows result toward total while keeping accepted and rejected counters separate; update skills/review/scripts/test-tally-code-votes.sh:348-378
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## risk-integration: scripts/scout-dynamic-archetypes.sh:70-75; skills/review-and-fix/scripts/review-and-fix.sh:592-614; scripts/run-step5-review.sh:104-147

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Dynamic scouting rejects the normal /implement plan-file layout because the scout only allows context files under the plugin root or the round output dir. With LARCH_DYNAMIC_ARCHETYPES_MAX=4 in /implement, PLAN_FILE points at $IMPLEMENT_TMPDIR/design-export/plan.txt while scout output lives under $IMPLEMENT_TMPDIR/round-N, so scout validation fails and dispatch-panel emits SCOUT_STATUS=validation-failed with zero dynamic slots. Allow the caller tmpdir from SESSION_ENV_PATH/IMPLEMENT_TMPDIR, or copy plan/feature context into the round dir before invoking the scout; add a nested /implement regression.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## architecture: scripts/scout-dynamic-archetypes.md:12-13 vs scripts/scout-dynamic-archetypes.sh:25-26

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Contract says the scout always uses launch-claude-subprocess.sh while the implementation allows an executable override. Security reviewers reading only the contract may omit auditing the substituted binary. Update scout-dynamic-archetypes.md to describe SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH and its trust implications.
- **Suggested revision**: Address the concern above.

