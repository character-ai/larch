# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `skills/review/scripts/aggregate-findings.sh` now accepts attestation-only duplicate merges as `REASON=ok` with a whitespace-only persisted ballot instead of `REASON=validation-exhausted`. Pseudo-headings combined with attestation are explicitly rejected via the new `nonconforming_heading_with_attestation` narrow-trigger. Closes #2939; reverses the #2782-encoded behavior and completes the #2881 plan.
- `scripts/ship-pr.sh` `run_rebase_rebump` no longer dead-locks in a CHANGELOG.md conflict loop when `OLD_VERSION == NEW_VERSION` (origin/main advanced via non-bump commits so classify-bump returned the same version we just dropped). After `drop-bump-commit.sh` removes the stale bump, the new `ship_pr_stage_rebump_bullets` helper extracts the `## [OLD]` body to `$IMPLEMENT_TMPDIR/.rrr-rebump-bullets.md` and invokes the new `scripts/drop-changelog-commit.sh` primitive to strip the companion `Update CHANGELOG for OLD` commit before the rebase replays. `ship_pr_commit_changelog_after_rebump` then reconstructs the entry under the new version via `write_changelog_entry` (hoisted from `scripts/implement-finalize.sh` to `scripts/lib-changelog.sh` so both callers share it), and falls back to the legacy commit-changelog.sh insertion when origin/main already published `## [NEW]` to keep the duplicate-heading guard from firing. Closes #2952 Bug A.
- `scripts/ship-pr.sh` `run_rebase_rebump` now calls `scripts/refresh-run-logs.sh` before `drop-bump-commit.sh` so any pending tracked `larch-logs/` writes are committed first. This closes the Guard-1 false-positive window where a prior step left a tracked log file modified-but-uncommitted, making the dropper refuse with `DROPPED=false` and a Guard-1 warning that the stall handler routed to `exit_stall`. Closes #2952 Bug B.
- `skills/review/scripts/aggregate-findings.sh` collapses its outer Cursor → Codex → Claude waterfall to a single Codex-primary slot, opting in to `dispatch-with-waterfall.sh --require-result-pattern '^(### FINDING_[0-9]+:|[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)'` so Cursor `--mode plan` narration-only outputs route through the dispatcher's internal phase-2/phase-3 fallback while valid empty-merge attestation outputs still pass the gate and reach the post-dispatch validator. The `### FINDING_` branch stays strict; leading whitespace is tolerated only on the attestation branch. `LARCH_AGGREGATE_MAX_OUTER_PHASES` and the `PHASES_ATTEMPTED` stdout key are removed; the test harness rewrites the `waterfall_*` cases and the `LARCH_AGGREGATE_MAX_OUTER_PHASES=1` cases. Narrow-trigger validator failures (`preamble_finding_substring`, `nonconforming_heading_with_attestation`) now terminate as `REASON=validation-exhausted` immediately at the aggregate-findings layer, and adjacent consumer surfaces are updated while preserving the downstream `REVIEW_CORE_STATUS=aggregator-validation-exhausted` contract. Closes #2881.
- `scripts/dispatch-with-waterfall.sh` accepts `--require-result-pattern <regex>` so callers can require a `STATUS=OK` result file to match a structural ERE; misses route through the existing phase-1 → phase-2 → phase-3 fallback. The decomposition aggregator (`skills/design/scripts/decompose-aggregator.sh`) and 8-slot panel (`skills/design/scripts/decompose-panel-dispatch.sh`) opt in with `^[[:space:]]*## Recommendation`, the aggregator's single-slot primary tool switches from Cursor to Codex, and `panel-outputs.ndjson` rows now reflect the dispatcher's resolved final paths (`ALL_OUTPUT_FILES_PATH`) so phase-2/phase-3 fallback content reaches operator presentation. `STATUS=cap_hit` bypasses the gate (token-budget skip stays terminal); invalid ERE patterns exit **2** before any slot launches. Closes #2865.
- Codex per-bucket token accounting now stays visible across launcher, `token-report`, and `/design` final-summary paths; per-bucket Codex cost rendering no longer emits misleading blended-rate warnings when `BUCKETS_codex` is populated.
- test-aggregate-findings, test-launch-review, test-append-tool-failure: unset `LARCH_EXECUTION_ISSUES_LOG` and related vars at harness entry so synthetic aggregator warnings do not append to a parent `/implement` execution-issues log.
- /implement — Create the feature branch at the start of Step 0 plan materialization (regression from #2588 / #2598; pre-existing dispatcher main-branch-prohibited guard exposed the gap).
- `breadcrumb-monitor.sh` no longer exits immediately on a pre-created surfaced or done sentinel: both checks now require non-empty content (`[ -s ]`) so monitor blocks until Family B script actually exits, preventing step-jumping (e.g., `ship-pr.sh` starting before `review-and-fix.sh` finished). `lib-quiet.sh:larch_quiet__exit_write_done` writes `EXIT_CODE=N` content (not just a touch) atomically; the surfaced-file touch in `larch_quiet_init` also writes content. Every Family B script (`ship-pr.sh`, `ci-wait.sh`, `run-step5-review.sh`, `review-and-fix.sh`, `run-step2-dispatch.sh`, `step2-implement.sh`, `collect-agent-results.sh`, `dispatch-with-waterfall.sh`, `dispatch-plan-voters.sh`) now installs `larch_quiet_append_done_trap` after sourcing `lib-quiet.sh`, ensuring the EXIT trap writes the done sentinel. New `scripts/test-breadcrumb-monitor.sh` harness covers the empty/non-empty sentinel paths and end-to-end coupling (`test-harnesses-18`). Closes #2826.

### Changed

- `/design`: remove Step 2b.5 optional plan-size prompts and retire the file-count metric; only hard `PLAN_LINES` / `DIFF_LINES` thresholds remain, while `--partition` routes directly to the decomposition panel (#2805).
- Restore Codex-first defaults for `/implement` Step 2 and fixer dispatch: omitted `--coder` defaults to Codex in `skills/implement/scripts/step2-implement.sh`, `### Implementer waterfall` in `skills/implement/SKILL.md` prefers Codex → Cursor → Claude, `review-and-fix.sh` and `lint-fix-loop.sh` try Codex before Cursor, with harness and cross-doc updates (`SECURITY.md`, `docs/linting.md`, sibling `.md` contracts). Closes #2756.
- `/design`: re-print the plan candidate at Step 3 entry (first-time only) and Gate C entry, with a large-plan summary mode controlled by `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` (default 120).
- **`/design` finalize split + upstream OOS filing** — Step 5 is now **finalize** (5a reviewer status, **5b** `/larch:issue` batch for accepted non-security OOS with `[OOS]` prefix + `file-design-oos.sh`, **5c** `larch:plan` write / publish / `[DESIGNED]` rename); Step **6** is tmpdir **cleanup** only (`cleanup-tmpdir.sh`). `/implement` Step 9a.1 skips design OOS blocks that already carry `- **Filed URL**:`; disposition counting for design-side GitHub URLs follows the structured Filed URL list lines from `[42.0.10]` (not incidental prose), while `oos-disposition-gate.sh` still accepts repeated `--filed-urls-file` arguments to **union** those extracted lists with implement tmp artifacts such as `oos-issues-created.md` (not a Description-URL bypass).
- **`/implement` admission precondition**: issues without a `[DESIGNED]` prefix are rejected with `ADMISSION_RESULT=missing-designed-prefix` at exit 5, requiring a completed `/design` run before `/implement` may proceed.
- **Migration posture**: legacy `[IN PROGRESS]` and `[PLANNED]` prefixes are stripped by `strip_lifecycle_prefix` for backward compatibility but are no longer accepted as `--state` values by `tracking-issue-write.sh` or as admission-pass prefixes.
- **Audit scope**: workflow call sites and rename `--state` surfaces in the active runtime tree (`skills/`, `scripts/`, `agents/`, `.claude/`, `docs/`, tests) now use the new prefix set; deliberate legacy bracket literals remain only where migration, admission recovery, strip helpers, or hermetic fixtures require them. This Unreleased section documents the migration and may name the old prefixes. Historical shipped changelog bodies and `larch-logs/` were not bulk-retitled.

## [42.6.3] - 2026-05-27

### Changed

- Closed: #2935

## [42.6.2] - 2026-05-26

### Changed

- Closed: #2957

## [42.6.1] - 2026-05-26

### Changed

- Fixed get-issue-state flag parsing so missing or flag-looking values fail instead of looping.
- Split Codex JSONL event capture from wrapper diagnostics in lint-fix, negotiation, and review-fix paths, then record sanitized token-ledger usage buckets.
- Kept raw events.jsonl artifacts local while allowlisting scout-archetype-yield.tsv for committed round logs.
- Updated docs, security notes, and regression harnesses for the parser, telemetry, and artifact publication contracts.

## [42.6.0] - 2026-05-26

### Changed

- Add manual_gate_b persistence to run-params and cover default, true, false, and invalid values
- Thread /design --manual/-m through the skill prompt, flag reference, and router recovery path
- Refactor Gate B so auto-apply and manual Apply all both share the named Apply-all body
- Update design docs and structural pins for the new auto-apply default

## [42.5.43] - 2026-05-26

### Changed

- Accept attestation-only aggregate empty merges as REASON=ok with MERGED_COUNT=0 and whitespace-only persisted findings.
- Reject attestation plus malformed pseudo-heading output through the new nonconforming_heading_with_attestation narrow trigger.
- Update aggregate-findings tests, sibling docs, SECURITY.md, and CHANGELOG.md for the #2939 empty-merge contract.

## [42.5.42] - 2026-05-26

### Changed

- Added vendor-path failed-job verification before CI-fix pushes, including local replay, repair dispatch, final sweep, and ci-local-unfixable bail handling.
- Threaded failed-jobs TSVs and vendor return codes through run_ci_fix_vendor and run_evaluate_failure so head-changed and sweep-regression outcomes keep their existing routing.
- Made _RCC_MAX_ITER the actual captured-command fix-loop ceiling with safe clamping and a bounded per-job/vendor verification default via LARCH_CI_LOCAL_FIX_ITER.
- Expanded ship-pr harness coverage for vendor verification, rc propagation, empty TSV fallback, max-iteration behavior, and section-boundary execution.

## [42.5.41] - 2026-05-26

### Changed

- Added vendor-path failed-job verification before CI-fix pushes, including local replay, repair dispatch, final sweep, and ci-local-unfixable bail handling.
- Threaded failed-jobs TSVs and vendor return codes through run_ci_fix_vendor and run_evaluate_failure so head-changed and sweep-regression outcomes keep their existing routing.
- Made _RCC_MAX_ITER the actual captured-command fix-loop ceiling with invalid-value clamping and raised per-job/vendor verification defaults via LARCH_CI_LOCAL_FIX_ITER.
- Expanded ship-pr harness coverage for vendor verification, rc propagation, empty TSV fallback, and max-iteration behavior, and updated sibling docs.

## [42.5.40] - 2026-05-26

### Changed

- Closed: #2958

## [42.5.39] - 2026-05-26

### Changed

- Verified the Phase 3 phase_plan_materialize implementation already present on the branch
- Applied the larch-logs Mermaid lint exclusion to explicit pre-commit filename inputs
- Added regression coverage for explicit larch-logs Mermaid lint skips

## [42.5.38] - 2026-05-26

### Changed

- Closed: #2962

## [42.5.37] - 2026-05-26

### Changed

- Closed: #2898

## [42.5.34] - 2026-05-26

### Changed

- `/implement` and `/design` terminal summaries now always surface the per-agent cost breakdown (`💰 TOTAL ~$X.XX — Claude $X.XX, Codex $X.XX, Cursor $X.XX  |  Tokens: Xk`) on every terminal outcome. Adds `--cost-unavailable` to `render-run-summary.sh`, two-stage degraded fallback to `write-final-report.sh`, degraded path and Phase=post single-print to `render-final-summary.sh`, Step 17/18 sentinel mechanics in `skills/implement/SKILL.md`, NEVER #20 forbidding free-form recap summaries, and parameterized regression test matrices. Closes #2837.

## [42.5.31] - 2026-05-26

### Changed

- Closed: #2823

## [42.5.30] - 2026-05-26

### Changed

- Add repeatable --context-files support to launch-claude-review.sh with strict explicit-path validation, canonical dedup, and allow-root propagation.
- Extend launcher and validator regression harnesses plus sibling docs for the new public context-file surface.
- Document the security contract and make the validator Perl timeout fallback immune to locale-warning help-capture pollution.

### Changed

- Closed: #2675

## [42.5.27] - 2026-05-26

### Changed

- Accepted same-branch, ancestor-preserved coder commits in lint-fix-loop when the pre-dispatch baseline is clean.
- Added prefix-aware forbidden-path enforcement for committed coder deltas plus residual working-tree forbidden cleanup.
- Updated lint-fix-loop, ship-pr, security, and linting docs/tests for the new applied-with-head-changed contract.

## [42.5.26] - 2026-05-26

### Changed

- Closed: #2878

## [42.5.24] - 2026-05-26

### Changed

- Closed: #2830 — Fixes #2830: Require file-backed gh body payloads

## [42.5.23] - 2026-05-26

### Changed

- Add a Bash 3.2-safe retry helper for empty or UNKNOWN mergeStateStatus reads
- Retry the initial merge-state read 4 times and route recovered BEHIND through main_advanced with empty ERROR
- Extend merge-pr docs and offline harness coverage for persistent and transient initial UNKNOWN states

## [42.5.19] - 2026-05-26

### Changed

- Parse Mermaid sanitizer REASON_TOKEN values by stripping the prefix and truncating at metadata whitespace while preserving embedded equals signs.
- Strip C0 and DEL control bytes from gh stderr diagnostic lines before relaying ci-failed-jobs.sh failures.
- Document both input-sanitization contracts and add regression harness coverage for production-shape reason lines, embedded equals tokens, fallback behavior, and control-byte stderr passthrough.

## [42.5.17] - 2026-05-25

### Changed

- Closed: #2853

## [42.5.18] - 2026-05-25

### Changed

- Closed: #2848

## [42.5.15] - 2026-05-25

### Changed

- Harden script issue-number boundaries with numeric self-validation before gh calls
- Validate non-empty tracking sentinel ISSUE_NUMBER and RUN_ID values with fixed-token malformed-value errors
- Add and wire offline regression coverage for the new validation contracts
- Derive Step 7a base_remote/base_ref once from forked_target and use it for the small/non-runtime classifier, generator, and 7a.r rebase probe.
- Add --base-remote/--base-ref support and validation to generate-code-flow-diagram.sh while preserving origin/main defaults.
- Cover fork-mode classifier skip and generator invocation paths in the Step 7a harness, and update sibling docs plus structural lint guards.

## [42.5.14] - 2026-05-25

### Changed

- Rewrote the make test-step-7a linting inventory row to use qualitative coverage prose without hardcoded case counts.
- Documented sanitizer rejection-token behavior as placeholder summary posting and included the missing diagram-failure-sanitizer, rebase-unexpected-rc, and quiet-diagram-skip-contract coverage categories.

## [42.5.13] - 2026-05-25

### Changed

- Codex launchers now consume --json usage events and record uncached input, cached input, output, and total buckets instead of aggregate-only totals.
- Added a shared fail-closed Codex usage parser with docs and offline coverage for schema variants, cache math, wrapper noise, and failure branches.
- Updated launcher and token-report harnesses to assert per-bucket Codex accounting, empty records on parse failure, and stderr-only auth classification.

## [42.5.12] - 2026-05-25

### Changed

- Closed: #2790

## [42.5.11] - 2026-05-25

### Changed

- Add step-7a.sh to consolidate Step 7a diagram generation, summary upsert, rebase checkpoint, and pre-bump log flushing
- Collapse the /implement Step 7a SKILL.md body to one foreground helper invocation with documented KV output
- Add an offline Step 7a regression harness and wire it into Makefile/docs lint inventory
- Extend foreground-marker linting for the new foreground-only step-7a.sh denylist case

## [42.5.10] - 2026-05-25

### Changed

- Implemented the Step 0 phase_tracking state machine in implement-bootstrap.sh, including repo/fork skips, Branch 1 sentinel resume, Branch 2 adoption, deferred metadata handling, tracking bails, and branch-aware final KV output.
- Added --forked-target session-env propagation and --run-id support in post-tracking-issue.sh so successful adoption writes the selected RUN_ID into parent-issue.md.
- Updated /implement docs and bootstrap contracts, and expanded the offline bootstrap harness to cover tracking success, skip, bail, deferred, mismatch, and malformed sentinel paths.

## [42.5.8] - 2026-05-25

### Changed

- Added inline manifest schema templates and jq self-validation to both generated implementer prompts.
- Added dispatcher recovery for malformed complete manifests with prelaunch baselines, NUL-safe recovery paths, post-implementer safety gates, and manifest quarantine metadata.
- Added shared plan-scope extraction plus pathspec-based commit support so recovery commits can avoid unrelated staged content.
- Documented the recovery trust boundary and covered the prompt, dispatcher, scope extraction, and pathspec commit paths with offline harnesses.

## [42.5.13] - 2026-05-25

### Changed

- Added a shared judge vote/rating parser and per-round findings-classification TSV emission with stable 21-column rows and vN_tool identity columns.
- Updated plan-review voter dispatch, prompts, retry wording, docs, and design-log publishing so the new classification artifact is produced and safely staged.
- Added regression coverage for parser edge cases, TSV row shape, fallback tool identity, MainAgent rules, and plan-review publish allowlisting.

## [42.5.4] - 2026-05-25

### Changed

- Closed: #2800

## [42.5.3] - 2026-05-25

### Changed

- Closed: #2787

## [42.5.2] - 2026-05-25

### Changed

- Closed: #2757

## [42.4.22] - 2026-05-25

### Changed

- Reject empty aggregate outputs when nonempty input findings existed, even if the empty-merge attestation is present.
- Retry the outer aggregation waterfall on the then-new empty-merge validation token.
- Update aggregate regression coverage and SECURITY.md to document the fail-closed invariant.

## [42.4.21] - 2026-05-25

### Changed

- Replace Step 2b.5 Split-path stub with a real 8-slot decomposition panel wired through dispatch-with-waterfall.
- Add decompose helpers (panel dispatch, aggregator merge, partition filing + redacted close) and normative decompose-panel.md reference.
- Register offline harnesses, topology rows, and design-structure anchors so the new flow stays mechanically pinned.

## [42.4.20] - 2026-05-25

### Changed

- Stop duplicate OOS/FINDING ballot headings when each reviewer restarts numbering by splitting markdown at any FINDING or OOS heading before dedup.
- Make Step 0b and flags.md spell out design_classification tokens so write-run-params and tier copy stay aligned with the persisted JSON field.
- Read design_classification (not .classification) when rendering final-summary mode so operators see TRIVIAL_DOC_ONLY / SIMPLE / HARD instead of N/A.
- Document CODE-only FINDING vote lines in voter parse-rate helper and list RUN_ID in tracking-issue-read --sentinel stdout contract.

## [42.4.19] - 2026-05-25

### Changed

- Add breadcrumb stream plumbing in lib-quiet (categories, done trap hook, surfaced sentinel) plus streaming redaction and a wc-offset breadcrumb-monitor consumer.
- Repurpose lint-foreground-markers to require background plus paired breadcrumb-monitor in fenced examples and reject stale foreground phrasing when the new pair is present.
- Refresh Family B skill and reference markdown to document the five-path env contract and paired Bash tool pattern so operators stop relying on brittle foreground-only harness behavior.

## [42.4.18] - 2026-05-24

### Changed

- Restore Codex as the default external implementer when `--coder` is omitted so Step 2 matches the stricter sandbox-first posture operators expect (#2756).
- Run review-fix and lint-fix Codex dispatch before Cursor so behavior matches the SKILL.md implementer waterfall.
- Re-pin the step2 dispatcher harness to assert the codex default via non-git cwd (exit 2) instead of a stubbed Cursor path.

## [42.4.17] - 2026-05-24

### Changed

- Closed: #2752

## [42.4.16] - 2026-05-24

### Changed

- **`/design --brainstorm`**: public `--brainstorm` flag, Step **1d.5** brainstorm panel between Round 1 and Gate A, `brainstorm_requested` in `run-params.json`, additive `brainstorm.md` reads in Steps 2a / 2a.5 / 2b / 3 (including plan-review feature-context merge).
- Catch drift between documented ship-pr state keys and write_initial_state emits before it confuses operators.
- Anchor the Required keys bullet list with stable HTML comment markers for deterministic extraction.
- Document the two-source set-equality contract in the implement-structure harness readme.

## [42.4.15] - 2026-05-24

### Changed

- Document how plan-ballot Claude voting via `scripts/launch-claude-review.sh` changes subprocess data paths and trust boundaries versus the old in-process Agent voter.
- Clarify where redaction runs (publish boundary) and how `.dirty-tree` and wrapper sidecars backstop read-only expectations without a CLI sandbox on this wrapper.
- Cross-link dispatcher and timing helpers so operators can reconcile this section with the existing External tool delegation / Claude Voter 1 note.

## [42.4.14] - 2026-05-24

### Changed

- Ensure tally abort paths always leave a readable `voting-tally.md` stub so design-local artifacts never strand FINALIZE.
- Treat `voting-tally.md` like other may-be-empty finalize inputs while still rejecting symlinks and non-regular files.
- Backstop the plan-review loop with a non-empty tally stub when the inner tally exits non-zero without emitting a file.

## [42.4.13] - 2026-05-24

### Changed

- String-key clustering on plan-review TSV columns collapses almost nothing when reviewers rephrase the same underlying concern.
- The /design plan-review path has no LLM aggregator; explicit prose steers orchestrators toward semantic grouping by meaning.
- A sixth NEVER rule and mindset count update keep the anti-pattern list internally consistent for operators skimming SKILL.md.

## [42.4.11] - 2026-05-24

### Changed

- Route four rebase checkpoints through rebase-checkpoint-probe.sh with bundled post-rebase phantom handling
- Add phantom-probe-with-warn.sh for Step 2 and Step 8 standalone probes plus shared lib-phantom-probe.sh
- Thin SKILL.md macro/probe prose to wrapper contracts and extend Makefile, lint, and harness coverage

## [42.4.10] - 2026-05-24

### Changed

- Move ship-pr cold-start state composition into scripts/ship-pr.sh so Step 8+ no longer needs a separate heredoc Bash call.
- Add seven argv per-key flags plus --force-init-state with resume vs rewrite semantics and CR/LF validation.
- Document the contract in scripts/ship-pr.md, update skills/implement/SKILL.md Step 8+ invoke and NEVER #11/#16, and extend scripts/test-ship-pr.sh coverage.
- Add implement-bootstrap.sh to consolidate /implement Step 0 infrastructure (branch check, entry gate, session setup, session-env, rehydrate) into one foreground script.
- Collapse SKILL.md Step 0 calls #1–#5 into a single implement-bootstrap invocation with KV parsing and failure routing.
- Register Family B foreground denylist entry, Makefile harness shard 7, docs/linting.md row, and offline harness for phase_infra + NEVER#14 + breadcrumb invariants.

## [42.4.8] - 2026-05-24

### Changed

- Align operator docs with the post-2714 token cost pipeline and shared run-summary renderer (non-dollar `--summary`, dollar line only via `render-run-summary.sh`, no removed `/fix-issue` callers on `token-cost.sh`).
- Document full `Outcome` bullet coverage and dual `/implement` + `/design` final-summary write and tracking-comment paths in run logs and `write-final-report.md`.
- Fix Bash 3.2 `set -u` empty-array expansion in `render-final-summary.sh` so `/design` finalization works on macOS system Bash.

## [42.4.7] - 2026-05-24

### Changed

- Add Gate B semantic duplicate-content sweep instructions after plan revisions
- Specify the unconditional dedup-sweep breadcrumb and distinct-context repetition carve-out
- Move /design Step 3 orchestration into plan-review-loop.sh so scout through tally stay script-owned and testable.
- Launch plan Voter 1 via launch-claude-review.sh inside dispatch-plan-voters.sh and share parse-rate helpers through lib-voter-parse-rate.sh.
- Add aggregate-findings --input-mode plan for relaxed merged-output severity checks on plan ballots.
- Refresh design/review docs, SECURITY subprocess note, Makefile harness shard, and regression harnesses (BSD-grep-safe design-structure pins).

## [42.4.6] - 2026-05-24

### Changed

- Align /design terminal output with /implement so one rendered summary owns cost and PR/review bullets differ by skill.
- Strip duplicate dollar lines from token-report --summary and remove implement chat-tail prints so operators see the template once.
- Add render-final-summary.sh with pre/post publish phases, upsert decoupling, and offline coverage via test-render-final-summary.

## [42.4.5] - 2026-05-24

### Changed

- Expand the design review-budget invoke harness so CI catches jq, grep, and default branches in read-design-review-budget.sh without relying on the happy path alone.
- Cover invoke-plan-validator-if-not-quick.sh env and argv failures, the no-run-params quick skip, and a full-tier defects-found run using the existing demo-plan fixture.
- Document the added scenarios in the sibling contract markdown while keeping the make target instructions unchanged.
- **`/design` Gate B (#2730)** — After revising `plan.txt` from accepted plan-review findings (apply-all, go-through-each batch, or one-by-one completion), the orchestrator performs a semantic duplicate-content sweep on the revised plan before `ACTION=EMIT_PLAN`, rewrites via the Write tool, and prints `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (documented in `skills/design/references/approval-gates.md`).

## [42.4.4] - 2026-05-24

### Changed

- Closed: #2718

## [42.4.1] - 2026-05-24

### Changed

- Document the read-design-review-budget and invoke-plan-validator harness so operators can find it next to the plan-command parser and validator rows.
- Order the harness table like the Makefile: parse-plan-commands, read-design-review-budget-invoke, then validate-plan-commands.
- Align external voter documentation and rendered prompts with the same YES↔EXONERATE tie-break used in quick-mode acceptance guidance.
- Add a structural harness check so prose drift in any of the four canonical locations fails CI early.
- Document the new harness obligation in the test-design-structure contract for operators scanning scope.

## [42.4.0] - 2026-05-24

### Added

- `external_classify_launch_failure` helper in `scripts/lib-external-launcher-common.sh` — emits `LAUNCHER_FAILURE_CLASS` (`none`/`health`/`other`) and `LAUNCHER_FAILURE_REASON` (`auth`/`binary-missing`/`health-probe`/`timeout`/`parse`/`refusal`/`unknown`) KVs, classifying launcher exits into health vs non-health failures.
- All three CI launchers (`launch-cursor-ci.sh`, `launch-codex-ci.sh`, `launch-claude-ci.sh`) emit `LAUNCHER_FAILURE_CLASS` and `LAUNCHER_FAILURE_REASON` on every exit via the new helper, including `health`/`binary-missing` before `die()` on binary-not-found paths.
- `/implement` Step 8+ Exit 3 branch: autonomous main-agent CI-fix sub-procedure (12 steps) fires when `BAIL_REASON=first-fixer-non-health`, with sentinel+counter guard (cap 3), `gh-run-logs.sh` capture with redaction, explicit `git add`, `refresh-run-logs.sh` parity, and re-invoke of `ship-pr.sh`.

### Changed

- `ship-pr.sh` `run_ci_fix_vendor()`: when the first-tier fixer (Cursor) returns `LAUNCHER_FAILURE_CLASS=other`, short-circuit the waterfall — skip remaining tiers and set `BAIL_REASON=first-fixer-non-health` rather than wasting tokens on backup fixers unlikely to succeed; `BAIL_NEEDS_USER_INPUT` is NOT set on this path.

## [42.3.0] - 2026-05-24

### Changed

- Closed: #2674

## [42.2.0] - 2026-05-24

### Changed

- Closed: #2683

## [42.1.0] - 2026-05-24

### Changed

- Add /design plan-size thresholds and Step 2b.5 so large plans route to split/cancel flows before review proceeds.
- Introduce -p/--partition (persisted in run-params.json) with pre-Step-0 mutual exclusion against --trivial.
- Wire Gate B and post-plan discussion to re-run the threshold check after every EMIT_PLAN revision.
- Document semantic sprawl Split/Cancel hooks in discussion-rounds Step 1c/1d and extend plan-review prompt heading guidance.

## [42.0.23] - 2026-05-24

### Changed

- Emit exact-match BAIL_REASON fix-attempts-exhausted at the FIX_ATTEMPTS cap so ship-pr exit 3 matches the documented operator-input contract.
- Ground CI-fix vendor prompts with a shared topology.tsv and generate-topology-docs fragment, and persist final bail reasons into the committed run log via restore-finalize-state.
- Add regression coverage for vendor-loop exhaustion (exit 4), larch-log final-bail-reason batch wiring, and fix-only topology.tsv sentinel checks across CI launchers.

## [42.0.22] - 2026-05-24

### Changed

- Flush implement run 4C3541E6-C95E-4489-B974-A1A173232D1B log artifacts for issue #2673.
- fix(ship-pr): `admin_failed` + "Base branch was modified" now routes to `run_rebase_rebump` instead of stalling at 12d.
- Raise `run_rebase_rebump` retry cap from 5 to 20.
- Voter prompt YES↔EXONERATE boundary: replace single-line proportionality note with multi-paragraph framing across `plan-review.md` voter prompts and `dispatch-plan-voters.sh`.

## [42.0.21] - 2026-05-24

### Changed

- Prevent /design summary-halts after /larch:issue returns so Step 5c plan write, publish, and [DESIGNED] rename still run.
- Make intra-Step-5 sub-step boundaries explicit in the anti-halt reminder and add a Step 5b continuation banner aligned with other steps.
- Record the Skill-tool sub-skill vs parent terminal-output rule in orchestrator-never.md and lock it in with structural tests.
- `/design` — mechanical plan-size thresholds (`check-plan-size.sh`), Step **2b.5** after each `ACTION=EMIT_PLAN`, and `-p` / `--partition` persistence via `run-params.json` (#2670).

## [42.0.20] - 2026-05-23

### Changed

- Plan review gains a fail-open scout plus panel dispatcher so Step 3 can run 10 static slots plus up to twelve dynamic Cursor/Codex pairs grounded in the plan's Files-to-modify scope.
- Scout-dynamic-archetypes now honors a PLUGIN_ROOT-only optional prompt override with explicit validation, regression coverage, and contract docs aligned to the plan-review wrapper.
- Merged review findings must include a Severity line on every FINDING block so aggregation stays compatible with future multi-round plan-review convergence work.

## [42.0.19] - 2026-05-23

### Changed

- Phase 1 cross-agent `@./` include probe did not meet Branch A (Claude did not surface SCARLET-FOX-9412 from INCLUDED.md; Codex fixture run errored), so CONVENTIONS.md extraction was skipped.
- Trimmed AGENTS.md under the 11000-byte budget by shortening three long Conventions bullets while preserving CI anchor literals and SKILL.md pointers.
- Dropped redundant inline blurbs from a few self-descriptive Canonical sources entries to reclaim space without changing semantics.

## [42.0.18] - 2026-05-23

### Changed

- Make Step 5 capture-file KV parsing safe under set -e so the review loop no longer exits when a key is missing from the current line.
- Detect malformed checks and lint captures with stderr plus fail-closed checks semantics where the loop already expects them.
- Add a parsers-only harness slice, docs, and a Makefile shard target so CI can run the regression cheaply.

## [42.0.17] - 2026-05-23

### Changed

- Clarify in the /design plan-review prompt that the plan describes post-merge state so reviewers stop reporting current-code gaps the plan already proposes to fix.
- Document the plan-vs-current-state invariant beside the renderer contract and lock it in with the existing archetype×vendor harness substring check.

## [42.0.16] - 2026-05-23

### Changed

- CI recovery now runs Cursor, Codex, and Claude once per outer attempt with fresh gh-run-logs captures and redacted failure logs only when safe.
- Single-baseline rollback reverts tier-introduced dirt while preserving pre-existing dirty paths and skipping submodule gitlinks with Warnings visibility.
- Outer vendor attempts drop from five to three with clearer backoff commentary and Bash 3.2-safe empty-array expansion for launcher argv.
- Fix-loop harness exercises tier order, failure-log gates, rc=3 deferral, missing Claude launcher, and macOS-friendly grep plus argv logging before option parsing.

## [42.0.15] - 2026-05-23

### Changed

- Closed: #2641

## [42.0.14] - 2026-05-23

### Changed

- Primary #2638 waterfall, substring guard, review-core stall path, and docs were already on this branch; verified aggregate/review-core/review-and-fix harnesses and relevant-checks.
- Persist IRF_LAST_ROUND_STATUS into each round review-and-fix.env so the Step 5 handoff matches disk artifacts operators and tests can grep.
- Extend the aggregator-validation-exhausted harness to assert that persisted IRF line alongside stdout KVs.

## [42.0.13] - 2026-05-23

### Changed

- Closed: #2643

## [42.0.12] - 2026-05-23

### Changed

- Closed: #2637

## [42.0.11] - 2026-05-23

### Changed

- Closed: #2395

## [42.0.10] - 2026-05-23

### Changed

- Foreground-marker lint for Family B denylisted script examples in skill/rules Markdown (`scripts/lint-foreground-markers.sh`, `make lint-foreground` / `make lint-foreground-markers`, pre-commit hook) with regression harness `test-lint-foreground-markers`; authoring rules in `BASH_AUTHORING.md` §4.
- Disposition gate now counts design-side GitHub URLs only from structured Filed URL list lines, closing the incidental-Description-URL loophole.
- /design persists and restores OOS filing sentinels across sessions via ~/.cache/larch/design-oos-filed/<issue>.md with an operator clear-cache flag.
- Offline harnesses cover strict loose union semantics and cross-session cache edge cases.

## [42.0.9] - 2026-05-23

### Changed

- Move accepted non-security OOS filing upstream into /design Step 5b so URLs land before the larch:plan write, with a sentinel and annotate helper mirroring /implement patterns.
- Split /design Step 5 into finalize (5a–5c) versus Step 6 cleanup-only so breadcrumbs and registry names match what operators actually run.
- Let /implement skip design-pre-filed OOS blocks and union multiple disposition-gate URL files so design-side Filed URL lines satisfy the gate alongside implement tmp artifacts.
- Document the workflow in README, skills, lifecycle, and CHANGELOG; wire Makefile test-file-design-oos into the harness shard used by lint.
- Fix shellcheck/agent-lint issues in the new helper and structure tests (case patterns, grep quoting, SKILL harness pins).

## [42.0.7] - 2026-05-23

### Changed

- Closed: #2622
- Fold operator-facing review tally vocabulary to accepted / rejected / exonerated (subset of rejected) while preserving internal classifier and scoreboard math.
- Emit KV and JSON with updated schema versions, enforce exonerated ≤ rejected before JSON writes, and keep internal NEUTRAL_COUNT accounting without surfacing neutral as a public finding outcome.
- Refresh voting-protocol, run-log docs, implement/review skill references, and offline harnesses to match the new tally envelopes and summaries.

## [42.0.6] - 2026-05-22

### Changed

- Absorb Step 5 multi-round control into Bash: new sourced loop module plus run-step5-review loop/single/mav-apply dispatch and shared degraded-round cap library.
- Collapse implement SKILL.md Step 5 to a single run-step5-review --mode loop invocation with token-aware STEP5_REVIEW_STATUS branching; drop duplicate tally/findings-full composition prose.
- Refactor review-and-fix.sh with _implement_round_body, optional KV suppression for the loop, per-round pre/post coder heads, gate counters on review-and-fix.env, classifier-failure return path, and main entry guard.

## [42.0.5] - 2026-05-22

### Changed

- Lead dialectic debate prompts with OUTPUT FORMAT plus steelman as a sixth required tag to stop truncation after steelman-only preludes.
- Document per-side Cursor/Codex assignment and a Cursor/Codex-to-Claude per-side waterfall with corrective prompts via render-debate-retry-prompt.sh.
- Register retry timing-task kinds, extend design structural tests, and refresh dialectic fixtures for the six-tag quorum gate.

## [42.0.4] - 2026-05-22

### Changed

- Clear inherited LARCH_EXECUTION_ISSUES_LOG, SESSION_ENV_PATH, and IMPLEMENT_TMPDIR at the start of aggregate-findings, launch-review, and append-tool-failure harnesses so synthetic warnings never append to a parent /implement execution-issues log.
- Add a Shape A regression that runs aggregate-findings behind the same unset prelude under a deliberately contaminated outer env and asserts the sentinel log stays absent or empty.
- Document the fix under CHANGELOG Unreleased Fixed.

## [42.0.3] - 2026-05-22

### Changed

- Closed: #2616

## [42.0.2] - 2026-05-22

### Changed

- Closed: #2613

## [42.0.0] - 2026-05-22

### Changed

- Closed: #2590

## [41.0.2] - 2026-05-22

### Changed

- Make /design standalone-only: remove SESSION_ENV_PATH and nested-mode branches across SKILL.md and references.
- Establish CLAUDE_PLUGIN_ROOT in Step 0a via loader-expanded export before session-setup; simplify Bash preludes to the PID-keyed source line plus timing-ledger only.
- Simplify tally-plan-review.sh to design-local artifacts only; drop parent tmpdir OOS handoff and implement tally-batch flush dead code.
- Tighten CI with negative greps (A1-A4) and an ordering check (A5) for the Step 0a export vs session-setup.

## [41.0.1] - 2026-05-22

### Changed

- Closed: #2594

## [41.0.0] - 2026-05-22

### Changed

- Remove the round-trip body detector and its title marker to stop false positives from ordinary English in issue bodies.
- Simplify tracking-issue lifecycle renames and finalize/ship-pr callers by dropping the detector pipeline and Makefile harness.
- Update docs, agent-lint exceptions, and offline tests so the tree no longer references the removed surface outside CHANGELOG and larch-logs.
- Align `/design` with standalone-only session wiring: drop nested-mode / `SESSION_ENV_PATH` handoffs, keep plan-review tally and accepted OOS under `$DESIGN_TMPDIR`, and refresh design/implement docs, `tally-plan-review` tests, and structure harness pins for the new contract.

## [40.0.0] - 2026-05-22

### Changed

- Drop /implement user argv for dynamic archetypes so the cap is only env and caller session-env, matching the real orchestrator contract.
- Trim the Step 5 code-review breadcrumb by removing the redundant degraded-round parenthetical; runtime caps are unchanged.
- Remove stale /implement --auto delegator language and fix /alias to forward argv without the removed flag.
- Sync subskill-invocation Pattern B and test pins; quote redacted TMPDIR placeholders in two flushed design logs so shellcheck passes CI.

## [39.0.2] - 2026-05-22

### Changed

- Key the stable `/design` session-env symlink on Claude PID (`$PPID`) so concurrent `/design` runs across working-tree clones no longer share one global path.
- Teach `write-design-current-env.sh` `--claude-pid`, keep a legacy unkeyed symlink plus `WARNING=` stderr when omitted, and pass `--claude-pid "$PPID"` from Step 0 with PID-keyed preludes throughout `skills/design/SKILL.md`.
- Extend `test-write-design-current-env.sh` (two-PID isolation, invalid PID, shim) and `test-design-structure.sh` probes; refresh `AGENTS.md`, `SECURITY.md`, and the writer contract doc.

## [39.0.1] - 2026-05-22

### Changed

- Closed: #2586

## [39.0.0] - 2026-05-22

### Changed

- Replace dev-only `.claude/skills/relevant-checks/` with consumer `scripts/relevant-checks.sh`; `run-relevant-checks-captured.sh` now emits `RELEVANT_CHECKS_SKIPPED=true` when the script is absent so downstream automation can detect skips (`RELEVANT_CHECKS_SKIPPED` migration sentinel for operators and fork CI).
- Closed: #2588

## [38.0.0] - 2026-05-22

### Changed

- Remove six rarely-used skills and their harnesses so the shipped plugin surface stays focused on core workflows.
- Retire /review description-mode auto-issue filing in favor of local artifacts plus manual /issue follow-up now that umbrella batching is gone.
- Rename analyze-issues fixture category wording and scrub docs or temp-path names so acceptance greps stay clean without rewriting CHANGELOG or run logs.
- Adjust the Makefile shard-coverage script labels and temp basenames so invariant scans never false-positive on the removed /umbrella skill token.

## [36.0.8] - 2026-05-22

### Changed

- Add `[PLANNED]` lifecycle prefix to tracking-issue rename so `/design` signals plan completion.
- Introduce `design-log-publish.sh` to flush `/design` session tmpdirs into `larch-logs/design/<run-id>/` via a disposable git worktree, `[skip ci]` commit, and admin squash-merge PR.
- Wire `/design` Step 0b/5b and the clarify path to parse `SESSION_ID`, rename on completion, and publish logs.
- Exclude `[PLANNED]`-prefixed issues from `/fix-issue` managed-lifecycle lock to avoid picking up active design sessions.
- Add offline harnesses for tracking-issue-write `planned` state and design-log-publish happy/edge/failure paths.

## [36.0.6] - 2026-05-22

### Changed

- Closed: #2487

## [36.0.3] - 2026-05-21

### Changed

- Treat /design as a prerequisite peer that anchors larch:plan in the issue body instead of a nested /implement sub-invocation.
- Shorten AGENTS.md SendMessage and session-env bullets into tier-scoped and NEVER #14 pointers.
- Update workflow-lifecycle, run-logs, README, and agents docs for issue-anchored materialization and remove retired --design-only and catalog flag rows.

## [36.0.2] - 2026-05-21

### Changed

- Align SessionStart health copy and regression harness with the retired post-/design boundary so operators are not pointed at dead hook paths.
- Delete harness cases that only asserted non-emission of a removed advisory and drop banned literal pins from the four acceptance-scanned files.
- Keep bump-boundary and cleanup-suppression cases meaningful by anchoring tmpdir resolution on review-round-summary fixtures where the resolver requires a manifest marker.

## [36.0.1] - 2026-05-22

### Changed

- Cache installed site-packages in `test-harnesses` CI shards to skip `pip install` on cache hits; install only `pyyaml==6.0.2` via a new `requirements-test-harnesses.txt` (dropping `pre-commit` from the harness install path).
- Rebalance 20 `test-harnesses` Makefile shards using actual CI wall-clock timing (LPT greedy), targeting ~30 s per shard and isolating the four slowest tests as solo shards.

## [35.0.0] - 2026-05-21

### Changed

- Cut over /design and /implement to issue-anchored GitHub plan blocks with preflight audit and clarify flow (issue #2485).
- Drop public --panel from review-and-fix; keep internal hard panel for review-core; extend clarify-label with --create-if-missing.
- Deprecate post-design-boundary and neutralize hooks; add editorial harnesses and satisfy agent-lint allowlist.

## [34.0.23] - 2026-05-21

### Changed

- Closed: #2549
- Audit report titles now end the bracket with a space before Report so generic report-prefix filtering matches them without a second title-shape guard.
- The audit-runs skill anti-recursion search pattern and harness expectations follow the new bracket layout.
- /fix-issue relies on the audit-report label plus has_report_prefix after removing the redundant run-logs audit title helper.

## [34.0.22] - 2026-05-21

### Changed

- Closed: #2552

## [34.0.21] - 2026-05-21

### Changed

- Retire legacy unified hard panel and hard review panel labels so Step 5 reads as plain review-and-fix plus review panel wording.
- Tighten the quick-mode docs-sync harness to four byte-pinned anchors and keep topology generator notes aligned with the harness.
- Refresh README and docs mirrors so public copy matches the canonical SKILL.md Step 5 breadcrumb and tally guidance.

## [34.0.19] - 2026-05-21

### Changed

- Add a mechanical oos-disposition gate so accepted non-security OOS items cannot clear OOS_PENDING without filed issues or Inline-triage commit breadcrumbs.
- Document terminal disposition rules and NEVER-list enforcement in the implement skill next to the Step 8+ OOS checkpoint.
- Add an audit-runs oos-silent-drop scan for retroactive detection in committed run logs.
- Register the gate harness in the Makefile and pin key prose in test-implement-structure.sh.
- Closed: #2544

## [34.0.18] - 2026-05-21

### Changed

- Orphan-drop guard now diffs against pre-fetch origin/main so a post-fetch squash merge cannot hide pure larch-log flush stacks.
- Document the pre-fetch SHA contract next to the larch-logs-only reset behavior.

## [34.0.17] - 2026-05-21

### Fixed

- Treat empty aggregator output (no FINDING blocks) as success so duplicate-only reviews do not fail validation.
- Normalize trailing parentheticals on reviewer slot labels before matching input slots, covering LLM suffixes such as coverage notes.
- Document the validator behavior and lock both shapes in the offline harness.

## [34.0.16] - 2026-05-21

### Changed

- Avoid redundant gh release edit when the selected release is already latest and not a pre-release.
- Document RELEASE_ALREADY_LATEST and align the private release skill with the new early-exit contract.

## [34.0.15] - 2026-05-21

### Changed

- OOS disposition gate and `oos-silent-drop` audit scan now honor `oos-issues.ndjson` URLs, explicit rejected-OOS markers, tighter security `focus-area` detection, and git-log Inline-triage aligned with the gate's revision walk (with a narrow artifact fallback when git is unavailable); merge-base-empty branches use `origin/main..HEAD` when `origin/main` resolves.
- Closed: #2539

## [34.0.14] - 2026-05-21

### Changed

- Document step8b_rebase conflict recovery through the same Phase 1-2 + local Phase 4 loop as early_rebase so non-bump conflicts can be resolved before PR creation.
- Dispatch Phase 4 exit 0 back into the Rebase + Re-bump Sub-procedure with rebase_already_done=true so step 8b keeps postbump force-push ownership without a reviewer panel in Phase 3.
- Leave step8_apply_bump_same_version on plain --no-push with immediate stall on conflict, matching the narrowed scope for that caller.

## [34.0.11] - 2026-05-21

### Changed

- Closed: #2524

## [34.0.10] - 2026-05-21

### Changed

- Closed: #2521

## [34.0.8] - 2026-05-21

### Changed

- Prevent manifest rows from widening glob expansion beyond a safe path grammar.
- Let the offline harness point the verifier at a synthetic TSV via LARCH_VERIFY_MANIFEST.
- Document the override so future harness authors know the supported escape hatch.

## [34.0.7] - 2026-05-21

### Changed

- Closed: #2523

## [34.0.6] - 2026-05-21

### Changed

- Closed: #2511
- Record `NS_RETRY_REASON=` tokens in `*-ns-retry*.txt.meta` sidecars and emit a sorted `reasons` histogram on `ns-retry-sidecars` audit NDJSON lines for operators and tooling (#2521).
- Run-log completeness manifest and verification no longer treat `oos-issues.ndjson` as a required-file-presence row; Step 9a.1 coverage still gates `run-statistics.md` and related checks (#2522).

## [34.0.5] - 2026-05-21

### Changed

- Point aggregator failure execution issues at committed round-relative stderr paths when nested under a session, instead of ephemeral TMPDIR paths.
- Treat plugin version lag in audit cache-freshness scans as informational and document the self-deploying lens banner for audit reports.
- Allowlist aggregator stderr for write-round commits and gate them in the run-log completeness manifest only when the matching aggregator failure signals appear.

## [34.0.4] - 2026-05-21

### Changed

- Closed: #2514

## [34.0.3] - 2026-05-21

### Changed

- Closed: #2506

## [34.0.2] - 2026-05-21

### Changed

- Add GitHub-backed helpers so issue bodies and comments can carry larch plan and clarification markers ahead of a future /implement cutover.
- Ship offline harnesses plus Makefile shard wiring so plan-block parsing, clarify posting, and clarify state logic stay regression-safe under make lint.
- Refresh issue-anchored-plan.md so the wire-format doc matches the new scripts while still marking skills integration as pending.
- Register new Makefile-only scripts in agent-lint suppressions to match existing harness policy.

## [34.0.0] - 2026-05-21

### Changed

- Closed: #2495

## [32.0.0] - 2026-05-21

### Changed

- Closed: #2481

## [31.0.0] - 2026-05-21

### Changed

- Closed: #2493

## [30.0.0] - 2026-05-21

### Changed

- Closed: #2497

## [29.8.63] - 2026-05-21

### Changed

- Closed: #2498

- Closed: #2490

## [29.8.61] - 2026-05-20

### Changed

- LLM-merge cross-reviewer findings before voting with safe degradation and LARCH_AGGREGATOR_DISABLED=1 escape hatch
- Credit each comma-separated reviewer slot on the competition scoreboard after merged ballots
- Emit review-findings-full JSONL schema_version 2 with reviewer_slots arrays split from attribution lines
- Stop byte-level dedupe in collect-findings so distinct same-title rows survive until aggregation

## [29.8.60] - 2026-05-20

### Changed

- Closed: #2479

## [29.8.59] - 2026-05-20

### Changed

- Closed: #2475

## [29.8.58] - 2026-05-20

### Changed

- Closed: #2472

## [29.8.56] - 2026-05-20

### Changed

- Unify /implement and /fix-issue terminal summaries behind a shared renderer so operators see the same fields, sentinel, and optional per-vendor cost semantics every run.
- Route final markdown through write-final-report with --print-stdout, persist post-plan flags for accurate mode display, and refresh final-summary on every pre-push log refresh without waiting for PR_URL.
- Document per-vendor rate env vars, run-log final-summary shape, and tighten structure tests plus agent-lint exclusions for Makefile-only harnesses.

- Empty invocations should follow the same since-last-audit PR window instead of failing on usage alone.
- Prior audit-report discovery and frontmatter errors stay aligned with the explicit since-last-audit path.
- Refresh the SKILL contract and offline harness so docs and tests describe the same default.
## [29.8.55] - 2026-05-20

### Changed

- Closed: #2469

## [29.8.54] - 2026-05-20

### Changed

- Closed: #2462
- Closed: #2456

## [29.8.51] - 2026-05-20

### Changed

- Reject non-canonical review headings so JSONL category stays aligned with the five focus-area tags used downstream.
- Document the whitelist contract next to the category field so consumers know empty means unknown or malformed extraction.
- Lock in OOS fixtures for mangled headings versus valid tags so regressions surface in the compose harness.
- Closed: #2438
- Closed: #2455

## [29.8.50] - 2026-05-20

### Changed

- Closed: #2454

## [29.8.49] - 2026-05-20

### Changed

- Closed: #2446

## [29.8.48] - 2026-05-20

### Changed

- Closed: #2439

## [Unreleased]

### Fixed

- RST changelogs with a leading `=========` document title: `auto-resolve-changelog.sh` now merges the first real section (e.g. `Unreleased`) instead of treating the document banner as the merge anchor, so `CHANGELOG.rst` / bare `CHANGELOG` rebase conflicts auto-resolve in `ship-pr.sh` without invoking the vendor. `run_rebase_rebump` falls back to the orchestrator `CONFLICT_FILES` CSV when `git rebase --continue` leaves no `diff-filter=U` paths. Cursor/Codex resolve-conflict launchers validate `--conflict-files` segments and fence the path list in the vendor prompt.
- Restore multi-voter `classify_result` exoneration in `scripts/lib-vote-tally.sh` (two-path rule: no-`NO` panels and mixed panels where `EXONERATE` meets or beats `NO` and exceeds `YES`), fixing mis-tallies after the narrow condition in PR #2428 (#2446).

### Changed

- **Breaking (downstream JSONL consumers)**: `scripts/compose-review-findings.sh` now emits `review-findings-full.jsonl` rows with `schema_version` and `reviewer_slots` instead of a string `reviewer` field. Parsers must accept both shapes when reading mixed committed logs (see `docs/run-logs.md` and `scripts/compose-review-findings.md`).
- Document the `review-and-fix.sh` applied-fixes contract change: accepted findings applied by the coder now complete with exit `0` plus `REVIEW_AND_FIX_STATUS=fix-applied`, and `review-and-fix-summary.json` now records `.status = "fix-applied"` instead of the old `fix-required`/exit-3 checkpoint shape. External wrappers, jq filters, and dashboards must key on the new status fields rather than exit `3`.
- Extend the plan-voter harnesses to cover healthy Codex/Cursor dispatch and retry-path waterfall promotion, so phase-2/phase-3 structured retry outputs cannot be dropped silently.
- Align description-mode specialist prompts with diff-mode’s pinned single-bullet finding grammar, and enforce the full scout closing-sentence repair in both code and tests.

## [29.8.44] - 2026-05-20

### Changed

- Closed: #2439
- Closed: #2442

## [29.8.43] - 2026-05-20

### Changed

- Closed: #2440

## [29.8.40] - 2026-05-20

### Changed

- Closed: #2429
- Closed: #2432
- Closed: #2434

## [29.8.39] - 2026-05-20

### Changed

- Closed: #2421

## [29.8.38] - 2026-05-20

### Changed

- Closed: #2420

## [29.8.37] - 2026-05-20

### Changed

- Closed: #2419

## [29.8.36] - 2026-05-20

### Changed

- Closed: #2416

## [29.8.35] - 2026-05-20

### Changed

- Closed: #2417

## [29.8.34] - 2026-05-20

### Changed

- Closed: #2418

## [29.8.33] - 2026-05-19

### Changed

- Closed: #2408

## [29.8.32] - 2026-05-19

### Changed

- Closed: #2409

## [29.8.31] - 2026-05-19

### Changed

- Align first-pass code-voter prompts with the retry prompt so voters are told to verify silently, avoid tools during verification, and emit only structured vote lines.
- Add harness greps on the generated claude vote prompt so the directive strings cannot drift unnoticed.

## [29.8.30] - 2026-05-19

### Changed

- Harmonized the code-voter first-pass prompt contract in Phase 2 of #2396 so voters may read the ballot and bounded diff/plan context files for silent verification while still emitting only `FINDING_N: VOTE` lines.
- Closed: #2398

## [29.8.29] - 2026-05-19

### Changed

- Closed: #2406

## [29.8.28] - 2026-05-19

### Changed

- Closed: #2396

## [29.8.27] - 2026-05-19

### Changed

- Fix compose-review-findings reviewer attribution by extracting canonical body reviewer metadata before falling back to panel.
- Add round_num to review-findings-full JSONL records and include per-round OOS findings with out_of_scope outcomes.
- Extend compose-review-findings regression coverage and update shipped docs for the expanded schema.

## [29.8.26] - 2026-05-19

### Changed

- Closed: #2380

## [29.8.25] - 2026-05-19

### Changed

- Closed: #2386

## [29.8.23] - 2026-05-19

### Changed

- Closed: #2375

## [29.8.22] - 2026-05-19

### Changed

- Closed: #2394
- Closed: #2390

## [29.8.19] - 2026-05-19

### Changed

- Closed: #2378

## [29.8.18] - 2026-05-19

### Changed

- Allow larch-log write-round to commit scout raw-output sidecars alongside scout manifests.
- Document scout raw sidecar preservation and committed round-log behavior.
- Cover raw sidecar preservation in scout tests and committed write-round copying in larch-log tests.
- Reserve Claude-only implementation for plans with at most three estimated diff lines so routine work stays on Codex or Cursor by default.
- Keep operator-facing breadcrumbs and Step 2 routing copy consistent with the stricter carve-out boundary.

## [29.8.17] - 2026-05-19

### Changed

- Closed: #2372

## [29.8.16] - 2026-05-19

### Changed

- Closed: #2376

## [29.8.15] - 2026-05-19

### Changed

- Closed: #2361

## [29.8.14] - 2026-05-19

### Changed

- Closed: #2367

## [29.8.13] - 2026-05-19

### Changed

- Closed: #2363

## [29.8.12] - 2026-05-19

### Changed

- Closed: #2355

## [29.8.11] - 2026-05-19

### Changed

- Closed: #2366

## [29.8.10] - 2026-05-19

### Changed

- Closed: #2356

## [29.8.3] - 2026-05-18

### Changed

- Add one-shot voter parse-rate retries with structured-vote prompt reinforcement and per-slot parse-rate status keys
- Add voter parse-rate degraded tally banners and normalize scoreboard live rows to short names with populated Status
- Extend dispatch and tally regression harnesses for retry success/failure, degraded banners, and scoreboard consistency

## [29.7.0] - 2026-05-18

### Changed

- Rebalanced the 16 Makefile test-harness shard lines from freshly measured harness timings using LPT bin-packing
- Preserved test-harness-shards-coverage as the first prerequisite on shard 12 and verified shard inventory coverage
- Added --no-logs-commit to missing /implement and /fix-issue argument hint/listing surfaces

## [29.6.1] - 2026-05-18

### Fixed

- `merge-pr.sh` no longer stalls Step 12d when `mergeStateStatus=UNKNOWN` immediately after the flush-commit force-push recovery. The post-force-push path now retries `gh pr view` up to 3 times (5s sleep) to absorb GitHub's transient post-push `UNKNOWN` propagation delay before failing closed (closes #2342).

## [29.6.0] - 2026-05-18

### Changed

- Add a Bash 3.2 portability authoring rule and linter for Bash 4+ constructs.
- Wire make lint-bash32 and its regression harness into local lint and the harness shards.
- Document the linter and add narrow suppressions for intentional static portability patterns.

## [29.3.12] - 2026-05-18

### Fixed

- Emit the anti-read-poll reminder only on the third identical read within the active window, and remove path echoing from the reminder payload.
- Preserve inner `###` headings inside rejected code-review finding bodies when composing `review-findings-full.md`.
- Count rejected findings from `rejected-findings-full.md` when present and fail closed if the optional log-copy write cannot be persisted.

## [29.3.11] - 2026-05-18

### Changed

- Disable agnix AS-014 with a repository-specific false-positive note.
- Rewrite GitHub host bash regexes to use [.] instead of escaped dots.
- Verify the fix with the targeted harness, relevant checks, agent-lint, and strict agnix.

## [29.1.35] - 2026-05-17

### Changed

- Derived code-review tally accepted/rejected counts from the composed review-findings-full markers and added a mismatched-count regression.
- Removed unconditional larch-log flush tail calls from git commit/amend primitives and synchronized lifecycle/logging documentation, including SECURITY.md.
- Added Step 8a no-summary-bullets diagnostics for manifest path, manifest existence, and implementer tool.

## [29.1.34] - 2026-05-17

### Changed

- Preserve per-round review diagnostics in committed run logs for post-run analysis
- Retain high-value setup and Codex implementation artifacts through the existing consolidated log flush
- Redact oversized or sensitive sidecar fields before durable log writes

## [29.1.23] - 2026-05-17

### Changed

- Rebalanced CI test harnesses from 11 shards to 13 shards in Makefile and CI workflow matrix.
- Moved the two heavy harnesses into a new shard 13 and split the former shard 11 inventory across shards 11 and 12.
- Updated the shard coverage guard and docs so the partition guard can live first in shard 12 while later heavy-test shards follow.

## [29.1.11] - 2026-05-17

### Changed

- Added HARD-path plan-review-tally flushing from tally-plan-review.sh into the parent implement run logs.
- Mirrored token-ledger marks beside the Step 2, Step 3, Step 5, and Step 6 timing-ledger marks.
- Updated sibling contracts and extended the tally regression harness for the new batch write.

## [29.1.9] - 2026-05-17

### Changed

- Replace fail-open voting-quorum (accept-all when fewer than 2 judges) with a four-tier diversity-preserving policy in `scripts/lib-vote-tally.sh` and `skills/review/scripts/tally-code-votes.sh`: 3 judges → 2+ YES accept; 2 judges → 2/2 unanimous accept; 1 judge → single-judge binding; 0 judges → main-agent-vote-required
- Mirror the same four-tier logic in `skills/design/scripts/tally-plan-review.sh`
- Add loud degraded-panel warnings (judge list, missing reason, accept rule) to `scripts/dispatch-code-voters.sh` and `scripts/dispatch-plan-voters.sh` when eligible judges drop below 3
- Wire the 0-judge `main-agent-vote-required` exit status through `skills/review-and-fix/scripts/review-and-fix.sh` and the `/implement` and `/design` orchestrators
- Add test coverage for tiered quorum logic in `scripts/test-lib-vote-tally.sh`, `skills/review/scripts/test-tally-code-votes.sh`, and `skills/design/scripts/test-tally-plan-review.sh`
- Update `docs/voting-process.md`, `skills/shared/voting-protocol.md`, and `docs/point-competition.md` to document the four-tier policy

## [29.1.8] - 2026-05-16

### Changed

- Extract execution-issues hashing and NDJSON composition into scripts/lib-execution-issues.sh for shared finalize and pre-bump use
- Add flush-execution-issues.sh with idempotent Step 7a pre-bump append behavior and larch-log failure capture
- Wire the pre-bump execution-issues flush into /implement docs, Makefile shard coverage, and regression harnesses

## [29.1.6] - 2026-05-16

### Changed

- Updated review competition wording and voting docs from the stale 2-voter conditional tie-breaker model to the unconditional 3-voter panel model.
- Made reviewer scoreboards symmetric for OOS findings by tracking neutral/exonerated and rejected OOS outcomes and subtracting rejected OOS from reviewer score.
- Aligned /review diff-mode round cap reporting to 5 rounds and expanded focused harnesses for the new OOS-rejected scoring columns.

## [29.1.5] - 2026-05-16

### Changed

- Moved Step 2, Step 3, Step 5, and Step 6 timing marks into the worker scripts that receive the real session tmpdir.
- Added best-effort Step 5 run-log flushing for code-review-tally and review-findings-full from review-and-fix.sh.
- Updated sibling contracts and extended review-and-fix coverage for successful batch flushing without stdout leakage.

## [29.1.4] - 2026-05-16

### Changed

- Removed the detect-wholesale-rejection review helper, contract, harness, Make target, and review-core integration.
- Changed zero-accepted review rounds to converge normally instead of returning wholesale-rejected exit status.
- Scrubbed wholesale-rejection protocol references from review docs, implement handling, voting protocol, reviewer prompts, and pre-rendered reviewer bodies.

## [29.1.3] - 2026-05-16

### Changed

- Remove the Claude coder fallback from `review-and-fix.sh`; the dispatch chain is Codex → Cursor only.
- Replace the broken `cursor-agent --print --prompt` invocation with the repo-standard `cursor agent -p --trust --workspace "$PWD"` shape, sourced through `lib-cursor-launcher-common.sh` for model/auth args.
- Fail closed on `SCRUB_OK=false` from `scrub-submodule-paths.sh` instead of collapsing to `CODER_STATUS=skipped`.
- Extend `post_dispatch_submodule_revert` to scan untracked paths via `git status --porcelain` and `rm -f` files under submodule roots.
- Add `.rs` and `.toml` to the `scrub-submodule-paths.sh` extension allowlist.
- Align `scripts/test-review-structure.md` contract markdown with the harness's `orchestrator-judge.md` / `voting.md` non-existence assertions.

## [29.1.1] - 2026-05-16

### Changed

- Replace review-and-fix call-fixer enumeration with Codex, Cursor, and Claude-subagent coder dispatch plus schema version 2 summary fields.
- Add scrub-submodule-paths.sh and post-dispatch submodule revert handling to enforce the triple-layer submodule guard.
- Delete call-fixer artifacts and update review, implement, security, docs, Makefile, and harness contracts for the new review-fix flow.

## [29.0.4] - 2026-05-15

### Changed

- Add shellcheck to the lint job SKIP environment list
- Update lint job comments to describe agnix and shellcheck as parallel dedicated jobs
- Update the shellcheck job header to remove Phase 1 and Phase 2 rollout language

## [29.0.3] - 2026-05-15

### Changed

- Guard the post-plan router so hard mode always persists POST_PLAN_WORKFLOW_PATH=HARD

## [29.0.2] - 2026-05-15

### Changed

- Removed the plugin-directory fallback for REPO_ROOT and LARCH_LOG_REPO_ROOT so non-git callers leave those values empty.
- Added an explicit larch-log commit failure when PWD is outside a git worktree.
- Updated larch-log contracts and added a focused regression for the outside-git commit guard.

## [29.0.0] - 2026-05-15

### Changed

- Export IMPLEMENT_TMPDIR before Step 18 transcript capture so post-merge sentinel checks see the run tmpdir.
- Add default-branch/main commit refusal to larch-log commit and a traceable suppressed-default-branch transcript status.
- Extend larch-log and transcript capture harnesses plus sibling docs for the new guards.
- Add a dependency-free runtime cache-key audit script for implement session transcripts.
- Document the analyzer contract and stable-prefix classification rules in a sibling script doc.
- Wire make audit-cache-keys-runtime RUNS=N and verify it over 10 recent implement runs with zero cache-invalidating findings.

## [27.6.28] - 2026-05-15

### Changed

- Warn when external implementers leave working-tree paths outside their manifest declaration.
- Strengthen implementer scope discipline prompts and keep generated agent prompts in sync.
- Document the warning-only scope-drift detector in the dispatcher and security trust model.

## [27.6.26] - 2026-05-15

### Changed

- Added /review-and-fix to README.md and docs/skills.md as an internal review helper
- Added the hard review-and-fix panel topology row and regenerated docs/topology.md
- Replaced stale SKILL.md line references in docs/external-reviewers.md with stable script references
- Added finalize-state write-prohibition assertions to the /implement structure harness
- Pinned Step 18 restore-before-teardown command ordering and helper/library contracts
- Updated the harness sibling doc to describe the finalize-state teardown coverage

## [27.6.25] - 2026-05-15

### Changed

- Switch execution-issues, review-findings, and oos-issues append batches to the json-lines sanitizer.
- Add larch-log append-path regression coverage proving raw markdown records are rejected for all three batches.
- Document the append-mode NDJSON contract in the batch table and test harness sibling docs.

## [27.6.21] - 2026-05-15

### Changed

- Thread manifest started_at into the report-token cache and parsed records.
- Add per-day markdown cost trend tables for Total, Claude, Codex, and Cursor across SIMPLE and HARD workflows.
- Document the new trend-table output in the run-analysis script contract.
- Add a pre-teardown restore-finalize-state helper that rebuilds finalize-state.sh from ship-pr-state.sh and restores final-bail-reason.txt
- Share finalize-state key ordering between ship-pr.sh and the restore helper through a sourced Bash 3.2-compatible library
- Wire the helper into /implement Step 18 and add Makefile, docs, agent-lint, and offline harness coverage

## [27.6.19] - 2026-05-15

### Changed

- Restored the private .claude /release skill from the pre-revert version.
- Changed release-state jq reads to avoid aborting when GitHub boolean fields are false.
- Verified latest-state promotion with gh release list because gh release view does not expose isLatest.

## [27.6.18] - 2026-05-15

### Changed

- Added scripts/write-tally.sh to compose tally JSON and write the matching larch-log batch in one helper call.
- Added write-tally contract docs and an 11-case regression harness covering happy paths, defaults, validation, passthrough failures, atomicity, and channel discipline.
- Wired make test-write-tally into shard 4 and updated /implement Step 1 and Step 5 tally instructions to use the wrapper.

## [27.6.14] - 2026-05-15

### Changed

- Scaffolded the private .claude /release skill with model invocation disabled for the dangerous release name.
- Added a release promotion wrapper that selects the newest non-draft character-ai/larch release, clears pre-release, marks it latest, and verifies the state.
- Documented the wrapper contract and wired the skill to run /upgrade-larch after successful promotion.

## [27.6.12] - 2026-05-15

### Changed

- Adopted the JSON no-findings sentinel in plan-review and external reviewer prompts while keeping NO_ISSUES_FOUND accepted by validators.
- Added CURSOR_EMPTY_RESPONSE detection for Cursor envelopes with empty .result and mapped validator exit 5 to a distinct collector status.
- Updated script contracts, docs, and regression harnesses for sentinel parsing, empty-result handling, and prompt assertions.

## [27.6.9] - 2026-05-15

### Changed

- Migrate post-init runtime shell diagnostics from raw stderr redirection to larch_err/larch_errf.
- Add S041/no-raw-stderr-after-quiet-init as a local pre-commit lint with regression coverage.
- Fix empty .diag failure reasons and split launch-claude-subprocess quiet-routing assertions.
- Update quiet-library, collector, linting, and agent-lint documentation for the new contract.

## [27.6.5] - 2026-05-15

### Fixed

- Complete `larch_quiet_init` stderr migration: migrate all post-init `echo/printf/cat >&2` diagnostics to `larch_err`/`larch_errf` across 98 scripts so callers capture real diagnostic output instead of empty buffers.
- Fix `collect-agent-results.sh` `build_failure_reason` to use `-s` (non-empty file) instead of `-f` so empty `.diag` files correctly fall through to status-based fallback messages.
- Add `S041/no-raw-stderr-after-quiet-init` pre-commit lint rule to enforce the `larch_err`/`larch_errf` contract statically.

## [27.6.4] - 2026-05-15

### Fixed

- Fix `tally-votes.sh` to accept all findings with a warning when fewer than 2 voter files are present (`BOTH_DOWN=false`), instead of manufacturing a fake `FINDING_1 NO` vote. Aligns with the threshold rules in `voting-protocol.md` rows 15-16.

## [27.6.2] - 2026-05-15

### Changed

- Extend Cursor auth failure detection to match macOS security CLI exit signatures
- Add Cursor launcher regression coverage for two-line exit-45 and wrapper-only security failures
- Update the shared launcher library docs for the new Cursor auth signature

## [27.6.1] - 2026-05-15

### Changed

- Harden Step 18 transcript flush handling to fetch origin/main, push only the single current-run log commit, and reset failed or orphaned flush-only commits back to origin/main.
- Add pre-pull local-cleanup orphan removal for prior larch-log flush commits while preserving non-flush local work.
- Document the new push and cleanup outcomes, wire a local-cleanup harness, and extend transcript tests for push success, push rejection, prior orphans, and non-flush ahead work.

## [27.6.0] - 2026-05-15

### Changed

- Extracted /review round orchestration into review-core.sh with FD3 KV output, dirty-tree recovery summaries, parent artifact copies, and harness coverage.
- Replaced /review with a thin wrapper prompt and added the internal /review-and-fix skill plus structured call-fixer path-safety scripts.
- Added simple/hard panel topology support to dispatch-panel.sh without overloading PANEL_MODE, plus stubbed topology tests.
- Added hand-maintained orchestrator aggregator/judge agents outside the reviewer-* glob and updated structure tests, Makefile shard wiring, and SECURITY.md.

## [27.5.71] - 2026-05-14

### Changed

- Convert remaining scripts in scripts/ and skills/implement/scripts/ to source lib-quiet.sh and initialize quiet mode.
- Route machine-readable stdout contracts through emit, emit_kv, or equivalent FD3-preserving output where newline-free output is required.
- Preserve internal file writes and command-substitution helper output while keeping validation harnesses green.

## [27.5.68] - 2026-05-14

### Changed

- Convert /design, /fix-issue, and selected root helper scripts to source lib-quiet.sh and emit machine-readable stdout through emit or emit_kv.
- Keep pure renderers/filters and migration harnesses byte-stable with LARCH_QUIET_DISABLE=1, including implement boundary harnesses that assert legacy reader output.
- Update sibling script contracts to document quiet-mode FAILURE_LOG stdout behavior.

## [27.5.67] - 2026-05-14

### Changed

- Convert /research helper scripts and hook utilities to source lib-quiet.sh and route contract stdout through emit or emit_kv.
- Keep migrated harness assertions stable with LARCH_QUIET_DISABLE=1 while documenting quiet logging and possible FAILURE_LOG output in sibling contracts.
- Remove lib-quiet.sh external dirname dependency so quiet initialization works in stripped-PATH hook fallback tests.

## [27.5.65] - 2026-05-14

### Changed

- Applied lib-quiet initialization and emit/emit_kv contract output to review machinery scripts.
- Preserved prompt and JSON content streams by restoring stdout for renderer-style helpers.
- Updated sibling contracts and quiet-aware harness assertions for diagnostics now captured in logs.

## [27.5.64] - 2026-05-14

### Changed

- Add a guarded Step 18 push for post-merge local main run-log commits
- Improve local-cleanup pull failures with an ahead-of-origin diagnostic
- Document the new local-cleanup divergence warning behavior

## [27.5.60] - 2026-05-14

### Changed

- Added scripts/larch-log-flush.sh and tail-called it from git-commit.sh, git-amend-add.sh, apply-bump.sh, and step2-implement.sh.
- Changed larch-log.sh commit to never push and removed its --no-push option from callers, docs, and harnesses.
- Removed dedicated larch-log flush commit sites from ship-pr.sh and implement-finalize.sh, with --no-logs-commit now exported as LARCH_NO_LOGS_COMMIT for subprocess tail calls.
- Removed larch-logs paths-ignore filters from CI and release-tag workflows and updated tests/docs for the new flush ownership model.

## [27.5.59] - 2026-05-14

### Changed

- Rationalized larch-log batch registry to JSON objects for tallies, markdown for full review findings, and JSON token/timing reports.
- Added JSON output modes to token-report.sh and timing-report.sh, and taught report-tokens to consume structured logs with legacy fallbacks.
- Fixed cache-session tmpdir redaction so multiple quoted JSON paths redact independently while preserving parseability.
- Populated manifest model_roster.main from the active Claude model environment and updated docs/security contracts.

## [27.5.58] - 2026-05-14

### Changed

- Added --plan-file support to Cursor and Codex CI launchers, including absolute-path validation and prompt insertion when the plan exists.
- Taught ship-pr.sh to safely read PLAN_FILE from session-env.sh and forward it to CI-fix and rebase-conflict vendor launchers.
- Updated launcher, state-machine, and harness docs plus argv/offline coverage for plan-file validation and forwarding.

## [27.5.56] - 2026-05-14

### Changed

- Redirect review helper subprocess output to files instead of buffering large command substitutions in gather-context, collect-findings, and tally-votes.
- Expose the collector results file in the collect-findings stdout envelope and document the file-backed contracts in sibling markdown.
- Add stdout-size cap assertions to every review script regression harness touched by the review pipeline.

## [27.5.55] - 2026-05-14

### Changed

- Short-circuit ship-pr version_already_published to already_merged when GitHub reports the PR is already merged
- Refresh origin/<branch> before the first git-force-push force-with-lease attempt while preserving existing retry statuses
- Add offline ship-pr regression coverage for merged and unmerged version_already_published PR states

## [27.5.50] - 2026-05-14

### Changed

- Add larch-logs/** paths-ignore filters to CI and release-tag workflow push/PR triggers.
- Make ship-pr ci-merge and postmerge larch-log flush commits local-only with --no-push.
- Document the shared larch-log --no-push discipline and cover the updated ship-pr flush arguments in the harness.
- Stop ship-pr.sh from replaying captured helper output and fail-file diagnostics to stdout.
- Emit FAILURE_DETAIL_LOG for failed helper invocations so callers can find captured diagnostics without stdout replay.
- Add an offline verbose-checks regression that caps ship-pr stdout and documents the new envelope key.

## [27.5.49] - 2026-05-14

### Changed

- Converted step section headings in skills and referenced phase docs to HTML comment anchors.
- Removed orchestrator-authored checkmark completion print directives while preserving skip, warning, and reviewer status table markers.
- Added missing start breadcrumb directives and updated progress-reporting plus harness expectations.

## [27.5.45] - 2026-05-14

### Changed

- Add a /design ACTION dispatcher plus extracted classify, emit-plan, tally-plan-review, and finalize-plan helper scripts with sibling contracts.
- Wire /design SKILL.md and heavy-worker.md to the helper scripts while preserving inline model-judgment steps and focus-area enum anchors.
- Register five new design harnesses in Makefile, agent-lint exclusions, docs/linting.md, and structural pins.

## [27.5.39] - 2026-05-13

### Changed

- Log Step 0 token-claude-source.sh snapshot failures under Warnings instead of silently swallowing them
- Recover missing session transcript source snapshots by discovering recent Claude project JSONL transcripts
- Add regression coverage and script contracts for fallback discovery and recovery warnings
- Persist LARCH_CLAUDE_PLUGIN_ROOT in session-env when CLAUDE_PLUGIN_ROOT is available.
- Add same-fence CLAUDE_PLUGIN_ROOT rehydration guards across implement, design, review, and fix-issue Bash blocks.
- Extend structural, roundtrip, linting, and security docs for plugin-root recovery.

## [27.5.31] - 2026-05-13

### Changed

- Add LARCH_EXECUTION_ISSUES_LOG precedence to all execution_issue_log resolvers
- Isolate affected test harness execution-issues.md writes inside their temporary sandboxes
- Document the override chain and harness isolation in sibling script contracts

## [27.5.30] - 2026-05-13

### Changed

- Recover missing larch-log manifests before postmerge run-log commits
- Recover missing manifests during Step 18 teardown before final flush commits
- Split Branch 4 handling so larch-log init failure stalls while summary-comment failure remains deferred
- Document the recovery contract and cover the postmerge missing-manifest path

## [27.5.29] - 2026-05-13

### Changed

- Added skill-path prefixes to visible step-start headers across the planned orchestrator skill docs.
- Extended the shared progress-reporting contract and /design step-prefix parsing docs with an optional parent skill path field.
- Updated /implement child /design and /review invocations to pass /implement as the parent skill path, plus the structural breadcrumb test pin.
- Strip the first source Implementation Plan heading from plan-goals-test output so the wrapper heading is not duplicated.
- Recognize Test plan, Tests, Testing, Verification, Test strategy, and Verification strategy headings at levels 1 through 3 and stop extraction at the next heading.
- Expand the compose-plan-goals-test regression harness and sibling docs for the new heading behavior.

## [27.5.22] - 2026-05-13

### Fixed

- `scripts/redact-tmpdir-paths.sh`: add left boundary anchor `(^|[^[:alnum:]_./-])` to expression 3 so numeric exit codes and variable-name prefixes are no longer consumed when redacting `/larch/sessions/` paths from session transcripts.

## [27.5.16] - 2026-05-13

### Changed

- Add script-owned /design plan-review external voter dispatch for Codex and Cursor through run-external-agent.sh.
- Document the dispatcher contract and update design voting instructions, shared voting protocol, SECURITY.md, lint docs, and Makefile wiring.
- Add an offline dispatcher harness covering happy path, fallback statuses, launch-failure logging, wrapper use, read-only argv, and prompt cleanup.

## [27.5.15] - 2026-05-13

### Changed

- Add a behavioral guideline for grep-family and find probe exit-code handling.
- Document guard patterns for informational no-match probes while preserving grep conditionals.
- Validate the Markdown-only change with the repo relevant-checks script.

## [27.5.14] - 2026-05-13

### Changed

- Log terminal external launcher failures into execution-issues with auth verdict context
- Extend append-tool-failure headers with optional verdict and retry-count suffixes
- Document the new launcher failure logging contracts and cover header suffixes in the harness

## [27.5.10] - 2026-05-13

### Changed

- Add compose-plan-goals-test.sh to build sectioned plan-goals-test payloads from file-backed plans and reject missing, short, or pointer-only plan files.
- Wire plan-goals-test to a plan-goals larch-log sanitizer that rejects empty or pointer-only Implementation Plan bodies before writes publish.
- Update /implement instructions, Makefile wiring, sibling docs, agent-lint exclusions, and larch-log harness fixtures for the new contract.

## [27.5.7] - 2026-05-13

### Changed

- Added a Step 18 capture-session-transcript wrapper that records every transcript capture outcome to execution issues and keeps cleanup best-effort.
- Bumped larch-log manifests to schema version 2 with operator_cwd and operator_repo_root provenance fields plus updated docs and security notes.
- Added and wired regression coverage for transcript capture statuses and refreshed existing manifest/log harness assertions.

## [27.5.6] - 2026-05-13

### Changed

- Rehydrate LARCH_TIMING_LEDGER and IMPLEMENT_TMPDIR in every /implement post-Step-0 timing/token context block.
- Add a structural regression harness and wire it into Makefile, docs, and agent-lint exclusions.
- Document the timing-ledger containment behavior in SECURITY.md and remove stale fallback ledgers from the temp root.

## [27.5.5] - 2026-05-13

### Changed

- Added scripts/lib-net.sh as the shared transient-network signature classifier with a source guard and sibling documentation.
- Updated collect-agent-results.sh and ship-pr.sh to source the shared helper and removed their duplicate local implementations.
- Extended collector and ship-pr harness coverage for the shared helper and synthetic-repo sourcing path.

## [27.5.4] - 2026-05-13

### Changed

- Changed wait-for-reviewers to use a poll-count timeout budget and discount suspend-length poll iterations.
- Extended collect-agent-results so transient-network FAILED, TIMED_OUT, and SENTINEL_TIMEOUT rows can reuse the existing .meta retry path.
- Added collector transient retry coverage and updated Makefile, agent-lint, and docs wiring.

## [27.5.0] - 2026-05-13

### Changed

- Extracted /review gather, dispatch, collect, voting, emit, and log phases into script-backed contracts with harness coverage.
- Added shared ballot, vote tally, scoreboard, and OOS serialization helpers for review/design reuse.
- Added a Claude subprocess review launcher with sidecar, path-validation, and security documentation.
- Reduced skills/review/SKILL.md to a thin orchestration prompt and updated larch-log review batch wiring.

## [27.0.16] - 2026-05-12

### Changed

- Added shared external launcher helpers for Darwin per-tool startup locks, stale-lock recovery, delayed release, and auth-failure classification.
- Wrapped Cursor, Codex, and Gemini review, implement, and CI spawn sites with shared serialization plus bounded auth-startup retry logic.
- Migrated cursor-specific lock env vars to LARCH_EXTERNAL_* names and updated launcher docs, SECURITY.md, and regression harness coverage.

## [27.0.14] - 2026-05-13

### Fixed

- Manifest finalization now runs inside `ship-pr.sh run_postmerge_phase` (gated on `PR_CLOSED=true`) so `manifest.json` is updated to `status=done` even when the LLM session ends before Step 18 teardown.
- Added regression tests for postmerge manifest flush in `test-ship-pr.sh`.

## [27.0.11] - 2026-05-12

### Changed

- Added explicit --log-root handling to larch-log.sh and removed IMPLEMENT_TMPDIR/repo-root fallback from lib-larch-log.sh.
- Updated /implement, ship-pr, and implement-finalize log call sites to pass $IMPLEMENT_TMPDIR/larch-logs explicitly.
- Added PREV_IMPLEMENT_TMPDIR session-env handoff and best-effort larch-logs copy during session setup.
- Updated docs, security notes, and regression harnesses for the new log-root contract.

## [27.0.0] - 2026-05-12

### Changed

- Split `agents/reviewer-correctness-edges.md` (generated combined "Correctness + Edge Cases" archetype) into two new specialist archetypes: `agents/reviewer-plan-fidelity.md` (plan-to-implementation traceability; requires the design plan as input) and `agents/reviewer-code-robustness.md` (edge cases, failure recovery, and silent data corruption; diff-only, no plan required). Replaces the old generator script and `agents/reviewer-correctness-edges.md`; adds `scripts/generate-reviewer-plan-fidelity-agent.sh` and `scripts/generate-reviewer-code-robustness-agent.sh`; updates `scripts/generators.tsv`, CI focus-area enum check, and `docs/review-agents.md`.

### Changed

- Expand `/design` Step 3 plan-review panel from 4 reviewers to 10 (5 personalities × 2 tools). Each of the 5 archetypes (Architecture/Standards, Edge-case/Failure-mode, Innovation/Exploration, Pragmatism/Safety, Requirements/Completeness) now runs on both Cursor and Codex. Adds `requirements` to `render-plan-review-prompt.sh`, adds new launch blocks in `skills/design/SKILL.md` Step 3, updates `plan-review.md` panel contract and output paths, extends test coverage for the new archetype, and updates `topology.tsv` + `docs/topology.md`.
- Align Codex plan-reviewer prompts with Cursor: switch `render-plan-review-prompt.sh` Codex branch from `short_role` to `full_role` and add TSV structured-record block; update `plan-review.md` collection call to pass `--structured-reviewer-validation` for all archetype slots; extend `test-plan-review-prompt.sh` to assert Codex TSV output and `full_role` prose.
- Replace tracking-issue anchor-comment storage with committed `larch-logs/` run artifacts plus five slim marker-keyed tracking comments. Adds `scripts/larch-log.sh`, `scripts/tracking-issue-summary.sh`, batch/manifest harnesses, and removes the old anchor assembly/hydration/refresh scripts.

## [26.0.20] - 2026-05-12

### Changed

- Pre-read Cursor macOS cursor-access-token service into CURSOR_API_KEY before shared Cursor launcher argv hydration.
- Make Cursor auth preflight service-specific for cursor-user / cursor-access-token.
- Cover the pre-read helper and shared launcher wiring in the Cursor auth harness and update security/auth docs.

## [26.0.17] - 2026-05-12

### Fixed

- `scripts/larch-log.sh`, `scripts/lib-larch-log.sh`: corrected `REPO_ROOT`/`LARCH_LOG_REPO_ROOT` fallback — `(A || B) && C` shell-precedence caused `pwd -P` to always run, doubling the path; now uses a two-assignment pattern so git operations target the project repo rather than the plugin cache.
- `scripts/ship-pr.sh` `run_postmerge_phase`: wired `larch:token-report` and `larch:final-summary` tracking-issue summary upserts before teardown; moved `advance_phase "done"` before teardown so the state file exists when updated; added `exit 0` to bypass the stale state-machine loop after teardown removes the state file.
- `scripts/implement-finalize.sh` `collect_changelog_bullets`: treat missing `CHANGELOG_BULLETS_FILE` as empty (not an error) on the no-manifest path, routing to `skipped-no-bullets` instead of `changelog-failed`.

## [26.0.15] - 2026-05-12

### Changed

- Added ship-pr.sh as a post-review /implement state machine with postbump, PR, CI, merge, and teardown phases.
- Added Cursor and Codex CI-fix launchers plus token sidecar normalization and timing allow-list entries.
- Collapsed the /implement post-review tail to the ship-pr entrypoint and wired offline harnesses, Makefile targets, lint docs, and security notes.

## [26.0.14] - 2026-05-11

### Changed

- correctness reviewer now verifies code against --plan-file and --feature-file when provided via launch-review.sh
- render-specialist-prompt.sh embeds plan/feature content inline in generic diff-mode prompts
- /implement quick mode and /review normal mode wire plan/feature paths to the correctness specialist

## [26.0.13] - 2026-05-11

### Fixed

- /implement Step 8 postbump directive now marks changelog-bullets composition as required (not optional) when MANIFEST_PATH is empty; removes misleading "Claude fallback path" qualifier and "skip only on manifest-backed" wording
- Remove stale reference to "Step 18's final larch-log.sh commit" from rebase-rebump-subprocedure.md step 6e (log-flush moved to Step 7a tail in v26.0.12)

## [26.0.12] - 2026-05-11

### Fixed

- Fix larch-logs commit order: move log-flush commit to pre-bump so logs ride inside the PR
- Add retry log refresh in rebase sub-procedure to keep token/timing data current on CI retries
- Fix quick-mode and small-skip paths to run pre-bump log flush before Step 8

## [26.0.11] - 2026-05-11

### Changed

- Add a cache-key discipline harness for audited prompt-construction surfaces and wire it into shard 7.
- Annotate existing per-session external-tool prompt path interpolations as intentionally non-stable.
- Document the new harness in its sibling contract and linting target table, and exclude the Makefile-only harness from dead-script lint.

## [26.0.10] - 2026-05-11

### Fixed

- Restore Step 9a.1 OOS pipeline numbered procedure inline in `skills/implement/SKILL.md` (removed with `anchor-template-oos-pipeline.md` in v26.0.8)
- Correct 4 stale `summary-comment-template.md step 3.4` references to point to `Step 9a.1 step 3.4`

## [26.0.9] - 2026-05-11

### Changed

- step2-implement.sh now accepts `--workflow SIMPLE|HARD` to tune coder timeout: 1 h for SIMPLE (default), 2 h for HARD

### Fixed

- Repair non-standard `qa-pending.json` `items[]` format on `needs_qa` path in `step2-implement.sh`, routing to the Q&A loop instead of bailing with `manifest-schema-invalid`

## [26.0.8] - 2026-05-11

### Changed

- Replace tracking issue anchor storage with committed larch-log batches and slim marker-keyed summaries.
- Migrate implement, review, design, fix-issue, and research consumers away from removed anchor scripts.
- Add larch-log and tracking-summary script families with regression coverage for manifests, batches, and publication.
- Harden implement finalization around version-bump logging and stale background-process cleanup.

## [26.0.7] - 2026-05-11

### Fixed

- Add Stop-hook guard for post-/bump-version halt boundary (issue #1878)

## [26.0.6] - 2026-05-11

### Added

- `--run-id <ID>` flag documented in all 22 plugin-exported skill SKILL.md files (preparatory for larch-logs run-correlation in #1438)

## [26.0.5] - 2026-05-11

### Fixed

- fix(implement): capture Codex stdout+stderr in review sidecar so "tokens used" lines land in the token ledger; export IMPLEMENT_TMPDIR for reliable session-id propagation to reviewer subprocesses

## [26.0.4] - 2026-05-11

### Added

- /report-tokens: per-vendor cost breakdown in workflow summary, optional LARCH_REPORT_TOKENS_ACTUAL_SPEND reconciliation line, test-rate-assertions harness

### Fixed

- /report-tokens: update Codex (GPT-5.5) and Cursor (Composer 2) default rates; add Gemini 2.5 Pro rate entry

## [26.0.3] - 2026-05-11

### Fixed

- fix duplicate step 9a.1 breadcrumb in /implement output (add explicit refresh-anchor.sh fence)
- /report-tokens now surfaces full matplotlib subprocess errors via stderr tail instead of masking them behind the font-cache banner

## [26.0.2] - 2026-05-11

### Fixed

- Add post-/review Stop hook guard in hook-stop-fail-close.sh (issue #1862) — blocks session stop between /review return and Step 6 breadcrumb via review-round-summary.md + .review-boundary-passed sentinel pair
- Extend lib-resolve-implement-tmpdir.sh to accept review-round-summary.md as a fallback sentinel, covering the both-externals-down path that skips /design
- Add two regression-test assertions in test-implement-anti-halt.sh and extend test-post-design-boundary.sh with review-boundary Stop hook fixtures

## [26.0.1] - 2026-05-11

### Added

- /report-tokens: auto-post [Analysis Report] GitHub issue after each analysis run
- /report-tokens: --no-issue flag to skip analysis report issue creation
- /report-tokens: --no-plot flag to skip plot generation
- /report-tokens: --plot-from <N> flag to re-plot from a prior report issue

### Fixed

- Fix plot_dir NameError in /report-tokens matplotlib subprocess (sys.argv[2] passthrough)

## [26.0.0] - 2026-05-11

### Changed

- Add --summary-only output mode to collect-agent-results.sh with regression coverage
- Document design and review heavy-worker structured summary JSON contracts
- Update design, review, and implement orchestration prose to validate fixed summary paths before consuming footer signals

## [25.0.1] - 2026-05-11

### Added

- pin post-/bump-version anti-halt regression assertions in test-implement-anti-halt.sh (issue #1850)

## [25.0.0] - 2026-05-11

### Changed

- **HARD-path `/review` panel expanded to 11 reviewers**: Added 5 Codex specialist reviewers (Codex-Structure, Codex-Correctness, Codex-Testing, Codex-Security, Codex-Edge-cases) alongside the existing 5 Cursor specialists + Claude generic. Rounds 4-7 (single-reviewer tail) removed; hard cap is now 3 rounds. New convergence thresholds: ≥2 high-severity findings OR ≥~100 LOC OR ≥8 accepted findings (round 3 escalation: ≥3 high-severity OR ≥~150 LOC). `--full` flag removed.
- **SIMPLE-path quick-mode review restructured to 6 reviewers**: Dropped Claude generic from rounds 1-3 (new panel: 5 Cursor specialists + 1 Codex generic). Rounds 4-7 removed; hard cap is now 3 rounds. Matching convergence thresholds. Claude generic fallback retained for the both-externals-down case. SIMPLE nit-only early exit added.
- **5 new Codex specialist timing-task-kind slugs**: `codex-specialist-structure`, `codex-specialist-correctness`, `codex-specialist-testing`, `codex-specialist-security`, `codex-specialist-edge-cases` added to `lib-timing-kinds.sh`.

### Changed

- Reviewer dirty-tree changes are now automatically logged and discarded instead of prompting the operator with a restore/stash/bail `AskUserQuestion`. When a Cursor, Codex, or Claude reviewer leaves uncommitted changes in the working tree, the orchestrator logs which reviewer caused it (to `execution-issues.md` under `Warnings` in `/implement` runs, or to the transcript in standalone `/review` runs) and immediately discards the changes via scoped `git restore` / `git clean` — no stash is created and `git stash list` remains clean. This replaces the three-option recovery prompt introduced by #1437. Updated: `skills/implement/SKILL.md` (Step 5.3.b quick mode, Step 5 normal mode, `--auto` flag description), `skills/review/SKILL.md` (Step 3a, line 22), `skills/review/references/heavy-worker.md`, `docs/external-reviewers.md`, `SECURITY.md`

## [24.2.2] - 2026-05-11

### Changed

- gate `git log` instruction from specialist reviewer prompts when branch has ≤5 commits (`--commit-count` in `gather-branch-context.sh`, `render-specialist-prompt.sh`, `launch-review.sh`; stored in retry sentinel); cap `gh-run-logs.sh` output to last 100 lines with full-artifact URL pointer (fixes #1842)

## [24.2.1] - 2026-05-11

### Added

- Add `--summary` flag test coverage to `test-token-report.sh` and `test-timing-report.sh` harnesses (three cases each: normal output, zero-vendor run, no-marks unavailable warning)

## [24.2.0] - 2026-05-11

### Added

- Add /block-issue skill: express native GitHub blocked-by relationships via the addBlockedBy GraphQL mutation

## [24.1.6] - 2026-05-11

### Changed

- Add session-scoped render cache (LARCH_RENDER_CACHE_DIR) for render-specialist-prompt.sh; all reviewer launchers in the same session share cached render output
- Ship pre-rendered reviewer agent body files (agents/pre-rendered/) to avoid per-launch awk extraction; generate-pre-rendered-reviewer-prompts.sh wired into generators.tsv CI

### Security

- Gate Gemini reviewer lane behind GEMINI_REVIEW=1 env var (default off); launch-review.sh --tool gemini exits 0 with empty output when unset

## [24.1.5] - 2026-05-11

### Changed

- Remove per-step `token-report --since-last-mark --terse` calls from `/implement`; add `--summary` flag to `token-report.sh`/`timing-report.sh` for grand-total one-liner
- Gate `/implement` Step 17 full token/timing table behind `LARCH_VERBOSE_TOKENS=true`; default chat output is now a brief summary line

## [24.1.3] - 2026-05-11

### Fixed

- fix-issue post-/implement boundary directive now says "do NOT end the turn (neither silently nor after text output)", covering silent turn-end halts after `/implement` returns

## [24.1.2] - 2026-05-11

### Fixed

- suppress Rebase Checkpoint Macro M1 log line on no-op rebase (SKIPPED paths)
- skip dirty-tree sidecar scan in Codex EXIT trap when --sandbox read-only is confirmed
- remove inline bump-version description prose from HAS_BUMP=false warning in /implement

## [24.1.1] - 2026-05-11

### Changed

- Skip Step 7a code flow diagram for ≤2 non-runtime files changed (docs/config only)
- Skip design Step 3b architecture diagram for non-architectural plans (docs/config/text-only)

## [24.1.0] - 2026-05-10

### Changed

- Centralize combined-specialist reviewer prompts in skills/shared/reviewer-templates.md and generate the specialist agents from registered scripts.
- Extract the shared external implementer prompt body into agents/_implementer-base.md with Codex, Cursor, and Gemini generator wrappers.
- Update structural and lint configuration so generated prompt sources and registry-driven scripts are validated without false positives.

## [24.0.0] - 2026-05-10

### Changed

- Added a shared compressed focus-area prompt and extended CI enum coverage to the shared file.
- Shrank Codex and Cursor read-only review preambles while preserving launcher anchors and retry-sidecar behavior.
- Moved /design plan-review external prompts behind a vendor-aware renderer with temp prompt files and harness coverage.
- Compressed repeated generic reviewer focus-area prompt prose in /review and /implement without moving required enum anchors.

## [23.0.0] - 2026-05-10

### Changed

- Add a jq-based run-params writer and regression harness for adaptive /design routing budgets.
- Teach /design to consume run-params.json, support --full and forwarded classifications, and route sketch fan-out through 0/2/4 budgets with zero-sketch sentinels.
- Update /implement routing prose for classification reuse, --design-classification forwarding, and POST_PLAN_WORKFLOW_PATH session state.
- Refresh topology, user docs, security notes, and structural harnesses for the adaptive sketch model.

## [22.0.0] - 2026-05-10

### Fixed

- Cover silent turn-end halts at post-/design and post-/review boundaries in /implement

## [21.0.0] - 2026-05-10

### Removed

- Remove /fq alias skill (shortcut for /fix-issue, which now defaults to SIMPLE mode)

## [20.9.0] - 2026-05-10

### Changed

- Scaffold /report-tokens with a single coordinator script and sibling contract.
- Implement GitHub issue discovery, token-report parsing, cost estimation, plot generation, and written analysis.
- Wire README, docs, and strict-permissions entries for the new skill.

## [20.8.4] - 2026-05-10

### Changed

- docs: qualify /design --quick plan-review topology (Claude-only, no voting panel) in voting-process.md, review-agents.md, topology.tsv
- test-design-structure.sh: extend Check 13 to validate plan-review-quick.md security OOS exclusion clauses

### Fixed

- show.sh: route STATUS= and SKILL_PATH= lines to stdout (contract correction)
- token-report.sh, timing-report.sh: route unavailable() messages to stderr so degradation signals survive stdout redirection
- anchor-template-oos-pipeline.md: narrow --no-dep-llm forwarding to not suppress Phase-2 LLM semantic dep analysis when file-conflict pre-pass is complete

## [20.8.3] - 2026-05-10

### Fixed

- /implement Rebase+Re-bump sub-procedure anti-halt now covers silent turn ends after apply-bump.sh returns APPLIED=true, not only text-output halts

## [20.8.2] - 2026-05-10

### Fixed

- Multi-step skill scaffold now generates scripts/step-name-registry.tsv and uses the MANDATORY TSV-read directive instead of an inline Step Name Registry table, matching the progress-reporting.md contract

## [20.8.1] - 2026-05-10

### Fixed

- Allow cleanup when session-id matches despite basename prefix mismatch in `verify_cleanup_target`

## [20.8.0] - 2026-05-10

### Changed

- replace long prose subskill-invocation cross-references with stable slugs in 9 SKILL.md files; add HTML anchors to subskill-invocation.md

## [20.6.6] - 2026-05-10

### Changed

- Move Step Name Registry tables from each orchestrator skill's SKILL.md into per-skill `scripts/step-name-registry.tsv` files; add MANDATORY load directives; update `progress-reporting.md` and fix-issue test harness

## [20.6.5] - 2026-05-10

### Fixed

- Kill stale detached background processes from the /implement session at Step 18 teardown (SIGTERM + SIGKILL backstop; scoped to session-unique tmpdir via fixed-string awk match)

## [20.6.4] - 2026-05-10

### Changed

- Raise CI fix-attempt limit from 3 to 10 in `scripts/ci-decide.sh` so `/implement`'s CI failure/fix/retry loop tolerates more iterations before bailing. Updated header comment, `-ge` guard, and bail-reason text in lockstep. Docs: `scripts/ci-decide.md`. Closes #1786.

## [20.6.3] - 2026-05-10

### Changed

- Consolidate external review launches behind one tool-selected entry point.
- Preserve Codex, Cursor, and Gemini reviewer safety checks while sharing retry metadata shape.
- Keep skill, documentation, and harness references aligned with the unified launcher.

## [20.6.2] - 2026-05-10

### Fixed

- Fix spurious post-`/design` halt: `hook-post-design.sh` now passes `--hook-mode true` to `post-design-boundary.sh`, skipping `.boundary-gate-passed` sentinel creation and emitting `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` instead of `POST_DESIGN_BOUNDARY_OK=true`. The Stop hook now remains armed until the orchestrator's mandatory Bash wrapper writes the sentinel, so spurious halts between the PostToolUse hook firing and the orchestrator Bash call are caught and blocked. Also strengthened `/design` SKILL.md Step 5 to explicitly forbid farewell messages in orchestrated mode and updated `/implement` SKILL.md boundary checkpoint to distinguish the hook-injected token from the orchestrator success token. Updated: `skills/implement/scripts/post-design-boundary.sh`, `skills/implement/scripts/hook-post-design.sh`, `skills/implement/scripts/test-post-design-boundary.sh`, `skills/implement/SKILL.md`, `skills/design/SKILL.md`, `SECURITY.md`

## [20.6.1] - 2026-05-10

### Changed

- Enforce artifact-only return contract for nested child skills: when `SESSION_ENV_PATH` is set, `/design` and `/review` emit only the machine footer (KV status block) and artifact file paths. Adds formal policy to `skills/shared/subskill-invocation.md`, NEVER rule to `/design` and `/review`, nested diff-mode KV footer to `/review` Step 4, and updates `/implement` Step 5 to prefer file-backed `review-round-summary.md` over visible output for the `code-review-tally` anchor fragment.

## [20.6.0] - 2026-05-10

### Changed

- Gate Codex effort args and Cursor max-mode/suffix behavior behind launcher --risk, with conservative specialist diff classification and retry metadata preservation.
- Remove hardcoded max-effort prose from reviewer, sketch, voter, judge, dialectic, and specialist prompt sources while leaving launcher-owned high-risk mechanisms intact.
- Add regression coverage for high/low/invalid/derived risk paths, outer retry risk replay, specialist prompt prose absence, and a new prompt-source prose guard.

## [20.5.5] - 2026-05-10

### Changed

- Remove redundant "You are X reviewer." opener from four plan-review inline prompts in skills/design/SKILL.md

## [20.5.3] - 2026-05-10

### Changed

- /implement simplicity classification now strongly defaults to SIMPLE; HARD requires genuinely uncertain approach or major new shared abstraction; explicit NOT-sufficient list (multi-file mechanical edits, pre-resolved decisions, parity/test requirements)
- `/fix-issue` Step 4 now evaluates and verbalizes COMPLEXITY (`SIMPLE` or `HARD`) in the breadcrumb when `INTENT=PR`, including `(forced by --hard)` suffix when `hard_mode=true`

### Fixed

- `skills/fix-issue/references/triage-classification.md`: corrects "default to HARD when uncertain" → "default to SIMPLE when uncertain" and tightens Dimension 2 HARD criteria

## [20.5.2] - 2026-05-10

### Added

- Add `plan-review-quick.md` slim checklist for quick-mode `/design` plan review (Claude self-review, same artifact set as normal mode, ~17 KB context savings per quick-mode run)

### Changed

- Gate `plan-review.md` MANDATORY load in `/design` Step 3 on `quick_mode=false`; update `flags.md` `--quick` description to reflect new behavior

## [20.4.3] - 2026-05-09

### Changed

- Batch `mergeStateStatus` and `headRefOid` into one `gh pr view --json` call in `merge-pr.sh`, eliminating one API round-trip per merge invocation.

## [20.4.2] - 2026-05-09

### Fixed

- Add echo-parsed-values as forbidden halt pattern after /bump-version returns in /implement Step 8

## [20.4.1] - 2026-05-09

### Fixed

- Voting report column header now uses stable role labels (`Claude`, `Codex`, `Cursor`) instead of improvising a model name (e.g., `Claude-Opus`) in the per-finding vote breakdown table; added explicit column-label guidance to `skills/design/references/plan-review.md` and `skills/review/references/voting.md`

## [20.4.0] - 2026-05-09

### Added

- Add `/show-skill` plugin skill — displays any skill's `SKILL.md` content by name (bare, `larch:`-prefixed, or `/`-prefixed). Searches plugin `skills/` tree first, then consumer `.claude/skills/`. Read-only; includes `show.sh` + test harness.

## [20.3.0] - 2026-05-09

### Changed

- Codex launcher prompts now keep static agent instructions separate from dynamic task content, improving cache reuse without changing the external implementer or reviewer contracts.
- Codex review hardening remains enforced while retry sidecars contain only replayable dynamic prompts.
- Documentation and offline harnesses now pin the temporary CODEX_HOME, conditional auth symlink, trusted-project override, and dynamic-only sidecar behavior.

## [20.2.4] - 2026-05-09

### Changed

- Compress `/design` `heavy-worker.md` (8 KB) to a 2 KB digest at `heavy-worker.digest.md`; full doc loads only on the subagent dispatch path, reducing parent orchestrator context by ~6 KB per `/design` invocation

## [20.2.3] - 2026-05-09

### Changed

- Extract shared "NEVER improvise ScheduleWakeup" anti-pattern rule to `skills/shared/orchestrator-never.md`; load it via a `MANDATORY at session start` directive in `fix-issue/SKILL.md` and `research/SKILL.md`, replacing verbose per-skill inline paragraphs with short pointers. Update `scripts/test-anti-improvised-wakeup.sh` to check the shared file and per-skill MANDATORY wiring instead of individual SKILL.md tokens (tighter token: `'MANDATORY at session start'`).

## [20.2.2] - 2026-05-09

### Fixed

- Collapse Step 0 double-line report into a single line per path in `/fix-issue`, removing the redundant 🔶 breadcrumb when `RENAMED=true` or `RENAMED=false`

## [20.2.1] - 2026-05-09

### Fixed

- Skip loading `voting.md` and emitting the Reviewer Competition Scoreboard when both Cursor and Codex are unavailable (both-down single-reviewer path); OOS artifact write now preserved on this path

## [20.2.0] - 2026-05-09

### Added

- Add `--no-issues` flag to `/implement`: when combined with `--design-only`, skips Steps 0.5 (tracking issue creation), 9a.1 (OOS filing), and 11 (anchor refresh); requires `--design-only`; mutually exclusive with `--issue`.

## [20.0.14] - 2026-05-09

### Fixed

- Emit reviewer status table only at round launch (all pending) and at round-complete (after `collect-agent-results.sh` returns), not on every individual status change (#1703)

## [20.0.13] - 2026-05-09

### Fixed

- Suppress Reviewer Competition Scoreboard from Step 4a final summary in nested /review runs (SESSION_ENV_PATH non-empty), mirroring existing per-round suppression in voting-protocol.md

## [20.0.11] - 2026-05-09

### Changed

- Reduce `/review` voting panel from 3 unconditional voters to 2 primary voters (Cursor + Codex); Claude is now invoked as a conditional tie-breaker only on 1Y/1N splits, making Claude voter cost conditional rather than unconditional

## [20.0.10] - 2026-05-09

### Changed

- Skip full `.prompt` sidecar for `--agent-file` Codex review launches; write compact hash+kind sentinel and reconstruct on retry via `render-specialist-prompt.sh`

## [20.0.9] - 2026-05-09

### Changed

- Add severity-gated prose length cap to all reviewer prompts: **Important** and **Latent** findings up to 4–5 sentences; **Nit** findings 1–2 sentences; no cap on finding count.

## [20.0.7] - 2026-05-09

### Changed

- /implement step-boundary completion and skip breadcrumbs now use compact key/value payloads by default
- Mechanical finalizer breadcrumbs for postbump, postmerge, and cleanup match the compact format
- Regression coverage pins compact Step 8, 8a, 8b, 14, 15, and 18 output

## [20.0.6] - 2026-05-10

### Changed

- Add `skills/implement/references/codex-manifest-schema.digest.md` (2.5 KB) and update Step 2's load directive to a tiered approach: the digest is sufficient for most dispatches; the full 15 KB doc loads only when editing dispatcher logic, implementer prompts, or downstream consumption steps.

## [20.0.5] - 2026-05-09

### Changed

- Add codex-manifest-schema.digest.md (2.5 KB) and update Step 2 load directive to tiered approach: digest suffices for dispatch-time validation; full 15 KB doc loads only when editing dispatcher, implementer prompts, or downstream consumption steps

## [20.0.4] - 2026-05-09

### Changed

- Specialist review prompts now narrow docs-only, test-only, and generated-only diffs to focused checks while keeping ambiguous diffs on the full prompt.
- Diff-mode routing is covered by renderer harness cases for explicit modes and auto-classification from precomputed diff files.

## [20.0.2] - 2026-05-09

### Changed

- Suppress full prose scoreboard in nested /review runs (SESSION_ENV_PATH non-empty); print only count summary instead

## [20.0.1] - 2026-05-09

### Changed

- Use explicit merge-base diff for reviewer launches: gather-branch-context.sh now computes MERGE_BASE=$(git merge-base HEAD main) and uses it for all three artifacts; reviewer prompts updated to git diff $(git merge-base HEAD main)...HEAD and git log $(git merge-base HEAD main)..HEAD --oneline

## [20.0.0] - 2026-05-09

### Changed

- `/fix-issue` default complexity changed from HARD to SIMPLE — most issues now use the faster `/implement --quick` path by default
- `--quick` flag replaced by `--hard` — pass `--hard` to force the full `/design` + `/review` pipeline
- `/fq` alias updated to match new default (equivalent to plain `/fix-issue`)

## [19.2.0] - 2026-05-09

### Changed

- `/review` default non-substantial round termination threshold raised: LOC >= ~30 → ~60; medium-severity findings no longer trigger another round (high severity only). Add `--full` flag to `/review` to revert to prior thresholds.

## [19.1.3] - 2026-05-09

### Added

- Add CI lint step (scripts/test-pipe-sigpipe-safety.sh) to detect SIGPIPE/pipefail anti-patterns (producer|head, bash-c|grep-q) in test scripts; wire into make lint and ci.yaml

### Changed

- Replace grep|head-1 patterns with grep -m 1 in test scripts to prevent SIGPIPE-induced pipefail flakiness on Linux

## [19.1.2] - 2026-05-09

### Changed

- Reviewer dirty-tree changes are now automatically logged and discarded instead of prompting the operator with a restore/stash/bail AskUserQuestion — no stash is created and git stash list remains clean

## [19.1.1] - 2026-05-09

### Fixed

- Fix SIGPIPE/pipefail flakiness in test scripts: replace `producer|head`/`grep|grep -qF` pipelines with `grep -m 1` and here-strings to prevent transient CI failures on Linux

## [19.1.0] - 2026-05-09

### Added

- Add `--subagent` flag to `/review` (diff mode) to run the review loop in an isolated Agent-tool subagent, keeping reviewer transcripts and fix reasoning out of the parent orchestrator context — mirrors the `/design` heavy-worker pattern
- New `skills/review/references/heavy-worker.md` defining the review subagent contract (inputs, artifact paths, wait discipline, return-value grammar)

### Changed

- `/implement` Step 5 (normal mode) now passes `--subagent` to `/review` by default when `inline_mode=false`; use `--inline` to run the review loop in the parent context

## [18.4.17] - 2026-05-09

### Changed

- Remove explicit full-file-read instructions from specialist reviewer preambles in `render-specialist-prompt.sh`; in no-diff-file mode reviewers no longer read every changed file in full upfront; in diff-file mode the pre-sliced diff already bounds context (closes #1632)

## [18.4.15] - 2026-05-09

### Changed

- Pre-compute `git diff -U20 main...HEAD` once and pass the path to all reviewers via `--diff-file` on `render-specialist-prompt.sh` and the launchers; each reviewer reads the shared pre-sliced diff instead of running `git diff` independently

## [18.4.14] - 2026-05-09

### Changed

- Split anchor-comment-template.md (37 KB) into four per-step fragment files (anchor-template-canonical-body.md, anchor-template-execution-issues.md, anchor-template-oos-pipeline.md, anchor-template-quick-mode.md) so each /implement step loads only the fraction it needs
- Update SKILL.md MANDATORY load directives to point each step at its relevant fragment and update CI structure-test assertions accordingly

## [18.4.13] - 2026-05-09

### Added

- Tiered MANDATORY read pattern: digest companion files for `fix-issue/references/triage-classification.md` and `implement/references/bump-verification.md`; updated MANDATORY directives to load digest by default, full file only when step-specific condition requires it

## [18.4.12] - 2026-05-09

### Changed

- Reorder /implement SKILL.md: Flags section moved after stable preamble sections (Single-runner, Mode matrix, Progress Reporting, Verbosity Control, Rebase Checkpoint Macro) for improved Anthropic prompt cache hit rate

## [18.4.11] - 2026-05-09

### Changed

- Replace 20-line worked examples in skills/implement, skills/research, and skills/create-skill SKILL.md files with compact key schemas and bullet-name formats, reducing token overhead on every orchestrator invocation

## [18.4.10] - 2026-05-09

### Changed

- Defer `rebase-rebump-subprocedure.md` load until rebase conflict detected; remove unconditional pre-Step-10 MANDATORY block and add targeted loads at each ACTION=rebase/rebase_then_evaluate invocation site

## [18.4.8] - 2026-05-09

### Fixed

- Fix diff-mode specialist reviewer prompt to use dual-section output (`### In-Scope Findings` / `### Out-of-Scope Observations`), matching agent files and review SKILL.md Step 3a parsing expectations

## [18.4.5] - 2026-05-09

### Fixed

- Add missing "Claude generic" positive anchor to test-quick-mode-docs-sync.sh POS_MARKERS so CI enforces the Claude generic reviewer slot across all public quick-mode docs

## [18.4.3] - 2026-05-09

### Changed

- /fix-issue: issues with titles matching [... Report] are now rejected (case-insensitive) on both auto-pick and explicit-target paths
- /fix-issue: GO comment is no longer required for eligibility; when present it is still removed at lock time via --lock; absent issues use --lock-no-go

## [18.4.2] - 2026-05-09

### Changed

- Add cap-hit assertions to 7 test harnesses (codex/cursor/gemini implement launchers, step2 dispatcher, codex/cursor review launchers, collect-agent-results.sh)

## [18.4.1] - 2026-05-09

### Changed

- /umbrella now prepends [UMBRELLA] to tracking issue titles; /fix-issue umbrella detection accepts [UMBRELLA] bracket-block as standalone signal (backward-compatible)

## [18.4.0] - 2026-05-09

### Fixed

- Generalize archival prefix filter to match any `[* Report]` title pattern (not just `[research report]`) in list-issues.sh and find-lock-issue.sh

## [18.3.0] - 2026-05-09

### Added

- Restore 5 specialist reviewer archetypes (structure, correctness, testing, security, edge-cases) that were merged into 2 in v18.0.0
- Add Claude generic reviewer to rounds 1-3 of both /review and /implement --quick review panels (7 reviewers total when all available)

### Changed

- Cursor-down fallback in specialist slots now skips to 1 generic Codex instead of spawning N Codex specialist instances

## [18.2.2] - 2026-05-09

### Changed

- Adds explicit continuation reminders at halt-prone orchestrator boundaries so long-running skill workflows keep advancing after intermediate deliverables.
- Defines the shared step-boundary anti-halt convention separately from Skill-tool return reminders.
- Pins /implement boundary coverage with a Makefile-wired regression harness.

## [18.2.1] - 2026-05-08

### Added

- LARCH_TOKEN_BUDGET_CAP_IMPLEMENT and LARCH_TOKEN_BUDGET_CAP_REVIEW env vars for automatic per-step budget caps without explicit --token-budget-cap flag passing

### Fixed

- Implement launchers now emit KV envelope (LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit) on stdout when the token budget cap is hit, preventing step2-implement.sh from treating cap-hit as a retryable runtime failure
- step2-implement.sh now emits STATUS=bailed REASON=cap_hit when a launcher hits the budget cap, surfacing a clean signal instead of codex-runtime-failure
- collect-agent-results.sh now classifies STATUS=cap_hit review-launcher outputs as a first-class cap_hit state (HEALTHY=true) that bypasses substantive validation, preventing budget-cap stops from poisoning tool health

## [18.2.0] - 2026-05-08

### Changed

- Infer `inferred:<step>` labels for null-`attributionSkill` transcript rows within a step-mark window in `token-report.sh`, reducing the unattributed token bucket from ~8% to near-zero; document the Skill Attribution two-category model in `token-report.md`

## [18.1.0] - 2026-05-08

### Added

- Add `/fq` alias skill — shortcut for `/fix-issue --quick`

## [18.0.16] - 2026-05-08

### Changed

- Reviewer launcher model-args preflight failures now write .done/.diag/.meta/dirty-tree artifacts (matching cursor-auth-preflight pattern) so collect-agent-results.sh detects failures promptly instead of timing out.
- Review prompt sidecars preserve the user or specialist body before hardening preambles, keeping replay paths idempotent.
- preflight.sh now calls check-clean-tree.sh --fail-closed; sort -- added to check-review-changes.sh.
- Design and review OOS public-boundary docs share the fenced/unfenced security discrimination contract with regression-test pins.

## [18.0.15] - 2026-05-08

### Changed

- Fix stale docs in skills/fix-issue/SKILL.md: update --quick description to reflect actual multi-round review topology (rounds 1-3 multi-reviewer, rounds 4-7 single generic — no voting panel)
- Fix plugin.json description: remove dormant Gemini reviewer claim, update plan review from "3-reviewer panel" to "8-reviewer panel (4 Codex + 4 Cursor archetypes)", fix sketch count from 9-agent/3-quick to 4-agent/2-quick
- Fix "Codex generic slot" label in docs/agents.md and docs/review-agents.md: rename to "Codex archetype slot", update fallback chain from Codex → Claude to Codex → Cursor (same archetype) → Claude, and add "same archetype" qualifier to Cursor → Codex fallbacks
- Fix find-lock-issue.sh resolver prose in skills/fix-issue/SKILL.md Step 0: add fallback-chain detail (gh repo view → scripts/github-remote-repo.sh → git remote)

## [18.0.14] - 2026-05-08

### Changed

- Rebalance test harness shards by splitting overloaded shard 6 (41 tests) into shards 6 and 7 (~20 tests each); expand CI matrix to 7 parallel cells.

## [18.0.13] - 2026-05-08

### Added

- Add .claude/rules/verify-external-tool-invocations.md: rule requiring verification of external CLI invocations (exact flags) before landing PRs that touch scripts, skills, or workflows

## [18.0.12] - 2026-05-08

### Fixed

- Fix Cursor review launcher to never pass --sandbox enabled, preventing crashes on hosts where the cursor-agent sandbox runtime is unavailable (issue #1583)

## [18.0.11] - 2026-05-08

### Added

- Add --token-budget-cap N flag to all six external-tool launcher scripts (cursor/codex/gemini review and implement) to short-circuit fan-out when combined vendor tokens since the last ledger mark exceed the cap, with a one-line operator warning, STATUS=cap_hit output, and .cap-hit sidecar
- Add scripts/check-step-token-budget.sh helper to read the session JSONL token-ledger and return cap_hit or under_cap status

## [18.0.10] - 2026-05-08

### Changed

- Fix recurrent double blank line after CHANGELOG entry by fixing separator logic in write_changelog_entry and changelog_categories_to_markdown

## [18.0.9] - 2026-05-08

### Added

- Add scripts/test-implement-cleanup-roundtrip.sh integration test verifying read_state + verify_cleanup_target round-trip with unquoted prefix

### Fixed

- Fix EXPECTED_TMPDIR_BASENAME_PREFIX literal-quote leak in /implement Steps 13.5/14 heredoc so Step 18 verify_cleanup_target no longer refuses rm-rf with session-id-match=y (#1572)
- Add negative assertion (31g) to test-implement-structure.sh pinning unquoted prefix form and forbidding quoted form

## [18.0.8] - 2026-05-08

### Changed

- Cache `node_modules` in the lint CI job so `npm ci` is skipped entirely when `package-lock.json` and `package.json` are unchanged, saving ~12s per run. `npm ci` now runs only when either the `node_modules` or Puppeteer cache misses.

## [18.0.7] - 2026-05-08

### Changed

- Reduce implement and review green-path validation output by routing relevant checks through a bounded Bash helper
- Preserve failure diagnostics with private captured logs, redacted triage artifacts, and fail-closed redaction behavior
- Add hook and harness coverage that prevents active orchestrators from drifting back to Skill invocation

## [18.0.6] - 2026-05-08

### Changed

- `scripts/read-session-env-key.sh` now tolerates an explicitly empty `--file ""` when `--default` is set (emits the default and exits 0). Standalone `/design` and `/review` invocations whose `SESSION_ENV_PATH` is intentionally empty no longer emit `--file is required` stderr noise. An OMITTED `--file` flag still keeps the usage error so caller bugs are not masked.

### Fixed

- `/implement` Step 13.5 / Step 14 state-file snippet now mirrors the full four-step `CLONE_TAG` algorithm (basename, sanitize, truncate to 32 chars, empty-fallback) used by `scripts/session-setup.sh` and `scripts/implement-finalize.sh::clone_basename_prefix`, so `EXPECTED_TMPDIR_BASENAME_PREFIX` matches the actual session tmpdir basename and Step 18's `verify_cleanup_target` no longer refuses rm-rf on every standard run. Closes #1563.

## [18.0.5] - 2026-05-08

### Fixed

- `/implement` Step 18 — emit a closing `Step 18 — done` token / timing ledger mark after the terminal `--since-last-mark --terse` reports so cross-run vendor records logged in the shared `pwd-hash` ledger fallback no longer accrue to the prior run's `Step 18 — cleanup` bucket. Resolves #1544 (umbrella #1553 Token Cost Savings Drive).

## [18.0.4] - 2026-05-08

### Changed

- `/design` regular-mode sketch fan-out reduced from 8 external slots to 4 (Cursor-Arch + Cursor-Edge + Codex-Innovation + Codex-Pragmatic). The 2 quick-mode slots and the 8-reviewer Step 3 plan-review panel are unchanged. Closes #1549 (umbrella #1553 — Token Costs Savings Drive). Updates runtime authorities (`sketch-launch.md`, `sketch-prompts.md`), the `skills/design/SKILL.md` description and Step 2a launch blocks, sibling launcher contracts (`launch-review.md`, `launch-review.md`, `cursor-wrap-prompt.md`), `docs/collaborative-sketches.md` table and mermaid, `skills/implement/SKILL.md`'s both-externals-down rationale, and `skills/shared/topology.tsv` (regenerating `docs/topology.md`). Adds an audit note in `docs/voting-process.md` recording that vote-aggregation thresholds are sketch-count-independent. Adds a structural assertion in `scripts/test-design-structure.sh` pinning the four retained sketch output paths and updates `scripts/test-generate-topology-docs.sh` fixtures to the new topology.

## [18.0.3] - 2026-05-08

### Changed

- `/fix-issue` Step 4 short-circuits `COMPLEXITY` to `SIMPLE` when `--quick` is set on the PR path, so the displayed classification matches the runtime behavior (which already forwarded `--quick` to `/implement` on the HARD bullet).

## [18.0.2] - 2026-05-08

### Added

- `LARCH_CURSOR_SANDBOX` env var (#1561) gating whether `scripts/launch-review.sh --tool cursor` passes `--sandbox enabled` to the inner `cursor agent` argv. Set to `disabled` (case-insensitive, surrounding whitespace tolerated) on hosts where `cursor-agent`'s sandbox runtime is unavailable; default and any unrecognized value preserve the issue #1529 behavior with a stderr warning on typos.

### Changed

- `scripts/launch-review.sh --tool cursor` HARD CONSTRAINTS read-only preamble is now rendered conditionally: the enforcement sentence describes CLI-sandbox enforcement on the default path and describes the degraded posture (prompt constraints + post-run dirty-tree sidecar) on the disabled path, so the preamble does not lie to the model when the sandbox is opted out.
- Trust-boundary docs (`SECURITY.md` § External tool delegation, `docs/external-reviewers.md`, `docs/review-agents.md`, `docs/configuration-and-permissions.md`) document the env var, when to use it, and the degraded enforcement consequence; `scripts/test-launch-review.sh` adds 8 assertions pinning the disabled-path argv shape, the unrecognized-value warning behavior, and the conditional preamble text.

## [18.0.1] - 2026-05-08

### Changed

- `/design` Step 3 plan-review and `/review` Step 3 voting-cycle sub-phases now emit `token-ledger.sh mark` calls alongside the existing `timing-ledger.sh` marks. The `scripts/token-report.sh` markdown table renders these as adjacent flat-segment rows under the parent `Step 1 — design plan` / `Step 5 — code review` segments — measurement prerequisite for #1550 (Haiku-routing ROI gate). Closes #1557.

## [18.0.0] - 2026-05-08

### Added

- `agents/reviewer-correctness-edges.md` (label `Correctness-Edges`) and `agents/reviewer-security-structure-tests.md` (label `Security-Structure-Tests`)
- Resolve #1543: `scripts/run-relevant-checks-captured.sh` adds a script-first relevant-checks path for `/implement` and `/review`, capturing verbose check output under the session tmpdir and emitting a bounded green-path `RELEVANT_CHECKS_OK=true` line. New helper, validation, byte-budget, failure-redaction, `/review`, and hook-backstop harnesses pin the stdout budget, tmpdir/site validation, redacted failure envelope, and active-session Skill-deny behavior.

### Changed

- `/review` and `/implement --quick` panels: combine 5 hand-maintained Cursor reviewer specialists into 2 (`reviewer-correctness-edges` + `reviewer-security-structure-tests`) — Cursor fan-out drops from 5x to 2x per run, cutting per-`/implement` Cursor + Codex review cost by roughly 60%
- `/implement` and `/review` now call the relevant-checks helper instead of invoking the `/relevant-checks` Skill on the green path; failures direct the orchestrator to `REDACTED_LOG_FILE`, and a PreToolUse hook blocks accidental `/relevant-checks` Skill calls inside active implement/review sessions.

### Removed

- `agents/reviewer-correctness.md`, `agents/reviewer-edge-cases.md`, `agents/reviewer-security.md`, `agents/reviewer-structure.md`, `agents/reviewer-testing.md` — backward-incompatible (MAJOR), replaced by the two new combined-personality files

## [17.1.1] - 2026-05-08

### Changed

- `bump-version`: cap Claude-appended escalation reasoning to ≤100 words / ≤5 sentences and forbid commentary on non-escalation runs to reduce ~23.5k Claude output tokens/run.

## [17.1.0] - 2026-05-08

### Added

- `/fix-issue` accepts an optional `--quick` flag, forwarded to `/implement` on the HARD bullet to override the SIMPLE/HARD complexity classification and force quick mode (skips `/design`, single-reviewer loop). SIMPLE is unaffected since it already passes `--quick`.

## [17.0.26] - 2026-05-08

### Changed

- Resolve #1530: bundle CHANGELOG dup heading, anchor-template false-positive guard, macOS bash 3.2 manual gate. Restores agnix-fix Added block at line 68 to '## [17.0.9] - 2026-05-08' (was duplicate '## [17.0.12]'); narrows Step 9a.1 security-token filter with a fenced-vs-unfenced discrimination procedure, security counter-invariant requiring at least one unfenced occurrence in real security findings, and a known-limitation note that upstream sites at plan-review.md/voting.md still substring-only (end-to-end propagation tracked as OOS_1); adds 'Manual Release Gates' section to docs/linting.md documenting macOS bash 3.2 'make test-create-pr' as a manual pre-release gate; extends scripts/test-implement-structure.sh assertion (24c) with grep -Fq pins on the new discrimination phrases.

## [17.0.25] - 2026-05-08

### Changed

- Resolve #1514: launcher defensive parity (combined OOS observations from #1497 and #1465; #1465 in turn combined #1457 and #1432). (A) Each of the six external-tool launchers (`scripts/launch-{codex,cursor,gemini}-{review,implement}.sh`) now applies the `[[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]` guard from #1480 to the `LARCH_TIMING_TASK_KIND` env path: an empty or flag-shaped env value silently falls back to the per-tool default (`codex-review`, `cursor-review`, `codex-implement`, `cursor-implement`, `gemini-review`, `gemini-implement`). The CLI `--timing-task-kind` flag still hard-rejects bad values with `exit 2` — only env-derived values fall back. Whitespace-only env values intentionally remain handled by `scripts/timing-ledger.sh`'s `^[a-z][a-z0-9-]{0,63}$` regex backstop. Per-launcher harness regressions added that assert env-supplied `LARCH_TIMING_TASK_KIND="--prompt"` does NOT bypass the guard, using isolated `LARCH_TIMING_LEDGER` TSV grep mirroring `scripts/test-launch-review.sh`'s case-TM pattern. All six sibling `.md` docs (`scripts/launch-{codex,cursor,gemini}-{review,implement}.md`) updated with one timing sentence documenting the env fallback. (B) `scripts/test-launch-review.sh` gains a localized `LARCH_TOKEN_SESSION_ID`-isolated assertion that exercises `scripts/launch-review.sh --tool codex`'s `token-ledger.sh record-vendor codex total=$N raw=codex_review` call: a per-test dedicated codex stub emits `tokens used\n42\n` on stderr (so it lands in `${OUTPUT}.sidecar` where the launcher scrapes it), launcher exit 0 is asserted before the ledger assertion, and `jq -e` matches `vendor=codex raw=codex_review total=42` in the dumped ledger. (C) `scripts/launch-codex-implement.sh` (model-args resolution failure) and `scripts/launch-cursor-implement.sh` (`cursor_launcher_load_model_args` failure) now emit the same five-line KV envelope as `launch-gemini-implement.sh`'s `resolve_gemini_model` failure path (`LAUNCHER_EXIT=`, `MANIFEST_WRITTEN=false`, `QA_PENDING_WRITTEN=false`, `TRANSCRIPT=`, `SIDECAR_LOG=`, `exit 0`) instead of the legacy raw `exit "$rc"`. Both launchers truncate `SIDECAR_LOG` (`: > "$SIDECAR_LOG"`) before appending captured stderr so stale chatter from prior runs cannot mix into preflight diagnostics. After /review FINDING_1, `scripts/launch-gemini-implement.sh` was brought up to the same truncation parity. The Cursor branch uses an explicit `MODEL_ARGS_RC=0; ... || MODEL_ARGS_RC=$?` idiom to avoid inherited-shell-state misclassification. File-header exit-semantics blocks in both `.sh` files and the sibling `.md` docs gained one bullet/paragraph each describing the new exit-0 preflight envelope. Coverage in `skills/implement/scripts/test-{codex,cursor,gemini}-implementer.sh` exercises the real `agent-model-args.sh` / model resolver via `LARCH_{CODEX,CURSOR,GEMINI}_MODEL` control-character / blank values, asserts wrapper exit 0 + `LAUNCHER_EXIT!=0` + the KV envelope + non-empty `SIDECAR_LOG`, plus a `STALE-SENTINEL-1514` preseeded sidecar that must be wiped post-run; the codex / cursor harnesses additionally assert two-attempt retry behavior (`step2-implement.sh`'s clean-tree single-retry branch) on persistent preflight failure and stable bail-token classification matching the Gemini reference outcome.

## [17.0.24] - 2026-05-08

### Changed

- Resolve #1531: surface `cache_read` and `cache_create` columns in `scripts/token-report.sh`'s Claude markdown table — the jq harvester `usage_row` already captured `cache_read_input_tokens` and `cache_creation_input_tokens` per assistant turn, but `claude_table` only emitted `Claude Input` and `Claude Output`, so reports understated Anthropic input volume by hiding cache reads (typically 5-20x uncached input on long orchestrators) and cache writes. Widen the 2-column `vendor_header` and `vrow` jq helpers (used only by `claude_table`) to a 6-column shape: `Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output`. Per-vendor (`vendor_header5` / `vrow5`) tables, the terse-line format, ledger schema, and `usage_row` are unchanged. Update `scripts/test-token-report.sh` golden header assertion plus three new body-row pin assertions for Step 1 step-total (`1 | 2 | 3 | 4`), Step 2 step-total (`10 | 20 | 30 | 40`), and Grand total (`11 | 22 | 33 | 44`) so a regression that zeros / swaps cache columns or drops them from `vrow` while keeping the column count would fail (harness now 116/116, was 113/113); reword the pipe-parity comment to describe the live-header-derived budget rather than pin "4 columns"; drop now-legitimate "Cache read" / "Cache create" from the negative-needle list. Update `scripts/token-report.md` Table Shape section with the new column list and restore concrete illustrative billable-proxy multipliers (`cache_read*0.1 + cache_create*1.25`) with an explicit "verify against current Anthropic pricing" disclaimer. Update `scripts/test-token-report.md` prose to reflect the 6-column header. Update `skills/implement/references/anchor-comment-template.md` token-report scaffold from 4-column to 6-column Claude header so the canonical template matches the renderer.

## [17.0.23] - 2026-05-08

### Changed

- Resolve #1529: cursor and codex review launchers (`scripts/launch-review.sh --tool cursor`, `scripts/launch-review.sh --tool codex`) now run in a CLI-level read-only sandbox — `cursor agent -p --trust --mode plan --sandbox enabled` (replacing `--force --trust`) and `codex exec --sandbox read-only -C "$PWD"` (replacing `--full-auto`'s workspace-write). Each launcher also prepends a HARD CONSTRAINTS read-only preamble to every prompt (specialist, generic, sketch, debater, voter), mirroring `scripts/launch-review.sh --tool gemini`'s `GEMINI_REVIEW_HARDENING_PREAMBLE`. The CLI sandbox is the primary mitigation; the prompt preamble is its prompt-level reinforcement. The contract applies wherever these review launchers are used — `/review`, `/implement --quick` Step 5, `/design` plan-review, `/design` sketches, `/design` dialectic debaters. The implementer launchers (`scripts/launch-codex-implement.sh`, `scripts/launch-cursor-implement.sh`, `scripts/launch-gemini-implement.sh`) are intentionally untouched because their job is to edit the working tree.

### Fixed

- Resolve #1529: review-launcher empty-output retry no longer double-prepends the HARD CONSTRAINTS preamble. `${OUTPUT}.prompt` (consumed by `collect-agent-results.sh` retry via `--prompt-file`) now stores the user-original body so retries read the body, prepend the preamble exactly once, and produce an identical outgoing PROMPT — no preamble stacking. Caught by the round-1 `/review` panel and pinned by a new retry-idempotency proof case in both `scripts/test-launch-review.sh` and `scripts/test-launch-review.sh` (replay via `--prompt-file` against the prior run's `OUTPUT.prompt` sidecar must produce exactly 1 preamble in argv). `SECURITY.md`, `docs/review-agents.md`, and `docs/external-reviewers.md` updated to reflect the new mechanical CLI-level read-only sandboxing posture for review-launcher lanes.

## [17.0.22] - 2026-05-08

### Fixed

- Resolve #1515: `/fix-issue` Step 0 now probes working-tree cleanliness via the new shared `scripts/check-clean-tree.sh` helper (invoked with `--fail-closed`) BEFORE the `issue-lifecycle.sh comment --lock` and title rename, so a dirty tree aborts the run with `exit 2` and a clear `ERROR=Working tree is not clean. Commit or stash changes, then re-run /fix-issue. No issue was locked.` message — leaving the `GO` sentinel and original title intact instead of trapping the operator with an `[IN PROGRESS]`-prefixed locked issue that previously required manual `IN PROGRESS` comment deletion plus title-prefix strip plus re-adding `GO`. The probe covers the explicit-target, auto-pick, and umbrella-dispatch paths uniformly (including a separate exit-2 sub-case for `git status --porcelain` invocation failure with the prefix `ERROR=Cannot determine working-tree cleanliness:` so consumers can substring-match the two classes). `scripts/preflight.sh` adopts the same shared helper in default fail-open mode (preserving its historical empty-stdout-as-clean semantics) but now also treats an empty / unrecognized `CLEAN=` line as fail-closed (per code-review feedback against round 1) and stops swallowing helper stderr — so operators see git diagnostics that `scripts/check-clean-tree.md` advertises as "echoed for operator debugging." Both callers go through one canonical predicate, structurally eliminating the drift risk between them. `skills/fix-issue/SKILL.md` Step 0 prose + Known Limitations "Lock-before-setup behavioral delta" entry are updated to reflect the new pre-lock gate. New `scripts/test-check-clean-tree.sh` regression harness covers clean / dirty / git-failure under both fail-open and `--fail-closed` modes; `skills/fix-issue/scripts/test-find-lock-issue.sh` adds a `with_sterile_repo` wrapper plus dirty-tree fixtures for the explicit-target, auto-pick, umbrella-dispatch, and probe-failure paths. The `scripts/preflight.sh` fail-open-on-git-invocation-failure asymmetry (whether to flip preflight to `--fail-closed`) is filed as a follow-up OOS issue — its scope is narrowed by this PR since the structural drift is already eliminated.

## [17.0.21] - 2026-05-08

### Changed

- Resolve #1493: consolidate post-bump-version Bash work into a new `scripts/implement-finalize.sh postbump` subcommand that owns the Step 8 anchor fragment write, Step 8a CHANGELOG amend, Step 8b rebase, and Step 8b force-push gate. The subcommand uses a `.postbump-phase` checkpoint file under `$IMPLEMENT_TMPDIR` to resume at the force-push gate after the prompt-driven Rebase + Re-bump Sub-procedure returns from a Step 8b rebase conflict — the operator override of the dialectic 2-1 majority traded explicit `--resume-from` flag plumbing for an implicit checkpoint that further reduces prompt-side coordination after `/bump-version` returns (the load-bearing halt-protection contract from the issue's telemetry: "Cogitated for 37m 28s" after `✅ 8: bump-version` success). `skills/implement/SKILL.md` Step 8/8a/8b are rewritten to invoke `postbump` once per branch (bump-commit-exists, BUMP_TYPE=NONE, HAS_BUMP=false, forked) and the legacy "skip directly to Step 8b" prose is removed; `scripts/implement-finalize.{sh,md}` and `scripts/test-implement-finalize.{sh,md}` document the new subcommand contract, stdout grammar (`STATUS=ok|skipped|conflict|rebase-failed|push-failed|remote-check-failed|changelog-failed|branch-mismatch|postbump-state-corrupt|postbump-cwd-not-repo`), and 152-assertion test coverage spanning happy/skip paths, conflict checkpoint write+resume, corrupt/symlink/oversized checkpoint rejection, multi-category CHANGELOG composition (manifest `summary_bullets_categorized` + Claude-fallback `--changelog-bullets-file Category<TAB>bullet`), Unreleased section preservation (including Unreleased-as-final-section EOF), duplicate-target-header rejection (fail-closed `STATUS=changelog-failed` instead of silent first-match-only behavior), `set -e` leak elimination across all guarded probes, `git rev-parse --show-toplevel` cwd guard, MANIFEST_PATH containment via `validate_small_tmp_file`, and the `--resume-from` flag rejection (since the checkpoint mechanism replaced the explicit-flag approach). `skills/implement/references/rebase-rebump-subprocedure.md` step8b_rebase return-target paragraph updated; `.claude/skills/bump-version/SKILL.md`, `SECURITY.md`, and `docs/linting.md` synced to reflect the new boundary. The structural anti-halt critical-boundary callout for Step 8 is wired into `skills/implement/SKILL.md` Step 8 prose so the post-`/bump-version` boundary is explicitly tagged as mid-run. OOS follow-ups filed for the pre-existing `## [17.0.12]` duplicate-header on `origin/main` (pre-dating this branch), the substring-based security-tag exclusion in the anchor-comment template, and the bash-3.2 macOS CI gap.

## [17.0.20] - 2026-05-08

### Changed

- Resolve #1513: combined session-env script defensive fixes (OOS observations from #1505 and #1504). **A.** `scripts/read-session-env-key.sh` extraction rewritten from the legacy `awk -F= '$1==k{print $2}'` form to a whole-key prefix match plus `substr` after the first `=`, so values containing additional `=` characters round-trip without truncation (parallel to `value="${line#*=}"` in `session-setup.sh`'s caller-env parser). **B.** `scripts/write-session-env.sh` adds a regex+length guard on `--timing-ledger` that mirrors the existing `--claude-source-file` check (`^[A-Za-z0-9_./~+-]{1,512}$`), giving direct callers (test harnesses, future skills) writer-side defense-in-depth that complements #1463's session-setup-side validation. New offline regression harness `scripts/test-session-env-roundtrip.sh` (14 assertions; multi-`=`, empty, trailing-`=`, comma-separated KV-list, KEY-prefix collision, present-empty + `--default`, and `--timing-ledger` accept/reject/overlong/absent fixtures), wired into `Makefile` (`test-harnesses-1`), `agent-lint.toml`, `docs/linting.md`, and the `scripts/read-session-env-key.md` Test-harness section. Stale awk-pattern descriptions in `scripts/read-session-env-key.{sh,md}` headers — which still cited the truncating legacy form — were aligned with the corrected implementation; `--default`'s "missing OR empty" semantics were clarified in the script header to match the contract doc.

## [17.0.18] - 2026-05-08

### Changed

- Resolve #1511: `scripts/token-report.sh` follow-ups (combined OOS from PR #1494). (A) `replace_token_block` aligns its marker handling with `scripts/assemble-anchor.sh`'s whole-line anchored regex (`^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$` and the matching `-end-` variant) for BOTH the awk rewrite (matched-pair branch and lone-marker branches) AND the `has_begin` / `has_end` presence probes (now `grep -Eq` with the same anchored pattern). Probe / rewrite parity is load-bearing — round-1 review consensus surfaced two data-loss paths against non-conforming input (whole-line begin + prose-only end mention silently dropped post-marker tail; prose-only mentions of both markers silently no-op'd the replacement). Files whose marker mentions appear only in prose now route through the no-marker append path: existing content preserved, fresh block appended. (B) Stop leaking the absolute jq-stderr temp path on stdout under `LARCH_DEBUG_TOKEN_REPORT`. `RENDER_FAIL_REASON` now carries a fixed `failed to parse token sources (jq stderr captured; debug)` phrase; the actual file path is emitted to the script's own stderr (`token-report.sh: jq stderr captured at <path>`). The published surface (stdout, which flows verbatim into tracking-issue anchors and PR bodies) no longer carries TMPDIR / username-bearing absolute paths. `scripts/token-report.md` updated to describe the new published-surface contract and the whole-line marker regex parity. `scripts/test-token-report.sh` expanded (115 / 115 assertions): (a) `LARCH_DEBUG_TOKEN_REPORT` truthy-spelling loop splits stdout / stderr and asserts the fixed phrase on stdout, the path line on stderr, no path leak on stdout, and a non-empty captured stderr file; (b) negative-spelling loop checks neither suffix appears; (c) three new whole-line marker regression cases (`PROSE_MARKER` for matched-pair preservation, `WHOLE_BEGIN_PROSE_END` for lone-begin recovery against prose-only end, `PROSE_BOTH_NO_WHOLE_LINE` for no-marker append against prose-only mentions of both markers). `scripts/test-token-report.md` updated to describe the new contract.

## [17.0.17] - 2026-05-08

### Changed

- Resolve #1502: dedup the byte-equivalent launcher helpers shared between the Cursor and Codex external-tool launchers into two new sourced-only common libraries — `scripts/lib-external-launcher-common.sh` (canonical `external_launcher_promote_inner_done` / `external_launcher_append_outer_meta`) and `scripts/lib-dirty-tree-sidecar.sh` (canonical `_write_dirty_tree_sidecar`). Per-tool wrappers `lib-codex-launcher-common.sh` and `lib-cursor-launcher-common.sh` now source the new common lib and expose the same `codex_launcher_*` / `cursor_launcher_*` names as one-line aliases, so existing call sites in `launch-review.sh --tool codex`, `launch-review.sh --tool cursor`, and `launch-cursor-implement.sh` are unchanged. The two review-launch wrappers (`launch-review.sh --tool codex`, `launch-review.sh --tool cursor`) source `lib-dirty-tree-sidecar.sh` instead of defining their own `_write_dirty_tree_sidecar` copy. After review feedback (Cursor structure + testing specialists round 1), `scripts/launch-review.sh --tool gemini` was also folded in: it now sources the same `lib-dirty-tree-sidecar.sh` so all three external-reviewer launchers share one implementation, and the lib's stricter `[[ -n "$DIRTY_TREE_SIDECAR" ]] || return 0` guard (originally Gemini-only) is hoisted to benefit all three callers. `agent-lint.toml` excludes both new sourced-only libraries from the executable check, consistent with existing `lib-*` exclusions. Sibling `.md` docs added for the new libraries; `Edit-in-sync` registries on `lib-codex-launcher-common.md`, `lib-cursor-launcher-common.md`, `launch-review.md`, `launch-review.md`, `launch-cursor-implement.md`, and `launch-review.md` updated.

## [17.0.16] - 2026-05-08

### Changed

- Resolve #1512: add CI structural pins to `scripts/test-implement-structure.sh` for the two follow-ups combined into #1512. Assertion `(29)` pins the anti-pattern doc-drift literals added by #1480 across `skills/design/references/dialectic-execution.md` (the recovery sentence), `skills/design/references/heavy-worker.md` (the `run_in_background: true` + yield anti-pattern and the `**SendMessage dependency.**` heading-style label), and `AGENTS.md` (the `` `/design --subagent` requires `SendMessage` `` bullet). Assertion `(30a)`/`(30b)`/`(30c)` pins the Coder simplicity override section in `skills/implement/SKILL.md` (heading, gate phrase, literal breadcrumb). Sibling `scripts/test-implement-structure.md` updated and the script header / assertion-history block refreshed to cover assertions 29-30.

## [17.0.15] - 2026-05-08

### Changed

- Resolve #1478: external implementers now triage doc drift and small bugs (rules 1-2 of `skills/implement/SKILL.md` § "OOS triage policy") inline into the implementer's own commit before emitting any public OOS candidate, with a sanitized `Inline-triage rule N: <reason>` annotation in `commit_message`. Security-tagged OOS findings are kept out of public accepted-OOS artifacts and `/issue` handoffs at three boundaries: `skills/design/references/plan-review.md` (accepted-OOS write to `oos-accepted-design.md` and `$DESIGN_TMPDIR/oos.md` visibility write), `skills/review/references/voting.md` (diff-mode accepted-OOS write to `oos-accepted-review.md`, mirroring the description-mode model already at line 32), and `skills/implement/references/anchor-comment-template.md` (Step 9a.1 defensive re-exclusion as the first operation after artifact reads, before dedup / combine / cap / file-conflict pre-pass). The canonical security-token match is `focus-area\s*=\s*security` case-insensitive anywhere inside the `### OOS_N:` block. `skills/implement/SKILL.md` and `skills/implement/references/codex-manifest-schema.md` prose narrowed to reflect the post-retrofit state; `SECURITY.md` documents the local-hold contract. Lightweight structural assertions added to `scripts/test-design-structure.sh`, `scripts/test-review-structure.sh`, and `scripts/test-implement-structure.sh`.

## [17.0.14] - 2026-05-08

### Changed

- Resolve #1487: bring `scripts/launch-review.sh --tool gemini` to dirty-tree sidecar parity with the contract introduced for Cursor/Codex by #1437. The Gemini reviewer launcher now publishes `${OUTPUT}.dirty-tree` via `scripts/check-mid-run-dirty-tree.sh --mode baseline` after every agent-ran path (success, JSON normalization failure, snapshot-guard-triggered revert, non-git fail-open) and emits `STATUS=unknown` with a documented `REASON=` token (`fail-closed-no-agent-ran` from `fail_closed`, `exit-trap-no-agent-ran` from the EXIT trap) on early short-circuits where no agent ran (MISSING_JQ, model-resolve failure, snapshot-guard setup failure). Pre-launch baseline capture via `scripts/snapshot-untracked.sh` and the sidecar variable assignments are sequenced before the EXIT trap registration so signal-driven exits in the narrow window between trap install and assignment can still publish a sidecar. Gemini reviewer call sites remain dormant per `SECURITY.md`; this is preparatory machinery so `/review` Step 5 sidecar consultation picks up Gemini coverage automatically when the call sites are reintroduced. The dirty-tree sidecar coexists with the existing repo-root snapshot guard (both run, covering overlapping but not identical surfaces). Regression coverage extended in `scripts/test-launch-review.sh` for success / `MISSING_JQ` / one resolver-rejection / non-git success / snapshot-guard mutation paths; sibling contracts at `scripts/launch-review.md`, `scripts/test-launch-review.md`, `docs/external-reviewers.md`, `docs/linting.md`, and `SECURITY.md`'s dormant-Gemini paragraph updated in lockstep.

## [17.0.12] - 2026-05-08

### Changed

- Resolve #1496: add a bash 3.2 regression test in `scripts/test-create-pr.sh` for the `create-pr.sh` empty-array `set -u` defect. The defensive `${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"}` expansion itself shipped via PR #1506 (#1464), which threaded `--repo` and parameterized `--base` across the `gh` CLI helpers and as a side-effect guarded all four `GH_REPO_ARGS` expansion sites in `create-pr.sh`. Issue #1496 was filed in parallel to specifically pin the macOS `/bin/bash` (3.2) `set -u` failure scenario. The new test invokes `create-pr.sh` without `--repo` against a stubbed `gh`/`git` and asserts: (a) no `unbound variable` abort on stderr, (b) `PR_STATUS=created` on stdout, (c) no `--repo` argument threaded into the `gh` stub log. The block re-runs under `/bin/bash` when that interpreter is bash 3.x — the actual macOS system shell that triggered the defect — and is a no-op skip on Linux runners shipping bash 4+ as `/bin/bash`. Verified by demonstrating the new test FAILs against the pre-#1506 script under `/bin/bash` 3.2.57 and PASSes against current main.

## [17.0.11] - 2026-05-08

### Fixed

- Resolve #1486: `scripts/snapshot-untracked.sh` no longer deletes the user-controlled `$OUTPUT` path on argument-parsing errors. The unknown-flag arm previously ran `rm -f "$OUTPUT" "${OUTPUT}.tmp"` — a typo'd later flag after a valid `--output <path>` would silently delete that path. The arm now logs to stderr and exits 0 without touching the output. Folded inline (rule 2): `${2:?--output requires a value}` replaced with an explicit guard that exits 0 instead of 1 on missing `--output` value, preserving the always-exit-0 contract. Header in `scripts/snapshot-untracked.sh`, sibling `scripts/snapshot-untracked.md`, and `skills/implement/SKILL.md` Step 5 narrowed from "any failure" to "operation failure" (git/sort/mv) vs. "argument-parsing failure" so the split contract is documented in all three places.

## [17.0.10] - 2026-05-08

### Changed

- Resolve #1463: combined OOS observations from #1459, #1444, #1434. **A.** `scripts/session-setup.sh` `--write-session-env` path now forwards `--timing-ledger` (mirroring the existing `--token-session-id` / `--claude-source-file` passthrough) when caller-env supplies `LARCH_TIMING_LEDGER`, gated by an inline `is_safe_timing_ledger_path` validation that requires absolute paths under `${TMPDIR:-/tmp}`, `$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, `$REVIEW_TMPDIR`, or `dirname("$CALLER_ENV")`. Validation failure emits a single stderr warning and skips forwarding (fail-soft); the key is intentionally NOT echoed on session-setup stdout (file-only contract). **B.** `scripts/session-setup.sh` inline GitHub remote URL parser (lines 322-339) now delegates to `scripts/github-remote-repo.sh` after `gh repo view` fails, preserving fail-soft `REPO_UNAVAILABLE=true` semantics. The helper anchors `owner/repo` exactly while the legacy inline regex matched the trailing two segments — a deliberate fail-closed tightening for malformed remotes that the legacy regex would have mis-parsed. **C.** Hook subprocess env-inheritance investigation: existing production wiring binds `session_id` from the hook-event JSON payload (not from inherited LARCH_TOKEN_SESSION_ID), so a one-line breadcrumb cross-reference is added to `skills/implement/scripts/hook-post-design.sh` and `skills/implement/scripts/hook-stop-fail-close.sh` — no behavior change. New regression coverage: `scripts/test-session-setup-repo-fallback.sh` (gh-success / gh-fails-SSH / gh-fails-HTTPS / gh-fails-malformed / gh-fails-no-origin) wired through Makefile `test-harnesses-*`; `skills/implement/scripts/test-implement-review-token-propagation.sh` extended for `LARCH_TIMING_LEDGER` (positive forwarding + negative-stdout + negative-validation cases). Two follow-up OOS issues filed: #1504 (writer-side `--timing-ledger` validation in `scripts/write-session-env.sh`) and #1505 (awk-truncation fix in `scripts/read-session-env-key.sh`).

## [17.0.9] - 2026-05-08

### Added

- Resolve #1484: add private dev-only `/agnix-fix <issue-number>` skill at `.claude/skills/agnix-fix/SKILL.md`. Wraps `/implement --forked --quick --auto --coder=codex` for fixing `agent-sh/agnix` issues end-to-end from a fork clone. Fetches the upstream issue via `gh issue view --repo agent-sh/agnix --json title,body,state,url`, validates `state=OPEN` and rejects PR URLs, then composes a feature description from the upstream URL/title/body and forwards to `/implement`. Bakes in CI-monitoring guidance for the deterministic `add-to-project.yml` failure on fork PRs (`secrets.PROJECT_TOKEN` is org-level on `agent-sh` and not shared with forks). Idempotently provisions the `skip-changelog` label on the fork via `gh api repos/$FORK_REPO/labels/skip-changelog` 404-check + `gh label create`. Defensive guards: strict `owner/repo` match on `git remote get-url upstream` (HTTPS / SSH / `ssh://` forms via sed normalization, then equality vs `agent-sh/agnix`); per-run random 16-byte hex delimiter wrapping the upstream issue body to resist prompt-injection from a hostile issue body in `--auto` mode (collision-guarded — refuses if body already contains the delimiter); `gh` stderr captured separately so warnings cannot corrupt the JSON stream `jq` parses; explicit `--coder=codex` to suppress the small-plan auto-route (#1481) on Rust agnix work. Not shipped to other plugin consumers; place in `.claude/skills/` only.

## [17.0.8] - 2026-05-08

### Changed

- Resolve #1464: thread `--repo` through repo-targeted `gh` calls and parameterize `--base` in `scripts/create-pr.sh`. New `scripts/resolve-repo.sh` prints `OWNER/REPO` from `gh repo view --json nameWithOwner` (with a `scripts/github-remote-repo.sh origin` fallback that handles trailing-slash and credentialed HTTPS forms). `scripts/create-pr.sh` accepts a new `--base BASE_REF` flag, falling back to `gh repo view --json defaultBranchRef`'s value, then to `main`; its `"${GH_REPO_ARGS[@]}"` expansions are now guarded with the `${arr[@]+"${arr[@]}"}` pattern so `set -euo pipefail` + bash 3.2 (macOS default) do not crash with "unbound variable" when neither `--repo` nor the resolver supplies a value. `scripts/extract-closes-issue-from-pr.sh` fails closed (exit 0 with empty stdout) when the resolver returns empty, preventing silent mis-routing under fork-configured clones. `scripts/implement-finalize.sh` Step 18's round-trip-detection branch resolves `repo` via the helper before its `gh issue view` fallback. `--repo` threaded through repo-targeted `gh` calls in `skills/fix-issue/scripts/{blocker-helpers,finalize-umbrella,find-lock-issue,issue-lifecycle,umbrella-handler,get-issue-details}.sh` and `skills/issue/scripts/fetch-issue-details.sh`. Defensive `(.labels // [])` in `skills/fix-issue/scripts/get-issue-details.sh` so a null `labels` field cannot crash `set -euo pipefail` downstream of a successful `gh issue view`. Three follow-up OOS items filed as #1501 / #1502 / #1503 (token-report jq-stderr path leak under `LARCH_DEBUG_TOKEN_REPORT`, launcher common-helper duplication, token-report marker substring vs. whole-line regex inconsistency) — all OOS items belong to recently-merged PRs and are out of scope for this branch. Regression coverage: `scripts/test-resolve-repo.sh` gains trailing-slash and credentialed-HTTPS cases; existing `scripts/test-create-pr.sh` covers the `--base` flag.

## [17.0.7] - 2026-05-08

### Changed

- Resolve #1469: misc SIMPLE cleanups rollup. **B1.** `docs/installation-and-setup.md` makes explicit that `jq` is required for halt-protection hooks (PostToolUse `hook-post-design.sh` + Stop `hook-stop-fail-close.sh`); without `jq`, both hooks short-circuit at their `command -v jq` probe and halt protection is silently disabled. **B2.** `scripts/implement-finalize.sh` surfaces the previously-silent `touch "$IMPLEMENT_TMPDIR/.run-cleaned-up"` failure via `warn_line` (writes to stdout and increments `FINALIZE_WARNINGS`) so an ENOSPC / FS-permission / read-only-mount mishap does not leave the post-/design Stop hook blocking on the next session. Best-effort posture preserved (no exit). **C1.** Retire `scripts/gh-pr-body-read.{sh,md}` (acknowledged debt — no caller after `scripts/extract-closes-issue-from-pr.sh` inlined `gh pr view --json body`); drop the corresponding `agent-lint.toml` exclusion. The negative-presence `(11d-1)` assertion in `scripts/test-implement-structure.sh` is unchanged and still pins zero invocations from `references/rebase-rebump-subprocedure.md`. **C2.** `scripts/rebase-push.sh` inline comments at the script header, exit-code docs, stdout-contract block, and the `--no-push` early-exit guard now reference `$BASE_TARGET` / "the configured base ref" in place of the literal `origin/main`, matching the parameterized code (`--base-remote` / `--base-ref` defaults preserve `origin` / `main`). **A.** Item A from the rollup (`scripts/tracking-issue-write.sh:91-104` byte-vs-character header reconciliation) was already addressed by PR #1443 — verified, no edit.

## [17.0.6] - 2026-05-08

### Fixed

- Resolve #1480: rewrite `skills/design/references/dialectic-execution.md` lines 32-48 to substitute `--timing-task-kind` literals directly per side (`cursor-debate-thesis`, `cursor-debate-antithesis`, `codex-debate-thesis`, `codex-debate-antithesis`), removing the variable indirection that lured the heavy-worker subagent into the `VAR=value cmd ... "$VAR"` env-var-prefix idiom (the gotcha: `"$VAR"` expands in the parent shell BEFORE the prefix scope, so the launcher receives `--timing-task-kind` followed immediately by the next flag). Add an inline anti-pattern note explaining the bash gotcha and a recovery-discipline sentence (re-launch + synchronous `collect-agent-results.sh` in the same Bash message, no yield between). Add defensive `--timing-task-kind` value validation to all six launchers (`scripts/launch-{codex,cursor,gemini}-{review,implement}.sh`): empty values and values starting with `--` are now rejected with exit 2 and the message `--timing-task-kind requires a non-empty, non-flag-like value`. Same-PR regression assertions in `scripts/test-launch-{codex,cursor,gemini}-review.sh` and `skills/implement/scripts/test-{codex,cursor,gemini}-implementer.sh` per `.claude/rules/launcher-argv-test-coverage.md`. Update launcher sibling contracts (`scripts/launch-*.md`) to document the new validation per `.claude/rules/script-md-siblings.md`. Append a `run_in_background: true` + yield + "await notifications" anti-pattern bullet plus a SendMessage subagent-suspend dependency paragraph to `skills/design/references/heavy-worker.md` "Wait Discipline" section. Document the SendMessage dependency under AGENTS.md "Conventions" so operators in environments without `SendMessage` know to pass `--inline` to `/implement`. Two follow-up OOS issues filed: (1) extend the same defensive validation to the `LARCH_TIMING_TASK_KIND` env-var-default path; (2) add a doc-drift lint asserting the new anti-pattern phrases stay present in `dialectic-execution.md` / `heavy-worker.md` / `AGENTS.md`.

## [17.0.5] - 2026-05-08

### Changed

- Resolve #1477: combined leaked-SIMPLE OOS cleanup. **A.** `skills/implement/SKILL.md` Step 0.5 MANDATORY-read paragraph: replace the stale literal "the eight section slugs" with "the canonical slugs per `scripts/anchor-section-markers.sh`" so the doc points readers at the executable source of truth instead of pinning a count that has drifted (the canonical list is now eleven slugs). **B.** `scripts/test-implement-structure.sh` assertion (9d): after the existing `awk` extraction of the Step 9a.1 OOS pipeline procedure section, assert the extracted slice is `>= 4000` bytes with a clear failure message naming the likely cause ("has a new ## heading been inserted inside Step 9a.1 of anchor-comment-template.md?"). Without this guard, a stray top-level `##` heading inside Step 9a.1 silently truncates the slice and the dependent (9d)-(9h) literal pins fail in opaque ways. The current section is ~17KB, so the 4000-byte floor catches any plausible early-truncation slice while leaving plenty of margin for normal copy evolution. Sibling contract `scripts/test-implement-structure.md` updated in lockstep.

## [17.0.4] - 2026-05-08

### Changed

- Resolve #1466 sub-items A and B (combined OOS cleanup downstream of #1429's token-report split). **A. `LARCH_DEBUG_TOKEN_REPORT` opt-in jq-stderr capture** (`scripts/token-report.sh`): replace the unconditional `2>/dev/null` jq stderr silencer with an explicit allowlist gate (`1`/`true`/`TRUE`/`True`/`yes`/`YES`/`Yes`/`on`/`ON`/`On`); negative spellings (`no`, `off`, `disabled`, `0`, empty, unset) keep the default silent path. When enabled, jq stderr redirects to a `mktemp` file under `${TMPDIR:-/tmp}` named `larch-token-report-jq-stderr-XXXXXX` (chmod 0600 explicitly applied as defense-in-depth) and the path is appended to the unavailable message as `(jq stderr at <path>)` on render failure with non-empty stderr. The stderr file is removed on render success and on render failure with empty stderr so `$TMPDIR` is not littered with empties. **B. Legacy `<!-- token-report-begin -->...<!-- token-report-end -->` block strip** (`scripts/assemble-anchor.sh emit_run_statistics`): pre-#1429 anchors embedded the Token Report inside `run-statistics`; after the split that block lives in its own `token-report` section, so resumed runs against pre-split anchors would publish duplicate Token Report content without this migration. The strip is implemented as an iterative awk pass (loops to a fixed point so multi-pair fragments and stray-end-then-pair residue both normalize), with whole-line-anchored marker regexes (so a legitimate prose / table-cell line that merely *mentions* the marker substring is not treated as a structural sentinel), and a `had_pair` pre-scan (so an orphan begin/end found after a matched pair is dropped as marker-line-only — NOT routed into the lone-marker branch that would strip BOF→end / begin→EOF and delete legitimate surrounding content). Lone-begin / lone-end semantics for genuinely-degraded input (no matched pair in the original) are preserved. **C.** `skills/research/references/eval-set.md` slug count was already resolved by commit cf3b5e5 (#1429); no edit. Regression coverage: `scripts/test-assemble-anchor.sh` adds (b8) matched-pair strip, (b9) lone-begin, (b10) lone-end, (b11) multi-pair, (b12) matched-pair + orphan end, (b13) matched-pair + orphan begin; `scripts/test-token-report.sh` adds full truthy-allowlist loop (1/true/yes/on with case variants), an explicit negative-spelling list including a hermetic `env -u`-isolated unset case, and a TMPDIR-isolated success-path stderr-temp-leak check.

## [17.0.3] - 2026-05-08

### Changed

- Resolve #1437: detect mid-run working-tree pollution between `/implement` Step 0 and downstream steps. New `scripts/check-mid-run-dirty-tree.sh` emits `STATUS=clean|dirty|unknown` with `--mode baseline|checkpoint`; `scripts/launch-review.sh --tool cursor` and `scripts/launch-review.sh --tool codex` capture a pre-launch untracked baseline, publish a post-invocation `${OUTPUT}.dirty-tree` sidecar before `${OUTPUT}.done`, and route Cursor's auth-preflight short-circuit through `STATUS=unknown` (not `STATUS=clean`) so consumers cannot mistake "no detector ran" for "tree proven clean". `/review` aggregates per-launcher dirty markers into `$IMPLEMENT_TMPDIR/review-dirty-tree-summary.env` and copies referenced `TRACKED_PATHS_FILE` / `NEW_UNTRACKED_PATHS_FILE` sidecars into `$IMPLEMENT_TMPDIR/review-dirty-tree-streams/` before its cleanup so `/implement`'s scoped recovery can reach them. `/implement` Step 5 (normal mode + new 5.3.b in quick mode) reads the summary and fires a three-option `AskUserQuestion` (restore / labeled stash / bail) regardless of `auto_mode`. Recovery commands documented portably for both GNU and BSD: `git restore --pathspec-from-file=- --pathspec-file-nul -- < TRACKED_PATHS_FILE` for tracked changes, `[ -s NEW_UNTRACKED_PATHS_FILE ] && xargs -0 git clean -f -- < NEW_UNTRACKED_PATHS_FILE` for new untracked files (`git clean` does not accept `--pathspec-from-file`; the portable stdin form works on both GNU and BSD xargs, while `xargs -0 -a FILE` is GNU-only and fails on macOS). Single-runner invariant added under AGENTS.md "Conventions" mirroring `/fix-issue`'s Known Limitation. SECURITY.md updated under the external-reviewer trust-model section. New `scripts/test-check-mid-run-dirty-tree.sh` harness wired into `Makefile` shard 3, with fixtures for clean baseline, tracked-dirty, staged-dirty, new-untracked-dirty, baseline-missing-untracked-ambiguous, three git-probe failure paths, atomic-publish leftover guard, AND a `checkpoint`-mode dirty fixture. `scripts/check-mid-run-dirty-tree.sh` baseline-mode `cat`/`sort` pipelines guarded with `if ! …; then emit_unknown …; fi` so any pipeline failure under `set -euo pipefail` still publishes `STATUS=unknown` and exits 0. `/implement` Step 5.3.b mid-run dirty-tree sidecar scan added so quick-mode reviewer rounds gain the same backstop normal-mode review provides via `review-dirty-tree-summary.env`. Codex launcher's EXIT trap consolidated into a single `_codex_exit_dispatcher` that runs timing-record → temp-file cleanup → dirty-tree sidecar → `.inner.done → .done` promotion in fixed order, mirroring Cursor's `_publish_done_on_exit` discipline. `docs/external-reviewers.md` documents the sidecar contract and retry behavior. CI rebase: rephrase manifest-reuse-path mention of `post-design-boundary.sh` in `skills/implement/SKILL.md` so the `test-implement-post-design-boundary.sh` `awk` extraction lands on the wrapper invocation block instead of the prose mention.

## [17.0.1] - 2026-05-07

### Fixed

- Resolve #1475: align the absent-sentinel encoding for the `.claude-plugin/plugin.json` baseline check in `skills/implement/scripts/step2-implement.sh`. The Step 1 baseline write now uses an empty file (`: > "$file.tmp"`) when `plugin.json` is absent, and the Step 6b post-implementer comparison uses `CURRENT_PLUGIN_JSON=""` for the same absent state. Previously the baseline used `printf '\n'` while the post-check used `$'\n'`, which compared unequal because `$(cat …)` strips trailing newlines per POSIX. The mismatch caused a deterministic false-positive `protected-path-modified` bail for `--coder=codex` (default), `--coder=cursor`, and `--coder=gemini` in any consumer repo lacking `.claude-plugin/plugin.json`. New Test 13 in `skills/implement/scripts/test-step2-dispatch.sh` covers the absent-then-still-absent case end-to-end with a stub Codex spawn → manifest → Step 6/7 → dispatcher-side commit flow, asserting `STATUS=complete` plus `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` + `MANIFEST=` per NEVER #10. Test 12 entry added to `test-step2-dispatch.md` to close the previously latent 11→13 numbering gap.

## [17.0.0] - 2026-05-07

### Changed

- `/implement` auto-routes small surgical changes to the main Claude agent when no `--coder` flag is set. New `coder_explicit` boolean tracks whether `--coder=...` was explicitly parsed; new "Coder simplicity override" sub-step in Step 1 flips `coder=claude` when `coder_explicit=false` AND `design_only=false` AND the resolved plan describes a small change (≤ ~100 LOC, no new abstractions, no new architectural contracts, no large refactors). Step 2.4 entry list and print-bullet ladder updated with first-match-wins ordering so the legacy `--codex-available false` and Cursor/Gemini health-fallback paths cannot collide with the auto-route bullet. Override is suppressed when `$IMPLEMENT_TMPDIR/step2-spawn-coder.txt` already records an external coder (in-progress resume case) so it cannot bypass the dispatcher's `coder-mismatch-tmpdir-reuse` guard. Operators who require a particular implementer regardless of plan size pass `--coder=<value>` explicitly — the explicit value wins. Routes through the existing `STATUS=claude_fallback` + `ORCHESTRATOR_EDIT_AUTHORITY=allowed` path; no new code path or script change.

## [16.0.1] - 2026-05-08

### Changed

- Resolve #1462: aggressively reduce /implement's OOS issue spam. The Step 9a.1 combine pass now leads with two prepended hard-combine rules — Rule A (LLM-judged "same logical concern" grouping) and Rule B (leaked SIMPLE singletons whose Description implies doc-drift or a less-than-30-LOC fix) — that cascade into the existing similarity criteria 1-4 (independence-respect intact) and the existing hard-combine criteria 5/6. Both new rules explicitly OVERRIDE the "do NOT combine genuinely independent entries" carve-out. A new ephemeral `oos-grouping-worksheet.md` artifact is written under `$IMPLEMENT_TMPDIR` for in-session human/review auditability of Rule A's grouping decisions; the worksheet uses `INPUT_<i>` indexing (post-3.3 merged-batch ordinal, NOT raw source `OOS_N`), a YAML key-per-line block format with `concern` / `group` / `justification` / `sources` keys, singleton group IDs of the form `g-singleton-<i>`, and is NOT consumed by `oos-issue-cap.sh` / `oos-file-conflict-deps.sh` / `/issue --input-file` and NOT one of the `anchor-sections/*.md` data fragments. Sentinel-recovery runs skip Rules A/B and worksheet writes for the same reason they skip criteria 1-6. New CI assertion `(9h)` in `scripts/test-implement-structure.sh` adds 11 fixed-string greps over the Step 9a.1 procedure block pinning Rule A/B literals, the ASCII cascade arrow `Rule A -> Rule B -> existing criteria 1-4`, override-independence semantics, the worksheet path and contract sub-pins, the sentinel-skip clauses, and the Rule B singleton predicate. SKILL.md cross-references at the OOS triage policy preamble, threshold convention, actionable consequence, Step 5.5, and Step 9a.1 manifest harvest are updated to reflect the new cascade and the worksheet artifact.

## [16.0.0] - 2026-05-07

### Changed

### Fixed

- `scripts/lint-mermaid-fences.sh` now passes `--no-sandbox` and `--disable-setuid-sandbox` to Chromium via a repo-pinned Puppeteer config (`scripts/lint-mermaid-puppeteer.json`) so the SVG-render fallback launches on Ubuntu 23.10+ runners with restricted unprivileged user namespaces. Previously CI (`Lint Mermaid fences (changed only)`) failed before any Mermaid syntax check on PRs touching `.md` files containing fences. Also fixes pre-existing `lint-mermaid-fences` failures in `docs/workflow-lifecycle.md` (parser choking on literal `(...)` text in pipe edge labels).

## [15.15.5] - 2026-05-07

### Fixed

- Resolve #1472: `/set-up-forked-open-source-repo` no longer aborts with `fork parent mismatch: expected <upstream>, got <none>` on valid forks. `gh repo view --json parent` does not always populate `.parent.nameWithOwner` — only `.parent.owner.login` and `.parent.name` — so the prior single-field jq expression evaluated to empty and rejected legitimate forks. `phase_github` in `skills/set-up-forked-open-source-repo/scripts/setup-forked-open-source-repo.sh` now prefers a non-empty `.parent.nameWithOwner` and otherwise composes `<owner.login>/<name>` from the populated subfields, with type guards (`.parent.owner` must be an object; `.login` and `.name` must be strings) so a malformed payload produces the stable `fork parent mismatch ... got <none>` diagnostic rather than a raw jq index/type abort. A pre-parse `jq -e 'type == "object"'` gate routes syntactically-invalid `gh` output through a dedicated `gh repo view returned invalid JSON` diagnostic. The case-insensitive comparison and `if .parent == null then empty` "not a fork" short-circuit are unchanged. Adds four regression cases to `test-setup-forked-open-source-repo.sh` (`parent-split-fields`, `parent-malformed-owner`, `parent-numeric-fields`, `parent-invalid-json`); updates `SECURITY.md` and the script's contract `.md` to match the parser's behavior.

## [15.15.4] - 2026-05-07

### Changed

- Resolve #1468: align downstream catalogs/allowlists with the actual catalog of shipped larch skills. `README.md`'s `## Skills` HTML table now lists `/upgrade-larch`. `docs/skills.md` gains a `## /upgrade-larch` section plus matching TOC entry, and recovers a missing `[/skill-evolver](#skill-evolver)` TOC bullet whose section already existed below. `.claude/settings.json` `permissions.allow` adds 13 missing `Skill(...)` entries (11 fully-qualified `larch:*` forms documented in the strict-permissions snippet — `larch:alias`, `larch:create-skill`, `larch:design`, `larch:fix-issue`, `larch:im`, `larch:imaq`, `larch:implement`, `larch:imq`, `larch:issue`, `larch:research`, `larch:review` — plus `Skill(upgrade-larch)` and `Skill(larch:upgrade-larch)` matching the new README row). All entries inserted in strict ASCII-codepoint order; no existing entries removed. Documentation/configuration alignment only; no functional code changes.

## [15.15.3] - 2026-05-07

### Fixed

- Resolve #1426: anchor mermaid diagrams now render reliably. Adds `scripts/sanitize-mermaid-fragment.sh`, a write-time validator that rejects the two failure classes documented in #1404 (literal `|` inside flowchart node labels; HTML `<br>` and `$` inside `sequenceDiagram` participant aliases) with a structured public-safe `STATUS=rejected REASON_TOKEN=<token> fence=<N> line=<N>` envelope, fail-closed on internal error, an optional `--from-md` mode that walks every ` ```mermaid ` fence per file, and a `--warnings-log` append path that lands categorized `### Warnings` entries via the new `scripts/append-execution-issue.sh` helper. `/design` Step 3b, `/implement` Step 7a, `/implement` Step 9a (PR-body composition), and `scripts/assemble-anchor.sh` (defense-in-depth at upsert time) all gate on the sanitizer and substitute heading-keyed placeholders (Architecture / Code Flow / unknown) for rejected fences, with fail-closed Tool Failures logging when the sanitizer is unreachable. CI gains a separate `lint-mermaid-fences (changed-only)` step that runs `mmdc` over every changed `.md` fence; `actions/checkout` now uses `fetch-depth: 0` and `scripts/lint-mermaid-fences.sh` fail-closes (exit 2) in CI when the diff base is unreachable instead of silently exiting 0. Adds `package.json` + `package-lock.json` (committed) pinning `@mermaid-js/mermaid-cli@11.12.0`; CI uses `npm ci` and a Puppeteer cache keyed on the lockfile so cold Chromium downloads only happen on dependency bumps. Contributors editing `.md` files locally must run `npm install` once (or `SKIP=lint-mermaid-fences` to opt out) — documented in `docs/installation-and-setup.md`. Authoring guidance lives at `skills/shared/mermaid-safe-content.md` (forbidden patterns, workarounds, Node toolchain maintenance) and is cross-referenced from `SECURITY.md`. Round-2 review surfaced and fixed three additional sanitizer bypasses (unclosed YAML frontmatter, indented mermaid fences with up to 3 leading spaces per GFM, multi-space `participant` declarations) plus the CI fetch/range failure mode. Regression coverage: 27 fixtures in the new `scripts/test-mermaid-fragments.sh` harness (wired into `test-harnesses-6`); 5 new fixtures across `test-assemble-anchor.sh` / `test-refresh-anchor.sh` for the per-fence rejection / warnings-log forwarding / IMPLEMENT_TMPDIR env-default paths.

## [15.15.2] - 2026-05-07

### Fixed

- Resolve #1428: token-ledger session id now propagates across Claude Code Bash tool calls and external launcher subshells. `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE` are persisted in `$IMPLEMENT_TMPDIR/session-env.sh` (extended `scripts/write-session-env.sh` with `--token-session-id` / `--claude-source-file`); every orchestrator-side `token-ledger.sh` / `token-report.sh` Bash block in `skills/implement/SKILL.md` now rehydrates both keys via `read-session-env-key.sh` before invoking the script. `step2-implement.sh` and all 6 launchers (`launch-codex-implement.sh`, `launch-review.sh --tool codex`, `launch-cursor-implement.sh`, `launch-review.sh --tool cursor`, `launch-gemini-implement.sh`, `launch-review.sh --tool gemini`) gain an authoritative-overwrite preamble that derives the canonical session id from `IMPLEMENT_TMPDIR/session-id` and overwrites any stale env value. `/review` (nested under `/implement` Step 5) inherits both keys via `session-setup.sh --caller-env`. A structure-test pin in `scripts/test-implement-structure.sh` asserts every SKILL.md `token-ledger.sh` / `token-report.sh` call site has the rehydrate prefix; `scripts/test-token-ledger.sh` gains a rehydrate-chain regression and an overwrite-stale assertion; new `skills/implement/scripts/test-implement-review-token-propagation.sh` proves the parent `/implement` → nested `/review` propagation. The result: every `/implement` run from the same cwd now writes to a session-id-keyed `larch-tokens-<sha>.jsonl` ledger that no other run shares; tracking-issue Token Reports no longer accumulate stale rows from prior runs. Code review accepted FINDING_4 — `scripts/token-report.sh::replace_token_block` now detects half-written anchor files (exactly one of `<!-- token-report-begin -->` / `<!-- token-report-end -->` present) and recovers via stderr warning + drop-adjacent-content + fresh append, instead of compounding duplicate sections.

## [15.15.1] - 2026-05-07

### Fixed

- Resolve #1427: surface vendor token totals in the per-vendor token report so Codex (which only exposes an aggregate `tokens used` count via its CLI) no longer renders as `Input=0 | Output=0` for every step. `scripts/token-report.sh` adds a fifth `Total` column to per-vendor markdown tables (Codex / Cursor / Gemini / future vendors) — the Claude table keeps its existing 4-column shape via dedicated `claude_header4` / `crow4` helpers and is mechanically locked against accidental widening by the new vendor-only `vendor_header5` / `vrow5` helpers. `vendor_row` now synthesizes `total` from `input + output + cache_read + cache_create` only when the ledger row's `total` key is missing entirely; rows that record an explicit numeric `total` (including zero) render that value as-is. `scripts/token-report.md` documents the asymmetric Claude (4-col) / vendor (5-col) shape via header literals; `scripts/test-token-report.sh` extends the Codex step- and grand-total assertions plus a legacy total-absent fallback fixture and tightens its pipe-parity classifier (Claude=4 vs vendor=5, keyed off the most recent `###` heading line); `scripts/test-token-vendor-scrapers.sh` (under the existing `jq` guard) records a Codex aggregate-only vendor row and asserts the renderer surfaces the total in the new column. `scripts/launch-codex-implement.sh` and `scripts/launch-review.sh --tool codex` are unchanged — Codex CLI does not expose an input/output split, so the launcher path continues to record `total=N` only and the renderer is now the surface that makes that visible.

## [15.15.0] - 2026-05-08

### Added

## [15.14.0] - 2026-05-07

### Added

- Resolve #1414: new `/set-up-forked-open-source-repo` skill that reconfigures a single git checkout for the upstream-fork OSS contribution workflow. Operates on cwd only (no multi-clone batch). Rewires `origin`→fork and `upstream`→upstream idempotently across three starting layouts (origin-upstream-only, origin-upstream-named-fork, already-configured), unsets `remote.origin.pushurl` to neutralize stale pushurls carried over from renamed `<named-fork>` remotes, sets the invalid-scheme `larch-disabled://` sentinel on `remote.upstream.pushurl`, fetches `origin --prune --tags`, sets `main` to track `origin/main`, and fast-forwards when clean. Phase A (one-time GitHub-side setup) verifies the fork via `gh repo view` with case-insensitive `parent.nameWithOwner` matching and offers a destructive scoped mirror-sync (`+refs/heads/* +refs/tags/*` from a fresh `mktemp -d` mirror clone of upstream) gated by TTY confirmation or `--mirror-confirmed` plus a TOCTOU re-probe; the post-push assertion compares the fork's new `refs/heads/main` to the SHA the mirror clone actually contained, not the pre-confirmation upstream snapshot, so a benign upstream advance during the destructive window does not spuriously fail an already-completed sync. Phase B mutations are wrapped in a snapshot-driven `ERR`-trap rollback (`restore_remote_state`) that stays armed through `phase_submodules` and `phase_verify`; assertion failures inside those late phases use a `phase_die` helper (`printf >&2; false`) so the rollback fires on the trap rather than `exit`-bypass. URL-override env vars (`LARCH_FORKED_REPO_URL_OVERRIDE_*`) are gated behind explicit `LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE=1` opt-in to neutralize a leaked-test-env-var footgun; `phase_preflight` now runs `normalize_github_url` on `remote.origin.url` BEFORE the first `git fetch origin` so a non-GitHub stored URL is rejected without a network round-trip. The remote classifier in `lib-remotes.sh` enumerates remotes via `git remote` + `git config --get-all` instead of regex-flattened config keys so dotted remote names (`my.fork` → `remote.my.fork.url`) participate in classification. `--init-submodules` is a strictly opt-in flag (default off) per #1414's safety posture; default runs leave `.gitmodules` alone. Ships with a 49-assertion offline regression harness exercising all three remote-state classifications, ambiguous-state refusals (including duplicate fork remotes, dotted-fork-name handling, multi-`pushurl` rejection), dirty / ahead / diverged refusals, fork-missing path with marker, non-404 `gh` failure path (rate-limit / SSO / network), TOCTOU mid-confirmation, scoped-refspec mirror push (verifies non-head/tag refs do NOT propagate), partial-failure rollback (mid-rewrite + late-phase `in-verify` injection points), rollback-failure recovery report, DISABLED upstream push sentinel, and submodule-default no-op semantics. Wired into `Makefile` shard `test-harnesses-3`, `agent-lint.toml` exclusions, `docs/skills.md`, `docs/configuration-and-permissions.md` strict-permissions list, `docs/installation-and-setup.md`, `docs/workflow-lifecycle.md`, `README.md` skills table, and `SECURITY.md` (destructive-sync posture, URL-override footgun, `url.*.insteadOf` residual, pushurl-survival hardening).

## [15.13.11] - 2026-05-07

### Changed

- Resolve #1429: split the anchor's run-statistics section so token tables get their own dedicated `token-report` slug, raise `PER_SECTION_CAP` from 8000 to 14000 chars in `scripts/tracking-issue-write.sh`, and emit a stderr warning when per-section truncation fires (was silent). The split moves the Token Report block (previously appended to `run-statistics.md` by `token-report.sh --append-run-statistics`) to a new `anchor-sections/token-report.md` fragment file, producer flag renamed `--append-run-statistics` → `--append-token-report`. `SECTION_MARKERS`, `COLLAPSE_PRIORITY`, the anchor-comment template, `/implement` Step 9a.1/11/18 callers, and the test harnesses are updated to walk the new canonical slug set. Existing anchor comments on older issues remain compatible: `assemble-anchor.sh` synthesizes any missing section as an empty marker pair on first upsert. Code review accepted FINDING_8 — extended `scripts/test-implement-structure.sh` `(28b2)` to assert `<!-- section:token-report -->` open/close markers in `anchor-comment-template.md`, mirroring the existing `(28b)` timing-report check.
- **Operator note:** Out-of-tree wrappers passing the old `--append-run-statistics` flag will silently no-op because `scripts/token-report.sh`'s `unavailable()` exits 0 on unknown flags. Update such callers to `--append-token-report` and rebase your fragments to write to `anchor-sections/token-report.md`.

## [15.13.10] - 2026-05-07

### Fixed

- Resolve #1433: close the partial-content observability window in `scripts/compose-review-findings.sh`'s archive publish path. The previous `cp "$TMP_JSONL" "$ARCHIVE_PATH"` could expose a half-written `docs/review-archive/issue-<N>.jsonl` to readers if interrupted mid-write. Replaced with a same-directory staged write — `mktemp "${ARCHIVE_PATH}.XXXXXX"` inside `$ARCHIVE_DIR`, copy `$TMP_JSONL` in, then `mv -f` to publish — which guarantees an atomic rename on POSIX same-filesystem semantics (the prior bare `mv -f` from `$TMP_JSONL` could fall back to copy+unlink across filesystems and reintroduce the same window). Failure paths in both staging and publish remove the tempfile before `fail`. Harness `scripts/test-compose-review-findings.sh` case (e) now asserts the archive directory contains only the published JSONL after a successful run, pinning the no-leftover-staging-tempfile invariant.

## [15.13.9] - 2026-05-08

### Fixed

- Resolve #1430: silence the cosmetic `rm: <TMPROOT>: Permission denied` stderr emitted by the EXIT trap in `scripts/test-collect-agent-retry.sh` during `make test-harnesses-1`. The warning was a transient macOS-APFS race: a backgrounded retry subshell (spawned by `scripts/collect-agent-results.sh` and chained via `wait_for_reviewers.sh`) could still hold a per-case workdir as cwd when the harness's EXIT trap fired. All TMPROOT contents are user-owned with normal permissions and a manual `rm -rf` succeeds; cleanup is best-effort tmpdir disposal that the OS reaps regardless. Trap now redirects rm stderr to `/dev/null` with a 4-line comment recording the rationale (review-round-1 follow-up). 121/121 test assertions still pass.

## [15.13.8] - 2026-05-08

### Changed

- Resolve #1425: combined OOS follow-ups (compose-review-findings JSONL safety + per-field redaction; lib-resolve-implement-tmpdir TTL/session binding via LARCH_TOKEN_SESSION_ID; sessionstart-health jq-missing fallback hardening; launch-gemini-implement preflight parity). Code-review-time hardening: SECURITY.md updated to drop the stale "intentionally not changed" claim about `scripts/launch-gemini-implement.sh` and document the new force-false KV envelope on model-resolution failure; `lib-resolve-implement-tmpdir.sh` TTL boundary tightened from `> ttl` to `>= ttl` (a candidate exactly TTL seconds old is now treated as stale, matching the operator-facing intent); `hook-post-design.sh` and `hook-stop-fail-close.sh` now parse `.session_id` from the Claude Code hook stdin payload and `export LARCH_TOKEN_SESSION_ID="$SID"` before sourcing the resolver, so the session-id binding branch is reachable in production (the in-bash `export` from `/implement` Step 0 does not propagate to hook subprocesses on its own). New regression coverage in `skills/implement/scripts/test-post-design-boundary.sh` for the TTL boundary and the hook-stdin session-id surfacing path (positive + negative).
- **Operator note:** `compose-review-findings.sh` now requires `jq` on PATH (was previously tolerant via python3/sed fallback). Install via `brew install jq` / `apt install jq`. The `/implement` Step 5 anchor compose step fails closed when jq is absent.

## [15.13.7] - 2026-05-08

### Added

- Resolve #1417: project-wide guard against improvised `ScheduleWakeup` calls outside skill-script direction. New bullet in `AGENTS.md` extending the existing anti-polling rule, mirroring `NEVER` ratchets in `skills/fix-issue/SKILL.md` (entry #8 of the existing Anti-patterns list) and a new `## Anti-patterns` section in `skills/research/SKILL.md`; `skills/implement/SKILL.md` already carries `NEVER` #9 and is unchanged. New `scripts/test-anti-improvised-wakeup.sh` regression harness (sibling contract `scripts/test-anti-improvised-wakeup.md`) pins the load-bearing literal `NEVER improvise ScheduleWakeup outside skill-script direction` at all three project anchors plus the legacy `NEVER call` ScheduleWakeup `anywhere in the` /implement `orchestrator` literal in `skills/implement/SKILL.md`. Wired into `Makefile` (new `test-anti-improvised-wakeup` target registered in the lightest `test-harnesses-1` shard) and excluded from `agent-lint.toml`'s `dead-script` list (Makefile-only invocation pattern matching every other `test-*.sh`). Failure mode addressed: a one-shot `/fix-issue` run that finished Step 8 cleanup observed the orchestrator inventing a 1800 s `ScheduleWakeup` to fire another `/fix-issue` iteration outside any skill's script direction; the harness fails CI on editorial drift weakening or removing any of the four anchor literals.

## [15.13.6] - 2026-05-08

### Added

- Resolve #1404: mechanical post-/design halt protection in `/implement` via two additive `hooks/hooks.json` entries. New `PostToolUse` hook on `Skill` (matched against skill name `design` / `larch:design`) auto-invokes `skills/implement/scripts/post-design-boundary.sh` and re-injects its byte-stable stdout into the next assistant turn via `hookSpecificOutput.additionalContext` — preserving the trailing newline by capturing wrapper stdout to `mktemp` and emitting JSON via `jq -Rs --rawfile`. New `Stop` hook refuses session stop when `$IMPLEMENT_TMPDIR/design-export/manifest.env` exists but neither `.boundary-gate-passed` (load-bearing sentinel written by the augmented `post-design-boundary.sh` on success — `touch` failure now triggers `fail_closed` with `ERROR=boundary-gate-sentinel-write-failed` instead of being silently swallowed) nor `.run-cleaned-up` (released by `scripts/implement-finalize.sh teardown` BEFORE both `verify_cleanup_target` and `cleanup-tmpdir.sh` so refused-cleanup paths still release the gate) is present, AND the Stop event is not a `stop_hook_active=true` continuation-loop reentry. Both hooks share a new sourced helper `skills/implement/scripts/lib-resolve-implement-tmpdir.sh` (sibling `.md` stub) that enumerates `claude-implement-*` candidates under all three supported session roots (`${XDG_CACHE_HOME}/larch/sessions`, `/tmp`, `/private/tmp`), filters by `.larch-keepalive` `CLONE_PATH` against the hook's `cwd` field, picks the freshest `manifest.env` mtime with lexicographic tie-break on equal mtimes, and **fails open by early-return when the supplied `cwd` is empty** so missing/unparseable `cwd` (or missing `jq`) cannot misbind to the globally-newest tmpdir. `/implement` Step 1 now writes a `$IMPLEMENT_TMPDIR/.design-only` single-token sidecar (`true|false` + newline) BEFORE invoking `/design` so the hook passes the correct `--design-only` to the wrapper. Stop hook envelope is `{"decision":"block","reason":"..."}` with operator escape paths (hard-quit / remove `design-export/manifest.env` / `touch .run-cleaned-up`) and basename-only path leakage; `hooks.json` `Stop` timeout is 30s (matching `PostToolUse`) so the resolver scan cannot exceed the timeout under accumulated session state. New regression coverage in `skills/implement/scripts/test-post-design-boundary.sh` (T2-T12: byte-identity assertion via `cmp`, sentinel write/non-write/load-bearing-failure, Stop predicate truth table including `stop_hook_active` continuation guard and concurrent-session disambiguation by `cwd` + missing/empty-cwd fail-open paths, executable-bit assertion). New `scripts/test-implement-finalize.sh` cases for `.run-cleaned-up` write before `verify_cleanup_target` (success + sanity-check refusal + non-blocking touch failure). `SECURITY.md` documents both hooks, the deterministic disambiguation under multiple matching `CLONE_PATH` dirs, and the residual stale-tmpdir risk. `skills/implement/SKILL.md` Step 1 post-/design checkpoint blockquote and Step 18 teardown prose name the mechanical enforcement.

## [15.13.5] - 2026-05-07

### Changed

- Resolve #1416: combined design-phase OOS follow-ups from #1410 and #1411. New root `.gitattributes` enforces LF EOL across the repo (default `* text=auto eol=lf` plus explicit `text eol=lf` for `*.md`, `*.sh`, `*.py`, `*.yaml`, `*.yml`, `*.json`, `*.tsv`, `*.toml`, `*.txt`) so CRLF normalization no longer depends on contributor editor settings or `git`'s `core.autocrlf`. `scripts/anchor-section-markers.md` test-harness bullet drops the stale "9-slug" literal in favor of referring to the `SECTION_MARKERS` array by symbol; the array now has 10 slugs (the `timing-report` slug was added). Also folded inline as same-class doc drift: `scripts/test-assemble-anchor.sh` header comment dropped its stale "8 empty marker pairs … (23 lines total)" literal counts in favor of a by-symbol reference to `SECTION_MARKERS`, per `.claude/rules/drift-prone-prose-in-docs.md` "Don't write hardcoded counts in prose".

## [15.13.4] - 2026-05-08

### Changed

- Resolve #1379: Strunk-style brevity polish on `.claude/rules/`. Tightened prose across the 8 long rules (`anchor-section-markers-array.md`, `drift-prone-prose-in-docs.md`, `external-tool-launcher-parity.md`, `launcher-argv-test-coverage.md`, `markdown-no-space-in-code-span.md`, `research-readonly-hook-coupling.md`, `script-md-siblings.md`, `timing-task-kind-allowlist.md`) plus light cleanup on 5 short rules (`no-direct-submodule-edits.md`, `topology-generation.md`, `reviewer-archetype-generation.md`, `skill-editing-trace.md`, `skill-md-description-trigger.md`). Three surgical short rules (`shell-strict-mode.md`, `version-bump-reserved-message.md`, `skill-runtime-root-paths.md`) were intentionally unchanged. **Total**: 21,419 B → 19,313 B (9.83% reduction; ~2,106 B saved across the rules surface). No new rules were added, no rule's claims were changed, no frontmatter keys were introduced, and no file outside `.claude/rules/` was touched (gate 8 enforced). The `topology-generation.md` `paths:` array is byte-preserved and `python3 scripts/check-topology-rule-paths.py` continues to pass. Code-review feedback folded inline restored agent-centered phrasing on `anchor-section-markers-array.md`'s `prevents` line and "prose enumerating supported tools" on `external-tool-launcher-parity.md:24` (3-reviewer convergence on the first; single-reviewer nit on the second). Both fixes preserve the rules' original semantics — the polish bias is brevity that doesn't change what a rule says.

## [15.13.3] - 2026-05-07

### Added

- Resolve #1399: add a CI/lint guard that asserts every distinct runtime-authority path in column 4 of `skills/shared/topology.tsv` is covered by an exact literal entry in the `paths:` frontmatter array of `.claude/rules/topology-generation.md`, so future TSV row additions force-extend the rule's `paths:` and Codex/Cursor/Gemini load the topology-generation rule when editing those authority files. New `scripts/check-topology-rule-paths.py` (Python 3 + PyYAML 6.0.2) parses the TSV with `open(..., newline="")` (CRLF survives for explicit rejection per the existing topology generator's hygiene), validates per-row column count and non-empty col 1 / 2 / 4, runs the same path-grammar rules as `scripts/generate-topology-docs.sh::validate_repo_path` plus an explicit leading/trailing-whitespace rejection, deduplicates col 4 into a `set[str]`, then `yaml.safe_load`s the rule file's first frontmatter block (validating `paths` is `list[str]`) and computes the set difference; non-empty difference is printed as a sorted "missing from rule paths:" diagnostic to stderr with exit 1. Dual lint surface per the design-phase Round 1 binding: a new step in the existing `agent-sync` job in `.github/workflows/ci.yaml` (uses the same `actions/setup-python@v6` + `pip install -r .github/workflows/requirements-lint.txt` posture as the `lint` and `test-harnesses` jobs) and a new `repo: local` hook in `.pre-commit-config.yaml` (`additional_dependencies: ['pyyaml==6.0.2']` matching the existing `lint-skill-invocations` pin; scoped via `files:` regex on the TSV, the rule, and the script itself; `pass_filenames: false`; no `always_run`). New `scripts/test-check-topology-rule-paths.sh` regression harness (~17 fixtures: happy path, multi-missing-authority sorted-stderr failure, extra rule paths permitted, CRLF rejection in both files, malformed-row rejection, empty col 1 / 2 / 4, path-grammar rejection including trailing whitespace, missing/non-list/non-string `paths:`, missing frontmatter, block-list and flow-style YAML, comments/blanks tolerance, **real-registry smoke pinning the current 7 distinct runtime authorities**, empty-TSV rejection per accepted plan-review FINDING_12, and non-root-cwd invocation). Wiring: Makefile `test-check-topology-rule-paths` target registered in the `test-harnesses-4` shard alongside `test-check-generators`. Sibling contracts: `scripts/check-topology-rule-paths.md` and `scripts/test-check-topology-rule-paths.md` per the script-md-siblings rule; `agent-lint.toml` exclude entry for the harness pair (Makefile-only invocation pattern matching the other `test-check-*.sh` entries). `.github/workflows/requirements-lint.txt` header comment updated to name the new PyYAML consumer (`check-topology-rule-paths` covers both the pre-commit hook and the agent-sync invocation); `docs/linting.md` lists the new Makefile target and notes the `agent-sync` job's new Python-dependency surface. Known limitation: the new Python `validate_repo_path` is deliberately stricter than `scripts/generate-topology-docs.sh::validate_repo_path` (adds the trailing-whitespace rejection per accepted plan-review FINDING_6 option (a)); both surfaces still reject paths with trailing whitespace in practice — the generator catches them via its downstream `[[ -f ]]` and `git ls-files --error-unmatch` checks rather than at the validator. Future harmonization of the two validators is preserved as a possible follow-up.

## [15.13.2] - 2026-05-07

### Changed

- Resolve #1397: launcher toolchain follow-up hardening sweep (six subtasks, post-#1367 / #1382). `scripts/tracking-issue-write.sh append-comment` now rejects unsafe non-empty `--lifecycle-marker` IDs before composing the synthesized HTML comment — split-rc validation distinguishes charset rejection (`return 1`) from the dedicated double-hyphen rule (`return 2`, HTML-comment-data invariant: parsers may terminate the comment early on the first `--`), with separate `ERROR=` strings for each case and four new `(e4)` test rows in `scripts/test-tracking-issue-write.sh`. `scripts/run-negotiation-round.sh` reserves exit 3 for `cursor_auth_preflight` failure (distinct from exit 2 reviewer-command failure) and emits `RESPONSE_FILE=$OUTPUT_FILE` symmetrically before exit 3 so callers can parse the response-file path with one rule regardless of failure class. Shared Cursor launcher mechanics live in new `scripts/lib-cursor-launcher-common.sh` (sourced-only library, Bash 3.2-safe; four functions populating fixed globals — no `ARRAY_NAME`/`eval`/`declare -n`, per FINDING_5 alignment with `lib-cursor-auth.sh`'s secret-handling posture). Gemini model resolution is centralized in new `scripts/lib-gemini-model-resolver.sh` with set-aware (`${VAR+x}`) precedence semantics matching `agent-model-args.sh`'s Gemini arm, sourced by all three Gemini consumers (`launch-gemini-implement.sh`, `launch-review.sh --tool gemini`, `check-reviewers.sh` probe). The token vendor scraper harness in `scripts/test-token-vendor-scrapers.sh` now fails early on an empty implementer ledger with variant-aware diagnostic strings (Cursor / Codex / generic).

### Documentation

- Launcher sibling `.md` argv-shape diagrams now match the shipped Bash 3.2-safe argv guards across `scripts/launch-cursor-implement.md`, `scripts/launch-review.md`, `scripts/launch-codex-implement.md`, `scripts/launch-review.md`; see [15.12.69] Item D for the original `agent-model-args.sh` line-token stdout contract.
- Sibling `.md` files updated in lockstep with harness changes per `.claude/rules/script-md-siblings.md`: `scripts/test-tracking-issue-write.md` (new `(e2)` / `(e3)` / `(e4)` assertion rows), `scripts/test-check-reviewers.md` (new resolver-rejection coverage block + edit-in-sync table entries), `scripts/test-launch-review.md` (resolver-rejection assertion paragraph + lockstep edit-in-sync notes), `skills/implement/scripts/test-gemini-implementer.md` (corrected `LAUNCHER_EXIT=<resolver-rc>` + process-exit-0 description matching the launcher's KV envelope), `scripts/run-negotiation-round.md` (stdout envelope symmetry section), `scripts/tracking-issue-write.md` (lifecycle-marker `--` rejection rule + `timing-report` in documented `COLLAPSE_PRIORITY` order). `skills/shared/external-reviewers.md` negotiation section now points readers at `scripts/run-negotiation-round.md`'s exit-code table.

## [15.13.1] - 2026-05-07

### Fixed

- Resolve #1405: tighten the `/design --subagent` heavy-worker contract so it cannot return without finalizing artifacts. Two layers — a prompt-level NEVER-style "Wait Discipline" subsection in `skills/design/references/heavy-worker.md` forbidding the worker from yielding while any `run_in_background: true` sketch / dialectic / reviewer process is still running (the only allowed wait mechanism is a foreground `collect-agent-results.sh` call, or the documented foreground judge collector for dialectic), and a mechanical defense-in-depth post-return artifact gate in `skills/design/SKILL.md` Step 2a's `On DESIGN_HEAVY=complete` branch that fail-closes with `REASON=worker-yielded-without-artifacts` when the agent returns success without three substantive non-empty artifacts (`plan.txt`, `approach-synthesis.txt`, `voting-tally.md` per the heavy-worker contract) or four may-be-empty existence-required artifacts (`contested-decisions.md`, `oos.md`, `rejected-findings.md`, `accepted-plan-findings.md` per `write-design-manifest.sh`'s `copy_required_may_be_empty` calls). The gate also coerces any non-canonical `DESIGN_HEAVY` value (i.e. neither `complete` nor `failed`) to the same fail-closed branch, addressing the issue #1402 trace where the worker yielded with no status line at all. Failure routes through the existing `DESIGN_HEAVY=failed` branch — preserves `$DESIGN_TMPDIR`; standalone path sets `STANDALONE_HEAVY_FAILED=true`; nested path lets parent `/implement` see `MANIFEST_FAILED` at its Step 1 and bail to Step 18 with `STALL_TRACKING=true`. Regression coverage added in `scripts/test-design-structure.sh` as check 12 (gate literals: `REASON` token, three `-s` checks, four `-f` checks), 12b (heavy-worker.md Wait Discipline + "wait for notifications" anti-pattern phrase), and 12c (write-design-manifest.sh `copy_required_may_be_empty` pin so Tier 2 stays mechanically in sync with the manifest writer). Sibling contract updated in lockstep: `scripts/test-design-structure.md`. Known limitation: `dialectic-resolutions.md` is intentionally NOT in the gate because `dialectic-protocol.md` permits absence on the `NO_CONTESTED_DECISIONS` short-circuit and the zero-externals guardrail, while `heavy-worker.md` "Artifact Contract" requires it as an empty file; reconciling those two normative sources is OOS for this PR.

## [15.13.0] - 2026-05-07

### Added

- Resolve #1402: persist full review-finding payloads in the `/implement` tracking-issue anchor under a new `<!-- section:review-findings-full -->` section so future mining tools can cluster recurring corrections by category without NLP. The new section is purely additive — the existing `plan-review-tally` and `code-review-tally` tables are byte-unchanged. New helper `scripts/compose-review-findings.sh` parses the existing finding artifacts (`accepted-plan-findings.md`, the plan-review entries of `rejected-findings.md`, and the code-review entries of `rejected-findings.md`), emits one structured `### <id> — <category>` block per finding with **Phase / Outcome / Reviewer / Category** bullets and a blockquoted verbatim **Prose body** (which preserves the file:line citation and suggested-fix prose authored by the reviewer), and switches to archive-pointer mode when the inline payload exceeds 30 KB by writing `docs/review-archive/issue-<N>.jsonl` (one JSON object per finding) and replacing the inline body with a pointer + count summary. Category derivation is mechanical from the reviewer name (`architecture | correctness | structure | edge-cases | innovation | pragmatism | security | testing | docs | generic | other`). Wiring: `scripts/anchor-section-markers.sh` adds `review-findings-full` to `SECTION_MARKERS` (10 slugs total, in assembly order); `scripts/tracking-issue-write.sh` adds the slug to `COLLAPSE_PRIORITY` at priority position 2 (second-most-ephemeral); `skills/implement/SKILL.md` Step 5 invokes the helper after `/review` returns or the quick-mode review loop completes; `skills/implement/references/anchor-comment-template.md` documents the section, the body-level collapse priority, and the edit-in-sync table. Regression harness `scripts/test-compose-review-findings.sh` covers 8 assertion categories (empty-input placeholder, accepted plan-review parsing, rejected plan-review parsing with synthetic id, rejected code-review parsing with synthetic id, archive switchover at threshold, JSONL shape via python3 round-trip, category derivation, JSON escaping for backslash/quote/newline) and is wired into `make lint` via the `test-compose-review-findings` target on shard 3. Sibling contracts updated in lockstep: `scripts/compose-review-findings.md`, `scripts/test-compose-review-findings.md`, `scripts/anchor-section-markers.{sh,md}`, `scripts/assemble-anchor.md`, `scripts/test-assemble-anchor.{sh,md}`, `scripts/tracking-issue-write.{sh,md}`, plus `skills/research/references/eval-set.md` (the eval-3 baseline question count was already stale at 8 and is updated to 10). Known limitation: accepted code-review findings are not currently captured in this fragment because `/review` and the quick-mode 5.5 loop do not emit a byte-preserved `accepted-code-review-findings.md` artifact today; the helper silently skips that phase / outcome pair, and wiring up the missing artifact is a documented follow-up. Inline → archive threshold (30 KB) and JSONL archive format were resolved during the design phase per the issue's clarification options.

## [15.12.74] - 2026-05-07

### Added

- Resolve #1378: ship three path-scoped `.claude/rules/` files from a Claude-proposed code-reading pass after migration (#1374) and mining (#1375 / #1377) completed. `.claude/rules/timing-task-kind-allowlist.md` couples `--timing-task-kind <kind>` literals across launcher families and skill SKILL.md launch blocks to the canonical `TIMING_TASK_KINDS_ALLOWED` array in `scripts/lib-timing-kinds.sh`, so adding or renaming a kind requires updating the allow-list in the same change (the `(28g)` harness covers literal launcher slugs but warns-and-appends rather than fail-closing on unknown kinds). `.claude/rules/anchor-section-markers-array.md` couples `SECTION_MARKERS` (in `scripts/anchor-section-markers.sh`) and `COLLAPSE_PRIORITY` (in `scripts/tracking-issue-write.sh`) along with the three sourcing scripts and pinned harness fixtures, citing case (i) for the subset invariant and case (i2) as a `timing-report` regression guard (the full converse is not enforced). `.claude/rules/research-readonly-hook-coupling.md` couples `skills/research/SKILL.md`'s frontmatter matcher, `scripts/deny-edit-write.sh`'s canonical-`/tmp` allow predicate, the harness, and SECURITY.md so the advertised read-only-repo posture cannot be silently weakened. Same-PR doc fix: `scripts/tracking-issue-write.md` lines 149 and 181 now refer to canonical `SECTION_MARKERS` instead of a stale section count. Eight rejected candidates listed in the PR description.

## [15.12.73] - 2026-05-07

### Changed

- Resolve #1374: migrate path-scoped invariants from `AGENTS.md` into `.claude/rules/`. Four new rules (`skill-runtime-root-paths.md`, `shell-strict-mode.md`, `topology-generation.md`, `reviewer-archetype-generation.md`) plus extensions to two pilot rules (`script-md-siblings.md`, `skill-editing-trace.md`) and an explicit `paths:` frontmatter on `version-bump-reserved-message.md` — every rule now carries `paths:`. AGENTS.md line 15 is rewritten as a generic glob-discovery instruction (per design DECISION_2 antithesis 2-1, plan-review FINDING_4); the previous hand-maintained enumeration is removed. The three implementer agent prompts (`agents/{codex,cursor,gemini}-implementer.md`) adopt the same generic glob-discovery sentence (per plan-review FINDING_2). Reverse references to migrated bullets are repointed from "per AGENTS.md" to the new rule paths across `agents/` and `scripts/**/*.md` and `skills/**/*.md`. Code-review folded three accepted findings inline: `script-md-siblings.md` `paths:` extended to include `.claude/skills/**/scripts/**/*.{sh,py}` so dev-only skill scripts inherit the sibling-doc invariant; `drift-prone-prose-in-docs.md` citation tightened (the cited rule was too narrow); three sibling stubs flipped from `${CLAUDE_PLUGIN_ROOT}/.claude/rules/...` to repo-relative `.claude/rules/...` for consistency with the rest of the migration.

## [15.12.72] - 2026-05-07

### Added

- Resolve #1377: land three path-scoped `.claude/rules/` files mined from recurring CI failures and the active blocking hook. `.claude/rules/markdown-no-space-in-code-span.md` (paths `["**/*.md"]`) shadows the pre-commit `markdownlint` MD038/MD037/MD001 hygiene class — the largest CI-failure cluster in the mining window (>= 11 distinct PRs across 6 weeks). `.claude/rules/skill-md-description-trigger.md` (paths `["skills/**/SKILL.md", ".claude/skills/**/SKILL.md"]`) shadows `agent-lint S017/desc-no-trigger` so the description-trigger requirement is loaded at SKILL.md edit time without needing to load the full `skills/shared/skill-design-principles.md` rubric. `.claude/rules/no-direct-submodule-edits.md` (paths `["**/*"]`) shadows the `scripts/block-submodule-edit.sh` PreToolUse hook so the agent does not attempt edits the hook would deny at write time. AGENTS.md's existing scale-free `paths:` matching guidance covers the new files automatically; no AGENTS.md edit needed. Mining method, cluster→rule mapping, and rejected-candidate reasoning are recorded on the tracking issue (#1377).

## [15.12.71] - 2026-05-07

### Changed

- Resolve #1384: repoint 9 remaining sibling-contract `.md` stubs from stale `AGENTS.md § Editing rules` / `AGENTS.md "per-script contracts live beside the script"` / `per AGENTS.md` citations to the canonical rule file `.claude/rules/script-md-siblings.md`. Targets enumerated in the issue body plus reviewer-surfaced candidates: `scripts/refresh-anchor.md`, `skills/create-skill/scripts/prepare-description.md`, `skills/simplify-skill/scripts/build-feature-description.md`, `skills/compress-skill/scripts/build-feature-description.md`, `scripts/test-eval-research-baseline-flag.md`, `scripts/test-round-trip-detect.md`, `skills/fix-issue/scripts/test-issue-lifecycle.md`, `scripts/test-prepare-description.md`, `scripts/test-post-scaffold-hints.md`. All targets are dev-only, so all use the repo-relative `.claude/rules/script-md-siblings.md` form per AGENTS.md line 13. Historical CHANGELOG.md entries are out of scope. Documentation-only — no behavior, lint config, or runtime contract changes.

## [15.12.70] - 2026-05-07

### Added

- Per-step timing instrumentation for `/implement` and the skills it nests (`/design`, `/review`), parallel to the existing token-tracking infrastructure. New helpers `scripts/timing-ledger.sh` (13-column TSV writer with `mark` / `record-vendor-task` / `workflow-path` / `dump` subcommands) and `scripts/timing-report.sh` (per-skill duration table + vendor task averages by `(vendor, task-kind)` + HARD/SIMPLE workflow path indicator) mirror `scripts/token-ledger.sh` / `scripts/token-report.sh` operationally. New 9th canonical anchor section `timing-report` (added to `scripts/anchor-section-markers.sh`'s `SECTION_MARKERS`, `tracking-issue-write.sh`'s `COLLAPSE_PRIORITY`, and `skills/implement/references/anchor-comment-template.md`) carries the rendered Timing Report on every tracking issue's anchor comment, replaced idempotently via `<!-- timing-report-begin -->` / `<!-- timing-report-end -->` sentinels. The six external launch wrappers (`launch-review.sh --tool codex`, `launch-review.sh --tool cursor`, `launch-review.sh --tool gemini`, `launch-codex-implement.sh`, `launch-cursor-implement.sh`, `launch-gemini-implement.sh`) emit one vendor timing row per invocation via an EXIT trap; task-kind values are validated against the closed allow-list in `scripts/lib-timing-kinds.sh`. Workflow path is recorded at every `/implement` Step 1 exit branch (HARD = normal `/design` + full `/review` panel; SIMPLE = quick mode or auto-classified simplicity). Path-canonicalization primitives are factored into `scripts/lib-timing-paths.sh` so `timing-ledger.sh` and `timing-report.sh` accept the same containment roots (`${TMPDIR:-/tmp}`, `$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, `$REVIEW_TMPDIR`, `dirname($SESSION_ENV_PATH)`). `LARCH_TIMING_LEDGER` is a new optional `session-env.sh` key emitted by `write-session-env.sh --timing-ledger`. `/design` and `/review` SKILL.md inline `SESSION_ENV_PATH=$SESSION_ENV_PATH` on every `timing-ledger.sh mark` call so nested marks resolve to the parent `/implement`'s `$IMPLEMENT_TMPDIR/timing-ledger.tsv` via priority 4 (`dirname($SESSION_ENV_PATH)/timing-ledger.tsv`) and Step 17's renderer aggregates them with the orchestrator-side marks. Plan-review accepted 18 findings before code; the 11-fix code review round added shared path validation, fail-closed flock fallback (no unlocked-append data corruption), symlink ledger rejection, basename-only output column, end_s-based terse-mode counting, and three new test harnesses (`scripts/test-timing-ledger.sh`, `scripts/test-timing-report.sh`, plus integration coverage in `scripts/test-launch-review.sh`).

## [15.12.69] - 2026-05-07

### Changed

- Resolve #1367: harden Codex / Cursor launcher toolchain along six lines (items A-F from the OOS umbrella) plus eight code-review fixes folded inline.
  - Item A: `scripts/launch-review.sh --tool codex` derives the writable root from `--output`'s parent (`cd $dir && pwd -P`) and passes `--add-dir $CANON_OUTPUT_DIR`, mirroring the #1353 fix on the implementer lane. Round-1 FINDING_1 added `validate_meta_scalar_path --output` before traps/sidecars to match `launch-review.sh --tool cursor`'s contract.
  - Item B: `skills/implement/scripts/step2-implement.sh` propagates the launcher's exit code into a separate `WRAPPER_EXIT=` field so launcher exit-2 validation failures classify as `wrapper-validation-failure` rather than as Codex runtime failures with spurious retries.
  - Item C: dispatcher `$TMPDIR_ARG` and launcher `dirname "$MANIFEST_PATH"` are canonicalized via `cd && pwd -P` before being passed as `--add-dir`, compared as manifest/qa parents, or written into the manifest argv field. Defends against symlinked / non-canonical caller-supplied paths that would EPERM under Codex's canonical-path resolution.
  - Item D (security/architecture cross-cutting): `scripts/agent-model-args.sh` emits one argv token per line on stdout and rejects values containing `[[:cntrl:]]` or whitespace-only / blank model strings before any external CLI sees them. Every consumer (`launch-codex-{review,implement}.sh`, `launch-cursor-{review,implement}.sh`, `launch-gemini-*.sh`, `step2-implement.sh`, `run-negotiation-round.sh`, `check-reviewers.sh`) now reads the line-token stream into a Bash array via mapfile-equivalent and expands quoted with `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}`. The new `scripts/test-agent-model-args.sh` regression harness statically asserts no remaining unquoted `MODEL_ARGS` expansion via `rg` (CI installs ripgrep before `test-harnesses-N`).
  - Item E: `scripts/launch-cursor-implement.sh` adopts the #1350 launcher-owned-sentinel + post-processing parity (`.inner.done` published before `record-vendor`; `.done` published only after post-processing completes). Forward-compat `OUTER_LAUNCHER` / `OUTER_LAUNCHER_PROMPT_FILE` / `OUTER_LAUNCHER_WORKDIR` `.meta` keys are written after a successful inner exit. Per design plan-review FINDING_5 the implementer lane intentionally does NOT reintroduce `--replay-meta` mode or the implement-replay sidecar; the collector's OUTER_LAUNCHER allowlist remains single-entry (`launch-review.sh --tool cursor`) until an implement-side replay caller exists.
  - Item F: `scripts/collect-agent-results.sh` `cmd_json_shape_valid_for_tool` gates the legacy CMD_JSON retry path with per-tool argv-shape allowlists. Cursor argv must include `cursor agent` + `--workspace` and forbid `--add-dir`; Codex must include `codex exec` + `-C` + `--add-dir` (round-1 FINDING_8 added the `--add-dir` requirement to preserve the writable-root contract on tampered `.meta` replay) + `--output-last-message`; Gemini must use a `launch-gemini-*.sh` basename or `gemini` and forbid Codex/Cursor workspace-widening flags. Unknown TOOL values fail closed.
  - Round-1 FINDING_2 + FINDING_9: Codex and Gemini health probes in `scripts/check-reviewers.sh` now apply the same blank/whitespace/`[[:cntrl:]]` rejection rules as production launchers (Codex via `agent-model-args.sh --tool codex` without `--with-effort`; Gemini via inline validation since the launcher uses `-m` directly). Probe argv mirrors production argv so probe failures correlate 1:1 with production failures.
  - Round-1 FINDING_10: skill bash snippets in `skills/research/references/{research,validation}-phase.md` and `skills/shared/{voting,dialectic}-protocol.md` now use a temp-file pattern (`agent-model-args.sh > $tmp || exit $?`) instead of process substitution, so a non-zero exit propagates and aborts the launch instead of silently producing an empty argv array.
  - Updated `SECURITY.md` to document the env-var trust boundary, the per-tool CMD_JSON argv-shape allowlists with unknown-tool fail-closed default, and the OUTER_LAUNCHER single-entry allowlist with forward-compat metadata. Updated `docs/configuration-and-permissions.md` to describe the Codex probe's new model-resolution behavior.
  - Tests: new `scripts/test-launch-review.sh` (Item A coverage), extended `scripts/test-collect-agent-retry.sh` Case P3 to include `--add-dir` per the new Codex shape, extended `skills/implement/scripts/test-cursor-implementer.sh` for Item E sentinel ordering and OUTER_LAUNCHER* meta-key contract.
  - 5 OOS follow-up issues filed by Step 9a.1 (#1389-#1393), all blocked by #1367.

## [15.12.68] - 2026-05-07

### Added

- Resolve #1375: extend `.claude/rules/` with three path-scoped rules mined from the repo's closed-issue history (677 issues scanned). New `.claude/rules/drift-prone-prose-in-docs.md` (paths cover docs/skills/scripts `.md`, README, SECURITY, AGENTS, CLAUDE, `.github/workflows/`) encodes the four drift-prone-prose patterns recurrent across the repo: hardcoded counts, line-number references, machine-local absolute paths, and stale post-refactor prose pointing at renamed entities. New `.claude/rules/external-tool-launcher-parity.md` (paths cover `scripts/launch-{codex,cursor,gemini}-*.sh`, the three implementer agent prompts, the shared collectors `run-external-agent.sh`/`collect-agent-results.sh`, the health probe, the dispatcher, and the cross-doc surface) encodes the parity audit checklist when modifying one of the three external-tool launchers — softened to "shared launcher surfaces" with an intentional-asymmetries callout (Gemini reviewer dormancy in some lanes; review-side JSON normalization and admin-policy snapshots not present implementer-side). New `.claude/rules/launcher-argv-test-coverage.md` (paths cover the launchers and their actual harness locations) makes the harness-update-on-argv-change discipline explicit, with an explicit launcher→harness map (review-side under `scripts/test-launch-*.sh`, implementer-side under `skills/implement/scripts/test-{codex,cursor,gemini}-implementer.sh` plus `test-step2-dispatch.sh`) instead of a single pattern that doesn't apply uniformly. `AGENTS.md` simultaneously replaces its explicit 3-pilot-rule enumeration with scale-free guidance ("consult every `.claude/rules/*.md` whose YAML `paths:` matches files you are about to edit") so future rule additions don't require AGENTS.md edits — itself an instance of the drift-prone-prose pattern the first new rule encodes. `skills/create-skill/scripts/render-skill-md.md` folds an inline doc-drift fix per the OOS triage policy: replaces "in-file header (lines 1–53 of the script)" line-pin with a symbol-anchor reference to the script's banner-through-flag-list block (the new drift rule discourages line-pins). One unrelated OOS observation surfaced by the Codex implementer (test-token-vendor-scrapers harness flake on `launch-cursor-implement.sh` smoke path) is filed as a separate issue. PR description carries a Mining Report (counts, cluster→rule mapping, rejected-candidate reasoning).

## [15.12.67] - 2026-05-07

### Changed

- Resolve #1381: add per-site `> **Continue after child returns.**` blockquotes immediately preceding each `/relevant-checks` Skill-tool invocation in `skills/implement/SKILL.md` (Step 3, Step 5.7 quick-mode after-fixes loop, Step 6 second-pass `FILES_CHANGED=true` branch, Step 10 `evaluate_failure` real-CI-failure case, Step 12c real-CI-failure case). Each callout names the literal next user-facing output (Step 4 commit (impl) breadcrumb / Step 5.8 re-review gate / Step 7 commit (review) flow / Step 10 CI-fix commit-push chain / Step 12c commit-push chain) and distinguishes clean vs non-clean `/relevant-checks` returns to keep the failure path (diagnose, fix, re-invoke) clearly inside the current step rather than reading as a halt. Step 6 also restructured to drop the dangling `If files changed,` predicate split — replaced with an explicit `Else (FILES_CHANGED=true):` branch so the if/else pairing is unambiguous for the orchestrator. Old generic Step 3 callout's meta-coverage parenthetical ("Covers every other `/relevant-checks` invocation in this file ...") removed now that per-site reminders exist at all five sites. New CI-backed text-presence harness `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` (sibling contract `.md`) statically pins the invariant: every `/relevant-checks` invocation site (matched by two awk patterns covering the `Invoke /relevant-checks via the Skill tool` form and the inline `; /relevant-checks; commit via` chain form) MUST have the canonical `> **Continue after child returns.**` opener within the 5 physical lines preceding it; expects exactly 5 sites today. Wired into `Makefile` `test-harnesses-6` shard alongside `test-anti-halt` and excluded from `agent-lint.toml`'s orphaned-file scan via the standard `skills/implement/scripts/test-*.sh` pattern. Mirrors the pinning style of `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh`.

## [15.12.66] - 2026-05-07

### Changed

- Resolve #1372: repoint stale `AGENTS.md § Editing rules` / `Per-script contracts live beside the script` citations at 12 enumerated `file:line` locations to `.claude/rules/script-md-siblings.md` (the new canonical per-script-contract rule from #1352's pilot migration). Public skill prose (`skills/umbrella/SKILL.md`, `skills/design/SKILL.md`, `skills/issue/SKILL.md`, `skills/shared/skill-design-principles.md`) uses `${CLAUDE_PLUGIN_ROOT}/.claude/rules/script-md-siblings.md` so paths resolve against the plugin tree in consumer installs; dev-only contract docs (`agent-lint.toml`, `scripts/repro-claude-p-edit-permissions.md` lines 3 and 139, `scripts/test-harness-shards-coverage.md`, `skills/alias/scripts/generate-alias.md`, `skills/create-skill/scripts/parse-args.md`, `skills/create-skill/scripts/render-skill-md.md` lines 3 and 59) use repo-relative `.claude/rules/script-md-siblings.md` matching AGENTS.md's own convention. Documentation-only PR — no behavior, lint config, or runtime contract changes. Two follow-up OOS issues are filed for remaining same-class stale citations outside this PR's enumerated list.

## [15.12.65] - 2026-05-07

### Added

- Resolve #1369: add a top-level `## Honesty` section to `AGENTS.md` so every agent (Claude session, Codex/Cursor/Gemini implementer, reviewer) loads honesty rules at session start. Six bullets cover: don't fabricate (paths/functions/line numbers/command output/test results), don't overstate completion ("done" means verified done), don't paper over failures, trust-but-verify own claims (confirm tool returned what's claimed before reporting), distinguish observation from inference (mark guesses as guesses), and value honesty over agreeableness (cross-references `KARPATHY_CLAUDE.md` §1 "Think Before Coding" instead of duplicating its push-back guidance). Section is unconditional content at ~9 lines so the per-session token cost stays minimal. Out of scope: enforcement mechanisms (lint rules, hooks, reviewer checks) and per-skill honesty rules.

## [15.12.64] - 2026-05-07

### Added

- Resolve #1352: introduce `larch/.claude/rules/` (Claude Code's modular path-scoped instruction directory) and migrate three pilot rules out of `AGENTS.md` so Claude only loads them when editing the matching paths. New `.claude/rules/script-md-siblings.md` (paths: `scripts/**/*.{sh,py}`, `skills/**/scripts/**/*.{sh,py}`, `skills/shared/*.md`) carries the per-script sibling-contract invariant. New `.claude/rules/skill-editing-trace.md` (paths: `skills/**/SKILL.md`, `skills/**/scripts/**/*.{sh,py}`, `skills/shared/*.md`) carries the "start at SKILL.md, then trace every helper" rule. New `.claude/rules/version-bump-reserved-message.md` is intentionally UNSCOPED (always-on per design plan FINDING_8 — the reserved `Bump version to X.Y.Z` commit subject is a workflow invariant governing commit creation, not a `plugin.json`-edit invariant). New `GEMINI.md` is a one-line `@./AGENTS.md` (13 bytes, Gemini-native @-import; per Round 1 user direction, NOT a symlink). `AGENTS.md` removes the three migrated bullets, adds a single navigation-pointer bullet so Codex/Cursor/Gemini (which do not load Claude Code `.claude/rules/`) can find the rule files, and lists `.claude/rules/` alongside `.claude/skills/` in the Repository-layout supplementary set. `agents/{codex,cursor,gemini}-implementer.md` extend their pre-edit checklist (Style section) to read applicable `.claude/rules/*.md` files when edits touch the matching path scopes. `.pre-commit-config.yaml` adds `\.claude/rules/.*\.md` to the agnix `files:` regex so rules-only commits invoke `agnix --strict` (durable CI coverage replaces the bespoke local YAML check). `larch/.claude/rules/` is dev-only and does NOT ship to consumers (mirrors the existing `.claude/skills/` convention). Token-savings before/after measurement was relaxed by the user during Round 1 design discussion; this PR does not gather that number — operators wanting a number can run a measurement post-merge. The `Cursor / non-Claude-Code` visibility tradeoff is the documented Claude-only scoping the issue explicitly authorized; the AGENTS.md navigation pointer plus the implementer-prompt updates preserve discoverability for external agents.

## [15.12.63] - 2026-05-07

### Fixed

- Resolve #1368: make per-section truncation in `scripts/tracking-issue-write.sh` fence-aware. Observed in issue #1356's anchor comment — `plan-goals-test` got cut mid- ` ```markdown ` fence at the 8000-byte cap, and the unclosed fence swallowed the inserted `[TRUNCATED — …]` marker plus every following section, so on GitHub the diagrams, voting-tally tables, and run-statistics token report rendered as raw code rather than as markdown. Strikingly different from issues #1357/#1358/#1353 worked at the same time which had even fence counts at the cut. Fix: scan the kept prefix line-by-line for column-0 backtick fence delimiters; track the opener's backtick count explicitly; apply the GFM closer rule (closer length ≥ opener length AND closer line is backticks-followed-by-whitespace-only, so a line like ` ```python ` inside an open fence stays content); insert a matching-length closing fence line before the TRUNCATED marker when the cut leaves a fence open. Tilde fences (`~~~`) and indented fences are out of scope — anchor sections are machine-composed by `/implement` and only emit column-0 backtick fences. `scripts/test-tracking-issue-write.sh` adds (d2)/(d3)/(d4) regressions covering 3-backtick mid-fence cut, 4-backtick opener with embedded 3-backtick content, and the GFM closer rule respectively (164 assertions pass). Sibling contracts `scripts/tracking-issue-write.md` and `scripts/test-tracking-issue-write.md` updated.

## [15.12.62] - 2026-05-07

### Fixed

- Resolve #1358: pass `--api-key` explicitly to `cursor agent` at every live call site so explicit env-token auth bypasses the macOS keychain entirely. Eliminates the intermittent `Password not found for account 'cursor-user'` / `Security process exited with code: 45` failure mode that affected 3-of-5 Cursor specialist reviewers per `/implement` round under concurrent keychain probes. New shared sourced library `scripts/lib-cursor-auth.sh` exposes `cursor_auth_argv` (Bash 3.2-safe; populates `CURSOR_AUTH_ARGS=(--api-key "$KEY")` when `CURSOR_API_KEY` is non-empty after whitespace trim, leaves array empty otherwise — preserving today's `cursor login` keychain fallback for users who haven't set the env var; rejects embedded newlines / CR in the trimmed key as paste-corruption guard) and `cursor_auth_preflight` (Darwin-gated read-only sanity check via `security find-generic-password -a cursor-user`; returns 2 with multi-line actionable stderr — caller identity, `docs/installation-and-setup.md` pointer, two remediation options — when `CURSOR_API_KEY` empty AND no `cursor-user` keychain entry on Darwin; no-op on non-empty key OR non-Darwin OR keychain entry present; never spawns `cursor` subprocess, never deletes keychain entries, never performs network I/O; test-mode hooks gated by `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1` only). New `scripts/cursor-auth-flags.sh` emits the conditional argv elements one per physical line so the runtime markdown templates (`skills/shared/voting-protocol.md`, `skills/shared/dialectic-protocol.md`, `skills/research/references/validation-phase.md`) build the same argv via a Bash-3.2-safe `while IFS= read -r line` loop without sourcing the library directly, and runs `cursor_auth_preflight` itself before emitting flags so markdown-template Bash blocks fail consistently with the launchers. Updated launchers/probe/negotiation: `scripts/launch-review.sh --tool cursor` synthesizes `${OUTPUT}.done` + `${OUTPUT}.diag` (`STATUS=FAILED` + `FAILURE_REASON=cursor-auth-preflight: ...`) + stub `${OUTPUT}.meta` on preflight failure so backgrounded callers see actionable failure within seconds rather than `SENTINEL_TIMEOUT` after the full collector timeout; `scripts/launch-cursor-implement.sh` emits the standard KV envelope (`LAUNCHER_EXIT=2 MANIFEST_WRITTEN=false QA_PENDING_WRITTEN=false TRANSCRIPT=... SIDECAR_LOG=...`) with the actionable stderr routed to `$SIDECAR_LOG` so `step2-implement.sh` surfaces a specific failure; `scripts/check-reviewers.sh` Cursor probe gets the same argv but intentionally skips `cursor_auth_preflight` (binary-health check should not fail on missing keychain — production-launcher preflight is the user-facing surface); `scripts/run-negotiation-round.sh` direct-exit-2 on preflight failure (foreground-synchronous; no sentinel collector). `docs/installation-and-setup.md` Cursor section gains a "macOS keychain interaction" subsection covering recommended setup, the `security delete-generic-password -a cursor-user && cursor login` workaround, and the Darwin-only preflight semantic. `SECURITY.md` documents the at-rest argv-visibility tradeoff: the API key appears in process argv (visible to `ps`) and in `.meta` `CMD_JSON` sidecars under the session tmpdir; `CMD_JSON` is intentionally NOT redacted because `scripts/collect-agent-results.sh` reconstructs retry argv from `CMD_JSON` for empty-output retries — redaction would silently break those retries by passing the literal `<redacted>` token to a relaunched Cursor child. Operators requiring zero at-rest persistence can leave `CURSOR_API_KEY` unset and rely on `cursor login` + keychain. New harness `scripts/test-lib-cursor-auth.sh` (17/17 assertions: `cursor_auth_argv` whitespace-trim variants, embedded-newline / CR rejection, `cursor_auth_preflight` decision tree, `LARCH_LIB_CURSOR_AUTH_TEST_MODE` gating, stderr-message anchors, `cursor-auth-flags.sh` line-per-element output and Darwin preflight-fail exit-2 path); wired into `Makefile` shard `test-harnesses-2` alongside `test-launch-review`. `scripts/test-launch-review.sh` gains 5 new assertions (AK1–AK3) pinning `--api-key` adjacency, empty-key absence, preflight-failure sentinel/diag/meta synthesis, and `CMD_JSON` contains the literal key (no redaction); brings the harness to 78 assertions. `skills/implement/scripts/test-cursor-implementer.sh` converts the existing absolute argv-line assertions to insertion-tolerant semantic relative-order checks (the `--api-key` insertion shifted line numbers) and adds 4 new assertions (6b/K1/K2/K3) pinning the same #1358 contracts on the implementer launcher (21/21 assertions). `scripts/test-check-reviewers.sh` adds Cursor probe argv coverage (PATH-stubbed `cursor`, records argv, asserts `--output-format json` + `--api-key` adjacency / absence; pins the existing "MUST track `launch-review.sh --tool cursor`" parity comment as a CI invariant). `agent-lint.toml` excludes the new sourced library and helper script.

## [15.12.61] - 2026-05-07

### Changed

- Resolve #1356: rewrite `/implement` token-spend report (`scripts/token-report.sh`) presentation. Replace the single mixed 8-column table — `Claude input | Cache read | Cache create | Output | Claude total | Vendor total` plus `N/A`-padded vendor rows and `&nbsp;`-indented skill cells — with one Claude table plus one table per vendor sharing a uniform 4-column shape `Step | Skill | Input | Output`. Drops the mixed-rate `Claude total` column whose `input + cache_read + cache_create + output` sum combined dramatically different billing rates (cache_read ~10% of normal input, cache_create ~125%) and produced numbers that did not reflect actual spend; operators who want a single billable proxy can derive `input + cache_read*0.1 + cache_create*1.25 + output` from the ledger themselves. New jq helpers: `md_cell` (escapes `|`, collapses CR/LF on every text cell), `vendor_label` (`codex→Codex / cursor→Cursor / gemini→Gemini`, with the unknown-vendor raw fallback routed through `md_cell` so a hostile vendor name cannot inject heading separators), `vendor_names` (coverage-lossless enumeration in stable order — codex first, cursor second, then any others alphabetically), `claude_table` + `vendor_table` (per-step rows + per-skill detail rows + grand total each), and `slice1` (one-array sibling of `step_slice`). `terse_line` is intentionally unchanged — terse breadcrumb mode keeps cache visibility because a one-line breadcrumb is consumed by humans tailing the chat, not as markdown. Sibling `scripts/token-report.md` Table Shape section rewritten with the breaking presentation contract. `scripts/test-token-report.sh` rewrites assertions for the new shape, derives the expected grand-total count from fixture vendor presence, and adds pipe/newline injection fixtures (mark.step containing `|`, mark.step containing a literal newline, transcript skill containing a literal newline, unknown-vendor heading containing `|` and newline) with anchored oracle checks (35/35 assertions pass). Out of scope: ledger schema (`scripts/token-ledger.sh`) and the transcript-source resolver — purely a presentation-layer change.

## [15.12.60] - 2026-05-07

### Fixed

- Cursor review output pipeline: launcher-owned sentinel + retry post-processing parity (closes #1350; combined from #1345 sentinel race and #1346 retry skips post-processing). Centralizes the sentinel/replay contract in the launcher: `scripts/run-external-agent.sh` accepts an optional `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX` env var (allowlist: exactly `.inner.done`); when set, the EXIT trap writes `${OUTPUT_FILE}.inner.done` instead of `${OUTPUT_FILE}.done`, defaulting to today's behavior for every non-wrapping caller. `scripts/launch-review.sh --tool cursor` exports the env var, validates `--output` and `--timeout` (rejecting both literal `0` and zero-padded `00` / `000` via the arithmetic floor) BEFORE any side effects, persists the un-wrapped prompt to `${OUTPUT}.prompt` for byte-stable retry replay, appends `OUTER_LAUNCHER` / `OUTER_LAUNCHER_PROMPT_FILE` / `OUTER_LAUNCHER_WORKDIR` to `.meta`, clears any stale `${OUTPUT}.json` before the post-run `cp` so a failed copy cannot leak prior-run JSON to `jq` + token-ledger, and atomically renames `${OUTPUT}.inner.done` → `${OUTPUT}.done` only after post-processing finishes. The launcher's EXIT trap reaps a still-live wrapper child before publishing `.done` (avoiding partial-output races) and writes a synthetic `99` matching the wrapper trap default when `.inner.done` is missing. The post-wrapper test seam is strictly gated: `LARCH_ALLOW_TEST_HOOKS=1` (exact match) AND `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` pointing at a regular non-symlink file are both required before the launcher `source`s that file (replaces the prior `eval`-based env channel). `scripts/collect-agent-results.sh` adds an outer-launcher retry branch placed BEFORE the legacy CMD_JSON gates so a Cursor sidecar with valid `OUTER_LAUNCHER*` keys but broken/missing `CMD_JSON` still retries through the launcher; the branch canonicalizes `OUTER_LAUNCHER` to `$SCRIPT_DIR/launch-review.sh --tool cursor`, rejects `..` / `-L` symlinks on the launcher, pins `OUTER_LAUNCHER_PROMPT_FILE` to `${ORIG_OUTPUT}.prompt` as a regular non-symlink readable file, validates `OUTER_LAUNCHER_WORKDIR`, and spawns the retry under `env -u LARCH_ALLOW_TEST_HOOKS -u LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE -u LARCH_TEST_TRAP_AFTER_INNER_DONE -- …` so the launcher's per-invocation test-hook gating cannot be re-armed by env vars inherited from the collector's process. The legacy inner CMD_JSON retry path is unchanged for Codex / Gemini retries and older `.meta` sidecars. New `scripts/test-launch-review.{sh,md}` (73 assertions: sentinel ordering, `.meta` enrichment, `--prompt-file` byte-stable round-trip, gated test-hook positive plus negatives — `LARCH_ALLOW_TEST_HOOKS` not "1", legacy single-env-var name not honored, symlinked hook rejected — wrapper-PID gate on signaled launchers, mutual exclusion of prompt-source flags, validate-before-side-effects for unsafe `--output` / non-positive / zero-padded `--timeout`, stale-`.json` cleanup) wired into `Makefile` `test-harnesses-2` shard, `docs/linting.md`, and `agent-lint.toml` G004/dead-script exclude list. `scripts/test-run-external-agent.sh` adds 4 cases for inner-sentinel mode (default, inner mode, stale-cleanup, allowlist rejection); `scripts/test-collect-agent-retry.sh` adds 8 cases (Q-X) plus Case Z verifying the env-strip prevents test-hook smuggle into retries. Sibling `.md` contracts and `SECURITY.md` updated in lockstep.

## [15.12.59] - 2026-05-07

### Fixed

- Codex implementer launcher (`scripts/launch-codex-implement.sh`) now grants Codex write access to the dispatcher-owned session tmpdir via `codex exec --add-dir "$(dirname "$MANIFEST_PATH")"`, so the manifest and qa-pending JSON can be atomically written without hitting `Operation not permitted` (closes #1353). The launcher derives `SESSION_TMPDIR` from `--manifest-path`, asserts `--manifest-path` and `--qa-pending-path` share a parent (string equality), and fails fast with `exit 2` when the directory does not exist. Argv ordering is preserved: `exec / --full-auto / -C / --add-dir / model flags / --output-last-message`. Cursor and Gemini implementer launchers are unchanged — `--trust` and `--approval-mode yolo --skip-trust` already permit absolute writes outside the workspace; their sibling `.md` contracts now record the rationale. `SECURITY.md` documents the widened Codex writable surface; `docs/linting.md` updates the harness contract row to mention `--add-dir`, the new parent-mismatch / missing-dir coverage, and the `test-harnesses-3` shard. `skills/implement/scripts/test-codex-implementer.sh` adds Test 11 (parent-mismatch → exit 2), Test 12 (missing-session-tmpdir → exit 2), and an argv-position assertion that `--add-dir <manifest-parent>` is emitted immediately after `-C "$REPO_ROOT"`. The Codex health probe in `scripts/check-reviewers.sh` now mirrors the implementer launcher by passing `--add-dir "$PROBE_DIR"`, so a Codex build that rejects the new flag fails the probe rather than passing healthy and failing later at `/implement` Step 2 spawn with worse diagnostics; `scripts/check-reviewers.md` Tool registry section records the probe-mirrors-launcher invariant.

## [15.12.58] - 2026-05-07

### Fixed

- Resolve #1357: replace the four layered prompt-text anti-halt reminders at the post-/design boundary in `/implement` Step 1 normal mode with a mechanical wrapper script `skills/implement/scripts/post-design-boundary.sh`. The wrapper delegates manifest validation to `read-design-manifest.sh --emit-load-breadcrumb`, performs Cross-Skill Health Propagation (monotonic flip), captures `BRANCH=` via `git-current-branch.sh` with retry-and-fail-closed, and emits a single coherent envelope ending with an imperative `➡️` continuation directive. SKILL.md Step 1 now invokes the wrapper as the FIRST mandatory post-`/design` action, replaces the Cross-Skill Health Update body with a pointer, parses `BRANCH=` from the wrapper instead of re-running the helper, and adds a post-/design legal next-actions matrix patterned after the Step 2 entry preconditions matrix. The wrapper buffers the reader's success block until every hard gate (manifest read + session-env validation + branch capture) passes — a late branch-capture failure now emits only the failure envelope, not a contradictory dual envelope of `MANIFEST_OK=true` plus a trailing `MANIFEST_FAILED=true`. New skill-local harness `skills/implement/scripts/test-post-design-boundary.sh` (success, missing manifest, invalid tmpdir, anchored parse, stale-health × 4 variants, branch-capture × 2 variants, design-only imperative variant, path-injection × 2, session-env validation × 2). Repo-root harness `scripts/test-implement-post-design-boundary.sh` extended with assertions K (wrapper exists), L (SKILL invokes it), M (no direct `read-design-manifest.sh --emit-load-breadcrumb` from the post-/design slice), N (matrix present in SKILL), F-prime (replaces retired F).

## [15.12.57] - 2026-05-06

### Added

- Five test-harness gaps from #1351 closed: `scripts/test-token-ledger.sh` now exercises the `--ledger PATH` "anywhere in argv" pre-pass (after-subcommand, tail, last-wins precedence — previously regressions to position-sensitive parsing went uncaught); `scripts/test-token-report.sh` covers the malformed-JSONL and no-step-marks paths that surface as `Token report unavailable: failed to parse token sources`; `scripts/test-token-vendor-scrapers.sh` smokes `launch-cursor-implement.sh` (`raw=cursor_implement total=10`) and `launch-codex-implement.sh` (`raw=codex_implement total=7777`); `skills/implement/scripts/test-{cursor,codex}-implementer.sh` add per-launcher `record-vendor` fixtures asserting the produced JSONL row carries the expected `vendor=` / `raw=` / per-counter / total values. New `scripts/test-token-claude-source.sh` (15 assertions, sibling `.md` contract, wired into `Makefile` `test-harnesses-4` and `agent-lint.toml`) covers the `LARCH_CLAUDE_SOURCE_FILE` snapshot replay short-circuit, snapshot fall-through (stale TRANSCRIPT_PATH, garbage env-file, missing env-file), the live mtime resolver, `LARCH_CLAUDE_SESSION_ID` override, malformed session-id rejection, empty project dir failure, and concurrent-session pinning (snapshot wins over a newer transcript in the project dir). Test transcripts deliberately use names whose lexical order contradicts mtime order so a buggy lexical-order resolver cannot satisfy the assertions. `scripts/token-claude-source.md` Test Harness section now points to the dedicated harness as the primary coverage source. `docs/linting.md` lists the new `make test-token-claude-source` target alongside its siblings.

## [15.12.56] - 2026-05-06

### Fixed

- `scripts/lib-gemini-tool-drift.sh` `write_style_uncovered` loop now normalizes the raw catalog tool name through `normalize_gemini_tools_from_raw` before the deny-list `gemini_tool_list_contains` check, mirroring the `warning_unknowns` pattern. Prior code compared a raw catalog name (e.g. `WRITE_FILE`, `write_File`) against a deny-list of strict snake_case policy keys (`write_file`), so semantically-equivalent casing variants were flagged as uncovered and forced `GEMINI_HEALTHY=false`. Names that fail strict normalization (`write-file`, `file.write`, `fileWrite` whose normalized form is not in the deny list) still flag as uncovered, preserving prior behavior. Closes #1348.

## [15.12.55] - 2026-05-06

### Added

- Token-spend reporting PoC for `/implement` (closes #1324). Adds three reusable scripts under `scripts/`: `token-ledger.sh` (subcommands `mark <step>` / `record-vendor <vendor> [key=value …]` / `dump`, JSONL ledger at `${TMPDIR}/larch-tokens-<sha256(session-id)>.jsonl`, observability-only `exit 0` contract), `token-report.sh` (`--since-last-mark --terse` for per-step lines and `--full --markdown [--output FILE | --append-run-statistics FILE]` for end-of-run tables, with `RENDER_FAIL_REASON` propagation so `unavailable()` can never corrupt captured output via command substitution), and `token-claude-source.sh` (resolves the live Claude transcript path with `LARCH_CLAUDE_SOURCE_FILE` snapshot short-circuit, `LARCH_CLAUDE_SESSION_ID`/`LARCH_TOKEN_SESSION_ID` env-var precedence under a `[A-Za-z0-9_-]{1,128}` charset allowlist, and newest-by-mtime fallback). Each `.sh` has a sibling `.md` per AGENTS.md per-script-contract rule, including a "Relationship to scripts/token-tally.md" section explaining that the existing `/research` token tally remains untouched.
- Vendor token capture in launchers: `scripts/launch-codex-{implement,review}.sh` scrape the trailing `tokens used\n<N>` block from sidecar stderr; `scripts/launch-cursor-{implement,review}.sh` add `--output-format json`, parse `.usage.{inputTokens,outputTokens,cacheReadTokens,cacheWriteTokens}` from the JSON sidecar, and (review only) extract `.result` back into `$OUTPUT` via `cp` + `jq` to a temp file + atomic rename, so `$OUTPUT` always contains usable bytes for downstream collectors even when `jq` is missing or extraction fails. All four launchers call `token-ledger.sh record-vendor` with the parsed counters.
- `skills/implement/SKILL.md` integration: per-numbered-step `# token-mark Step <N> — <name>` and `# token-step-end Step <N>` instrumentation across 23 numbered steps with paired `token-ledger.sh mark` (entry) and `token-report.sh --since-last-mark --terse` (exit) calls; structural pairing pinned by `scripts/test-implement-structure.sh` (assertion 27). Step 0 also exports `LARCH_TOKEN_SESSION_ID` from `$IMPLEMENT_TMPDIR/session-id` and snapshots the resolved Claude transcript path into `$IMPLEMENT_TMPDIR/claude-source.env` (exporting `LARCH_CLAUDE_SOURCE_FILE`) BEFORE later concurrent Claude sessions can race the resolver. Step 18 performs the authoritative final `token-report.sh --append-run-statistics $IMPLEMENT_TMPDIR/anchor-sections/run-statistics.md` plus an anchor refresh, so the published Token Report covers Steps 12, 14-18 (which Step 11 misses).
- New regression harnesses: `scripts/test-token-ledger.sh` (10 assertions covering `mark`/`record-vendor`/`dump` round-trip, sha-derived ledger filename, `--ledger PATH` containment under `${TMPDIR}`, JSON-safe field escaping for `raw=` content with embedded quotes/newlines, session-id traversal-attempt rejection, and `chmod 600` on ledger files), `scripts/test-token-report.sh` (13 assertions covering `--since-last-mark --terse` rendering, `--full --markdown` table shape with sub-skill indentation, `--append-run-statistics` idempotent rewrite between `<!-- token-report-begin -->` / `<!-- token-report-end -->` sentinels, and graceful `Token report unavailable: <reason>` failure modes), and `scripts/test-token-vendor-scrapers.sh` (7 assertions covering Codex sidecar awk extraction with multiple `tokens used` blocks asserting LAST-wins, Cursor `.usage` jq extraction with non-numeric value rejection, and stub-cursor smoke through `launch-review.sh --tool cursor`). All three wired into `Makefile` `test-harnesses-4` and `agent-lint.toml`.

### Changed

- `scripts/check-reviewers.sh` Cursor health probe argv now matches production `scripts/launch-review.sh --tool cursor` (`--capture-stdout-only` + `--output-format json`); `evaluate_probe` parses Cursor's `.result` / `.error` JSON fields with a plain-text fallback when jq is missing or the body is not valid JSON. Closes the probe-vs-production drift surfaced by the round 1 review panel as FINDING_7.

### Changed

- `/implement` Step 5 quick-mode review loop and `/review` Step 3f now stop after the just-fixed round when its accepted findings are non-substantial — defined as no medium-to-high severity bug, applied fixes small in size (~30 LOC convention), AND accepted-fix count `< 5`. Any one of those failing keeps today's loop-back behavior. The 7-round safety cap remains the upper bound. Anti-halt notes, Step 3 round-state machine table, and the Step 5 quick-mode breadcrumb all updated to reflect the new convergence path. Pure SKILL.md prompt change; no script or topology changes.

## [15.12.53] - 2026-05-06

### Changed

- `scripts/session-setup.sh` now creates session tmpdirs under `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/<prefix>-<clone-tag>-XXXXXX` (with a `/tmp` fallback when the cache root is unwritable), writes `$SESSION_TMPDIR/.larch-keepalive` (PID/PPID/CLONE_PATH/SESSION_ID/PREFIX/CREATED + ext-cleaners-please-skip note), and emits `SESSION_ID=<value>` on stdout. `scripts/write-session-id.sh` is now idempotent — if the target file already has content (from session-setup.sh) it returns 0 without rewriting.
- Path validators in `scripts/cleanup-tmpdir.sh`, `scripts/implement-finalize.sh` `is_tmp_path`, and `scripts/token-tally.sh` `validate_dir` accept the new cache-sessions root in addition to `/tmp/` and `/private/tmp/`.
- New regression harnesses (38 assertions): `scripts/test-redact-tmpdir-paths.sh`, `scripts/test-keepalive-sentinel.sh`, `scripts/test-cache-root-validation.sh`, `scripts/test-finalize-sanity-check.sh`. Wired through `make` targets and `test-harnesses-6`.

## [15.12.52] - 2026-05-06

### Fixed

- `scripts/session-setup.sh` `.health` sidecar write block defaults `CODEX_HEALTHY` / `CURSOR_HEALTHY` / `GEMINI_HEALTHY` to `false` (fail-closed) instead of `true` when `FINAL_*_HEALTHY` is empty (e.g., a future refactor drops the key from `check-reviewers.sh` probe output, or a passthrough caller-env omits the key). Backstops the #1317 infra-error fail-closed contract at the sidecar-write layer so an unhealthy session cannot be silently re-masked as healthy. New regression harness `scripts/test-session-setup-health-defaults.sh` (12 assertions across empty caller-env, `--check-gemini-reviewer`, explicit-true, and explicit-false scenarios) wired through `make test-session-setup-health-defaults` and `test-harnesses-6`. Header comment in `scripts/session-setup.sh` and contract in `scripts/session-setup.md` updated to note that `--check-gemini-reviewer` also gates `GEMINI_HEALTHY` emission in the sidecar on the passthrough path. `scripts/check-reviewers.md` Compatibility-audit paragraph rewritten to reflect the new fail-closed default. (closes #1336)

## [15.12.51] - 2026-05-06

### Changed

- Session tmpdirs created via `scripts/session-setup.sh` and the `/issue` skill now embed a sanitized cwd-basename "clone tag" between the prefix and the random suffix (`/tmp/claude-implement-larch1-xYt7WL`), so concurrent runs from independent clones are distinguishable in `/tmp` while keeping `mktemp`'s random suffix.
- `scripts/cleanup-tmpdir.sh` now appends a best-effort audit line (UTC timestamp, pid, ppid, parent command, removed dir) to `${TMPDIR:-/tmp}/larch-cleanup-audit.log` before each `rm -rf`, so future surgical-wipe incidents can be traced to their caller. The audit file inherits the operator's umask (no explicit chmod) to avoid widening readability on shared / multi-user hosts.
- New regression harness `scripts/test-cleanup-tmpdir.sh` covers the audit-log line shape under a private `TMPDIR` override; wired through `make test-cleanup-tmpdir` and `test-harnesses-6`.

## [15.12.50] - 2026-05-06

### Fixed

- `scripts/check-reviewers.sh` infra-error path emits `*_HEALTHY=false` (fail-closed) instead of `*_HEALTHY=true`, so consumers gate downstream work correctly when the wait-for-reviewers infrastructure aborts. The `WAIT_INFRA_ERROR=` line still carries the orthogonal diagnostic. Side fix: drop `tr '=' ' '` so `=` characters in the diagnostic value survive end-to-end through `session-setup.sh`'s line-then-`key=value` parser. (closes #1300, OOS sub-issue A of #1317)
- `scripts/lib-gemini-tool-drift.sh` raw-discovery / strict-normalization split: `discover_gemini_tools_raw` preserves case + separators for unknown-tool warnings and write-style classification; `normalize_gemini_tools_from_raw` keeps the snake_case set-comparison stream. New `gemini_tool_tokenize_for_write_style` splits camelCase before separators before lowercase, then `gemini_tool_is_write_style` matches anchored tokens (substring forbidden). `gemini_tool_list_contains` uses `grep -F` literal matching so dot-separator tool names (`write.file`) cannot false-match snake_case deny-list entries (`write_file`). `write_gemini_drift_artifact`'s `status=` line now drives off the raw `warning_unknowns` set so hyphenated/dotted non-write-style tools no longer yield contradictory artifact + stderr signals. (closes #1299, OOS sub-issue B of #1317)
- `skills/fix-issue/scripts/issue-lifecycle.sh` `_run_false_positive_marker` switches from `cat` fallback to buffer-then-cat for redactor output, with three explicit branches: redactor exit 0 + non-empty buffer → emit redacted bytes; exit 0 + empty buffer → emit `INFO: mark-false-positive stderr fully redacted (...)` (clean redaction signal); failure / missing redactor → emit `WARNING: mark-false-positive stderr suppressed: redactor exit=<code> (<bytes> bytes discarded)`. New `LARCH_TEST_REDACTOR_PATH` test seam exercises all three branches via fixtures 15b/c/d. SECURITY.md updated to document the 3-outcome contract. (closes #1298, OOS sub-issue C of #1317)
- `.claude/skills/analyze-issues/scripts/analyze.py` `load_issues` detects duplicate parsed `number` values and skips later occurrences (first-occurrence wins), counting toward the existing 5% `LOAD_ISSUES_SKIP_THRESHOLD` and `--lenient` flag. Prevents silent dict-key collisions in `categorize` / `category_breakdown` / `growth_chart` when `"007"` and `7` parse to the same int. (closes #1297, OOS sub-issue D of #1317)

## [15.12.49] - 2026-05-06

### Changed

- Add consumer-facing `STATUS=OK` guidance to `docs/external-reviewers.md` clarifying that the success signal is `STATUS=OK` paired with empty `FAILURE_REASON`, not `EXIT_CODE` alone — `EXIT_CODE=0` can still appear on retry-failure rows when the retry sentinel was `0` but the retry output stayed empty (`STATUS=EMPTY_OUTPUT`). Cross-link to `scripts/collect-agent-results.md` for the full retry-row exit-code semantics.
- Redesign the `MAX_RETRY_TIMEOUT` floor in `scripts/collect-agent-results.sh` to derive from queued retries: seed at 30s (small safety floor) instead of a fixed 180s and let the existing per-slot loop raise it to `max(ORIG_TIMEOUT+60)` over queued reviewers. Production retry waits now scale with reviewer timeouts so short reviewers no longer pay a fixed 180s floor. Updates the contract doc `scripts/collect-agent-results.md` and the harness contract `scripts/test-collect-agent-retry.md` (Case K) to describe the new formula.

## [15.12.48] - 2026-05-06

### Changed

- Fold the installed-version listing into `skills/upgrade-larch/scripts/upgrade-larch.sh` so `/upgrade-larch` makes a single Bash invocation instead of two. The script now prints `Installed larch plugin version:` followed by the `claude plugin list | grep -A2 'larch@larch-local'` block (best-effort with `|| true` so listing failures do not turn a successful install into a failed upgrade). Updates `skills/upgrade-larch/SKILL.md`, `skills/upgrade-larch/scripts/upgrade-larch.md`, and `docs/installation-and-setup.md` to describe the version-listing block as best-effort confirmation rather than a gate on the restart instruction.

## [15.12.47] - 2026-05-06

### Changed

- Eliminate Gemini reviewer call sites from `/implement` (Step 5 quick-mode rounds 1-3 generic-additive slot and rounds 4+ chain) and `/review` (optional Gemini generic slot in diff and description modes; rounds 4-7 chain). Updates `skills/implement/SKILL.md`, `skills/review/SKILL.md`, the structural test harnesses (`scripts/test-implement-structure.sh`, `scripts/test-review-structure.sh`, `scripts/test-quick-mode-docs-sync.sh`) and their sibling contracts, the public docs (`README.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, `docs/review-agents.md`, `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `SECURITY.md`), and `skills/shared/external-reviewers.md` to describe the new no-Gemini-reviewer review-panel topology and to document the Gemini reviewer machinery as dormant.
- Allowlist `scripts/launch-review.sh --tool gemini` in `agent-lint.toml`'s G004/dead-script exclude list so the launcher remains in-tree as machinery for future re-enablement without failing the dead-script lint.
- Preserve all Gemini machinery: `scripts/launch-review.sh --tool gemini`, `scripts/launch-gemini-implement.sh`, `agents/gemini-implementer.md`, the dispatcher `coder=gemini` path in `skills/implement/scripts/step2-implement.sh`, the `--coder=gemini` flag and its docs, the dispatcher Gemini bail-reason enum tokens (`gemini-runtime-failure`, `gemini-bailed-no-reason`, `gemini-modified-history`), the `--check-gemini-reviewer` opt-in flag in `scripts/session-setup.sh` (still consumed by `--coder=gemini` dispatch and cross-skill `GEMINI_HEALTHY` propagation), and the Gemini health probe in `scripts/check-reviewers.sh`. Reviewer call sites were the only thing removed; the dispatcher implementer path remains active.
- Negative test pins in `scripts/test-implement-structure.sh` (assertion 23j) and `scripts/test-review-structure.sh` (assertions 19b/19c) guard against re-introducing `launch-review.sh --tool gemini` invocations or `gemini-output.txt` collector argv in the two skills without an intentional reversal.

## [15.12.46] - 2026-05-06

### Changed

- Align collector retry fail-closed signaling and sentinel validation: `mark_retry_metadata_invalid` now emits `EXIT_CODE=99` instead of `EXIT_CODE=0`, matching the missing-retry-sentinel branch, while preserving the documented retry-zero/empty-output failure row where `STATUS=EMPTY_OUTPUT` can still carry `EXIT_CODE=0`. Consumers that fingerprinted on `EXIT_CODE=0|STATUS=EMPTY_OUTPUT` must switch to `STATUS` plus `FAILURE_REASON`; `skills/shared/external-reviewers.md` now calls out that `STATUS=OK` with empty `FAILURE_REASON` is the success signal. The collector validates `.done` sentinel content with `^[0-9]{1,3}$` plus `<=255` before interpolating into structured output, coercing malformed bytes to `99` with stderr diagnostics to protect the pipe-delimited `RESULTS` invariant. The missing-retry-sentinel row construction is exposed through `build_missing_retry_sentinel_result` for direct regression coverage. Coerced-99 with empty output and a valid `.meta` now routes to the empty-output retry path rather than `STATUS=FAILED`, so a corrupt or partially-written initial `.done` no longer denies the one-shot retry recovery the path was designed for; real (non-coerced) non-zero exits with empty output still route to `FAILED`. Closes #1315.

## [15.12.45] - 2026-05-06

### Changed

- Keep linting documentation aligned with the six-shard harness partition.
- Document the research planner harness under its actual shard prerequisite (`test-harnesses-2`). Closes #1322.

## [15.12.44] - 2026-05-06

### Changed

- Tighten `/implement`'s OOS-issue filing algorithm to drive per-work-item OOS-issue rate well below 1 (the prior 1:1 rate paralyzed progress because every fix surfaced ~1 new OOS issue). Adds a new `### OOS triage policy` subsection to `skills/implement/SKILL.md` with four rules: (1) documentation drift folds inline regardless of size; (2) bugs < ~30 LOC fold inline; (3) multiple medium-bug-class entries (≥ ~30 LOC each) combine into ONE filed OOS issue; (4) multiple moderate-doc-class entries (~30-100 lines each, NOT drift) combine into ONE filed OOS issue. Rule 1 takes precedence over rule 4 when both could apply. Rules apply at controlled acceptance points (main-agent `Pre-existing Code Issues` dual-write and Step 5 quick-mode 5.5 OOS evaluation); Step 9a.1 external-implementer manifest harvest applies only rules 3-4 plus the security carve-out because folding inline is no longer mechanically possible at that step (propagating rules 1-2 upstream into implementer-agent prompts is documented as follow-up). `/design` and `/review` voting acceptance writers (`oos-accepted-design.md` / `oos-accepted-review.md`) are also documented as follow-up retrofit work. Rewrites the dual-write subsection so logging to `execution-issues.md` stays unconditional but the OOS-artifact append is conditional on triage. Step 5.5 documents the security carve-out (highest precedence), the rules-1/2 fold-inline branch with a `Warnings` log requirement, and the filed-OOS-candidate branch (NOT filtered by rules 1-2). Step 5.6 explicitly counts triaged-inline findings as accepted-for-fix. Extends `skills/implement/references/anchor-comment-template.md` step 3.4 with belt-and-suspenders combine criteria 5 and 6 (medium-bug class combine; moderate-doc class combine) that override the "do NOT combine genuinely independent entries" carve-out. Closes #1314.

## [15.12.43] - 2026-05-06

### Changed

- Bring linting docs and agent-lint allow-list comments back in sync with current merge and bump harness coverage (`docs/linting.md`'s `make test-merge-pr` row now mentions PATH-stubbed `gh` and `git` plus the same-version gate cases — `version_already_published`, no-op merge fallthrough, fail-closed stale/unsafe inputs — and corrects the shard prerequisite to `test-harnesses-4`; a new `make test-apply-bump` row enumerates the success / fetch-failure-rollback / same-version-rollback / differing-origin / malformed-origin / commit-failure / dirty-worktree paths under `test-harnesses-2`; `agent-lint.toml`'s `scripts/test-merge-pr.sh` exclude comment is refreshed in lockstep).
- Clarify the re-bump merge invariant in `skills/implement/references/rebase-rebump-subprocedure.md` so local safety probes are distinguished from the remote merge operation: `merge-pr.sh` reads local git state for its HEAD-OID precondition, branch-range bump-subject scan, `origin/main` refresh, and origin `plugin.json` same-version gate, while `ci-wait.sh` and the final `gh pr merge` operation still act on the remote PR/branch state. Unpushed local commits remain invisible to the merge itself.
- Align `skills/research/scripts/run-research-planner.md` Step 1.1.b/1.1.c bullets with today's `/research` topology: the planner pre-pass runs unconditionally on every `/research` invocation (no `--plan` flag exists), and the operator re-validation checkpoint is described as TTY-context-only without the stale "interactive pause runs" wording. Closes #1316.

## [15.12.42] - 2026-05-06

### Changed

- Inject the larch plugin version into the `/implement` tracking issue's anchor comment under the existing `run-statistics` section, captured once per assembly via a new `scripts/read-plugin-version.sh` helper that reads `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` and falls back to `unknown` on any failure. `scripts/assemble-anchor.sh` now special-cases the `run-statistics` slug: it emits a self-contained minimal table on the seed (`## Run Statistics` + `| Metric | Value |` header + `| larch plugin version | <X.Y.Z> |`), and on populated fragments it strips trailing blank lines AND any pre-existing trailing `| larch plugin version | … |` rows before appending a freshly-captured row — keeping the assembler idempotent across hydration / resume so duplicate version rows never accumulate. When stripping leaves the interior empty (e.g. a fragment that contained only a stale version row), the helper falls through to the seed-style scaffold so the assembled section is always a well-formed table. Sibling contract `scripts/assemble-anchor.md` and the canonical `skills/implement/references/anchor-comment-template.md` template document the auto-injected row, the version-row injection rules, and the resume-idempotency contract. Regression harness `scripts/test-assemble-anchor.sh` adds three new assertion blocks — `(b4)` populated-fragment append, `(b5)` hydrated-stale-row dedup, `(b6)` empty-after-normalization scaffold fallback — plus `(a6)` for the missing-`CLAUDE_PLUGIN_ROOT` `unknown` fallback path; the harness now covers 18 categories.

## [15.12.41] - 2026-05-06

### Changed

- Prevent stale version-bump branches from publishing a duplicate plugin version after `origin/main` has already advanced. `scripts/merge-pr.sh` adds a pre-merge gate that verifies `git rev-parse HEAD == gh pr view --json headRefOid`, scans `origin/main..HEAD` for the canonical `Bump version to X.Y.Z` subject (so post-bump `Fix CI failure` commits do not bypass the gate), and compares against `origin/main:.claude-plugin/plugin.json`'s strict-semver-validated `.version`; same-version matches emit the new `MERGE_RESULT=version_already_published`, ancestry mismatches emit `MERGE_RESULT=main_advanced`, and any unparseable origin version fails closed with `MERGE_RESULT=error`. `.claude/skills/bump-version/scripts/apply-bump.sh` adds a parallel pre-commit probe with explicit rollback (restore `plugin.json` from backup, `git reset HEAD`) on fetch failure, parse failure, or same-version race. `skills/implement/SKILL.md` Step 12b learns the new `version_already_published` terminal state, Step 12d's bail list is broadened to cover all `merge-pr.sh` mechanical bails (`policy_denied` / `admin_failed` / `error` / `version_already_published`), and Step 8 routes the new `apply-bump.sh` abort through the Rebase + Re-bump Sub-procedure with `caller_kind=step8_apply_bump_same_version` for one re-classification attempt before stalling. Make release creation tolerant of concurrent workflow runs that race to create the same GitHub release: `.github/workflows/release-tag.yaml`'s "Create GitHub Release" step wraps `gh release create` so a non-zero exit followed by a successful `gh release view "$TAG"` is treated as success ("Release $TAG was created by a concurrent run — skipping."); the optional `concurrency: { group: release-tag, cancel-in-progress: false }` block was deliberately rejected because Actions concurrency cancels pending intermediate items and would drop a release. Add offline regression coverage for merge-time gates and bump rollback paths: `scripts/test-merge-pr.sh` is extended with stubbed `git` (fail-closed unknown subcommand), 11 new same-version / branch-range / ancestry / fetch-failure / OID-mismatch / parse-failure cases, and a new sibling harness `scripts/test-apply-bump.sh` covers the success / fetch-failure-rollback / same-version-rollback / differing-origin / malformed-origin / commit-failure paths. Closes #1288.

## [15.12.40] - 2026-05-06

### Changed

- Rebalance CI test-harness shards to ~20s each (closes #1294). Three slow harnesses paid hardcoded sleeps that the existing fake-clock pattern had not yet reached; one non-sleep harness was hot-looping awk forks inside its union-find. Speedups (production defaults preserved): `test-collect-agent-retry` exports `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05` (27s → 2.5s); `validate-citations.sh` reads `__VC_BUDGET_POLL_INTERVAL` (default `1`) for its budget-bounded child-PID poll loop, and `test-validate-citations.sh` overrides it to `0.05` (15s → 3.8s); `lib-gemini-tool-drift.sh` reads `LARCH_GEMINI_TOOL_DISCOVERY_TIMEOUT` (default `5`) for the slash-command discovery watchdog, and `test-check-reviewers.sh` overrides it to `1` (41s → 14s); `skills/implement/scripts/oos-file-conflict-deps.sh` replaces its file-backed union-find parent array with an in-memory bash array (~5500 awk forks eliminated; 26s → 15s). All three poll-interval validators now reject padded-zero forms (`00`, `000`, `00.0`).
- Reshard `Makefile` `test-harnesses-N` from 5 to 6 cells via LPT bin-packing, with `.github/workflows/ci.yaml` matrix updated in lockstep. `scripts/test-harness-shards-coverage.sh` is now shard-count-agnostic — `extract_shard_prereqs` discovers `test-harnesses-N` rules from the Makefile, and the continuation-line regex matches any numeric shard. Self-test fixture (still 5 shards) keeps working unchanged. `docs/linting.md` documents the new shard count, refreshed rebalance procedure, and updated branch-protection migration list (now includes `test-harnesses (6)`).

## [15.12.39] - 2026-05-05

### Fixed

- `scripts/collect-agent-results.sh` now propagates the retry `.done` sentinel value as `EXIT_CODE=<RETRY_EXIT>` on the retry-failed branch (previously masked as `EXIT_CODE=0`) and emits `EXIT_CODE=99` when the retry sentinel is missing entirely (matching the cat-fallback default at `:308-309`). Consumers that mix process exit, sentinel `.done`, and collector `EXIT_CODE` no longer see divergent signals. The retry success branch is unchanged. Sibling contract `scripts/collect-agent-results.md` documents the new propagation rule and the `EXIT_CODE=0|STATUS=EMPTY_OUTPUT` sub-case (retry sentinel is `0` but retry output stayed empty — a failure row, not a success). Regression harness `scripts/test-collect-agent-retry.sh` adds Case I (non-zero retry exit, asserts `EXIT_CODE=<RETRY_EXIT>` and `FAILURE_REASON` end-to-end) and Case J (zero retry exit + empty output, pins `EXIT_CODE=0|STATUS=EMPTY_OUTPUT|HEALTHY=false`). Closes #1290.

## [15.12.38] - 2026-05-06

### Changed

- Harden `scripts/launch-review.sh --tool gemini` against shell-redirect bypass of the `gemini-reviewer-policy.toml` write-deny: the launcher now snapshots the working tree (HEAD SHA, sha256 of tracked + untracked files, and `git diff --cached` index state) before launching Gemini and again after JSON normalization, reverts any reviewer mutation via `git checkout HEAD -- <path>` / `git reset HEAD -- <path>` / `rm -f`, fails loud with `SNAPSHOT_GUARD_TRIGGERED:` (or `UNRECOVERABLE_DELTA:`) and exit code `1` (or `99` on guard infrastructure failure), and clears `$OUTPUT` so non-zero `.done` always implies empty `$OUTPUT`. The launcher also prepends a fixed hardening preamble to the caller-provided prompt forbidding shell writes, mutating commands, and index/ref mutation. `LARCH_GEMINI_SNAPSHOT_TIMEOUT` is validated as a positive base-10 integer (rejects `0`, `00`, `000`; treats `010` as 10s, not octal). Snapshot temp resources are removed by an `EXIT` trap. The launcher's regression harness `scripts/test-launch-review.sh` is extended with mutation-detection cases (new untracked, modified-tracked, deleted-tracked, index-only `git add` against worktree-modified file), `.done` parity assertions on every guard-failure branch, `$OUTPUT`-cleared assertions, and a non-git fail-open case. Sibling contract `scripts/launch-review.md` documents exit code `99` and the snapshot-guard semantics; `scripts/test-launch-review.md` documents the new test coverage. Closes #1280.

## [15.12.37] - 2026-05-06

### Fixed

- `/relevant-checks` no longer prints the misleading "all changes are deletions" message in `.claude/skills/relevant-checks/scripts/run-checks.sh` when `MODIFIED_FILES` consists only of paths rejected by the `[ -f ]` regular-file filter (deletions, directories, or other non-regular paths). The empty-`files[]` branch now prints `No existing regular files to pass to pre-commit.`, the zero-phase `ERROR:` line says `(no changes, or no regular files for pre-commit)`, and the surrounding comment block + `[ -f ]` filter-comment + `.claude/skills/relevant-checks/SKILL.md` Mindset/NEVER/taxonomy/How-it-works text + `.claude/skills/relevant-checks/scripts/run-checks.md` invariants line + `docs/linting.md`'s `/relevant-checks` bullet are all aligned with the broader `[ -f ]` semantics. Closes #1277.

## [15.12.36] - 2026-05-06

### Fixed

- Malformed GitHub issue numbers in `analyze-issues` dumps are now treated as recoverable input defects instead of collapsing distinct issues onto synthetic issue 0. `_parse_issue_number` validates `number` before body capping in `load_issues` and skips missing/null/non-numeric/non-positive/bool/unicode-digit values with stderr WARN. The lenient skip policy now consistently covers both non-dict rows and malformed-number rows while preserving per-row warnings. The `issue_number` helper is strict and analyses now read `int(issue["number"])` directly. Regression coverage pins malformed-number warnings, mixed-corruption threshold behavior, digit-string acceptance, and W4/W5 no-issue-0 output (closes #1284).

## [15.12.35] - 2026-05-06

### Added

- New `skills/shared/topology.tsv` projection layer + `scripts/generate-topology-docs.sh` generator (registered in `scripts/generators.tsv`, `Makefile` shard `test-harnesses-5`, `agent-lint.toml`, `docs/linting.md`) that emits `docs/topology.md` as the consumer-doc projection of runtime authorities. Each TSV row's `runtime_authority` path is validated as repo-tracked and contains the row's `value` literal; the generator rejects bare-numeric or too-short values, duplicate keys, duplicate anchors, CRLF line endings, and uses an ASCII record-separator (`\035`) intermediate so empty `composition` columns render correctly. New regression harness `scripts/test-generate-topology-docs.sh` (sibling contract `test-generate-topology-docs.md`) pins write/check round-trips, anchor rendering, drift detection, TSV grammar, runtime-authority validation, CRLF rejection, duplicate-key rejection, short-numeric-value rejection, and empty-composition rendering. Consumer docs (`README.md`, `docs/skills.md`, `docs/review-agents.md`, `SECURITY.md`) link to verbatim-key anchors in `docs/topology.md` instead of repeating drift-prone counts.

### Changed

- Phase-2 drift-prone-count cleanup (closes #1271, combines #1259 + #1261). Sub-task A extends PR #1262's prose-rewrite sweep into runtime/dev surface — `skills/design/references/sketch-launch.md`, `skills/design/references/flags.md`, `skills/design/references/plan-review.md`, and `skills/implement/references/conflict-resolution.md` carry summary-prose rewrites with grep-stable allowlist preservation for byte-pinned literals (e.g. `2+ YES threshold accepts a finding`, `All 4 keys are required`) and CI-grepped focus-area enums. `SECURITY.md:42` updated to reflect the current `/research` flag surface (only `--no-issue`).

## [15.12.34] - 2026-05-06

### Changed

- `docs/linting.md:130` `make test-launch-review` description refreshed to document launcher exit-code parity with `${OUTPUT}.done` (success: `0`/`0`; `.error` and empty `.response`: `1`/`1`; missing `jq`: `127`/`127`), now that `scripts/test-launch-review.sh` asserts the launcher process exit code alongside the `.done` sidecar value (introduced by the #1273 Sub-task A `fail_closed` change). Closes #1289.

## [15.12.33] - 2026-05-06

### Added

- New regression harness `.claude/skills/relevant-checks/scripts/test-run-checks.sh` (sibling contract `test-run-checks.md`) that pins documented exit-code paths in `.claude/skills/relevant-checks/scripts/run-checks.sh`. Coverage: zero-phase exit 2 (empty `MODIFIED_FILES`, deletions-only branch), `agent-lint` exit-code propagation (rc=0 and rc=7) on BOTH the empty-`MODIFIED_FILES` post-checks-only path AND the changed-file dual-phase path, changed-file dual-phase happy path, changed-file pre-commit-fails path (script propagates pre-commit's exit code without invoking `run_post_checks`), changed-file pre-commit-success + agent-lint-absent path (`WARNING: agent-lint not found on PATH — skipping` banner), pre-commit-missing preflight (exit 1 + `ERROR: pre-commit not found`), and not-inside-a-git-repo (exit 1 + `ERROR: not inside a git repository`). Disposable git repos under `mktemp -d` with controlled-`PATH` `pre-commit` / `agent-lint` stubs; harness bails fast when `git` is missing from PATH. Wired into `Makefile` as `make test-run-checks` plus `test-harnesses-5` shard so it runs under `make lint` and the CI matrix. `.claude/skills/relevant-checks/SKILL.md` and `run-checks.md` updated to point at the new harness, document the rev-parse preflight invariant, and clarify `ERROR:` prefix wording. `docs/linting.md` adds a Makefile-targets row describing the harness coverage. Closes #1275.

## [15.12.32] - 2026-05-06

### Changed

- Gemini reviewer admin-policy hardening (combined OOS follow-ups #1254/#1253/#1252; closes #1273). **Sub-task A**: `scripts/launch-review.sh --tool gemini` `fail_closed` now `exit "$code"` (matching the `.done` sidecar value) instead of `exit 0`, so callers running under `set -e` fail fast on Gemini reviewer launch failures rather than relying on JSON-sidecar inspection. Test harness `scripts/test-launch-review.sh` updated to wrap fail-closed paths in `set +e` / `code=$?` and assert the expected exit codes (1 on `.error` and empty `.response`, 127 on missing `jq`); sibling contract `scripts/launch-review.md` adds the process-exit-matches-`.done` invariant. **Sub-task B**: deferred — neither `/research` nor `/design` currently routes Gemini lanes through `scripts/gemini-reviewer-policy.toml`, so no code change ships in this PR; the hardening intent stands as a tracked reminder. **Sub-task C**: tool-name drift alarm. New `scripts/lib-gemini-tool-drift.sh` sourced library wires `scripts/gemini-reviewer-policy.toml` as the single source of truth for the deny list plus a committed fixture `scripts/gemini-known-tools.txt` (with sibling `.md` and a `# checksum:` header) for known-catalog snapshot. `scripts/check-reviewers.sh` accepts a new `--artifact-dir` flag and runs `check_gemini_tool_drift` on the normal-probe success branch (skipping `WAIT_INFRA_ERROR` shortcut), classifying observed tools against `(deny_list ∪ fixture_lines)` with token-boundary substring matching against `{write,edit,delete,replace,create,modify,save,put,post,remove}`. Severity matrix: warn-always for any unknown tool (emit `GEMINI_TOOL_DRIFT_WARNING=` + stderr); flip `GEMINI_HEALTHY=false` only when the unknown tool's name token-boundary-matches a write-style keyword OR when a fixture-known tool with a write-style match is missing from the deny list. `scripts/session-setup.sh` parses + aggregates + re-emits drift warnings as multiple stdout lines plus a stderr banner, and now passes `--artifact-dir "$SESSION_TMPDIR"` to `check-reviewers.sh` for persistent diagnostic artifacts. New test cases in `scripts/test-check-reviewers.sh` cover clean fixture / benign new tool / write-style new tool / discovery unavailable / policy parser failure / fixture checksum mismatch / fixture undenied write-style tool / hung discovery. `SECURITY.md` updated with drift-alarm note + probe-vs-reviewer surface caveat. Code-review fixes also applied: forward `--repo` to `tracking-issue-write.sh rename` from `scripts/implement-finalize.sh` and `skills/fix-issue/scripts/finalize-umbrella.sh` so view and rename target the same repo; replace `IFS='='` `read` with explicit parameter expansion in `session-setup.sh`'s caller-env and probe-output parsing for self-documenting first-`=` split; guard `mktemp` failure in `rename_issue`; distinguish `gh api` probe failure from clean zero in `marker_present` check; pipe `_run_false_positive_marker` raw stderr through `scripts/redact-secrets.sh` to match the SECURITY.md `"suppresses raw marker stderr"` invariant.

## [15.12.31] - 2026-05-05

### Changed

- `docs/linting.md` `/relevant-checks` bullet updated to document the post-#1278 contract: the skill now also attempts the full-repo `agent-lint` phase even when the changed-file set is empty, and exits 2 with an `ERROR: no validation phases ran ...` line when zero validation phases actually ran. Cross-references the canonical contract in `.claude/skills/relevant-checks/SKILL.md`. Doc-only change. Closes #1276.

## [15.12.30] - 2026-05-05

### Added

- New `scripts/lint-literal-counts.py` repo-wide markdown policy lint that flags lines matching `^\s*\d+\s+(assertions|rules|bullets|rows|reviewers|agents|specialists|cases|fields|sections)\b` so prose drift after the markdown sweep landed in #1236 stays mechanically prevented. Authors who genuinely need a literal count (historical references, fixed counts that won't drift) opt out with the same-line pragma `<!-- lint-literal-counts: allow <reason> -->` (reason required; lowercase `allow`). Lines inside fenced code blocks are exempt with a length-aware state machine that honors nested fences. Wired as a `repo: local` pre-commit hook (`lint-literal-counts`, `language: python`, `pass_filenames: false`, `always_run: true`) so the full markdown sweep runs on every `pre-commit run --files` invocation including `/relevant-checks`. The hook enumerates markdown via `git ls-files --cached --others --exclude-standard -z -- '*.md'` so untracked-non-ignored markdown is also covered while gitignored trees stay excluded; non-git fixture roots fall back to a sorted `os.walk(followlinks=False)` traversal that excludes `.git/`, `node_modules/`, `.venv/`, `.agents/`. Sibling contract `scripts/lint-literal-counts.md`. Regression harness `scripts/test-lint-literal-counts.sh` (cases a–s) covers the fence state machine, BOM/CRLF normalization, allow-pragma parsing with reason and case-sensitivity, multi-file aggregation, exit-code precedence, git-worktree enumeration plus `.gitignore`/`.agents/` exclusion paired with the non-git fallback, untracked-non-ignored coverage, symlink non-following, and positional-argument rejection. Wired into Makefile target `test-lint-literal-counts` on shard 2; `agent-lint.toml` adds the harness `.sh` to the Makefile-only-reachability exclude list mirroring the `test-lint-skill-invocations.sh` precedent. `.claude/skills/relevant-checks/SKILL.md` notes the new repo-wide hook alongside `gitleaks` so operators reading the skill see that the literal-count lint runs on every invocation regardless of which files changed. The single existing match in the tree (`skills/research/scripts/test-render-findings-batch.md:13`, a fixture-ledger summary that diverges from a per-case enumeration that follows) carries an inline allow pragma with an explicit reason. Closes #1245.

## [15.12.29] - 2026-05-05

### Changed

- `.claude/skills/analyze-issues/scripts/analyze.py` `load_issues` now warns to stderr per non-dict element (with index + 60-char repr) and aborts the load when the skip ratio exceeds 5% of the input list, with `--lenient` to suppress the threshold abort. `default_category` now matches keywords via precompiled per-category word-boundary regexes, with a `_STEM_KEYWORDS` frozenset (`determin`, `validate`, `sanitize`, `simplify`, `permission`, `secret`, `feature`, `scaffold`, `failure`, `regression`, `assert`, `crash`, `refactor`, `rename`) for inflectional stems, so short tokens like `fix` no longer alias inside `fixture` / `prefix` / `affix` while inflections like `documentation` / `validation` / `refactoring` still classify correctly. Documentation/contract drift uses explicit kw enumeration with `\bdoc\b` whole-word boundary so `Docker` no longer aliases as Documentation. `run-analysis.sh` forwards `--lenient` via `ANALYZE_ARGS`; `SKILL.md`, `analyze.md`, `run-analysis.md`, `test-analyze.md`, and `docs/linting.md` updated; `test-fixture.json` extended to 10 issues; `test-analyze.sh` extended to 31 assertions covering the new word-boundary, stem, plural, and `--lenient` paths. Closes #1272.

## [15.12.28] - 2026-05-05

### Changed

- `skills/fix-issue/scripts/issue-lifecycle.sh` `cmd_close` no longer accepts the no-op `--repo` flag. Previously the flag was silently consumed (`shift 2`) and discarded; now it falls through to the case-statement's `*` branch and exits 2 with `Unknown option for close: --repo`. The repo binding for the `mark-false-positive` marker call remains the script-global `$REPO` resolved internally via `gh repo view`. Updates `skills/fix-issue/scripts/issue-lifecycle.md` (signature and Test harness paragraph) and `skills/fix-issue/scripts/test-issue-lifecycle.sh` fixture 8 to assert exit 2 and "Unknown option" stderr with no `gh issue comment` / `gh issue close` invocation. No in-tree caller passes `--repo` to `close`. Closes #1269.

## [15.12.27] - 2026-05-05

### Changed

- Refresh prose docs around the generators registry walker: `docs/review-agents.md`, `skills/shared/reviewer-templates.md`, `AGENTS.md`, `agent-lint.toml`, and `scripts/generate-code-reviewer-agent.md` now describe `scripts/check-generators.sh` (which iterates `scripts/generators.tsv` and dispatches each registered generator in `--check` mode) as the CI enforcement entry point, and `scripts/generate-code-reviewer-agent.md` no longer claims a pre-commit / `make lint` invocation wraps the generator's `--check` mode locally — only CI's `agent-sync` job runs the walker; locally `make test-check-generators` (or `make lint` via the test-harnesses aggregate) exercises it. No behavior change.

## [15.12.26] - 2026-05-05

### Changed

- `.claude/skills/relevant-checks/scripts/run-checks.sh` now fails loudly (exit 2 with `ERROR: no validation phases ran ...`) when zero validation phases actually executed — the empty-`MODIFIED_FILES` branch now attempts the full-repo `agent-lint` phase via `run_post_checks` instead of exiting 0 immediately, and `run_post_checks` increments a session-scoped `PHASES_RUN` counter only when `agent-lint` actually ran. The post-pre-commit happy path is unchanged (pre-commit success increments `PHASES_RUN` so exit 0 stands when `agent-lint` is absent). Closes a CI-parity footgun where callers treating `/relevant-checks` alone as full CI equivalence got a false green when no phases ran. Updates `.claude/skills/relevant-checks/SKILL.md` (Mindset, Maintenance rule, How it works, Failure-mode taxonomy, NEVER table) and the sibling `.claude/skills/relevant-checks/scripts/run-checks.md` contract to match the new exit semantics. Closes #1260.

## [15.12.25] - 2026-05-05

### Added

- New `--close-class <false-positive|duplicate|superseded|done>` flag on `skills/fix-issue/scripts/issue-lifecycle.sh close`. The structured close-reason enum deterministically drives the `[FALSE-POSITIVE]` title marker decision at the call site (mark on `false-positive`, `duplicate`, `superseded`; skip on `done`); the closing comment is never scanned. When paired with the legacy `--mark-false-positive-if-keyword` flag on the same call, `--close-class` wins silently. Invalid enum values exit 2 with a usage error before any `gh` work runs.
- `/fix-issue` Step 3 (not-material close) now passes `--close-class <inferred>` derived from the triage decision (already-fixed → `done`, duplicate-of → `duplicate`, superseded-by → `superseded`, invalid/false-positive → `false-positive`) instead of the keyword-inference flag. Step 6b NON_PR closes pass `--close-class done` so legitimate completion summaries cannot misclassify as false-positive closes (resolves the FINDING_7 risk that excluded NON_PR from the v1 keyword wiring). Legacy `--mark-false-positive-if-keyword` callers external to `/fix-issue` are not changed and continue to work via the keyword scan.

### Changed

- `skills/fix-issue/scripts/issue-lifecycle.sh` factors the marker invocation into a shared `_run_false_positive_marker` helper used by both the enum branch and the legacy keyword branch. Updates `skills/fix-issue/scripts/issue-lifecycle.md`, `skills/fix-issue/SKILL.md` (Steps 3 / 6b), `skills/fix-issue/references/triage-classification.md`, `skills/fix-issue/references/non-pr-execution.md`, `scripts/false-positive-keywords.md`, and `SECURITY.md` to document the structured close-reason enum as the new default and the keyword flag as the legacy fallback. Closes #1268.
- `skills/fix-issue/scripts/test-issue-lifecycle.sh` adds 9 new fixtures (f17-f25) covering each enum value's marker behavior, `done` suppresses the marker even with keyword-bearing comments, precedence over the legacy flag for both marking values and `done`, invalid-value rejection, marker on already-CLOSED branch, and empty `--comment` permitted under `--close-class`.

## [15.12.24] - 2026-05-05

### Added

- New `[FALSE-POSITIVE]` additive title marker, applied at event-triggered close-time hook points (NOT a periodic sweep) when an OOS-style issue closes without a corresponding fix. Closing-comment keyword scan covers `won't fix`/`wontfix`, `superseded`/`superseded by #N`, `not an issue`/`not a bug`, `duplicate of #N`, `false positive`/`false-positive`, with a leading negation guard for `not a duplicate` / `not a bug` / `not a false positive` / `not an issue`. The marker coexists with managed lifecycle prefixes (`[IN PROGRESS]` / `[DONE]` / `[STALLED]`) and the sibling `[ROUND-TRIP]` marker (#1240); idempotent against the leading bracket-block sequence.
- New shared sourced libraries `scripts/lib-title-markers.sh` (pure title-grammar `insert_signal_marker` helper) and `scripts/false-positive-keywords.sh` (negation-guarded keyword matcher with `matches_false_positive_keywords`).
- New `mark-false-positive` subcommand on `scripts/tracking-issue-write.sh`, sharing the existing redact + 256-char truncation pipeline. New opt-in `--mark-false-positive-if-keyword` flag on `skills/fix-issue/scripts/issue-lifecycle.sh cmd_close`, default off; wired into `/fix-issue` Step 3 (not-material close) only. Step 6b NON_PR closes intentionally not wired (free-form `WORK_SUMMARY` would mis-classify legitimate completions).
- New regression harness `scripts/test-false-positive-keywords.sh` (positive + negative + grep-failure fixtures) wired into `make lint` via `test-harnesses-5`. New fixture (q) on `scripts/test-tracking-issue-write.sh` for the `lib-title-markers.sh` startup-guard fail-closed path. New fixtures on `skills/fix-issue/scripts/test-issue-lifecycle.sh` for flag-on/flag-off, close-failure, idempotent re-run, already-closed-branch, marker-call-failure, and non-repo-cwd invocation paths.
- Documents the deferral of `/implement` Step 9a.1 hook in `skills/implement/SKILL.md` (event-triggered scope only). Closes #1239.

## [15.12.23] - 2026-05-05

### Added

- Cap per-run /implement OOS issue filing via new env var `OOS_ISSUES_PER_RUN_CAP` (default 5). Once the combine pass at `skills/implement/references/anchor-comment-template.md` step 3.4 has written `$IMPLEMENT_TMPDIR/oos-combined.md`, a new step 3.4b runs `skills/implement/scripts/oos-issue-cap.sh`: when the resulting batch exceeds the cap, the helper keeps the first `(cap-1)` entries verbatim and folds the surplus tail into ONE aggregated `### OOS_<cap>:` summary entry. The aggregated entry's Description enumerates the rolled-up titles plus a brief excerpt of each rolled-up Description (bounded by `OOS_ISSUE_CAP_EXCERPT_MAX`, default 200, via the companion `oos-issue-cap-excerpt.py` UTF-8-aware truncator); each bullet carries an untruncated `[Files: <paths>]` suffix so the file-conflict pre-pass at step 3.5 still emits serialization edges for paths that would otherwise have fallen past the excerpt cutoff. The helper fails closed on parser/heading parity mismatches, non-OOS-shaped inputs, invalid env values, and on a same-path `--input-file`/`--output` collision; on any helper failure step 3.4b skips both step 3.5 and step 4 and emits a filing-skipped breadcrumb plus a tracking-issue placeholder so operators can manually file the items.
- New regression harness `skills/implement/scripts/test-oos-issue-cap.sh` (31 cases) wired into `make lint` via `test-harnesses-3`. `scripts/test-implement-structure.sh` assertion 9g pins the SKILL.md and anchor-comment-template.md prose so the helper invocation, env var names, fail-closed wording, and helper warning string cannot drift silently.
- `docs/configuration-and-permissions.md` documents both env vars (defaults, behavior, security guidance). Closes #1244.

## [15.12.22] - 2026-05-05

### Changed

- Make generated-artifact drift checks registry-driven so future generators can join CI with one reviewed row.
- Preserve the existing code-reviewer drift guard as the initial registry entry.
- Add focused offline coverage for registry parsing, validation, generator failures, and post-run drift. Closes #1237.

## [15.12.21] - 2026-05-05

### Changed

- Reduce documentation drift by anchoring topology summaries to the canonical phase and reviewer docs (`docs/agents.md`, `docs/collaborative-sketches.md`, `docs/external-reviewers.md`, `docs/installation-and-setup.md`, `docs/review-agents.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, `README.md`).
- Preserve quick-mode marker literals, voting thresholds, and security/trust-boundary counts where the number is the tested or normative contract.
- Keep this PR limited to consumer-facing documentation prose; the future P2c lint rule remains out of scope. Closes #1236.

## [15.12.20] - 2026-05-05

### Added

- Add offline /analyze-issues regression coverage for category, waste, growth, reviewer, and vote-tally behavior.
- Wire the analyze harness into the Makefile shard suite while preserving the dev-only runtime prompt surface.

## [15.12.19] - 2026-05-05

### Changed

- Block file writes by the Gemini reviewer launcher via gemini-cli's Policy Engine. `scripts/launch-review.sh --tool gemini:158` now appends `--admin-policy "$SCRIPT_DIR/gemini-reviewer-policy.toml"` to the inner `gemini` argv; the new plugin-shipped TOML denies `write_file`, `replace`, `edit`, `edit_file`, `delete_file` at admin priority 5999, which overrides `--approval-mode yolo`'s default-allow. Shell remains under yolo so `git diff` / `git log` reviewer probes still work. The Gemini implementer launcher (`launch-gemini-implement.sh`) is intentionally NOT changed. `scripts/test-launch-review.sh` now pins both `--approval-mode yolo` and the `--admin-policy` argv pair (basename + non-empty path on disk). `SECURITY.md`, `scripts/launch-review.md`, `scripts/test-launch-review.md`, `docs/external-reviewers.md`, and `docs/review-agents.md` updated to record the new mechanical guarantee, the off-label `--admin-policy` use, and the residual shell-write risk. Closes #1234.

## [15.12.18] - 2026-05-05

### Changed

- Document the `/analyze-issues` coordinator's sensitivity behavior in `.claude/skills/analyze-issues/SKILL.md` — the dump path is now correctly described as `${TMPDIR:-/tmp}/<sanitized-repo>-issues.json` with the slug rule (forward-slash → dash, alnum/`-`/`_` only), `umask 077`, and `fetch-issues.sh`'s atomic temp+mv contract, plus a link to `scripts/run-analysis.md` for the full contract. The sibling `scripts/run-analysis.md` Invariants line is updated in lockstep so the cross-reference is credible. Documentation-only; no behavioral change. Closes #1249.

## [15.12.17] - 2026-05-05

### Added

- Project-local `/analyze-issues` skill at `.claude/skills/analyze-issues/` that produces a backlog-and-process insight report from a repository's GitHub issues. Single shell-out point (`gh issue list`) plus local `python3` processing covers coverage stats, category breakdown, cumulative-growth ASCII chart, pattern observations, wasteful-work findings, reviewer/persona effectiveness (with longest-first regex alternation so `codex` is not confused with `code`), and a one-paragraph executive summary. Coordinator at `scripts/run-analysis.sh` writes the raw `gh` JSON dump under `${TMPDIR:-/tmp}` with `umask 077` and atomic temp+mv so issue bodies stay user-private and never torn on partial fetch failure. Per-script contracts at `scripts/{run-analysis,fetch-issues,analyze,render-chart}.md`. Dev-only — does not ship in the plugin tree.

## [15.12.16] - 2026-05-05

### Changed

- Harden the wait/collector/check-reviewers script family. `scripts/wait-for-reviewers.sh` now emits indexed stdout records (`DONE <idx> <basename>: exit=<code>`, `TIMEOUT <idx> <basename>`) and rejects zero-valued padded timeout / poll-interval forms (`00`, `000`), while `scripts/collect-agent-results.sh` correlates wait timeouts by argv index instead of basename and fails closed on missing or malformed retry `TIMEOUT=` metadata. `scripts/check-reviewers.sh` now distinguishes wait infrastructure errors with `WAIT_INFRA_ERROR=<reason>` and preserves available tools as `*_HEALTHY=true` instead of turning a wait failure into a per-tool health failure. Regression coverage and contracts updated across wait, collector retry, duplicate-basename, and probe-infrastructure harnesses plus `SECURITY.md`, `docs/linting.md`, and shared external-reviewer docs. Closes #1217, #1218, #1219, #1220, #1222.

## [15.12.15] - 2026-05-05

### Changed

- `/implement` Step 9a.1 OOS pipeline now runs an automatic combine pass before filing. When more than one accepted OOS entry exists across the three source artifacts (`oos-accepted-design.md`, `oos-accepted-review.md`, `oos-accepted-main-agent.md`), the orchestrator groups related entries (same code area, similar change pattern, overlapping scope, sequential dependency) into a smaller batch written to `$IMPLEMENT_TMPDIR/oos-combined.md`. Both `oos-file-conflict-deps.sh` and the `/issue` batch invocation read that path as `--input-file`. Combined entries preserve all actionable content from sources, retain `--blocked-by-issue $ISSUE_NUMBER` forwarding to the tracking issue, and continue to receive inter-OOS dependency edges from the file-conflict pre-pass plus `/issue` Phase 2 LLM dep analysis. Combining is silent and unconditional in the orchestrator path — no interactive `/combine-issues` invocation. New `scripts/test-implement-structure.sh` assertion `(9f)` pins the literal `oos-combined.md` in the canonical Step 9a.1 procedure section so the combine-pass output path cannot regress while CI stays green.

## [15.12.14] - 2026-05-05

### Changed

- Replace the literal "47 literal-substring assertions on awk-extracted blocks" in `docs/linting.md`'s `make test-umbrella-emit-output-contract` row with the structural prose "structural literal-substring assertions on awk-extracted blocks" so the row stays accurate as new pinned literals are added to `skills/umbrella/scripts/test-umbrella-emit-output-contract.sh`. The "47" was already stale (the harness has 53 `assert_contains` calls today), and parallels the same drift-resistance fix #1215 applied to the harness's sibling `.md`. Documentation-only edit; no harness or CI behavior change. Closes #1227.

## [15.12.13] - 2026-05-05

### Changed

- Replace the literal "Fifty-two assertions, fail-fast on first miss." line in `skills/umbrella/scripts/test-umbrella-emit-output-contract.md` with a structural description ("All `assert_contains` calls fail-fast on first miss; the total grows as new pinned literals are added.") so the doc cannot silently disagree with the harness's actual `assert_contains` total as new pinned literals (e.g. the recent `k*` family) are added. Documentation-only edit; no harness or CI behavior change. Closes #1215.

## [15.12.12] - 2026-05-05

### Changed

- Strengthen the three implementer-launcher harnesses (`skills/implement/scripts/test-{codex,cursor,gemini}-implementer.sh`) so missing-input Tests 3 / 3a / 3b / 3c capture stderr to per-test scratch paths and pin the launcher's literal validation phrasing via `grep -F -- "<expected>"` (`plan file not found`, `feature file not found`, `agent prompt not found`, `--answers-file given but path does not exist`) — a future launcher regression where a different exit-2 path fires first or the input-file check is silently disabled now fails CI instead of satisfying the existing exit-code-only assertion. Add a Cursor `--answers-file` positive resume-path test to `test-cursor-implementer.sh` (mirroring `test-codex-implementer.sh:256-288` / `test-gemini-implementer.sh:230-258`): create an `ANSWERS` JSON fixture, invoke the existing PATH-stub launcher with `--answers-file "$ANSWERS"`, capture the wrapped prompt via `STUB_PROMPT_FILE`, and assert the prompt contains both `## Resume invocation` and the `$ANSWERS` path so the Cursor wrapper can no longer drop the resume block without an offline-harness failure. Update the three implementer-test sibling `.md` Coverage sections to record the pinned validation phrasing and (for cursor) the new resume-path assertion. Closes #1223 (combines #1213 + #1214).

## [15.12.11] - 2026-05-05

### Added

- Four mechanisms (A+B+C+D) that prevent leftover state in a single git clone from polluting the next `/clear`-bounded task. **(A)** `/implement` Step 18 stall-cleanup auto-stash: when `STALL_TRACKING=true` and `git status --porcelain` is non-empty, `scripts/implement-finalize.sh run_teardown()` runs `git stash push -u -m "larch-stalled-${ISSUE_NUMBER}-${STALL_STEP} ${UTC}"` and resolves the stash ref by label match with a `stash list -1` fallback. Stash failure or `git status` failure is best-effort (warns + continues). New optional state-file key `STALL_STEP`. **(B)** `scripts/sessionstart-health.sh` adds five probes — dirty working tree, larch-prefixed stash, interrupted rebase/merge/cherry-pick state, unmerged feature branches (gated on local `main` existing so master-only repos do not silently skip), and `.git/larch-stalled-run.txt` sentinel — emitted via a `jq -n --arg` JSON encoder so dynamic content (issue numbers, stall steps, stash refs) is safely escaped. Empty `STASH_REF` in the sentinel produces no-stash guidance instead of a fabricated `git stash apply no stash` command. The hook stays non-blocking and always exits 0; probes silently skip outside a git work-tree. **(C)** `scripts/preflight.sh` splits the single `--skip-branch-check` boolean into two: `--skip-branch-check` now skips only the on-main check; new `--skip-clean-check` is required to bypass the clean-tree check. The clean-tree check therefore runs whenever `--skip-clean-check` is absent, including the IS_USER_BRANCH=true continuation paths that previously waived it. The stalled-run sentinel is cleared only after every requested check passes AND the working tree is genuinely clean — never on a fetch/rebase failure or with `--skip-clean-check` over a dirty tree. **(D)** `run_teardown()` atomically writes `<git-dir>/larch-stalled-run.txt` (resolved via `git rev-parse --git-dir`) with five lines: `ISSUE_NUMBER=`, `ISSUE_URL=`, `STALL_STEP=`, `STASH_REF=` (from A), `TIMESTAMP=` (UTC ISO 8601). Documentation updates in `scripts/implement-finalize.md`, `scripts/preflight.md`, `scripts/sessionstart-health.md`, `skills/implement/SKILL.md` Steps 14 and 18, and `scripts/session-setup.sh` header. New `scripts/test-preflight-args.sh` (sibling `.md`) wired through `Makefile` `test-harnesses-5` and `docs/linting.md`. `scripts/test-sessionstart-health.sh` extended with cases for empty STASH_REF, master-only repos, interrupted-rebase, unmerged-branches, and the work-tree-skip path. `scripts/test-implement-finalize.sh` extended with stall+dirty / stall+clean / status-failure / success-path cases for the auto-stash and sentinel behavior. Closes #1203.

## [15.12.10] - 2026-05-05

### Changed

- Pin `scripts/wait-for-reviewers.sh`'s `--timeout` rejection contract (literal `0`, non-numeric, no-value-supplied) and the `DONE` / `TIMEOUT` stdout grammar via a new Makefile-wired regression harness `scripts/test-wait-for-reviewers.sh` (test-harnesses-5 shard) so future relaxations or grammar drift fail in CI. Fix the silent-swallow at `scripts/collect-agent-results.sh:183` where `2>/dev/null) || true` masked the new `wait-for-reviewers.sh --timeout 0` exit-1 (and any other wait usage / fatal error) into `SENTINEL_TIMEOUT` reviewer records: the **initial** wait now captures stderr to a temp file under `${TMPDIR:-/tmp}` (cleaned up via `EXIT` trap so signal-driven exits don't leak), surfaces wait stderr followed by a `collect-agent-results.sh: wait-for-reviewers.sh exited <N>` trailer, and exits 1 on any non-zero wait exit. The empty-output retry-phase wait (line ~492) deliberately keeps `>/dev/null 2>&1 || true` because retry outcomes are re-checked from sentinel state downstream. Wire the new harness into `Makefile` (`.PHONY` + shard 5 + recipe), `agent-lint.toml` (harness + sibling-doc allow-lists), and `docs/linting.md` (target table). Closes #1200 (combines #1186 + #1188).

## [15.12.9] - 2026-05-05

### Changed

- Expand offline implementer-launcher harnesses (`skills/implement/scripts/test-codex-implementer.sh`, `test-cursor-implementer.sh`, `test-gemini-implementer.sh`) with three additional missing-input rejection tests (Tests 3a/3b/3c — missing `--feature-file`, missing `--agent-prompt`, `--answers-file` pointing at a non-existent path) mirroring Test 3's exit-2 shape, plus a positive leading-zero timeout acceptance test (Test 9 — `--timeout 010`) pinning contract stability of the leading-zero positive form at the launcher boundary. Update each sibling `.md` Coverage section to enumerate the four asserted missing-input cases (replacing the overclaiming "Missing input files exit 2" bullet) and add the leading-zero acceptance bullet. Add one Edit-in-sync rule bullet to `skills/umbrella/scripts/test-umbrella-emit-output-contract.md` covering the `(k1)`–`(k5)` family (PIECES_JSON pipeline + `--blocked-by-issue` forwarding prose in `skills/umbrella/SKILL.md` Step 3B.1 / 3B.1.5 / 3B.2 / 3B.4), parallel to the existing `(j1)`–`(j7)`, `(g1)`–`(g4)`, `(h1)`–`(h4)`, `(i1)`–`(i6)` rules. Closes #1211 (combines #1208 / #1209 / #1204).

## [15.12.8] - 2026-05-05

### Changed

- Source `scripts/external-tool-registry.sh` from `scripts/collect-agent-results.sh` and rewrite `derive_tool()` to validate observed `.meta` `TOOL=` labels via `larch_is_external_tool` and to scan the basename for any registered `LARCH_EXTERNAL_TOOLS` token. Closes the deferred convergence point flagged by DECISION_2 of #1099 (and tracked as #1146): `derive_tool()` no longer hardcodes `codex|cursor|gemini` in either the `.meta` validation `case` or the basename `[[ ... ]]` chain, so adding a new external tool to `LARCH_EXTERNAL_TOOLS` automatically extends collector tool labeling. The `unknown` outcome is preserved verbatim as the observational fallback for partial / malformed launches whose `.meta` and basename do not identify a registered tool. The collector's per-tool monotonic-health helpers (`get_tool_healthy`, `set_tool_unhealthy`, and the `--write-health` envelope's `CODEX_HEALTHY` / `CURSOR_HEALTHY` / `GEMINI_HEALTHY` fields) intentionally remain hardcoded — these three explicit variables are consumed downstream by `session-setup.sh` / `write-session-env.sh` as discrete keys and generalizing them is a separate health-envelope change. The residual wedge is documented in `scripts/collect-agent-results.md` and `scripts/external-tool-registry.md`, and a new step 6 in the registry's "Adding a new external tool" checklist explicitly directs maintainers to extend the collector health envelope when the new tool flows through `collect-agent-results.sh`. The substantive-validation block comment that previously listed the literal `codex|cursor|gemini|unknown` enum is updated to describe the registry-driven label set. Sourcing pattern matches `scripts/check-reviewers.sh` and `scripts/agent-model-args.sh`: idempotent sentinel-guarded `source` of `external-tool-registry.sh` with fail-closed `exit 1` on read error or missing `LARCH_EXTERNAL_TOOL_REGISTRY_LOADED` sentinel; `scripts/external-tool-registry.md` and the `external-tool-registry.sh` header comment now list `scripts/collect-agent-results.sh` in the consumers list. Closes #1146.

## [15.12.7] - 2026-05-05

### Added

- Add `skills/implement/scripts/test-codex-implementer.sh` (with sibling `test-codex-implementer.md`), an offline launcher-contract harness for `scripts/launch-codex-implement.sh`. Mirrors the `test-cursor-implementer.sh` / `test-gemini-implementer.sh` shape: PATH-stubs `codex`, exercises required-flag validation, bad/zero/multi-digit-zero (`0`/`00`/`000`) timeout rejection, missing-input-file rejection, the five-line KV stdout envelope, transcript capture, the Codex argv shape (`exec`, `--full-auto`, `-C`, `--output-last-message`, model args, `--` separator before the prompt), model-arg forwarding (`LARCH_CODEX_MODEL=stub-codex-model`), and resume-block prompt composition under `--answers-file`. Wires `test-codex-implementer` into the `Makefile` `.PHONY` list and into `test-harnesses-2`, and references the new harness from `skills/implement/SKILL.md` Step 2 launcher coverage and `docs/linting.md`. Closes #1197.

## [15.12.6] - 2026-05-05

### Changed

- Switch `scripts/launch-review.sh --tool gemini` from `--approval-mode plan` to `--approval-mode yolo` so the Gemini reviewer (used by `/review` and `/implement --quick`) can read the live working tree and run `git diff main...HEAD` / `git log main...HEAD --oneline` itself, matching the Cursor (`--workspace "$PWD"`) and Codex (`-C "$PWD"`) reviewer postures. Reviewer prompts in `skills/implement/SKILL.md` Step 5 (rounds 1-3 generic Gemini slot and rounds 4+ Gemini fallback) and `skills/review/SKILL.md` (optional Gemini generic slot, both diff and description modes; rounds 4-7 single generic) drop the "build a self-contained prompt by inlining `DIFF_FILE`/`COMMIT_LOG_FILE`/`FILE_LIST_FILE`" preamble and use the same standard prompt the Cursor/Codex reviewers use, with an explicit `Do NOT modify files. Do NOT commit. Do NOT push.` behavioral request. Verification: tested locally that Gemini's `--approval-mode plan` allows file reads (`read_file` tool) but blocks shell execution ("Tool execution denied by policy. You are in Plan Mode with access to read-only tools. Execution of scripts (including those from skills) is blocked."), so a "compromise" mode that keeps `plan` while granting shell tools does not exist — `yolo` is the only Gemini posture that supports the live-repo review workflow. The Gemini health probe in `scripts/check-reviewers.sh` deliberately stays at `--approval-mode plan` (least privilege) — it sends a fixed `"Respond with OK"` prompt and never invokes a tool, so it does not need the shell/file-read affordance. Probe and reviewer share only the `$GEMINI_MODEL` resolution, not the approval posture. Regression guards: `scripts/test-launch-review.sh` now records the inner `gemini` argv via stub and asserts `--approval-mode yolo`; `scripts/test-check-reviewers.sh` now records the probe argv and asserts `--approval-mode plan`. A future drift in either direction fails the harness instead of silently re-aligning the two. `SECURITY.md` and `docs/review-agents.md` updated to reflect the new posture (Gemini reviewer trust boundary now matches Cursor's `--trust` and Codex's `--full-auto` reviewer postures — non-modification is a behavioral request, not a sandbox guarantee). Closes the user-reported gap "gemini code reviewer ... appears to be unable to read the diff / local repo, so it has to be called in a way where the diff is embedded in the prompt."

## [15.12.5] - 2026-05-05

### Fixed

- Align `<output>.done` with the real exit code on the `scripts/run-external-agent.sh` jq `CMD_JSON` serialization-failure path. Previously the script set `EXIT_CODE=99` ("wrapper crashed before capturing real exit code") as a default at line ~138, installed an EXIT trap that wrote `$EXIT_CODE` to `<output>.done`, then called `exit 1` on jq failure without updating `EXIT_CODE` — so callers reading `.done` saw `99` instead of `1` and could not distinguish a clean configuration / wrapper failure from an unhandled wrapper crash. Now the jq-failure branch sets `EXIT_CODE=1` immediately before `exit 1`, the EXIT trap writes `1` to the sentinel, and `scripts/test-run-external-agent.sh` carries a regression case with a `PATH`-prefixed stub `jq` that asserts wrapper exit `1`, the expected stderr line, `<output>.done == 1`, and absence of `<output>.meta`. The `99` default remains reserved for true wrapper crashes after trap installation. Closes #1195.

## [15.12.4] - 2026-05-05

### Changed

- Align two umbrella skill test artifacts under `skills/umbrella/scripts/` with current contracts. `test-umbrella-parse-args.md`'s Purpose paragraph now lists `PIECES_JSON` in the documented stdout-grammar key set (between `UMBRELLA_SUMMARY_FILE` and `BLOCKED_BY_ISSUE`, matching `parse-args.md`'s order) and drops the now-stale "intentionally leaves the pre-existing `PIECES_JSON` list drift to the separate OOS PR" sentence. `test-umbrella-emit-output-contract.sh` gains a `k5` assertion in the `(k*)` family pinning the literal `--blocked-by-issue $BLOCKED_BY_ISSUE` forwarding inside the awk-extracted Step 3B.2 block — defense-in-depth complementary to `test-umbrella-blocked-by-issue.sh`'s dedicated needles. The sibling `.md` documents the new assertion (51 → 52). Closes #1201 (combines OOS observations #1191 and #1192).

## [15.12.3] - 2026-05-05

### Removed

- Drop the dead trailing for-loop and its misleading comment block from `scripts/hydrate-anchor.sh`. The loop body was a single no-op (`:`) yet the surrounding comment claimed to "strip exactly one trailing newline that awk's `>>` reliably appends per `print`" — behavior that was never actually implemented. The hydrate→assemble round-trip is byte-stable in practice via the awk-level `>>` accumulation symmetry between `hydrate-anchor.sh` and `assemble-anchor.sh`. The script's section extraction and stdout contract (`HYDRATED=` / `SECTIONS=` / `ERROR=`) are unchanged. Closes #1159.

## [15.12.2] - 2026-05-05

### Fixed

- Reject zero-valued multi-digit timeout strings (`00`, `000`, ...) in `scripts/launch-cursor-implement.sh`, `scripts/launch-codex-implement.sh`, `scripts/launch-gemini-implement.sh`, `scripts/launch-review.sh --tool gemini`, and `scripts/run-external-agent.sh`. The previous `''|*[!0-9]*|0)` case pattern only rejected the single-character literal `0` — strings like `00` and `000` slipped through; in `run-external-agent.sh` this re-created the original bug where `[ "$SECONDS" -ge "$TIMEOUT_SECONDS" ]` treated `00` as 0 and reported the child as already timed out on the first poll iteration. Each script now adds an `if (( 10#$TIMEOUT < 1 )); then ...; fi` guard immediately after the existing case statement (using base-10 arithmetic to avoid octal interpretation), reusing the same error message and exit code. `launch-review.sh --tool gemini` and `run-external-agent.sh` additionally normalize `TIMEOUT=$((10#$TIMEOUT))` after validation so downstream arithmetic — the 600s clamp at `launch-review.sh --tool gemini:132` and the timeout-message division at `run-external-agent.sh:187` — interprets accepted leading-zero positive values (e.g. `010` → 10) consistently as decimal. Regression coverage extended in `scripts/test-run-external-agent-args.sh` (cases for `00`, `000`, and `010` acceptance), `skills/implement/scripts/test-cursor-implementer.sh`, `skills/implement/scripts/test-gemini-implementer.sh`, and `scripts/test-launch-review.sh`. Sibling `.md` contracts updated. Closes #1167.

## [15.12.1] - 2026-05-05

### Changed

- Allow `/implement`'s early rebase checkpoints (Steps 1.r, 4.r, 7.r, 7a.r) to attempt conflict resolution rather than immediately bailing on the first rebase conflict against latest main. `scripts/rebase-push.sh` gains a `--keep-on-conflict` flag (only valid with `--no-push`) that leaves the rebase in progress and emits `CONFLICT_FILES=...` on stdout, plus relaxes the `--continue` + `--no-push` mutex so the local-only resolution loop can finish. The Rebase Checkpoint Macro M2 now passes `--no-push --skip-if-pushed --keep-on-conflict`; M3 dispatches on exit code (exit 1 → invoke `conflict-resolution.md` Phase 1+2+4 with new `caller_kind=early_rebase`; exit 3 / other → bail to Step 18 as before). `conflict-resolution.md` adds the `early_rebase` caller family that skips Phase 3 (reviewer panel — redundant with Step 5's later `/review`) and runs a simplified Phase 4 with `rebase-push.sh --continue --no-push --keep-on-conflict` (no re-bump dispatch — no version bump exists at these checkpoints). Defense-in-depth: `rebase-push.sh` rejects `--continue --no-push` without `--keep-on-conflict` at parse time so a future caller can never silently abort an in-progress local-only rebase on a nested conflict. New regression harness `scripts/test-rebase-push-keep-on-conflict.sh` (with sibling `.md`) pins the four flag-combination behaviors via a sandbox repo: plain `--no-push` aborts on conflict (preserved), `--no-push --keep-on-conflict` leaves the rebase in progress, `--continue --no-push --keep-on-conflict` finishes a resolved local-only rebase without pushing, and the two flag-combination rejections (`--keep-on-conflict` without `--no-push`, `--continue --no-push` without `--keep-on-conflict`) exit 3 with the expected `REBASE_ERROR` lines. `scripts/test-implement-rebase-macro.sh` updated to assert the new M2 flag combo and the M3 conflict-resolution dispatch. `Makefile` and `agent-lint.toml` wire the new harness into `test-harnesses-1` and the agent-lint exclude list. Tracking issue #1184.

## [15.12.0] - 2026-05-05

### Added

- `--blocked-by-issue N` flag on `/umbrella`. The flag accepts a positive integer issue number and is forwarded to `/issue` on Step 3A (one-shot) and Step 3B.2 (batch children). Only batch child creation can succeed with the policy edge — single-mode is rejected by `/issue`'s frozen batch-mode-only error, providing fail-fast on misclassified one-shot runs (no silent drop). The flag is intentionally NOT forwarded to the Step 3B.3 umbrella-create call — the policy edge is meant for children, not the umbrella itself. `/umbrella` adds no new GitHub-API code; the policy edge POSTs flow through `/issue`'s existing `add-blocked-by.sh` invocation (one extra native blocked-by edge from N to each newly-created child). The flag is caller-agnostic: `/umbrella` enforces only the forwarding mechanics; the policy meaning ("tracking issue", "umbrella controller", etc.) belongs to the caller. Validation of N (digit-only positive integer; existence/open-state/not-PR via `/issue`'s Step 4.0 probe) is unchanged. New regression harness `skills/umbrella/scripts/test-umbrella-blocked-by-issue.sh` (with sibling `.md`) pins the SKILL.md forwarding grammar and `parse-args.sh` validation; `skills/umbrella/scripts/test-umbrella-parse-args.sh` extended with cases 35-44 covering parse, KV emission ordering, and rejection of empty / non-numeric / signed / leading-zero / zero values. Wired into `make lint` via `test-harnesses-4`. `README.md`, `docs/skills.md`, `docs/linting.md`, `SECURITY.md`, `skills/umbrella/SKILL.md`, `skills/umbrella/scripts/parse-args.sh`, and `skills/umbrella/scripts/parse-args.md` updated to document the new flag and forwarding semantics. Closes #1122.

## [15.11.24] - 2026-05-05

### Changed

- Update the header comment block in `scripts/external-tool-registry.sh` (lines 10-12 pre-PR) so it mirrors the `## Related` section in the sibling `scripts/external-tool-registry.md`. The previous header described `scripts/run-external-agent.sh` as a "label-only" consumer (citing only DECISION_1 of #1099), which drifted from the contract introduced by #1145 — the wrapper now sanitizes the `.meta` `TOOL=` field through a label-safe allowlist (alphanumerics, `.`, `_`, `-`); disallowed bytes translate to `_` (length-preserved); empty falls back to `sanitized-empty`. The updated header keeps the human-facing log / no-validation framing from #1099 while documenting the `.meta` sanitization behavior, and points readers to `scripts/run-external-agent.md` for the full sanitization contract. Comment-only change; no code or behavior modification. Closes #1181.

## [15.11.23] - 2026-05-05

### Changed

- Reject zero reviewer wait timeouts in `scripts/wait-for-reviewers.sh` so timeout values must be positive (case pattern `''|*[!0-9]*)` extended to `''|*[!0-9]*|0)`), aligning with the implement-family launchers (#1115) and `scripts/launch-review.sh --tool gemini`. `scripts/wait-for-reviewers.md` documents the `--timeout` argument contract beside the script. Closes #1166.

## [15.11.22] - 2026-05-05

### Added

- Structural-test assertion (27) in `scripts/test-implement-structure.sh` pinning `/implement` Step 1 normal-mode sub-step ordering: within `## Step 1 — Ensure Design Plan Exists`, the line introducing `**Manifest reuse (resumed sessions — runs first)**` must precede the lines introducing `**Simplicity classification preamble — skip condition**` and `**Both-externals-down inline-plan branch**`. The ordering is load-bearing: manifest reuse must run before simplicity classification (which can auto-switch to quick mode) and before the both-externals-down inline-plan branch (which writes a degraded `plan.txt`) so a resumed session never overwrites the prior `/design` artifact set. Sibling `scripts/test-implement-structure.md` updated to document the new assertion and bump the live-assertion count to 27. Closes #1165.

## [15.11.21] - 2026-05-05

### Changed

- Replace `eval`-based reconstruction of serialized child argv in `scripts/collect-agent-results.sh`'s empty-output retry path (lines 370-373 pre-PR) with a JSON-array deserializer. The writer side (`scripts/run-external-agent.sh:144`, `scripts/launch-review.sh --tool gemini write_meta()`) now emits `CMD_JSON=<jq -cn --args '$ARGS.positional'>` — a single-line JSON array of the post-`--` argv strings — instead of the legacy `CMD=<printf %q ...>`. The reader validates `type==array AND length>0 AND all string` via `jq -e`, decodes through base64+sentinel records (`jq -r '.[] | @base64'`) into a Bash array (Bash 3.2 portable: here-string `<<<` loop, no `mapfile`, no process substitution; trailing-newline-safe via per-element `printf X` sentinel), asserts decoded length, swaps only standalone argv elements equal to `OUTPUT_FILE` (substring-preserving), and exec's directly via array expansion — no `eval`. Missing or malformed metadata fails closed: the original result is rewritten to `STATUS=EMPTY_OUTPUT|HEALTHY=false`, `set_tool_unhealthy` runs for the affected tool, and a per-`j` `RETRY_LAUNCHED` array prevents the post-wait result-update loop from overwriting the specific `mark_retry_metadata_invalid` `FAILURE_REASON` (e.g., `Retry metadata invalid: malformed CMD_JSON`) with the generic "sentinel file missing" message when sibling indices in the same batch did launch retries. Distinct missing-key messages (`missing CMD_JSON and TOOL`, `missing CMD_JSON`, `missing TOOL`) narrow each fail-closed reason to the field actually absent. The Gemini launcher carries a missing-`jq` carve-out so the existing `LARCH_TEST_FORCE_MISSING_JQ` fail-closed path still calls `write_done()`. New regression harness `scripts/test-collect-agent-retry.sh` (with sibling `.md`) covers Cases A–H: happy path, malformed JSON, missing `CMD_JSON` (legacy `CMD=`-only sidecar with TOOL present), missing `CMD_JSON` and `TOOL` together, non-string array elements, newline-bearing argv (byte-exact via base64+sentinel), output-path-as-prompt-substring (must NOT mutate), Bash 3.2 vulnerable-runtime guard, and mixed-batch invalid+valid (regression guard for the `RETRY_LAUNCHED` per-`j` tracker). Wired into `make lint` via `test-harnesses-3`. `scripts/run-external-agent.md`, `scripts/launch-review.md`, `scripts/collect-agent-results.md`, and `SECURITY.md` updated to document the JSON-array format, `jq` + `base64 -d` retry-path prerequisites, the standalone-argv invariant for output paths, and the fail-closed health-flip contract. Closes #1154.

## [15.11.20] - 2026-05-05

### Added

- Regression harness coverage asserting that `--timeout 0` is rejected by the implement-family external launchers and the shared runner. `skills/implement/scripts/test-cursor-implementer.sh` and `skills/implement/scripts/test-gemini-implementer.sh` gain a Test 2b (parallel to Test 2's `--timeout nope`) asserting exit 2 plus stderr containing `must be a positive integer`. New `scripts/test-run-external-agent-args.sh` (with sibling `scripts/test-run-external-agent-args.md` per AGENTS.md per-script-contract rule) pins `run-external-agent.sh --timeout 0` exit 1 plus the unprefixed stderr literal `ERROR: --timeout must be a positive integer, got '0'`, and asserts no `<output>` / `.done` / `.meta` / `.diag` files are created on the rejection path. The new harness is wired into `make test-harnesses-5` plus `.PHONY`, registered in `agent-lint.toml` (the script and its sibling contract), and listed in `docs/linting.md`. `scripts/run-external-agent.md` lists the new harness alongside `scripts/test-run-external-agent.sh`. Closes the test-coverage gap left by #1115/#1171. Closes #1170.

## [15.11.19] - 2026-05-05

### Changed

- Update `scripts/external-tool-registry.md` `## Related` and step 5 of `## Adding a new external tool` to reflect that `scripts/run-external-agent.sh` sanitizes the `.meta` `TOOL=` field via a label-safe allowlist (introduced by #1145) — the human-facing log retains the raw `--tool` label, while disallowed bytes in the `.meta` sidecar are translated to `_` (length-preserved) and an empty result falls back to `sanitized-empty`. Also document that non-label-safe ids may collide after sanitization (e.g. `tool/a` and `tool?a` both become `tool_a`), so `.meta` `TOOL=` is not a bijection from arbitrary labels.
- Sync `scripts/run-external-agent.md` cross-link to `external-tool-registry.md` so both sibling contracts agree on the registry's framing (NOT sourced; no `--tool` validation; raw label in logs; sanitized `.meta` `TOOL=`).

## [15.11.18] - 2026-05-05

### Changed

## [15.11.16] - 2026-05-05

### Changed

- Document the line-oriented `.meta` sidecar grammar consumed by `scripts/collect-agent-results.sh` and emitted by `scripts/run-external-agent.sh` and `scripts/launch-review.sh --tool gemini::write_meta()`. Adds a per-field contract section in `scripts/run-external-agent.md` (TOOL allowlist, TIMEOUT integer validation, capture booleans, OUTPUT_FILE caller responsibility, CMD `printf '%q'` serialization with locale qualification), short pointer comments at the writer site in `scripts/run-external-agent.sh` and the parser sites in `scripts/collect-agent-results.sh`, and a cross-reference paragraph in `scripts/collect-agent-results.md`. Closes #1155 (OOS surfaced during round-1 review of #1145). Documentation only — no behavioral change.

## [15.11.15] - 2026-05-05

### Changed

- Reject unsafe `--output` paths at argv-validation time in `scripts/run-external-agent.sh` and `scripts/launch-review.sh --tool gemini` so they cannot corrupt the line-oriented `.meta` sidecar parsed by `scripts/collect-agent-results.sh` (closes OOS #1156, parallel to PR #1158 which sanitized `TOOL=`). Validation runs before any side effects (`rm -f`, `.done` trap install, `.meta` write, child launch) and is centralized in a new sourced-only library `scripts/lib-validate-meta-path.sh` consumed by both writers. Unlike `TOOL=` (transformed via a label-safe allowlist), `OUTPUT_FILE` paths are rejected because the same byte string is used on disk, in `.meta`, and inside the shell-quoted `CMD=` field that retry reconstruction substitutes; a `.meta`-only transform would split-brain those copies. The accepted alphabet is the conservative shell-quote-passthrough set `[A-Za-z0-9._/-]` — narrower than rejecting only `[:cntrl:]` and `=`, because `printf '%q'` shell-quotes spaces (and many other bytes) while `OUTPUT_FILE=` stores them raw, and the collector's substring substitution would silently miss spaced paths. **External integrators** invoking `run-external-agent.sh` or `launch-review.sh --tool gemini` directly with previously-tolerated paths (containing spaces, `=`, control bytes, or non-ASCII) will now fail fast with a clear stderr error; future widening of the alphabet is tracked separately via the OOS issue covering retry-substitution redesign.
- Reject `--timeout 0` in `scripts/launch-review.sh --tool gemini` (parallel to `scripts/run-external-agent.sh` and the implement launcher family per #1115); add a regression test in `scripts/test-launch-review.sh` and a parallel timeout-zero rejection assertion in the new `scripts/test-run-external-agent.sh` so the launcher contract cannot silently re-diverge.

## [15.11.14] - 2026-05-05

### Fixed

- Avoid implying that a PR completed with zero GitHub CI checks when `ci-wait` exits on its first poll (closes #1133).
- Clarify `ci-wait` stderr progress by labeling the internal loop counter as polls in user-facing strings and the surrounding comment / file-header.

## [15.11.13] - 2026-05-05

### Changed

- Generalize the validation rule 5 ("Dispatcher commit") parenthetical in `skills/implement/references/codex-manifest-schema.md` from "embedded by Codex" to "embedded by the external implementer" so the redactor's intent reads tool-neutrally alongside the rule 4 / rule 6 framing established by #1113. Closes #1149.

## [15.11.12] - 2026-05-05

### Changed

## [15.11.11] - 2026-05-05

### Fixed

- Align implement-launcher timeout validation with the documented positive-integer contract.
- Reject literal zero before any external implementer process is spawned.

## [15.11.10] - 2026-05-05

### Changed

- Hoist the `read-design-manifest.sh` reusable-design-manifest check above the both-externals-down inline-plan branch in `/implement` Step 1 normal mode so a resumed session never overwrites the prior `/design` artifact set when both externals happen to be unavailable. Closes #1126.

## [15.11.9] - 2026-05-05

### Changed

- Pin the post-merge anti-halt reminder literals in `skills/implement/SKILL.md` via a new structural assertion in `scripts/test-implement-structure.sh` (closes #1143).

## [15.11.8] - 2026-05-05

### Changed

- Align setup documentation with Gemini as an optional external tool (closes #1097).
- Keep collector and dispatcher harness documentation in sync with the canonical external-tool taxonomy.

## [15.11.7] - 2026-05-05

### Changed

- Keep Gemini implementer model values as a single CLI argument even when configured values contain whitespace.
- Align the Gemini implementer launcher contract with the safer reviewer-side model resolution pattern.

## [15.11.6] - 2026-05-05

### Fixed

- Harden `scripts/hydrate-anchor.sh` against path traversal and content injection in fetched anchor bodies. The awk extractor now sources the canonical `SECTION_MARKERS` allowlist from `scripts/anchor-section-markers.sh` and rejects any `<!-- section:<slug> -->` open whose slug contains `/`, `\`, or `..`, or that is not in the allowlist; an open arriving while a section is already active is also treated as malformed and drops the parser out cleanly so subsequent body lines are not appended to the previously-opened legitimate fragment. Adds `scripts/test-hydrate-anchor.sh` (wired into `make lint` via `test-harnesses-5`) covering traversal-shaped slugs, unknown slugs, traversal canaries, and the nested-malicious-open data-corruption case. Updates `SECURITY.md` to separate sentinel/id recovery (`tracking-issue-read.sh --sentinel`) from direct anchor hydration (`hydrate-anchor.sh`) and to state the parser's malformed-input contract. Adds `hydrate-anchor.sh` to the consumer lists in `scripts/anchor-section-markers.{sh,md}` so the edit-in-sync surface stays current. Closes #1138.

## [15.11.5] - 2026-05-05

### Changed

- Sanitize the `TOOL=` value written to `<output>.meta` in `scripts/run-external-agent.sh` through a label-safe allowlist (`LC_ALL=C tr -c 'a-zA-Z0-9._-' '_'`) so unusual `--tool` labels cannot corrupt line-oriented metadata parsing in `collect-agent-results.sh::derive_tool()` (closes #1145). Translation (rather than deletion) preserves length so adversarial labels like `cu\nrsor` become `cu_rsor` instead of collapsing into the canonical `cursor` id; the same logic blocks `=`, whitespace, and non-ASCII bytes (including Unicode line/paragraph separators U+2028/U+2029). Empty results fall back to a distinct `sanitized-empty` sentinel so the empty-output retry path stays functional. Human-readable log messages still use the raw `--tool` value as-is. Per the contract in `scripts/external-tool-registry.md`, `--tool` registry validation remains unchanged — labels remain permissive at the registry level.

## [15.11.4] - 2026-05-05

### Changed

- Extend the dispatcher mechanical bail-token enumerations in `skills/implement/scripts/step2-implement.md` to include `gemini-runtime-failure` and `gemini-modified-history` alongside their Cursor counterparts in both the "bailed manifests are NOT enforced" invariant bullet and the stdout-contract commented block under `MANIFEST=<path>`. Aligns the invariant bullet and stdout-contract comments with the canonical bail-token enumeration, the mechanical-bail behavior in `step2-implement.sh` (`emit_bailed`, no `MANIFEST=`), and the existing Codex/Cursor entries. Closes #1114. The reviewer panel surfaced — and this PR rejected — the originally-requested addition of `gemini-bailed-no-reason` to those two enumerations: that token is the per-tool fallback substituted into an implementer-authored `STATUS=bailed` envelope which DOES emit `MANIFEST=` (script lines 720-736), so listing it among mechanical / no-`MANIFEST` reasons would have contradicted the implementation. Doc-only; no script behavior changes.

## [15.11.3] - 2026-05-05

### Changed

- Update `scripts/preflight.sh` header comment so the exit-code listing for code 3 documents argument-validation failures in addition to fetch and rebase failures (closes #1125). The script already exits 3 on unknown CLI options at line 22 and the sibling contract `scripts/preflight.md` already enumerates all three exit-3 paths; this aligns the header comment with both. Comment-only change; no behavior change.

## [15.11.2] - 2026-05-05

### Changed

- Generalize validation rules 4 and 6 in `skills/implement/references/codex-manifest-schema.md` from naming "Codex" specifically to naming "external implementers" — the trust model documented in those two rules applies equally to all three external `--coder` choices (codex / cursor / gemini) per `SECURITY.md` and the file's own Tool-scope paragraph. Rule 5 wording was deliberately left unchanged per the issue's explicit scope (rules 4 and 6 only); the rule 5 consistency follow-up was filed as a separate issue. Closes #1113.

## [15.11.1] - 2026-05-05

### Changed

- Centralize external-tool and implementer-coder names in a sourced registry (`scripts/external-tool-registry.sh`) declaring `LARCH_EXTERNAL_TOOLS=(codex cursor gemini)` and `LARCH_IMPLEMENTER_CODERS=(claude codex cursor gemini)` once for the repo. Three consumers source the registry — `scripts/agent-model-args.sh`, `scripts/check-reviewers.sh`, and `skills/implement/scripts/step2-implement.sh` — using a fail-closed source guard plus sentinel check. `scripts/run-external-agent.sh` is a related label-only wrapper that aligns to the registry via a header comment per dialectic DECISION_1 (closes #1099).
- Keep per-tool behavior local while deriving validation and probe iteration from the registry. Per-tool model/effort `case` arms in `agent-model-args.sh`, parallel `get_*`/`set_*` helpers in `check-reviewers.sh`, and the launcher dispatch in `step2-implement.sh` are unchanged in shape; defensive `*)` arms catch drift if a future tool is added to the registry without a matching per-tool branch. Stderr wording (`--tool must be 'cursor', 'codex', or 'gemini'`, `--coder must be one of {claude,codex,cursor,gemini}`) is byte-identical to the prior literals.
- Add regression coverage and lint wiring for registry drift via `scripts/test-external-tool-registry.sh` (29 assertions: registry contents, predicates, brace-list formatters, double-source idempotency, no source-time stdout/stderr, no-shebang/non-executable, registry-vs-`check-reviewers.sh` consistency, registry-vs-`agent-model-args.sh` consistency, nested-cwd `step2-implement.sh --coder claude` path resolution). Wired into `make lint` via the `test-harnesses-5` shard with matching exclusions in `agent-lint.toml` and a row in `docs/linting.md`.

## [15.10.12] - 2026-05-05

### Changed

- Update the Cwd contract paragraph in `skills/implement/SKILL.md` Step 2.1 so the enumeration of external implementers covers Gemini in addition to Codex and Cursor (closes #1112). The same `REPO_ROOT` / cwd rules already apply once `--coder=gemini` passes the health gate; the paragraph now documents all three implementers uniformly. No behavior change.

## [15.10.11] - 2026-05-05

### Changed

## [15.10.10] - 2026-05-05

### Fixed

- `docs/linting.md` `make test-step2-dispatch` row now reports 37 assertions (was 35), matching the harness file header and `test-step2-dispatch.md`.

## [15.10.8] - 2026-05-05

### Changed

- Document the multi-tool `<tool>-commit-stderr.txt` path in `skills/implement/references/codex-manifest-schema.md` (lines 59 and 76). The dispatcher in `skills/implement/scripts/step2-implement.sh` writes `${TOOL_TAG}-commit-stderr.txt` where `<tool>` is `codex`, `cursor`, or `gemini`; the schema doc previously hard-coded the `codex-` literal. Documentation-only.

## [15.10.7] - 2026-05-05

### Changed

- Add sibling `.md` contracts for all 43 previously-undocumented `.sh` scripts under `scripts/` so every script in that directory now has a sibling per the AGENTS.md "Per-script contracts live beside the script" rule (closes #1107). Tightens AGENTS.md to spell out the two co-location patterns — primary-owns-the-full-contract for sourced libraries and test harnesses, plus cross-tree harnesses — and clarifies that neither is a file-existence exemption (test harness stubs still get a sibling pointing readers to the primary's contract). Pure documentation change; no script behavior is altered.

## [15.10.6] - 2026-05-05

### Changed

- Document the `--branch-info` trust model as a "Sharp edge — power-user / nested-call shape only" in `skills/design/references/flags.md` and the `skills/design/SKILL.md` flag table. Standalone callers that supply a complete `--branch-info` are trusted not to lie about `IS_MAIN`/`IS_USER_BRANCH`/`USER_PREFIX`/`CURRENT_BRANCH`; mismatched values silently bypass the standalone branch-state check. Also reworded `skills/design/SKILL.md` Step 0's `branch_info_supplied=true` paragraph so it no longer asserts "nested under `/implement`" — the four key values are accepted as-is from a trusted caller (normally `/implement`) and not cross-checked against the working tree. No behavior change.

## [15.10.5] - 2026-05-05

### Changed

- Document the strict clean-main entry contract for `/implement` and standalone `/design` in `docs/installation-and-setup.md`. The new section covers the four parts of the contract: (a) clean `main` is required by default — preflight asserts on-main + clean working tree + fetch + rebase before any side effects; (b) running on a `<USER_PREFIX>/*` branch is the explicit continuation opt-in; (c) `--issue <N>` adopts identity but does not waive the gate; (d) the normalized `PREFLIGHT_ERROR=...` failure message and three remediation paths (clean main, prefix-branch continuation, commit-or-stash). README's Setup TOC links to the new section.

## [15.10.3] - 2026-05-04

### Changed

- Speed up CI test-harness shards by parameterizing the wrapper / lock poll cadences. Adds `RUN_EXTERNAL_AGENT_POLL_INTERVAL` (default `10`) to `scripts/run-external-agent.sh`, `WAIT_FOR_REVIEWERS_POLL_INTERVAL` (default `5`) to `scripts/wait-for-reviewers.sh`, and `ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS` (default `1`) to `skills/fix-issue/scripts/issue-lifecycle.sh`. Production callers inherit the prior hard-coded sleeps unchanged; offline test harnesses (`test-cursor-implementer`, `test-gemini-implementer`, `test-launch-review`, `test-check-reviewers`, `test-find-lock-issue`) export sub-second values to avoid paying multi-second sleeps per stub invocation. Per-elapsed-minute progress lines in both wrappers now key off `$SECONDS / 60` instead of iteration count, so the cadence stays minute-based regardless of poll interval. The CI matrix shrinks from six shards to five (`test-harnesses-1` through `test-harnesses-5`) after merging the previously slowest cells; `make test-harnesses`, `.github/workflows/ci.yaml`, `scripts/test-harness-shards-coverage.sh`, and `docs/linting.md` are updated together. Coverage is preserved end-to-end — every prior assertion still runs, only the inert wait time was eliminated.

## [15.10.2] - 2026-05-04

### Added

- /implement Step 1 normal mode auto-switches to the quick workflow when the orchestrator classifies the task as SIMPLE, without consulting the user, emitting a clear bold breadcrumb. Skipped on resumed sessions where a reusable design manifest is present and when `--design-only` is set.

## [15.10.1] - 2026-05-04

### Fixed

- `scripts/preflight.sh` now runs `git rebase --abort` when the default-mode rebase fails, mirroring `scripts/rebase-push.sh:162-165`'s `--no-push` behavior. Previously a rebase conflict left the working tree mid-rebase. Adds `scripts/preflight.md` sibling contract documenting the new failure shape and exit-code semantics, including the unknown-flag exception that uses stderr-only output.

## [15.10.0] - 2026-05-04

### Added

- `/issue --blocked-by-issue N` — caller-supplied native-blocking edge for batch mode. When set, every newly created (non-DUPLICATE) batch item is recorded as `blocked_by` issue `N` using GitHub's Issue Dependencies REST API via `skills/issue/scripts/add-blocked-by.sh`. The flag is **caller-agnostic**: the policy meaning (e.g. "tracking issue") is the caller's. `N` must reference an OPEN issue (not a pull request) in the target repo at invocation time — verified by an open-issue precondition probe at the top of Step 4 (single `gh api` GET, single `jq @tsv` parse with tab-IFS, PR rejection, state check, title sanitization, runs in `--dry-run` too). The probe-cached `BLOCKED_BY_ISSUE_ID` is reused in Step 6 to skip per-edge id-lookups. Mutually exclusive with `--no-dedup`; rejected outside batch mode; non-positive integers rejected. Step 5 merges the policy edge alongside intra-batch deps with a narrow no-external-refs carve-out for the probe-validated value; Step-5-skip paths (`LIST_STATUS=failed`, allocator-fail, empty-CANDIDATES + N<2) are augmented at Step 6 so the policy edge still applies.
- `/implement` Step 9a.1 forwards `--blocked-by-issue $ISSUE_NUMBER` to `/issue` only when `$ISSUE_NUMBER` is set, `deferred=false`, and `repo_unavailable=false`. In any degraded mode the flag is omitted and OOS issues file without the policy edge — preferable to bailing OOS filing. Inter-OOS dependencies among batch items continue to be emitted by `/issue`'s existing Phase 1/2 analysis, now persisted as native `blocked_by` POSTs.
- `skills/issue/scripts/test-blocked-by-issue.sh` structural-grep harness pinning the new SKILL.md prose: `argument-hint` advertising, the three Validations rules, the Step 4-top probe (`gh api`, `pull_request != null`, `IFS=$'\t' read`, state check, title `tr -d '\t\n'`, dry-run inclusion), the Step 4 snapshot augmentation, the Step 5 merge paragraph, the Step 5 carve-out, the Step 6 Step-5-skip-path augmentation, and the cached `--blocker-id $BLOCKED_BY_ISSUE_ID` mention. Wired into `make lint` via `make test-blocked-by-issue` (`test-harnesses-3`). `scripts/test-implement-structure.sh` assertion 9d now also pins the `--blocked-by-issue` forwarding gate in `skills/implement/references/anchor-comment-template.md`.

## [15.9.1] - 2026-05-04

### Changed

- `/implement` and standalone `/design` now require a clean `main` branch at session entry by default, fail-closed with a normalized "clean main required" message listing three remediation paths (switch to clean main; check out a `<USER_PREFIX>/*` feature branch; commit/stash). The single continuation predicate is `IS_USER_BRANCH=true` from `scripts/create-branch.sh --check`; `--issue <N>` no longer waives the gate. Step 0 always fetches and rebases `origin/main` on the strict path before any tracking-issue side effects. Nested `/design` calls (with `--branch-info` from `/implement`) keep `--skip-branch-check` since the parent ran the gate. Adds `scripts/test-clean-main-gate.sh` structural test pinning the new invocation rules in both SKILL.md files.

## [15.9.0] - 2026-05-04

### Added

- `/implement --coder=gemini` — Gemini implementer launcher (`scripts/launch-gemini-implement.sh`) and agent file (`agents/gemini-implementer.md`) paralleling the Codex/Cursor scaffolding. `skills/implement/scripts/step2-implement.sh` accepts `gemini` in its `--coder` enum, takes a new `--gemini-healthy true|false` flag, and falls back to `claude_fallback` (main-agent edit path) when Gemini is unhealthy or unavailable — symmetric with the Cursor fallback. Generalized HEAD-baseline guard via a per-tool `REQUIRES_HEAD_UNCHANGED` capability set: Gemini emits `gemini-modified-history` on bail; Cursor's emitted token remains `cursor-modified-history` (byte-identical to current main); Codex (sandboxed) does not set the capability. Full session-env parity: `scripts/check-reviewers.sh --include-gemini` populates `GEMINI_AVAILABLE` / `GEMINI_HEALTHY`; `scripts/session-setup.sh --check-gemini-reviewer` opt-in keeps the probe scoped to `/implement` only (`/design`, `/review`, `/research` unaffected); `scripts/write-session-env.sh --gemini-healthy` persists the value; `/fix-issue` Step 1 forwards it. Implementer launches resolve `--model` from `LARCH_GEMINI_MODEL` → `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` → `gemini-2.5-pro` (matching the reviewer-side default). Includes `skills/implement/scripts/test-gemini-implementer.sh` regression harness (8 assertions), wired into `make test-harnesses-2`, plus extensions to `test-step2-dispatch.sh` (now 37 assertions) and `test-implement-structure.sh` assertion (24) for Cursor/Gemini shared-guardrails parity (modulo per-tool token substitution). `SECURITY.md` documents the new unsandboxed implementer alongside Cursor. Auto-selection (no `--coder` flag) remains byte-identical to current main; Gemini is opt-in only. Closes #1080.

## [15.8.4] - 2026-05-04

### Changed

- Give repository Q&A a direct-read default before broader agent dispatch.
- Clarify the limited cases where Explore or Agent escalation is appropriate.

## [15.8.3] - 2026-05-04

### Added

- `gemini_model` userConfig stanza in `.claude-plugin/plugin.json` paralleling `cursor_model` / `codex_model`, plus a `LARCH_GEMINI_MODEL` section in `docs/configuration-and-permissions.md`. Wires `scripts/launch-review.sh --tool gemini` and the Gemini health probe in `scripts/check-reviewers.sh` to resolve `-m` from `LARCH_GEMINI_MODEL` then `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL`, defaulting to `gemini-2.5-pro` (replacing the previously hardcoded `-m pro` argv on both paths). Operators preferring the prior alias can set `LARCH_GEMINI_MODEL=pro`. Closes #1088.

## [15.8.2] - 2026-05-04

### Added

- Wire Gemini in as a third optional external Code Reviewer in `/review` and `/implement --quick` Step 5 review rounds. New `scripts/launch-review.sh --tool gemini` (generic mode) clamps the Gemini headless invocation to a 600s timeout, parses the CLI's JSON envelope via `jq -er '.response // empty'` (rejecting `.error` and whitespace-only responses), and writes outputs through the standard atomic raw → normalized → `.done` sentinel lifecycle with `--capture-stdout-only` so Gemini stderr cannot corrupt the parsed review. Gating: `gemini_available=true` requires both binary present and a healthy probe; `scripts/session-setup.sh --check-gemini-reviewer` opt-in keeps `/design` and `/research` unaffected; `scripts/check-reviewers.sh` retry/early-exit logic is now N-tool data-driven; `scripts/write-session-env.sh` adds `--gemini-healthy`. Wired into `skills/review/SKILL.md` (panel grows from 6 to 7 when Gemini healthy; rounds 4-7 chain extends to Cursor → Codex → Gemini → Claude) and `skills/implement/SKILL.md` Step 5 quick-mode rounds 1-3 generic slot + rounds 4+ chain. Strictly additive: when Gemini is unavailable, every Gemini token is omitted from output (status tables, scoreboard, collector argv, summaries). Includes `scripts/test-launch-review.sh` regression harness with success / `.error` / empty-`.response` / missing-`jq` cases, plus structural assertions in `scripts/test-review-structure.sh` / `scripts/test-implement-structure.sh`. Also adds `scripts/run-external-agent.sh --capture-stdout-only` (stderr → `.diag`); hardens `collect-agent-results.sh` `build_failure_reason` against pipe / newline / CR injection from multi-line Gemini stderr; redacts the inlined `--prompt` body from `${OUTPUT}.meta` `CMD=` to a sha256+length tag to limit secret persistence in the session tmpdir. Out of scope (deferred to sibling issues): Gemini in design sketches/dialectic. Closes #1079.

## [15.8.1] - 2026-05-04

### Changed

- `/implement --merge` now has `scripts/merge-pr.sh` verify merge state and CI before any merge command, then try `gh pr merge --admin` first by default and fall back to a plain squash merge only if the privileged attempt is rejected. `--no-admin-fallback` still opts out of the privileged path, but now runs the same gate followed by a plain-only merge attempt; a plain failure still emits `MERGE_RESULT=policy_denied` with the existing error string. Step 12b prose, permission docs, and skill catalog text are updated to match the new order, and `scripts/test-merge-pr.sh` is wired into `make test-harnesses-2` to pin admin-first ordering, fallback, opt-out, and gate short-circuits (plus regression cases for `admin_failed` with multi-line `gh` output and empty / `UNKNOWN` `mergeStateStatus`).

## [15.8.0] - 2026-05-04

### Added

- New `/imq` alias skill forwarding to `/implement --merge --quick` (quick mode without `--auto`), filling the gap between `/im` and `/imaq`. Updates README aliases table, `.claude/settings.json` and `docs/configuration-and-permissions.md` permission allowlists, `docs/workflow-lifecycle.md` delegation topology and forwarder bullets, `docs/installation-and-setup.md` skill list, and the pure-delegator scope lists in `skills/shared/subskill-invocation.md` and `scripts/test-anti-halt-banners.sh`.

## [15.7.14] - 2026-05-04

### Added

- Document Gemini CLI install + setup in `docs/installation-and-setup.md`: Homebrew/npm install, OAuth login, `~/.gemini/settings.json` and `~/.gemini/trustedFolders.json` (with the macOS case-sensitivity gotcha), the Gemini CLI 0.40.x bundled-`rg` workaround, and free-tier `MODEL_CAPACITY_EXHAUSTED` vs Google AI Pro/Ultra capacity notes. Closes #1078; sibling integration issues under umbrella #1081 will wire Gemini into reviewer/coder paths.

## [15.7.13] - 2026-05-04

### Changed

- Update repo references from `zhupanov/larch` to `character-ai/larch` following the GitHub ownership transfer to the `character-ai` org. Touches `.claude-plugin/plugin.json` (`repository` and `homepage` URLs), `docs/installation-and-setup.md` (the `claude plugin marketplace add` install command and the `git clone` URL), `docs/configuration-and-permissions.md` (three historical issue links — #586, #566, #585), and the `/upgrade-larch` skill (`skills/upgrade-larch/SKILL.md`, `skills/upgrade-larch/scripts/upgrade-larch.sh`, `skills/upgrade-larch/scripts/upgrade-larch.md`). Historical CHANGELOG entries, the author email (`zhupanov@yahoo.com`), references to the separate `zhupanov/agent-lint` and `zhupanov/claude-lint` repos (not part of this transfer), and machine-local `/Users/zhupanov/larch1` paths in CHANGELOG history are intentionally left untouched.

## [15.7.12] - 2026-05-04

### Changed

- Speed up the lint CI job by parallelizing shellcheck (~21s → ~6s on 4-core runners), splitting it into a dedicated CI job that runs in parallel with `lint`, and adding pip caching to `actions/setup-python` across `lint`, the new `shellcheck` job, and the six `test-harnesses` matrix cells. The upstream `shellcheck-py` pre-commit hook is replaced by a local hook (`scripts/pre-commit-shellcheck.sh`) that fans `shellcheck -x` out via `xargs -0 -n1 -P $(nproc)`, with the engine binary still pinned to `shellcheck-py==0.10.0.1` via `additional_dependencies` on the local hook (`require_serial: true` keeps pre-commit from double-parallelizing on top). A new `.github/workflows/requirements-lint.txt` (`pre-commit==4.2.0` + `pyyaml==6.0.2`) is the shared dep manifest consumed by `cache: pip` and `pip install -r` across all three job classes; PyYAML is pinned in lockstep with the existing `lint-skill-invocations` `additional_dependencies` per `scripts/lint-skill-invocations.md`. Phase 1 (this PR) keeps `shellcheck` running inside `lint` so coverage is preserved while branch protection migrates to require the new `shellcheck` check; a small Phase 2 follow-up flips `lint`'s `SKIP=agnix` to `SKIP=agnix,shellcheck` once the branch-protection update lands. `docs/linting.md` documents the rollout, the shared requirements file, and the no-longer-required local `shellcheck` binary; `agent-lint.toml` excludes `scripts/pre-commit-shellcheck.sh` from the dead-script scan because pre-commit-config.yaml entries are not part of agent-lint's reachability graph. Closes #1074.

## [15.7.11] - 2026-05-04

### Fixed

- `/issue` Phase 1 dedup and `/fix-issue` auto-pick no longer drop legitimate non-archival titles that share a substring with archival prefixes. The grammar in `skills/issue/scripts/list-issues.sh`'s `DEDUP_SKIP_PREFIX_FILTER` and the new `has_archival_prefix` helper in `skills/fix-issue/scripts/find-lock-issue.sh` both require an ASCII space immediately following each archival keyword (<code>research </code>, <code>[research] </code>, <code>investigate </code>, <code>[investigate] </code>, <code>[research report] </code> after leading-whitespace trim + lowercase), so titles like "Researches went for a walk" or "Investigation of slow query" pass through. Auto-pick mirrors `/issue` Phase 1; explicit `/fix-issue <N>` is intentionally exempt. New fixture 14 in `skills/fix-issue/scripts/test-find-lock-issue.sh` covers substring non-collisions. Closes #1063.

## [15.7.10] - 2026-05-04

### Added

- `skills/issue/scripts/test-list-issues.sh` regression test harness pinning the dedup + TSV-shaping behavior of `skills/issue/scripts/list-issues.sh` end-to-end. Covers the `DEDUP_SKIP_PREFIX_FILTER` jq pipeline spliced into both `JQ_FILTER` branches: the five skip prefixes (case-insensitive, including `[Research]` / `[INVESTIGATE]` / leading-whitespace variants), TSV `\t` / `\n` / `\r` sanitization, the open-only branch (`CLOSED_WINDOW_DAYS=0`), and the closed-window branch (`CLOSED_WINDOW_DAYS>0`) with cutoff boundary checks. Drives `list-issues.sh` against static paginated-JSON fixtures (`fixtures/list-issues/page1.json`, `fixtures/list-issues/page2.json`) via PATH-stubbed `gh` and `python3` fakes; production code is unchanged. The fake `python3` extracts and validates the integer following `datetime.timedelta(days=` against an `EXPECTED_DAYS` env var the harness exports per invocation, so an off-by-one constant in production fails closed. Assertions use multiset TSV equality (`sort` + row-count) so duplicate rows from a buggy helper trip the check rather than collapsing under `sort -u`. Wired into `test-harnesses-2` shard via `Makefile` and listed in `docs/linting.md`; `skills/issue/SKILL.md` references the harness adjacent to the `list-issues.sh` invocation. Sibling contract `skills/issue/scripts/test-list-issues.md` documents the harness invariants. Closes #1059.

## [15.7.9] - 2026-05-04

### Changed

- Step 9a.1 OOS pipeline procedure in `skills/implement/references/anchor-comment-template.md` now requires the `/issue` batch invocation to forward `--title-prefix "[OOS]"` and forbids passing any `--label` flag. Auto-filed OOS issues consistently get the `[OOS]` title prefix without manual retitling, and consumer repos no longer see per-invocation stderr warnings from the `/issue` label-existence probe. A new structural assertion (9d) in `scripts/test-implement-structure.sh` pins the contract. Closes #1065.

## [15.7.8] - 2026-05-04

### Changed

- `/fix-issue` Step 4 classify breadcrumb refines the highlighting: only `$COMPLEXITY` is wrapped in 🟨 yellow-square markers (now with a space on each side of the bold value so the value isn't visually squeezed by the marker glyphs), while `$INTENT` keeps its bold but loses the surrounding 🟨 wrapping. New format: `✅ 4: classify — INTENT=**$INTENT** [COMPLEXITY=🟨 **$COMPLEXITY** 🟨] (<elapsed>)`. `skills/fix-issue/SKILL.md:193` and the matching contract paragraph in `skills/fix-issue/references/triage-classification.md:5` updated together. Closes #1068.

## [15.7.7] - 2026-05-04

### Fixed

- `skills/implement/scripts/test-step2-dispatch.sh` header comment no longer claims the default-coder path produces `STATUS=claude_fallback`. The bullet now correctly describes the default Codex outside-git → exit 2 behavior, matching Test 1b and the sibling contract doc. Closes #1067.

## [15.7.6] - 2026-05-04

### Changed

- `/implement` Step 2 enforces a mechanical edit-authority gate. The dispatcher (`skills/implement/scripts/step2-implement.sh`) now emits `ORCHESTRATOR_EDIT_AUTHORITY=allowed|forbidden` on every exit-0 outcome, with `allowed` iff `STATUS=claude_fallback`; on every external-implementer outcome (`complete` / `needs_qa` / `bailed`) it emits `forbidden`. `skills/implement/SKILL.md` adds NEVER #10 (the dual-predicate gate), a Step 2 entry preconditions matrix, and a §2.1.5 envelope-validation block that fail-closes any malformed or pair-illegal envelope to a synthetic `orchestrator-envelope-invalid` bail. `skills/implement/scripts/test-step2-dispatch.sh` grows to 28 assertions including Test 11 (pair invariant: exactly one AUTH line per envelope, `allowed` iff `STATUS=claude_fallback`). Prevents the `/imaq --coder=cursor` regression where the main agent could perform Edit/Write code edits while the dispatcher was supposed to own the working tree. Closes #1058.

## [15.7.5] - 2026-05-04

### Changed

- `skills/issue/scripts/list-issues.sh`: Phase 1 dedup snapshot now drops issues whose trimmed, lowercased title starts with `research`, `[research]`, `investigate`, `[investigate]`, or `[research report]`. /research-style archival reports no longer crowd out real semantic candidates from the per-item Phase 2 cap. Filter applies uniformly to the open-only and closed-window fetch branches. Closes #1055.

## [15.7.4] - 2026-05-04

### Changed

- Fix two agnix warnings surfaced in CI (CC-SK-012 in `.claude/skills/combine-issues/SKILL.md`, AS-010 in `skills/research/SKILL.md`) and promote agnix warnings to errors in every invocation mode: `.github/workflows/ci.yaml` agnix job now passes `strict: 'true'`, and `.pre-commit-config.yaml` invokes `agnix . --strict` (which `make agnix` inherits via pre-commit). `docs/linting.md` updated to surface the strict-mode behavior. Closes #1051.

## [15.7.3] - 2026-05-04

### Changed

- `skills/shared/subskill-invocation.md`: documents the dual-flag handoff for nested skill orchestration. New `## Subagent execution topology` section explains that `--session-env` (file-backed I/O routing) and `--subagent` (heavy-phase execution topology) are orthogonal, prescribes forwarding both when an orchestrator delegates heavy work to `/design`, and describes how `/implement`'s `--inline` flag controls whether `--subagent` is appended (default off → appended). Documentation-only; no behavior change. Closes #1039.

## [15.7.2] - 2026-05-04

### Changed

- `/fix-issue` Step 4: the `classify` breadcrumb now wraps `$INTENT` and `$COMPLEXITY` values in 🟨 yellow-square markers and `**...**` bold so the classification (e.g. `INTENT=PR COMPLEXITY=SIMPLE`) stands out at a glance in the Claude Code transcript. `skills/fix-issue/SKILL.md:192` and the matching contract paragraph in `skills/fix-issue/references/triage-classification.md:5` updated together (closes #1043).

## [15.7.1] - 2026-05-04

### Changed

- README.md and `docs/skills.md`: argument-hint tables for `/design` and `/implement` now match the canonical `argument-hint:` frontmatter in `skills/design/SKILL.md` and `skills/implement/SKILL.md`. Adds `[--subagent]` and `[--session-env <path>]` to `/design`; adds `[--inline]` and `[--session-env <path>]` to `/implement`. Documentation-only; no behavior change. Closes #1041.

## [15.7.0] - 2026-05-04

### Added

- `/fix-issue`: new `--inline` flag. Default (`inline_mode=false`) does not forward; when set, `--inline` is forwarded to the delegated `/implement` run on the **HARD bullet only** (Step 5a), where `/design` is invoked. The SIMPLE bullet uses `/implement --quick` which skips `/design`, so `--inline` is intentionally not forwarded there (no-op). Closes #1040.

## [15.6.0] - 2026-05-04

### Added

- `/design`: new `--subagent` flag. When `subagent_mode=true` AND `quick_mode=false`, Step 2a's heavy non-interactive phase (sketches → plan synthesis → plan review → optional Step 3b/4) runs in an isolated Agent-tool subagent that consumes `skills/design/references/heavy-worker.md`; otherwise the heavy phase runs inline in the executing agent. Standalone `/design --subagent` is a new capability — on `DESIGN_HEAVY=complete` the parent replays plan / voting tally / accepted findings / OOS / (auto-mode) architecture diagram inline before Step 5 cleanup so artifacts are not lost when `cleanup-tmpdir.sh` removes `$DESIGN_TMPDIR`. `STANDALONE_HEAVY_FAILED` gates Step 5b cleanup so a failed standalone subagent run preserves `$DESIGN_TMPDIR`. The dispatch decision is now keyed on `--subagent` instead of `SESSION_ENV_PATH` non-empty (the I/O contract — verbosity suppression, manifest export, OOS routing — remains gated on `SESSION_ENV_PATH`).
- `/implement`: new `--inline` flag. Default (`inline_mode=false`) forwards `--subagent` to `/design`, preserving today's token-saving nested behavior. `--inline` (`inline_mode=true`) omits `--subagent`, so `/design`'s heavy phase runs in `/design`'s in-turn context (richer tool transcript, higher token cost). Execution-topology only — parent verbosity suppression remains gated on `SESSION_ENV_PATH`. Migration note: callers other than `/implement` that previously relied on `--session-env` alone for subagent dispatch must now pass `--subagent` explicitly. Closes #1036.

## [15.5.0] - 2026-05-04

### Changed

- `/implement` Step 2 dispatcher (`skills/implement/scripts/step2-implement.sh`) now defaults `--coder` to `codex` when the flag is omitted (was `claude`). Operators relying on the prior main-agent default should pass `--coder=claude` explicitly. The flag enum is unchanged; surface signatures (`SKILL.md` `argument-hint:`) are unchanged.
- `/implement` Step 2 dispatcher: when `--coder=cursor` is requested but Cursor is unhealthy or unavailable, the dispatcher now emits `STATUS=claude_fallback` and the orchestrator runs the main-agent code-edit path — symmetric to passing `--coder=claude`. The previous fail-closed `STATUS=bailed REASON=cursor-unhealthy` behavior (and the `cursor-unhealthy` bail token) is removed from the dispatcher's emitted enum. `skills/implement/scripts/test-step2-dispatch.sh` 26 assertions updated to expect the fallback envelope and a non-git default-coder=codex check; sibling contracts in `step2-implement.md`, `codex-manifest-schema.md`, and `SKILL.md` Step 2 dispatch / 2.2 / 2.4 updated accordingly. `README.md`, `SECURITY.md`, `docs/configuration-and-permissions.md`, `docs/external-reviewers.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, and `docs/linting.md` updated to reflect the new default and the cursor-fallback semantics (closes #1037).

## [15.4.9] - 2026-05-04

### Changed

- `.github/workflows/ci.yaml` — add `push: branches: [main]` trigger so the `actions/cache` entry for `~/.cache/pre-commit` populates under the default-branch scope. PRs on feature branches can read the default branch's cache but not each other's, so without this trigger every fresh PR paid the cold-install cost (~115s lint job) instead of the warm-cache cost (~32s). Also set `SKIP=agnix` on the `Run pre-commit linters` step because the dedicated `agnix` CI job covers the same lint; gitleaks remains in the lint step (its `--no-git` working-tree scan is documented in `SECURITY.md` as complementary to the dedicated `gitleaks` job's history scan, not redundant). `docs/linting.md` updated to describe the split (closes #1034).

## [15.4.7] - 2026-05-03

### Changed

- Rebalance test-harnesses matrix shards in CI so shard run times are more even. `test-validate-citations` (the wall-clock floor) now shares shard 6 with the partition-invariant guard `test-harness-shards-coverage`; previous shard 1/2 contents are redistributed across the lighter shards. Adds a "Last manual rebalance: 2026-05-03 (issue #1028)" audit-trail line in `docs/linting.md` "Refreshing harness shard balance" per the Makefile-shard-layout lockstep contract in `scripts/test-harness-shards-coverage.md` (closes #1028).

## [15.4.6] - 2026-05-03

### Changed

- `scripts/check-reviewers.sh` replaces the prior initial-probe + retry-once block with a 3-attempt loop that sleeps 10s between attempts. Each round only re-probes tools that are still unhealthy; healthy tools settle and stay healthy. Worst-case probe duration when both tools stay unresponsive across all 3 attempts rises from ~240s to ~380s — documented in `scripts/check-reviewers.md` so callers with hard wallclock budgets can plan around it.
- `skills/implement/SKILL.md` Step 1 normal-mode adds a both-externals-down inline-plan branch: when `codex_available=false AND cursor_available=false AND design_only=false`, `/implement` skips `/design` entirely and produces an inline plan in the main agent (mirrors the quick-mode path), avoiding the token-expensive 8-Claude-subagent fallback that has no independent-perspective value when no external can produce one. With `--design-only` the orchestrator instead bails to cleanup with `STALL_TRACKING=true` because `--design-only`'s contract requires external-backed plan-review (closes #1024).

## [15.4.5] - 2026-05-03

### Fixed

- `scripts/test-eval-research-baseline-flag.md` — drop the spurious `.scale` clause from the documented jq stub expression so the contract doc matches the actual `validate_baseline_json` predicate in `scripts/eval-research.sh` (`.version and (.entries | type == "array")`) and the harness header in `scripts/test-eval-research-baseline-flag.sh` (closes #1025).

## [15.4.4] - 2026-05-03

### Changed

- `/implement` Step 2 dispatcher (`skills/implement/scripts/step2-implement.sh`) writes `step2-spawn-coder.txt` under `$IMPLEMENT_TMPDIR` on the first external-implementer invocation and bails fail-closed with `STATUS=bailed REASON=coder-mismatch-tmpdir-reuse TOOL=<current>` on any subsequent invocation whose `--coder` differs. The guard runs before the shared baseline files (`step2-baseline.txt`, `step2-spawn-branch.txt`, `step2-plugin-json-baseline.txt`) and the per-tool `${TOOL_TAG}-resume-count.txt` are touched, closing the cross-coder tmpdir-reuse footgun where a partial `--coder=codex` run reused for `--coder=cursor` (or vice versa) would desynchronize shared baselines and per-tool counters. The `claude_fallback` early-return path is unchanged (writes no baselines, no sentinel). Sibling contract `skills/implement/scripts/step2-implement.md`, the dispatcher bail-token list in `skills/implement/references/codex-manifest-schema.md`, and `docs/linting.md` are updated; `skills/implement/scripts/test-step2-dispatch.sh` grows from 22 to 26 assertions covering first-invocation sentinel write and second-invocation mismatch bail with no per-tool state leak (closes #1018).

## [15.4.3] - 2026-05-03

### Changed

- Replace stale `Makefile:148` and `Makefile:157-163` line-number citations with target-name anchors (`test-eval-set-structure` target). Affects `Makefile`, `scripts/test-eval-research-baseline-flag.md`, and `scripts/test-eval-research-baseline-flag.sh`. Pre-existing hygiene fix unrelated to issue #1016 (closes #1021).

## [15.4.2] - 2026-05-03

### Changed

- Split the CI `test-harnesses` job into a six-cell parallel matrix (`test-harnesses (1)` through `test-harnesses (6)`), with per-shard prerequisite lists balanced via LPT bin-packing on measured per-harness timings. New `scripts/test-harness-shards-coverage.{sh,md}` partition guard runs FIRST on shard-6 and validates set-equality between recipe-target inventory and union of shard prereqs, single-physical-line shard rules, lowercase-hyphenated naming (`^test-[a-z0-9-]+$` — rejects `test_foo:`, `test-foo_bar:`, etc.), `.PHONY` membership of every shard-bound `test-*` target including the guard itself, umbrella membership, and self-reference-as-first-prereq on shard-6. Carve-out registry centralized via the `CARVE_OUTS` shell variable and shared `is_carve_out()` awk function. `--self-test` mode covers happy-path, missing-target, orphan-in-shards, duplicate-across-shards, backslash-continuation, naming violations (both `test_foo:` and `test-foo_bar:`), self-reference-not-first, umbrella-missing-shard, umbrella-extra-shard, missing-phony, and missing-phony-self fixtures. `lint:` continues to depend on the `test-harnesses` umbrella; `make test-harnesses-N` invocations remain available locally. `docs/linting.md` adds the CI sharding section, branch-protection migration checklist, manual rebalance procedure, and a lockstep edit note for shard-count changes. Sibling-contract sweep updates references in `scripts/test-ci-wait-exit-trap.md`, `skills/research/scripts/test-validate-citations.md`, `skills/issue/scripts/test-body-file-title.md`, `skills/issue/scripts/test-intra-batch-deps.md`, and `skills/research/scripts/test-render-findings-batch.md` to the new shard wiring (closes #1016).

## [15.4.1] - 2026-05-03

### Changed

- `/implement` NEVER list gains item #9 forbidding orchestrator `ScheduleWakeup` calls anywhere in Steps 0–18, with rationale citing `step2-implement.sh` (foreground synchronous) and `ci-wait.sh` (foreground synchronous, 31-min timeout) and the `/loop`-continuation symptom (a non-sentinel `prompt` re-fires on wakeup as a `/loop` input, perpetuating a chain that survived past Step 18 and triggered spurious post-completion follow-up offers like `/review --diff` against an empty diff). `AGENTS.md` anti-polling rule extended to cover `ScheduleWakeup`; `skills/implement/scripts/step2-implement.md` colocates a one-line top reminder cross-referencing NEVER #9. Prose-only fix; no shell script changes. The pinned literal `Don't spawn a Monitor or a Bash` in `AGENTS.md` is preserved so `scripts/test-implement-anti-polling-rule.sh` continues to pass.

## [15.4.0] - 2026-05-03

### Added

- `/implement --coder=cursor`: third implementer choice alongside `claude` (default) and `codex`. New `scripts/launch-cursor-implement.sh` wrapper (parallel to `launch-codex-implement.sh`, same KV stdout grammar) spawns a non-interactive `cursor-agent` subprocess driven by the new `agents/cursor-implementer.md` system prompt; the implementer writes the same `manifest.json` schema as Codex (note added to `skills/implement/references/codex-manifest-schema.md`). `skills/implement/scripts/step2-implement.sh` gains a `--coder cursor` branch that fails fast with a clear error when `CURSOR_HEALTHY=false` (no silent fallback). `skills/implement/scripts/test-step2-dispatch.sh` covers the new routing branch; new `skills/implement/scripts/test-cursor-implementer.sh` exercises the launcher offline with a mocked cursor-agent and is gated on `CURSOR_HEALTHY=true` for the real-cursor smoke variant. Docs (`README.md`, `docs/workflow-lifecycle.md`, `docs/configuration-and-permissions.md`) updated to show `--coder={claude,codex,cursor}` and note that `LARCH_CURSOR_MODEL` (already used by sketch/review) now also drives the implementer (closes #993).

## [15.3.1] - 2026-05-03

### Changed

- Split CI's `test-harnesses` gate into a six-cell matrix (`test-harnesses (1)` through `test-harnesses (6)`) backed by Makefile shard targets balanced from measured harness timings. Local `make test-harnesses` remains the umbrella target, now aggregating the six shard targets plus the new `test-harness-shards-coverage` partition guard. Docs cover branch-protection migration, shard refresh, and the ordering change.
- `/implement` Step 1 (normal mode) carries a new "Post-/design boundary checkpoint" reminder enumerating the in-step continuations permitted between `/design`'s return and the 1.r/Step-2 breadcrumb (📥 manifest-loaded breadcrumb, Cross-Skill Health Update, `BRANCH_NAME` capture, anchor-section writes — in that order); the reminder explicitly classifies "design phase complete," "returning control," and "handing off" as halts in disguise (NEVER #7 family). `skills/design/scripts/read-design-manifest.sh` gains an opt-in `--emit-load-breadcrumb` flag that prints `📥 1: design plan — manifest loaded (plan=<basename>)` as the trailing line of stdout on the success path (suppressed on rejection); the post-`/design` re-run in `/implement` Step 1 forwards this flag so the orchestrator's first mid-Step-1 visible line is unambiguously mid-step. New `scripts/test-implement-post-design-boundary.sh` regression harness pins the SKILL.md reminder phrasing, both breadcrumb literals, the NEVER #7 reference, the reader flag handler, the `plan=<basename>` form (rejecting the legacy `PLAN_FILE=<basename>` form which would collide at the KV-namespace level), and a stdout-shape integration test asserting the breadcrumb is the LAST line on success and is suppressed on the missing-manifest failure path. Wired into the Makefile and `agent-lint.toml` exclude list (closes #1014).

## [15.3.0] - 2026-05-03

### Added

- `/fix-issue` accepts an optional `--auto` flag and forwards bare `--auto` to the delegated `/implement` run on PR paths (both SIMPLE and HARD bullets) when set; default behavior is unchanged when omitted. Updates `argument-hint`, the Flags section, the positional-argument flag-strip list, the Step 5a SIMPLE / HARD invocation bullets, the bail-detection harness (assertions a7 / a8) and its sibling contract, plus README / `docs/skills.md` / `docs/workflow-lifecycle.md`.

### Changed

- Reverts #1010 (parallel `make test-harnesses` runner via `scripts/test-harnesses.sh`) due to a Broken-pipe race surfacing intermittently in CI. Restores the serial `test-harnesses` Makefile target and removes the meta-harness `test-test-harnesses`. Revisit parallelization after the race is diagnosed.

## [15.2.3] - 2026-05-03

### Changed

- `AGENTS.md` anti-polling rule extended to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job, in addition to the existing Monitor prohibition. Inline reminders added at `skills/implement/SKILL.md` Step 5.3-rounds1to3 and Step 5.3-generic launch sites pointing to `collect-agent-results.sh` as the wait point. New regression harness `scripts/test-implement-anti-polling-rule.sh` pins both the AGENTS.md literals and per-Step-5.3-site reminder presence (heading-bounded extraction, not a global count). Closes #1011.

## [15.2.1] - 2026-05-03

### Changed

- `scripts/test-quick-mode-docs-sync.sh` tightened to detect rounds-1-3 quick-mode topology drift: adds three positive markers (`rounds 1-3`, `5 Cursor specialists`, `generic Codex`) encoding the multi-lane rounds-1-3 vs rounds-4+ contract; refactors marker storage into a `POS_MARKERS` array; adds `docs/skills.md` to the `PUBLIC_DOCS` target list. Self-test fixtures extended so the new markers are exercised in good and bad fixtures. Sibling `scripts/test-quick-mode-docs-sync.md` and `docs/linting.md` updated to match. (Closes #1002.)

## [15.2.0] - 2026-05-03

### Added

- File-backed `/design` → `/implement` handoff. New `skills/design/scripts/write-design-manifest.sh` exports plan / plan-review tally / contested-decisions / OOS / rejected findings / accepted findings (and optional architecture diagram) into `$IMPLEMENT_TMPDIR/design-export/` with a KV manifest at `manifest.env`; `skills/design/scripts/read-design-manifest.sh` parses + verifies the manifest in `/implement` Step 1 (no `source`/`eval`; rejects malformed keys, control characters / NUL, non-absolute paths, symlinks, paths outside `design-export/`, and duplicate load-bearing keys with `ERROR=duplicate-key:<KEY>`; emits `MANIFEST_OK=true` only after every path validation succeeds; ERR-trapped to preserve the "always exits 0 with envelope" contract). The writer canonicalizes both tmpdirs, rejects symlinked source artifacts (and any source resolving outside `$DESIGN_TMPDIR`), strips C0/DEL controls from `SESSION_ID`, and stages all artifacts to a fresh sibling tmpdir + poisons the live manifest before atomic per-file `mv` to eliminate mixed-vintage exports on partial-rerun failure.
- `/implement` Step 1 manifest reuse: when a session-bound, valid manifest already exists (matched by `SESSION_ID` equality alone — `TIMESTAMP` is informational), `/implement` reuses it and hydrates ALL file variables (`PLAN_FILE`, `PLAN_REVIEW_TALLY_FILE`, `CONTESTED_CRITERIA_FILE`, `OOS_FILE`, `REJECTED_FINDINGS_FILE`, `ACCEPTED_PLAN_FINDINGS_FILE`, and the optional staged `architecture-diagram.md`) without re-spawning `/design`.
- `skills/design/references/heavy-worker.md`: subagent runbook that the nested `/design` heavy phase delegates to (sketches + plan + plan-review under an isolated Agent-tool context). The main `/implement` context receives only `DESIGN_HEAVY=complete` (or `failed REASON=<token>`), saving ≈100–300K tokens per nested run. Required Reads use `${CLAUDE_PLUGIN_ROOT}/…` so the subagent loads from the shipped plugin tree regardless of consumer-repo CWD.
- New regression harness `skills/design/scripts/test-design-manifest.sh` (wired into `make lint` via `test-design-manifest`) covers writer atomic output (glob-checked stale-tmp), missing required artifacts, safe KV grammar, source/eval injection resistance, path traversal, symlink rejection (source AND destination), control-character rejection, malformed-key rejection, duplicate load-bearing key rejection, manifest-not-found and malformed-line error paths, source-symlink rejection, and relative-`--implement-tmpdir` canonicalization.
- `scripts/test-quick-mode-docs-sync.sh` extended with a `--design-only` literal-anchor block: `README.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, and `skills/implement/SKILL.md` MUST contain the `--design-only` substring or CI fails.
- `/fix-issue --coder=<value>` pass-through flag. Forwarded verbatim to the delegated `/implement` run on PR paths (both SIMPLE and HARD bullets); `/fix-issue` performs no validation — `/implement`'s own `--coder` flag is the validating boundary.

### Changed

- `/implement` Step 0 `uuidgen` snippet is now a self-contained Bash block with a `command -v uuidgen` guard + basename fallback so hosts without `uuidgen` no longer exit non-zero before the prose-only fallback ever runs.
- `/implement` Step 18 PR-reminder block now branches on `DESIGN_ONLY_DONE=true` first so design-only runs no longer claim a draft or unmerged PR exists.
- `/implement` Step 1 anchor-comment template clarification: `PLAN_FILE` is the plan body; the `## Implementation Plan` / `## Goal` / `## Test plan` headings are fragment-level wrapping, not requirements on the source file.
- `/design` Step 5 cleanup now gates `cleanup-tmpdir.sh` on a `MANIFEST_EXPORT_OK` flag so a manifest-export failure preserves `$DESIGN_TMPDIR` for parent inspection. `/design` `Finalize Plan Review` bullets 1 + 3 now branch on `SESSION_ENV_PATH` so nested runs no longer push voted-in findings + revised plan back into the parent context.
- Anchor-comment template `Step 9a.1 OOS pipeline` documents that any of the three `oos-accepted-*.md` artifact files MAY be missing — missing-file is treated as empty (no entries from that phase), not as an error.

### Fixed

- `/implement` Step 2 dispatcher (`skills/implement/scripts/step2-implement.sh`) emitted `STATUS=bailed REASON=protected-path-modified` on every successful Codex `complete` manifest. Root cause: the path-normalization check used a `*$'\0'*` glob, which collapses to `**` in bash (since `$'\0'` is empty in bash strings) and matches every non-empty path. Drop the dead NUL subexpression and add a jq-layer NUL guard that rejects any manifest where a path contains a NUL byte, closing the `read -r` truncation bypass. `--coder=codex` is functional again.

### Internal / docs

- `agent-lint.toml` comment block for `test-quick-mode-docs-sync.sh` mentions the new `--design-only` literal sync surface.
- `skills/design/scripts/{read,write}-design-manifest.md` siblings document the intentional `CONTESTED_CRITERIA_FILE` → `contested-decisions.md` naming asymmetry (stable for `MANIFEST_VERSION=1`).
- `skills/shared/subskill-invocation.md` sentinel bullet describes the full manifest-backed handoff (plan + tally + OOS + rejected + accepted-plan + optional architecture diagram), not just one path.
- `scripts/test-implement-structure.sh` banner + sibling `.md` updated to "20 live assertions (assertion 5 retired)".
- `scripts/test-design-structure.sh` grep literal updated for the heavy-worker.md `${CLAUDE_PLUGIN_ROOT}/…` path-prefix change.
- `.gitignore` adds `.claude/scheduled_tasks.lock` (transient ScheduleWakeup bookkeeping).

## [15.1.3] - 2026-05-03

### Changed

- `/implement` quick mode: rounds 1-3 of the code review loop now spawn the 5 Cursor specialists in parallel plus a generic Codex reviewer (specialist slot fallback Cursor → Codex → Claude; generic slot fallback Codex → Cursor → Claude). Previously only round 1 spawned the 5 specialists; rounds 2+ used a single generic reviewer. Rounds 4-7 are unchanged (single generic Cursor → Codex → Claude per round). Public docs (README, `docs/review-agents.md`, `docs/workflow-lifecycle.md`, `docs/skills.md`) updated to match.

## [15.1.2] - 2026-05-03

### Changed

- `/implement` Step 2: post-Codex commit responsibility moves from Codex into the dispatcher (`skills/implement/scripts/step2-implement.sh`). Codex now leaves working-tree edits + a manifest with `commit_message`; the dispatcher pipes `commit_message` through `scripts/redact-secrets.sh` and runs `git add -A && git commit -F …` with no Claude-side diff or subject verification. Eliminates the `git-index-write-blocked` failure class (Codex stays inside `workspace-write` sandbox) and collapses the prior "Codex commits + dispatcher cross-checks" trust boundary. Drops the now-tautological `commit-subject-mismatch` / `manifest-diff-mismatch` / `no-commit-since-baseline` / `dirty-tree-after-codex` bail tokens; adds `commit-failed` for the new git-commit error path. `manifest.files_touched` is now advisory documentation. Closes #992.

## [15.1.1] - 2026-05-03

### Added

- `AGENTS.md` Conventions: bullet forbidding spawning a Monitor task to wait for a Bash `run_in_background` job to finish (the Bash task-completion notification already covers that case).

## [15.1.0] - 2026-05-03

### Added

- `/implement` (and aliases `/im`, `/imaq`) now accept `--coder={claude,codex}` to select the Step 2 implementer. Default is `claude` (main agent in main context — restores pre-Codex behavior). `--coder=codex` spawns the Codex implementer via `skills/implement/scripts/step2-implement.sh`. `--coder=cursor` is reserved for #993 and currently rejected at parse time.

### Changed

- `skills/implement/scripts/step2-implement.sh` now branches on `--coder` instead of `--codex-available`. The legacy `--codex-available true|false` flag is still accepted by the dispatcher for one release with a stderr deprecation warning that maps `true` to `coder=codex` and `false` to `coder=claude`. Passing both `--coder` and `--codex-available` exits 2 with a mutex error. Test harness `test-step2-dispatch.sh` extended to 15 assertions covering the new flag, mutex, cursor rejection, and the deprecation path. Closes #995.

## [15.0.3] - 2026-05-03

### Changed

- `skills/implement/SKILL.md` Step 0.5 Branch 3 (PR-body recovery) now invokes `scripts/extract-closes-issue-from-pr.sh` instead of inlining the `gh pr view --json body --jq | grep -oE 'Closes #[0-9]+' | head -1 | grep -oE '[0-9]+'` pipeline. The new helper script and its sibling contract `scripts/extract-closes-issue-from-pr.md` follow the per-script-contract convention in `AGENTS.md`. Behavior is unchanged: empty stdout when no PR exists on the current branch or the PR body has no `Closes #<N>` line; otherwise the matched issue number. Closes #985.

## [15.0.2] - 2026-05-03

### Fixed

- `scripts/launch-codex-implement.sh` now passes the composed prompt to `codex exec` after a `--` end-of-options separator. The agent prompt is built by `cat`ting `agents/codex-implementer.md`, which begins with YAML frontmatter (`---`); codex-cli 0.125.0 interpreted the leading `---` as a flag delimiter and aborted with `unexpected argument`, blocking every `/implement` Step 2 Codex spawn. Operators had to fall back to `--codex-available false` (Claude implementer) to make progress. The sibling `scripts/launch-codex-implement.md` now documents the `--` separator as a load-bearing invariant. `scripts/launch-review.sh --tool codex` is unaffected because `render-specialist-prompt.sh` strips frontmatter from reviewer prompts. Closes #991.

## [15.0.1] - 2026-05-03

### Fixed

- `/implement` Step 2 dispatcher (`step2-implement.sh`) now resolves the consumer git repo via `git rev-parse --show-toplevel` instead of `SCRIPT_DIR/../../..`. The old computation pointed at the installed plugin cache (which has no `.git`), causing `git -C "$REPO_ROOT" rev-parse HEAD` to abort under `set -euo pipefail` with no KV envelope; operators had to re-invoke with `--codex-available false` to get `STATUS=claude_fallback`, which violated Step 2's mandatory-Codex-spawn invariant. Plugin asset paths (agent prompt, launcher, redactor) now use a separate `PLUGIN_ROOT` derived from the script location. Both root computations live below the `--codex-available false` early-exit so the fallback path stays git-free. Test harness extended (10/10) to assert exit-2 outside a git working tree.

## [15.0.0] - 2026-05-03

### Removed

- `--debug` flag from `/design`, `/implement`, `/fix-issue`, `/create-skill`, `/simplify-skill`, `/compress-skill`, and `/umbrella` (BREAKING). The flag and its supporting `debug_mode` / `DEBUG` machinery have been deleted from each skill's argument hint, parser, and Verbosity Control prose. The compact / status-table output that was the default when `--debug` was absent is now the only behavior. Callers that pass `--debug` to a strict-parsing skill (`/create-skill`, `/umbrella`) will now hit the unknown-flag error path; the parse-args harnesses (`scripts/test-parse-args.sh`, `skills/umbrella/scripts/test-umbrella-parse-args.sh`) and the `test-implement-rebase-macro.sh` regression guard were updated accordingly.

## [14.1.1] - 2026-05-02

### Fixed

- Makefile `.PHONY` declaration and `test-harnesses` prerequisite list contained the concatenated token `test-subskill-anchorstest-tracking-issue-write` (missing whitespace separator). Split into two separate tokens `test-subskill-anchors` and `test-tracking-issue-write` so both harnesses are properly wired as prerequisites of the aggregate `test-harnesses` target (closes #977).

## [14.1.0] - 2026-05-02

### Added

- Re-introduce code-writing-by-spawned-Codex at `/implement` Step 2 with mandatory spawn when Codex is healthy. Adds a single dispatcher (`skills/implement/scripts/step2-implement.sh`) that branches on `codex_available`, spawns Codex via `scripts/launch-codex-implement.sh`, validates a JSON manifest mechanically (path normalization, baseline-rooted `git diff` set-equality, branch / `.claude-plugin/plugin.json` / submodule unchanged checks, HEAD-subject-equals-manifest check, working-tree-clean check on `status=complete`), and emits a deterministic KV envelope. Codex's full transcript stays on disk; Claude reads only the validated, sanitized manifest — Steps 4 / 8a / 9a / 9a.1 are manifest-driven on the Codex path. On `status=needs_qa`, the dispatcher surfaces `qa-pending.json` to the orchestrator, which collects answers via `AskUserQuestion` and re-invokes the dispatcher with `--answers`; Codex resumes from prior partial work on the branch (resume cycles capped at 5)
- New `agents/codex-implementer.md` system prompt loaded as Codex's `--agent-prompt` body, with hard guards (no `git reset --hard`, no edits to `.claude-plugin/plugin.json`, no submodule edits, no branch switches, atomic manifest writes, question-text sanitization guidance)
- New canonical manifest schema reference at `skills/implement/references/codex-manifest-schema.md` documenting the JSON shape, per-status required keys, validation rules, atomic-write rule, and bail-reason token enumeration (including dispatcher-emitted `commit-subject-mismatch`, `qa-pending-missing`, `redactor-not-executable`, `manifest-missing`, `no-commit-since-baseline` tokens)
- New offline regression harness `skills/implement/scripts/test-step2-dispatch.sh` (8 assertions covering claude-fallback branch, argument validation, resume-counter cap, corrupt-counter bail) wired into `make test-step2-dispatch`
- `scripts/test-implement-structure.sh` extended with a 19th assertion pinning the Step 2 dispatcher path, launcher executability, and Codex-implementer agent-prompt presence; MANDATORY-occurrences floor raised from 5 to 6 (added `codex-manifest-schema.md` to the expected-references set)

## [14.0.0] - 2026-05-02

### Removed (breaking)

- `/research`: removed `--plan`, `--interactive`, `--adjudicate`, `--scale` (with `quick` and `standard` modes and Step 2.5 dialectic adjudication), `--token-budget` (with budget-gate machinery), `--keep-sidecar`, and `--debug` flags. Only `--no-issue` and the positional `<research question>` remain.
- `/review`: removed `--debug` and verbosity-control machinery; status-table mode is now the permanent default.
- Removed `skills/research/scripts/classify-research-scale.sh`, `test-standard-angle-prompts.sh`, dialectic ballot scripts, deep-lane-status renderer, `quick-vote-state.sh`, `quick-disclaimer*.txt` data files, and the `adjudication-phase.md` reference.

### Changed

- `/research`: planner pre-pass and TTY interactive review checkpoint are now always-on (non-TTY falls back to non-interactive passthrough). Validation panel is fixed at 3 reviewers (Claude Code Reviewer + Codex + Cursor). Research lanes are Codex-first across 4 angles (architecture / edge cases / external comparisons / security) with per-lane Claude `Agent` fallback; Cursor is no longer used for research lanes (still in validation panel). Token telemetry remains observability-only — budget enforcement is removed. Step 4 cleanup unconditionally wipes the tmpdir sidecar.

## [13.1.1] - 2026-05-02

### Fixed

- Replace prompt-only `CHANGELOG.md` presence check at `/implement` Step 8a with a scripted probe (`scripts/check-changelog-present.sh`); the probe's `CHANGELOG_PRESENT=true|false` output is now the authoritative branch decision and is echoed verbatim in the skip breadcrumb so a false skip is visible in the transcript

## [13.0.1] - 2026-05-02

### Fixed

- Strengthen anti-halt continuation reminders across `/implement`, `/review`, and `/design` to prevent orchestrator from stopping mid-run at step boundaries, skip breadcrumbs, and visible outputs
- Fix `/review` round-skipping bug: Step 3f now explicitly mandates re-launching reviewers after fixes (convergence requires 0 new findings, not just "all fixes applied")
- Fix `/review` Step 3d mode-gating: continuation after round summary now correctly distinguishes diff mode (→ Step 3e) from description mode (→ Step 4)
- Add `/design` to anti-halt test harness (`BANNER_ONLY_ORCHESTRATORS`)
- Update canonical anti-halt rule in `skills/shared/subskill-invocation.md` to cover Bash completions and visible outputs (not just child Skill returns)

## [12.5.0] - 2026-05-01

### Added

- `/upgrade-larch` skill — automates upgrading the larch plugin to the latest version by removing and re-adding the marketplace, then reinstalling. Includes failure recovery guidance and a local-dev warning.

### Changed

- `docs/installation-and-setup.md` — removed "Install a specific version" section (version pinning caused downgrade bugs), added Upgrade section with `/upgrade-larch` instructions

## [12.4.8] - 2026-05-01

### Changed

- `skills/implement/SKILL.md` Step 8 (Version Bump) — added a post-return anti-halt continuation reminder right after sub-step 3b, mirroring the existing post-`/design` and post-`/review` reminder patterns. Reduces the probability of a non-deterministic halt after `/bump-version` returns successfully (closes #946).

## [12.4.7] - 2026-04-30

### Changed

- `.github/workflows/release-tag.yaml` — auto-created releases are now marked as pre-release (`--prerelease`) in addition to `--latest=false`
- `scripts/promote-release.sh` — promotion now clears the pre-release flag (`--prerelease=false`) alongside setting latest; also handles the "already latest but still pre-release" edge case idempotently

## [12.4.6] - 2026-04-30

### Added

- `scripts/promote-release.sh` — operator utility to promote a GitHub Release to "Latest" by semver version. Takes mandatory `X.Y.Z` argument, validates format, checks release existence, and promotes via `gh release edit --latest`. Idempotent (exits 0 if already latest).

## [12.4.5] - 2026-04-30

### Changed

- `.github/workflows/release-tag.yaml` — auto-creates GitHub Releases (not just tags) with `--latest=false` and CHANGELOG body extraction. Includes idempotent recovery for tag-exists-but-no-release state.
- `docs/installation-and-setup.md` — updated install instructions to reference the latest stable release; added section for pinning a specific version via `@vX.Y.Z` syntax.

## [12.4.4] - 2026-04-30

### Added

- `.github/workflows/release-tag.yaml` — new GitHub Actions workflow that auto-creates a `v<semver>` git tag on every push to main, derived from `.claude-plugin/plugin.json` version. Includes strict semver validation, exact ref matching, and TOCTOU race handling for concurrent runs.

## [12.4.3] - 2026-04-30

### Fixed

- Update stale "3-reviewer" references for `/design` plan-review panel to reflect the current 6-reviewer composition (1 Claude + 1 Codex generic + 4 Cursor archetypes) across README.md, docs/review-agents.md, docs/agents.md, docs/collaborative-sketches.md, docs/workflow-lifecycle.md, and docs/skills.md.

## [12.4.1] - 2026-04-30

### Changed

- `/design` Step 3 plan reviewer Claude subagent and plan Voter 1 Claude subagent now use `model: "opus"` (defaults to Claude 4.7) with high effort. Fallback reviewers (when Codex/Cursor unavailable) remain on `model: "sonnet"`.

## [12.4.0] - 2026-04-30

### Added

- `/research` Step 3.5 auto-archives the full research report (question, results, token spend) as a GitHub issue after each successful run via `/issue` single mode. `--no-issue` flag (default off) skips this step.
- Transitive callers (`scripts/eval-research.sh`, `/skill-evolver`) pass `--no-issue` to suppress auto-issue when `/research` is invoked as an intermediate step.
- `SECURITY.md` documents the auto-issue publication surface, `redact-secrets.sh` backstop, residual risk, and `--no-issue` escape hatch.

## [12.3.0] - 2026-04-30

### Changed

- `/design` sketch phase expanded from 5 agents (1 Claude + 2 Cursor + 2 Codex) to 9 in regular mode (1 Claude + 4 Cursor + 4 Codex, one per personality per tool) and 3 in quick mode (1 Claude + 1 Cursor-Generic + 1 Codex-Generic).
- Added `--quick` flag to `/design` for a lightweight 3-agent sketch phase.

## [12.2.0] - 2026-04-30

### Changed

- `/implement` Step 2 implementation is now always performed by the main Claude agent using Edit/Write tools directly — removed Codex coding delegation branch (one-shot `codex exec --full-auto` invocation, pre-launch baseline snapshot, and fallback recovery logic).
- Updated trust model and external agent documentation to reflect that Codex/Cursor participate only as reviewers, sketch authors, and voters — not as implementors.

## [12.0.9] - 2026-04-29

### Added

- `/implement` Step 2 Codex coding delegation: one-shot `codex exec --full-auto` with `gpt-5.5` model and high reasoning effort, monitored via `run-external-agent.sh` with sentinel-based collection and automatic fallback to inline implementation.
- Pre-launch baseline snapshot in Step 2 for accurate diff attribution in resumed sessions.
- `--default-model` flag in `agent-model-args.sh` for per-call-site model override.

### Changed

- Renamed `run-external-reviewer.sh` → `run-external-agent.sh`, `collect-reviewer-results.sh` → `collect-agent-results.sh`, `reviewer-model-args.sh` → `agent-model-args.sh` to reflect broader agent usage beyond reviews.
- Codex default model changed from empty (Codex CLI default) to `gpt-5.5` across all work invocations.
- Health probes in `check-reviewers.sh` bypass the `gpt-5.5` default to test basic Codex availability without model-specific coupling.
- Progress strings in `run-external-agent.sh` updated from "review" to "agent" terminology.

## [12.0.8] - 2026-04-28

### Fixed

- `find-lock-issue.sh` explicit-target mode: `umbrella-handler.sh detect` non-zero exit is now fatal — emits `ELIGIBLE=false` with propagated error and exits 2, instead of silently falling through to the ordinary-issue path.

### Added

- `test-find-lock-issue.sh` fixture 13: regression test for detect-failure-exits-2 with `VIEW_FAIL_BODY` stub mechanism that differentiates `gh issue view` calls by `--json` fields.

## [12.0.7] - 2026-04-28

### Fixed

- `get-issue-details.sh` — replaced `echo` with `printf '%s\n'` for issue body and comment body serialization to prevent corruption when bodies start with `-n` or `-e`.
- `get-issue-details.sh` — fixed empty-label fallback from `join(", ") // "none"` (jq `//` does not substitute for empty string) to explicit `if length == 0` check.

## [12.0.1] - 2026-04-28

### Removed

- Stale `loop-fix-issue` test harness exclusion entry from `agent-lint.toml` (leftover from `/loop-fix-issue` deletion in PR #879).

## [11.0.0] - 2026-04-28

### Removed

- `/loop-review` skill deleted entirely — SKILL.md, driver.sh, driver.md, diagram.svg, test harnesses, Makefile targets, settings entries, and all references across docs, shared skills, CI config, SECURITY.md, and agent-lint.toml. Closes #884.

## [7.17.61] - 2026-04-27

### Fixed

- `/issue` Step 4E/Step 5 — intra-batch dependency analysis no longer silently skipped when external CANDIDATES is empty. When `N_NON_MALFORMED >= 2`, Phase 2 runs for intra-batch dep reasoning regardless of Phase 1 results.
- `/issue` Step 4D — allocator exit-0 with empty CANDIDATES now correctly handles `N_NON_MALFORMED < 2` (jump to Step 6 with CREATE verdicts).

### Added

- `skills/issue/scripts/test-intra-batch-deps.sh` — 7-assertion structural regression harness pinning Step 4E/5 gating logic, conditional fetch skip, empty-CANDIDATES verdict guidance, no-external-refs validation rule, FETCH_STATUS scope narrowing, and old short-circuit removal.

## [7.17.60] - 2026-04-27

### Changed

- Reviewer subagents (`larch:code-reviewer`) in `/review`, `/design`, and `/implement` quick-mode now explicitly use `model: "sonnet"` for plan and code reviews. Judge/voter subagents retain the default model.

## [7.17.59] - 2026-04-27

### Added

- `LARCH_BUMP_FILES` env var — colon-separated list of bump files for `drop-bump-commit.sh` Guard 4, enabling consumer repos whose `/bump-version` touches files beyond `.claude-plugin/plugin.json` (e.g., `version.go`, `package.json`, `Cargo.toml`) to configure the allowed set.
- `scripts/test-drop-bump-commit.sh` — 16-case offline regression harness for `drop-bump-commit.sh` Guard 4, wired into `make test-harnesses`.
- `scripts/drop-bump-commit.md` — sibling contract document for `drop-bump-commit.sh`.

### Changed

- `scripts/drop-bump-commit.sh` Guard 4 — dual-path: exact equality when `LARCH_BUMP_FILES` unset (byte-identical default), membership check with `BUMP_FILE_FOUND` fail-closed gate when set. Empty-diff and CHANGELOG-only commits are rejected on both paths.
- `skills/implement/references/conflict-resolution.md` Phase 1 — `LARCH_BUMP_FILES` entries classified as trivial only for bump-commit conflicts (not feature-commit conflicts), preserving multi-purpose file changes during rebase.

## [7.17.57] - 2026-04-27

### Changed

- `/issue` now accepts `--body-file FILE` combined with a trailing positional argument — the trailing arg becomes the explicit title and the file content becomes the body. Previously rejected as mutually exclusive. Updated `/umbrella` SKILL.md Step 3B.3 and `render-umbrella-body.md` to reflect explicit-title semantics.

### Added

- `skills/issue/scripts/test-body-file-title.sh` — structural regression harness pinning the `--body-file` + trailing title two-source branching, `EXPLICIT_TITLE` variable, and backward-compatible derive-from-first-line path.

## [7.17.56] - 2026-04-27

### Fixed

- `docs/installation-and-setup.md` — updated the `### Claude` settings snippet to match actual `~/.claude/settings.json` values: effort level `high` (was `xhigh`), model `claude-opus-4-6` (was `opus`).

## [7.17.54] - 2026-04-27

### Added

- `scripts/git-force-push.md` — sibling contract document for `scripts/git-force-push.sh`, documenting the stdout contract (`BRANCH`, `PUSHED`, `STATUS`), exit codes, callers, dependencies, and edit-in-sync rules per the AGENTS.md "Per-script contracts live beside the script" convention.

## [7.17.51] - 2026-04-27

### Fixed

- `skills/research/scripts/test-validate-citations.sh` — added Test 21, a Linux-only fixture that exercises the no-`setsid` budget-exhaustion fail-soft branch in `validate-citations.sh:765`. Outer `setsid -w env -u __VC_SETSID_DONE PATH=$CLEAN_BIN` wraps the validator in its own POSIX session; a hermetic clean-bin built from symlinks (omitting `setsid`, including `uname` returning `Linux`) makes `command -v setsid` fail inside the validator so the no-setsid branch is the only path taken. Hung fake-curl honoring `--max-time` (parses both `--max-time N` and `--max-time=N`) plus `--budget-seconds 1` drives the per-fetch-timeout window; assertions cover exit 0, sidecar produced, `UNKNOWN`/`timeout` rows for both URLs, and zero orphan fake-curl PIDs after kill loop. Demonstrably fails if the `__VC_SETSID_DONE` marker gate at `validate-citations.sh:765` is reverted to unconditional `kill -- -$$` (validator gets SIGTERM under outer setsid → exit 143). Test 21 runs on current Ubuntu CI; complements Test 20 (Darwin-only, exercised on developer macOS). Test 20 skip line rephrased to `"skip: Darwin-only (Linux no-setsid path covered by Test 21)"`.
- `skills/research/scripts/test-validate-citations.md`, `skills/research/scripts/validate-citations.md`, `skills/research/references/citation-validation-phase.md` — sibling-contract / phase-doc updates document Test 21's coverage of the Linux no-setsid path and replace the previous "Linux runners skip and rely on CI" wording with explicit Test 20 / Test 21 attribution. Closes #849.

## [7.17.50] - 2026-04-27

### Changed

- `skills/fix-issue/scripts/umbrella-handler.sh` `child_eligible` — replaced the native-only `child_native_blockers` call with the full `all_open_blockers` (native + prose) check from `blocker-helpers.sh`. The native-first short-circuit inside `all_open_blockers` keeps the typical case at one `gh api` call per child. Pre-fix, `pick-child` returned the first native-eligible child even when that child carried a prose blocker; the post-pick defense-in-depth `all_open_blockers` re-check in `find-lock-issue.sh handle_umbrella` then exited 5 with no fallback to ready siblings, stalling the umbrella until the prose blocker resolved. Post-fix, `pick-child` walks past prose-blocked siblings to the next ready child. The post-pick re-check is preserved as a defense-in-depth guard (now redundant in the common path rather than load-bearing for sibling iteration).
- `skills/fix-issue/scripts/blocker-helpers.sh` (new sourced library) — extracted the canonical `native_open_blockers`, `prose_open_blockers`, and `all_open_blockers` from `find-lock-issue.sh` so both `find-lock-issue.sh` and `umbrella-handler.sh` apply the same native+prose dependency semantics. Permissions `0644` (sourced-only convention). Both callers wrap their `source` call with explicit failure handling so the documented `KEY=VALUE` stdout contract is preserved on load failure.
- `skills/fix-issue/scripts/find-lock-issue.sh` — removed the inline `native_open_blockers` / `prose_open_blockers` / `all_open_blockers` definitions in favor of sourcing `blocker-helpers.sh` after `REPO` is resolved. Behavior unchanged.
- `skills/fix-issue/scripts/test-umbrella-handler.sh` — extended the `gh` stub to honor `--jq` filters via a shared `emit_json` helper (so per-child state lookups behind `child_eligible`'s prose path see the bare state value), added `ISSUE_<N>_VIEW_FAIL=true` injection for fail-open testing. Added Fixture 21 (positive prose-skip with STUB_LOG assertion that `pick-child` walked past the prose-blocked first child) and Fixture 22 (fail-open negative — prose state-lookup failure preserves eligibility).
- `skills/fix-issue/scripts/test-find-lock-issue.sh` — added Fixture 11 (e2e umbrella dispatch with prose-blocked first child + ready second child); extended `dispatch_issue_view` for per-issue state lookup with `--jq` filter handling; added stateful runtime comments via `RUNTIME_COMMENTS_DIR` so the lock-no-go post-check can find the just-posted IN PROGRESS comment by id; refactored the inline comment-posting into a proper `dispatch_issue_comment` function. Asserts the dispatched-child path AND the absence of `ISSUE_NUMBER=1101` (prose-blocked first child must NOT be the locked child) AND `RENAMED=true`.
- `skills/fix-issue/scripts/parse-prose-blockers.md`, `skills/fix-issue/scripts/umbrella-handler.md`, `skills/fix-issue/scripts/test-umbrella-handler.md`, `skills/fix-issue/scripts/test-find-lock-issue.md`, `skills/fix-issue/SKILL.md` — sibling contract docs updated to reflect the new `all_open_blockers` semantics inside `child_eligible`, the `blocker-helpers.sh` orchestration owner for prose parsing, the new fixtures, and a Known Limitations bullet documenting the `pick-child` API cost increase. `agent-lint.toml` updated to add `blocker-helpers.{sh,md}` to the exclude list (sourced-only library, mirrors the `parse-prose-blockers.{sh,md}` exclusion pattern). Closes #768.

## [7.17.49] - 2026-04-27

### Fixed

- `scripts/ci-wait.sh` — added optional `--output-file <path>` mode that publishes the 7 KV-line payload via atomic write (`<path>.tmp` then `mv -f`) and emits a numeric `<path>.done` sentinel on any trap-deliverable exit path (SIGTERM included). The EXIT trap captures `$?` first, calls `emit_output`, and writes `.done` only when `emit_output` succeeded — fail-closed if the publish step fails (no `.done`, consumers time out instead of reading stale state). Default mode (no `--output-file`) preserves the prior 7-KV-on-stdout contract verbatim. Mirrors the consumer contract (numeric exit code in `.done`) of `scripts/run-external-agent.sh:70`.
- `scripts/ci-wait.md` — sibling contract added per AGENTS.md per-script contracts rule. Documents the synchronous-only invocation contract (`ci-wait.sh` MUST NOT be invoked with `run_in_background: true`), default I/O contract, optional `--output-file` semantics (atomic publish, `emit_output`-gated `.done` sentinel, fail-closed publish), trusted-path discipline, SIGTERM-trappable vs SIGKILL-uncatchable distinction, test harness wiring, and the 6 invocation sites that must stay in sync.
- `skills/implement/SKILL.md` Step 10, Step 12a — added explicit synchronous-only guardrail prose paragraph after each `ci-wait.sh` Bash invocation block, documenting the leaked-polling-loop failure mode that occurs when the wrapper shell is signal-killed mid-poll while running in the background.
- `skills/implement/references/rebase-rebump-subprocedure.md` step 7 — added matching synchronous-only guardrail paragraph covering all five caller-kind branches that re-invoke `ci-wait.sh` (`step12_rebase`, `step12_phase4`, `step12_rebase_then_evaluate`, `step10_rebase`, `step10_rebase_then_evaluate`).
- `scripts/test-ci-wait-exit-trap.sh` — new regression harness with 3 sub-tests: (A) `--output-file` SIGTERM-mid-poll convergence using a stub `ci-status.sh` that touches a `loop-entered` ready signal; (B) default-mode (stdout) backward-compat asserting all 7 KV keys appear in order with no implicit file-mode side effects; (C) fail-closed regression using a read-only directory to force `mv -f` to fail and asserting `<path>.done` is absent (10/10 assertions pass).
- `scripts/test-implement-structure.sh` — added assertion 17 with scoped negative pin (awk-window adjacency check that fails if `run_in_background: true` appears within ±5 lines of `ci-wait.sh` references in `skills/implement/SKILL.md` or `skills/implement/references/rebase-rebump-subprocedure.md`, with whitelist for guardrail prose lines containing the literal `MUST be invoked synchronously`) plus positive pin requiring the literal in each affected file.
- `Makefile`, `agent-lint.toml`, `docs/linting.md` — wired the new test harness into `make test-ci-wait-exit-trap` and `test-harnesses`; excluded the new test fixtures from `agent-lint`. Closes #842.

## [7.17.48] - 2026-04-27

### Fixed

- `skills/umbrella/scripts/render-batch-input.sh` — added per-entry case-(f) guard rejecting any piece `body` whose lines begin with `###` followed by an ASCII space, with stable `ERROR=pieces.json entry <i> body contains line starting with '### '` stderr line + exit 1. Mechanical backstop for the producer-side prohibition documented in PR #848 / `/umbrella` SKILL.md Step 3B.1: without it, a body line with the `###`-plus-space prefix flowed verbatim into `batch-input.md` and was re-parsed by `/issue --input-file`'s line-based parser (`parse-input.sh` Path 3, generic mode) as a new-item boundary, silently splitting one piece into multiple parsed items with corrupted titles and broken `depends_on` index alignment.
- `skills/umbrella/scripts/test-render-batch-input.sh` — added `assert_invalid_body` harness coverage (mid-body and body-start positions, line-anchored stderr assertion via `grep -qxF`) plus four `assert_valid_baseline_with_body` negative baselines (`##` two-hash, `####` four-hash, `###X` no-separator, mid-line `###` prefix) confirming the guard's match grammar is intentionally narrow. 16/16 tests pass.
- `skills/umbrella/scripts/render-batch-input.md` — documented case-(f) alongside cases (a)-(e) in the Test coverage paragraph; revised the Single-line stdout free-text fields paragraph (`body` is no longer fully exempt); added a Conservative-rejection note covering both the bare-heading false positive (Path 3 requires non-empty title capture) and the `### OOS_<N>:` absorption case (`parse-input.sh` OOS-before-plain ordering with #132 generic-body absorption guard) as accepted intentional collateral per #847's "pick the simpler approach" directive. Closes #847.

## [7.17.47] - 2026-04-27

### Changed

- `skills/implement/SKILL.md` Step 8b — replace the exit-1 (rebase conflict) bail with an invocation of the existing Rebase + Re-bump Sub-procedure under a new `caller_kind=step8b_rebase` so concurrent main-bump conflicts in the 8a→9 window auto-recover. The typical case (concurrent `.claude-plugin/plugin.json` bump on main) is fully resolved by sub-procedure step 1's `drop-bump-commit.sh` removing the local bump before re-rebasing. On unrecoverable failures the existing bail behavior is preserved (`STALL_TRACKING=true` + skip to Step 18). Step 8b's exit-3 / other-non-zero handlers are unchanged. NEVER #8 added to the SKILL.md NEVER list to forbid reuse of `step12_rebase` / `step10_rebase` for Step 8b's invocation (wrong post-success control flow + wrong failure routing).
- `skills/implement/references/rebase-rebump-subprocedure.md` — added third caller family (`step8b_rebase`) parallel to the existing `step12_*` and `step10_*` families: contract token list, Inputs schema, caller-family failure semantics, step-2 exit-1 / exit-3 branches, step-4 STATUS-degraded + HAS_BUMP=false branches (step12-strict semantics routed to STALL+18 instead of 12d), step-5 push SKIPPED for step8b (Step 8b's existing `git ls-remote` trichotomy handles fresh-branch path), step-7 return-to-caller branch (return to Step 8b's force-push gate; no `ci-wait.sh` re-invocation, no sleep, no counter updates). Per sketch-phase dialectic — DECISION_1 (3-0 narrow scope, no Phase 1-4), DECISION_2 (1-2 token name `step8b_rebase` over `step_8b`), DECISION_3 (3-0 step12-strict STATUS handling), DECISION_4 (3-0 skip step 5 for step8b).
- `skills/implement/references/bump-verification.md` Block β — added step8b family rows for `STATUS=git_error`, `STATUS=missing_main_ref`, `VERIFIED=false AND COMMITS_AFTER == COMMITS_BEFORE`, and `VERIFIED=false AND COMMITS_AFTER != COMMITS_BEFORE` branches (all hard-fail to STALL+18). Also extended Block γ sentinel-check warning prefix to cover step8b family.
- `skills/implement/references/conflict-resolution.md` — `Consumer` and `When to load` lines extended with step8b carve-out clarifying that step8b family deliberately does NOT enter Phase 1-4 (Phase 2-3 user-escalation + reviewer panel are post-PR machinery and inappropriate for the 8a→9 pre-PR window).
- Documentation-only PR; no shell-script changes. Closes #840.

## [7.17.46] - 2026-04-27

### Changed

- `skills/fix-issue/scripts/umbrella-handler.sh` — removed body-based umbrella detection. Detection becomes title-only, using the existing post-#819 bracket-prefix-peel grammar (<code>Umbrella: </code> or <code>Umbrella — </code> after stripping leading `[…]` / `(…)` blocks). The prior body-literal substring match on `Umbrella tracking issue.` produced false positives on issues that *quoted* the marker in code spans or prose (e.g., #753, whose body documented the marker inside backticks). Removed the `is_umbrella_body()` helper and the `DETECTION=body|title` field from `cmd_detect`'s stdout (no in-repo consumers). Sibling contracts (`skills/fix-issue/scripts/umbrella-handler.md`, `skills/fix-issue/scripts/test-umbrella-handler.md`) and the test harness (`skills/fix-issue/scripts/test-umbrella-handler.sh`) updated; Fixture 1 converted into a #753 regression check (body literal present + plain title → `IS_UMBRELLA=false`). `skills/fix-issue/SKILL.md`, `skills/fix-issue/scripts/find-lock-issue.sh`, `skills/fix-issue/scripts/find-lock-issue.md`, `docs/skills.md`, and `docs/workflow-lifecycle.md` updated to describe title-only detection and the operator migration path (rename hand-authored umbrellas relying on body-only detection to start with <code>Umbrella: </code> to restore detection). Body content remains used by `parse_children_from_body` for child enumeration — the change is scoped to the umbrella-vs-not decision. All 31 `test-umbrella-handler` fixtures and 45 `test-find-lock-issue` fixtures pass. Closes #846.

## [7.17.45] - 2026-04-27

### Fixed

- `scripts/create-pr.sh` — the existing-PR fast-path's `git push -u origin HEAD >/dev/null 2>&1 || true` (line 69) silently swallowed every push failure (non-fast-forward, lease failures, network errors), causing the script to emit `PR_STATUS=existing` and exit 0 while origin's branch tip was actually stale. Replaced with a plain-push-first / force-with-lease-fallback strategy that surfaces real push failures via exit 1, mirroring the new-PR path's exit-1 channel (lines 88-91). Plain `git push -u origin HEAD` handles the routine fast-forward case; on non-fast-forward (commonly after `/implement` Step 12 rebase + re-bump), escalation delegates to `scripts/git-force-push.sh` which already encodes lease + fetch + race-recovery + single retry. Helper stdout is suppressed to `/dev/null` so its `BRANCH=`/`PUSHED=`/`STATUS=` keys do not leak into create-pr.sh's documented `PR_*` stdout contract; helper stderr is captured and surfaced on real failure. Defensive `git fetch origin "$BRANCH"` + `git branch --set-upstream-to=origin/$BRANCH` guards run before the helper invocation, since git-force-push.sh requires upstream tracking + a populated origin/$BRANCH ref. `scripts/git-force-push.sh` and the new-PR path at line 88 are not modified. Per design dialectic DECISION_1 (voted 2-1 ALTERNATIVE — plain-push-first chosen over unconditional force-with-lease) and DECISION_2 (voted 2-1 THESIS — exit-code-only preserved over a new `PUSH_STATUS` stdout key); 2 accepted plan-review findings (defensive fetch before set-upstream; testing-strategy phrasing). Adds sibling `scripts/create-pr.md` per AGENTS.md "Per-script contracts live beside the script". Closes #837.

## [7.17.44] - 2026-04-27

### Fixed

- `scripts/test-improve-skill-iteration.sh` — replaced the file-wide `check_contains '/larch:design --auto'` regression guard (which silently passed because the rescue prompt at `skills/improve-skill/scripts/iteration.sh` line 875 also carries the token) with a new `check_count` helper that pins exactly **2** non-overlapping occurrences of `/larch:design --auto` (the primary `DESIGN_PROMPT` site + the rescue `RESCUE_PROMPT` site). Helper uses `grep -oF | wc -l` rather than `grep -F -c` so a future single-line collapse of both tokens still trips the guard. The `/larch:im --auto` guard at the same location is unchanged: only one occurrence in `iteration.sh` (the primary). Sibling contract doc `scripts/test-improve-skill-iteration.md` updated with the dual call-site rationale and an edit-in-sync rule for adding/removing `/larch:design --auto` invocation sites. Closes #838.

## [7.17.43] - 2026-04-27

### Changed

- `skills/umbrella/SKILL.md` Step 3B.1 unbundled `body` bullet — extended with a sibling clause prohibiting `###` sub-headers in any piece body (including inside fenced code blocks), mirroring the canonical wording of the existing bundled `Body shape` bullet. Documents the silent-corruption hazard where a `^### <title>` line in any piece body matches Path 3 in `parse-input.sh` (generic-mode flush + start new item), splitting the piece into multiple parsed items with broken `depends_on` index alignment relative to the original `pieces.json`.
- `skills/umbrella/scripts/render-batch-input.md` — added a new "Piece-body item-split hazard (#831)" paragraph documenting the producer-side contract (scoped to the normal-mode pipeline; pre-decomposed `--input-file` callers bypass this surface).
- `skills/issue/scripts/parse-input.md` — added a parallel "Reverse coupling: `/umbrella`'s piece bodies (#831)" subsection mirroring the existing `/research` reverse-coupling pattern, with an explicit caller catalog (covering all upstream `/issue --input-file` producers including operator-prebuilt batches that bypass `/umbrella` Step 3B.1 and the renderer) and a doc-only-enforcement note clarifying that `/umbrella` has no mechanical escape mechanism analogous to `/research`'s body-line backslash escape.
- `skills/umbrella/scripts/test-umbrella-emit-output-contract.md` — added a "Coverage asymmetry" sub-subsection plus an Edit-in-sync rule bullet documenting why the new unbundled-bullet `###` prohibition is intentionally NOT pinned by a `j8` assertion (panel-vote rationale from #831 plan review FINDING_1).
- Documentation-only — no script behavior changes; `j5` (bundled-body wording pin) and all 47 emit-output-contract assertions, 136 parse-input assertions, and 10 render-batch-input assertions continue to pass. Per code review FINDING_2 (3 YES unanimous), all in-prose references to "line 126" / "line 136" use stable semantic anchors ("Step 3B.1's unbundled `body` bullet" / "Step 3B.1's bundled `Body shape` bullet") instead of fragile fixed line numbers. Closes #831.

## [7.17.42] - 2026-04-27

### Fixed

- `skills/research/scripts/validate-citations.sh` — moved `export __VC_SETSID_DONE=1` inside the `command -v setsid` branch so the marker accurately reflects "running in the dedicated setsid session", and gated the Linux budget-exhaustion `kill -- -$$` on `__VC_SETSID_DONE=1`. When `setsid` is absent from PATH the timeout handler now falls back to per-PID `kill` over `CURL_PIDS` (orphan curl children bounded by `--per-fetch-timeout`) instead of self-signaling the validator's own process group. Restores the documented "always exits 0" fail-soft contract on Linux hosts where `setsid` is missing — previously the script could exit 143 with no sidecar. Sibling contract docs (`skills/research/scripts/validate-citations.md`, `skills/research/references/citation-validation-phase.md`) updated to describe the dual role of `__VC_SETSID_DONE` and the no-setsid fallback. Closes #779.

## [7.17.41] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/test-finalize-umbrella.sh` — initialized `OUT=""`, `ERR=""`, `EC=0` as globals near the top of the harness (alongside `PASS=0`, `FAIL=0`). The `run_script_capture` helper writes to these as implicit globals while the script runs under `set -euo pipefail`; without the explicit init, any future fixture that read `$OUT`/`$ERR`/`$EC` before the first `run_script_capture` call would trip `set -u`'s unbound-variable error. Defensive — current fixtures all call `run_script_capture` first, so behavior is unchanged. Closes #839.

## [7.17.40] - 2026-04-27

### Fixed

- `skills/umbrella/scripts/helpers.sh` — hoisted the `wire-dag` subcommand's `--dry-run` early-return from after the GitHub `/dependencies/blocked_by` probe block to immediately after argument validation, mirroring the `prefix-titles` subcommand's existing pattern. As a result, `wire-dag --dry-run` is fully side-effect-free: no `gh api` round-trip (or its 5xx/empty-status retry), no `**⚠ /umbrella: wire-dag probe failed (HTTP <code>): ...**` stderr warnings, no `UMBRELLA_PROBE_TARGET_FILE` write, no `EXISTING_EDGES_TSV` population. Stdout grammar (eight zeroed keys including the literal `PROBE_FAILED=0`) is preserved exactly. Sibling docs (`helpers.md`, `test-helpers.md`, `test-helpers.sh`) updated to describe the new ordering. Closes #769.

## [7.17.39] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/umbrella-handler.sh` — `is_umbrella_title` now recognizes umbrella titles that carry leading bracket-prefix tags. After stripping zero or more leading `[...]` and/or `(...)` blocks (with optional surrounding whitespace) via a bounded peel loop (cap=16, fail-closed on unbalanced/unclosed leading brackets), the remainder is matched against the existing case-sensitive <code>Umbrella: </code> / <code>Umbrella — </code> markers. Positive examples now detected: `[IN PROGRESS] Umbrella: foo`, `(urgent) Umbrella: foo`, `[IN PROGRESS] (urgent) Umbrella: foo`. Negative examples still rejected: `[IN PROGRESS] Do something umbrella related` (Umbrella mid-title after the prefix strip), `/umbrella ...` (lowercase command syntax). Body-literal detection unchanged.
- `skills/fix-issue/scripts/find-lock-issue.sh` — coordinated explicit-target reorder so umbrella detection runs BEFORE the `has_managed_prefix` early-reject. Without this reorder the title widening above would be unreachable in the explicit-target flow for hand-authored umbrellas with managed-prefix titles (e.g., `[IN PROGRESS] Umbrella: foo`). Auto-pick path is intentionally NOT mirrored — auto-pick excludes umbrellas regardless of order. Also fixes a latent `set -euo pipefail` interaction in the umbrella branch's BLOCKERS union pipeline (`grep -v '^$'` returned 1 on all-empty input, aborting the script silently for any umbrella with zero blockers): added `|| true` bracket so empty unions propagate as empty strings and `handle_umbrella` is reached.
- Documentation and harness contract sync: `skills/fix-issue/scripts/umbrella-handler.md` (Title-fallback grammar limitations and silent fail-closed contract), `skills/fix-issue/scripts/find-lock-issue.md` (new explicit-path order), `skills/fix-issue/scripts/test-umbrella-handler.md` (catalog F14-F20), `skills/fix-issue/scripts/test-find-lock-issue.md` (Fixture 10 entry), and `skills/fix-issue/SKILL.md` (Step 0 umbrella-issue exception widening, Known Limitations rewrites for "Umbrella support is explicit-target-only" and "Umbrella's own blockers gate dispatch"). Per design dialectic DECISION_1 (voted 2-1) and 10 accepted plan-review findings. Closes #819.

## [7.17.38] - 2026-04-27

### Added

- `skills/implement/SKILL.md` — added new **Step 8b** (rebase onto latest main before PR creation) between Step 8a (CHANGELOG amend) and Step 9 (Create PR). Step 8b is inline (NOT a fifth Rebase Checkpoint Macro call site) because its contract differs from the macro's `--skip-if-pushed` semantics — it always rebases so resumed Branch 1/2/3 runs are refreshed before the PR is opened. On rebase exit 1 (conflict) or exit 3 (other failure), bails to Step 18 with `STALL_TRACKING=true`. On rebase success, distinguishes `git ls-remote --exit-code --heads` exit 0 (branch exists → force-push via `git-force-push.sh`), exit 2 (positively absent → fresh-branch path, skip force-push), and other non-zero (transport/auth failure → bail rather than silently degrading and letting `create-pr.sh:69` swallow a non-fast-forward push). Step 8 `HAS_BUMP=false` now skips to Step 8b (was: Step 9) so repos without a `/bump-version` skill also benefit from the freshness rebase. Skipped entirely when `repo_unavailable=true`. Updated `scripts/test-implement-rebase-macro.sh` assertion (H) to expect 3 `--no-push`-only call sites (was: 2). Closes #818.

## [7.17.37] - 2026-04-27

### Fixed

- `CHANGELOG.md` — rewrote the v7.17.27 entry to drop the absolute line-number references `(line 833)` and `(line 928)` in `skills/improve-skill/scripts/iteration.sh`. The line-number anchors went stale as soon as `iteration.sh` gained or lost lines above those sites (same maintenance-nightmare anti-pattern that drove #789 / #828). The bullet now refers to "the primary `/larch:design` and `/larch:im` prompt builders in `iteration.sh`" — a stable phrase that survives future edits to the script. Documentation-only correction; runtime behavior unchanged. Closes #827.

## [7.17.36] - 2026-04-27

### Fixed

- `scripts/test-eval-research-baseline-flag.md` — dropped the stale `:25` line-number suffix from the cross-reference to `scripts/test-loop-improve-skill-driver.sh` on line 37. Same maintenance-nightmare pattern as #789 (which removed a separate stale line-number reference on line 35); the script-name reference is already a precise machine-greppable identifier and is robust to future drift inside that file. Documentation-only; runtime behavior unchanged. Closes #826.

## [7.17.35] - 2026-04-27

### Fixed

- `skills/research/SKILL.md` — aligned three stale wording occurrences with issue #520's K=3 quick-mode contract. Line 74's `--plan` resolution rule changed `(single lane, no fan-out)` to `(K=3 homogeneous lanes, no per-angle differentiation)`, matching the scale-matrix row at line 66 and the warning text at lines 76-77. Line 180's parenthetical aside about Step 1.1 / 1.2 skip semantics changed `single-lane quick mode has no fan-out to assign subquestions to` to `quick mode has no per-angle differentiation to assign subquestions to`. Line 334's quick-mode skip gate dropped the stale `single-lane` qualifier on `research-report.txt` (the file name is canonical regardless of K-lane vote-merge vs single-lane fallback). Same family of stale-K=3-contract drift as #823 (which fixed line 31 of the same file). Documentation-only; runtime behavior unchanged. Closes #824.

## [7.17.34] - 2026-04-27

### Fixed

- Apply unified `grep -F` doctrine at three regex-injection-class call sites (closes #775; closes #743 as duplicate). `skills/umbrella/scripts/helpers.sh` wire-dag back-link probe (`grep -qE "^${marker}"` → anchored awk `index($0, m) == 1`); existing-edge probe (`grep -qE "^${blocker}\t${blocked}$"` → string-forced awk field-equality `($1 "") == b && ($2 "") == t`, fixing an auto-numeric-coercion subtlety caught by a new regression test); and a new `--umbrella` numeric-grammar arg-parse guard (`^[1-9][0-9]*$`) that rejects non-empty non-numeric values on both normal and `--no-backlinks` bypass paths. `skills/issue/scripts/create-one.sh:182` label-existence probe `grep -qx` → `grep -Fqx` — active-current-path fix since `/umbrella --label` forwards operator labels verbatim.
- Add `SECURITY.md` "Fixed-string matching for interpolated values" section codifying the doctrine for future call sites.

## [7.17.33] - 2026-04-27

### Fixed

- `skills/research/SKILL.md` — replaced the stale `(1 / 3+3 / 5+5)` lane-shape parenthetical on the `--scale=` flag bullet (line 31) with `(3+0 / 3+3 / 5+5)` to match the file's `description:` on line 3 and the canonical scale matrix (per #520, `quick = 3+0`). Same family of stale-lane-count fix as #782 (which fixed `skills/research/diagram.svg`), different file. Documentation-only correction; runtime behavior unchanged. Closes #823.

## [7.17.32] - 2026-04-27

### Changed

- `skills/umbrella/SKILL.md` — added a "Bundle very small work items" rule to Step 3B.1: when two or more candidate pieces are each expected to be under ~10 lines of change (especially when touching only 1-3 files), the LLM decomposer biases toward merging them into a single composed `(title, body, depends-on)` tuple to reduce the token cost of downstream `/implement` runs. Conservative bundling criteria (all required): same component / skill / script-and-its-test pair; pairwise incomparable in the `depends_on` graph (no directed path in either direction — transitive, not just direct-edge); merged `depends_on` equals sorted unique union of bundled predecessors after compaction; body uses `- [ ]` checklist bullets only (never `###` sub-headers — `parse-input.sh` is line-based and would silently undo the bundle even inside fenced code blocks). Security / permissions carve-out keeps tiny-but-risky items as separate pieces. Bundling must keep `N>=2` final pieces; collapse to 1 falls through to the existing `decomposition-lt-2` one-shot path. Pinned all seven load-bearing clauses via new `j1`–`j7` assertions in `test-umbrella-emit-output-contract.sh` (40 → 47 assertions). Updated sibling `.md` doc, `docs/linting.md` count + j2 wording, and "one child per piece" phrasing in `docs/skills.md` / `docs/workflow-lifecycle.md` (L54 + L155) / `skills/skill-evolver/SKILL.md` to acknowledge bundling.

## [7.17.31] - 2026-04-27

### Fixed

- `skills/fix-issue/SKILL.md` — rewrote the "Umbrella concurrent finalize is comment-idempotent" Known-Limitations bullet (line 354) to reflect the current `finalize-umbrella.sh cmd_finalize` idempotency-guard semantics. The pre-FINDING_3 wording claimed any of the three idempotency signals (state=CLOSED, `[DONE]` title prefix, marker comment) triggered a strict short-circuit emitting `FINALIZED=false ALREADY_FINALIZED=true`. The new bullet enumerates three cases consistently with `skills/fix-issue/scripts/finalize-umbrella.md` Idempotency-guard section: (a) state=CLOSED → strict short-circuit; (b) OPEN with `[DONE]` title → skip rename, proceed to close path (still posts `--comment` when marker absent), emit `FINALIZED=true CLOSED=true RENAMED=false`; (c) OPEN with marker → skip comment-post, close-only retry, emit `FINALIZED=true CLOSED=true RENAMED=<bool>`. Documentation-only sibling-doc drift correction; runtime behavior unchanged. Closes #814.

## [7.17.30] - 2026-04-27

### Fixed

- `scripts/test-eval-research-baseline-flag.md` — dropped the stale absolute line-number reference in the `claude` PATH-stub paragraph ("`require_tool claude` check at line 130"). The actual call drifted to a different line after subsequent growth in `scripts/eval-research.sh`, and per the user's stated principle ("There should be no line number references like this, since it is obviously a maintenance nightmare") the line-number clause is removed entirely — the script-name + function-name pair (`eval-research.sh` `require_tool claude`) is already a precise machine-greppable identifier and is robust to future drift. Documentation-only; runtime behavior unchanged. Closes #789.

## [7.17.29] - 2026-04-27

### Fixed

- `skills/research/diagram.svg` — corrected two stale lane-count claims so the diagram matches the canonical `quick=3+0 / standard=3+3 / deep=5+5` scale matrix from `skills/research/SKILL.md`. The subtitle on line 15 now reads `quick=3 lanes no validation` (was `quick=1 lane no validation`), and the research-agents box label on line 24 now reads `3/3/5 Research Agents (scale-dependent)` (was `1/3/5`). Closes #782 (part of umbrella #784 — /research slice review).

## [7.17.28] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/umbrella-handler.md` — aligned the `pick-child` contract with the implementation. Line 27 previously stated "`pick-child` does NOT consult the blocker helpers (those live in `find-lock-issue.sh`)", contradicting `umbrella-handler.sh`'s `child_native_blockers` (called from `child_eligible`, invoked by `pick-child`). Reworded line 27 to distinguish the native-only filter owned by `pick-child` from the full `all_open_blockers` (native + prose) pass owned by `find-lock-issue.sh`; updated the matching Edit-in-sync rule near line 61 and added the missing `child_native_blockers` bullet to the "Per-child eligibility" list; synced the corresponding header comment block in `umbrella-handler.sh` (lines 37-46). Documentation-only correction; runtime behavior unchanged. Closes #764.

## [7.17.27] - 2026-04-27

### Fixed

- `skills/improve-skill/scripts/iteration.sh` — prepended `--auto` to the primary `/larch:design` and `/larch:im` prompt builders in `iteration.sh`, matching the rescue retry which already passed `--auto`. Without `--auto`, the iteration kernel's `claude -p` subprocesses had no interactive user but `/design` and `/implement` were free to invoke `AskUserQuestion` (`/design` Steps 1c, 1d, 3.5 when `auto_mode=false`), stalling the subprocess until the 3600s watchdog fired. Updated the sibling `iteration.md` contract with a new "Non-interactive `--auto` flag forwarding" subsection and added Tier 1 regression-guard pins (`/larch:design --auto`, `/larch:im --auto`) to `scripts/test-improve-skill-iteration.sh`. Closes #758 and the merged duplicate #761.

## [7.17.26] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/test-finalize-umbrella.sh` — every fixture now asserts the script's exit code AND its stderr behavior in addition to the existing stdout key/value substring matches. Replaces the per-fixture `OUT=$("$SCRIPT" ... 2>&1) || true` pattern with a `run_script_capture` helper that captures stdout, stderr, and `$?` separately, plus new `assert_eq_exit` / `assert_stderr_contains` / `assert_stderr_empty` helpers alongside the existing `assert_contains` / `assert_not_contains`. Fixtures 1-4 now require exit 0 + empty stderr; fixture 5 requires exit 0 + the literal `WARNING: title rename to [DONE] failed` on stderr (best-effort rename invariant). Sibling contract `skills/fix-issue/scripts/test-finalize-umbrella.md` updated in lockstep to document the new exit-code + stderr assertions and the `run_script_capture` canonical entry point. Harness ends at 26 passed / 0 failed. Closes #767.

## [7.17.25] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/find-lock-issue.sh:618` — the repo-ownership URL parser no longer hard-codes `https://github.com/...`. The regex was widened to `https://[^/]*/<owner>/<repo>/issues/<n>` so explicit `--issue <full-URL>` invocations work for GitHub Enterprise / self-hosted GHE deployments where the host is not `github.com`; the cross-repo guard (`ISSUE_REPO != REPO`) remains the actual safety net since `$REPO` already comes from `gh repo view` in the current repo. Sibling `find-lock-issue.md` and `test-find-lock-issue.{sh,md}` updated in sync; the test harness gains a fixture-9 `ISSUE_URL_HOST` knob and a regression case for a `ghe.example.com` URL (40 assertions pass). Closes #766.

## [7.17.24] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/finalize-umbrella.md:33-39` — replaced the misleading three-value `REASON` enum in the Stdout-contract table with the granular four-row split from duplicate #759. The script `finalize-umbrella.sh` only emits `REASON=already CLOSED` (line 153, paired with `ALREADY_FINALIZED=true` on the strict CLOSED short-circuit); the prior table listed `title already prefixed [DONE]` and `existing closing-comment marker detected` as `REASON` values, but those literals exist nowhere in the script. New rows tie `ALREADY_FINALIZED` / `REASON` to the strict CLOSED short-circuit and `RENAMED` / `CLOSED` to the executed path (including the close-only retry path where `RENAMED` may be `false` when the title was already prefixed `[DONE]`). Documentation alignment only; no script behavior change. Closes #756.

## [7.17.23] - 2026-04-27

### Fixed

- `skills/research/references/research-phase.md` — corrected the `RESEARCH_SCALE=quick` bullet under "Baseline prompt" (line 309). It previously stated quick mode "the single inline Claude lane runs `RESEARCH_PROMPT_BASELINE` verbatim", contradicting the same file's K=3 homogeneous Claude Agent-tool lane contract at lines 5, 11, 13, 17, and the "### Quick" subsection (issue #520). Reworded so the bullet states that each of the K=3 quick lanes is a Claude Agent-tool subagent running `RESEARCH_PROMPT_BASELINE` verbatim, and that the orchestrator does not run a separate inline lane in quick mode. Doc-only correction; runtime behavior is unchanged. Closes #781.

## [7.17.22] - 2026-04-27

### Fixed

- `scripts/test-loop-fix-issue-driver.md:7` — replaced the stale "Tier-2 stub-shim coverage is future work / out of scope for the current PR" framing with a pointer to the live behavior fixture `scripts/test-loop-fix-issue-driver-behavior.sh` (also wired into `make lint`), enumerating the three NDJSON scenarios it exercises (success, no-eligible-issues, sentinel-mismatch). Updated `skills/loop-fix-issue/scripts/driver.md`'s `LARCH_LOOP_FIX_ISSUE_CLAUDE_OVERRIDE` paragraph in sync to list all three scenarios — round-1 review caught the previous wording, which mentioned only success and no-eligible-issues. Closes #762.

## [7.17.21] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/test-finalize-umbrella.md` — aligned fixture descriptions with the actual close-only retry semantics in `test-finalize-umbrella.sh` and the canonical `finalize-umbrella.md` contract (FINDING_3 from the umbrella-PR code-review panel). Fixture 2 (marker present + state=OPEN) now correctly describes close-only retry yielding `FINALIZED=true RENAMED=true CLOSED=true` (NOT the stale `ALREADY_FINALIZED=true` short-circuit). Fixture 3 (`[DONE]` title + state=OPEN) now describes close-only retry skipping the rename, yielding `FINALIZED=true RENAMED=false CLOSED=true`. Only fixture 4 (state=CLOSED) is the strict short-circuit emitting `ALREADY_FINALIZED=true REASON=already CLOSED`. Tightened the "Test scope" preamble to make the asymmetry between the strict CLOSED short-circuit and the title/marker close-only-retry signals unambiguous on first read. Closes #760.

## [7.17.20] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/test-fix-issue-bail-detection.md` — aligned the intro sentence and edit-in-sync footer with the harness it documents. The .md previously opened with "six load-bearing literals (five conceptual checks)" but `test-fix-issue-bail-detection.sh` runs eight literal assertions (`a1`–`a4`, `b`–`e`) covering six conceptual checks. Updated the count to "eight literal assertions covering six conceptual checks", added the missing `--no-admin-fallback` SIMPLE/HARD bullet pair (issue #559 — branch-protection bypass safety flag) so the bullet list matches the harness's checks, and updated the closing edit-in-sync line. Doc-only correction; the harness itself and runtime behavior are unchanged. Closes #763.

## [7.17.19] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/finalize-umbrella.md` — correct the "Caller contract" Edit-in-sync count from THREE to FOUR (the bullet enumerated four sites — Step 0, Step 3, Step 5a, Step 6 — but stated "THREE call sites"). Reorder the enumeration to match SKILL.md flow order and tighten the "AND ... AND" phrasing to a clean comma-separated list. Closes #757.

## [7.17.18] - 2026-04-27

### Fixed

## [7.17.17] - 2026-04-27

### Fixed

- `skills/research/scripts/render-findings-batch.sh` — narrowed the `^####` flush branch in the awk splitter so it triggers only on planner-mode `#### Subquestion <N>` organizers (case-insensitive, whitespace-tolerant via `tolower(line) ~ /^####[[:space:]]+subquestion[[:space:]]+[0-9]+/` — BSD-awk portable). Other `####` headings (e.g., a `#### Notes on the data` subsection inside a finding's prose) now fall through to the existing list/paragraph branches and are preserved as ordinary body content. Adds Case 17 in `test-render-findings-batch.sh` exercising a column-0 non-planner `#### Notes on the data` heading inside a finding body, asserting `COUNT=1` plus a standalone `grep -Fq` post-condition that the heading literally survives in the rendered sidecar (verified to fail without the fix). Sibling contracts `render-findings-batch.md` (heuristic-ladder narrowed contract + Known Limitations on broader organizer scope for `### Cross-cutting findings` / `### Per-angle highlights`) and `test-render-findings-batch.md` (16→17 cases, Case 6 description aligned, Case 17 entry added) updated in sync per AGENTS.md. Closes #746.

## [7.17.16] - 2026-04-27

### Added

- `/umbrella` now prepends the literal marker <code>(Umbrella: &lt;N&gt;) </code> (with trailing space — load-bearing) to the title of every newly-created child issue on the multi-piece-with-real-umbrella path. Implemented as a new `helpers.sh prefix-titles` subcommand invoked from Step 3B.4 after `wire-dag`, iterating a caller-filtered TSV of newly-created children only. Idempotent — same-umbrella prefixes are skipped on re-runs; per-row `gh issue edit` failures bucket as `TITLES_FAILED` with redacted stderr warnings. Dedup'd, failed, and dry-run children are excluded so prior-umbrella prefixes are not stomped. The `created-eq-1` bypass, one-shot, dry-run, batch-fail, and umbrella-fail paths all skip the rename pass intentionally (no umbrella to anchor the marker). Stdout adds parse-only `TITLES_RENAMED` / `TITLES_SKIPPED_EXISTING` / `TITLES_FAILED` counters; not propagated through `output.kv`. New regression suite in `test-helpers.sh` covers idempotency, layering, gh-failure, dry-run, malformed-input, and validation paths. Closes #794.

## [7.17.15] - 2026-04-27

### Fixed

- `skills/improve-skill/scripts/iteration.sh` — narrow `detect_plan_status` refusal detection to the first non-empty line of the design output (was a whole-file `grep -qiE` that silently misclassified valid plans as `design_refusal` whenever any body line — e.g. a discussion line beginning `Cannot run in parallel …` or a quoted error excerpt — matched the refusal regex). Plan presence is now established by an explicit search for the canonical `## Implementation Plan` markdown header, replacing the prior coarse structural-marker grep that could match unrelated headings. New regression fixture `issue_755_refusal_phrase_in_plan_body` in `scripts/test-improve-skill-iteration.sh` exercises the bug-fix gate. Sibling `iteration.md` gains a "Design output classification" subsection documenting the decision order. Closes #755.

## [7.17.14] - 2026-04-27

### Changed

- `scripts/ci-decide.sh` — bumped the rebase-count safety limit from 5 to 20 so /implement's CI+rebase+merge loop tolerates a much busier `main` before bailing on `BAIL_REASON=Too many rebases (...)`. Updated all three sites (header comment, the `-ge` guard at line 113, and the bail-reason text) in lock-step. The other safety limits (`iteration >= 50`, `fix_attempts >= 3`) are unchanged. Closes #799.

## [7.17.13] - 2026-04-27

### Fixed

- Align `/implement`'s `plan-goals-test` anchor-fragment composition consumer with `/design`'s actual emitted plan heading (`## Implementation Plan`, with `## Revised Implementation Plan` superseding when plan review accepts findings). The previous instruction at `skills/implement/SKILL.md:510` directed the orchestrator to compose from `## Goal` and `## Test plan` sections that `/design` never produced, leaving the anchor fragment structurally non-extractable on every path. Closes #749.
- Add cross-skill drift-prevention assertion (16) to `scripts/test-implement-structure.sh` (producer pin + scoped consumer pin + anchor template pin + contiguous-phrase negative pin) so the producer/consumer schema agreement cannot silently re-emerge.

## [7.17.12] - 2026-04-27

### Changed

- `skills/umbrella/scripts/helpers.sh` — refactored the four `wire-dag` per-run caches (`BLOCKER_ID_CACHE`, `BLOCKED_BY_CACHE`, `_WD_LOOKUP_FAILED`, and the local `_seen_set` inside `_wd_populate_existing_edges_transitively`) from `declare -A` (Bash 4+) to Bash 3.2-safe storage primitives matching `skills/issue/scripts/allocate-candidates.sh`. Value-bearing caches now use parallel indexed arrays (`BIC_KEYS[]`/`BIC_VALS[]` and `BBC_KEYS[]`/`BBC_VALS[]` with a colon-delimited `BBC_PRESENT` for `+x`-style presence semantics including empty-value caching); membership sets (`WDL_PRESENT`, the inline `_seen` colon-string) use the `case "$_seen" in *:"$key":*) ... esac` idiom from `allocate-candidates.sh`. Pre-existing test suite passes on stock macOS Bash 3.2.57 because numeric-only keys made the indexed-array fallback after silent `declare -A` failure happen to produce equivalent semantics — the refactor is invariant-preserving cleanup that brings `helpers.sh` into compliance with the documented cross-skill Bash 3.2 portability invariant in `skills/issue/scripts/allocate-candidates.md`. `skills/umbrella/scripts/test-helpers.sh` adds a static portability guard (mirroring `test-allocate-candidates.sh` Test 21 including the comment-line filter) plus two new behavioral tests pinning the warn-once invariant and the colon-string delimiter-collision safety (positive + negative cases for nodes 1 and 11). Sibling contracts `helpers.md` and `test-helpers.md` updated. Closes #744.

## [7.17.11] - 2026-04-27

### Fixed

- `skills/fix-issue/scripts/finalize-umbrella.sh` — rewrote the obsolete "Idempotency guard (FINDING_2)" header comment block to match the current contract documented in `finalize-umbrella.md` and the actual `cmd_finalize` implementation. The prior header described a single rule ("any of CLOSED / `[DONE]` title / closing-comment marker → `FINALIZED=false ALREADY_FINALIZED=true`") that did not reflect runtime behavior; only `state=CLOSED` is a strict short-circuit, while OPEN issues with `[DONE]` title or marker are partial-success signals that drive selective skips (title → skip rename only; marker → skip comment-post only; close-only is the intersection). Also added the missing `REASON=already CLOSED` line to the in-script Stdout contract so all stdout keys are documented. Comment-only; no executable code changed. Closes #754.

## [7.17.10] - 2026-04-27

### Fixed

- `skills/design/references/flags.md` — replaced the dead "see Verbosity Control below" cross-reference on the `--debug` bullet (line 14) with an explicit pointer to the Verbosity Control section in `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md`. The Verbosity Control rules live in `SKILL.md`, not `flags.md`, and the file ends after the `--branch-info` bullet — readers following the original "below" pointer hit a dead link. The new pointer matches the cross-reference style used by the adjacent `--step-prefix` bullet (which references `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md`). Closes #750.

## [7.17.9] - 2026-04-27

### Fixed

- `skills/research/scripts/render-findings-batch.sh` — awk splitter no longer promotes indented nested numbered/bulleted sublists into separate top-level findings. Tracks a per-block `base_indent` (captured at the first top-level marker after each flush) and gates the flush-and-start branch on `current_indent <= base_indent`; deeper-indented markers stay as continuation. Adds a high-priority post-flush re-init branch (`current == "" && (is_numbered || is_bulleted)`) so the next list marker after a `####` or paragraph blank-line flush captures a fresh baseline. BSD-awk-safe `match()` + `RLENGTH` indent computation (guards `RLENGTH=-1` on no-match). Adds Cases 15 and 16 in `test-render-findings-batch.sh` covering the nested-numbered sublist and the nested-then-top-level-sibling paths. Sibling contracts `render-findings-batch.md` (heuristic-ladder + Known Limitations on sibling-indentation drift and tab/space mixing) and `test-render-findings-batch.md` (fixture inventory) updated in sync per AGENTS.md. Closes #745.

## [7.17.8] - 2026-04-27

### Fixed

- `skills/design/SKILL.md` — Step 5 cleanup section's "Repeat any external reviewer warnings" parenthetical cited `Step 0b binary checks`, but Step 0 in the file is titled only "Session Setup" and has no `0b` subsection. Reworded the citation to `Step 0 reviewer-availability checks via session-setup.sh`, matching the simpler attribution style used in `skills/review/SKILL.md`. The other three citations (`Step 2a`, `Step 3`, `Step 3b`) correspond to real anchors and are unchanged. Documentation-only. Closes #748.

## [7.17.7] - 2026-04-27

### Fixed

- `skills/skill-evolver/SKILL.md` — fixed the false-positive "filed as a single issue" message printed when `/umbrella`'s one-shot path deduplicates the would-be-new issue to an existing GitHub issue. The success branch now mutually-exclusively branches on `CHILDREN_CREATED=1` (filed) vs `CHILDREN_CREATED=0` AND `CHILDREN_DEDUPLICATED=1` (dedup'd), matching `/umbrella`'s own one-shot summary distinction at `skills/umbrella/SKILL.md:256`. The `created-eq-1` bypass case (where both counters can be `1` simultaneously) correctly falls into the filed branch. Updated the inline grammar reference and intro overview to mention dedup. Closes #771.

## [7.17.6] - 2026-04-27

### Changed

- `skills/fix-issue/scripts/find-lock-issue.sh` — auto-pick now prefers issues whose title matches the whole word `urgent` (case-insensitive, anywhere in the title) ahead of non-Urgent candidates, with oldest-first by issue number remaining the within-tier tiebreaker. The match uses an explicit non-word lookaround character class `[-A-Za-z0-9_]` rather than `\b` because jq's `\b` treats hyphen as a non-word char (so `\burgent\b` would mis-match `non-urgent`); the chosen pattern correctly rejects `non-urgent`, `insurgent`, and `urgently`. The preference is a soft re-ordering, not an eligibility filter — a non-Urgent issue is still picked when no Urgent eligible candidate exists; explicit-target mode (`/fix-issue <N>`) is unaffected. Companion docs in `skills/fix-issue/SKILL.md` and `skills/fix-issue/scripts/find-lock-issue.md` updated; `scripts/test-find-lock-issue.sh` adds two regression fixtures (Urgent-preference + non-urgent-rejection, and oldest-first preserved when no Urgent exists). Closes #787.

## [7.17.5] - 2026-04-27

### Fixed

- `scripts/eval-research.sh` — `require_value` now rejects a candidate value that starts with `--`, so a trailing flag followed by another flag (e.g. `eval-research.sh --baseline --scale standard`) cleanly exits 2 with `eval-research: --baseline requires a value` instead of silently binding `BASELINE_REF=--scale` and producing a confusing downstream `git show --scale:...` error. The validity regex `^[0-9A-Za-z._/-]+$` allowed `--scale` because hyphens are valid; the third `next_val` argument plus a `[[ "$next_val" == --* ]]` guard mirrors `take_value` in `scripts/render-reviewer-prompt.sh`. All 7 call sites updated to pass `"${2:-}"`. New Sub-5 case in `scripts/test-eval-research-baseline-flag.sh` pins the behavior; sibling contracts `scripts/eval-research.md` and `scripts/test-eval-research-baseline-flag.md` updated. Closes #780.

## [7.17.4] - 2026-04-27

### Changed

- `skills/issue/SKILL.md` — replaced the stale `since j < i` justification in Step 6's `DUPLICATE_OF_ITEM=<j>` paragraph with topological-schedule wording. After issue #546 the batch create order is topological, not input-index order, so `j` may exceed `i` in input order yet still be processed first via the synthetic `j → i` prerequisite edge. The new phrasing matches the language already used at line 312 for `BLOCKED_BY=ITEM_<j>` edges. Documentation-only. Closes #742.

## [7.17.3] - 2026-04-27

### Fixed

- `skills/research/references/validation-phase.md` — dedented the third `<<'EOF'` heredoc example (lines 240-252) from 3-space indentation to flush-left at column 0, matching the convention of the two prior working examples in the same file. Previously the block was nested under numbered list item 4, so an LLM agent (or human) copying the source literally would produce a non-terminating heredoc (`<<'EOF'` requires `EOF` flush-left) and indented `VALIDATION_*` body lines that fail the downstream `grep '^VALIDATION_'` filter. Closes #783.

## [7.17.2] - 2026-04-27

### Changed

- `skills/improve-skill/scripts/iteration.md` — added `[--subordinate]` to the documented invocation synopsis (line 12) and a brief description of its purpose. The flag was already parsed by `iteration.sh` (line 230) and always passed by `driver.sh` (line 470); the contract sibling `.md` is now in sync with the kernel's actual argv. Closes #752.

## [7.17.1] - 2026-04-27

### Changed

- `skills/review/SKILL.md` — replaced four stale `/issue` references with `/umbrella` in slice-mode descriptions (frontmatter `description:`, Slice Mode bullet, voting.md slice-mode-bypass note, and Step 4 heading) so the documentation matches the actual Step 4b runtime, which has invoked `/umbrella` (wrapping `/issue` for batch creation) since the umbrella was introduced. Documentation-only — runtime behavior unchanged. Surviving `/issue` mentions intentionally remain to describe `/umbrella`'s wrapping of `/issue` and the underlying OOS-format parser. Closes #739.

## [7.17.0] - 2026-04-27

### Changed

- `/umbrella` promoted from dev-only `.claude/skills/umbrella/` to shipped `skills/umbrella/` so consumer repos that load larch as a plugin can resolve it (closes #723). `/review --create-issues` and `/skill-evolver` now work for plugin consumers without requiring them to copy `/umbrella` into their own `.claude/skills/`. Path-style normalized to `${CLAUDE_PLUGIN_ROOT}/...` per AGENTS.md; `helpers.sh`'s relative climb to `redact-secrets.sh` adjusted from 4 to 3 levels (`skills/umbrella/scripts/` → repo root); `skills/review/SKILL.md` and `skills/skill-evolver/SKILL.md` consumer-repo prerequisite caveats deleted; `docs/configuration-and-permissions.md` strict-permissions snippet extended with `Skill(umbrella)` / `Skill(larch:umbrella)`; `Makefile` umbrella test targets and the `scripts/repro-claude-p-edit-permissions.{sh,md}` debug-target paths updated; `README.md` and `docs/skills.md` skills catalog augmented with the `/umbrella` entry.

## [7.16.38] - 2026-04-27

### Fixed

- `.claude/skills/umbrella/scripts/helpers.sh` and SKILL.md Step 3B.4 — `/umbrella` now wires the umbrella issue into GitHub's native blocked-by DAG. Step 3B.4 (both normal mode and pre-decomposed-input mode) writes `child→umbrella` edges into `proposed-edges.tsv` for every successfully-resolved child (newly-created via `ISSUE_<i>_NUMBER` OR deduplicated via `ISSUE_<i>_DUPLICATE_OF_NUMBER`, excluding `ISSUE_<i>_FAILED=true`). The umbrella is gated on its children's completion in the native graph so DAG-aware automation no longer sees it as an isolated leaf — directly addressing the user-stated requirement that interdependencies of all issues including the umbrella be saved.
- `.claude/skills/umbrella/scripts/helpers.sh` back-link loop — replaced the unreachable `blocked_by` native-detection probe with an anchored comment-existence idempotency check. The previous `gh api .../blocked_by --jq ".[] | select(.number == ${UMBRELLA})"` could never return a hit because no path in `/umbrella` ever created the matching native edge in the direction the probe tested, so re-runs accumulated duplicate `Part of umbrella #M — ...` comments on each child. The new check uses `gh api .../comments --paginate --jq '.[].body | split("\n")[0]'` piped to `grep -qE "^Part of umbrella #${UMBRELLA} — "` — first-line `jq` extraction + leading `^` anchor restrict the match to a comment whose body starts with the canonical prefix (a comment that quotes the marker mid-prose will not false-match); the trailing literal space-em-dash-space terminator prevents prefix-collision on numeric umbrella numbers (`#1` vs `#12`). Counter renamed `BACKLINKS_SKIPPED_NATIVE` → `BACKLINKS_SKIPPED_EXISTING` (parse-only set; no `output.kv` shape change). Check runs unconditionally — independent of the dependency-API `api_available` probe, since the comments API is a separate GitHub surface; on transient `gh api` failure the check fails open (post the comment), matching the rest of `wire-dag`'s fail-open posture.
- `skills/fix-issue/scripts/find-lock-issue.sh` — children-filter on the umbrella's blocker check. Without this filter, the new child→umbrella native edges would deadlock `/fix-issue <umbrella#>` dispatch — every open child would mark the umbrella blocked → `handle_umbrella` never runs. The umbrella branch now bypasses `all_open_blockers` (which short-circuits on any native blocker without consulting prose) and calls `native_open_blockers` and `prose_open_blockers` independently, filtering parsed children only from the native set and unioning with prose before the eligibility decision. A `list-children` failure emits a `WARNING:` stderr breadcrumb so support / debugging can distinguish "real external blockers" from "could not read umbrella body to filter children".
- `.claude/skills/umbrella/scripts/test-helpers.sh` — fixed a latent post-#728 stub bug surfaced by the new tests: when the URL-scanning logic produces an empty `_stub_url` (e.g., for `gh issue comment` and other non-API commands), `case "$1 $_stub_url"` evaluated to `"issue "` and the `gh issue comment` arm fell through to the default `*) exit 99`, silently breaking `BACKLINKS_POSTED` accounting. Added `if [ -z "$_stub_url" ]; then _stub_url="${2:-}"; fi` fallback so legacy `case "$1 $2"` arms keep matching. Adds 4 new tests for back-link comment-existence idempotency: existing-comment skip, no-comment post, numeric prefix-collision guard (`#12` vs `#1`), and fail-open posture (`STUB_LIST_COMMENTS_RC=22` → fail-open, post). All 53 tests pass.
- `helpers.md` and `test-helpers.md` — semantic-migration note for the counter rename, operational-cost note about paginated comment scanning, idempotency-as-coordination-convention caveat, persistent-failure recovery guidance. `find-lock-issue.md` documents the independent native+prose fetching with children-filter on native only and the new `list-children` stderr breadcrumb.

Supersedes #731 (paginate the back-link's `gh api blocked_by` call) — that code path is replaced entirely. Closes #716.

## [7.16.37] - 2026-04-27

### Fixed

- `.claude/skills/umbrella/scripts/helpers.sh` — `wire-dag` repo-wide API probe at lines 154-165 replaced its binary `gh api ... --silent && echo "ok" || echo "fail"` shape with a status-aware classifier (#728). The old probe collapsed all non-zero-exit outcomes into "feature missing" and bulk-routed every proposed edge to `EDGES_SKIPPED_API_UNAVAILABLE`, so transient network outages (TCP timeout, DNS failure, rate-limit hit during the probe itself) were silently masked as steady-state feature-absence. The new classifier reuses the issue #720 body-fingerprint pattern at the probe stage (`gh api -i` with status-line + body parse): 2xx → available; 404 + dual-regex feature-missing fingerprint → confirmed feature-missing (legacy "API not available" warning fires); 429 / other 4xx → transient probe failure (single-attempt, no retry); 5xx / empty-status → retry once, then transient probe failure if the retry also fails to classify. Adds a new parse-only `PROBE_FAILED=<0|1>` stdout key (per-run binary disambiguator: 0 = confirmed feature-missing OR no probe attempted; 1 = transient/operational probe failure) and a fifth one-time-per-run stderr warning prefix `**⚠ /umbrella: wire-dag probe failed (HTTP STATUS): REASON**` mirroring the existing per-edge `emit_edge_failure_warning` redact-secrets fail-closed discipline. `EDGES_SKIPPED_API_UNAVAILABLE` semantics are intentionally preserved as broad "repo-wide skip"; cause is read from `PROBE_FAILED` (parallel to issue #720's edge-counter migration note). The legacy "API not available" stderr is now gated on `PROBE_FAILED=0 AND probe_attempted=1` so transient failures and the empty-`probe_target` `--no-backlinks` path do not double-warn or false-warn. The new `_wd_is_feature_missing_404` shared shell predicate is consumed by both the probe-stage classifier and the existing per-edge POST 404 handler — single source of truth, prevents drift. Retry policy adopted via dialectic 2-1 vote (DECISION_1 ANTI_THESIS) over the alternative single-attempt-only design; the unanimous DECISION_2 THESIS preserved the existing edge-counter contract over narrowing it. `helpers.md`, `test-helpers.md`, `SKILL.md` Step 3B.4 prose, and `test-umbrella-emit-output-contract.sh` (six new structural-drift assertions `i1`–`i6`) updated in lockstep. `test-helpers.sh` adds 11 probe-classification fixtures and splits the existing `--no-backlinks` test (o) into feature-missing vs probe-failed scenarios; the probe stub gains per-attempt sequencing (`STUB_PROBE_RC_<N>` / `STUB_PROBE_RESPONSE_<N>` plus a `PROBE_CALL_COUNT_FILE` counter) and now recognizes the new `gh api -i URL` invocation shape. All 49 helper tests + 40 contract assertions pass. Closes #728.

## [7.16.36] - 2026-04-27

### Fixed

- `.claude/skills/umbrella/scripts/helpers.sh` — back-link branch's native-relationship probe now uses `gh api ... --paginate` so a child issue with more than one page of `blocked_by` entries (>30 by GitHub's default page size) is fully scanned. Without `--paginate`, the umbrella could appear on a later page and the script would either skip the back-link comment (treating the relationship as native when it wasn't visible) or post a redundant comment. Mirrors the existing `--paginate` idiom at `helpers.sh:280` (the `_wd_blocked_by_lookup` site fixed by #718). `helpers.md` updated in the same PR per repo edit-in-sync rule. Closes #731.

## [7.16.35] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/SKILL.md` Step 3B.2 — when the `/issue --input-file` batch dedups N-1 of N pieces to existing tickets and creates exactly one new issue, `/umbrella` was still proceeding to Step 3B.3 to create a brand-new umbrella tracking that single newly-created child plus N-1 duplicates. Add a new `created-eq-1` post-3B.2 bypass branch (normal mode only): when `INPUT_FILE` is empty AND `DRY_RUN=false` AND `ISSUES_FAILED=0` AND `ISSUES_CREATED=1`, skip Steps 3B.3 + 3B.4 entirely and emit the one-shot output shape with `UMBRELLA_VERDICT=one-shot` + `UMBRELLA_DOWNGRADE=created-eq-1` + `UMBRELLA_RATIONALE`. Precedence: `failed batch > created-eq-1 > existing 3B.3 dispatch`. CHILD_* renormalization: `CHILD_1` is always the newly-created child (preserves `/skill-evolver`-style one-shot consumer compat); deduplicated siblings appended as `CHILD_2+` in pieces order for auditability. `EDGES_*` and `BACKLINKS_*` keys remain reserved for multi-piece success — bypass output stays one-shot-shaped. Dependency wiring on the bypass path goes through a new `helpers.sh wire-dag --no-backlinks` flag: when set, the umbrella-rooted API probe is replaced by a probe of the FIRST CHILD in `CHILDREN_FILE` (children always exist on this path), and the entire back-link emission loop is skipped (no native-relationship `gh api` calls, no `gh issue comment` posts, no use of `$UMBRELLA`/`$UMBRELLA_TITLE`). `--umbrella` may be empty when `--no-backlinks` is set; otherwise it's required. `children.tsv` on the bypass path includes ALL resolved children (newly-created first, then dedup'd siblings) so `wire-dag`'s transitive `blocked_by` traversal (#718) enumerates the full existing-edge graph for cycle-check completeness — closes review FINDING_1. Step 4 schema parenthetical broadened to enumerate all 3 emission sites: `decomposition-lt-2` (Step 3B.1), `input-file-distinct-lt-2` (Step 2), `created-eq-1` (Step 3B.2). New breadcrumb shape: `✅ /umbrella: filed #<N> — <url> (multi-piece downgraded — created-eq-1, <D> sibling(s) deduplicated to existing issues, no umbrella issue created)`. `helpers.md` "GitHub dependency-API note" qualified to distinguish default mode (back-links via comments still proceed on probe failure) from `--no-backlinks` mode (back-link loop skipped regardless of probe outcome; stderr is mode-aware) — closes review FINDING_5. Regression: extends `test-umbrella-emit-output-contract.sh` to 30 assertions (8 new: `c8` for the bypass breadcrumb shape, `a3`/`a3b`/`a3c` for the broadened UMBRELLA_DOWNGRADE schema, `g1`–`g4` for the Step 3B.2 bypass-condition heading + full-conjunction predicate + precedence note + "do NOT execute Step 3A" guardrail). Extends `test-helpers.sh` with 4 new `--no-backlinks` cases (probe targets first child, zero `gh issue comment` calls, mode-aware stderr on probe failure, empty `--umbrella` without `--no-backlinks` errors helpfully). `helpers.md`, `test-helpers.md`, `test-umbrella-emit-output-contract.md`, and `docs/linting.md` updated in lockstep. Closes #717.

## [7.16.34] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/helpers.sh` — `wire-dag` cycle detection misses cycles closing through non-child intermediaries (#718). Replace the children-only `EXISTING_EDGES_TSV` seed loop with a bounded BFS over `blocked_by`, seeded from children + both endpoints of every proposed edge. New helpers `_wd_blocked_by_lookup` (per-run `BLOCKED_BY_CACHE`; `gh api --paginate`; on transient gh failure caches `_GH_FAIL_` sentinel + emits one-time per-failed-node stderr warning, individual lookup remains fail-open) and `_wd_populate_existing_edges_transitively` (worklist BFS; bounded by `WIRE_DAG_TRAVERSAL_NODE_CAP`, default 200, env override; TSV-append unconditional per discovered blocker, `_seen_set` guards re-querying only). Bound enforcement covers both the seed phase (post-seed cap check fires if children + EDGES_FILE endpoints already exceed the cap) and the BFS expansion phase. On cap exhaustion: `_wd_traversal_truncated=1`; the per-edge cycle-check loop routes any `CYCLE=false` candidate to `EDGES_FAILED` with reason `bound-exhausted` (per-edge fail-CLOSED — DECISION_1 voted 3-0 in the design-phase dialectic) rather than POSTing a potentially cycle-creating edge. The `WIRE_DAG_TRAVERSAL_NODE_CAP` env var is validated as a positive integer; non-numeric / zero values fall back to default 200 with a one-time warning instead of aborting wire-dag under `set -e`. **Semantic migration**: `EDGES_FAILED` now covers two categories: (a) operational POST failures from #720 (rate-limit, permission denied, ambiguous 404, 5xx, request-shape mismatches, blocker-id lookup failure, network) and (b) policy-driven `bound-exhausted` candidates whose cycle-check verdict could not be trusted on a known-incomplete TSV. Both share the existing per-edge stderr warning prefix `**⚠ /umbrella: wire-dag edge BLOCKER->BLOCKED failed (HTTP STATUS): REASON**` (the `STATUS` field carries the HTTP code or the literal `bound-exhausted`). Two new one-time stderr prefixes: traversal-cap-reached (per run) and `blocked_by` lookup-failed (per failed node). `helpers.md`, `test-helpers.md`, and `SKILL.md` Step 3B.4 updated to document the extended `EDGES_FAILED` taxonomy and the four-category stderr contract. `test-helpers.sh` extended with per-node `STUB_BLOCKED_BY_<N>` dispatch (legacy global `STUB_EXISTING_BLOCKERS` preserved as default-empty fallback for back-compat) plus four new regressions: standalone non-child-intermediary `check-cycle` invariant, wire-dag non-child-intermediary cycle rejection, EDGES_FILE-only seeding cycle closure, bound exhaustion → `EDGES_FAILED` with `bound-exhausted` reason, transient blocked_by lookup failure → fail-open with one-time warning. All 31 tests pass. Closes #718.

## [7.16.33] - 2026-04-26

### Changed

- `.claude/skills/umbrella/SKILL.md` Step 2 — strengthen the `Distinct-resolved-child-count rule` (governing `/umbrella --input-file` classification post-3B.2) with an explicit caller-agnostic authoritativeness note: the rule applies uniformly regardless of whether `/issue --input-file --dry-run` is invoked through `/review --create-issues` (today's caller), a future CI driver exercising `/umbrella --input-file --dry-run`, or any other future caller. The note enumerates the four load-bearing literals — `Distinct-resolved-child-count rule** (dry-run-safe)`, the `ISSUE_<i>_DRY_RUN=true` count-as-1 sentence, the `len(set_of_numbers) + count_of_dry_run_items` formula, plus the new note itself — and confirms `scripts/test-umbrella-emit-output-contract.sh` pins them. Behavior-preserving: the rule itself is unchanged; only its documentation strength + a structural drift guard. Regression: extends `test-umbrella-emit-output-contract.sh` to 22 assertions (4 new `f1`–`f4` literals over a new Step 2 awk-extracted block). `test-umbrella-emit-output-contract.md` (extraction-boundaries table + edit-in-sync rules), `docs/linting.md` row, and the `Script contracts` bullet in `umbrella/SKILL.md` are refreshed in lockstep. Closes #724.

## [7.16.32] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/helpers.sh` — `wire-dag` per-edge POST: replace the all-or-nothing classifier (lines 172-181) with a status-aware branch using `gh api -i`. Captures HTTP status from the response, branches on 2xx (`EDGES_ADDED`) / 404 + feature-missing body (`EDGES_SKIPPED_API_UNAVAILABLE`) / 422 already-exists (`EDGES_SKIPPED_EXISTING`, idempotent per `add-blocked-by.sh:193-196`) / everything else (new `EDGES_FAILED` counter with one redacted stderr line per failure). Switches the per-edge POST body shape from `-f issue_number=<display>` to canonical `{"issue_id": <internal numeric id>}` matching `add-blocked-by.sh:170-183` — the original shape was malformed and silently 422'd, which the previous classifier mis-bucketed as "API unavailable" (#720 root cause). Resolves blocker internal ids via `gh api ... --jq .id`, cached per run. Stderr warnings are piped through `scripts/redact-secrets.sh` (canonical secret scrubber); when the redactor exists but exits non-zero, fails closed to a `<REDACTION_FAILED>` placeholder rather than printing the raw API body. **Semantic migration**: counters that previously bucketed in `EDGES_SKIPPED_API_UNAVAILABLE` after a successful probe (post-probe 403/429/5xx) now move to `EDGES_FAILED` with one stderr line each; dashboards keyed on the old counter as a "benign skip volume" gauge will see a corresponding rise in `EDGES_FAILED` plus new diagnostic noise. Doc updates in `helpers.md` (stdout grammar + stderr contract + residual-redaction-risk note + narrowed edit-in-sync rule restricted to `output.kv`-propagated keys), `SKILL.md` Step 3B.4 (parse-list rewrites `EDGES_SKIPPED_API_UNAVAILABLE` description and adds `EDGES_FAILED`) plus the `Script contracts` bullet for `test-helpers.sh`. `test-helpers.sh` adds 13 new wire-dag PATH-stub `gh` tests covering 200 / 404 feature-missing / 404 ambiguous / 429 / 403 / 5xx / 422 already-exists / 422 non-idempotent / probe failure / dry-run includes `EDGES_FAILED=0` / non-zero `gh` exit + `-i` blob (proves `set +e/-e` wrapper) / blocker-id lookup failure / `id-lookup` tag in warning. All 26 tests pass. `test-helpers.md` and `test-umbrella-emit-output-contract.md` updated to drop the stale "wire-dag is out of scope" disclaimer. Closes #720.

## [7.16.31] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/SKILL.md` Step 3B.3 — short-circuit `DRY_RUN=true` BEFORE umbrella-body rendering. The previous code only skipped Step 3B.4 (DAG wiring + back-links) on `--dry-run`; Step 3B.3 still ran and crashed because `/issue --dry-run` does not emit real issue numbers, so `children.tsv`'s numeric-first-column invariant could not hold and `render-umbrella-body.sh`'s validator at lines 38–42 hard-failed with `ERROR=children.tsv malformed at line N`. The multi-piece `--dry-run` path was therefore unusable end-to-end. The fix mirrors Step 3B.4's existing `Skip this entire sub-step when DRY_RUN=true` pattern, prepending the same directive at the top of Step 3B.3 with a folded skip-line breadcrumb (`⏭️ /umbrella: umbrella body + umbrella create + dependency wiring + back-links skipped (--dry-run)`) that subsumes 3B.4's wiring/back-links message on the dry-run path because the orchestrator never enters 3B.4 from this gate. Step 4's emit-output renders the canonical multi-piece dry-run breadcrumb (`ℹ /umbrella: dry-run — would file umbrella with <N> children`) using `<N> = CHILDREN_CREATED` from session state. `render-umbrella-body.sh` and `/issue` are deliberately unchanged — preserves the renderer's strict numeric-first-column invariant (still load-bearing for real runs) and avoids teaching shared code paths about a special dry-run format. Also updates the Step 1 `--dry-run` flags-table row, adds a qualifying sentence to Step 3B's "Four sub-steps run in order" framing, and rewords Step 3B.2's parenthetical to reflect that dry-run items now skip both 3B.3 and 3B.4. Regression: extends `test-umbrella-emit-output-contract.sh` to 18 assertions (5 new: `d1`–`d3` for Step 3B.3 + `e1`–`e2` for Step 3B.4) pinning the shared dry-run skip directive prefix in BOTH blocks plus each block's skip-line breadcrumb — the matched-pair invariant prevents the two parallel dry-run gates from drifting apart. `docs/linting.md` row updated to reflect the new assertion count and scope. Closes #719.

## [7.16.30] - 2026-04-26

### Changed

- `/review --create-issues` (slice mode) now delegates issue filing to `/umbrella` (via Skill tool) instead of calling `/issue --input-file` directly. When ≥2 distinct issues are filed (counted post-`/issue` dedup, dry-run-safe), `/umbrella` produces a tracking umbrella issue + children with back-link comments. When ≤1 distinct → no umbrella (one-shot path). Adds `--input-file PATH` and `--umbrella-summary-file PATH` to `/umbrella` (paired-flag validation, mutual exclusion with positional TASK; bypasses Step 1 task resolve and Step 3B.1 LLM decomposition). `/review` composes the umbrella summary from slice context with concrete sanitization (strip control chars, redact secrets / internal URLs / PII, cap ~200 chars). Slice-result KV footer schema unchanged: `ISSUES_CREATED` includes the umbrella tracker (per dialectic DECISION_2 — uniform "any GitHub issue created counts" semantic); `ISSUES_FAILED` uses a structural signal (`UMBRELLA_VERDICT=multi-piece` AND `UMBRELLA_NUMBER` empty AND `CHILDREN_FAILED=0`) so the children-batch-failed abort path doesn't double-count. `skills/loop-review/scripts/driver.md` documents the "Issues filed" semantic shift. Test harness extended (32 invocations covering 7 new flag/validation cases, 16 frozen ERROR templates). `/umbrella` is currently dev-only at `.claude/skills/umbrella/`; the `/review` SKILL.md now carries a consumer-repo caveat parallel to `/skill-evolver`. Closes #713.

## [7.16.29] - 2026-04-26

### Changed

- `scripts/test-research-structure.md` and `scripts/test-research-structure.sh` — refresh stale opener prose/comments to describe the 5-reference progressive-disclosure topology (`research-phase.md`, `validation-phase.md`, `adjudication-phase.md`, `citation-validation-phase.md`, `critique-loop-phase.md`) and the all-four-others `Do NOT load` reciprocal-guard structure. The `.sh` harness has enforced 5 references since #516 / #517 added `critique-loop-phase.md` (lines 41-47, 62, 122-126, 140; fail message at line 118 explicitly names "5-reference symmetric topology — #517"), but the sibling `.md`'s line-3 contract paragraph still said "4-reference progressive-disclosure topology" with only four files in the parenthetical and Check 3's prose said "**both** other references"; the `.sh` header comments lines 3-9 still said "4-reference symmetric topology" / "ALL THREE other references", lines 65-76 (Check 3 inline comments + procedure block) repeated "ALL THREE" / "OTHER three", and `check_mandatory_topology`'s `local -a others` comment said "the other three filenames". All five surfaces now read "5-reference" / "all four other references" / "ALL FOUR" / "OTHER four" / "the other four filenames". Doc-only change; harness behavior unchanged (still asserts "all 54 structural invariants hold"). Closes #714.

## [7.16.28] - 2026-04-26

### Fixed

- `skills/loop-fix-issue/scripts/driver.sh` — pass `--output-format stream-json --verbose` to the per-iteration `claude -p /fix-issue` invocation in `invoke_claude_p_skill`. Default-mode `claude -p` emits only the FINAL assistant message text on stdout, so the driver's grep for `/fix-issue`'s Step 0 success sentinel `find & lock — found and locked` was always missing the breadcrumb — even when `/fix-issue` actually shipped a PR and merged. The loop halted with `Step 0 unknown short-circuit (sentinel mismatch)` after one productive iteration. Stream-json mode emits one JSON object per assistant turn / tool_use / system / result event, with the breadcrumb text appearing verbatim somewhere in the NDJSON sidecar (typically inside an `assistant`-typed turn's text content); `&` and the em-dash stay as raw UTF-8 (no `&` / `—` escaping by Anthropic's encoder), so the existing literal-substring grep keeps matching against the file. Switches the four `grep -F -q` calls to `grep -aF -q` for binary-mode safety on the NDJSON sidecar. Adds `scripts/test-loop-fix-issue-driver-behavior.sh` — a Tier-2 fixture using `LARCH_LOOP_FIX_ISSUE_CLAUDE_OVERRIDE` + a stub `CLAUDE_PLUGIN_ROOT` tree + a PATH-mocked `gh` to exercise three scenarios (success / no-eligible / no-sentinel) end-to-end against canned NDJSON, plus 2 new structural pins in `test-loop-fix-issue-driver.sh` (count 20→22) anchored on the live `$claude_bin` invocation line. Doc/contract sync across `driver.md`, `SKILL.md`, `SECURITY.md` (NDJSON sidecars carry richer trace data on retained paths), `docs/workflow-lifecycle.md`, and `docs/linting.md`. Closes #708.

## [7.16.27] - 2026-04-26

### Added

- `scripts/test-research-structure.sh` — Check 53 (artifact-filename alignment) and Check 54a/54b (skip-precondition order at /research Step 2.7). Check 53 asserts that `skills/research/references/adjudication-phase.md` and `skills/research/references/citation-validation-phase.md` do NOT carry the historical tmpdir artifact name `research-synthesis.txt` and DO reference the canonical `research-report.txt` at least once each. Check 54a section-scopes `citation-validation-phase.md` § 2.7.1 (singleton heading + `Budget-abort gate (evaluated FIRST` precedes `Empty-synthesis gate (evaluated SECOND`); Check 54b paragraph-scopes SKILL.md Step 2.7's `**Skip preconditions** (emitted FIRST` opener (singleton anchor + budget-abort skip breadcrumb byte-precedes empty-synthesis breadcrumb via bash parameter expansion). Bumps PASS message from "all 52 structural invariants hold" to "all 54". `scripts/test-research-structure.md` updated to document the new checks, edit-in-sync surfaces, and gate-count bump. Guards the bug class that surfaced as #665 (artifact name drift) and #666 (skip-order inversion); both underlying bugs are already fixed. Closes #671.

## [7.16.26] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-batch-input.sh` — add a `[ -w "$TMPDIR" ]` writability preflight immediately after the existing `[ -d "$TMPDIR" ]` check, mirroring the guard in `render-umbrella-body.sh:28-30`. Without it, an unwritable `--tmpdir` produced a raw bash "Permission denied" line on the first redirect under `$TMPDIR` (`2>"$JQ_PARSE_ERR"` or `: > "$OUT"`) and an exit code other than 1, breaking the documented `ERROR=...` stable stderr line + exit 1 grammar that downstream `umbrella` SKILL.md Step 3B.1 consumers rely on. The new guard emits `ERROR=tmpdir not writable: <path>` and exits 1 BEFORE any redirect under `$TMPDIR`. Adds an `assert_unwritable_tmpdir` regression case to `test-render-batch-input.sh` (creates a sub-tmpdir, `chmod 555`, runs the script, asserts exit 1 + `ERROR=tmpdir not writable:` stderr line, restores the writable mode for trap cleanup) and updates `render-batch-input.md` "Test coverage" + CLI sections to document the new failure mode. Closes #687, same bug class as #645 / #710 on a sibling script.

## [7.16.25] - 2026-04-26

### Fixed

- `scripts/eval-research.sh` — close the `--smoke-test` grep-fallback bypass that let truncated/malformed `eval-baseline.json` pass schema validation. Previously, when `jq` was unavailable, `validate_baseline_json` fell back to three substring `grep` checks for `"version"`, `"scale"`, `"entries"` — a bug-shaped JSON containing those literals anywhere (including inside string values or comments) returned success even though it was not parseable, contradicting the contract at `scripts/eval-research.md` ("parse and schema-validate"). Move `require_tool jq` outside the `SMOKE_TEST` guard so `jq` is required in all modes and drop the grep-fallback `else` branch in `validate_baseline_json` so JSON validation has a single deterministic path. Updates the `--smoke-test` row in `scripts/eval-research.md` to document `jq` as required in this mode and rewrites the exit-code-3 prose (and the script's matching usage-block comment / tooling-check section title) to spell out per-mode tool requirements. Existing test harnesses are unaffected: `test-eval-research-baseline-flag.sh` already PATH-stubs `jq`, and `test-eval-set-structure.sh`'s `--smoke-test` invocation will surface a clear exit-3 if `jq` is genuinely missing. Closes #669.

## [7.16.24] - 2026-04-26

### Fixed

- `skills/implement/scripts/check-review-changes.sh` (line 81) — replace `echo "$CURRENT"` with `printf '%s\n' "$CURRENT"` so untracked filenames matching bash `echo` flags (`-n` / `-e` / `-nn` / `-E`) are not silently swallowed when the sorted current-untracked stream is fed to `comm`. Pre-fix, a real `/implement` Step-5/6 run could miss review-created untracked files when the current set contained exactly such a name (reproduced with an external baseline + a repo whose only untracked file was named `-n` — the script returned `FILES_CHANGED=false`). The existing `sed '/^$/d'` empty-CURRENT safety net is preserved (`printf '%s\n' ""` still emits a single trailing newline). Add regression case (i) to `test-check-review-changes.sh` (untracked `-n` + external empty baseline) and update the script's docstring header, `check-review-changes.md` case-count prose, and `test-check-review-changes.md` table + harness summary in sync. Closes #695.

## [7.16.23] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-umbrella-body.sh` — install a narrow `trap 'rm -f "$OUT_TMP" 2>/dev/null || true' EXIT` immediately after the `OUT_TMP=$(mktemp ...)` block so the three subsequent error-exit branches (empty staged body, pre-existing non-regular `$OUT`, `mv` failure) no longer leak `umbrella-body.md.*` partials into the caller's `--tmpdir` across retries or CI reruns. On the success path the trap is a no-op because `mv` has already moved the partial. Sibling `render-umbrella-body.md` updated in sync to document the new contract. Closes #694.

## [7.16.22] - 2026-04-27

### Fixed

- `skills/skill-evolver/SKILL.md` — fix `--debug` placement on the `/research` (line 86) and `/umbrella` (line 108) invocation lines. The skill previously documented "append `--debug` only if `DEBUG=true`", but both downstream skills parse flags from the start of `$ARGUMENTS` and stop at the first non-flag token (`skills/research/SKILL.md:21`, `.claude/skills/umbrella/SKILL.md:24`), so an appended `--debug` would be swallowed into the research question / umbrella task description instead of enabling debug mode. Move `[--debug]` to the front of each documented args spec and rewrite the trailing prose ("prepend" instead of "append") with an inline rationale citing the downstream parsers. Closes #690.

## [7.16.21] - 2026-04-26

### Fixed

- `docs/linting.md` row for `make test-umbrella-emit-output-contract` (line 66) — counts and breadcrumb-shape parenthetical were stale relative to the on-disk harness `.claude/skills/umbrella/scripts/test-umbrella-emit-output-contract.sh` (drift introduced in commit 9be8d96 / Fix #644 which added the c6b assertion). Update `12 literal-substring assertions` → `13 literal-substring assertions` (a1, a2, c1-c5, c6, c6b, c7, b1, b2, b3) and `the seven canonical breadcrumb shape templates` → `the eight canonical breadcrumb shape literals` (matching the harness comment "on disk these expand to eight concrete breadcrumb literals"). Split the parenthetical breadcrumb-shape list `multi-piece success/dry-run/partial/children-batch-failed` → `multi-piece success/dry-run/partial-fallback/partial-with-reason/children-batch-failed` to reflect the c6 + c6b split (fallback vs UMBRELLA_FAILURE_REASON-parenthetical variants). Closes #686.

## [7.16.20] - 2026-04-26

### Fixed

- `skills/research/scripts/validate-citations.md` and `skills/research/references/citation-validation-phase.md` — clarify the citation-validator's exit-code contract by replacing every "always exits 0 on every path"-style claim with "exits 0 on validation paths; exit 2 only for argument/flag errors — operator or harness bug." `validate-citations.sh:124,128,147,153` already exit 2 for unknown args, missing required args, invalid numeric flag values, and missing `--tmpdir`; the documentation now matches that shipped behavior. Three in-script doc surfaces in `validate-citations.sh` (header banner at line 11, `# Exit code:` block at line 35, and the `set -uo pipefail` introduction comment) are aligned to the same canonical wording for consistency. Closes #668.

## [7.16.19] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-batch-input.sh` — guard `PIECE_<i>_TITLE` against embedded newlines in the per-entry validation loop. A multi-line title from untrusted `pieces.json` would previously be emitted via `printf 'PIECE_<i>_TITLE=%s\n' "$title"`, splitting one logical KV into multiple physical stdout lines and silently breaking the one-KV-per-line grammar that umbrella SKILL.md Step 3B.1 parses. New `case "$title" in *$'\n'*) ... esac` assertion fires immediately after the existing empty-title check, before any markdown or stdout emission, with stable `ERROR=pieces.json entry <i> title contains embedded newline` stderr line + exit 1. Scope is LF only; CR (`\r`) and Unicode line separators (U+2028 / U+2029) are documented as out of scope. Sibling docs updated in sync — `render-batch-input.md` bumps the pinned-mode count from 3 to 4, adds the single-line stdout free-text fields rationale, and documents the residual gap; `test-render-batch-input.md` adds case 8 to Cases list, qualifies the Out-of-scope paragraph, and adds an edit-in-sync rule pinning the new `ERROR=` literal. Regression test in `test-render-batch-input.sh` (case 8 — `assert_invalid_title`) feeds a multi-line title and asserts the documented stderr line + exit 1; existing 8 cases continue to pass. Closes #648.

## [7.16.18] - 2026-04-26

### Changed

- `scripts/eval-research.md` and `scripts/eval-research.sh` — refresh the `--scale` flag's documentation across both surfaces. The `.md` flag table row at line 30 previously claimed `/research` did not yet accept `--scale` and pointed at issue #418 as a future landing point; #418 has since closed and the harness already builds `/larch:research --scale=$SCALE` directly (`scripts/eval-research.sh:331`), with `skills/research/SKILL.md:31` documenting `--scale=quick|standard|deep` as a manual override of the adaptive scale classifier (#513). Rewrite the row to describe current behavior — forwarded to `/larch:research`, manually overrides the adaptive scale classifier, and recorded in produced JSON's top-level `scale` field only when `--write-baseline` is used. Align the matching `eval-research.sh` header comment block (lines 19-25) so both surfaces describe the flag identically (canonical "adaptive scale classification" vocabulary from `skills/research/SKILL.md`). Closes #667.

## [7.16.17] - 2026-04-26

### Fixed

- `skills/research/scripts/validate-citations.sh` — split the case arm `2??|3??)` so 3xx HEAD responses are reclassified as `UNKNOWN(redirect-not-followed)` instead of `PASS`. With `--max-redirs 0` (set as part of the SSRF guard), curl never fetches the redirect destination, so a cited URL that 301s to a removed page or to a private/internal host appeared valid in the citation ledger — silently overstating audit certainty for any redirected URL. The DOI ledger composer is special-cased in lockstep: `https://doi.org/<doi>` is a redirect resolver by design (every resolvable DOI returns a 3xx HEAD), so the DOI path interprets `UNKNOWN(redirect-not-followed)` as PASS rather than collapsing it to `UNKNOWN(doi-unresolved)` — preserving DOI ledger behavior bit-identically while correcting URL ledger behavior. Sibling docs updated in sync (`validate-citations.md` Reason vocabulary + Test harness bullet, `references/citation-validation-phase.md` Failure-modes table, `test-validate-citations.md` scenarios table). New Test 9b pins HEAD 301 → `UNKNOWN(redirect-not-followed)` and new Test 9c pins DOI HEAD 302 → PASS via the special-case; the shared fake-curl shim gains explicit `example-301.invalid → 301` and `doi.org → 302` arms. Closes #663.

## [7.16.16] - 2026-04-26

### Fixed

- `skills/review/SKILL.md` — pin slice-mode external-reviewer dual-list contract (closes #659). External slice-mode reviewers (Cursor line 179, Codex line 190) now emit dual-list output with `### In-Scope Findings` / `### Out-of-Scope Observations` section headers (matching the Claude reviewer's existing dual-list contract from `skills/shared/reviewer-templates.md:191,197`). Step 3a item 2 (line 238) becomes mode-conditional with three-way fail-open rules (one missing header → empty section; both absent + `NO_ISSUES_FOUND` → reviewer reported nothing; both absent + not `NO_ISSUES_FOUND` → entire body in-scope, preserving backward compatibility); diff mode keeps single-list. Step 3a item 3 (line 239) adds symmetric merge for external OOS observations. Step 3a item 1 (line 233) wording aligned to canonical `###` headings. `NO_ISSUES_FOUND` sentinel emission tightened to "neither in-scope findings nor out-of-scope observations" so OOS-only findings cannot be silently dropped. Coordinated narrowing edits to `skills/shared/voting-protocol.md:221`, `docs/voting-process.md:107`, and `docs/review-agents.md:83` scope the prior blanket "externals produce single-list, no OOS" claims to diff mode. New structural assertions (14)/(15)/(16)/(17) in `scripts/test-review-structure.sh` (and `scripts/test-review-structure.md`) pin both halves of the contract. PASS line bumped to "all 17 structural invariants hold". Closes #659.

## [7.16.15] - 2026-04-26

### Changed

- `README.md` Skills table — trim three over-long descriptions (`/issue`, `/research`, `/skill-evolver`) to 1-2 sentences matching the surrounding entries; canonical detail remains at the linked `docs/skills.md` anchors. The `/research` row drops from a multi-paragraph block (~5500 chars) to a 2-sentence summary; `/issue` from ~600 chars to ~150; `/skill-evolver` from ~830 chars to ~280. Adds a parallel paragraph to `docs/skills.md#issue` covering always-on inter-issue blocker-dependency analysis (per-item rollback / multi-item continuation / run-level non-zero exit on retry exhaustion) so no factual detail is lost. Closes #682.

## [7.16.14] - 2026-04-26

### Fixed

- `skills/research/scripts/validate-citations.sh` — on macOS (Darwin), `set -m` (job-control mode) puts each backgrounded `fetch_url` subshell in its own process group, so the budget-exhaustion `kill -- -$$` only signaled the parent's group and leaked every subshell's curl child past the deadline. Replace the Darwin handler with a per-`CURL_PIDS` loop running `kill -- -<pid>` against each recorded subshell pgid, terminating the whole subtree (subshell + curl substitution + descendants) together. The original `kill -- -$$` is intentionally NOT retained as a Darwin fallback: with `set -m` active, `$$`'s group contains the validator itself, so signaling it would kill the script before it writes the per-claim `UNKNOWN(timeout)` rows and the sidecar (verified empirically: exit 143, sidecar absent, fail-soft contract broken). When `set -m` silently fails the script now emits a stderr `WARNING:` line so operators know orphan-curl cleanup is degraded. New Test 20 (Darwin-only) in `test-validate-citations.sh` runs the validator against a hanging fake-curl shim with `--budget-seconds 1` and pins the regression class: validator exited 0, sidecar produced with `UNKNOWN | timeout` rows for the hung URLs, no surviving fake-curl PIDs after the kill loop. Linux is unaffected (the `setsid` re-exec keeps curl children in the script's session, where a single `kill -- -$$` still works). Sibling docs updated in sync (`validate-citations.md`, `test-validate-citations.md`, `references/citation-validation-phase.md`). Closes #662.

## [7.16.13] - 2026-04-26

### Fixed

- `skills/research/references/citation-validation-phase.md` — reorder §2.7.1 skip preconditions to match `skills/research/SKILL.md` Step 2.7's emission order: `BUDGET_ABORTED=true` budget-abort gate FIRST (proceed to Step 4 because Step 3 was already skipped), then missing/empty `$RESEARCH_TMPDIR/research-report.txt` empty-synthesis gate SECOND (proceed to Step 3). Each gate now explicitly names its downstream branch in the prose. The line-23 prose previously folded `BUDGET_ABORTED` into the "no synthesis to validate" rationale for the Step 3 path; the budget-abort cause is now removed from that list and the empty-synthesis explanation states that `BUDGET_ABORTED=true` is handled by the budget-abort gate above and never reaches the empty-synthesis branch. Also updates the §2.7.6 "Step 2.7 → Step 3 control-flow summary" diagram to spell out the two ordered input gates with their distinct downstream targets, replacing the prior `skip if empty/budget-aborted` line that conflated the two skips. SKILL.md Step 2.7 was already correct; this is a documentation-only alignment fix. Closes #666.

## [7.16.12] - 2026-04-26

### Fixed

- `skills/review/SKILL.md` (Step 3a), `skills/implement/SKILL.md` (Step 5 quick-mode), and `skills/design/references/plan-review.md` — pass `--substantive-validation --validation-mode` to `collect-agent-results.sh` so banner-only reviewer output (e.g., a CLI `Authentication required` banner) is rejected as `STATUS=NOT_SUBSTANTIVE` rather than passing as `STATUS=OK` and getting merged into round-1 dedup/voting. NOT_SUBSTANTIVE flows through the existing Runtime Timeout Fallback (`skills/shared/external-reviewers.md:35`), triggering the same Claude-subagent fallback as a timeout. The three call sites all use prompts that demand "numbered findings ... If NO issues, output exactly NO_ISSUES_FOUND" — the exact format `--validation-mode` is designed for (30-word floor + `NO_ISSUES_FOUND` short-circuit + citation requirement). Per dialectic resolutions: DECISION_1 (3-0 voted) skipped `skills/design/SKILL.md:199` (sketch collector with `--timeout 1260` and prose-paragraph contract); DECISION_2 (2-1) added structural-test pins (`scripts/test-{review,design,implement}-structure.sh` plus their sibling `.md` contracts) so future edits cannot silently drop the flags; DECISION_3 (0-3, OVERRULES synthesis) left `/design` plan-review prompts unchanged — ship and revisit only if monitoring shows chronic NOT_SUBSTANTIVE rate. `docs/external-reviewers.md` "Output Validation" rewritten as two layers (default sentinel/non-empty/retry vs opt-in substantive check) with a per-skill opt-in matrix; `skills/shared/external-reviewers.md` gets a cross-reference note; `scripts/collect-agent-results.sh` header drops `/research`-only scoping language. Closes #661.

## [7.16.11] - 2026-04-26

### Fixed

- `skills/research/references/adjudication-phase.md` — line 5 of the **Contract** paragraph named `$RESEARCH_TMPDIR/research-synthesis.txt` as the consumed input artifact, but the `/research` pipeline standardizes on `$RESEARCH_TMPDIR/research-report.txt` and no other in-repo reference creates the `research-synthesis.txt` filename. A reader/implementer following only that line would look for a non-existent path. Replace `research-synthesis.txt` with `research-report.txt` and explicitly state that the validated body lives under the `## Revised Research Findings` header (with fallback to Step 1.4's `## Research Synthesis` header when no findings were accepted at validation), aligning the one-line Contract summary with `validation-phase.md`, `research-phase.md`, and `SKILL.md` Step 2.5. Closes #665.

## [7.16.10] - 2026-04-26

### Fixed

- `skills/research/scripts/validate-citations.md` — add the missing `curl-unavailable` row to the Reason vocabulary table. The script emits `STATUS=UNKNOWN(curl-unavailable)` at line 353 when the `curl` binary is not found on PATH, and the sibling reference `skills/research/references/citation-validation-phase.md` already documents this token, but the script's own contract `.md` table omitted it. A cross-check of every `STATUS=...` emission in `validate-citations.sh` against the table confirmed `curl-unavailable` was the only missing token. Closes #664.

## [7.16.9] - 2026-04-26

### Fixed

- `scripts/tracking-issue-write.sh` — add a paginated, multi-anchor-fail-closed `find-anchor` read-only subcommand that reuses the existing `list_anchor_comments` (`gh api --paginate`) and `filter_anchor_ids` (strict v1 first-line + BOM-strip) helpers. Stdout envelope: `ANCHOR_COMMENT_ID=<id>` for one match, empty value for zero, `FAILED=true ERROR=multiple anchor comments found (ids: <list>)` exit 2 for multi-anchor (mirrors the existing `upsert-anchor` marker-search-fallback). `skills/implement/SKILL.md` Step 0.5 Branch 2 (`--issue $ISSUE_ARG`) and Branch 3 (`--issue $RECOVERED_N`) now invoke the subcommand instead of the buggy inline `gh api .../comments | head -1` lookup, parsing `FAILED=true` first to abort on multi-anchor / gh failure before extracting `ANCHOR_ID`. The legacy lookup silently missed anchors past page 1 of issue comments and silently picked one anchor when multiple existed, causing `upsert-anchor` to plant an empty seed alongside the missed anchor (silent canonical-state data loss on tracking issues with >30 comments). Per dialectic resolution DECISION_1 (THESIS=3, ANTI_THESIS=0) the existing `upsert-anchor` marker-search-fallback (lines 568-609) is left byte-identical — `find-anchor` is a parallel subcommand reusing the same shared helpers, not a refactor of the working write path. New tests (l)/(m)/(n)/(o) in `scripts/test-tracking-issue-write.sh` cover zero-anchors / one-anchor / multi-anchor / pagination across >100 comments — case (o)'s stub is sensitive to whether `--paginate` is in the `gh api` argv, so a future drop of `--paginate` from `list_anchor_comments` fails the test. New structural assertion (14) in `scripts/test-implement-structure.sh` pins both find-anchor invocations in SKILL.md Branch 2/3 and rejects any revert to the legacy `gh api .../comments | head -1` pattern. Updates `scripts/tracking-issue-write.md` (Purpose paragraph, Success keys table, exit-code 2 description, find-anchor invariant section), `scripts/test-tracking-issue-write.md`, `scripts/test-implement-structure.md`, and SKILL.md Load-Bearing Invariant #4 to name `find-anchor` for read-only discovery. Closes #654.

## [7.16.8] - 2026-04-26

### Fixed

- `skills/implement/scripts/check-review-changes.sh` — replace the union-of-untracked detection (which flipped `FILES_CHANGED=true` on ANY pre-existing untracked file in the working tree) with a sorted pre-/review baseline + post-/review delta computed via `comm -23 | sed '/^$/d'`. The script now emits two stable-order stdout keys — `FILES_CHANGED=true|false` and `UNTRACKED_BASELINE=present|missing` — and degrades gracefully on bad CLI input (parse errors emit `ERROR=…` on stderr and route to the missing-baseline path on stdout, preserving the always-2-keys, exit-0 contract). `skills/implement/SKILL.md` Step 5 captures the baseline once via `set -o pipefail` subshell with on-failure cleanup of any stale prior baseline; Step 6 passes `--baseline` and logs to Warnings on `UNTRACKED_BASELINE=missing`. New sibling contract `check-review-changes.md` and 8-case offline regression harness `test-check-review-changes.sh` (wired via `Makefile` and excluded from `agent-lint.toml`) pin the new behavior including the empty-vs-missing distinction and the `echo ""` → `comm` → `sed` safety net. Closes #651.

## [7.16.7] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-umbrella-body.sh` — fix failure-as-success masking on the body-write path (#645). Add a `[ -w "$TMPDIR" ]` writability preflight emitting the documented `ERROR=tmpdir not writable: <path>` stderr line; replace the grouped redirect with a checked write + atomic rename via an unpredictable `mktemp` partial → `[ -s ]` verify → `mv` into place; reject pre-existing non-regular `$OUT` (defends against the BSD `mv source dir/` silent-nesting class on macOS, caught during code review by Codex); emit `UMBRELLA_BODY_FILE=` / `UMBRELLA_TITLE_HINT=` ONLY past the `mv` gate. Critical bash-gotcha avoided: the grouped redirect remains standalone (no trailing `||`) so `set -e` aborts on inner `cat`/`awk` failure — bash suppresses errexit inside a compound on the left of `||`, which would have re-introduced the very masking this PR fixes. New runtime conformance harness `test-render-umbrella-body.sh` (23 assertions across 6 cases) wired into `make lint` via the `test-render-umbrella-body` Makefile target and documented in `docs/linting.md`. Sibling `render-umbrella-body.md` enumerates the canonical `ERROR=` taxonomy and the umbrella `SKILL.md ## Script contracts` section adds the new harness bullet. Closes #645.

## [7.16.6] - 2026-04-26

### Fixed

- `docs/external-reviewers.md` — replace the single "Output capture" bullet (which read "Captures stdout to a specified output file" as if universal) with two sub-bullets that distinguish the two patterns the `run-external-agent.sh` wrapper supports: stdout capture under `--capture-stdout` (Cursor pattern; `skills/review/SKILL.md:146-148, 177-179`), and tool-managed output paths when the reviewer takes its own output-path argument such as Codex's `--output-last-message` (Codex pattern; `skills/review/SKILL.md:160-163, 186-190`). The prior single bullet implied a universal stdout-capture behavior, so a skill author following the doc could omit `--output-last-message` for Codex (yielding an empty output file) or add `--capture-stdout` redundantly. Closes #660.

## [7.16.5] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-batch-input.sh` — tighten the per-entry `depends_on` validator to reject non-integer numbers. The `bad_deps` jq predicate now disqualifies any value where `. != (. | floor)` in addition to the existing non-number / out-of-range checks, so `depends_on:[1.5]` fails with the documented `ERROR=pieces.json entry <i> has out-of-range depends_on values:` line + exit 1 instead of silently passing and leaking `PIECE_<i>_DEPENDS_ON=1.5` downstream into DAG construction. Adds a regression case to `test-render-batch-input.sh` pinning the contract; updates the sibling `render-batch-input.md` Test coverage paragraph and `test-render-batch-input.md` cases / edit-in-sync rules to reflect the new boundary assertion. Closes #647.

## [7.16.4] - 2026-04-26

### Fixed

- `skills/review/references/voting.md` — qualify the "Zero accepted in-scope findings" parenthetical on line 27 so it correctly distinguishes diff-mode and slice-mode OOS routing. The prior text ("OOS items accepted for issue filing are processed separately by `/implement`.") read as an unconditional rule on first encounter, but the same file's "Slice mode" bullet (further down) specifies that under `--create-issues` slice-mode runs, `/review` Step 4b files OOS findings inline via `/issue` and bypasses the `/implement` Step 9a.1 pipeline entirely. Round-1 readers hit the misleading parenthetical before reaching the qualifying bullet. The new wording names the routing explicitly per mode and points to the bullets by stable label rather than by line number. Closes #658.

## [7.16.3] - 2026-04-26

### Fixed

- `skills/review/diagram.svg` — correct the "Launch Reviewers" rect label from `Reviewers (2 Claude + 2 Codex + Cursor)` to `Reviewers (1 Claude + 1 Codex + 1 Cursor)` so the rendered diagram matches the documented 3-reviewer panel topology used by `/review` (`skills/review/SKILL.md:10`, `docs/external-reviewers.md:12`, `docs/review-agents.md:92`). The previous label implied a 5-reviewer panel that never existed in the implementation. Closes #657.

## [7.16.2] - 2026-04-26

### Fixed

- `docs/external-reviewers.md` — correct the "Timeout Handling" range from "typically 600-900 seconds" to "typically 1200 seconds for voting and 1800 seconds for code review". Production code uses `--timeout 1800` in `skills/review/SKILL.md` (4 sites) and `--timeout 1200` in `skills/shared/voting-protocol.md` (2 sites); the prior range understated real kill times by 2-3x and would mislead an operator diagnosing a "reviewer timed out" event. Closes #656.

## [7.16.1] - 2026-04-26

### Fixed

- `scripts/cursor-wrap-prompt.md` — align the Callers registry with the actual `cursor-wrap-prompt.sh` invocations across the codebase. The registry undercounted call sites in three places and listed one stale entry, weakening the auditor invariant the registry exists for ("auditors can verify every Cursor invocation routes through the max-mode wrapper"): `skills/review/SKILL.md` corrected from `(1)` to `(2 — diff-mode and slice-mode Cursor reviewer blocks)` (the original code-review finding); `skills/research/references/research-phase.md` corrected from `(1)` to `(3 — standard-mode Cursor lane and deep-mode Cursor slots 1 and 2)`; new bullet added for `skills/research/references/adjudication-phase.md (1 — Cursor judge launch)`; stale `skills/loop-review/SKILL.md` entry removed (the file no longer invokes the wrapper). Header total updated from `12 wrapped launch strings in 11 files` to `15 wrapped launch strings in 11 files`. Closes #655.

## [7.16.0] - 2026-04-26

### Added

- `/skill-evolver [--debug] <skill-name>` — research-and-file-issues orchestrator that targets an existing larch skill. Validates the skill name (regex + plugin-repo CWD + `skills/<name>/SKILL.md` or `.claude/skills/<name>/SKILL.md`) via `skills/skill-evolver/scripts/validate-args.sh`, then invokes `/research --scale=deep` against repo-local sibling skills + reputable external sources (Anthropic / OpenAI / DeepMind / ≥500-star OSS) for concrete actionable improvements with citations. The research prompt mandates an `ACTIONABLE_IMPROVEMENTS_COUNT=<n>` machine-readable footer (with a deterministic shape-based fallback when the lane synthesis omits it). On `≥1` improvement, distills the findings into a task description and delegates to `/umbrella` with `--label evolved-by:skill-evolver --label skill:<name> --title-prefix "[skill-evolver:<name>] "`; `/umbrella`'s own classifier picks one-shot (single issue) vs multi-piece (umbrella + one child per piece). Step 3 reads `/umbrella`'s `UMBRELLA_VERDICT` and only quotes `UMBRELLA_NUMBER` / `UMBRELLA_URL` on the multi-piece success path or `CHILD_1_URL` on the one-shot path; failure / dry-run / partial shapes get a clear "did not return a recognized success shape" warning instead of fabricated URLs. Research-and-file-issues only — does NOT modify the target skill's files; implementation lands later via `/fix-issue` (per filed issue), `/improve-skill` (single judge-design-implement iteration), or `/loop-improve-skill` (multi-round). Prerequisite: `/umbrella` must be present in the loaded plugin/session — currently shipped under `.claude/skills/umbrella/` (project-local), not yet promoted to the plugin tree.

## [7.15.8] - 2026-04-26

### Fixed

- `skills/implement/references/anchor-comment-template.md` — lift the outer fence of the "Canonical template" code block from three backticks to four so the inner ` ```mermaid ` blocks no longer terminate it under CommonMark / GitHub-flavored Markdown. The rendered template was previously broken on GitHub (the first inner triple-backtick run was parsed as the outer block's closing fence); anyone copying the template visually rather than via `assemble-anchor.sh` would have gotten a malformed structure. Also escapes the literal pipes in the Edit-in-sync pointers row's documentation reference (`\| OOS issues filed \|`) to silence pre-existing markdownlint MD056 / MD038 warnings on that line; the load-bearing literal `| OOS issues filed |` still appears verbatim at line 110 inside the Run Statistics table of the canonical template, so `scripts/test-implement-structure.sh` assertion (9a) is unchanged. Closes #653.

## [7.15.7] - 2026-04-26

### Added

- `skills/implement/scripts/check-review-changes.md` — sibling contract file for `skills/implement/scripts/check-review-changes.sh` per the AGENTS.md per-script-contract convention. Documents the script's purpose ("detect whether code-review step modified the working tree"), output contract (`FILES_CHANGED=true|false` to stdout, always exit 0), the unstaged/staged/untracked detection union, the known limitation that any pre-existing untracked file flips the flag, the sole call site (Step 6 of `skills/implement/SKILL.md`), read-only/idempotent invariants, and edit-in-sync rules. `agent-lint.toml` skill-local-sibling-`.md` exclude list extended to include the new file (matches the existing pattern for `skills/<name>/scripts/*.md` contracts not cited from the owning SKILL.md). Closes #652.

## [7.15.6] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-batch-input.sh` — harden the LLM-output gatekeeper boundary against malformed `pieces.json`. The prior `PIECES_TOTAL=$(jq 'length' "$PIECES_FILE")` call leaked raw `jq:` parse errors and exited with jq's exit code on parse failure, breaking the script's documented `ERROR=…` + exit 1 grammar. Replaced with a captured-stderr guard that emits a stable `ERROR=invalid pieces.json: <reason>` line and exits 1. Added a top-level type assertion (must be a JSON array) using the same prefix so a valid-JSON-but-non-array root (object with ≥2 keys, string root, etc.) no longer crashes the per-entry loop with raw jq output. New regression harness `.claude/skills/umbrella/scripts/test-render-batch-input.sh` (with sibling `.md` contract) pins both gatekeeper failure modes plus the pre-existing too-few-entries path and the valid-baseline happy path; wired into `make lint` via the new `test-umbrella-render-batch-input` Makefile target. Updated `render-batch-input.md` Test coverage section and added a script-catalog bullet to the umbrella `SKILL.md`. Closes #646.

## [7.15.5] - 2026-04-26

### Changed

- `scripts/test-loop-fix-issue-skill-md.sh` Assertion B — pins the `*/..|*/../*` path-component guard alongside the existing `/tmp/*|/private/tmp/*` prefix check, so removing the `..` guard from `skills/loop-fix-issue/SKILL.md` would now fail `make lint`. Achieves parity with the sibling driver harness's Assertion E pin on `driver.sh`'s `LOOP_TMPDIR` `..` guard. Sibling `scripts/test-loop-fix-issue-skill-md.md` and `docs/linting.md` updated in lock-step (assertion count 12→13, "Why these tokens are byte-pinned" rationale documents both dimensions of the security boundary). Closes #649.

## [7.15.4] - 2026-04-26

### Changed

- `skills/fix-issue/scripts/test-issue-lifecycle.sh` — adds Fixture 7 covering the `cmd_close` partial-success retry path documented in `skills/fix-issue/scripts/issue-lifecycle.md` "Partial-success semantics". Two `run_case` calls: the first forces probe + close to fail (asserting the DONE comment was posted before the failures, and that the probe-failure WARNING fires on stderr); the second is a clean retry. A combined-log `grep -c` assertion pins exactly two `comment|42|DONE` lines across the retry sequence — the regression guard for the documented duplicate-comment retry behavior. Top-of-file Fixtures comment block extended; total assertion count 43→50. Closes #642.

## [7.15.3] - 2026-04-26

### Fixed

- `scripts/test-implement-structure.sh` line 129 — the explanatory block comment for assertion (4) said "at least 4 occurrences" while the actual enforcement on line 135 (`(( occurrences < 5 ))`), the error message on line 136 ("expected at least 5"), and the sibling contract `scripts/test-implement-structure.md` all require at least 5. Aligned the comment to "at least 5 occurrences" so a maintainer reading only the comment sees the correct threshold. Documentation-only edit; no behavioral effect on the test. Closes #650.

## [7.15.2] - 2026-04-26

### Changed

- `.claude/skills/umbrella/scripts/test-umbrella-emit-output-contract.sh` — adds a `c6b` structural assertion pinning the `(<UMBRELLA_FAILURE_REASON>)`-parenthetical variant of the multi-piece partial breadcrumb literal. SKILL.md Step 4 documents two on-disk shapes for the same partial case (with-reason / fallback); the existing `c6` assertion only pinned the fallback, so a future edit could remove or reword only the parenthetical variant unnoticed. Sibling `test-umbrella-emit-output-contract.md` updated in lock-step (assertion count 12→13, coverage table now lists eight concrete literals split as c1–c5, c6, c6b, c7, supporting prose and Edit-in-sync rules aligned). Closes #644.

## [7.15.1] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/render-batch-input.md` line 19 — the edit-in-sync rule referenced the consuming `/issue` parser as `/Users/zhupanov/larch1/skills/issue/scripts/parse-input.sh`, a machine-local absolute path that does not exist on any clone other than the original author's. Replace with the repo-relative form `skills/issue/scripts/parse-input.sh` so contributors following the rule on any machine resolve to the actual shipped parser. Documentation-only change; no behavioral effect. Closes #643.

## [7.15.0] - 2026-04-26

### Added

- `/fix-issue <umbrella#>` now accepts an umbrella issue (detected by body literal `Umbrella tracking issue.` OR title prefix `Umbrella:` / `Umbrella —`) and dispatches to the next eligible child instead of working on the umbrella body itself. Neither the umbrella nor the chosen child needs a `GO` comment — the umbrella body is the approval signal, and children inherit approval from the umbrella's existence. Children are parsed from markdown task-list items (`- [ ] #N — ...`) in body order; cross-repo references (`owner/repo#N`) and prose `#N` mentions are filtered out at parse time. When all parsed children close, the umbrella is automatically renamed to `[DONE]` and closed (idempotent: concurrent finalize attempts won't double-comment, and a partial-success "rename + comment done but close failed" is recoverable on retry via a close-only retry path). Auto-pick mode (no positional argument to `/fix-issue`) NEVER selects umbrellas — the umbrella state machine is opt-in only via explicit positional argument. New scripts: `skills/fix-issue/scripts/umbrella-handler.sh` (detect / list-children / pick-child) and `skills/fix-issue/scripts/finalize-umbrella.sh` (idempotent rename + close composer). New `--lock-no-go` mode in `skills/fix-issue/scripts/issue-lifecycle.sh comment` for locking umbrella-dispatched children without a GO sentinel. Closes #622.

## [7.14.12] - 2026-04-26

### Changed

- `scripts/test-review-structure.sh` — three new structural assertions (10/11/12) pin the `/review` skill's three-way slice-mode activation contracts introduced by PR #638. Assertion (10) is a line-scoped grep pipeline (parallel to (5a)/(5b)/(5c)) requiring at least one `SKILL.md` line to carry `Slice mode`, `--slice`, `--slice-file`, AND `positional` together. Assertions (11) and (12) are verbatim `grep -Fq` pins for the empty-positional abort message (`**⚠ --create-issues requires a slice description (--slice <text>, --slice-file <path>, or trailing positional text). Aborting.**`) and the positional-vs-slice-flag mutual-exclusion abort message (`**⚠ Positional slice text cannot be combined with --slice or --slice-file. Aborting.**`). Final PASS line count bumped from 9 to 12; file-header comment block extended; sibling `scripts/test-review-structure.md` contract updated. Closes #637.

## [7.14.11] - 2026-04-26

### Changed

- `/review --create-issues <description>` now activates slice mode with the trailing positional remainder as `SLICE_TEXT` (equivalent to `/review --slice "<description>" --create-issues`). Previously this invocation hard-aborted with `**⚠ --create-issues requires --slice or --slice-file. Aborting.**`, even though it is the most natural human-typed form. `--slice <text>` and `--slice-file <path>` remain unchanged; the positional form is gated on `--create-issues` and mutually exclusive with the two flag forms. New abort message names all three activation forms when the slice description is truly absent. Six prose edits to `skills/review/SKILL.md` (argument-hint, Flags paragraph, `--create-issues` bullet, Mutual exclusion section, `## Slice Mode` header, Step 1 slice-resolve, both Step 1 subheadings, Diff mode bullet) plus one to `skills/review/references/voting.md` (Diff/Slice mode definitions now reference SKILL.md's three-way activation rule instead of flag presence, so positional-slice runs are correctly routed away from the `oos-accepted-review.md` staging artifact). The `/loop-review` driver (uses `--slice-file`) and `/implement` Step 5 (no `--create-issues`) are unaffected. Closes #630.

## [7.14.10] - 2026-04-26

### Fixed

- `skills/loop-fix-issue/scripts/driver.sh` header comment block (lines 54-56 on `main`) claimed `LARCH_LOOP_FIX_ISSUE_CLAUDE_OVERRIDE` was "Documented in SECURITY.md as test-only", but `SECURITY.md` only documents the parallel `LARCH_LOOP_REVIEW_CLAUDE_OVERRIDE` (under `## /loop-review subprocess invocation`); no entry exists for `LARCH_LOOP_FIX_ISSUE_CLAUDE_OVERRIDE`. The sibling `skills/loop-fix-issue/scripts/driver.md:99` already correctly defers SECURITY.md registration to Tier-2 stub-shim work. Apply option (b) from the issue: rephrase the comment block to point readers at `driver.md` and explicitly defer SECURITY.md registration to Tier-2, mirroring the wording structure used by the post-#633 loop-review-side `driver.sh` comment block; cross-reference uses a section-heading anchor (`## /loop-review subprocess invocation`) rather than a fragile line number. Comment-only change; no behavioral effect; assertion K of `scripts/test-loop-fix-issue-driver.sh` (which greps for the env-var name token) continues to pass. Closes #632.

## [7.14.9] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/parse-args.sh`'s `read_unquoted_token` arm at line 103 emitted the frozen template `embedded newline in quoted value at offset <N>` for backslash-escaped newlines in **unquoted** values, contradicting both `parse-args.md:58`'s frozen list (which scoped that template to quoted values) and the script's own header comment block. Introduce a distinct frozen template `ERROR=embedded newline in unquoted value at offset <N>` for the unquoted backslash-newline path; cases 18 and 25 in `test-umbrella-parse-args.sh` (genuinely quoted-value paths) keep the existing template; case 24 (the unquoted backslash-newline repro) is retargeted to the new substring and a one-line guard comment warns future editors not to dedupe the distinct templates back into a shared substring. Lockstep updates: `parse-args.md` frozen list and TASK-section prose (now states the rule covers both quoted and unquoted phase-1 flag-value paths); the Outside-quotes bullet (now documents `\<LF>` rejection); the edit-in-sync rule (narrowed to clarify that wording-only ERROR= changes do NOT require a SKILL.md update because Step 0 surfaces ERROR= lines verbatim and does not parse them); `parse-args.sh`'s `read_unquoted_token` helper comment (now says "next non-newline byte"); `test-umbrella-parse-args.md` case-24 coverage-row prose; and `docs/linting.md`'s `test-umbrella-parse-args` row (frozen-template count 11 → 12). Lexer behavior is unchanged — only stderr text and surrounding documentation. Closes #616.

## [7.14.8] - 2026-04-26

### Fixed

- `skills/loop-fix-issue/scripts/driver.sh` Usage block (lines 9-19) gains a `--no-admin-fallback` entry, matching the existing parser at line 148 and the SKILL.md frontmatter (line 4) + Flags section (line 21) advertisement. Pre-existing inconsistency surfaced as out-of-scope by the codex reviewer during an earlier `/loop-fix-issue` design phase. Pure docstring fix; no behavioral change. Closes #626.

## [7.14.7] - 2026-04-26

### Added

- New structural regression harness `.claude/skills/umbrella/scripts/test-umbrella-emit-output-contract.sh` (plus sibling contract `.md`) pinning the `/umbrella` SKILL.md Step 4 (Emit Output) prose contract — closes the gap surfaced as out-of-scope during the `/implement` run for #571. The harness mirrors the `test-fix-issue-bail-detection.sh` pattern (awk-bounded extraction + literal-substring assertions, fail-fast) and runs 12 assertions against two awk-extracted blocks: the SKILL.md Step 4 block (orchestrator-attribution sentence + single-emission-point invariant + the seven concrete canonical breadcrumb shape literals — one-shot filed/dedup'd/failed; multi-piece success/dry-run/partial/children-batch-failed) and the `helpers.md` `emit-output` subsection (`stderr` reserved for parse/validation errors, breadcrumb emitted by orchestrator not by `helpers.sh`, explicit `wire-dag` carve-out preserving its independent stderr-warning behavior). The harness is structural — it does NOT exercise `helpers.sh emit-output` at runtime (which remains exercised indirectly via SKILL.md integration; `test-helpers.sh` continues to scope `emit-output` out per its sibling contract). Wired into `make lint` via a dedicated `test-umbrella-emit-output-contract` Makefile target alongside `.PHONY` + `test-harnesses` updates; documented under the Makefile Targets table in `docs/linting.md`; cross-linked from the `.claude/skills/umbrella/SKILL.md` Script contracts inventory and the refreshed "Out of scope" line in `.claude/skills/umbrella/scripts/test-helpers.md`. Two adjacent doc-precision fixes were applied during code review: SKILL.md's stale "wire into `make lint` as a follow-up issue" line for `test-helpers.sh` was updated to reflect that `test-umbrella-helpers` is already a `make lint` prerequisite, and the new `make test-umbrella-emit-output-contract` target was added to `docs/linting.md`'s Makefile Targets table to match the established one-row-per-harness convention. Closes #602.

## [7.14.6] - 2026-04-26

### Fixed

- `SECURITY.md` line 97, `skills/loop-review/scripts/driver.md` line 71, and `skills/loop-review/scripts/driver.sh` lines 51-54 each described `LARCH_LOOP_REVIEW_CLAUDE_OVERRIDE` as "used exclusively / ONLY by `scripts/test-loop-review-driver.sh` Tier-2 fixtures", but the shipped test script's lines 5-10 explicitly state it is the Tier-1 structural test only and that Tier-2 stub-shim integration tests using the override are tracked as a focused follow-up — the Tier-1 test only references the env-var name in assertion J without exercising the override at runtime. Rephrase all three sites to say the env var is reserved for forthcoming Tier-2 stub-shim integration tests in `scripts/test-loop-review-driver.sh`, keeping the production-safety warnings ("Never set this env var in production"; same-user arbitrary-executable risk) intact. Doc-only alignment; no fixtures added; env-var name unchanged. Closes #627.

## [7.14.5] - 2026-04-26

### Fixed

- `skills/loop-improve-skill/scripts/driver.sh:402-404`'s slim `invoke_claude_p` (used only for the Step 5a post-iter-cap re-judge) now passes `--permission-mode bypassPermissions` adjacent to the FINDING_7 `--plugin-dir "$CLAUDE_PLUGIN_ROOT"` argv pair, mirroring the `iteration.sh` fix from issue #585. Without this flag, an in-child tool-permission prompt could stall the post-iter-cap re-judge subprocess until the 1200s watchdog fires — the same halt-class variant that #585 closed in the kernel, now closed in the driver as well. `scripts/test-loop-improve-skill-driver.sh` adds a Tier-1 `check_contains` needle for the new flag literal and a `--permission-mode) shift 2 ;;` arm in the stub `claude` parser adjacent to `--plugin-dir`'s arm, so any future Tier-2 fixture reaching Step 5a does not mis-consume `bypassPermissions` as the prompt; `scripts/test-loop-improve-skill-driver.md` enumerates the new permission-mode contract alongside FINDING_7/9/10. `SECURITY.md`'s `## Trust Model` carve-out paragraph is extended to cover both `iteration.sh` and `driver.sh` launch sites, and a peer bullet is added under `## /loop-improve-skill subprocess invocation` parallel to the existing bullet in the `## /improve-skill subprocess invocation` subsection. `docs/installation-and-setup.md` line-53 minimum-CLI-version note updated to reflect that both `claude -p` launch sites in `/loop-improve-skill` (per-iteration kernel + post-iter-cap re-judge) are now pinned. Closes #614.

## [7.14.4] - 2026-04-26

### Added

- New Tier-1 structural regression harness pair for `/loop-fix-issue` mirroring the `/loop-review` precedent: `scripts/test-loop-fix-issue-driver.sh` (20 assertions over `skills/loop-fix-issue/scripts/driver.sh` — `set -euo pipefail`, three-up `CLAUDE_PLUGIN_ROOT` derivation tolerated through the `if [[ -z … ]]` guard, `cleanup_on_exit` EXIT trap, the `if [[ ]]` form of `LOOP_TMPDIR`'s `/tmp/*|/private/tmp/*` prefix guard plus the `..` path-component guard, `invoke_claude_p_skill` definition with FINDING_7/9/10 contracts, the live `SETUP_SENTINEL='find & lock — found and locked'` assignment, all four Step-0 sub-sentinels including the defensive `no recognized Step 0 literal` fallback, an exact count of four `LOOP_PRESERVE_TMPDIR="true"` abnormal-exit assignments plus the default-`false` initialization, the `LARCH_LOOP_FIX_ISSUE_CLAUDE_OVERRIDE` token, and the live `printf '/fix-issue%s\n'` prompt-construction line tied to `fix-issue-prompt.txt`) and `scripts/test-loop-fix-issue-skill-md.sh` (12 assertions mirroring `test-loop-review-skill-md`'s A-F shape: `allowed-tools: Bash, Monitor` frontmatter, `LOOP_FIX_ISSUE_DRIVER_LOG_FILE` env-overridable default with `/tmp/*|/private/tmp/*` validation, the `📄 Full driver log:` and `📄 Full driver log (retained):` log-path visibility lines, `run_in_background: true` AND `persistent: true` Monitor directives, the byte-verbatim filter regex, and breadcrumb-prefix parity with `driver.sh`'s three `printf` helpers). Both harnesses ship with sibling `.md` contract files per the AGENTS.md "Per-script contracts live beside the script" rule, are wired into `make lint` via `.PHONY`, the `test-harnesses` aggregate, and two explicit recipe targets adjacent to the existing `test-loop-review-*` entries, and are documented under the Makefile Targets table in `docs/linting.md`. `skills/loop-fix-issue/SKILL.md` gains a `## Verification` section pointing at both new harnesses (parallels `skills/loop-review/SKILL.md`); `skills/loop-fix-issue/scripts/driver.md`'s `## Test-only override` paragraph is rewritten to drop the "harness is a future addition" line and reflect that a Tier-1 harness now exists, while flagging that override-driven Tier-2 coverage remains future work. Closes #609.

## [7.14.3] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/SKILL.md` anti-patterns block (lines 16-17) and Step 3B.4 narrative (line 147) referred to `scripts/wire-dag.sh` and `check-cycle.sh` as if they were independent scripts. The shipped coordinator is `.claude/skills/umbrella/scripts/helpers.sh` exposing `wire-dag` and `check-cycle` subcommands; the bash invocation at line 144 and script inventory at lines 202-203 already used the correct form. Update the three offending prose locations to point at the real entry points (`helpers.sh wire-dag` / `helpers.sh check-cycle`) so future maintainers are not directed at filenames that do not exist. Doc-only edit; no script or behavior changes. Closes #618.

## [7.14.2] - 2026-04-26

### Changed

- `.claude/skills/umbrella/SKILL.md` Step 4 canonical `output.kv` grammar gains an optional `UMBRELLA_FAILURE_REASON=<text>` field (only present on multi-piece partial — children created, umbrella creation failed). Step 3B.3's umbrella-creation-failure path now derives the value from `/issue`'s failure signals (stderr `**⚠ /issue: create failed for item 1: …**` line first, `ISSUE_1_ERROR=…` from stdout when present for dep-link / transitive paths, and a constrained stdout fallback restricted to `^ISSUE_1_` / `^ISSUES_FAILED=` prefixes), with sanitization that strips control characters, collapses whitespace, strips markdown metacharacters (so the value cannot break the surrounding `**…**` formatting), redacts secrets / internal URLs / PII with the canonical `<REDACTED-TOKEN>` / `<INTERNAL-URL>` / `<REDACTED-PII>` tokens, and trims to ~200 chars. Step 4's multi-piece-partial human-summary template interpolates the reason when present (`**⚠ /umbrella: <N> children created but umbrella creation failed (<reason>). Children remain unlinked.**`) and falls back to the original wording when no failure signal could be extracted. The `## Sub-skill Invocation` section gains a narrow stderr-consumption carve-out documenting that Step 3B.3 reads `/issue`'s stderr in addition to its stdout grammar. `helpers.sh emit-output` is unchanged (the new key is accepted by the existing `^[A-Z][A-Z0-9_]*=` validator). Closes #603.

## [7.14.1] - 2026-04-26

### Fixed

- `docs/linting.md`'s `make test-umbrella-parse-args` table row and `CHANGELOG.md` entry [7.13.9] now match the actual harness and ERROR= template count: the row body says "25 cases" (was "22 cases") and "11 templates" (was "10 templates"), aligned with the 25 numbered cases in `.claude/skills/umbrella/scripts/test-umbrella-parse-args.sh` and the 11 frozen ERROR= templates in `.claude/skills/umbrella/scripts/parse-args.md`. The drift was introduced when umbrella parse-args FINDING_1 / FINDING_2 added cases 23-25 without updating the lint doc and changelog template count. Closes #615.

## [7.14.0] - 2026-04-26

### Changed

- `/alias` now auto-detects Claude plugin source repos (two-file predicate `.claude-plugin/plugin.json` AND `skills/implement/SKILL.md` at the git repo root, matching `validate-args.sh:133`) and routes the generated alias to `skills/<name>/SKILL.md` (exported plugin skill) when the predicate matches; outside plugin repos the default stays `.claude/skills/<name>/SKILL.md` (dev-only). New `--private` flag forces `.claude/skills/<name>/` even inside a plugin repo (escape hatch); in non-plugin repos `--private` is a no-op. Target-directory resolution is extracted into `skills/alias/scripts/resolve-target.sh` (3-0 dialectic decision over inline bash) so SKILL.md Steps 2/3/4 thread a single `$TARGET_DIR` value computed once at Step 2 by a non-eval line-by-line allowlist parser, eliminating the silent path-split failure class. Two CI-wired test harnesses lock the contract: `scripts/test-alias-target-resolution.sh` exercises the helper across six cases of `(plugin-detect × --private × git-state)` plus arity and validation guards; `scripts/test-alias-structure.sh` pins SKILL.md prompt-side contracts so a future edit cannot silently re-introduce hardcoded paths in Steps 2/3/4. Backfills the AGENTS.md-required sibling `skills/alias/scripts/generate-alias.md` contract doc. Updates README, `docs/skills.md`, `docs/workflow-lifecycle.md` for the new arg signature and routing behavior, and `docs/linting.md` for the new make targets. Closes #597.

## [7.13.18] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/SKILL.md` Step 3B.2 children-batch-failure abort path now mirrors Step 3B.3's umbrella-failure pattern: capture the failure as session state, omit `UMBRELLA_NUMBER` and `UMBRELLA_URL` from `output.kv` entirely (do NOT write them with blank values), skip 3B.3 / 3B.4, and defer the human summary to Step 4 (the single emission point). A fifth Step 4 human-summary shape — `multi-piece children-batch-failed` — distinguishes the new state ("children batch had failures, umbrella never attempted") from the existing `multi-piece partial` shape ("children created, umbrella failed"). Closes #610.

## [7.13.17] - 2026-04-26

### Fixed

- `skills/improve-skill/scripts/iteration.sh::invoke_claude_p` (lines 590-592) now passes `--permission-mode bypassPermissions` adjacent to the FINDING_7 `--plugin-dir "$CLAUDE_PLUGIN_ROOT"` argv pair on every `claude -p` child it launches, so an in-child tool-permission prompt cannot stall the non-interactive subprocess until the 3600s `kill -0` watchdog fires. Closes the in-child permission-stall halt-class variant left open after #273 eliminated the post-child-return halt — the parent has no human at the prompt to answer it, so a permission gate previously converted to a silent hang. `scripts/test-improve-skill-iteration.sh` adds Tier-1 `check_contains` for the new flag literal plus a Tier-2 stub-claude argv-log capture (`printf '%s\n' "$*" >> $fixture_tmp/claude-argv.log`) and a per-fixture `grep -Fq` assertion in `run_fixture`; the stub's case-table handles `--permission-mode` as a 2-arg flag (`--permission-mode) shift 2 ;;`) like `--plugin-dir` so the value is not mistaken for the FINDING_9 positional prompt. The fifth fixture `judge_failure_fixture` exits non-zero before parsing flags so its argv path is uncovered by the Tier-2 log — the Tier-1 source pin remains authoritative for that fixture's path; gap is documented in `scripts/test-improve-skill-iteration.md`. `skills/improve-skill/scripts/iteration.md` gains a "Non-interactive permission contract" section under "Security invariants" that frames the actual trust boundary as kernel-composed prompts that transitively carry `/skill-judge` → `/design` → `/larch:im` LLM output plus repo-derived content plus user argv (NOT "no user-typed input"), notes that `bypassPermissions` does not mitigate prompt-injection within that boundary, and points at `docs/installation-and-setup.md` for the minimum CLI version requirement. `SECURITY.md`'s `## Trust Model` paragraph carves out the `/improve-skill` and `/loop-improve-skill` child subprocesses (operator-facing permission flow above is unchanged), and the `## /improve-skill subprocess invocation` subsection adds a peer bullet to the existing FINDING_7/9/10 bullet describing the contract, including the residual prompt-injection risk and fail-fast posture for older `claude` binaries. `docs/installation-and-setup.md`'s Claude prerequisites section gains a minimum-CLI-version note (must support `--permission-mode bypassPermissions`) scoped explicitly to `iteration.sh::invoke_claude_p`, with a SECURITY.md cross-reference for the carve-out. Out-of-scope follow-ups (filed as separate issues): #614 (driver.sh:402 + test-loop-improve-skill-driver.sh sync — now fixed in a subsequent release), #615 (docs/linting.md test-umbrella-parse-args row counts stale), #616 (parse-args.md ERROR template misdescribes unquoted-newline path). Closes #585.

## [7.13.16] - 2026-04-26

### Fixed

- `skills/research/references/research-phase.md:553` quoted a pre-#520 literal `"1 agent (Claude inline only — single-lane confidence)"` that Step 3 no longer emits. #520 replaced single-lane quick mode with K=3 vote-merge, and Step 3 now branches on `LANES_SUCCEEDED` and emits one of three current literals (documented at `skills/research/SKILL.md` Step 0b summary and Step 3 Quick literal assignment). The prose now points at the canonical SKILL.md headers rather than copying a now-wrong byte-quoted literal. Closes #594.

## [7.13.15] - 2026-04-26

### Added

- New opt-in operator script `scripts/repro-claude-p-edit-permissions.sh` plus its sibling contract `scripts/repro-claude-p-edit-permissions.md` (per the `AGENTS.md` per-script-contract rule). The script reproduces the `claude -p` Edit-permission stall observed in #566 across four variants (A=current settings + no kernel flag, B=`--permission-mode bypassPermissions`, C=`.claude/settings.json` replaced with path-qualified `Read`/`Edit`/`Write` allow rules built via `jq`, D=settings file renamed away). Variants A/B do not mutate `.claude/settings.json`; C/D mutate and a single EXIT/INT/TERM trap restores both `.claude/settings.json` and `.claude/settings.local.json` (staged aside for A/C/D), plus the edit target via `git checkout --`. Result classification combines a pinned stall-regex grep on combined stdout+stderr with a `git diff` ground-truth check on the edit target. Variant C is `EXPECTED=observational_only` (records the observed outcome, exits 0). `--smoke-test` mode runs the preflight + variant staging + cleanup round-trip without invoking `claude` for offline structural validation. New `agent-lint.toml` exclusion entry mirrors the `eval-research.sh` / `test-loop-improve-skill-halt-rate.sh` opt-in pattern. The script is opt-in operator instrumentation, NOT a CI gate. Closes #587.

## [7.13.14] - 2026-04-26

### Fixed

- `skills/loop-fix-issue/SKILL.md` lines 100-103 (and surrounding "unfiltered" wording in Step 2 line 62 and Step 5 line 94) no longer claim the driver log at `LOG_PATH` holds "FULL unfiltered output — every breadcrumb, all `/fix-issue` subprocess stdout, all stderr, and any other diagnostic lines." `skills/loop-fix-issue/scripts/driver.sh:102-103` redirects each iteration's `claude -p /fix-issue` stdout to `$LOOP_TMPDIR/iter-N-out.txt` and stderr to `iter-N-out.txt.stderr` (including any `claude-iter-N: TIMED OUT after Xs` watcher diagnostic appended via `>> "$stderr_file"`); driver stdout (captured by the SKILL.md Step-3 outer `> "<LOG_PATH>" 2>&1` redirect) carries only driver-emitted breadcrumbs, the unconditional cleanup `LOOP_TMPDIR=…` line, and the final summary line. SKILL.md's "What the Monitor stream shows vs. what the log file holds vs. where child output lives" subsection is rewritten to describe all three observability surfaces (Monitor stream, `LOG_PATH`, per-iteration sidecars) accurately, with explicit "Does NOT contain" language for child stdout/stderr in `LOG_PATH` and an explicit retention boundary noting that sidecars are wiped on clean success and on `--max-iterations` cap-hit (also a clean exit) — they are retained only when `LOOP_PRESERVE_TMPDIR=true`, which the driver sets on four documented abnormal-exit paths (claude subprocess error, Step 0 error, Step 0 lock failure, sentinel mismatch). `skills/loop-fix-issue/scripts/driver.md` adds an Observability/Retention matrix that pins the same surfaces byte-faithful to `driver.sh` and is the canonical contract; the SKILL.md subsection is the operator-facing mirror. The driver.md retention prose at the existing `## Security boundaries` bullet (formerly "retained on any abnormal exit") is restated in terms of `LOOP_PRESERVE_TMPDIR=true` semantics with the four preserve paths enumerated. The driver.sh header comment block is aligned with the same wording. The `cleanup_on_exit` retained-tmpdir warning at `driver.sh:84` now names both iteration-artifact glob patterns (`${LOOP_TMPDIR}/iter-*-out.txt` and `${LOOP_TMPDIR}/iter-*-out.txt.stderr`) — both rooted under `${LOOP_TMPDIR}` — so artifacts are discoverable in-band on retained paths without consulting docs. New driver.md `## Edit-in-sync` row mandates that the matrix and SKILL.md subsection remain semantically consistent across PRs. Closes #583.

## [7.13.13] - 2026-04-26

### Added

- New `## claude -p permission propagation` section in `docs/configuration-and-permissions.md` documenting empirical findings from auditing how `.claude/settings.json` propagates to non-interactive `claude -p` subprocesses spawned by `invoke_claude_p` in `skills/improve-skill/scripts/iteration.sh` (and the indirect path via `skills/loop-improve-skill/scripts/driver.sh` → `iteration.sh`). The audit was tested against Claude Code CLI version 2.1.119 and answers all five investigation questions from issue #586 with concrete evidence: bare `Edit`/`Write` allow rules ARE honored, `defaultMode: bypassPermissions` IS in effect for `-p` runs, project settings ARE loaded via the working directory established by the parent's `cd "$REPO_ROOT"`, and user-level `~/.claude/settings.json` does not silently override project allows. The umbrella stall in #566 is therefore not caused by missing or insufficient on-disk permissions — the kernel-side fix tracked in #585 remains the decisive remedy. The new section also includes a forward-compatible manual reproducer recipe (writing logs to a private `$HOME` path), evidence-handling guidance (do NOT paste raw debug logs into PRs/issues), and known limitations (cd-fallback edge case, version drift, no automated CI guard). No change to `.claude/settings.json` — empirical audit confirmed the existing settings are sufficient. Closes #586.

## [7.13.12] - 2026-04-26

### Fixed

- `skills/research/SKILL.md:350` and three failure-recovery sites in `skills/research/references/adjudication-phase.md` (`RAN=false` branch, pre-launch coordinator failure, ballot-builder failure) said "proceed to Step 3" / "return to Step 3" / "Step 3 proceeds" from Step 2.5 (adjudication) skip/exit paths, but the Step Name Registry places Step 2.7 (citation validation) and Step 2.8 (critique loop) between Step 2.5 and Step 3 — literally proceeding to Step 3 silently skipped both phases on every adjudication-skipped run. All four sites now route to Step 2.7 (the next numbered step after Step 2.5). Closes #590.

## [7.13.11] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/SKILL.md` Step 4 (lines 174-179) and Step 3B.3 (line 131) no longer claim that `helpers.sh emit-output` prints a single human summary line on stderr in four shapes (one-shot success/dedup/failed, multi-piece success, multi-piece dry-run, multi-piece partial). The implementation at `.claude/skills/umbrella/scripts/helpers.sh:220-244` only validates and streams `output.kv` to stdout; no stderr summary is emitted. Step 4 prose now attributes the human summary breadcrumb to the orchestrator (the LLM running the skill), preserving the four shape templates verbatim as the orchestrator's print menu. Step 3B.3's inline umbrella-creation-failure print is retired and the failure is captured as session state for Step 4 to render the multi-piece partial shape — Step 4 becomes the **single emission point** for the human summary on every path. Step 3B.3 now also requires `UMBRELLA_NUMBER` and `UMBRELLA_URL` to be **omitted** from `output.kv` entirely on the failure path (not written with blank values), preserving the canonical Step 4 grammar's "only on multi-piece success" presence/absence contract. Step 4 line 155 narrows the validation claim from "no unset values" (which the awk validator never enforced) to "well-formed `KEY=VALUE` lines, no embedded newlines, no duplicate keys", with the orchestrator owning completeness. `helpers.md` adds a single sentence scoped to `emit-output` only (stderr is reserved for parse/validation/usage errors; human summary is orchestrator-emitted at SKILL.md Step 4) with an explicit carve-out preserving `wire-dag`'s documented stderr warning behavior. `helpers.sh`'s emit-output banner comment is aligned with the same wording. Closes #571.

## [7.13.10] - 2026-04-26

### Changed

- `AGENTS.md` "Conventions" section gains a parallel rule mandating that interactive / assistant-driven `gh issue create` calls flow through `/larch:issue` (mirroring the existing `gh pr create` rule). The rule prevents the heredoc-quoting failure mode documented in #588's "Symptom" section (markdown bodies with backticks and inline code blocks crash the bash parser when passed via `gh issue create --body "$(cat <<'EOF' ... EOF)"`); `/larch:issue` composes a body file and runs `gh ... --body-file`, sidestepping shell quoting. The new bullet carves out scripts under `scripts/` and `skills/*/scripts/` (e.g., `skills/improve-skill/scripts/iteration.sh`, `skills/loop-improve-skill/scripts/driver.sh`, hooks) which own their body composition and don't share the failure mode. Closes #588.

## [7.13.9] - 2026-04-26

### Fixed

- `.claude/skills/umbrella/scripts/parse-args.sh` no longer destroys quoted whitespace in flag values or breaks the documented one-`KEY=VALUE`-per-line stdout grammar. The unquoted-expansion tokenizer (`TOKENS=( $ARGS_STR )` plus an awk-based `TASK` re-join) is replaced by a two-phase pure-bash lexer: phase 1 walks the flag prefix character-by-character with a quote-preserving scanner (recognizing single quotes, double quotes with `\"`/`\\`/`\$` escapes, outside-quote backslash escapes, and space/tab/newline as unquoted separators); phase 2 takes `TASK` as the verbatim remainder of `$ARGS_STR` from a recorded byte offset, preserving embedded multi-space runs and trailing whitespace as a documented contract property. Repeated `--label` flags now emit indexed `LABELS_COUNT=<N>` + `LABEL_1=…` / `LABEL_<N>=…` instead of a newline-joined `LABELS=` value, restoring the single-line-per-key invariant that line-based consumers (`grep '^LABEL_'`) require. The lexer pins `LC_ALL=C` so substring/length operations are byte-deterministic regardless of caller locale, and the frozen `ERROR=` template list (11 templates) is published in `parse-args.md` so the new test harness's expectations stay in lockstep with the lexer's literal strings. A `TASK` post-Phase-2 newline guard (`ERROR=embedded newline in TASK at offset <N>`) plus backslash-newline rejection in both readers' `\\)` arms (3-0 YES code-review accept) closes the remaining single-line-KV violation paths. Consumer parsing in `.claude/skills/umbrella/SKILL.md` Step 0 + the `/issue` forwarding prose in Steps 3A / 3B.2 / 3B.3 reads the new indexed grammar and reconstructs repeated `--label` flags. New regression harness `test-umbrella-parse-args.sh` (sibling `.md`) covers 25 cases — quoted whitespace in `--title-prefix` and `--label`, repeated `--label`, `--` end-of-flags, exact `TASK` byte preservation, both-quote unclosed-quote symmetry, embedded-newline rejection, backslash-newline rejection (FINDING_2 from /review), `TASK`-with-newline rejection (FINDING_1 from /review), `LABEL` value containing `=`, quoted positional starting with `--`, newline as unquoted separator, and unbalanced quote inside `TASK` — wired into `make lint` via the new `test-umbrella-parse-args` Makefile target alongside `test-umbrella-helpers`, with a corresponding row in `docs/linting.md`'s Makefile-targets table. Closes #572.

## [7.13.8] - 2026-04-26

### Fixed

- `scripts/merge-pr.sh` no longer mis-routes empty or `UNKNOWN` `mergeStateStatus` to `MERGE_RESULT=main_advanced` with the misleading "Branch mergeStateStatus is " (empty trailing) error. After the existing `BEHIND` check at line 85-89 and before the CI re-verify block, an early branch now treats empty `MERGE_STATE` (typically caused by `gh pr view --json mergeStateStatus` API/network/`gh` failure) and the `UNKNOWN` enum value as the existing `MERGE_RESULT=error` outcome with a clear `ERROR="could not read mergeStateStatus from gh pr view (state=...)"` string. `/implement` Step 12b's `error` branch already bails to 12d, which is the correct behavior when the merge state is unreadable — preventing the prior useless rebase loop. `scripts/merge-pr.md`'s MERGE_RESULT enum table `error` row is updated to document the new coverage; the enum itself is unchanged so no cascading edits to `skills/implement/SKILL.md` Step 12b's parse table or the script header comment. Closes #581.

## [7.13.7] - 2026-04-26

### Fixed

- `skills/research/SKILL.md` line 587 (Step 4 Budget-abort prelude) now reads `set by any of the budget gates after Steps 1, 2.5, or 2.8` instead of the stale `Steps 1, 2, or 2.5`. The prelude both named a non-existent post-Step-2 gate (relocated to post-Step-2.8 by #517) and omitted the actual post-Step-2.8 gate that sets `BUDGET_ABORTED=true` and skips Step 3. Mirrors the sibling fix #574 (PR #591) which corrected the line-56 measurable-lanes inventory after the same #517 relocation. Closes #575.

## [7.13.6] - 2026-04-26

### Fixed

- `/research --scale=quick` now layers `scripts/validate-research-output.sh` on each K=3 homogeneous Claude Agent-tool lane output after the existing non-empty check, mirroring the `--substantive-validation` gate that standard/deep modes apply via `collect-agent-results.sh`. Validator-failed lanes (any non-zero exit, codes 1/2/3/4) collapse into the existing empty-lane bucket: the lane file is truncated (`: > "$LANE_FILE"`) so the existing `SYNTHESIS_PROMPT_QUICK_VOTE` "omit empty/unreadable lanes" instruction naturally excludes it from synthesis without prompt or `quick-vote-state.sh` schema changes. Sanitized per-lane breadcrumb (`tr '|\n' '/ '` + 80-char cap, mirroring `collect-agent-results.sh`'s `FAILURE_REASON` handling) preserves operator observability. SKILL.md Step 0b summary, Step 3 Quick `LANES_SUCCEEDED == 0` literal, research-phase.md §1.5 Quick all three branch prose updates, and the operator-visible hard-fail warning string aligned to the new "empty or failed substantive validation" phrasing. `scripts/test-research-structure.sh` gains Check 52 (subsection-scoped via two-stage `awk` windowing into `## 1.4` → `### Quick (RESEARCH_SCALE=quick)`) pinning the validator invocation, the truncation mechanism, and the breadcrumb shape; PASS-message count bumps 51 → 52, and `scripts/test-research-structure.md` is updated in sync. Closes #543.

## [7.13.5] - 2026-04-26

### Fixed

- `skills/create-skill/scripts/render-skill-md.sh` body interpolation no longer loses the operator's original feature spec on PR #549's synthesis path. The script gains a new optional `--feature-spec-file <path>` flag whose content is interpolated into the scaffolded SKILL.md body's opening paragraph (raw passthrough, multi-line preserved); when omitted, the body falls back to `${DESCRIPTION}` for backward compatibility. `skills/create-skill/SKILL.md` Step 3 forwards the resolved absolute path of `$RAW_DESC_FILE` to the new flag so the body-vs-frontmatter split is now mechanically guaranteed by the renderer rather than relying on the implementing agent to manually rewrite the scaffold body. Two new sibling contract files close AGENTS.md "Per-script contracts" gaps: `skills/create-skill/scripts/render-skill-md.md` (the renderer's contract) and `skills/create-skill/scripts/test-render-skill-md.md` (the test harness's contract). `SECURITY.md` describes the new body path's safety posture (single-pass parameter expansion; pre-synthesis F9 banned-token scan still applies). `test-render-skill-md.sh` adds three new cases covering multi-line `--feature-spec-file` distinct from `--description`, explicit backward-compat body assertion, and missing-file rejection. Closes #568.

## [7.13.4] - 2026-04-26

### Fixed

- `skills/loop-fix-issue/scripts/driver.sh` no longer conflates the three `/fix-issue` Step-0 sentinel-absent outcomes. The loop now dispatches on four distinct sub-sentinels — clean exhaustion, Step-0 error, Step-0 lock failure, and a defensive unknown-mismatch fallback — each with its own termination reason and `LOOP_PRESERVE_TMPDIR` retention. Sub-sentinels are anchored on the literal `0: find & lock —` step prefix so user-data-bearing `$ERROR` text in one branch cannot trigger another branch's keyword. Sibling contract `driver.md` `## Termination signal` updated in sync (AGENTS.md per-script-contract rule). Closes #582.

## [7.13.3] - 2026-04-26

### Changed

- `.claude/skills/umbrella/SKILL.md` Step 3B.1 fallback no longer breaks the strict `UMBRELLA_VERDICT=<one-shot|multi-piece>` token grammar declared at Step 2 (issue #570 — Cursor flagged in PR #549's `/review`). The downgrade path now emits three strict KV lines instead of a single line with a parenthetical: `UMBRELLA_VERDICT=one-shot` (preserving the line-62 token grammar), `UMBRELLA_DOWNGRADE=decomposition-lt-2` (shell-safe machine token capturing the downgrade trigger on a separate KV line), and `UMBRELLA_RATIONALE=…` (preserving the Step 2 verdict + rationale shape required by the "NEVER skip the user-visible classification verdict" anti-pattern). Step 4's canonical `output.kv` schema gains an optional `UMBRELLA_DOWNGRADE=<token>` entry so consumers reading only the final emitter output can still see the downgrade signal. Closes #570.

## [7.13.2] - 2026-04-26

### Fixed

- `skills/research/SKILL.md` line 56 budget-enforcement gate list updated from the stale `after Step 1, after Step 2, after Step 2.5` to the correct relocated set `after Step 1, after Step 2.5, after Step 2.8`. PR #565 / issue #517 had relocated the post-Step-2 gate to fire after Step 2.8; lines 34 (flag description), 344 (relocation note), 360 (post-Step-2.5 gate prose), and 411 (relocated post-Step-2.8 gate) already reflected the new gate set, but the prose summary on line 56 was missed in that sweep. Closes #574.

## [7.13.1] - 2026-04-26

### Changed

- `.claude/skills/umbrella/SKILL.md` now uses portable path tokens — `${CLAUDE_PLUGIN_ROOT}/…` for plugin-shipped references (`skills/shared/skill-design-principles.md`, `skills/shared/subskill-invocation.md`, `scripts/cleanup-tmpdir.sh`) and `$PWD/.claude/skills/umbrella/…` for the five dev-only umbrella scripts (`parse-args.sh`, `render-batch-input.sh`, `render-umbrella-body.sh`, `helpers.sh` ×2). Replaces 8 hardcoded `/Users/zhupanov/larch1/…` and `/Users/zhupanov/larch5/…` absolute paths that had been baked into the dev-only skill, restoring portability for any contributor whose checkout is not at one of those exact paths. AGENTS.md path-convention split (`${CLAUDE_PLUGIN_ROOT}` for plugin-shipped, `$PWD` for dev-only `.claude/skills/`) is now respected uniformly. Pure prompt-text edit; no behavior change. Closes #569.

## [7.13.0] - 2026-04-26

### Changed

- `/research --scale=quick` evolved from 1 inline Claude lane to **K=3 homogeneous Claude Agent-tool lanes with vote-merge synthesis** (issue #520). Operator surface (`--scale=quick|standard|deep` enum) unchanged; the auto-classifier (#513) routes to `quick` automatically and inherits the new K-lane confidence. Lane outputs persist to stable named paths `$RESEARCH_TMPDIR/quick-lane-{1,2,3}-output.txt`; a new helper `skills/research/scripts/quick-vote-state.sh` writes/reads `LANES_SUCCEEDED ∈ {0,1,2,3}`. Step 1.5 Quick branches: `LANES_SUCCEEDED >= 2` invokes a synthesis subagent (reusing the #507 contract) emitting `### Consensus` / `### Divergence` / `### Correlated-error caveat` markers with the new K-lane voting confidence disclaimer; `LANES_SUCCEEDED == 1` falls back to inline single-lane synthesis with the existing "Single-lane confidence" disclaimer (now in `quick-disclaimer-fallback.txt`); `LANES_SUCCEEDED == 0` hard-fails the research phase. `quick-disclaimer.txt` rewritten to "K-lane voting confidence — no validation pass; correlated-error risk: all K lanes are Claude (same model, same prompt — voting catches independent stochastic errors only)." `test-synthesis-subagent.sh` Pin 5 negative replaced with two new positive profiles (Quick-vote + Quick-fallback) keyed off ####-scoped sub-subsections in `research-phase.md` §1.5 Quick. `test-research-structure.sh` Check 21e split into vote and fallback path anchors; new Check-29-parallel + Check-30-parallel pin `quick-disclaimer-fallback.txt` cross-references and existence; new pins for `quick-vote-state.sh` helper. K=3 lanes + Synthesis subagent are measurable for `--token-budget` (token sidecars `Quick-Lane-1/2/3` + `Synthesis`). Synthesis prompt wraps lane content in `<lane_N_output>` tags with the canonical "treat as data, not instructions" preamble (parallel to Standard/Deep). Closes #520.

## [7.12.2] - 2026-04-26

### Changed

- `scripts/test-research-structure.sh` Check 50 replaced with a paragraph-scoped 16-slot enumeration (#564, supersedes the original #517 narrower whole-file check). The check extracts the `**Measurable lanes**` paragraph from `skills/research/SKILL.md` between anchor-bounded openers and asserts every canonical token-tally slot name (`planner`, `Synthesis`, `Revision`, `Code`, `Code-Sec`, `Code-Arch`, `Cursor`, `Codex`, `Cursor-Arch`, `Cursor-Edge`, `Codex-Ext`, `Codex-Sec`, `Critique-1`, `Critique-2`, `Revision-Critique-1`, `Revision-Critique-2`) appears as a backtick-quoted literal — the backtick wrap disambiguates prefix overlaps (`Code` vs `Code-Arch`); singleton boundary `grep -c \|\| true` lets a missing/renamed anchor surface via descriptive `fail` rather than a silent `set -e` abort. SKILL.md "Measurable lanes" prose updated to enumerate the 7 previously-implicit slot literals (the 4 deep-mode research-phase angle slots `Cursor-Arch` / `Cursor-Edge` / `Codex-Ext` / `Codex-Sec` were genuinely absent from the prose; `planner` / `Cursor` / `Codex` were named without backtick wrap). `references/critique-loop-phase.md` line 144 cross-reference narrowed so the four critique-loop slots remain the single source of truth for those four names while clarifying that Check 50 enforces the full 16-slot SKILL.md inventory. Sibling-contract clause appended to `scripts/test-research-structure.md` per AGENTS.md per-script-contract rule. Closes #564.

## [7.12.1] - 2026-04-26

### Changed

- `/issue` Phase 1 two-tier triage now reserves a per-item floor before applying the global 30-cap on the union CANDIDATES list, preventing early items in a batch from starving later items of Phase 2 deep-dedup coverage. Tier-1 emits structured `CAND <item> <issue> <kind:dup|dep|both> <confidence:high|medium|low>` rows; the new `skills/issue/scripts/allocate-candidates.sh` reads them via stdin heredoc and applies a deterministic two-pass selector — Pass A reserves up to `F = 0 if N>30 else min(3, floor(30/N))` slots per non-malformed item with union-credit semantics (a candidate already in the union covers every item that nominated it), Pass B fills remaining slots up to 30 by confidence-desc → issue-asc → item-asc. Output is exactly one `CANDIDATES=<comma-list>` line on stdout; all diagnostics on stderr. Bash 3.2-safe (no `declare -A`). Sibling `allocate-candidates.md` is the normative algorithm spec. New `skills/issue/scripts/test-allocate-candidates.sh` regression harness covers 23 cases / 53 assertions (floor boundary at N=10/11/15/16/30/31, partial-floor + Pass-B interaction, tie-breaks, kind=both first-class, defensive-default row drops, N>30 stderr warning, empty-stdin/N=0, stdout-shape invariant, Bash 3.2 portability guard). Wired into `make lint` via `test-allocate-candidates`; documented in `docs/linting.md`. Closes #554.

## [7.12.0] - 2026-04-26

### Added

- `--no-admin-fallback` opt-out flag for `/implement`, `/fix-issue`, and `/loop-fix-issue` (which forwards through to per-iteration `/fix-issue` invocations). When set, `scripts/merge-pr.sh` returns a new `MERGE_RESULT=policy_denied` instead of retrying with `gh pr merge --admin` once the admin-eligible gate (CI good + branch fresh) is reached, and `/implement` bails to Step 12d with `FINAL_BAIL_REASON="branch protection denied merge; --no-admin-fallback set"`. Default behavior is unchanged for backward compatibility — the silent `--admin` retry still fires by default. When `--admin` does fire (default path), `/implement` Step 12b posts a best-effort PR comment recording the bypass for audit visibility (the existing stderr warning is retained). New sibling contract `scripts/merge-pr.md` per AGENTS.md per-script-contracts rule. New harness assertions a3/a4 in `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` pin `--no-admin-fallback` forwarding in both SIMPLE and HARD `/implement` invocation bullets. `/im` and `/imaq` are unchanged — they auto-forward `$ARGUMENTS` verbatim. Closes #559.

## [7.11.4] - 2026-04-26

### Changed

- `/research` Step 2.8 critique loop now emits a per-iteration citation-revalidation breadcrumb of the form `✅ 2.8 [iter <iter>]: citation-revalidation — <pass> PASS, <fail> FAIL, <unknown> UNKNOWN (<total> claims) (<elapsed>)` after each in-loop re-run of `validate-citations.sh`. Mirrors Step 2.7's completion-breadcrumb shape but namespaces under `2.8 [iter <iter>]` so each in-loop revalidation result is operator-visible without colliding with the original Step 2.7 output. Updates `skills/research/references/critique-loop-phase.md` Section 2.8.6 (replaces the prior "the re-run is silent" deferral) and `skills/research/SKILL.md` Step 2.8 inventory + ownership prose to point at the canonical breadcrumb template in the reference. Closes #563.

## [7.11.3] - 2026-04-26

### Changed

- `/create-skill` now separates the validated frontmatter `description:` line from the freeform feature spec forwarded to `/im` as a brief. New Step 1.4 captures the raw user input to a tmpfile (preserving multi-line content past `parse-args.sh`'s space-joining), Step 1.5 invokes a new `skills/create-skill/scripts/prepare-description.sh` coordinator that probes `validate-args.sh` and classifies the result as `MODE=verbatim` / `MODE=needs-synthesis` / `MODE=abort`, and Step 1.6 re-validates an LLM-distilled `Use when…` one-liner when synthesis fires. Synthesis is narrow-gated: it triggers only on the validator's `Description contains newlines or control characters` and `Description length (...)` errors, with a pre-synthesis security scan that aborts on mixed inputs (synthesis-trigger class plus any banned token like XML/backtick/`$(`/heredoc, including newline-delimited boundaries). Updates `parse-args.md`, `SECURITY.md` (#549 two-concept-split bullet), `Makefile` + `agent-lint.toml` (new `scripts/test-prepare-description.sh` harness — 18 cases). Closes #549.

## [7.11.2] - 2026-04-25

### Changed

- `scripts/test-implement-structure.sh` header refreshed to reflect the 13 structural invariants the body actually implements: line 3 count word "10"→"13", line 19 count word "Ten"→"Thirteen", and the enumeration extended past `(10)` with summaries of `(11)` Phase 5 rebase-rebump-subprocedure.md reference set with sub-assertions `(11a)–(11d)`, `(12)` Phase 5 single-source-of-truth invariant for `SECTION_MARKERS` with sub-assertions `(12a)–(12b)`, and `(13)` orchestrator-judgment-bail invariant. Pure documentation drift fix — no behavioral change; the PASS line at the end of the script already correctly said "all 13 structural invariants hold". Closes #556.

## [7.10.4] - 2026-04-25

### Changed

- Wire `.claude/skills/umbrella/scripts/test-helpers.sh` (cycle-detection regression harness, 13 assertions covering empty graph / self-loop / 2- and 3-cycle close / parallel forward edge / diamond cycle and cross-edge / disconnected components / four error-path cases) into `make lint` via a new `test-umbrella-helpers` Makefile target added to `.PHONY` and to the `test-harnesses` prerequisite list, mirroring the `test-parse-input` style. CI's existing `test-harnesses` job now exercises the harness; future regressions in `helpers.sh check-cycle` semantics or stdout grammar (`CYCLE=true|false`) will fail CI. Sibling `test-helpers.md` flipped from a "Wire into `make lint`" pending TODO to a statement that the wiring is in place. Closes #558.

## [7.10.3] - 2026-04-25

### Changed

- `skills/implement/SKILL.md` adds a 7th NEVER rule and a positive cue near Step 2 forbidding orchestrator-judgment bail mid-run on subjective scope or capacity concerns. Only three non-error halt paths between Step 1 and Step 17 are sanctioned: (a) Step 12d under one of its three documented judgment conditions; (b) explicit user halt via a fresh interactive turn; (c) hard tool failure. The rule explicitly carves out the mechanical 12d routes (Rebase + Re-bump sub-procedure hard-bail, conflict-resolution abort, merge-pr.sh errors) so scripted control flow into 12d is not affected. New structural assertion (13) in `scripts/test-implement-structure.sh` byte-pins the two anchor headlines (NEVER #7 + Step 2 cue) so future edits cannot silently delete the invariant; sibling contract `scripts/test-implement-structure.md` updated from twelve to thirteen assertions. Closes #553.

## [7.10.2] - 2026-04-25

### Added

- `/issue` now performs **always-on inter-issue blocker dependency analysis** (no opt-out flag) on every invocation. Phase 1 reshaped into a two-tier triage (cap 500 most-recent open titles for dep-candidacy; closed rows still participate in dup-candidacy only); Phase 2 emits typed `BLOCKED_BY` / `BLOCKS` edges alongside the existing `VERDICT=CREATE|DUPLICATE`. New Step 5b validation: snapshot membership (open-only for deps), intra-batch range, DUPLICATE override + chain-collapse, SCC-based cycle resolution (Tarjan-style with deterministic edge-removal), `DUPLICATE_OF_ITEM` as topological prerequisite. Step 6 reorders creates topologically (Kahn's, ascending input-index tie-break) while keeping `ISSUE_<original_i>_*` keyed by input index in stdout — consumers parse by key match, not stream position. Per-edge dependency wiring goes through new `skills/issue/scripts/add-blocked-by.sh` (3-attempt retry, 10s/30s pre-retry sleeps, idempotent on 422-with-pinned-message-fragment, fail-fast on 404 feature-unavailable, redacted stderr); orphan-recovery on retry-exhaustion via new `skills/issue/scripts/cleanup-failed-issue.sh` followed by transitive-failure propagation through the dep graph. `--go` post is deferred until all blocker edges for the issue succeed (brief no-GO window — typically <1s, up to ~40s on retry — explicitly cross-referenced in `skills/fix-issue/SKILL.md`). `create-one.sh` extended to capture `ISSUE_ID=<numeric-id>` via single-response `gh issue create --json id,number,url` (eliminates the orphan-failure mode of a separate id-lookup), with fallback to `gh issue create` + `gh api .../issues/N --jq .id` for older gh CLI versions; the fallback path includes inline `rollback_orphan` (best-effort `gh issue close --reason "not planned"`) so a transient id-lookup failure does not leave an unclosed orphan. New stdout fields are additive: `ISSUE_<i>_ID`, `ISSUE_<i>_BLOCKED_BY`, `ISSUE_<i>_BLOCKS`, `ISSUE_<i>_BLOCKER_LINKS_APPLIED`, `ISSUE_<i>_BLOCKER_LINKS_FAILED`, `ISSUE_<i>_DRY_RUN_DEPS` (dry-run only). `--dry-run` computes and emits the dep-edge plan but applies no API writes. Test harness `skills/issue/scripts/test-add-blocked-by.sh` (26 assertions covering 200 success, 4 idempotent-422 message-fragment variants, 5xx-retry success, exhaustion, 404 feature-unavailable no-retry, implicit blocker-id lookup, secret-leak redaction), wired into `make lint` via the `test-add-blocked-by` Makefile target. `.gitleaks.toml` allowlist extended for the new test fixture's token-shaped strings, mirroring the existing `test-redact-secrets.sh` allowlist. Closes #546.

## [7.10.1] - 2026-04-25

### Fixed

- `scripts/token-tally.sh` `validate_dir` now canonicalizes the nearest existing-or-symlink ancestor of `--dir` before any subcommand body runs, replacing the prior `[[ -d "$d" ]]`-gated canonicalization that allowed `cmd_write`'s `mkdir -p` to materialize directories outside `/tmp/` via a symlinked parent. The walk uses `! -e && ! -L` so dangling symlinks are caught at validation rather than letting `cd` (or downstream `mkdir -p`) fail with an opaque error; a regular-file ancestor is rejected explicitly rather than silently normalized via `dirname`. Both `/tmp` and `/private/tmp` are canonicalized when distinct so the dual-root contract is preserved on hosts where `/tmp` is not a symlink to `/private/tmp`. Pattern mirrors `scripts/deny-edit-write.sh`'s nearest-existing-ancestor probe with a `/tmp`-allow predicate. New `scripts/test-token-tally.sh` T17 adds 5 assertions across three sub-cases (live-symlink escape — the verified reproducer; dangling-symlink; regular-file ancestor) and uses `/var/tmp` as the primary escape-target location with a `$HOME` fallback so the harness stays portable in restricted CI sandboxes. Operator-visible: `--dir` whose ancestor escapes `/tmp/` now exits 1 in `report` and `check-budget` instead of emitting the "missing dir" placeholder; the tolerant missing-dir paths still apply when the ancestor is safely under `/tmp/`. Closes #538.

## [7.10.0] - 2026-04-25

### Added

- New unconditional **Step 2.7 — Citation Validation** phase for `/research`. Between Step 2.5 (adjudication) and Step 3 (final report), a deterministic shell validator (`skills/research/scripts/validate-citations.sh`) extracts cited URLs / DOIs / file:line references from the synthesis, HEAD-fetches URLs under SSRF guards (HTTPS-only, `--max-redirs 0`, `--noproxy '*'`, RFC1918 / IPv6 link-local / RFC6598 hostname pre-rejection with bracketed-IPv6 stripping, DNS resolved-IP private-range check via `host -t A` + `host -t AAAA` resolution and `is_private_ip` v4+v6 classifier, multi-answer DNS rebinding defense, connection-pinning via `--resolve` to mitigate TOCTOU rebinding), validates DOIs syntactically + via `doi.org` HEAD, and spot-checks file:line ranges against the git tree (with `realpath` canonical-path containment). Output is a 3-state ledger (PASS / FAIL / UNKNOWN with reason classifier) sidecar at `$RESEARCH_TMPDIR/citation-validation.md` that Step 3 splices as a `## Citation Validation` section into `research-report-final.md`. **Fail-soft**: per-claim failures surface as advisory warnings only; the validator always exits 0; Step 3 is never blocked. Domain-credibility heuristic is advisory only — never flips PASS to FAIL. Validator costs zero measurable Claude tokens (shell only). Operator allow-list (`--trusted-domains=`) deferred to #514; critique-loop integration deferred to #517. New `scripts/file-line-regex-lib.sh` shared source-only library (namespaced `__filelinelib_*`) powers both `validate-research-output.sh`'s provenance probe and `validate-citations.sh`'s file:line claim extractor (refactored, byte-identical behavior). Test harness (`skills/research/scripts/test-validate-citations.sh`, 33 assertions) covers SSRF rejections (file://, RFC1918 literal, multi-answer DNS rebinding), HTTPS-only enforcement, idempotency rerun, HEAD 403/404/501 mapping, file:line PASS/FAIL/UNKNOWN paths, curl argv MUST/MUST-NOT split, hostile `http_proxy` env bypass, malformed numeric flag rejection, and combined `--max-claims` cap. SKILL.md adopts the 4-reference symmetric topology (each MANDATORY line names all 3 other references in `Do NOT load` clauses). `scripts/test-research-structure.sh` is extended (45 invariants, presence-not-order topology check). Closes #516. Unblocks #514, #517.

## [7.9.3] - 2026-04-25

### Changed

- Adaptive scaling becomes the default behavior for `/research`: when `--scale=` is omitted, a new deterministic shell classifier (`skills/research/scripts/classify-research-scale.sh`) inspects `RESEARCH_QUESTION` at Step 0.5 and resolves `RESEARCH_SCALE` to one of `quick|standard|deep` automatically. `--scale=quick|standard|deep` is preserved as a manual override (skips classifier; CI/eval determinism path); explicit `--scale=` (empty value) still aborts as operator error. On classifier failure, falls back to `RESEARCH_SCALE=standard` with a visible warning. The classifier uses **asymmetric conservatism** (per dialectic resolution on issue #513 DECISION_1, voted 2-1 ANTI_THESIS): `quick` requires conjunction of length<80 + single `?` + lookup keyword + zero deep keywords; `deep` fires on any single strong trigger (length>600, ≥2 deep keywords, or ≥2 `?`); ambiguity → `standard`. Pure shell heuristic — zero measurable LLM tokens, fully reproducible across CI and laptops. New `make test-classify-research-scale` harness with 26 cases wired into `make lint`. The `--plan + --scale=quick` warning text branches on `SCALE_SOURCE` (`override` vs `auto/fallback`) so operators never see a warning citing a flag they did not type. `scripts/eval-research.sh` now forwards `--scale=$SCALE` so adaptive auto-classification doesn't silently route runs labeled in baseline metadata to a different bucket. Bucket schema and per-bucket lane shapes (1 / 3+3 / 5+5) are unchanged. Closes #513 (umbrella #512).

## [7.9.2] - 2026-04-25

### Changed

- `scripts/test-research-structure.sh` Check 13 replaces a brittle 5-flag literal substring pin with a structural completeness check that derives the expected "independent" flag set from `skills/research/SKILL.md`'s flag-bullet block (canonicalizing value forms like `--scale=quick|standard|deep` to `--scale` and compound bullets like `--keep-sidecar` AND `--keep-sidecar=<PATH>` to `--keep-sidecar`) and asserts set-equality with the backticked `--<name>` tokens on the line beginning `Flags are independent`. Bullets whose body contains the literal case-sensitive substring `cross-effect` are classified as coupled and exempted (today only `--plan`, whose bullet documents a `--scale` cross-effect). Two distinct failure modes name the specific flag(s): `MISSING` (independent flag absent from the line) and `STALE` (flag listed on the line but not present as an independent bullet). All `sort`/`comm` invocations use `LC_ALL=C` for deterministic cross-platform behavior. The previous pin would silently pass on any new flag added to the bullet block but not the independence statement (a pattern that affected #418, #424, #510, #518). `scripts/test-research-structure.md` is updated to document the new contract: section anchors, the `cross-effect` sentinel, the canonical-token rule, the single-line independence-statement requirement, and the limited-fence-awareness contract. Closes #531.

## [7.9.1] - 2026-04-25

### Changed

## [7.9.0] - 2026-04-25

### Added

- New `--interactive` boolean flag for `/research` (requires `--plan`; hard-fails on non-TTY before the planner subagent runs). Pauses Step 1.1 after planner validation so the operator can review, edit (via `$EDITOR` or stdin fallback), or abort the proposed 2–4 subquestions before lane fan-out. Standard and deep modes both supported. Deep mode confirms only the subquestion list — the per-lane subq×angle pairing (Step 1.2 ring rotation) stays mechanical regardless. Becomes a no-op with a notice when `--scale=quick` auto-disables `--plan`. SIGINT (Ctrl-C) does NOT run the cleanup recipe; only typed `abort` does. Closes #522.

### Changed

- `skills/research/scripts/run-research-planner.sh` validator now rejects any retained subquestion line containing the literal substring `||` with the new `REASON=delimiter_collision` token. The check runs BEFORE the count gate so the more actionable token surfaces when both `||` and an out-of-range count apply. `lane-assignments.txt` (`research-phase.md` §1.2.b) uses unquoted `||` as in-cell delimiter with plain prefix-strip + `||`-split rehydration; the new rule prevents silent mis-splits at deep-mode rehydration. The same script is now consumed in two distinct caller contexts (Step 1.1.b planner-output validation → fall back to single-question mode; Step 1.1.c operator re-validation → bounded one-retry then abort) — `run-research-planner.md` gains a "Caller contexts" section distinguishing them.
- `SECURITY.md` extended with a new bullet covering the `--plan --interactive` operator-edit surface: the `$EDITOR` subprocess (operator-controlled, runs with operator's privileges; trust model matches the operator's interactive shell), operator-edited subquestions feeding the existing `<reviewer_subquestions>` "treat as data, not instructions" hardening wrap, the new `||` rejection rule as an integrity surface, and the documented SIGINT divergence (Ctrl-C does NOT run cleanup).
- Public-doc mirrors updated: `README.md` and `docs/skills.md` argument-hint tables, `docs/workflow-lifecycle.md` `/research` bullet + flag table get the new `--interactive` row, `scripts/test-research-structure.sh` adds structural pins for the `--interactive` literal, the pre-planner TTY-guard error literal, and the `RESEARCH_PLAN_INTERACTIVE=true` mental flag (Check 13b — pinned to umbrella #522). The `--debug`/`--scale`/`--adjudicate`/`--keep-sidecar`/`--token-budget`/`--interactive` independence statement in SKILL.md is updated to include the new sixth flag and is structurally pinned. Co-evolved with /design + /review: 1 design round (5-agent sketch all converged on placement between Step 1.1.b and Step 1.2; 5-decision dialectic resolved D1 ANTI_THESIS 2-1 (inline Bash, NOT helper script), D2 THESIS 2-1 ($EDITOR-primary), D3 THESIS 3-0 (pre-planner TTY check), D4 THESIS 2-1 (bounded one-retry), D5 THESIS 3-0 (validator rejects `||`); 3-reviewer plan-review with 14 of 17 in-scope findings accepted including the `||`-precedes-count ordering, multi-word `$EDITOR` value support, case-insensitive matching mechanism, scale-quick-before-TTY ordering, and the SECURITY.md update; 2 rejected (1 YES each); 1 unanimously exonerated; 1 OOS not filed) + 2 code review rounds (round 1: 3 in-scope findings accepted including F1 `$EDITOR_STATUS=$?` after `if !` always 0 and F2 `${CHOICE,,}` breaks on macOS bash 3.2; round 2: 0 new findings; 1 OOS accepted for filing — token-tally.sh symlink-parent escape from sibling PR #532).

## [7.8.4] - 2026-04-25

### Changed

- `skills/implement/SKILL.md` adds a `**Skill-name fallback reminder.**` banner parallel to the existing Anti-halt banner, restating the canonical bare-name-first / fully-qualified-fallback rule (`relevant-checks` before `larch:relevant-checks`) at the call site. Fixes the `Unknown skill: larch:relevant-checks` error observed when `/implement` (running as `larch:implement`) mirrored its own namespaced invocation onto child Skill calls — `/relevant-checks` and `/bump-version` are intentionally project-local under `.claude/skills/` and do NOT exist under the `larch:` prefix, so a `larch:`-first attempt fails outright before the LLM retries with the bare name. Banner cross-references the canonical rule at `skills/shared/subskill-invocation.md` § "Bare-name-then-fully-qualified fallback".

## [7.8.3] - 2026-04-25

### Changed

- `scripts/test-research-structure.sh` now structurally pins the `## Finalize Validation` section of `skills/research/references/validation-phase.md` (Checks 38a-38c, anchored on a section-scoped awk window). 38a pins the post-#507 revision-subagent shape (`Route the synthesis-revision step to a separate Claude Agent subagent` + `revision-raw.txt` Write capture). 38b pins the atomic rewrite of `research-report.txt` (`Atomically rewrite` + `mktemp` + `mv`). 38c pins FINDING_1's marker contract — the 5 body markers (`### Agreements` / `### Divergences` / `### Significance` / `### Architectural patterns` / `### Risks and feasibility`) enumerated by REVISION_PROMPT. Sibling contract `scripts/test-research-structure.md` is updated in the same commit (gate count 41 → 44, new sub-bullet, must-stay-in-sync sentence). Closes #534.

## [7.8.2] - 2026-04-25

### Changed

- `/research` Step 1.5 synthesis is now routed to a separate Claude Agent subagent in the four non-quick branches (Standard `RESEARCH_PLAN=false`, Standard `RESEARCH_PLAN=true`, Deep `RESEARCH_PLAN=false`, Deep `RESEARCH_PLAN=true`), eliminating the self-judge bias where the orchestrator authored the lane-3 SEC inline research at Step 1.3 and then synthesized all 3-5 lane outputs at Step 1.5. The Quick branch (`RESEARCH_SCALE=quick`) is byte-untouched — single-lane synthesis remains inline. Closes #507 (umbrella #505). Validation-phase Finalize Validation revision is also routed to a second Claude Agent subagent (same separation-of-concerns argument) — the revision subagent receives the existing synthesis body + accepted findings under `<accepted_findings>` tags + revision brief instructing "incorporate accepted corrections only; do not introduce new findings or undo merged outcomes". The orchestrator owns the reduced-diversity banner (#506) via a new canonical executable helper `skills/research/scripts/compute-degraded-banner.sh` (sibling contract `compute-degraded-banner.md`) — computed BEFORE the subagent invocation and post-processed (prepended) to the synthesis body before writing `research-report.txt` atomically (mktemp + mv); the synthesis subagent prompt explicitly forbids emitting the banner literal or the `## Research Synthesis` header (orchestrator-owned envelope). Synthesis output is gated by a 4-profile structural marker validator: Standard `RESEARCH_PLAN=false` requires the 5 body markers (`### Agreements` / `### Divergences` / `### Significance` / `### Architectural patterns` / `### Risks and feasibility`); Standard `RESEARCH_PLAN=true` requires anchored regex `^### Subquestion [0-9]+:` count == `RESEARCH_PLAN_N` + `### Cross-cutting findings`; Deep `RESEARCH_PLAN=false` requires the 5 markers + 4 angle names ("architecture & data flow" / "edge cases & failure modes" / "external comparisons" / "security & threat surface"); Deep `RESEARCH_PLAN=true` requires the anchored Subquestion regex + `### Per-angle highlights` + `### Cross-cutting findings` + 4 angle names. On validator failure or subagent timeout/empty, the orchestrator falls back to inline synthesis with operator-visible warning (mirrors planner-fallback at `research-phase.md:60-62`); the same per-profile validator applies to the inline-fallback path with degraded-path-warning semantics. The fork command for the helper uses the guarded form `BANNER=$(bash compute-degraded-banner.sh ... 2>/dev/null) || BANNER=""` so a missing/unreadable helper degrades to empty `$BANNER` rather than aborting under `set -euo pipefail`. The helper's own arity guard exits 0 (with stderr WARNING) per the documented "Always exits 0" contract — mistakenly omitting an argument under `set -e` produces an empty banner rather than aborting the run. Pre-synthesis lane-output persistence: the orchestrator MUST write the inline Claude lane output (Step 1.3 conversation prose) to `$RESEARCH_TMPDIR/claude-inline-output.txt` and each Claude pre-launch / runtime-timeout fallback Agent return value to its corresponding canonical slot file path BEFORE invoking the synthesis subagent — without this, the subagent's Read tool would hit ENOENT on every standard/deep run. Banner-emission edit-in-sync surfaces grow from 4 to 5 (helper script becomes the canonical executable; `research-phase.md` preamble becomes documentation only). The `test-degraded-path-banner.sh` harness is refactored from a duplicated reference implementation to a fixture-driven harness that forks the helper and compares stdout against hardcoded fixture pairs — eliminates duplicated formula logic while preserving an independent oracle. New harness `skills/research/scripts/test-synthesis-subagent.sh` (sibling `.md` per AGENTS.md) structurally pins the 4 non-quick branches contain Agent-tool subagent invocation + helper fork + structural-validator gate + inline-fallback prose; pins the Quick branch unchanged; pins the 5 body markers + per-subquestion regex + Per-angle highlights + Cross-cutting findings literals + 4 angle names; pins validation-phase.md Finalize Validation routing of revision to a subagent + revision-raw.txt capture + atomic-rewrite + structural validator + inline-revision fallback. Existing `scripts/test-research-structure.sh` Check 21a is updated to grep `compute-degraded-banner.sh` for the formula literals (canonical executable pin) AND `research-phase.md` for the banner template literal (documentation pin); new Check 21a-helper-fork pins the helper reference in the §1.5 preamble. Token telemetry: the synthesis (slot `Synthesis`) and revision (slot `Revision`) subagents are added to the "Measurable lanes" enumeration in `SKILL.md`; per-lane sidecars are written via `token-tally.sh write` after each Agent return — counted toward `--token-budget` per the existing telemetry contract. SECURITY.md residual-risk paragraph is extended to name the synthesizer + revision subagents (same boundary class as the planner subagent — separate Agent subprocess, no inherited `deny-edit-write.sh` PreToolUse hook, prompt-level `<lane_N_output_path>` / `<accepted_findings>` / `<existing_synthesis_body_path>` wrappers as model-level convention not parser-level). Operator-locked decisions (umbrella #505): apply unconditionally (no flag-gated path), drop inline-synthesis backcompat, update affected byte-stability tests, banner option (b) chosen (orchestrator post-processes), validation-phase revision routed to a subagent. Co-evolved with /design + /review: 1 design round (5-agent sketch all converged on the planner-subagent shape; 3-decision dialectic resolved D1 ALTERNATIVE 2-1 (extract helper script), D2 ALTERNATIVE 2-1 (full structural validator with 4 profiles), D3 CHOSEN 3-0 (keep prompts inline) — 3-reviewer plan-review with 11 of 14 in-scope findings accepted plus 1 OOS accepted for filing) + 1 code review round (5 of 7 in-scope findings accepted: guard `BANNER=$(bash …)` under `set -e` with `|| BANNER=""`; honor "Always exits 0" contract on arity-error path; pre-synthesis persistence of inline + fallback lane outputs to canonical slot file paths; clean `<existing_synthesis_body_path>` tag wrapping path only with prose moved outside the tag; add synthesis + revision subagents to "Measurable lanes" with stable slot names + matching token-tally write hooks in research-phase.md and validation-phase.md — 2 exonerated: SKILL.md banner-post-processing wording nit, test-synthesis-subagent.sh early-return masking nit). Filed OOS_1 as future GitHub issue: structural pin for validation-phase.md Finalize Validation absent from `test-research-structure.sh` Checks 21-block (covers research-phase.md only).

## [7.8.1] - 2026-04-25

### Changed

- `/research` external-evidence prompts now instruct lanes to issue 3+ independent web-search/fetch calls in parallel rather than sequentially when the runtime supports it and queries are independent, with explicit "degrade to serial when one query's result must inform the next" guard. Closes #521 (per Anthropic's multi-agent research guidance: "subagents that fan tool calls 3+ in parallel cut research time materially"). Edit confined to two prompt literals in `skills/research/references/research-phase.md`: (1) `RESEARCH_PROMPT_BASELINE` (the `external_evidence_mode=true` variant — applies to quick mode and deep mode's Claude inline integrator when external_evidence is triggered), and (2) `RESEARCH_PROMPT_EXT` (deep mode's Codex-Ext slot always; standard mode's Codex lane when external_evidence_mode=true). The instruction is best-effort prompt-level guidance, not a runtime contract — Codex/Claude runtimes that support parallel tool calls within a single turn benefit; runtimes that serialize degrade gracefully. Per dialectic resolutions: ARCH/EDGE/SEC angle prompts intentionally NOT modified (DECISION_1 voted 2-1 for proportionality — synthesis decision stands), and the concrete "3+" anchor lives only in the two web-fanout prompts (DECISION_2 voted 3-0 — matches Anthropic's exact citation, ARCH/EDGE/SEC kept qualitative if they had been edited). Co-evolved with /design + /review: 1 design round (5-agent sketch all converged on EXT being primary edit target with concrete 3+ wording; 2-decision dialectic resolved 2-1 ANTI_THESIS / 3-0 THESIS; 3-reviewer plan-review with 5 of 7 in-scope findings accepted including soften-to-best-effort framing, drop the Anthropic vendor parenthetical from prompt body, fix "byte-exactly" wording, fix degrade-to-serial failure-mode misattribution, remove bogus test script reference; 2 rejected — restrict-to-EXT-only and document-deep-mode-EDGE-residual; 1 OOS not filed — body-level prompt pin in test harnesses) + 1 code review round (corrected diff after fast-forwarding stale local main; Cursor and Codex both reported NO_ISSUES_FOUND on the single-commit diff; 1 Claude finding rejected 3-0 as misreading "this branch" in pre-existing prose).

## [7.8.0] - 2026-04-25

### Added

- `/research` now reports per-run token spend at Step 4 cleanup and accepts an optional `--token-budget=N` flag that aborts the run when measurable Claude subagent token use exceeds the cap. Closes #518 (umbrella #512). New helper `scripts/token-tally.{sh,md}` with three subcommands (`write` per-lane sidecar; `report` to render the `## Token Spend` section; `check-budget` to sum measured tokens with exit 2 on overage). Per-lane sidecars at `$RESEARCH_TMPDIR/lane-tokens-<phase>-<safe-lane>.txt` use a KEY=value schema (PHASE / LANE / TOOL=claude / TOTAL_TOKENS=integer-or-unknown) parallel to `lane-status.txt` / `.meta`. Measurable lanes (sidecar-writing): the planner subagent (Step 1.1.a when `--plan`); Cursor/Codex pre-launch and runtime-timeout fallback subagents in research/validation phases; the always-on Claude `Code` subagent in validation; deep-mode `Code-Sec` and `Code-Arch` validation subagents; the always-on Claude judge subagent and any judge replacements in adjudication. Unmeasurable lanes (no sidecar): Claude inline (orchestrator self-introspection unavailable) and external Cursor/Codex non-fallback lanes (runners do not expose `total_tokens`); the report labels itself "Claude tokens only; external lanes excluded" so coverage is honest. Step 4 reorders `## Token Spend` rendering to run BEFORE `cleanup-tmpdir.sh` (previously sidecars under `$RESEARCH_TMPDIR` would have been deleted before reading). Budget enforcement runs between phases only (after Steps 1, 2, 2.5); on overage the run aborts before the next phase, sets `BUDGET_ABORTED=true`, skips Step 3 entirely, renders the partial token report, and the completion line carries the `(aborted: budget exceeded)` suffix. `TOTAL_TOKENS=unknown` sidecars contribute zero to the budget sum (parser-broken `<usage>` blocks do not silently fail open — the unknown count is surfaced via the start-of-run notice, the `UNKNOWN_LANES=<count>` field on `check-budget` stdout, and the `(N lanes, M measured, K unmeasurable)` coverage parenthetical in each phase row). Optional `$` cost column gated on `LARCH_TOKEN_RATE_PER_M` env var (USD per million tokens, single combined rate v1 since Anthropic Agent-tool API exposes only `total_tokens`). Co-evolved with /design + /review: 1 design round (5-agent sketch + 5-decision dialectic where 2 voted 3-0 in favor of synthesis (option (b) external-tool exclusion + Claude-only governor) and 3 fell back to synthesis on debater-quorum failure (sidecar schema, helper location, cost column) + 3-reviewer plan-review with 11 in-scope findings + 1 OOS unanimously accepted via reviewer convergence — formal voting panel skipped pragmatically, deviation noted) + 1 code review round (10 in-scope findings accepted: zero-rate-not-handled, validate_dir path-escape via `..`, missing `BUDGET=` on missing-dir success line, header subtitle drift, "cents" vs "dollars" comment, contract drift in start-of-run-notice claim, fragile `IFS='='` parser, /tmp/private-tmp doc drift, Research-row dropped on healthy standard runs, Adjudication mis-rendered "no rejections" on budget abort) plus 1 round-2 nit (T15 missing check-budget coverage). New offline harness `scripts/test-token-tally.{sh,md}` with 34 assertions across 17 test cases. Wired into `Makefile` (.PHONY + test-harnesses + test-token-tally recipe). Updates `scripts/test-research-structure.sh` Check 13 to extend the flag-independence pinning to include `--token-budget`. Cross-doc sweep: `skills/research/SKILL.md` (frontmatter argument-hint + flag block + independence statement + Step 0 start-of-run notice + three between-phase budget gates + Step 4 reorder + completion-line suffix); `skills/research/references/research-phase.md`, `validation-phase.md`, `adjudication-phase.md` (per-lane sidecar write hooks); `docs/skills.md`, `docs/workflow-lifecycle.md`, `docs/configuration-and-permissions.md` (flag list + `LARCH_TOKEN_RATE_PER_M` env-var entry); `agent-lint.toml` exclude. Unblocks #513 (adaptive scaling, hard-blocked on per-bucket token-cost data).

## [7.7.1] - 2026-04-25

### Fixed

- `scripts/collect-agent-results.sh:405` validator-call-site bash 3.2 portability hazard — under `set -uo pipefail` (line 57), the bare `"${VAL_ARGS[@]}"` expansion raised `VAL_ARGS[@]: unbound variable` on bash 3.2 (macOS default `/bin/bash`) when `VAL_ARGS=()` was empty, which fires whenever a caller passes `--substantive-validation` without `--validation-mode` (the documented `/research` Step 1.4 invocation at `skills/research/references/research-phase.md:273-275`). The validator never ran, every reviewer file was misclassified as `STATUS=NOT_SUBSTANTIVE`, and callers fell through to spurious Claude subagent re-runs (silently doubling the cost of `/research --scale=standard` and `/research --scale=deep` runs on macOS dev environments). Closes #511. Replaced the bare expansion with the bash-3.2-safe `"${VAL_ARGS[@]+"${VAL_ARGS[@]}"}"` idiom (precedented at `scripts/create-pr.sh:105`) plus a one-line WHY-comment that pins the rationale at the call site so a future reader cannot "simplify" it back. Added new regression harness `scripts/test-collect-reviewer-bash32.sh` with three cases: (1) static idiom grep — Linux-CI backstop on every PR; bash 4.4+ does not exhibit the hazard at runtime; (2) dynamic empty-`VAL_ARGS` exercise of the actual collector under any `/bin/bash` whose version is `< 4.4` (bash 3.x or bash 4.0-4.3 — both still vulnerable; the gate broadened from bash-3-only after code-review FINDING_1 caught the 4.0-4.3 coverage gap); (3) dynamic `--validation-mode` forwarding pin using a literal `NO_ISSUES_FOUND` fixture with both a positive assertion (`STATUS=OK` with `--validation-mode`) and a negative control (`STATUS=NOT_SUBSTANTIVE` without — proves the flag actually changes behavior). Wired into `make lint` via the `test-collect-reviewer-bash32` target and the `test-harnesses` aggregator. Added sibling contracts `scripts/collect-agent-results.md` (NEW — pins the bash 3.2 portability invariant at the validator call site, edit-in-sync with the harness regex) and `scripts/test-collect-reviewer-bash32.md` (NEW). Extended `agent-lint.toml`'s exclude array following the established Makefile-only-harness pattern. Documented in `docs/linting.md` mirroring the `test-validate-research-output` row. Co-evolved with /design + /review: 1 design round (5-agent sketch + 3-reviewer plan-review + 2-decision dialectic where both decisions resolved 2-1 voted in favor of the synthesis choice, expansion idiom + hybrid CI strategy; 7 plan-review findings accepted including the sibling `.md` mandate, REPO_ROOT anchoring, ≥200-word fixture requirement, distinct Case 3 fixture for `--validation-mode` forwarding, and `agent-lint.toml` exclude wiring) + 1 code review round (2 findings accepted: bash 4.0-4.3 dynamic-test coverage gap and `:402` → `:405` line-number doc precision after the WHY-comment was added).

## [7.7.0] - 2026-04-25

### Changed

- `/research --plan` is now supported with `--scale=deep`, lifting the previous standard-only restriction. Closes #519. Replaces the deep-mode disable rule (skills/research/SKILL.md:48 — was: warn + force `RESEARCH_PLAN=false`) with full functionality. When `--plan + --scale=deep` is set, Step 1.1 (planner) decomposes `RESEARCH_QUESTION` into 2-4 subquestions as today; Step 1.2 assigns subquestion×angle pairs across the 5 deep-mode lanes via a **balanced partial matrix** (issue #519 dialectic-resolved): the 4 angle lanes (k = 1..4) get a clean ring rotation `(s_{((k-1) mod N)+1}, s_{(k mod N)+1})` so every subquestion appears in at least one named-angle lane (and at least two when N < 4); Claude-inline (lane 5) unions all subquestions as the integrator that ensures cross-coverage regardless of N. At N=2 the ring degenerates to full union for all 4 angle lanes. Step 1.5 synthesis organizes the deep + planner output as **subquestion-major** top level (`### Subquestion N` sub-sections with angle-labeled bullets within), plus a `### Per-angle highlights` sub-section that names the 4 canonical angles by name (architecture & data flow, edge cases & failure modes, external comparisons, security & threat surface — preserves the existing deep-mode contract), plus the `### Cross-cutting findings` sub-section. `lane-assignments.txt` now writes 5 LANE keys (LANE1..LANE5) in deep mode (3 keys remain in standard); both heredoc variants use `<<'EOF'` to defend against shell-expansion of subquestion text. Step 1.4 deep runtime-fallback rehydration uses the failed slot's angle base prompt — `RESEARCH_PROMPT_ARCH` / `_EDGE` / `_EXT` / `_SEC` for the 4 external slots, `RESEARCH_PROMPT_BASELINE` for the Claude-inline integrator — per a canonical lane→slot→angle table pinned in `references/research-phase.md` § 1.4 Deep, NOT a generic baseline prompt (preserves the named-angle-diversity claim). Standard-mode `--plan` path is byte-equivalent to pre-#519 behavior (no changes to standard table or synthesis); Deep-mode `--plan=false` (default) path is byte-equivalent to pre-#519 behavior (no changes to deep numbered template). Planner failure paths (count out of [2,4], empty output, prose-only reply, timeout) fall back to single-question mode with each lane reverting to its existing per-scale base prompt and no per-lane suffix. Cross-doc sweep: `skills/research/SKILL.md` (resolution rule + scale matrix narrative + Step 1 MANDATORY directive); `skills/research/references/research-phase.md` (Contract header + §1.1 / §1.2 gate broadening from `=standard` to `!= quick` + §1.2.a Deep assignment table + §1.2.b 5-key heredoc + §1.2.c per-scale base-prompt rules + §1.3 Deep per-lane suffix preamble + §1.4 Deep runtime-fallback canonical mapping + §1.5 Deep splits into `RESEARCH_PLAN=false` and `RESEARCH_PLAN=true` sub-branches); `README.md` skill catalog row; `docs/skills.md` `--plan` section; `docs/workflow-lifecycle.md` skill description + flag table; `SECURITY.md` `/research --plan` subsection (deep-mode prompt-composition surface widened from 3 lanes to 5; angle-specific runtime-fallback rehydration; unchanged residual-risk model). Extends `scripts/test-research-structure.sh` with Checks 33-37 (5 section-scoped pins: SKILL.md must NOT contain "is not yet supported"; deep-mode resolution-rule fragment ending with literal "full functionality"; §1.5 Deep RESEARCH_PLAN=true sub-branch must mention `### Subquestion` / `### Per-angle highlights` / `### Cross-cutting findings`; §1.4 Deep must name all four angle-prompt literals; §1.2 Deep table must contain `Lane 5 (Claude inline)`). PASS count bumped 36 → 41 assertion gates. Co-evolved with /design + /review: 1 design round (5-agent sketch all converged on additive design + 2-decision dialectic resolved 2-1 each: balanced partial matrix vs rotation-with-integrator, subquestion-major vs angle-major + 3-reviewer plan-review with 11 voted findings unanimously or 2-1 accepted including SKILL.md gate-string sweep, section-scoped structural pins, lane→slot→angle canonical table, operator-facing doc sync, §1.2.c per-scale rewrite, SECURITY.md update, §1.1 scale-neutral phrasing, §1.1.b deep fallback qualifier, §1.5 Deep sub-branch split, hardcoded count bump, and quoted-EOF for 5-key heredoc) + 1 code review round (2 in-scope findings accepted 3-0 and 2-1: sibling-md sync for new Checks, lane-numbering clarification in §1.2.a Deep preamble; 3 pre-existing findings about #525/#526 surface left out of scope). Builds on closed #420 (planner pre-pass infrastructure) and unblocks #522 (`--plan --interactive`, hard-blocked on #519).

## [7.6.0] - 2026-04-25

### Added

- `/research` accepts a new `--keep-sidecar` boolean flag (and `--keep-sidecar=<PATH>` value form; positional path is intentionally rejected per the existing flag-grammar contract). When set, Step 4 cleanup copies a `/issue`-batch markdown sidecar (one <code>### </code>title block per finding, parseable by `skills/issue/scripts/parse-input.sh` via the generic-fallback path) to `./research-findings-batch.md` (default) or the explicit path past the tmpdir cleanup. Closes #510. New helper `skills/research/scripts/render-findings-batch.{sh,md}` with bash + awk extraction: named-bound section slicing (terminates at `### Risk Assessment` / `### Difficulty Estimate` / `### Feasibility Verdict` / `### Key Files and Areas` / `### Open Questions` / top-level <code>## </code> — NOT generic <code>### </code>, so planner-mode `### Subquestion N` headings inside Findings Summary do not truncate), fence-aware (matches `^[[:space:]]*` plus three backticks so indented fenced blocks toggle correctly), three-tier heuristic ladder (numbered, top-level bulleted, paragraph-per-item, with adaptive mode-transitions for planner-mode mixed shapes), `^###[[:space:]]` body-line backslash escape so finding prose containing literal heading-shaped lines does not split items downstream in `parse-input.sh`, and `Finding <N>` empty-title fallback so titles stripped to empty by punctuation-only first sentences do not get silently dropped by `parse-input.sh:161-163`. Helper exit codes 0/1/2/3 (success / usage / report missing or non-regular file / empty findings — non-fatal: writes empty sidecar + stderr warning distinguishing empty-section from missing-section). New harness `skills/research/scripts/test-render-findings-batch.{sh,md}` with 14 fixtures (numbered / bulleted / paragraph / mixed / empty / missing / planner-nested / fenced / column-0 body-hash escape / tab-after-hashes body-escape / indented-fence / quick-disclaimer / special chars / multi-paragraph) plus round-trip integration through `parse-input.sh` (asserts `ITEMS_TOTAL` matches `COUNT` and no `MALFORMED` items). New canonical data file `skills/research/data/quick-disclaimer.txt` consumed by both `references/research-phase.md` Step 1.5 Quick branch (synthesis prose) and `skills/research/SKILL.md` Step 3 (helper `--quick-disclaimer` flag) — single source of truth pinned by structural harness. SKILL.md Step 3 now writes a single authoritative `$RESEARCH_TMPDIR/research-report-final.md` (guarded under `set -euo pipefail` via `if/then/fi` so a write failure sets `SKIP_SIDECAR=true` rather than aborting Step 4 cleanup), invokes the helper, then prints the file via `cat` gated on `[[ -s … ]]` so a missing file from a guarded-write failure does not abort the orchestrator. Step 4 preserve-or-cleanup runs `cp` BEFORE `cleanup-tmpdir.sh` with `realpath`-resolved tmpdir-escape protection (string-prefix fallback documented for missing-realpath platforms — maintainers must NOT remove the realpath branch); empty sidecar surfaces a distinct "empty (no findings extracted)" advertisement; non-empty sidecar advertisement uses `--dry-run` (operator manually escalates to `--go` after content review per SECURITY.md). Co-evolved with /design and /review: 1 design round (5-agent sketch + 3-reviewer plan-review panel with 12 unanimous findings accepted including bash array-expansion correctness, named-bound section extraction, KEEP_SIDECAR_PATH binding, SECURITY.md update, single-authoritative-write pattern, three-location Makefile wiring) plus 1 code review round (8 unique findings accepted: array-expansion bug fix, indented-fence support, tab-after-hashes body-escape, KEEP_SIDECAR_PATH explicit binding, guarded-cat after guarded-write, SKIP_SIDECAR explicit init, exit-2 wording, odd-fence-count known limitation; 2 OOS findings rejected as out-of-scope or phantom). Adds `Makefile` target `test-render-findings-batch` (three locations updated per the `test-run-research-planner` template — `.PHONY` declaration, `test-harnesses` prerequisite chain, recipe). Extends `scripts/test-research-structure.sh` with Checks 27-32 (helper invocation in Step 3, `--keep-sidecar` flag forms in Flags section, `data/quick-disclaimer.txt` cross-reference between SKILL.md and `research-phase.md`, Quick disclaimer file existence, `research-report-final.md` write, Step 4 `KEEP_SIDECAR` cp branch). PASS count bumped 30 to 36. Updates `SECURITY.md` "External reviewer write surface in /research and /loop-review" subsection with a paragraph documenting the opt-in workspace-write trade-off and operator content-review responsibility for security-relevant findings from `/research --scale=deep` `Codex-Sec` lane. Updates `skills/issue/scripts/parse-input.md` with reverse-coupling note: research's sidecar shape depends on this parser's generic-mode behavior; changes to the `^\#\#\#[[:space:]]+` regex or OOS field-branch gates require re-running research's `make lint`.

## [7.5.1] - 2026-04-25

### Changed

- `/research --scale=standard` now runs angle-differentiated lane prompts instead of one shared brief: Cursor → `RESEARCH_PROMPT_ARCH` (architecture); Codex → `RESEARCH_PROMPT_EDGE` by default or `RESEARCH_PROMPT_EXT` when `external_evidence_mode=true` (edge cases / external comparisons); Claude inline → `RESEARCH_PROMPT_SEC` (security). Renames the shared `RESEARCH_PROMPT` literal to `RESEARCH_PROMPT_BASELINE`, restricting it to quick mode and deep-mode's Claude inline lane. Closes #508 (operator decision in umbrella #505: extend the angle prompts; option a). URL-gathering capacity in standard mode is concentrated on the Codex lane by design (only Codex carries the external-evidence prompt under `external_evidence_mode=true`); Cursor (ARCH) and Claude inline (SEC) keep their angle focus regardless. Step 1.5 standard synthesis prose copies deep-mode's "complementary, not redundant" framing so angle-driven divergence is treated as expected rather than contested. Per-lane `--plan` suffix appends to each lane's angle base prompt; single-angle perspective per subquestion is explicitly acknowledged in synthesis prose. Adds `skills/research/scripts/test-standard-angle-prompts.{sh,md}` (offline harness with 7 structural pins on the standard-mode angle assignment, H2-then-H3 nested section extraction so other `### Standard` subsections in 1.4/1.5 cannot satisfy the pins) wired into `make lint` via new `test-standard-angle-prompts` target. Sibling-contract refresh: `scripts/test-research-structure.{sh,md}` Check 5 doc-comment update (`RESEARCH_PROMPT` → `RESEARCH_PROMPT_BASELINE` substring pin); `scripts/test-eval-set-structure.md` cross-reference update; `skills/research/scripts/run-research-planner.md` planner-fallback semantics now name the per-lane angle base prompts; `skills/research/scripts/test-degraded-path-banner.md` four-way edit-in-sync rule (added SKILL.md Step 3 as surface 4, pinned by Check 22 of test-research-structure.sh). Cross-doc sweep: `skills/research/SKILL.md` top-line + scale matrix + Step 1 MANDATORY directive; `README.md` skill catalog; `docs/skills.md`, `docs/agents.md`, `docs/workflow-lifecycle.md`, `skills/shared/progress-reporting.md`, `docs/linting.md` (new make target row). Co-evolved with /design + /review: 1 design round (5-agent sketch all converged + 3-reviewer plan review with 10 voted findings, all 10 accepted including external-evidence narrowing documentation, sibling-md updates per AGENTS.md, test-harness section-scoping correction, and cross-doc sweep extension) + 3 code review rounds (round 1 — 5 findings, 2 accepted: 4-surface edit-in-sync rule, count + Checks 21-22 documentation; round 2 — Check 21a-21e descriptions corrected to match script behavior; round 3 — NO_ISSUES_FOUND, loop converged).

## [7.5.0] - 2026-04-25

### Added

- `/issue` accepts a new `--sentinel-file <path>` flag and writes a small post-success KV sentinel (`ISSUE_SENTINEL_VERSION=1`, counters, `TIMESTAMP`) at the end of Step 7 when `ISSUES_FAILED=0 AND not dry-run` (closes #509). The sentinel proves *execution*, not *creation count* — the all-dedup case (`ISSUES_CREATED=0`, `ISSUES_FAILED=0`, `ISSUES_DEDUPLICATED>=1`) writes the sentinel because a successful dedup-only run is a legitimate `/issue` outcome (plan-review FINDING_1 overruled the issue body's stricter `ISSUES_CREATED>=1` gate that would have caused false-aborts in `/research`). `/research` gains a new `## Filing findings as issues` numbered procedure (5 steps: defensive `rm -f`, invoke `/issue --sentinel-file $RESEARCH_TMPDIR/issue-completed.sentinel`, parse `ISSUES_*` stdout (primary mechanical check), invoke `${CLAUDE_PLUGIN_ROOT}/scripts/verify-skill-called.sh --sentinel-file ...` (defense-in-depth supplementary gate, fail-closed on missing sentinel), explicit fail-closed-on-any-failure intent doc) — mirrors the `/alias → /implement` sentinel pattern (dialectic DECISION_1, THESIS 2-1: reuse `verify-skill-called.sh` over inline `[ -f ]` for cross-skill mechanical-vocabulary parity). `subskill-invocation.md` "Post-invocation verification" gains a third canonical example with explicit reconciliation: stdout parsing of `ISSUES_*` is the **primary** post-`/issue` mechanical check (canonical for `/implement`); the sentinel+verify pattern is `/research`-specific defense-in-depth on top of stdout parsing (plan-review FINDING_2). Path resolution: `--sentinel-file` is the narrow per-call flag (NOT `--session-env`, plan-review FINDING_10 — replaces the issue body's `--session-env` reader to avoid widening `/issue`'s public arbitrary-path write surface). Default path `${TMPDIR:-/tmp}/larch-issue-$$.sentinel` is **child-local only** — `$$` differs across processes so the default cannot serve as a cross-process handoff (FINDING_4); `/issue` Step 9 cleans up the default-path sentinel itself when `--sentinel-file` was not supplied (FINDING_3 — prevents `/tmp` accumulation for non-opting callers). New `skills/issue/scripts/write-sentinel.{sh,md}` helper with atomic same-dir mktemp + mv (rename-atomicity, not durability — FINDING_1 review-fix); status output to **stderr** to preserve `/issue` Step 7's `^(ISSUES?_[A-Z0-9_]+)=` stdout grammar (FINDING_5). Argument parser uses `${2-}` + `require_value` helper to emit stable `ERROR=Missing value for <flag>` instead of `set -u` "unbound variable" on a trailing value-taking flag with no value (FINDING_3 review-fix). New `skills/issue/scripts/test-sentinel-write.{sh,md}` regression harness — 12 cases × 35 sub-assertions (all-success / all-dedup / partial-failure / dry-run / explicit path / channel discipline / structural mktemp+mv pin / 4 argument-validation cases / missing-value flag case). Extends `scripts/test-research-structure.sh` with Checks 23-26 (numbered procedure pins for the `## Filing findings as issues` section: `rm -f`, `--sentinel-file` arg, `verify-skill-called.sh` invocation, fail-closed intent literal). PASS count bumped 26 → 30. Test-ownership choice (extend `test-research-structure.sh` rather than create a new `test-anti-halt-mechanical.sh`) is the dialectic DECISION_2 outcome (ANTI_THESIS 3-0 — synthesis was overruled). Co-evolved with /design + /review: 1 design round (5-agent sketch + 3-reviewer plan review + 2-decision dialectic + 11 voted findings, 10 accepted including the all-dedup correctness fix and the `--session-env` → `--sentinel-file` security narrowing) + 1 code review round (4 unique findings + 1 OOS, 3 in-scope accepted: fsync-comment correction, test-isolation fix, set-u argument-parser bug fix; 1 OOS accepted for separate filing).

## [7.4.29] - 2026-04-25

### Changed

- `/research` Step 1.5 synthesis now emits a "Reduced lane diversity" banner when any external lane (Cursor or Codex) ran as a Claude-fallback, prepending `**⚠ Reduced lane diversity: <N_FALLBACK> of <LANE_TOTAL> external research lanes ran as Claude-fallback. The model-family heterogeneity claim does not hold for this run.**` to BOTH the printed `## Research Synthesis` AND `$RESEARCH_TMPDIR/research-report.txt` so Step 2 validation reviewers see the diversity caveat. Per-scale formulas: standard `LANE_TOTAL=2`, `N_FALLBACK = (RESEARCH_CURSOR_STATUS != ok) + (RESEARCH_CODEX_STATUS != ok)` ∈ {0,1,2}; deep `LANE_TOTAL=4`, `N_FALLBACK = 2*(RESEARCH_CURSOR_STATUS != ok) + 2*(RESEARCH_CODEX_STATUS != ok)` ∈ {0,2,4}. Quick mode is unchanged — its existing `**Single-lane confidence — no validation pass.**` disclaimer stays. The per-scale formulas correct the issue spec's original `LANE_TOTAL=3`/`5` (which conflated external lanes with the Claude inline lane); plan review surfaced and resolved this 3-way unanimous correctness finding before implementation. The deep-mode `2*` multiplier mirrors `lane-status.txt`'s per-tool aggregation (each tool covers 2 external slots) and is documented as a known limitation that can overstate by 1 in the partial-degradation mid-flight case. Adds `skills/research/scripts/test-degraded-path-banner.{sh,md}` (offline harness with 4 fixtures × 2 scales + reference-impl assertions + prose pins, wired into `make lint` via new `test-degraded-path-banner` target). Extends `scripts/test-research-structure.sh` with Checks 21a-21e (section-scoped pins on the §1.5 banner preamble + 3 branches' references + Quick negative check) plus Check 22 (banner phrase pin in `skills/research/SKILL.md` Step 3 example). PASS count bumped 20 → 26. The four edit-in-sync surfaces (research-phase.md preamble, test-research-structure.sh, test-degraded-path-banner.sh, SKILL.md) are documented in the sibling `test-degraded-path-banner.md` contract per AGENTS.md "Per-script contracts live beside the script". Co-evolved with /design + /review: 1 design round (5-agent sketch + plan review with 9 unanimous findings accepted, including the LANE_TOTAL semantic correction) + 1 code review round (7 unique findings accepted including unreadable-fixture handling, section-extractor cross-section leakage fix in `test-research-structure.sh`, SKILL.md edit-in-sync surface addition, content-order ambiguity clarification, and the deep-mode partial-degradation known-limitation paragraph). Closes #506.

## [7.4.28] - 2026-04-25

### Changed

- `/fix-issue` Step 0 now folds the prior fetch + lock + (deferred) `[IN PROGRESS]` title rename into a single `find-lock-issue.sh` invocation that runs Find + Lock + Rename atomically, eliminating the multi-minute delay between the comment lock posting and the title prefix appearing (closes #496). The script is renamed from `fetch-eligible-issue.sh` to `find-lock-issue.sh` and gains an exit-code-3 contract for `eligibility passed but lock failed`. /fix-issue collapses Steps 0+1 → 0 and renumbers 2..9 → 1..8 throughout SKILL.md, references (`triage-classification.md`, `non-pr-execution.md`), `shared/subskill-invocation.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, `agent-lint.toml` comment blocks, `eval-set.md` eval-13 keyword, and the two existing fix-issue test harnesses (`test-fix-issue-step-order.{sh,md}` rewritten for the new Step 0 = find & lock / Step 1 = setup structure; `test-fix-issue-bail-detection.{sh,md}` extraction window shifted from `### 6a` / `## Step 7` to `### 5a` / `## Step 6` and `Skip to Step 9` → `Skip to Step 8`). Adds a new hermetic offline harness `test-find-lock-issue.{sh,md}` with a PATH-prepended `gh` stub covering five executed fixtures (eligible+lock+rename ok; lock-fail with exit 3; rename-fail best-effort with stderr WARNING; ineligible managed-prefix; auto-pick no candidates) plus a deferred-coverage note for idempotent rename no-op (covered by `test-tracking-issue-write.sh`). Adds best-effort terminal `tracking-issue-write.sh rename --state done` calls on the not-material (Step 3) and NON_PR (Step 6b) close paths so closed issues no longer persist with the misleading `[IN PROGRESS]` title prefix on those /implement-bypassing flows. /implement Step 0.5 Branch 2's `tracking-issue-write.sh rename` call is preserved as an idempotent defensive no-op (`RENAMED=false` short-circuit) so standalone `/implement --issue` against non-pre-marked issues still gets the visibility marker. Internal-script-only refactor — no public CLI surface change (/fix-issue flags and positional argument unchanged); fetch-eligible-issue.sh is plugin-internal so the rename has no external API impact. Co-evolved with the design / review process: 1 round of /design (5-agent sketch + 3-judge dialectic on 2 contested decisions) + 1 round of 3-reviewer code review surfaced 18 findings total across plan-review and code-review (cross-doc cascade alignment + 1 substantive correctness fix on the Exit 3 recovery prose flagged by Codex), 17 accepted and 1 each exonerated.

## [7.4.27] - 2026-04-25

### Changed

- `skills/shared/dialectic-protocol.md` `## Disposition Enum` section's two /design-only-framed clauses scoped for both callers after #469 made the Consumer Contract dual-caller. The `over-cap` row's `Step 3.5 treats as still-contested` clause now carries an explicit `For /design:` qualifier (no /research --adjudicate parallel — research has no Step 3.5, and the "no debate occurred" semantics already suffice). The trailing paragraph after the disposition table now scopes its /design-only `Step 2a.4` / `Step 2b` / "antithesis engagement prose" sentence with `For /design:` and adds a parallel `For /research --adjudicate:` clause matching the existing Consumer Contract item 3 vocabulary (validation-merge synthesis stands; Step 2.5 must not reinstate a finding for non-`voted` entries — no reinstatement-into-validated-synthesis sub-step where the dialectic layer did not produce a heard counter-position). Pre-existing drift; predates #469. Closes #499.

## [7.4.26] - 2026-04-25

### Fixed

- `skills/shared/dialectic-protocol.md` Tally and Resolution section: typo `bothhere` → `both` in the `voted`-eligible decision sentence so it reads "both sides passed the eligibility gate". Pre-existing OOS surfaced by Cursor during round-2 review of #469. Closes #498.

## [7.4.25] - 2026-04-25

### Changed

- Cross-doc sweep applying the canonical execution-vs-publication disambiguation phrasing for `/research --scale=quick` (already in `skills/research/SKILL.md` line 17 + `### Quick (RESEARCH_SCALE=quick)` subsection per PR #482/#449) to 9 lines across 7 satellite docs: `README.md:111`, `docs/workflow-lifecycle.md` (lines 136 + 161), `docs/agents.md` (lines 49 + 75 — second occurrence in the Research Agents subsection caught during plan review and added to scope), `docs/review-agents.md` (lines 96 + 98 — both the table cell and Note A updated for within-file consistency), `docs/skills.md:117`, and `skills/research/references/research-phase.md:311` (appended cross-reference clause without modifying the existing lane-status sentence). Each new phrasing names both layers explicitly: Step 2 (validation panel) for execution and the 0-reviewer Validation phase placeholder line for publication. Two intentionally-untouched matches in `docs/workflow-lifecycle.md:163` and `docs/skills.md:122` describe `--adjudicate` orchestration semantics ("no rejections to adjudicate when Step 2 doesn't run"), not the report-rendering claim — code-review panel re-examined and confirmed (1Y/1E/1N, 2+ YES threshold not met). Pre-existing OOS surfaced during PR #482 plan review (FINDING_4, 3-0 accepted) and code review (FINDING_1, 3 EXONERATE). Closes #495.

## [7.4.24] - 2026-04-25

### Changed

- `skills/shared/dialectic-protocol.md` Consumer Contract section now enumerates both callers (`/design` Steps 2b/3.5 parsing `$DESIGN_TMPDIR/dialectic-resolutions.md`; `/research --adjudicate` Steps 2.5/3 parsing `$RESEARCH_TMPDIR/adjudication-resolutions.md`) and documents per-caller existence/short-circuit guards, the caller-specific `Resolution` literal sets (`/design` uses `{CHOSEN}`/`{ALTERNATIVE}`; `/research --adjudicate` uses `reinstate`/`rejection-stands`), and a parallel research-side paragraph in `## Scope and Precedence`. Field names and the `Disposition` enum stay shared across callers so a single parser can extract them. Pre-existing documentation gap unrelated to issue #440. Closes #469.

## [7.4.23] - 2026-04-25

### Fixed

- `scripts/build-research-adjudication-ballot.sh` now fails closed (exit 2 with `FAILED=true` / `ERROR=REJECTED_FINDING_<N> is incomplete...`) on any incomplete `### REJECTED_FINDING_<N>` block (missing one of `Reviewer`, `Finding`, or `Rejection rationale`; whitespace-only field bodies treated as missing). The prior soft-drop policy created a `DECISION_k → REJECTED_FINDING_<N>` mapping inconsistency between this builder and `skills/research/references/adjudication-phase.md` Step 2.5.5: the builder dropped incomplete records before numbering, but Step 2.5.5's reverse-mapping algorithm parsed all blocks (no completeness filter) and could reinstate the wrong rejected finding into the validated synthesis when one or more captures were degraded. The completeness check uses shadow `finding_check` / `rationale_check` variables so the original payload bytes flow unchanged into Phase 2's `sha256(finding_text)` sort key and Phase 3's ballot body — required so Step 2.5.5's raw-block hashes match the builder's verbatim hashes. Per dialectic resolution DECISION_2, `scripts/run-research-adjudication.sh` gains a narrow string guard that prepends an `incomplete-input:` tag to the coordinator's `ERROR=` line when the builder's failure matches the anchored sentinel `^REJECTED_FINDING_[0-9]+ is incomplete`, so operators distinguish malformed input from generic builder breakage at the coordinator seam. The previously soft `DECISION_COUNT=0` short-circuit on header-positive input is converted to a defensive parser-regression hard fail. Sibling contracts (`build-research-adjudication-ballot.md`, `run-research-adjudication.md`, `adjudication-phase.md` Step 2.5.5, `test-research-adjudication.md`) updated in lockstep. Five new harness assertions (Tests 12-16) pin the fail-closed contract: mixed complete+incomplete, lone incomplete, whitespace-only field, coordinator `incomplete-input:` prefix, and verbatim leading/trailing whitespace preservation in ballot. Pre-existing OOS surfaced during PR #420 review. Closes #462.

## [7.4.22] - 2026-04-25

### Fixed

- `scripts/validate-research-output.sh` probe 1 split into long-tier (relaxed rule, current behavior unchanged) and short-tier (strict path-likeness rule for the `lock|env|txt|c|h|m|r` extensions). Short-tier citations must carry a path-likeness signal — `/`, `_`, `-` somewhere in the stem, OR a trailing `:line-ref` — so prose tokens like `the spin.lock primitive`, `the my.env switch`, `the big.m optimization`, `the foo.r constant`, and `the raw.txt format` no longer match probe 1. **Forward-compat behavioral change**: bare short-extension citations like standalone `Cargo.lock`, `main.c`, `app.env`, `foo.h`, `notes.txt` (no `/`, `_`, `-` in basename, no `:line-ref`) are no longer markers — operators citing short-extension files in `/research` outputs must add a line-ref (e.g., `Cargo.lock:7`) or path segment (e.g., `kernel/spin.lock`, `parser_state.h`, `kernel-mod.h`). Long-tier extensions (`.go`, `.py`, `.md`, `.json`, etc.) are unaffected. The fix updates the script header, the sibling contract `scripts/validate-research-output.md`, the regression harness `scripts/test-validate-research-output.sh` (51 cases now, up from 38; 13 new cases for the short-extension rule), and the case-count line in `docs/linting.md`. BSD/macOS `grep -E` compatible. Closes #473.

## [7.4.21] - 2026-04-25

### Fixed

- `scripts/eval-research.sh` now exits 2 (not 1) when a value-taking flag is invoked with no following value (e.g. a trailing `--baseline`). Pre-fix, `shift 2` aborted under `set -euo pipefail` with exit 1, colliding with the documented schema-validation exit code and making malformed flag invocations indistinguishable from real schema failures to wrappers checking `$?`. A new `require_value` helper applies an arity check before each `shift 2` for all seven value-taking flags (`--id`, `--scale`, `--baseline`, `--work-dir`, `--write-baseline`, `--timeout`, `--judge-timeout`) and emits a clear stderr message naming the offending flag. The exit-code contract in `scripts/eval-research.md` is updated, and `scripts/test-eval-research-baseline-flag.sh` adds Sub-4 spot-checking the trailing-`--baseline` regression. Closes #477.

## [7.4.20] - 2026-04-25

### Fixed

- `scripts/build-research-adjudication-ballot.md` fixture-case table row at line 108 corrected to use the leading `]`-delimiter case. The prior row claimed input `[Code] The orchestrator skipped negotiation step 3.` is stripped, with a rationale citing the regex `^[Code]\s*`, but the leading-prefix regex applied at `scripts/build-research-adjudication-ballot.sh:252` is anchored on the alternation members (`Cursor|Codex|Claude|Code-Sec|Code-Arch|Code|orchestrator|Code Reviewer`) followed by a delimiter from `{':', ']', ')'}` — a line whose first non-space character is `[` does not satisfy the anchored alternation, so `[Code] ...` is NOT stripped. Row rewritten to first-line input `Code] The orchestrator skipped negotiation step 3.` with rationale citing the regex `^Code\s*]\s*`, preserving pedagogical coverage of the `]`-delimiter alternative in the fixture table. Pre-existing OOS — not introduced by issue #461. Closes #485.

## [7.4.19] - 2026-04-25

### Fixed

- `scripts/build-research-adjudication-ballot.md` "Test harness" paragraph now correctly describes the Makefile wiring: the harness runs under `make lint` locally (since `lint: test-harnesses lint-only`) and under CI's `test-harnesses` job (split from `lint-only` in CI per `docs/linting.md`), and is NOT part of `make smoke-dialectic`. The previous text incorrectly claimed the harness was wired into `make test-harnesses` "(NOT `make lint` and NOT `make smoke-dialectic`)", contradicting the actual `Makefile:9` definition (`lint: test-harnesses lint-only`) and the sibling test script's own header comment at `scripts/test-research-adjudication.sh:28-33`. The replacement matches the sibling-script header phrasing for cross-file consistency. Closes #486.

## [7.4.18] - 2026-04-25

### Fixed

- `/research` deep-mode Step 3 lane-attribution headers now derive from the per-phase `RESEARCH_*` / `VALIDATION_*` slices in `$RESEARCH_TMPDIR/lane-status.txt` instead of mutable session-wide `cursor_available` / `codex_available` flags. A new sibling renderer `scripts/render-deep-lane-status.sh` emits the deep-mode 5+5 header shape (5 research agents + 5 validation reviewers) reading the same 8-key schema as standard mode. A new shared library `scripts/render-lane-status-lib.sh` factors out `render_lane()` and `sanitize_reason()` so both renderers share one canonical token vocabulary; `RENDER_LANE_CALLER` parameterizes the unknown-token stderr warning so each consumer attributes correctly. Standard mode rendering remains byte-stable (`scripts/render-lane-status.sh` `printf` block unchanged; existing 10-fixture harness passes). Eliminates cross-phase contamination: a validation-only fallback (e.g., a Cursor render failure during validation flipping `cursor_available=false`) no longer retroactively taints research-phase attribution. Granular fallback reasons (binary missing / probe failed / runtime timeout / runtime failed) now surface in deep-mode headers with the same vocabulary as standard. New harness `scripts/test-render-deep-lane-status.sh` (9 fixtures, 19 assertions) includes phase-segregation guards F2 and F3 as direct bug-fix witnesses. `scripts/test-research-structure.sh` extends from 18 to 20 assertions: Check 19 section-scopes the `render-deep-lane-status.sh` invocation pin to the `### Deep (RESEARCH_SCALE=deep)` subsection; Check 20 (fence-aware extractor + symmetric `cursor_available` / `codex_available` regex) anti-regression-pins that the deep branch never re-derives headers from session-wide flags. `agent-lint.toml` exclusions added for the sourced-only library and Makefile-only test harness. Closes #451.

## [7.4.17] - 2026-04-25

### Fixed

- `scripts/build-research-adjudication-ballot.sh` attribution scrubber now strips the deep-mode reviewer attributions `Code-Sec` and `Code-Arch` (introduced by `/research --scale=deep`) at anchored prefix/suffix positions, in addition to the standard `Cursor|Codex|Claude|Code|orchestrator|Code Reviewer` set. Without this, a deep-mode reviewer's rejected finding carried into adjudication preserved its leading `Code-Sec:` / `Code-Arch:` attribution inside `<defense_content>`, breaking the anonymous-Defense-A/B guarantee since judges could infer which deep-mode lane authored the defense. The two new tokens precede `Code` in the alternation so the longer deep-mode names match before the shorter prefix (POSIX ERE leftmost-longest within an alternation is unreliable across awk implementations; explicit ordering is portable). The script's file-header comment block documenting the regex literal and the sibling contract `scripts/build-research-adjudication-ballot.md` (Anchored-only attribution stripping section, Regex applied block, fixture-case table, deterministic-ordering inequality chain) are updated in lockstep. The harness `scripts/test-research-adjudication.sh` adds Test 11 covering anchored prefix stripping (`Code-Sec:` / `Code-Arch:`), anchored suffix stripping (`(Code-Sec)` / `— Code-Arch`), and mid-content preservation. Closes #461.

## [7.4.16] - 2026-04-25

### Fixed

- `scripts/build-research-adjudication-ballot.sh` `emit_failure` now writes `FAILED=true` / `ERROR=<msg>` to stderr (fd 2) instead of stdout (fd 1). The two `emit_failure` calls in the Phase 3 `base64 -d` failure paths are inside the `{ ... } > "$OUTPUT"` brace group; with the former stdout output, the failure lines were redirected into the ballot file, leaving the caller (`scripts/run-research-adjudication.sh`) with no `ERROR=` line to extract via `grep -E '^ERROR='` and forcing it to fall back to a hardcoded "Ballot builder failed" message. The in-repo caller already merges streams via `2>&1`, so its existing extraction continues to work after the fix. Header docstring, `usage()` heredoc, and sibling contract `scripts/build-research-adjudication-ballot.md` updated to describe the split-stream output contract. New regression Test 10 in `scripts/test-research-adjudication.sh` asserts `ERROR=` lands on stderr (not stdout) under separated-stream capture, with a parallel assertion that caller-style `2>&1` merge still surfaces the line. Pre-existing OOS surfaced during PR #420 review; not introduced by #420 (the ballot builder was added in PR #443). Closes #463.

## [7.4.15] - 2026-04-25

### Changed

- `skills/fix-issue/SKILL.md` Known Limitations — extended the "Lock-before-setup behavioral delta" bullet to explicitly cite preflight `git fetch origin main` (run by `session-setup.sh` via `preflight.sh` before mktemp) as the network-bound, transient Step 2 failure most likely to leave a stale `IN PROGRESS` lock under the `fetch → lock → setup` ordering introduced by PR #468, alongside the existing non-network `REPO_UNAVAILABLE=true` example. Adds an editorial note recording that the design panel for the related reorder voted 3 EXONERATE on the heavier "split `session-setup.sh` into pre-lock preflight + post-lock setup" mitigation (judging the structural split heavier than warranted), so the documented failure mode is the accepted trade-off rather than a deferred bug. Documentation-only; no `session-setup.sh` / `preflight.sh` code changes, no step reordering, no new test harness. Closes #471.

## [7.4.14] - 2026-04-25

### Fixed

- `scripts/test-research-structure.sh` Check 12 — replaced the two-grep AND (`grep -Fq "Aborting" && grep -Fq "must be one of quick|standard|deep"`) with a single `grep -Fq` of the full composite literal `must be one of quick|standard|deep (got: foo). Aborting.`, the intended `--scale=foo` error sentence in `skills/research/SKILL.md`. The prior two-grep form succeeded if either substring appeared anywhere in the file, so an unrelated `Aborting` elsewhere could satisfy it spuriously. Failure message and the sibling contract assertion (12) in `scripts/test-research-structure.md` updated to reference the composite literal. Pre-existing OOS surfaced during PR #420 review. Closes #460.

## [7.4.13] - 2026-04-25

### Fixed

- `skills/research/SKILL.md` — aligned two outlier prose statements with the canonical "always-print-with-zero-marker" rule for quick mode's report-publication layer. Line 17 (overview) previously said "skips the validation phase entirely"; line 139 (Step 0b) previously said Step 3 "omits the validation-phase line entirely". Both contradicted the Step 3 Quick branch (lines 226-233) which sets `VALIDATION_HEADER="0 reviewers (validation phase skipped — see synthesis disclaimer)"` and explicitly states "the validation-phase line is still rendered ... so the report template's structure is preserved", and the unconditional report template at line 252 (`**Validation phase**: <VALIDATION_HEADER>`). The fix disambiguates two surfaces: (a) execution layer — Step 2 (validation panel) does not run in quick mode; (b) publication layer — the report still renders a `**Validation phase**: 0 reviewers (...)` placeholder line so the template shape is uniform across scales. Edit 2's parenthetical uses a section-heading anchor rather than approximate line numbers (per /design plan-review FINDING_1). Closes #449.

## [7.4.12] - 2026-04-25

### Fixed

- `scripts/validate-research-output.sh` exit-4 diagnostic now reads `file missing or not readable: <path>` instead of `file not found: <path>`. The predicate gating exit 4 is `[[ ! -r "$INPUT" ]]`, which is true for both a nonexistent file and an existing-but-permission-denied file, so the original "file not found" wording silently mis-described the second case. The combined wording matches the existing repo convention used in `scripts/render-reviewer-prompt.sh:86`. Header-comment contract lines documenting exit 4 and the sibling `scripts/validate-research-output.md` updated in lockstep; the regression test `scripts/test-validate-research-output.sh` case 15 only asserts exit code 4, not the diagnostic text, so no test edits were required (38/38 cases still pass). Closes #459.

## [7.4.11] - 2026-04-25

### Fixed

- `scripts/test-research-adjudication.md` — corrected the contract heading from "Scope (seven assertions)" to "Scope (nine assertions)" and added bullets describing Test 8 (multi-line Finding/rationale round-trip via the FS sentinel substitution) and Test 9 (literal-tab round-trip via the GS sentinel substitution + tr-decode). Extended the Edit-in-sync invariants subsection with FS-sentinel and GS-sentinel substitution rules so future edits to those encoders surface the matching test updates. `scripts/test-research-adjudication.sh` header (lines 5-15) — replaced the stale 7-item listing with a 9-item listing that mirrors the actual test order in the script (1: empty input; 2: deterministic ordering; 3: DECISION renumbering; 4: position rotation; 5: anchored-only attribution stripping; 6: `<defense_content>` wrapping; 7: ballot header text; 8: multi-line round-trip; 9: literal-tab round-trip). Pure documentation drift fix; no behavioral change to the harness. Pre-existing OOS surfaced during PR #420 review; not introduced by #420. Closes #457.

## [7.4.10] - 2026-04-25

### Changed

- `scripts/build-research-adjudication-ballot.sh`'s `strip_attribution()` awk END block dropped the dead `prefix_re` variable assignment. Only `prefix_re_short` was ever read (applied to the first non-empty line); the unused `prefix_re` was a maintenance/clarity hazard for future regex tweaks. `prefix_re_short` and `suffix_re` remain unchanged. Pre-existing OOS surfaced during issue #420 review. Closes #458.

## [7.4.8] - 2026-04-25

### Fixed

- `SECURITY.md` line 70 — corrected the `tracking-issue-write.sh` outbound-path subsection's count from "nine assertion categories" to "eleven assertion categories (a)–(k)", matching the canonical (a)–(k) ID table in `scripts/test-tracking-issue-write.md` and the `Eleven assertion categories (a-k)` header comment in `scripts/test-tracking-issue-write.sh`. Added an inline pointer from the SECURITY.md sentence to the canonical ID table so future drift between the count word and the table is caught at edit-time. Pre-existing OOS surfaced during PR #420 review (Cursor); not introduced by #420. Closes #456.

## [7.4.7] - 2026-04-25

### Fixed

- `scripts/validate-research-output.sh` provenance probe 1 (line 182) now broadens the recognized extension list from 13 to 51 entries (adding `tsx`, `jsx`, `vue`, `html`, `css`, `scss`, `rb`, `java`, `c`, `cpp`, `h`, `kt`, `swift`, `php`, `cs`, `lua`, `r`, `m`, `scala`, `dart`, `gradle`, `mk`, `cfg`, `ini`, `env`, `lock`, `proto`, plus a few other common forms) and requires a trailing-token boundary so the extension cannot bleed into adjacent path-token characters. Boundary class `[^A-Za-z0-9_:/-]` excludes alnum, `_`, `-`, `:`, and `/`; `.` IS a valid boundary so sentence-ending periods (`See foo.sh.`) and compound-extension forms (`Cargo.lock.bak`, `bundle.js.map`) match by substring evidence, while bypass forms (`file.mdjunk:42`, `file.md:garbage`, `file.md/child`) are rejected. Alternation is ordered longest-first within each prefix-conflict family (`cc|cfg|cjs|cpp|css|csv|cs|c`, `html|htm|hpp|h`, `json|jsx|js`, `mjs|mk|mm|md|m`, `rb|rs|r`, `tsx|tsv|ts`) so `grep -E` on BSD/macOS does not depend on backtracking-through-alternation to satisfy the trailing-boundary constraint. Updates lock down behavior across `scripts/validate-research-output.sh` (probe 1 regex + the script-header extension list which feeds `--help`), the sibling contract `scripts/validate-research-output.md` (extension list, boundary semantics, documented limitations: bare hidden-file forms `.env:7` / `.gitignore:5` not matched; underscore-glued prose like `file.md_for` not matched; short / generic-English extensions like `lock`/`env`/`txt`/`r`/`m` may false-positive on prose tokens), the regression test `scripts/test-validate-research-output.sh` (38 cases — added 25-30 for broadened extensions, 31-32 for fake-citation bypass rejection, 33-34 for happy-path / prose-glued comma, 35 for compound-extension acceptance, 36 for sentence-ending period acceptance, 37-38 for `:garbage` / `/child` bypass rejection; harness header listing extended to 1-38), and `docs/linting.md` (case count 24 → 38). Closes #447.

## [7.4.6] - 2026-04-25

### Changed

- `scripts/test-design-structure.sh` now pins the Step-3a removal that landed in PR #454 with two additional structural assertions: Check 5 grep-walks the entire `skills/design/` tree (SKILL.md and `references/**`) for the residue tokens `Step 3a`, `Post-Review Confirmation`, `user-qa-happened`, `qa_happened`, `dialectic_adjudicated` and fails on any match; Check 6 verifies that `skills/design/SKILL.md`'s Step 3 ("all reviewers OK") branch and Step 3.5 auto-mode branch both forward to `Step 3b` (literal-match `or Step 3b if auto_mode=true` and `and proceed to Step 3b` respectively). The success line now reports "all 6 structural invariants hold". `scripts/test-design-structure.md` documents Checks 5 and 6 in the contract per the AGENTS.md per-script-contracts rule. No Makefile changes — the existing `test-design-structure` `make lint` target continues to wire the harness in. Closes #453.

## [7.4.5] - 2026-04-25

### Added

- `skills/fix-issue/scripts/test-fix-issue-step-order.sh` — offline regression harness pinning the `/fix-issue` Step 1 = lock, Step 2 = setup ordering established by PR #468 (closes #445). Twelve assertions over `skills/fix-issue/SKILL.md`: nine textual literal pins (Step Name Registry rows, section headings, anti-pattern #1 wording, lock breadcrumb literals positive/negative) plus three operational ordering pins (`awk`-scoped block extraction asserting that the Step 1 block contains the `issue-lifecycle.sh ... --lock` invocation, the Step 1 block does NOT contain `session-setup.sh`, and the Step 2 block contains `session-setup.sh --prefix claude-fix-issue --skip-branch-check`). The block-scoped assertions are the load-bearing guard against a future edit that keeps headings/registry/breadcrumbs intact while moving setup back into the lock block. Sibling contract `skills/fix-issue/scripts/test-fix-issue-step-order.md` documents the assertion list and edit-in-sync rules. Wired into `make lint` via the `test-fix-issue-step-order` target under `test-harnesses`; both the `.sh` and the sibling `.md` are added to `agent-lint.toml`'s `exclude` lists, matching the same Makefile-only-reference pattern used by `test-fix-issue-bail-detection`. Co-evolved with the PR review process: 1 round of /review surfaced FINDING_1 (header-comment / accumulator-pattern accuracy) and FINDING_2 (operational ordering not pinned by literal-only assertions); both accepted by 2-1 vote and applied before merge. Closes #445 follow-up.

## [7.4.4] - 2026-04-25

### Changed

- `skills/shared/dialectic-protocol.md` is now caller-neutral: every `$DESIGN_TMPDIR` placeholder in the Overview, Ballot Format, Judge Prompt Template, judge-launch bash blocks, and the Writing dialectic-resolutions.md section was renamed to a generic `$DIALECTIC_TMPDIR` placeholder, and a new `## Caller Binding` section near the top documents that callers MUST substitute the literal `$DIALECTIC_TMPDIR` token with their own session-tmpdir path at prompt-construction time (a *prompt-construction substitution rule, not a shell-level variable export* — external CLIs do not expand shell variables in prompt arguments). The two known callers were updated in lockstep with caller-binding paragraphs: `skills/design/references/dialectic-execution.md` documents `DIALECTIC_TMPDIR ↔ $DESIGN_TMPDIR` (semantic correspondence — the file's bash continues to use `$DESIGN_TMPDIR` directly); `skills/research/references/adjudication-phase.md` documents `DIALECTIC_TMPDIR ↔ $RESEARCH_TMPDIR` (body uses `$RESEARCH_TMPDIR` directly with research-context basenames `research-adjudication-ballot.txt` / `adjudication-resolutions.md`). The adjudication-phase.md substitution-note paragraph (line 13) was rewritten to drop the now-inaccurate "$RESEARCH_TMPDIR substituted for $DESIGN_TMPDIR" framing and replace the implementer checklist with three distinct, non-self-matching grep entries scoped to executable bash code-fenced blocks — items 1, 2, 3 cover the design-context tmpdir variable, ballot filename, and resolutions filename respectively, each describing the failure mode the grep catches without spelling the literal token in checklist prose. Closes #440.

## [7.4.3] - 2026-04-25

### Changed

- `/fix-issue` now acquires the `IN PROGRESS` comment lock at Step 1, immediately after Step 0 fetches an eligible issue, before Step 2 session setup. The prior `fetch → setup → lock` ordering left a TOCTOU window between candidate selection and lock acquisition; the new `fetch → lock → setup` ordering narrows that window. Trade-off: a Step 2 setup failure (e.g. `REPO_UNAVAILABLE=true`) can now strand the issue locked with `IN PROGRESS` rather than leaving the `GO` sentinel intact — recovery is the same manual `IN PROGRESS` clearance + re-add `GO` flow as any other post-lock failure, documented in Known Limitations under "Lock-before-setup behavioral delta". `issue-lifecycle.sh` resolves repo identity itself via `gh repo view`, so the lock script does not depend on session-setup state. Cross-doc renumbering: `skills/fix-issue/SKILL.md` Step Name Registry, anti-pattern 1, Mindset crash-locus bullet, Step 0 / Step 9 cross-references, Known Limitations, the triage-classification reference's `Do NOT load` early-exit list; `skills/fix-issue/scripts/fetch-eligible-issue.sh` header comment; `skills/fix-issue/scripts/issue-lifecycle.md` contract preamble; `skills/shared/subskill-invocation.md` session-env handoff bullet; `scripts/tracking-issue-write.md` distinction-from-comment-lock note; `agent-lint.toml` parser-and-harness exclusion comments.

## [7.4.2] - 2026-04-25

### Fixed

- `scripts/eval-research.sh validate_eval_set()` now rejects entries whose id does not match `^[a-z0-9-]+$` (lowercase letters, digits, and hyphens only) and tracks duplicate ids across the eval set, so duplicates and path-like ids fail fast under `--smoke-test` before `run_one_research()` uses the raw id as `$WORK_DIR/$id` (closes #442). The duplicate-detection `case` is gated on format-validity so glob metacharacters (`*`, `?`, `[`) in a malformed id cannot leak into the case pattern. The structural lint harness `scripts/test-eval-set-structure.sh` gains a Check 5b mirroring the same rule via a single awk pass over `### eval-N: <id>` headings, so duplicate / path-like ids are also rejected at `make lint` time. Sibling contracts updated in lockstep per AGENTS.md: `scripts/eval-research.md` authoring section adds the id rule; `scripts/test-eval-set-structure.md` adds the 5b assertion.

## [7.4.1] - 2026-04-25

### Fixed

- `/research` Deep mode's Step 1.4 collection block now passes `--substantive-validation` to `collect-agent-results.sh`, matching Standard mode (closes #446). Previously the `### Deep (RESEARCH_SCALE=deep)` block at `skills/research/references/research-phase.md` invoked the collector without the flag while the `### Standard` block had it, so external lanes that returned thin or uncited prose received `STATUS=OK` (instead of `STATUS=NOT_SUBSTANTIVE`) and slipped silently into synthesis. The runtime-fallback prose in the same Deep block now lists `NOT_SUBSTANTIVE` alongside `STATUS != OK` as a trigger for tool-flag flipping, mirroring Standard. `scripts/test-research-structure.sh` Check 16 was tightened in the same PR: a single whole-file grep had been masking the omission because Standard's flag presence satisfied it. The check now narrows extraction to the `## 1.4 — Wait and Validate Research Outputs` window first, then runs separate awk-scoped greps for the per-scale `### Standard` and `### Deep` collection subsections (terminating at the next `^###`) so neither the Step 1.3 launch sections nor a Standard ↔ Deep substitution can satisfy the pin. Both per-section greps anchor on the literal bash-invocation prefix `${CLAUDE_PLUGIN_ROOT}/scripts/` so prose paragraphs that mention both `collect-agent-results.sh` and `--substantive-validation` on the same line cannot satisfy the assertion. The sibling contract at `scripts/test-research-structure.md` was updated in lockstep to describe the new shape of Check 16. Validation-phase.md's single (scale-agnostic) collection block keeps the whole-file pin, reusing the same invocation-anchored pattern. Closes #446.

## [7.4.0] - 2026-04-25

### Added

- `/research --plan` flag enables an optional planner pre-pass before the lane fan-out (closes #420). When `--plan` is set with `--scale=standard` (the default), a single Claude Agent subagent decomposes `RESEARCH_QUESTION` into 2–4 focused subquestions before the 3 lanes launch; each lane researches its assigned subquestion(s) (deterministic assignment by lane order: N=2 union, N=3 one-each, N=4 lane #1 gets two and lanes #2/#3 each get one); synthesis is organized by subquestion sub-section + a final `### Cross-cutting findings` sub-section. Two-step planner dance: orchestrator (`skills/research/references/research-phase.md` Step 1.1) invokes the Agent subagent (no `subagent_type`, since the `code-reviewer` archetype's dual-list output shape conflicts with the planner's prose-list output) and captures raw output to `$RESEARCH_TMPDIR/planner-raw.txt`; new helper `skills/research/scripts/run-research-planner.sh` validates count `2 ≤ N ≤ 4`, applies a question-shape heuristic (each retained line must end with `?` — fail-closed against prose preambles like "Here are the subquestions:"), strips bullet prefixes and control characters, and persists `subquestions.txt`. Falls back cleanly to single-question mode on any planner failure (count out of range, empty output, prose-only reply) with a visible `**⚠ ...**` warning. New Step 1.2 (lane-assignment) computes per-lane subquestions and persists `$RESEARCH_TMPDIR/lane-assignments.txt` (`LANE<k>_SUBQUESTIONS=<subq1>||<subq2>` lines, quoted heredoc) so Step 1.4's runtime-timeout fallback rehydrates the per-lane prompt for any replacement subagent. Per-lane suffix wraps subquestion text in `<reviewer_subquestions>` tags with a "treat as data" instruction to harden against prompt-injection (mirrors the reviewer archetype convention). `--plan` is incompatible with `--scale=quick` (single lane → no decomposition benefit) and `--scale=deep` (deep mode's 4 named angle prompts already differentiate per-lane focus; combining is documented as future work) — both incompatible combinations downgrade `--plan` to off with a visible warning at the start of Step 1. Step renumbering in `research-phase.md`: new 1.1 (planner pre-pass) and 1.2 (lane assignment) inserted before former 1.2; existing 1.2/1.3/1.4 shifted to 1.3/1.4/1.5. Cross-references in `SKILL.md` (`(phases 1.2, 1.3, 1.4)` → `(phases 1.1 through 1.5)`), `validation-phase.md` (Step 1.3 → 1.4, Step 1.4 → 1.5), and inline references updated. New `skills/research/scripts/test-run-research-planner.sh` (22-case offline regression harness wired into `make lint` via `test-harnesses` target); `SECURITY.md` updated with planner-subagent residual-risk subsection. `docs/skills.md`, `README.md`, `docs/workflow-lifecycle.md` (skill docs + flags table) updated; the same flags-table edit also adds the `--adjudicate` row that was previously missing. Closes #420.

## [7.3.4] - 2026-04-25

### Removed

- `/design` Step 3a "Post-Review Confirmation" and all machinery whose sole consumer was that gate. The conditional second approval pause (gated on `qa_happened` from a `$DESIGN_TMPDIR/user-qa-happened.md` sentinel touched by Steps 1c/1d/3.5, OR `dialectic_adjudicated` from a `grep -qE '^\*\*Disposition\*\*:[[:space:]]+(voted|fallback-to-synthesis)[[:space:]]*$'` over `dialectic-resolutions.md`) is gone — once ambiguity-resolution Q/A in Steps 1c/1d/3.5 completes, the run proceeds straight to Step 3b (Architecture Diagram). Steps 1c/1d/3.5 ambiguity-resolution Q/A is preserved unchanged. The `--auto` flag is retained because it still suppresses 1c/1d/3.5. User-visible flow change: every `auto_mode=true` exit from Step 3 ("all reviewers OK") and Step 3.5 ("skipped" or short-circuit) that previously routed to Step 3a now routes directly to Step 3b. `skills/design/SKILL.md` drops the `| 3a | confirmation |` Step Name Registry row, narrows the `--auto` flag-table description to "(1c, 1d, 3.5)", redirects both Step 3 and Step 3.5 auto-mode branches to Step 3b, and deletes the entire `## Step 3a — Post-Review Confirmation` section. `skills/design/references/discussion-rounds.md` rewrites its Consumer/Contract/When-to-load/Binding-convention header for three bodies (1c/1d/3.5), removes the `1c/1d/3.5/3a` inline literal from When-to-load, deletes all three `### Sentinel — record that Q/A occurred` subsections (1c/1d/3.5), redirects the Step 3.5 short-circuit to Step 3b, and deletes the Step 3a body section. `skills/design/references/plan-review.md` drops `3a` from Do-NOT-load and redirects both `auto_mode=true` exit branches (lines 70, 100) to Step 3b. `skills/design/references/flags.md` narrows the `--auto` description. `skills/design/references/sketch-prompts.md` and `skills/design/references/sketch-launch.md` drop `3a` from their Do-NOT-load enumerations. No script or test-harness changes (`scripts/test-design-structure.sh` does not pin Step-3a content; CI's `.github/workflows/ci.yaml` focus-area enum lives in plan-review prompts and is untouched). A follow-up issue tracks adding `test-design-structure.sh` structural pins against accidental Step 3a reintroduction (filed as #453, not blocking). Closes #439.

## [7.3.3] - 2026-04-25

### Fixed

- `/research`'s validation-phase render-failure path now rewrites `lane-status.txt` so Step 3's final report cannot show a native pass for a lane that actually ran as a Claude fallback (closes #435). Previously, when `scripts/render-reviewer-prompt.sh` exited non-zero for a Cursor or Codex validation lane, `skills/research/references/validation-phase.md`'s "On non-zero exit" handlers flipped `cursor_available` / `codex_available` to `false` and launched a Claude Code Reviewer subagent fallback, but the `VALIDATION_<TOOL>_STATUS` keys in `$RESEARCH_TMPDIR/lane-status.txt` were never rewritten — so Step 3's `VALIDATION_HEADER` could render `Cursor: ✅` / `Codex: ✅` for a lane composed entirely of Claude output. Both render-failure handlers (Cursor ~line 77, Codex ~line 121) now surgically rewrite the `VALIDATION_*` slice (token: `fallback_runtime_failed`, sanitized REASON; collapse whitespace, strip `=` and `|`, trim, truncate to 80 chars) BEFORE launching the fallback so an abort after spawn still leaves Step 3 attribution honest, using the same quoted-heredoc / `mktemp` / atomic-`mv` pattern already established at Step 2 entry and Step 2.4. Step 2.4's "no update needed" comment is clarified to enumerate the new third path producing already-correct `VALIDATION_*` keys. Sibling contracts updated in lockstep: `scripts/render-lane-status.md` Consumers + Edit-in-sync rules now enumerate the render-failure-path rewrite as a third write site; `scripts/render-reviewer-prompt.md`'s Caller pattern note documents the lane-status rewrite as the first step on the non-zero-exit branch; `skills/research/SKILL.md` Step 0b extends its lane-status write-site enumeration. `scripts/test-render-reviewer-prompt.sh` gains two structural assertions (`VALIDATION_CURSOR_STATUS=fallback_runtime_failed` and `VALIDATION_CODEX_STATUS=fallback_runtime_failed`) so a future edit cannot silently remove the rewrite blocks. No new test harness needed — `scripts/test-render-lane-status.sh` already exercises the `fallback_runtime_failed` token. Closes #435.

## [7.3.2] - 2026-04-24

### Changed

## [7.3.1] - 2026-04-25

### Fixed

- `/implement`'s tracking-issue anchor comment no longer renders as visually empty in GitHub's UI when first planted (issue #431). Previously, Step 0.5's seed body was the first-line `<!-- larch:implement-anchor v1 issue=N -->` marker plus 8 `<!-- section:slug -->`/`<!-- section-end:slug -->` pairs with empty interiors — entirely HTML comments, which GitHub renders invisible. `scripts/assemble-anchor.sh` now runs an "all-empty" pre-pass over `SECTION_MARKERS` using the lenient predicate `grep -q '[^[:space:]]'` (a fragment is "empty" iff absent OR zero-byte OR whitespace-only); when every fragment is empty, the assembled body carries one extra italic-markdown placeholder line (`_/implement run in progress — sections below populate as the run proceeds._`) between the first-line marker and the first section open marker. As soon as any fragment has non-whitespace content, the placeholder is suppressed and the populated-anchor body is byte-for-byte unchanged from pre-fix output, so progressive upserts at Steps 1/2/5/7a/8/9a.1/11 and downstream parsers (truncation, hydration awk) are unaffected. The lenient-vs-strict predicate choice was resolved via dialectic adjudication (2-1) and confirmed by user in design discussion round 2. `scripts/test-assemble-anchor.sh` extended from 10 to 14 assertion categories — (a) bumped to 18 lines with a line-2 placeholder-literal assertion, plus new `(a2)` (placeholder-presence regression for empty-sections), `(a3)` (partial-fragment suppression), `(a4)` (lenient-predicate validation against whitespace-only fragments), and `(a5)` (nonexistent `--sections-dir` still fires the placeholder). New integration assertion `(k)` in `scripts/test-tracking-issue-write.sh` pins that the placeholder line survives the `upsert-anchor` redact + truncate pipeline verbatim and on its own line (line 2 of the captured outbound body, between the first-line anchor marker and the first `<!-- section:... -->` open marker). Sibling contracts updated in lockstep: `scripts/assemble-anchor.md` ("Seed-only visible placeholder" subsection + assertion catalog refreshed), `scripts/test-assemble-anchor.md` (assertion-table additions), `scripts/test-tracking-issue-write.md` (table extended to (a)-(k)), and `skills/implement/references/anchor-comment-template.md` (new "Seed-only visible placeholder line" subsection). `skills/implement/SKILL.md` Branch 2 (~line 271) and Branch 4 step 5 (~line 371) seed-anchor prose updated to mention the placeholder. Closes #431.

## [7.3.0] - 2026-04-24

### Added

- `/research --adjudicate` boolean flag (default off) runs an additional 3-judge dialectic adjudication step (Step 2.5) over reviewer findings the orchestrator REJECTED during validation merge/dedup, with reinstated findings folded into the validated synthesis before Step 3 renders. THESIS = "rejection stands"; ANTI_THESIS = "reinstate the reviewer's finding"; majority binds; ties fall back to rejection-stands. The 3-judge panel (1 Claude code-reviewer subagent + 1 Codex + 1 Cursor) uses the dialectic-protocol.md replacement-first pattern when externals are unhealthy at fresh re-probe time. Skips the `/design`-style adversarial debate fanout — both sides exist at merge time (orchestrator rejection rationale + reviewer's original finding), so the ballot builder reads them directly. Lands as a new third reference `skills/research/references/adjudication-phase.md` (3-reference progressive-disclosure topology, replacing the prior 2-reference layout); `scripts/test-research-structure.sh` rewritten to validate 3 references with reciprocal Do-NOT-load guards across all three on the same MANDATORY line, and extended from 17 to 18 structural assertions. Capture sites A and B in `skills/research/references/validation-phase.md` persist `(finding, rejection_rationale)` records to `$RESEARCH_TMPDIR/rejected-findings.md` unconditionally regardless of the flag — tmpdir-only, wiped at Step 4 cleanup. New `scripts/run-research-adjudication.sh` (pre-launch coordinator: empty-check + ballot-build + judge re-probe in one Bash call per `skill-design-principles.md` III.B/C) and `scripts/build-research-adjudication-ballot.sh` (deterministic ballot composer: sort by `(reviewer_attribution, sha256(finding_text))`, position rotation, anchored-only attribution stripping, FS/GS sentinel encoding for multi-line + tab-safe TSV). New `scripts/test-research-adjudication.sh` offline harness with 9 assertions (deterministic ordering, DECISION renumbering, position rotation, anchored attribution stripping with mid-content preservation, `<defense_content>` wrapping, multi-line round-trip, literal-tab round-trip). `skills/shared/dialectic-protocol.md` overview annex declares the protocol now serves both `/design` Step 2a.5 (decision adjudication) and `/research --adjudicate` (rejection adjudication) with token names unchanged. `SECURITY.md` adds residual-risk note for the `<defense_content>` wrapper inheriting the same prompt-injection caveat as `/design`'s existing dialectic ballot. `docs/voting-process.md`, `skills/shared/external-reviewers.md`, `README.md`, and `docs/skills.md` updated. Composes cleanly with `--scale=quick` (Step 2 skipped → no rejections → Step 2.5 short-circuits). Closes #424.

## [7.2.1] - 2026-04-24

### Added

- Substantive-content validator for `/research` outputs (Phase 3 of umbrella #413, closes #416). New `scripts/validate-research-output.sh` is a POSIX-shell filter that exits 0 when its file argument has at least N words of body text (default `--min-words 200`, fenced-code-block interiors excluded) AND (under `--require-citations`, the default) at least one provenance marker — file or `file:line` regex with extensions `{md, sh, py, ts, js, json, yaml, yml, toml, txt, sql, go, rs}` (extended to permit leading `.` for hidden files), extensionless `Makefile`/`Dockerfile`/`GNUmakefile`, fenced code block with ≥1 non-blank line, or URL — and exits non-zero with a one-line stdout diagnostic otherwise. A new `--validation-mode` preset accepts the literal `NO_ISSUES_FOUND` token (the explicit no-findings signal emitted by `scripts/render-reviewer-prompt.sh`) and lowers the default word-count floor to 30, tuned for `/research` Step 2.4 validation-phase outputs whose shape is short numbered findings rather than 2-3 paragraph prose. `scripts/collect-agent-results.sh` gains a default-OFF `--substantive-validation` flag that, after the existing non-empty + retry path settles, invokes the validator on each `STATUS=OK` entry and rewrites the result to `STATUS=NOT_SUBSTANTIVE | HEALTHY=false | FAILURE_REASON=<sanitized diagnostic>`, calling `set_tool_unhealthy` to preserve per-tool health monotonicity. Default-OFF preserves byte-identical behavior for `/loop-review`, `/review`, `/design`, `/implement`, and any other current callers; only `/research` opts in. `/research` enables the validator at both Step 1.3 (research collection) and Step 2.4 (validation collection, with `--validation-mode`). `skills/shared/external-reviewers.md` adds `STATUS=NOT_SUBSTANTIVE` to the Runtime Timeout Fallback trigger list (same Claude-subagent-fallback behavior as a timeout) and to the documented STATUS enum. `scripts/render-lane-status.md` documents the collector STATUS-to-render-token mapping (`NOT_SUBSTANTIVE` folds into the existing `fallback_runtime_failed` token; `FAILURE_REASON` carries operator-facing distinction). New regression test `scripts/test-validate-research-output.sh` covers 24 cases (happy path, empty file, short-but-cited, long-but-uncited, adversarial zero-citations, file:line / Makefile / fenced-code / URL / leading-dot citations, fence-stripping body word count, error paths, and the seven `--validation-mode` cases including `NO_ISSUES_FOUND` short-circuit and explicit `--min-words` override). Wired into `make test-harnesses` via the new `test-validate-research-output` Makefile target; harness excluded from agent-lint as Makefile-only. `scripts/test-research-structure.sh` extended with two new structural pins (checks 16 + 17) asserting `--substantive-validation` appears in both `/research` collector invocations and `STATUS=NOT_SUBSTANTIVE` is mapped in the lane-status update bullets. Sibling contract `scripts/validate-research-output.md`. `docs/linting.md` Makefile Targets table documents the new gate. Closes #416 under umbrella #413.

## [7.2.0] - 2026-04-24

### Added

- `/research --scale=quick|standard|deep` value flag (default `standard`, byte-equivalent to pre-#418 behavior) adapts the lane count to question complexity. `quick` runs 1 inline Claude lane and skips Step 2 validation entirely (single-lane confidence — fastest, lowest assurance; the synthesis carries an explicit single-lane disclaimer). `standard` runs the existing 3 research agents + 3-reviewer validation panel. `deep` runs 5 research lanes (Claude inline running baseline `RESEARCH_PROMPT` + 2 Cursor and 2 Codex slots carrying four diversified angle prompts `RESEARCH_PROMPT_ARCH` / `RESEARCH_PROMPT_EDGE` / `RESEARCH_PROMPT_EXT` / `RESEARCH_PROMPT_SEC`) and a 5-reviewer validation panel (the standard 3 plus 2 extra Claude code-reviewer subagents `Code-Sec` / `Code-Arch` carrying lane-local emphasis on the unified Code Reviewer archetype — NOT new agent slugs; both reuse the existing `<reviewer_research_question>` / `<reviewer_research_findings>` XML wrappers as defense-in-depth against prompt injection). `skills/research/SKILL.md` adds a value-flag class distinct from boolean flags, gates Step 2 with a `RESEARCH_SCALE=quick` skip emitted before the MANDATORY directive (preserving Check 3 of `test-research-structure.sh`), makes Step 1 / Step 2 completion breadcrumbs and Step 3 report counts dynamic, and branches Step 3 header rendering per scale (standard uses `render-lane-status.sh`; quick / deep emit literal headers). `skills/research/references/research-phase.md` and `skills/research/references/validation-phase.md` gain explicit `### Standard` (byte-stable) / `### Quick` / `### Deep` subsections; `### Standard` is byte-drift-guarded by new harness assertions on the existing `cursor-research-output.txt` / `codex-research-output.txt` / `cursor-validation-output.txt` / `codex-validation-output.txt` filename literals. `scripts/test-research-structure.sh` extended from 8 to 15 assertions (the four `RESEARCH_PROMPT_*` identifiers, the literal quick-mode skip breadcrumb, abort-on-invalid `--scale=foo`, flag order-independence, and the Standard byte-drift pins). Doc sweep: README, `docs/skills.md`, `docs/agents.md`, `docs/review-agents.md`, `docs/external-reviewers.md`, `docs/workflow-lifecycle.md`, `SECURITY.md` (explicit lower-assurance note for `--scale=quick`), `skills/research/diagram.svg` (scale-aware primary box labels), and `skills/shared/progress-reporting.md` (scale-conditional table examples). Closes #418.

## [7.1.0] - 2026-04-24

### Added

- `/loop-review` overhauled with inversion-of-control: `skills/loop-review/SKILL.md` is now a thin (~80-line) delegator (`allowed-tools: Bash, Monitor`) that background-launches the new bash driver at `skills/loop-review/scripts/driver.sh` and attaches Monitor to its log file. The driver invokes `claude -p` once with a partitioning prompt to enumerate 1–20 verbal slice descriptions (replacing the prior `.claude/loop-review-partitions.json` + auto-discovery), then loops invoking `claude -p /review --slice-file <path> --create-issues --label loop-review --security-output <path>` once per slice. Each per-slice `/review` runs the standard 3-reviewer panel under the Voting Protocol; accepted findings (in-scope-accepted AND OOS-accepted, 2+ YES) are filed inline via `/issue`. Halt class eliminated by construction. `/review` gains 5 new flags: `--slice <text>` / `--slice-file <path>` (mutually exclusive; activate slice mode), `--create-issues` (post-vote inline /issue call; requires slice mode), `--label <label>` (forwarded to /issue), `--security-output <path>` (where to write security-tagged findings; defaults to `$REVIEW_TMPDIR/security-findings.md`). Slice mode emits a `### slice-result` KV footer (mirrors `### iteration-result` from `improve-skill/iteration.sh`) for driver consumption. `/review`'s default behavior (no slice flag) is unchanged. New sibling contract `skills/loop-review/scripts/driver.md`. New regression harnesses `scripts/test-loop-review-driver.sh` and `scripts/test-loop-review-skill-md.sh` with sibling `.md` contracts, modeled on the loop-improve-skill pair and wired into `make lint`. `/loop-review` reclassified ORCHESTRATOR → DELEGATOR in `scripts/test-anti-halt-banners.sh` and `skills/shared/subskill-invocation.md`. `SECURITY.md` adds `/loop-review subprocess invocation` section documenting the bash-driver topology, `LOOP_TMPDIR` security boundary, driver log file retention pattern, and `LARCH_LOOP_REVIEW_CLAUDE_OVERRIDE` test-only env var. Removed legacy `/loop-review` behaviors: sub-slicing >50 files, batched `/issue` flushes across slices, Negotiation Protocol, JSON partition config, auto-discovery — documented as intentional removals in `driver.md`. `skills/loop-review/scripts/init-session-files.sh` deleted. Docs updates to `docs/workflow-lifecycle.md` and `docs/review-agents.md`. Closes #423.

## [7.0.13] - 2026-04-24

### Added

- `/research` evaluation set + harness for measuring prompt-side improvements to `/research`. New `skills/research/references/eval-set.md` (frozen catalog of 20 questions across 5 categories — `lookup`, `architecture`, `external-comparison`, `risk-assessment`, `feasibility` — with 2 entries flagged adversarial: one fictitious-mechanism, one data-absence, to test over-claiming). New `scripts/eval-research.sh` (opt-in operator harness — runs each entry through `/research` as a fresh `claude -p --plugin-dir` subprocess matching the `iteration.sh` pattern; scores each output along deterministic axes — file:line + repo-path + URL provenance counters, case-insensitive substring keyword-coverage, length — plus a fail-closed LLM-as-judge rubric heredoc with required-field parser; `--smoke-test` for offline schema validation; `--baseline <ref>` regex-validated against shell injection). New `skills/research/references/eval-baseline.json` (committed schema-only stub; operator populates via `--write-baseline` after merge). New `scripts/test-eval-set-structure.sh` (offline structural regression — entry count, category coverage, schema validity, ≥2 adversarial entries with both fictitious and data-absence shapes, baseline JSON shape, harness self-test invocation). Both new scripts plus their sibling `.md` contracts (per AGENTS.md). `Makefile` adds `eval-research` and `test-eval-set-structure` standalone targets to `.PHONY` (NEITHER is a `test-harnesses` prerequisite — explicit "not a CI gate" carve-out, mirroring the `halt-rate-probe` pattern). `agent-lint.toml` excludes both new scripts (Makefile-only references). `docs/linting.md` documents both targets in the opt-in operator-tools table. Source: Anthropic's *How we built our multi-agent research system* — small-sample (~20-case) rubric-based LLM-as-judge evaluation as the substrate for prompt-side iteration. Closes #419 under umbrella #413.

## [7.0.12] - 2026-04-24

### Changed

- `/implement` Step 0.5 Branch 2 (`--issue` adoption, used by `/fix-issue` forwarding `--issue $ISSUE_NUMBER`), Branch 3 (PR-body recovery), and Branch 1 (sentinel-reuse resume safety net) now rename the adopted tracking issue's title to `[IN PROGRESS]` so the title-prefix lifecycle applies uniformly across fresh-created and adopted runs. Step 12a/12b (terminal `[DONE]`) and Step 18 (terminal `[STALLED]`) drop the `ADOPTED=false` guard so adopted issues also flip on completion / failure. The `ADOPTED=` sentinel field retains its created-vs-adopted metadata semantic but no longer gates the title prefix. `scripts/tracking-issue-write.md` updated to clarify the cross-skill policy (`/improve-skill` / `/loop-improve-skill` use a narrower lifecycle than `/implement`) and to extend the Step 18 summary to include Branch B (`[DONE]` on non-merge / draft completion). `skills/fix-issue/SKILL.md` Step 6a generic-failure message and a new "Title-prefix interaction on adopted-issue retry" Known Limitations entry document the manual-recovery flow — operators must clear the `[STALLED]` prefix before re-running `/fix-issue` against the same adopted issue. Closes #430.

## [7.0.11] - 2026-04-24

### Changed

- `skills/research/SKILL.md` Step 3 final-report header now distinguishes WHY each external lane fell back to a Claude subagent instead of collapsing to ✅/❌. Five canonical states render: `✅` (ran natively), `Claude-fallback (binary missing)`, `Claude-fallback (probe failed: <reason>)`, `Claude-fallback (runtime timeout)`, and `Claude-fallback (runtime failed: <reason>)`. Pre-launch state from `session-setup.sh --check-reviewers` (`*_AVAILABLE`/`*_HEALTHY`/`*_PROBE_ERROR`) and runtime state from `collect-agent-results.sh` (`STATUS`/`FAILURE_REASON`) accumulate into `$RESEARCH_TMPDIR/lane-status.txt` via surgical phase-local rewrites at Step 0b (init), Step 1.3 (research runtime), Step 2 entry (propagate research-phase fallbacks to validation lanes), and Step 2.4 (validation runtime). New `scripts/render-lane-status.sh` (with sibling `.md` contract and 10-fixture regression harness wired into `make lint`) parses the KV file at Step 3 and emits the rendered header lines; the Code (Claude code-reviewer subagent) lane is hard-coded `✅` (no fallback path). KV writes use quoted heredocs (`<<'EOF'`) to neutralize shell-injection vectors in untrusted probe-error text. `scripts/test-research-structure.sh` extended with two new structural pins (Step 3 references `render-lane-status.sh`; both phase references mention `lane-status.txt`). Closes #421.

## [7.0.10] - 2026-04-24

### Changed

- `skills/research/references/validation-phase.md`: Cursor and Codex external-reviewer lanes now render the unified Code Reviewer archetype from `skills/shared/reviewer-templates.md` via the new `scripts/render-reviewer-prompt.sh`, so all 3 lanes (Claude always-on + Cursor + Codex) walk the same five focus areas (code-quality / risk-integration / correctness / architecture / security) with XML-wrapped untrusted-context (`<reviewer_research_question>` + `<reviewer_research_findings>`) for prompt-injection hardening. Lanes use a foreground-render → background-launch pattern so render failure escalates synchronously to a Claude Code Reviewer subagent fallback (preserves the 3-lane invariant) rather than blocking on a missing `.done` sentinel. The helper applies a research-validation sentinel-override (`No in-scope issues found.` → `NO_ISSUES_FOUND`) and a section-keyed `{OUTPUT_INSTRUCTION}` expansion that instructs models to leave the OOS section empty for research validation — preserving `/research`'s negotiation-pipeline single-list contract. Adds `scripts/render-reviewer-prompt.{sh,md}` (sibling contract per AGENTS.md) and `scripts/test-render-reviewer-prompt.{sh,md}` (18 assertions: happy + 5 negative + 3 regression + 1 lane-specific integration). Updates `docs/review-agents.md` to retire the documented Codex/Cursor 4-perspectives asymmetry. Wires the new harness into `Makefile` `test-harnesses` and excludes it from `agent-lint.toml` G004/dead-script (Makefile-only invocation pattern, mirroring `test-research-structure.sh` siblings). `scripts/test-research-structure.sh` runs unchanged — Check 6 stays green via the unchanged Claude variable-binding section. Closes #417.

## [7.0.9] - 2026-04-24

### Changed

- Tighten `/research` safety claims to accurately partition mechanically-enforced (PreToolUse hook on `Edit|Write|NotebookEdit`, `/tmp`-only) vs prompt-enforced (Cursor/Codex external reviewers with `--workspace "$PWD"` / `-C "$PWD"`, Claude's own `Bash`, and Agent-tool fallbacks) perimeter. Replaces the dense "Read-only-repo contract" paragraph in `skills/research/SKILL.md` with a structured two-tier statement; promotes the externals + Bash write-surface content out of the long "External tool delegation" paragraph in `SECURITY.md` into a dedicated subsection ("External reviewer write surface in /research and /loop-review") with sub-bullets distinguishing `/research`'s hook-bounded orchestrator from `/loop-review`'s unconstrained write-capable surface; cross-links from `README.md`, `docs/review-agents.md`, `docs/external-reviewers.md`, `docs/skills.md`, and `docs/workflow-lifecycle.md` so the partition vocabulary stays consistent. Documentation-and-claims accuracy fix; no script or hook changes. Closes #422.

## [7.0.8] - 2026-04-24

### Changed

- `skills/research/references/research-phase.md`: Step 1.2 now carries an external-evidence trigger detector and a conditional `RESEARCH_PROMPT` branch (Phase 2 of umbrella #413). When `RESEARCH_QUESTION` matches a documented case-insensitive keyword list (`external`, `other repos`, `github`, `compare with`, `contrast`, `reputable sources`, `karpathy`, `anthropic`, `open source`, `oss`, `large amount of stars`, `high stars`, `star count`), `external_evidence_mode` flips to `true` and the prompt prepends an external-evidence stanza inviting `WebSearch` / `WebFetch` against reputable origins (vendor docs, well-known engineer blogs, high-star GitHub repos), with URL provenance required for every external claim. The 3-lane invariant holds at the prompt-text level; a residual asymmetry note documents that Cursor's `cursor agent` runtime does not expose web tools the way Claude does, so external-evidence yield is realized primarily through Codex + Claude-inline. SKILL.md Step 1 entry blurb updated to match. Closes #415.

## [7.0.7] - 2026-04-24

### Changed

- `skills/research/references/research-phase.md`: shared `RESEARCH_PROMPT` literal now mandates a provenance schema (Phase 1 of umbrella #413). Added clause (4) requiring every concrete claim to carry one of `file:line` / `file:line-range`, a fenced command + output snippet, or a URL; tightened the existing "Explore the codebase to ground your findings" sentence to point at clause (4). Phase 1 is schema-only — no validator change yet (Phase 3, #416). Closes #414.

## [7.0.6] - 2026-04-24

### Fixed

- `skills/fix-issue/scripts/fetch-eligible-issue.sh` explicit-issue path now emits a lock-specific error (`Issue #N is locked by another /fix-issue run (last comment: IN PROGRESS)`) when the requested issue's last comment is `IN PROGRESS`, instead of the misleading `not approved` framing. Mirrors the auto-pick path's existing `IN PROGRESS` skip; behavior is unchanged (already rejected via the GO check), only the message clarity improves. Closes #410.

## [7.0.5] - 2026-04-24

### Added

- Tracking-issue title-prefix lifecycle: `/implement`, `/improve-skill`, and `/loop-improve-skill` now create their tracking issues with `[IN PROGRESS]` in the title, rename to `[DONE]` on successful completion (right before merge for `/implement`; pre-closeout for `/loop-improve-skill`; both success exits for `/improve-skill`), and rename to `[STALLED]` on bail / failure paths. `/fix-issue` excludes issues whose titles start with any managed prefix from both auto-pick and explicit-issue selection, so tracking issues never appear as fix-issue candidates. New `tracking-issue-write.sh rename --issue N --state in-progress|done|stalled` subcommand is the single idempotent mutator (strip-exactly-one-then-prepend, redact parity with `create-issue`, char-oriented 256 truncation). Bash drivers (`iteration.sh`, `driver.sh`) install an EXIT trap with footer-first ordering so the KV footer contract is preserved even when the best-effort stall rename fails.

## [7.0.4] - 2026-04-24

### Changed

- `/issue` batch-mode `parse-input.sh` no longer emits long opaque base64-encoded `ITEM_<i>_BODY` lines on stdout — those strings were tripping Anthropic's Usage Policy classifier when the SKILL's Bash tool result entered the main agent's post-tool-use context. The script now requires `--output-dir DIR` and writes each item's body as plain text to `$OUTPUT_DIR/item-<i>-body.txt`; stdout carries `ITEM_<i>_BODY_FILE=<absolute-path>` in place of the former base64 line. No backwards-compatibility shim. Closes #402.
- `skills/issue/SKILL.md`: `$ISSUE_TMPDIR` creation moves from Step 4 to the top of Step 3 so both single and batch modes share one session tmpdir for bodies + Step 5 candidates + Step 6 OOS template wrap. Step 3 batch mode passes `--output-dir "$ISSUE_TMPDIR/bodies"` and mandatorily checks parser exit status, running `rm -rf "$ISSUE_TMPDIR"` on the abort path. Step 5 Phase 2 adds an explicit `cat "$ITEM_<i>_BODY_FILE"` preamble for non-malformed items so the LLM has body content for `<new_item_<i>>` dedup corpus. Step 6 CREATE passes `--body-file "$ITEM_<i>_BODY_FILE"` directly for generic items; OOS items `cat` the raw body file and compose the template wrap into `$ISSUE_TMPDIR/oos-body-<i>.txt`.
- `skills/issue/scripts/test-parse-input.sh`: `b64_decode` / `get_body` helpers replaced by `get_body_file_contents` (reads the file at `ITEM_<i>_BODY_FILE`); every `run_parser` call passes a per-case `--output-dir` so cases cannot stomp each other's body files. New regression guard inside `run_parser` greps stdout for `^ITEM_[0-9]+_BODY=` (extended regex) and aborts the suite on match — pins the "no base64 on stdout" invariant at the test layer. Two new negative tests: missing `--output-dir` must fail fast with usage error; unwritable `--output-dir` must fail under `set -euo pipefail`. 136/136 assertions pass.
- `skills/issue/scripts/parse-input.md`: contract doc expanded to describe file-based body emission, the required `--output-dir` flag, the non-zero-exit "ignore partial stdout" rule, and the test-layer regression guard.

## [7.0.3] - 2026-04-24

### Changed

- `/design` Step 3a — Post-Review Confirmation now fires only when `auto_mode=false` AND (`qa_happened` OR `dialectic_adjudicated`), replacing the prior `plan was revised` gate. `qa_happened` is recorded by Steps 1c/1d/3.5 via a `$DESIGN_TMPDIR/user-qa-happened.md` sentinel touched whenever an `AskUserQuestion` actually asks the user at least one question; `dialectic_adjudicated` is detected by grepping `$DESIGN_TMPDIR/dialectic-resolutions.md` for `**Disposition**: voted` or `**Disposition**: fallback-to-synthesis` lines (`bucket-skipped` / `over-cap` dispositions do not count — no adjudication occurred there). Reviewer-only plan revisions without Q/A and without dialectic no longer pause for a second approval; `/implement` proceeds straight to coding when Claude saw no ambiguity and no sketch-phase debate took place.

## [7.0.2] - 2026-04-24

### Changed

- `/loop-improve-skill` and `/improve-skill` retain `$LOOP_TMPDIR` / `$WORK_DIR` on any non-success iteration status (`no_plan`, `design_refusal`, `im_verification_failed`, `judge_failed`, subprocess exit non-zero, KV parse failure, iter-cap without grade-A reclassification) so per-iteration artifacts survive for post-mortem analysis. Cleanup still runs on `grade_a` / `ok`. The driver's close-out comment gains a `## Diagnostics` section with the retained path + a pointer list to the relevant per-iteration files, and the driver always emits `LOOP_TMPDIR=<path>` to stdout at EXIT. Closes #399.
- On any `invoke_claude_p` non-zero rc, both `driver.sh` and `iteration.sh` dump a redacted `── subprocess stderr (label=<label>) ──` banner + full stderr sidecar + last 50 lines of the subprocess stdout (tail sanitized via `sed 's/^### iteration-result/### (banner-redacted)/'` to prevent KV-footer spoofing) to stdout, so both the live Monitor stream and the retained driver log capture the verbatim error. Applied uniformly to judge / design / design-rescue / im / final re-judge subprocess sites plus helper-script failure sites (session-setup parse, standalone `gh issue create`, close-out `gh issue comment`, close-out `redact-secrets.sh`). Iteration-kernel helper-script failures signal cross-boundary retention to the driver via a `$WORK_DIR/preserve.sentinel` file that the driver's `cleanup_on_exit` reads.
- `SECURITY.md` and `skills/improve-skill/scripts/iteration.md` carve out the new post-failure diagnostic dump path in the Stdout discipline / KV-footer discipline sections.
- No `invoke_claude_p` timeout modified per user directive (judge 1200s / design 1800s / design-rescue 1800s / im 3600s / final re-judge 1200s — all ≥20 min).

## [7.0.1] - 2026-04-24

### Changed

- `/loop-improve-skill` and `/improve-skill` now print the tracking-issue URL as the final `✅` breadcrumb so the user gets a clickable link at the end of a run. `driver.sh` emits the URL after the Step 5 close-out comment; `iteration.sh` emits it from the EXIT trap in standalone mode (create OR `--issue <N>` adopt), gated on `OWNS_WORK_DIR=true` and a non-empty `ISSUE_URL`. Loop-mode invocations stay silent so `driver.sh` owns the final URL output.
- `iteration.sh` hydrates `ISSUE_URL` on the standalone `--issue <N>` adopt path via `gh issue view --json url --jq .url`. Graceful degradation: on `gh` failure `ISSUE_URL` stays empty, a warning is logged to stderr, and the EXIT trap's `-n` gate silently falls through.

## [7.0.0] - 2026-04-24

### Changed

- `/implement` Step 12 now sets `pr_closed=true` on merge success (both Step 12b `MERGE_RESULT in (merged, admin_merged)` and `ACTION=already_merged`) so final outcome state classifies externally-merged PRs as `closed` instead of `blocked`. Step 12d persists `FINAL_BAIL_REASON` into parent scope so the state machine has the bail reason available as the `--detail` tail.
- `/implement` conflict-resolution procedure Phase 2 sets `BAIL_NEEDS_USER_INPUT=true` when bailing under `auto_mode=true` due to low confidence. final state machine checks this flag (not a free-form BAIL_REASON grep) to emit the ❓ emoji.

### Removed

### Added

## [6.3.1] - 2026-04-24

### Changed

- `/fix-issue` skill-judge dimensions D1/D2/D3/D5 raised to grade A via an additive/reorganizing change. Adds a `## Mindset` section (before-processing thinking framework for triage, classification, complexity, and crash-recovery questions), a `## Anti-patterns` section (6 NEVER rules with `**Why:**` + `**How to apply:**` lines distinguishing 4 CI-backed pins enforced by `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` from 2 editorial invariants), and a new `skills/fix-issue/references/` directory with two files — `triage-classification.md` (owns the Step 4 triage + Step 5 classification detail) and `non-pr-execution.md` (owns the Step 6b NON_PR path detail). Each reference carries the CI-mandated Consumer / Contract / When-to-load header triplet with explicit `Do NOT load` guards enforced by `scripts/test-references-headers.sh`. `skills/fix-issue/SKILL.md` Steps 4, 5, and 6b are slimmed to load the references via `MANDATORY — READ ENTIRE FILE` triggers. No behavior change, no script edits. The anti-halt banner, all 3 branch-specific micro-reminders, the Step 6a bail-detection awk window's 6 literals, the Step Name Registry, Known Limitations, frontmatter, and every script contract are preserved byte-for-byte. During review, the Mindset and Step 5 "default to PR" rule was softened across both SKILL.md and the reference to add an explicit carve-out: when the issue text explicitly forbids a PR or mandates research/issues as the deliverable, pick `NON_PR` regardless — `/implement`'s `/review` phase cannot reliably recover a shape-of-work mismatch. The `triage-classification.md` Not-material-closure-flow prose was also corrected from "written into the issue body" to "posted as the closing comment on the issue" to match the actual `issue-lifecycle.sh close --comment` wiring (inherited pre-existing inaccuracy from the original SKILL.md, fixed while the prose was migrating into the reference).

## [6.3.0] - 2026-04-24

### Added

- New `/improve-skill` skill (`skills/improve-skill/SKILL.md` + `scripts/iteration.sh` + `scripts/iteration.md`) runs **one iteration** of the judge → design → im pipeline against an existing larch skill. Standalone invocation creates its own GitHub tracking issue; `--issue <N>` adopts an existing one. The amended `/design` prompt carries a **narrow per-finding pushback carve-out**: `/design` may surface disagreement with specific `/skill-judge` findings via a dedicated `## Pushback on judge findings` subsection with detailed per-finding justification (dimension + excerpt + specific reasoning + `file:line` evidence). The carve-out is strictly per-finding — the existing rules 1-3 (no-minor-self-curtail, no-budget-self-curtail, no-no-plan-sentinel) remain byte-present and in force. SKILL.md ships the same Bash + Monitor live-streaming pattern as `/loop-improve-skill` (with `IMPROVE_SKILL_LOG_FILE` env override, `/tmp/`+`/private/tmp/` validation, `run_in_background` + persistent Monitor tail with the byte-verbatim filter regex).

### Changed

- `/loop-improve-skill`'s driver (`skills/loop-improve-skill/scripts/driver.sh`) shrank from ~780 lines to ~530: the per-iteration body (judge → grade-parse → design → im → verify) was factored out into the shared kernel at `skills/improve-skill/scripts/iteration.sh`, which the driver now invokes once per round via direct bash call (not nested `claude -p`) with `--work-dir $LOOP_TMPDIR --iter-num $ITER --issue $ISSUE_NUM`. Halt class stays eliminated by construction (closes #273). Per-iteration state flows from kernel to driver via a 9-key KV footer on iteration.sh stdout (`### iteration-result` delimited; emitted via EXIT trap so the driver always sees a result even on abnormal abort; keys: `ITER_STATUS`, `EXIT_REASON`, `PARSE_STATUS`, `GRADE_A`, `NON_A_DIMS`, `TOTAL_NUM`, `TOTAL_DEN`, `ITERATION_TMPDIR`, `ISSUE_NUM`). Driver retains a slim `invoke_claude_p_final` helper for the Step 5a post-iter-cap re-judge with FINDING_7/9/10 contracts preserved. KV-parse is scoped to post-`### iteration-result`-header lines so pre-block KEY=VAL diagnostics cannot spoof the parse. `LARCH_ITERATION_SCRIPT_OVERRIDE` env var documented in SECURITY.md as test-only (never set in production).
- Propagation across canonical registries: README.md features table (new `/improve-skill` row), `docs/skills.md` TOC + section, `docs/workflow-lifecycle.md` (prose + mermaid diagram updated for the new kernel delegation topology), `docs/configuration-and-permissions.md` strict-permissions allowlist, `docs/installation-and-setup.md` shipped-skill catalog, `SECURITY.md` (new `/improve-skill` subsection + `LARCH_ITERATION_SCRIPT_OVERRIDE` test-only note), `skills/shared/subskill-invocation.md` scope lists + exemption prose, `scripts/test-anti-halt-banners.sh` DELEGATORS array, `agent-lint.toml` dead-script exclusions, Makefile `test-harnesses` aggregate + `.PHONY` line, `.claude/settings.json` allow-list (`Skill(improve-skill)` + `Skill(larch:improve-skill)`). Loop SKILL.md's "byte-identical driver" paragraph revised to describe the factored-out topology while asserting the streaming contract (background Bash + Monitor tail + filter regex + breadcrumb prefixes) is unchanged from #291.
- Two new regression harnesses: `scripts/test-improve-skill-iteration.sh` (two-tier: structural asserts on the kernel + four behavioral fixtures stubbing claude/gh for grade_a / no_plan / design_refusal / im_verification_failed cases) and `scripts/test-improve-skill-skill-md.sh` (mirrors the `/loop-improve-skill` SKILL.md harness assertions A-F against the new SKILL.md). `scripts/test-loop-improve-skill-driver.sh` updated: iteration-body tokens removed (moved to the kernel harness); delegation + KV-parse + retained-slim-helper tokens added; Tier-2 fixtures use `LARCH_ITERATION_SCRIPT_OVERRIDE` to redirect iteration invocations at a deterministic stub shim.

## [6.2.14] - 2026-04-23

### Changed

## [6.2.13] - 2026-04-23

### Changed

- Move `/implement` tracking-issue creation from Step 9a.1 to Step 0.5 Branch 4 so the tracking issue exists immediately on a fresh run. The issue body carries the original `FEATURE_DESCRIPTION` verbatim (after mandatory compose-time prompt-level sanitization — secrets / internal URLs / PII) wrapped in a blockquote for fence-injection safety. The anchor comment is now populated progressively as the run executes (`plan-goals-test` and `plan-review-tally` at Step 1, `code-review-tally` at Step 5, `diagrams` at Step 7a, `version-bump-reasoning` at Step 8, `oos-issues` + `run-statistics` at Step 9a.1, `execution-issues` at Step 11). Step 2 adds a new `Q/A` category to `execution-issues.md` with a progressive anchor upsert after each opportunistic question or mid-coding ambiguity, so Q/A appears on the issue live rather than batched until Step 11. Step 18 prints `📎 Tracking issue: <url>` at the end of the run (derived via `gh issue view --json url` so it works on GitHub Enterprise). Step 9a.1 no longer performs the first-remote-write (removed "Deferred-Creation" sub-step); it is OOS + run-stats only. Step 9a drops the `<PLACEHOLDER_TRACKING_ISSUE>` path entirely: the degraded run (create-issue failure or `repo_unavailable=true`) omits the `Closes` line and writes `_No tracking issue — auto-close N/A._` instead of a malformed `Closes #...` reference. Load-Bearing Invariant #4 text tightened: on Branch 4 first-creation, the sentinel is written ONLY after both `ISSUE_NUMBER` and `ANCHOR_COMMENT_ID` resolve to non-empty values; any create-issue or upsert-anchor failure flips to `deferred=true` and skips the sentinel. `scripts/tracking-issue-read.md`, `skills/implement/references/rebase-rebump-subprocedure.md`, `skills/implement/references/anchor-comment-template.md`, `skills/implement/references/pr-body-template.md`, `scripts/assemble-anchor.sh`, and `scripts/assemble-anchor.md` updated in sync. One follow-up OOS filed (Step 2 pre-existing ambiguity-log sanitization gap for entries that flow into the public anchor comment).

## [6.2.12] - 2026-04-23

### Changed

- Cleanup `README.md`: move full skill descriptions to a new `docs/skills.md` reference (skills table now shows command, arguments, and a one-line summary, with the command linking into the detailed doc); shorten the Features section to 1-2 line entries, each linking to the relevant in-repo doc; drop the redundant "Slash commands available in Claude Code sessions…" intro line; restructure the skills table as an HTML `<table>` with alternating Name+Arguments and full-width description rows separated by `<hr>` so argument lists no longer wrap awkwardly. Aliases table and other sections are unchanged. `scripts/test-quick-mode-docs-sync.sh` still passes (required `7 rounds`, `Cursor → Codex → Claude`, and `no voting panel` markers are retained in the `/implement` description cell).

## [6.2.11] - 2026-04-23

### Changed

- Extend `scripts/test-quick-mode-docs-sync.sh` with a target-specific cross-reference check guarding the Note A citation in `docs/review-agents.md` to `skills/shared/voting-protocol.md` (closes #377). The new `check_xref` function asserts both (a) the literal path is present in the doc (`grep -Fq`) AND (b) the path resolves to a regular file on disk (`[[ -f ]]`, directories deliberately rejected). Self-test is extended with three xref fixtures: `xref-good` (both assertions pass), `xref-bad-existence` (existence assertion only fires), and `xref-bad-grep` (grep assertion only fires) — symmetric guards so removal of either assertion is caught by exactly one bad fixture. Sibling `scripts/test-quick-mode-docs-sync.md` documents the two-assertion design, the substring-level scope limitation of assertion (a), and updated edit-in-sync rules for future rename / removal of the cited target. `docs/linting.md` row for `make test-quick-mode-docs-sync` refreshed to name the new check family.

## [6.2.10] - 2026-04-23

### Changed

- Note the `gitleaks` full-tree scan exception in the `README.md` `/relevant-checks` row (closes #378). The row previously said the checks were "scoped to files modified on the current branch," but `gitleaks` is configured with `pass_filenames: false` in `.pre-commit-config.yaml` and always scans the full working tree regardless — the consumer-surface `.claude/skills/relevant-checks/SKILL.md` already documented this exception, so the README is now aligned with it and no longer understates the `/relevant-checks` coverage.

## [6.2.9] - 2026-04-23

### Changed

- `.gitleaks.toml` path allowlist narrowed to scripts + config + tracking-issue-write contract docs (closes #375). The five high-churn documentation paths previously whole-file-exempted — `README.md`, `CHANGELOG.md`, `SECURITY.md`, `skills/issue/SKILL.md`, and `skills/issue/scripts/create-one.sh` — are now scanned by gitleaks in both pre-commit (`--no-git`) and CI (full-history) modes. Empirical finding inventory against the pinned `v8.18.4` engine reported 0 leaks across 290 commits after the narrowing, confirming the existing short-prefix mentions in those docs don't trigger default detectors; a canary synthetic `ghp_…` token in a non-allowlisted path correctly fires rule `github-pat`. `SECURITY.md` "Layered secret scanning" updated to reflect the narrower scope and the explicit gitleaks/trufflehog layer split — trufflehog `--only-verified` catches only live, authenticable credentials and is non-redundant with gitleaks for that reason, NOT a replacement for it; tokens whose format falls outside gitleaks' covered rule families may slip both Layer 1–2 and Layer 3, so contributors must not rely on scanner layers as a substitute for editorial discipline in docs. Out-of-scope files that retain whole-file allowlists — `scripts/redact-secrets.sh`, `scripts/test-redact-secrets.sh`, `scripts/tracking-issue-write.sh`, `scripts/tracking-issue-write.md`, `scripts/test-tracking-issue-write.md` — legitimately carry token-shaped strings throughout.

## [6.2.8] - 2026-04-23

### Fixed

- Align public `/implement --quick` descriptions in `README.md`, `docs/review-agents.md`, and `docs/workflow-lifecycle.md` with the current `skills/implement/SKILL.md` Step 5 contract (up to 7 rounds, per-round Cursor → Codex → Claude Code Reviewer subagent fallback chain, no voting panel). Add `scripts/test-quick-mode-docs-sync.sh` regression harness with a `--self-test` mode that proves the negative-check path fires, wired into `make lint` via the `test-harnesses` target. Closes #370.

## [6.2.7] - 2026-04-23

### Changed

- Phase 6 documentation polish (umbrella #348 closes #354): align public docs with shipped Phase 3-5 tracking-issue behavior. `README.md` adds `--issue <N>` to the `/implement` argument-hint, extends the description, adds a "Tracked runs" Features bullet, and rewrites the `/fix-issue` row to acknowledge INTENT (PR/NON_PR) classification and scope `--issue` forwarding to the PR path. `SECURITY.md` appends anchor body-level truncation posture (`BODY_CAP=60000`, `PER_SECTION_CAP=8000`, marker-preserving deterministic collapse, redaction-before-truncation) to the existing `tracking-issue-write.sh` subsection and corrects a stale "seven assertion categories" claim to nine. `docs/workflow-lifecycle.md` extends both `/implement` and `/fix-issue` bullets with Step 0.5, anchor-as-single-source-of-truth, and `--issue` forwarding semantics. `docs/review-agents.md` Output Format cross-references `workflow-lifecycle.md` for the anchor-comment routing contract. `scripts/test-tracking-issue-write.sh` header comment updated to match the sibling `.md`'s nine-category count.

## [6.2.6] - 2026-04-23

### Added

- Two-layer secret scanning: `gitleaks` as pre-commit hook (with an `entry` override to `gitleaks detect --no-git --source .` so the hook scans the working tree/staged content — upstream's default `protect --staged` scans zero commits on a clean tree) plus a dedicated CI job that installs the same pinned `v8.18.4` engine via SHA256-verified direct download and runs a full git-history scan. `trufflehog` as a CI-only job, pinned to commit SHA `1aa1871f9ae24a8c8a3a48a9345514acf42beb39` for `v3.82.13` with `version: 3.82.13` pinning the scanner Docker image and `--only-verified` for live credential verification.
- `.gitleaks.toml` path-based allowlist for files that legitimately contain token-shaped strings (test fixtures, regex-defining source, token-family documentation in release notes and security policy).
- `make gitleaks` and `make trufflehog` Makefile targets matching the existing per-hook one-liner pattern.
- `SECURITY.md` "Layered secret scanning" subsection documenting the three-layer model (Layer 1 commit-time working-tree scan, Layer 2 PR-gate git-history scan, Layer 3 PR-gate verified-only live check) and allowlist rationale. `docs/linting.md` updates gain a "CI secret scanning" subsection. `.claude/skills/relevant-checks/SKILL.md` documents the `pass_filenames: false` exception.

## [6.2.5] - 2026-04-23

### Changed

- Add `/loop-improve-skill` to the skills inventory in `docs/installation-and-setup.md` (closes #371). The skill is shipped at `skills/loop-improve-skill/` and documented in `README.md`, but was omitted from the "What the plugin provides" table when the setup docs were split out in 6fe1262.

## [6.2.4] - 2026-04-23

### Changed

- Phase 5 of umbrella #348 (closes #353): retarget the rebase-rebump sub-procedure's Version Bump Reasoning refresh from the PR body to the tracking-issue anchor's `version-bump-reasoning` section. Extract a shared anchor-body assembler (`scripts/assemble-anchor.sh` + `scripts/anchor-section-markers.sh`) so `tracking-issue-write.sh` and the assembly walk share one executable source of truth for the 8 canonical `SECTION_MARKERS`. `skills/implement/references/rebase-rebump-subprocedure.md` Step 6 now reads the tracking-issue sentinel, preserves the prior fragment on `HAS_BUMP=false` degraded paths (no placeholder overwrite), assembles via the shared helper, and upserts the anchor — with fail-soft skip semantics when the sentinel is unusable. `skills/implement/SKILL.md` routes all anchor assembly (Step 0.5 Branch 2/3 seed, Steps 1/5/7a/8/9a.1/11 progressive upserts) through the same helper. Doc sweep across `rebase-rebump-subprocedure.md`, `conflict-resolution.md`, `anchor-comment-template.md` retargets every "PR body refresh" mention. New test harnesses: `scripts/test-assemble-anchor.sh` (10 assertions — empty/partial/full fragment shapes, missing-helper fail-closed, non-directory `--sections-dir`, unreadable fragment, first-line marker, trailing-newline regression guard). `scripts/test-tracking-issue-write.sh` gains (h) missing-helper-contract + (i) `SECTION_MARKERS ⊆ COLLAPSE_PRIORITY` invariant. `scripts/test-implement-structure.sh` gains (11) sub-procedure reference set + (12) SSoT source-call invariant (now 12 structural invariants total).

## [6.2.3] - 2026-04-23

### Changed

- `/fix-issue` Step 6a now forwards `--issue $ISSUE_NUMBER` to `/implement` (both SIMPLE and HARD branches) so the child skill adopts the queue issue as its tracking issue via Phase 3 Branch 2, avoiding a duplicate tracking-issue on the `/fix-issue` path. On `IMPLEMENT_BAIL_REASON=adopted-issue-closed` (emitted when the adopted tracking issue is closed externally), Step 6a prints a specific warning and skips Step 7's `issue-lifecycle.sh close` call entirely — cleanup redirects straight to Step 9. Generic-failure path unchanged (IN PROGRESS retained as manual-intervention indicator). Phase 4 of umbrella #348 (closes #352). Adds two Known Limitations bullets (external-close recovery, token-never-seen caveat), a new offline regression harness `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` pinning six load-bearing literals inside the Step 6a block, a paired token-literal assertion in `scripts/test-implement-structure.sh` (now 10 structural invariants), and doc-only syncs in `skills/implement/SKILL.md` (line 247 parenthetical + `/fix-issue coordination` paragraph at lines 308-310) to reflect post-Phase-4 landed state.

## [6.2.2] - 2026-04-23

### Changed

- Slim `README.md` by factoring verbose reference sections into three new `docs/*.md` files — `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, `docs/linting.md`. Adds a Table of Contents at the top of `README.md` in reader-journey order, alphabetizes the Skills table by slash-command name (case-insensitive), and drops the small Review Agents block (replaced by a TOC pointer to the canonical `docs/review-agents.md`). Downstream contracts retargeted in lockstep: `AGENTS.md` canonical-sources list, `SECURITY.md` strict-permissions pointer, `Makefile` halt-rate-probe comment, `skills/create-skill/scripts/post-scaffold-hints.{sh,md}` + `skills/create-skill/SKILL.md` strict-permissions pointer, `scripts/test-loop-improve-skill-halt-rate.{sh,md}` README references. Also adds a "Migration from legacy agent slugs" section to `docs/review-agents.md` preserving the `general-reviewer` / `deep-analysis-reviewer` → `code-reviewer` guidance formerly in README.

## [6.2.1] - 2026-04-23

### Changed

- `.claude/skills/bump-version/SKILL.md` Output contract aligned with the slim PR body that Phase 3 of umbrella #348 shipped (closes #364). The section no longer claims the reasoning log is embedded into the PR body under `<details><summary>Version Bump Reasoning</summary>` — that block does not exist in the post-Phase-3 PR body template. It now states that `/implement` Step 8 reads the reasoning log as source content for the `version-bump-reasoning` anchor-section fragment, which is upserted into the tracking issue's anchor comment via `tracking-issue-write.sh upsert-anchor` and is the canonical audit surface. The `classify-bump.sh REASONING_FILE=<path>` stdout guidance is unchanged.

## [6.2.0] - 2026-04-23

### Added

- `/implement --issue <N>` flag + new Step 0.5 "Resolve Tracking Issue" with 4-branch decision tree (sentinel reuse with hydration / `--issue` explicit adoption / PR-body-recovery from `Closes #<N>` / deferred-to-Step-9a.1). Step 9a.1 creates the tracking issue on the deferred path. Phase 3 of umbrella #348 (tracks #351).
- Anchor-section accumulation: each relevant step (1 / 5 / 7a / 8 / 9a.1 / 11) writes per-step fragments to `$IMPLEMENT_TMPDIR/anchor-sections/<slug>.md` and upserts a single canonical anchor comment on the tracking issue (via `scripts/tracking-issue-write.sh upsert-anchor`) as the single source of truth for voting tallies, diagrams, version-bump reasoning, OOS list, execution issues, and run statistics.
- Load-Bearing Invariant #4 (Tracking-Issue Sentinel Idempotency) — `$IMPLEMENT_TMPDIR/parent-issue.md` is the byte-exact session-scope guard against double-creation on retry.
- `SECURITY.md` documents the anchor comment as a durable public store, compose-time sanitization obligations, public-publication boundary, `repo_unavailable=true` audit-loss, and cross-session recovery via `Closes #<N>`.

### Changed

- `skills/implement/references/pr-body-template.md`: rewritten to the slim Phase 3 projection — Summary + Architecture Diagram + Code Flow Diagram + Test plan + `Closes #<N>` + Claude Code footer only. Rich report content lives in the anchor comment per `anchor-comment-template.md`. Step 11's post-execution refresh now targets the anchor's `execution-issues` section (was the PR body's `<details><summary>Execution Issues</summary>` block).
- `skills/implement/references/anchor-comment-template.md`: active-consumer status updated; the three load-bearing marker literals (`Accepted OOS (GitHub issues filed)`, `| OOS issues filed |`, `<details><summary>Execution Issues</summary>`) are now pinned here by `scripts/test-implement-structure.sh` assertion (9a). Step 9a.1 pipeline becomes canonical here.
- `scripts/test-implement-structure.sh` + sibling `.md`: `expected_refs` extended to 5 entries (adds `anchor-comment-template.md`); MANDATORY-occurrence floor raised to 5; assertion (9a) pins the 3 marker literals in `anchor-comment-template.md` (migrated from `pr-body-template.md`); assertion (9b) pins a new ≥3 reference floor for `anchor-comment-template.md` in SKILL.md (Step 0.5 MANDATORY + Step 9a.1 + Step 11); assertion (9c) lowers `pr-body-template.md` floor to ≥1 (just the Step 9a MANDATORY pointer).
- NEVER #5 renamed from "PR-body Accepted-OOS update" to "anchor-comment Accepted-OOS update"; "How to apply" clause retargeted to the anchor's `oos-issues` / `run-statistics` sections.
- `scripts/tracking-issue-read.md` `ADOPTED=` contract gets Phase 3 producer semantics pinned: `true` on Branches 2 & 3 (explicit-flag or PR-body-recovery adoption), `false` on Branch 4's deferred creation (new issue created, not adopted).

## [6.1.12] - 2026-04-23

### Changed

- `scripts/tracking-issue-read.sh` `--sentinel` mode: pinned the `ADOPTED=` field contract (closes #359) before Phase 3 (#351) wires the sentinel as its first consumer. Allowed values are now strictly `true` or `false` when the key is present with a valid value, or empty (key absent or explicit `ADOPTED=`). Empty means "sentinel unusable" — consumers MUST NOT treat empty as equivalent to `false` and MUST fall back to their fresh-creation path. Any other non-empty value (e.g. `TRUE`, `1`, `yes`, `true` with trailing whitespace) is rejected with `FAILED=true` / `ERROR=invalid ADOPTED value in sentinel: '<val>' (expected 'true' or 'false' or absent)` and exit 1. Parser hardening added at the same time: leading UTF-8 BOM is stripped before key extraction, trailing `\r` is stripped from extracted values (CRLF tolerance), column-0 keys only (indented lines treated as absent), first-match wins on duplicate keys, and an explicit `[[ -r "$SENTINEL" ]]` readability guard emits the `FAILED=true`/`ERROR=sentinel file not readable: <path>` envelope instead of silently tripping `set -e`. Contract pinned in `scripts/tracking-issue-read.md` and a focused regression harness `scripts/test-tracking-issue-read-sentinel.sh` (15 cases, 30 assertions) wired into `make lint` via `test-harnesses` locks the behavior against drift. `agent-lint.toml` exclusion mirrors the existing `test-tracking-issue-write.sh` Phase-1 pattern.

## [6.1.11] - 2026-04-23

### Fixed

- `scripts/tracking-issue-write.sh` `truncate_body` no longer leaks its `work_dir` (from `mktemp -d`) when an `awk` call fails mid-function under `set -e` (closes #360). The function body is now a subshell (`truncate_body() ( … )`) and installs `trap "rm -rf '$work_dir'" EXIT` immediately after `mktemp -d`, so cleanup is structurally scoped to the function's own subshell and fires on every exit path — not only the trailing success-path `rm -rf` that the previous code relied on. The subshell-body form also makes the cleanup contract robust to future refactors: callers no longer have to preserve the implicit "always invoke via `$(…)`" invariant for the EXIT trap to stay scoped. The misleading header comment claiming the caller's EXIT trap covered `work_dir` transitively is rewritten to reflect the new ownership (each per-subcommand EXIT trap only names `BODY_TMP`/`ERR_TMP`/`JSON_TMP`, never `work_dir`). Pure resource-management fix — no change to stdout contract, redaction ordering, truncation algorithm, or anchor skeleton preservation; `scripts/test-tracking-issue-write.sh`'s 43 assertions pass unchanged.

## [6.1.10] - 2026-04-23

### Added

- Phase 1 of umbrella #348 (tracking-issue lifecycle) — foundation helper scripts `scripts/tracking-issue-write.sh` (three subcommands `create-issue` / `append-comment` / `upsert-anchor`; KEY=value stdout envelope with the `FAILED=true` / `ERROR=` failure namespace distinct from `/issue`'s `ISSUE_FAILED=` prefix; fail-closed redaction via `scripts/redact-secrets.sh`; structural choke point `compose → redact → truncate`; two-pass truncation preserving the anchor HTML first-line marker and all eight section-open/section-end marker pairs; strict `<!-- larch:implement-anchor v1` version matching with fail-closed on multiple-anchor comment lists) and `scripts/tracking-issue-read.sh` (pure reader with three mutually-exclusive task-source branches `--issue + --prompt` / `--issue` alone / `--prompt` or stdin, fail-closed flag-combination matrix, `--sentinel` local-markdown parse mode, strict-v1 anchor-marker and `<!-- larch:lifecycle-marker:` filters, data-not-instructions `<external_issue_body>` / `<external_issue_comment id=>` envelope for fetched GitHub content, deterministic caps `--max-body-chars` / `--max-comments` / `--max-total-chars` with integer validation at parse time, lossless JSON-per-line comment transport via `jq '... | tojson'`, local gh-stderr redaction on all ERROR= emissions). New regression harness `scripts/test-tracking-issue-write.sh` with seven assertion categories (redaction, exit-3 fail-closed on missing helper, anchor + 8-section-marker preservation under body-level collapse, per-section 8000-cap inline marker on its own line, append-comment anchor isolation, single-anchor idempotency, multiple-anchor fail-closed, gh-failure stderr redaction) wired into `make test-harnesses`. New reference file `skills/implement/references/anchor-comment-template.md` carries the canonical 8-section anchor-comment template and the three load-bearing literals (`Accepted OOS (GitHub issues filed)`, `| OOS issues filed |`, `<details><summary>Execution Issues</summary>`) that Phase 3's `test-implement-structure.sh` migration will pin. `SECURITY.md` documents the new outbound and read-path security invariants; `agent-lint.toml` excludes the helper scripts and harness until Phase 3 wires the first consumer. All new scripts are Bash 3.2-compatible. No user-visible behavior changes — scripts ship unwired. Closes #349.

## [6.1.9] - 2026-04-23

### Changed

- `skills/fix-issue/scripts/issue-lifecycle.sh` `cmd_close` is now idempotent against an already-CLOSED issue (Phase 2 of umbrella #348; closes #350). Before invoking `gh issue close`, the subcommand probes current state via `gh issue view --json state`; on `CLOSED` it skips the close call and emits `INFO: issue #N already closed; backfilling DONE metadata only` on stderr while still printing `CLOSED=true` on stdout — the DONE comment and `--pr-url` body backfill still run in both branches. On probe failure the subcommand logs `WARNING: failed to probe state for issue #N; attempting close anyway` on stderr and falls through to `gh issue close`, preserving the pre-idempotency OPEN-path reliability (transient `gh issue view` blips no longer abort a close that the write-side would have succeeded on). Additionally tightened: `cmd_close` now suppresses the internal `cmd_update_body` stdout via `>/dev/null` so `UPDATED=`/`SKIPPED=` keys never leak into `cmd_close`'s stdout, making the `CLOSED=true` contract byte-stable across open and already-closed paths. Sibling contract doc `skills/fix-issue/scripts/issue-lifecycle.md` added per AGENTS.md. Offline PATH-stub regression harness `skills/fix-issue/scripts/test-issue-lifecycle.sh` (6 fixtures) added and wired into `make test-harnesses` via the new `test-issue-lifecycle` target; `agent-lint.toml` excludes updated for the new harness and its sibling `.md`.

## [6.1.8] - 2026-04-23

### Changed

- `skills/create-skill/SKILL.md` prose compressed via Strunk & White filler removal. Two sentence-level tweaks on line 10 drop "if you want to" and sentential "it is" from the `--merge` explicit-pass note. Net saving: 19 bytes (0.11% of file); 0 line-count delta. `scripts/parse-args.md` unchanged — every paragraph is already at or below the ~10% per-paragraph compression threshold, so meaning-preservation beats marginal compression. Zero structural changes: YAML frontmatter, fenced code blocks, headings, link targets, table structure, file paths, numeric values, flag names all byte-identical.

## [6.1.7] - 2026-04-23

### Changed

- `README.md` "Setting Up Claude, Codex, Cursor, etc." section intro rewritten to state explicitly that only `claude` is mandatory; `codex` and `cursor` are optional and are substituted with Claude subagents when missing or unauthenticated (deduplicated with `Prerequisites > Optional integrations` via cross-reference rather than restating). Adds a sentence clarifying that larch is agent-agnostic about authentication — each agent can be set up with either an API key or a subscription plan via web-based login; larch only needs the binary on `PATH` and a successful authenticated session.
- `README.md` Cursor-subsection `cli-config.json` note trimmed from a multi-sentence paragraph to the single sentence "Note — larch overrides the cli-config.json model for its own Cursor invocations." The `--model` precedence, `LARCH_CURSOR_MODEL` resolution, `composer-2` default, and max-mode prompt injection details are preserved in the `Environment Variables > LARCH_CURSOR_MODEL` section rather than being duplicated in the setup recipe.

## [6.1.6] - 2026-04-23

### Changed

- `skills/implement/SKILL.md` anti-halt banner at line 12 normalized to byte-match the canonical wording in `skills/shared/subskill-invocation.md:99` (closes #346). The abbreviated form — missing the `e.g.,` prefix in the tool-list parenthetical, `The rule is` / `any` prefixes and `directive` (singular) in the subordination clause, `instruction` in the default-continuation line, `anywhere in this file` and `by this rule` in the `/relevant-checks` sentence, and `for the canonical rule` in the trailing pointer — diverged from the canonical form used by every other orchestrator (`/fix-issue`, `/review`, `/loop-review`, `/alias`, `/research`). Concurrently-maintained divergence makes single-replacement-string sweeps (like PR #347's broadening) fragile; this restores the single-source-of-truth invariant. Contract token `**Anti-halt continuation reminder.**` unchanged — `scripts/test-anti-halt-banners.sh` passes unchanged.

## [6.1.5] - 2026-04-23

### Changed

- Broadened the anti-halt continuation prohibition across 6 orchestrator SKILL.md files and `skills/shared/subskill-invocation.md` to explicitly name "summary, handoff, status recap, or 'returning to parent' message" as halts-in-disguise — not just the prior narrower "child's cleanup output" phrasing. Motivation: PR #345 exposed a halt where `/fix-issue`'s agent wrote a "Returning to /fix-issue caller" handoff message after `/implement`'s Step 18 cleanup, forcing the user to type "continue" to resume Step 7. The PR adds new post-call blockquote directives at 3 heavy-child `Skill`-tool call sites naming the concrete next parent step: `/fix-issue` Step 6a (post-`/implement` → Step 7, success-path scoped), `/implement` Step 1 normal mode (post-`/design`), `/implement` Step 5 normal mode (post-`/review`); `/alias` Step 3's existing post-call reminder is broadened to match. The canonical source `skills/shared/subskill-invocation.md` is the single source of truth; all pre-existing per-call-site micro-reminders (9 locations across 5 files) were updated to include the new broadened clause for internal consistency. Both harness contract substrings (`**Anti-halt continuation reminder.**` and `Continue after child returns`) preserved byte-exact; `scripts/test-anti-halt-banners.sh` passes unchanged.

## [6.1.4] - 2026-04-23

### Added

- `scripts/test-references-headers.sh` gained a second assertion that rejects stale `L<digits>-<digits>` line-range citations inside the `**Contract**:` paragraph of every `skills/*/references/*.md` file (closes #322). The check extends the existing triplet-header scan: for each reference file, `awk` extracts the Contract paragraph (from `^**Contract**:` to the next whitespace-only line or the next anchored `**Consumer**:` / `**When to load**:` header), and `grep -E` rejects any word-bounded `L<digits>(-|–|—)<digits>` substring. All three dash forms (ASCII hyphen, en-dash, em-dash) are matched via alternation so the check stays locale-safe under `LC_ALL=C`. The v5.2.7 refactor had already eradicated such citations from the 4 `skills/implement/references/*.md` files (replacing them with range-free descriptions in FINDING_4); this regression guard prevents reintroduction in any current or future reference file. Sibling contract `scripts/test-references-headers.md` and the script's top-of-file comment updated in sync.

## [6.1.3] - 2026-04-23

### Changed

- `README.md` Cursor setup section gained a note clarifying that larch overrides `~/.cursor/cli-config.json` `modelId` via its own `--model $MODEL` flag, where `$MODEL` resolves from `LARCH_CURSOR_MODEL` or the plugin userConfig `cursor_model` (exported to subprocesses as `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`; default `composer-2`). Users pinning a specific Cursor model for larch should set `LARCH_CURSOR_MODEL` or the `cursor_model` userConfig rather than editing the JSON file. Also notes that larch enforces max-mode at the prompt level (`scripts/cursor-wrap-prompt.sh`), so `"maxMode": true` in the JSON is not required for larch-driven calls. Closes #334.

## [6.1.2] - 2026-04-23

### Fixed

- `skills/simplify-skill/scripts/build-feature-description.sh:134-135` now strips all whitespace from `wc -l` / `wc -c` output via `tr -d '[:space:]'` instead of only ASCII spaces. BSD `wc` pads its numeric output with whitespace that is not a plain space, so the previous `tr -d ' '` left stray characters concatenated into `SKILL_MD_LINES` / `SKILL_MD_CHARS`. Identical fix to the one already applied to `skills/compress-skill/scripts/build-feature-description.sh` for issue #311. Closes #328.

## [6.1.1] - 2026-04-23

### Added

- `scripts/test-implement-structure.sh` gained a 9th assertion that pins load-bearing marker literals inside the extracted `skills/implement/references/pr-body-template.md` reference (closes #323). (9a) Three byte-pinned markers — `Accepted OOS (GitHub issues filed)`, `| OOS issues filed |`, and `<details><summary>Execution Issues</summary>` — must remain in `pr-body-template.md`; these are parsed and rewritten at runtime by the Step 9a.1 OOS issue-filing pipeline (OOS placeholder + Run Statistics OOS cell) and the Step 11 post-execution PR-body refresh (Execution Issues details block), so a silent rename or removal would break runtime behavior with no test failure. Fixed-string matching because the literals contain regex metachars (`|`, `<`, `>`). (9b) `skills/implement/SKILL.md` must reference `pr-body-template.md` at least 3 times — Step 9a MANDATORY pointer + Step 9a.1 prose binding + Step 11 prose binding — guarding against a future edit that keeps the MANDATORY pointer (which assertion (4) already pins) but orphans Step 9a.1 or Step 11 from the extracted reference. Sibling contract `scripts/test-implement-structure.md` and the script's top-of-file comment updated in sync.

## [6.1.0] - 2026-04-23

### Added

## [6.0.10] - 2026-04-23

### Changed

- `.github/workflows/ci.yaml:36` comment no longer asserts a hardcoded harness count: the literal string `the 22 test-*` was replaced with `the test-*` so the phrase reads "the `test-*` bash scripts in Makefile". The count was already stale (the target lists 25+) and would keep drifting every time a harness is added; CI still runs `make test-harnesses`, the authoritative list. Cosmetic, no behavioral effect. Closes #319.

## [6.0.9] - 2026-04-23

### Changed

- `scripts/test-review-structure.sh` hardened with three line-scoped callsite pins (closes #318), pattern parallel to `test-research-structure.sh`'s reciprocal Do-NOT-load pins. New check (5) asserts that a single `skills/review/SKILL.md` line carries (5a) `MANDATORY — READ ENTIRE FILE` + `Step 3` + `references/domain-rules.md` together (Step 3 entry callsite pin); (5b) `MANDATORY — READ ENTIRE FILE` + `round 1` (case-insensitive) + `references/voting.md` together (round-1 branch callsite pin); (5c) `Do NOT load` + `references/voting.md` together (reciprocal rounds-2+ guard). Token boundaries are non-word-char-anchored so `Step 3a` / `Step 30` / `round 10` cannot false-pass. Old assertions (5)–(8) renumbered to (6)–(9); PASS line now reports 9 invariants. Sibling contract `scripts/test-review-structure.md` updated in parallel to document the new pins and boundary rationale.

## [6.0.8] - 2026-04-23

### Fixed

- `skills/create-skill/scripts/render-skill-md.sh` scaffold bullet 6 (Anti-halt continuation reminder) in both `MULTI_STEP_BODY` and `MINIMAL_BODY` heredocs no longer enumerates a hard-coded four-name pure-delegator list. It now points at `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section "Scope list" — the single source of truth already used by `scripts/test-anti-halt-banners.sh`'s `DELEGATORS` array. Eliminates the drift surface that had left newly-scaffolded skills with an outdated checklist missing `/simplify-skill` and `/compress-skill` (closes #327).

## [6.0.7] - 2026-04-23

### Changed

- `.agnix.toml` cleared four residual CI warnings with no behavioral change to any skill (closes #317). Added `XP-SK-001` to `disabled_rules` with a comment explaining that `argument-hint` is a Claude Code-supported field and intentional across every skill here. Added a top-level `exclude` list that preserves agnix's defaults (`node_modules/**`, `.git/**`, `target/**`) and adds `tests/fixtures/**` so deliberately-skeletal halt-rate fixtures (e.g. `tests/fixtures/loop-halt-rate/SKILL.md`) no longer trigger `AS-010`. Added a `[tool_versions]` section pinning `claude_code = "2.1.0"` to satisfy `VER-001`. `AGENTS.md` tightened `contributors developing in this repo should load larch as a plugin …` to `must` to clear `PE-003` in the critical "Editing rules" section.

## [6.0.6] - 2026-04-23

### Fixed

- `.github/workflows/ci.yaml` Node.js 20 deprecation and invalid `agent-lint` input (closes #316). Bumped `actions/checkout@v4` → `@v6`, `actions/setup-python@v5` → `@v6`, and `actions/cache@v4` → `@v5` — each major publishes a Node.js 24 entrypoint (runner v2.327.1+, already on `ubuntu-latest`). Replaced the silently-ignored `args: --pedantic` on `zhupanov/agent-lint@v2.3.2` with the documented `pedantic: true` input.

## [6.0.5] - 2026-04-23

### Changed

- Cursor default model flipped from `composer-2-fast` to `composer-2` in `scripts/agent-model-args.sh`, and every substantive Cursor invocation now wraps its prompt through new `scripts/cursor-wrap-prompt.sh`, which owns the single source of truth for the ` /max-mode on. Prompt: ` prefix that engages Cursor's max-mode. 12 wrapped launch strings in 11 files were updated: `skills/{research/references/{research-phase,validation-phase}.md, design/SKILL.md, design/references/{sketch-launch (x2), dialectic-execution}.md, shared/{voting-protocol,dialectic-protocol}.md, review/SKILL.md, implement/SKILL.md, loop-review/SKILL.md}` and `scripts/run-negotiation-round.sh`. `scripts/check-reviewers.sh` health probes are deliberately NOT wrapped (max-mode is unnecessary latency/cost for a `Respond with OK` reachability check; rationale comments added at both probe sites). `scripts/run-external-agent.sh` header example now references the wrapper. `README.md` External Reviewer Model Configuration and `.claude-plugin/plugin.json` `cursor_model` description document the new default; users can opt back into the previous behavior by setting `LARCH_CURSOR_MODEL=composer-2-fast`. Preflight confirmed the prefix engages max-mode (model self-reports `MAX_MODE=on` only when the wrapper is applied).

## [6.0.4] - 2026-04-23

### Changed

- `/issue --go` now works in both single and batch modes (closes #315). `skills/issue/SKILL.md` Step 1 no longer aborts when `--input-file` and `--go` are combined; Step 6's CREATE branch posts `gh issue comment ... --body "GO"` inline after each successful create for both modes, binding the per-iteration issue number from `create-one.sh`'s `ISSUE_NUMBER=<N>` output. A new per-item stdout line `ISSUE_<i>_GO_POSTED=true|false` is emitted only on the CREATE path (never for DUPLICATE, FAILED, or DRY_RUN items). GO-post failures are non-fatal: the stderr excerpt is redacted through `scripts/redact-secrets.sh` before surfacing in a per-item warning, the item still counts as CREATED, and the batch continues. The single-mode duplicate+`--go` pre-flight is explicitly scoped to `MODE=single`. The old Step 9 (single-mode GO post) is removed; its logic is unified inside Step 6 so Step 8's human summary now accurately branches on `ISSUE_1_GO_POSTED`. `README.md` skill catalog row and `SECURITY.md` updated: a new "`/issue --go` approval semantics" subsection documents the batch-approval widening, operator guidance to restrict `--go` callers, and the fail-open-dedup amplifier (a transient dedup-helper failure combined with batch `--go` can produce a burst of newly-created AND auto-approved issues for `/fix-issue`).

## [6.0.3] - 2026-04-23

### Changed

- `docs/workflow-lifecycle.md` Delegation Topology now includes `/compress-skill` — added to the intro "pure forwarders" list, the Delegation Topology mermaid diagram as a two-hop `COMPRESS → IMAQ → IMPLEMENT` chain mirroring the `/create-skill → /im → /implement` pattern, the Topology bullet list, and the "Pure forwarders are exempt..." sentence (closes #312). `skills/shared/subskill-invocation.md` extended in parallel: both exemption paragraphs (`## Post-invocation verification`, `## Anti-halt continuation reminder`) now list `/compress-skill` alongside `/im`, `/imaq`, `/create-skill`, `/loop-improve-skill`, `/simplify-skill`; the `The banner MUST NOT appear in pure-delegator SKILL.md files:` bullet list gains `skills/compress-skill/SKILL.md`; and the Update-triggers paragraph updated from "five pure-delegator SKILL.md files" to "six". `scripts/test-anti-halt-banners.sh` `DELEGATORS` array extended with `skills/compress-skill/SKILL.md` so banner-absence is enforced for this skill; harness passes 18 checks (6 orchestrators, 6 delegators, 6 micro-reminders). Doc/test-only change; no behavioral effect on plugin surface.

## [6.0.2] - 2026-04-23

### Fixed

- `/compress-skill` temp-file leak: `skills/compress-skill/scripts/build-feature-description.sh` emits `FEATURE_FILE` (a `mktemp -t` temp file under `$TMPDIR`) on stdout and exits without cleanup — by contract the caller owns the file's lifetime. `skills/compress-skill/SKILL.md` Step 2 was reading the contents into `FEATURE_DESCRIPTION` but never removing the file, so every `/compress-skill` invocation leaked one temp file (persists across reboots on macOS `/private/tmp` when `$TMPDIR` routes there, accumulates on long-running Linux containers/VMs). Adds `rm -f "$FEATURE_FILE"` to the STATUS=ok branch of Step 2 (only on the success path — failure paths abort before the rm so we never delete a file we could not confirm reading). Documents the caller-owns-lifetime invariant in the script's in-file header and the sibling contract `build-feature-description.md` in the same PR (per AGENTS.md's stdout-contract mirror rule). Closes #310.

## [6.0.1] - 2026-04-23

### Fixed

- `skills/compress-skill/scripts/build-feature-description.sh:153-154` — replaced `tr -d ' '` with `tr -d '[:space:]'` on both the `wc -c` and `wc -l` pipelines. The space-only strip failed to remove BSD `wc` leading/padding whitespace that is not a plain ASCII space on some platforms, letting stray whitespace flow into `TOTAL_BYTES` / `TOTAL_LINES` arithmetic and table cells. Restores the safer normalization the removed `measure-set.sh` previously used. Closes #311.

## [6.0.0] - 2026-04-23

### Changed

## [5.2.9] - 2026-04-23

### Changed

- README Installation section: replaced the enumerated list of slash commands ("/design, /implement, /review, /research, ...") with the generic "all larch skills (e.g., /implement)" to reduce doc maintenance as the skill catalog evolves, and added a new `### Setting Up Claude, Codex, Cursor, etc.` subsection with per-tool API key / env-var / settings-file / install-command instructions covering Claude Code, OpenAI Codex, and Cursor. Doc-only change; no behavioral effect on plugin surface.

## [5.2.8] - 2026-04-21

### Changed

- `/implement` SKILL.md refactored via progressive disclosure and prose compression. `skills/implement/SKILL.md` shrinks from 944 to 683 lines (-261 lines, -29 KB) by (a) compressing Section-I (knowledge-delta) prose across Load-Bearing Invariants, NEVER List, Progress Reporting, Verbosity Control, Execution Issues Tracking, and the per-step narratives, and (b) extracting two workflows into the existing `skills/implement/references/pr-body-template.md`: the full Step 9a.1 OOS GitHub issue creation pipeline (repo-unavailable early-exit, 3-artifact read, all-empty early-exit, idempotency sentinel recovery, cross-phase dedup, `/issue` batch-mode invocation, stdout parsing, PR body "Accepted OOS" placeholder replacement, Run Statistics `| OOS issues filed |` cell rewrite, sentinel write) and the Step 11 post-execution PR body refresh (fetch live body, replace `<details><summary>Execution Issues</summary>` block content, update via `gh-pr-body-update.sh`). Adds Block γ (reasoning-file sentinel defense-in-depth, #160) to `skills/implement/references/bump-verification.md`, consolidating the step-3b procedure previously duplicated inline. Updates `**Contract**:` fields in all 4 reference files to drop stale `SKILL.md L<range>` citations in favor of range-free descriptions. Behavior-preserving: all flags, exit codes, stdout contracts, sentinel-file names, Step Name Registry rows, NEVER-list titles, Rebase Checkpoint Macro invocation shape + M1-M4 body + call-site registry, 3 byte-pinned ⏩ verbosity literals, and Step 5 quick-mode Cursor/Codex Bash blocks (carrying the focus-area enum + `security` on same line that CI's `agent-sync` greps for) remain byte-identical. `scripts/test-implement-structure.sh` (9 assertions) and `scripts/test-implement-rebase-macro.sh` (A-I assertions) pass unchanged.

## [5.2.7] - 2026-04-21

### Added

- `scripts/test-references-headers.sh` + sibling contract `scripts/test-references-headers.md` — cross-skill structural regression guard for the progressive-disclosure Consumer/Contract/When-to-load header triplet (closes #308). Scans every `skills/*/references/*.md` via flat glob and enforces the triplet as anchored line-start patterns (`^\*\*Consumer\*\*:`, `^\*\*Contract\*\*:`, `^\*\*When to load\*\*:`) via `grep -Eq`. Fails closed on empty glob. Path-qualified failure messages.

### Changed

- `scripts/test-implement-structure.sh` narrowed from 9 to 8 assertions: the Consumer/Contract/When-to-load triplet check (formerly assertion 8, scoped to `skills/implement/references/` only) is retired. Cross-skill ownership now lives in `scripts/test-references-headers.sh`. The `/implement`-specific topology invariants (top-level headings, MANDATORY binding, CI-parity focus-area enum, the no-`see Step N below|above` ban in `references/*.md`) remain. PASS echo updated to "all 8 structural invariants hold". Sibling contract `scripts/test-implement-structure.md` rewritten to reflect the new 8-assertion list and cite `test-references-headers.md` as the new triplet owner.
- `scripts/test-research-structure.{sh,md}` Check 4 — the `/research`-local first-20-lines tightening — now uses anchored `grep -Eq` patterns (`^\*\*Consumer\*\*:` etc.) against `head -n 20`, so it actually layers on top of the anchored cross-skill presence check instead of relying on the looser `grep -Fq` substring match. Comment block updated to describe the rule as `/research`-local tightening on top of `scripts/test-references-headers.sh`.
- Backfilled `**Contract**:` + `**When to load**:` headers on 9 reference files under `skills/design/references/` (7 files) and `skills/review/references/` (2 files) so every `skills/*/references/*.md` complies with the new cross-skill triplet contract. `plan-review.md` already had Contract so only When-to-load was added. Existing `**Binding convention**:`, `**Delivery pattern**:`, `**Effort-suffix convention**:`, and `**Substitution placeholders**:` headers preserved in place — no renames.
- `skills/design/references/dialectic-execution.md`'s new `**When to load**:` paragraph now mirrors the caller contract at `skills/design/SKILL.md` Step 2a.5: on the zero-externals guardrail path, debate-execution mechanics MUST NOT fire but a one-time load to consult the `dialectic-resolutions.md` schema is acceptable when the orchestrator does not already have the schema in context.
- `Makefile`: new `test-references-headers` target wired into `.PHONY` and the `test-harnesses` aggregate.
- `agent-lint.toml`: new exclude entry for `scripts/test-references-headers.sh` with documenting comment block; existing `test-implement-structure.sh` comment retargeted to drop the triplet-ownership claim and cite the new harness.

## [5.2.6] - 2026-04-21

### Added

- `scripts/test-review-structure.sh` + sibling contract `scripts/test-review-structure.md` — structural regression guard for `skills/review/SKILL.md` and `skills/review/references/` (closes #306). Eight assertions: SKILL.md + references dir exist; baseline refs (`domain-rules.md`, `voting.md`) exist; every `references/*.md` file on disk is named on a `MANDATORY — READ ENTIRE FILE` line in SKILL.md via a `references/<basename>` path-token form with non-filename/EOL boundary (prevents suffix/name-containing-name false-pass); baseline refs appear on a MANDATORY line (distinct diagnostic); CI-parity focus-area enum check (every `code-quality / risk-integration / correctness / architecture` line also contains `security` — mirrors agent-sync `UNQUOTED_FILES` loop); anti-halt banner and micro-reminder substrings pinned (intentional overlap with `test-anti-halt-banners.sh` for single-file fail locality); each reference opens with `**Consumer**:` and `**Binding convention**:` in the first 20 lines (the `/review` native 2-line header schema, deliberately NOT the `/implement` triplet). Wired into `Makefile` `test-harnesses` target and `agent-lint.toml` exclude list.

## [5.2.5] - 2026-04-21

### Changed

- `/research` SKILL.md refactored via progressive disclosure. `skills/research/SKILL.md` shrinks from 357 to 174 lines (-183 lines, -14.1 KB) by extracting Step 1 and Step 2 bodies into new references: `skills/research/references/research-phase.md` owns the 3-lane research invariant banner, `RESEARCH_PROMPT` literal, Cursor/Codex launch blocks with per-slot Claude subagent fallbacks, Claude inline-research independence rule, Step 1.3 `COLLECT_ARGS` / zero-externals branch / Runtime Timeout Fallback pointer, and Step 1.4 synthesis requirements. `skills/research/references/validation-phase.md` owns the 3-lane validation invariant banner, Cursor/Codex validation launches with long reviewer prompts, the Claude Code Reviewer subagent archetype with research-validation variable bindings (`{REVIEW_TARGET}` / `{CONTEXT_BLOCK}` XML wrap / `{OUTPUT_INSTRUCTION}`), process-Claude-findings-immediately rule, Step 2.4 collection / zero-externals / runtime-timeout replacement, negotiation delegation, and Finalize Validation procedure. Each reference is loaded via a single `MANDATORY — READ ENTIRE FILE` directive with reciprocal `Do NOT load` guard on the other phase's reference on the same line. Behavior-preserving: frontmatter, hooks, anti-halt banner (`**Anti-halt continuation reminder.**` + `Continue after child returns` substring), Step Name Registry, `RESEARCH_PROMPT` literal, and reviewer XML wrapper tags all preserved byte-identical and pinned by the new harness. Adds `scripts/test-research-structure.sh` (six assertions: reference files exist; each named on a `MANDATORY — READ ENTIRE FILE` line that also carries the reciprocal `Do NOT load` guard; each reference opens with the `**Consumer**:` / `**Contract**:` / `**When to load**:` header triplet in its first 20 lines; `RESEARCH_PROMPT` byte-pin; reviewer XML wrapper tags byte-pin) plus sibling contract `test-research-structure.md`. Wired into `Makefile` `test-harnesses` target and excluded from `agent-lint.toml` S030. Existing harnesses (`make test-anti-halt`, `make test-lint-skill-invocations`, `make test-deny-edit-write`, `make agent-lint`) pass unchanged.

## [5.2.4] - 2026-04-21

### Changed

- `/review` SKILL.md refactored via progressive disclosure. `skills/review/SKILL.md` shrinks from 298 to 259 lines (-39 lines, -3.8 KB) by extracting two cohesive blocks into new references: `skills/review/references/voting.md` owns the Step 3c.1 round-1 voting panel mechanics (3-voter setup, ballot file rule, threshold + competition scoring, OOS-accepted artifact write, save-not-accepted IDs) and is loaded via MANDATORY READ inside the round-1 branch with a Do-NOT-load guard for rounds 2+ and the Step 3b zero-findings short-circuit; `skills/review/references/domain-rules.md` owns the Settings.json permissions ordering and skill/script genericity rules and is loaded via MANDATORY READ at Step 3 entry unconditionally (the rules must remain visible during the zero-findings short-circuit). Behavior-preserving: all harness-asserted literals stay inline in SKILL.md byte-identical (`**Anti-halt continuation reminder.**` banner, `Continue after child returns` micro-reminder, the focus-area enum `code-quality / risk-integration / correctness / architecture / security` on both Cursor and Codex prompt lines that `.github/workflows/ci.yaml` greps for). Existing harnesses (`make test-anti-halt`, `make test-orchestrator-scope-sync`, the CI `agent-sync` job) pass unchanged.

## [5.2.3] - 2026-04-21

### Changed

- `/compress-skill` now delegates to `/imaq` so compression changes ship as a PR instead of being written to the working tree in place. `skills/compress-skill/SKILL.md` is rewritten as a thin delegator (parse args → build feature description → delegate to `/imaq`), mirroring the `/simplify-skill` pattern; the actual file-by-file prose rewrite happens inside `/implement`'s Step 2. Adds `skills/compress-skill/scripts/build-feature-description.sh` as the coordinator (resolver with four probe paths, transitive `.md` discovery via `discover-md-set.sh`, baseline byte/line snapshot, self-contained feature description embedding the Strunk & White style guide, anti-patterns, per-file judgment rules, and PR-body `## Token budget` requirement) plus its sibling contract `build-feature-description.md`. Deletes `setup.sh`, `measure-set.sh`, and `report-deltas.sh` (subsumed / no longer needed now that the delta report is produced inside the PR body). Updates `README.md` and `docs/workflow-lifecycle.md` catalog entries.

## [5.2.2] - 2026-04-21

### Changed

- Two prose paragraphs in `skills/implement/SKILL.md` compressed via Strunk & White rewrites (omit-needless-words). Affects the Cross-Skill Health Propagation trailer sentence and the `oos-accepted-main-agent.md` create-on-missing paragraph. Structure, code references, modals, and technical content preserved verbatim; -101 bytes, no line-count change.

## [5.2.1] - 2026-04-21

### Changed

- `/design` SKILL.md refactored via progressive disclosure. `skills/design/SKILL.md` shrinks from 655 to 431 lines (~34%) by: extracting the four external sketch-launch Bash blocks + spawn-order rule + per-slot fallback notes + Claude General sketch independence rule to new `skills/design/references/sketch-launch.md`; extracting the interactive-branch bodies of Steps 1c, 1d, 3.5, and 3a to new `skills/design/references/discussion-rounds.md` (loaded via MANDATORY only when `auto_mode=false`); absorbing the Step 3 Claude subagent archetype + Collecting External Reviewer Results + Voting Panel launch-order + Finalize Plan Review + Track Rejected Plan Review Findings sections into the existing `skills/design/references/plan-review.md`. Behavior-preserving: all harness-asserted literals preserved byte-identically (flag MANDATORY pointer above `## Step 0`, both Step 2a.5 Do-NOT-Load guards, Step Name Registry rows, Anti-patterns NEVER titles, `## Step 0 — Session Setup` heading, focus-area enum on SKILL.md). The two Step 3 external reviewer Bash blocks (Cursor + Codex) remain inline in SKILL.md because `.github/workflows/ci.yaml` greps them for the focus-area enum. `scripts/test-design-structure.sh` + `scripts/test-subskill-anchors.sh` pass unchanged.

## [5.2.0] - 2026-04-21

### Added

- `/compress-skill` — new skill that rewrites an existing skill's Markdown prose to reduce size while preserving meaning. Discovers the transitive `.md` set via BFS from `SKILL.md`, following both inline Markdown links and path-shaped backticked references (e.g. `` `${CLAUDE_PLUGIN_ROOT}/skills/<name>/references/foo.md` ``), restricted to the skill's own directory tree so shared docs and callee sub-skills are excluded. Applies Strunk & White's *Elements of Style* adapted for technical writing — preserves YAML frontmatter, fenced code blocks, headings, link targets, inline code, file paths, and numeric values verbatim; only prose is rewritten. Emits a per-file before/after byte and line delta report. Standalone skill — does not delegate to `/im`. Adds `skills/compress-skill/` with `SKILL.md` plus four scripts (`setup.sh`, `discover-md-set.sh`/`.py`, `measure-set.sh`, `report-deltas.sh`); wires `Skill(compress-skill)` / `Skill(larch:compress-skill)` / `Bash($PWD/skills/compress-skill/scripts/*)` into `.claude/settings.json`; updates `README.md` (installation blurb, Skills catalog row, strict-permissions example) and `docs/workflow-lifecycle.md` (Standalone Usage entry).

## [5.1.4] - 2026-04-21

### Fixed

- `/simplify-skill` resolver (`skills/simplify-skill/scripts/build-feature-description.sh`) now probes `$PWD/skills/<name>/SKILL.md` as priority 2, between the existing `${CLAUDE_PLUGIN_ROOT}/skills/` and `$PWD/.claude/skills/` probes. Previously, invoking `/simplify-skill` from inside the larch plugin repo itself (cwd is the plugin repo with a `skills/<name>/SKILL.md` layout, and `CLAUDE_PLUGIN_ROOT` unset in the helper subshell) failed with `STATUS=not_found`. The `STATUS=not_found` error message now lists all four probed paths. `skills/simplify-skill/SKILL.md` NEVER #2 prose is updated to name the three probe locations the resolver covers.

## [5.1.3] - 2026-04-21

### Changed

- `AGENTS.md` shrinks from 44k to 4.4k chars (10x reduction). Per-script and test-harness contract bullets under `## Editing rules` move verbatim to sibling `<basename>.md` files co-located with each primary script (e.g., `scripts/redact-secrets.md` beside `scripts/redact-secrets.sh`); 22 new sibling `.md` files are created under `scripts/`, `skills/issue/scripts/`, `skills/fix-issue/scripts/`, `skills/create-skill/scripts/`, and `skills/simplify-skill/scripts/`. AGENTS.md keeps only cross-cutting rules, Common editing tasks, the Canonical sources list (preserved verbatim to satisfy `scripts/test-post-scaffold-hints.sh`'s literal assertion), Conventions, plus a new co-location convention sentence under Editing rules. Canonical-.md-source bullets move into their respective canonical files as trailing "Update triggers" sections in `skills/shared/reviewer-templates.md`, `skills/shared/subskill-invocation.md`, and `skills/shared/skill-design-principles.md` — no sibling `.md` is created for an `.md` file. Stale prose pointers updated in `skills/shared/skill-design-principles.md:39` (owning-contract-doc pattern acknowledged), `skills/shared/subskill-invocation.md:191` (§ Editing rules → § Canonical sources), and 14 comment occurrences in `agent-lint.toml`. `scripts/test-implement-structure.sh` comments cite sibling `.md`. Five skill-local sibling `.md` files added to `agent-lint.toml` exclude list (S030/orphaned-skill-files).

## [5.1.2] - 2026-04-21

### Removed

- `CLAUDE.md`: delete the stale `All output caveman full.` instruction. The caveman plugin was uninstalled, so the directive no longer matches any available plugin and was incorrectly forcing caveman-style output in every session.

## [5.1.1] - 2026-04-21

### Changed

- CI split: `make lint` is now composed of two split targets, `lint-only` (pre-commit over all files) and `test-harnesses` (the 22 `test-*` bash regression harnesses). `.github/workflows/ci.yaml` replaces the single `lint` job with two parallel jobs (`lint` → `make lint-only` and `test-harnesses` → `make test-harnesses`) so harness regressions and linter regressions surface on independent job tiles and can be re-run independently. Local `make lint` behavior is unchanged.

## [5.1.0] - 2026-04-21

### Added

- `/simplify-skill <skill-name>` — new pure-delegator skill that refactors an existing larch skill for stronger adherence to `skills/shared/skill-design-principles.md` and reduced SKILL.md token footprint. Resolves the target skill directory, enumerates in-scope `.md` files (excluding `scripts/`, `tests/`, sibling sub-skills invoked via the `Skill` tool, and `skills/shared/`), and delegates a pinned behavior-preserving refactor feature description to `/im`. PR body includes a `## Token budget` section tracking SKILL.md line/char deltas.
- `skills/simplify-skill/scripts/build-feature-description.sh` — helper that validates the target name (bare form, no plugin-qualified `<a>:<b>` shape), resolves the target dir (plugin tree first, then consumer `.claude/skills/`, then `${CLAUDE_PLUGIN_ROOT}/.claude/skills/`), fail-closes on enumeration errors, and emits the full feature-description prose to a temp file. `/im` receives the prose as its `args`.

### Changed

- `scripts/test-anti-halt-banners.sh` `DELEGATORS` array + `skills/shared/subskill-invocation.md` `### Scope list` "banner MUST NOT appear" list + "Pure forwarders" parentheticals all extended with `skills/simplify-skill/SKILL.md`. Cross-validated by `scripts/test-orchestrator-scope-sync.sh`.
- `docs/workflow-lifecycle.md` Delegation Topology mermaid + bullet list + Standalone Usage bullet now document `/simplify-skill`. Exempt-list parentheticals also pick up `/loop-improve-skill` (pre-existing doc gap closed while that line was open for editing).

## [5.0.7] - 2026-04-21

### Changed

- Revert the bulk caveman-style prose compression released in 5.0.6 (restore ~50 `.md` files under `skills/`, `docs/`, `tests/fixtures/`, `.claude/skills/`, plus `AGENTS.md` and `README.md` to their pre-5.0.6 prose) and restore the stricter forms of the three accompanying harness loosenings: `scripts/lint-skill-invocations.py` again requires the canonical `Invoke the Skill tool` / `via the Skill tool` phrases (no shortened variants); `scripts/test-design-structure.sh` again requires `All 4 keys are required` with the `are` connective; `scripts/test-orchestrator-scope-sync.sh` again requires the `The` prefix on scope-list intro sentences. `agents/code-reviewer.md` is regenerated from the reverted (uncompressed) `skills/shared/reviewer-templates.md`. Additionally, the `caveman@caveman` plugin entry and the `caveman` entry in `extraKnownMarketplaces` are removed from `.claude/settings.json` (dev-only settings — no runtime surface impact).

## [5.0.6] - 2026-04-21

### Changed

- Bulk caveman-style prose compression across ~50 `.md` files under `skills/` (except `skills/implement/SKILL.md` and `skills/design/SKILL.md`, kept uncompressed for readability of the two critical orchestrator skills), `docs/`, `tests/fixtures/`, `.claude/skills/`, plus `AGENTS.md` and `README.md`. Technical content (code fences, URLs, frontmatter, file paths, quoted error strings) preserved verbatim. Accompanying harness loosenings keep CI green against the compressed forms: `scripts/lint-skill-invocations.py` accepts `Invoke Skill tool` / `Call the Skill tool` / `Call Skill tool` / `via Skill tool` variants in addition to the original canonical phrases; `scripts/test-design-structure.sh` accepts `All 4 keys required` without the `are` connective; `scripts/test-orchestrator-scope-sync.sh` accepts the scope-list intro sentences with or without the leading `The` prefix (case-insensitive `B|b`). `agents/code-reviewer.md` is regenerated from the unchanged `GENERATED_BODY` block of `skills/shared/reviewer-templates.md` (the template's surrounding prose is compressed, but the generator-extracted block is not — keeps the agent file byte-identical to generator output so the `agent-sync` CI gate stays green).

## [5.0.5] - 2026-04-21

### Changed

- `/loop-improve-skill`: stream driver output live via `Monitor` (closes #291). SKILL.md flips the synchronous foreground driver launch to `run_in_background=true` with combined stdout/stderr redirected to a stable log file under `/tmp/` (env-overridable via `LOOP_DRIVER_LOG_FILE`, validated to `/tmp/` or `/private/tmp/` prefix with `..`-component rejection), then attaches `Monitor` (`persistent: true`) tailing the file with `grep --line-buffered -E '^(✅|> **🔶|**⚠)'`. Log path is surfaced to the user via a visible `📄 Full driver log: <path>` line before Monitor attaches and re-emitted on completion, so the full unfiltered output stays accessible post-run. Path resolution uses a single synchronous Bash call emitting `RESOLVED_LOG_FILE=<path>` since Bash tool calls do not share shell state. Driver.sh is byte-identical; skill remains a pure DELEGATOR (anti-halt banner-free). Companion updates: `AGENTS.md` + `SECURITY.md` describe the new `Bash, Monitor` tool surface and log-file retention boundary (outside `LOOP_TMPDIR`, under `/tmp/` only); `scripts/test-loop-improve-skill-halt-rate.sh` extracts the driver-log path from `claude -p` stdout and reads breadcrumbs from that file via a new `extract_driver_log_path()` helper; new structural harness `scripts/test-loop-improve-skill-skill-md.sh` wired into `make lint` asserts frontmatter, visible log-path lines, the byte-verbatim filter literal, and filter/driver breadcrumb-helper parity; `agent-lint.toml` globally suppresses `tools-unknown` (S040) because agent-lint 2.3.2's registry predates the `Monitor` tool — removal trigger documented.

## [5.0.4] - 2026-04-21

### Changed

- `/create-skill`: prose-only improvement along six skill-judge dimensions of `skills/create-skill/SKILL.md`. Adds `## Design Mindset` (expert pre-scaffold prompts keyed to real forks), `## Anti-patterns` (8 NEVER bullets grounded in `/create-skill` pipeline failures), `## Decision Tables` (path mode + template + troubleshooting + skill-tool resolution), replaces the thin `## Principles` pointer with a `MANDATORY — READ ENTIRE FILE` directive plus two chronologically-ordered `Do NOT Load` branches, rewrites the frontmatter `description:` within the 250-char agent-lint cap, and trims the Step 3 `/im` feature-description template by dropping the `--plugin` enumeration block already emitted by `post-scaffold-hints.sh`. No scripts or references/ layer touched; Pattern A invocation block byte-stable (cited by `skills/shared/subskill-invocation.md`); delegator classification preserved.

## [5.0.3] - 2026-04-21

### Added

- `scripts/test-orchestrator-scope-sync.sh` — cross-validation harness that asserts exact set equality between the `ORCHESTRATORS`/`DELEGATORS` bash arrays in `scripts/test-anti-halt-banners.sh` and the bulleted scope lists under `### Scope list` in `skills/shared/subskill-invocation.md`. Fail-closed on empty parse; symmetric-diff output on drift. Wired into `make lint` via the `test-orchestrator-scope-sync` target (closes #285).

### Fixed

- `skills/shared/subskill-invocation.md`: aligned `## Post-invocation verification` pure-forwarders list (added `/loop-improve-skill`), `## Anti-halt continuation reminder` stateful-orchestrators list (added `/research`), and `## allowed-tools narrowing heuristic` hybrid-orchestrator example row (added `skills/research/SKILL.md`) with the `### Scope list` enumerations.
- `skills/create-skill/scripts/render-skill-md.sh`: added `/loop-improve-skill` to the pure-delegators exempt list in both scaffold variants (lines 157, 195).
- `AGENTS.md`: corrected the `test-anti-halt-banners.sh` orchestrator cardinality from "seven" to "six" to match the live `ORCHESTRATORS` array.

## [5.0.2] - 2026-04-21

### Changed

- `/fix-issue` Step 2 lock now deletes the `GO` comment (instead of leaving it alongside `IN PROGRESS`). `issue-lifecycle.sh comment --lock` captures the GO comment's id + `created_at`, deletes the comment via `DELETE /repos/{owner}/{repo}/issues/comments/{id}`, posts `IN PROGRESS`, and uses the captured timestamp (not a surviving GO anchor) for the concurrent-race duplicate-`IN PROGRESS` post-check. Recovery semantics updated for the crash-between-delete-and-post scenario.

## [5.0.1] - 2026-04-21

### Fixed

- `skills/loop-improve-skill/scripts/driver.sh`: derive `CLAUDE_PLUGIN_ROOT` from the script's own location when the harness did not export it, so the driver no longer aborts at Step 2 session-setup under `set -u` when invoked as a Skill (closes #288).

## [5.0.0] - 2026-04-21

### Changed

- `/loop-improve-skill` rewritten as bash-driver topology per umbrella #273. **BREAKING**: removes the inner skill `/loop-improve-skill-iter` (hard delete). Driver at `skills/loop-improve-skill/scripts/driver.sh` invokes each child skill (`/skill-judge`, `/design`, `/im`) as a fresh `claude -p` subprocess, eliminating the ~70%+ halt rate previously observed at inner Step 3.j between child-return and post-call Bash. Halt class eliminated by construction.

### Removed

- `skills/loop-improve-skill-iter/` — inner single-iteration skill superseded by bash driver (#273).
- `scripts/test-loop-improve-skill-continuation.sh` — regression harness for the split-skill topology, retired.

### Added

- `skills/loop-improve-skill/scripts/driver.sh` — bash driver owning loop control, subprocess invocation, grade parsing, audit-trail posting, infeasibility detection.
- `scripts/test-loop-improve-skill-driver.sh` — structural + behavioral regression harness for the driver, wired into `make lint` via `test-loop-improve-skill-driver` target.

### Notes

- Observability tradeoff: partial runs are no longer resumable via sentinel ledger (halt class eliminated → resume machinery unnecessary). See SECURITY.md and docs/workflow-lifecycle.md.

## [4.3.17] - 2026-04-21

### Added

- `scripts/test-loop-improve-skill-halt-rate.sh`, `scripts/lib-loop-improve-halt-ledger.sh`, `tests/fixtures/loop-halt-rate/`, plus `Makefile` `halt-rate-probe` / `test-lib-halt-ledger` targets and a README subsection — opt-in halt-rate regression harness for `/larch:loop-improve-skill` (closes #278 under halt-problem umbrella #273). Probe invokes the skill end-to-end N times against a throwaway fixture skill, parses outer's `✅ 5: close out` breadcrumb as primary classifier (filesystem sentinel forensics only for `halt_mid_turn` survivors), and emits `HALT_RATE` + `MEASURED_RUNS` + `PROBE_STATUS` + per-status + per-location breakdowns. Per-run isolation via `mktemp -d` scratch with bare-origin git provisioning and PATH-shimmed `gh`; `timeout --kill-after` wrapper handles both exit 124 and SIGKILL-escalation exit 137. Missing `claude` binary exits non-zero per #278 contract. Not wired into `make lint` (opt-in only).

## [4.3.16] - 2026-04-20

### Fixed

- `skills/loop-improve-skill-iter/SKILL.md` — Step 3.j now runs a three-state idempotency machine keyed on the on-disk ledger (State A `3j.done` non-empty skips entirely; State B armed-marker + `3j.done` absent + `$JUDGE_OUT` non-empty reuses captured judge output and runs only the post-call gh-comment + sentinel write; State C otherwise runs the full path, writing `iter-${ITER}-3j-armed.marker` in its own pre-invocation Bash block before the Skill-tool call). Previously a halt between Skill-tool return and the post-call Bash block that writes `3j.done` caused resume to re-invoke `/skill-judge` (duplicate expensive judge work + duplicate `gh issue comment`). `scripts/test-loop-improve-skill-continuation.sh` gains a line-order assertion that mechanically enforces the State C "armed marker before Skill call" invariant (needle anchored on the redirect-target shape `> "$LOOP_TMPDIR/iter-${ITER}-3j-armed.marker"`, unique to the pre-invocation printf write). `AGENTS.md` bullet enumerates the new sentinel and describes the ordering assertion. Closes #262.

## [4.3.14] - 2026-04-20

### Fixed

- `README.md` — `/loop-improve-skill` feature-matrix row loop-exit enumeration was missing the outer sentinel-gate `VERIFIED=false` halt-detected branch (handled in outer SKILL.md Step 4.v); `docs/workflow-lifecycle.md` line 41 was already complete. Appended one sentence citing `verify-skill-called.sh --sentinel-file` so the two enumerations agree. Closes #261.

## [4.3.13] - 2026-04-20

### Fixed

- `scripts/git-amend-add.sh` — header comment on line 5 carried a stale "/implement Step 8a + Rebase + Re-bump Sub-procedure step 4a" anchor pointing at the pre-extraction SKILL.md inline home. Appended the parenthetical `(skills/implement/references/rebase-rebump-subprocedure.md)` on the following line, matching the pattern used by the four headers fixed under #235. Closes #249.

## [4.3.12] - 2026-04-20

### Fixed

- `skills/loop-improve-skill/SKILL.md` — outer Step 4.v `VERIFIED=false` branch now scans `$LOOP_TMPDIR` for per-substep `.done` sentinels (`3j`, `3jv`, `3d-pre-detect`, `3d-post-detect`, `3d-plan-post`, `3i`) and emits an enriched `EXIT_REASON` with a 7-way halt-location clause pinpointing which substep the inner iteration halted at. Converts the previously-opaque "iteration sentinel missing" diagnostic into an observable halt-location surfaced in the close-out comment. The `LAST_COMPLETED=none` clause disambiguates halt-before-/skill-judge from argument-validation failure via REASON token. Harness extended to assert all 7 halt-location clauses against drift. Closes #247.

## [4.3.11] - 2026-04-20

### Fixed

- `scripts/test-implement-structure.sh` — assertion (8) previously iterated the hard-coded `expected_refs` array when checking the `**Consumer**:` / `**Contract**:` / `**When to load**:` header triplet, so a new `skills/implement/references/*.md` added without the triplet would slip through CI unvalidated. Replaced with the `shopt -s nullglob` + `"$REFS_DIR"/*.md` + basename-in-message pattern used by assertion (9), and added the parallel "no .md files found" guard. Assertion (7) (canonical four-file presence check) is unchanged. Header and block comments updated to drop the "four hard-coded" implication. Closes #252.

## [4.3.10] - 2026-04-20

### Changed

- `.claude/skills/relevant-checks/SKILL.md` — polish pass from `/loop-improve-skill` iter-3 (#245): `## Mindset` gains two additional paragraphs — a "doc DESCRIBES behavior, does NOT define policy" guardrail encoding the governing constraint explicitly, and a "Re-run after structural edits" frame capturing the full-repo-phase escalation discipline for cross-file invariants that the changed-file phase cannot detect. The third NEVER bullet's inline `(a)(b)(c)` enumeration of reduced-coverage exit-0 cases is converted to a 3-row micro-table (Case / Observable signal / Coverage implication) for triage-time scan-ability. Doc-only.

## [4.3.9] - 2026-04-20

### Fixed

- `scripts/test-implement-structure.sh` — assertion (9) regex `see Step [0-9]+[a-z.]* (below|above)` could not consume a digit after the `a.` segment, so dotted substep back-references like `see Step 9a.1 below` or `see Step 3c.2 above` evaded the guard (`/implement` already uses dotted substep numbering). Broaden the step-number token to `[0-9][0-9a-z.]*` so bare digits, letter-suffix forms, and dotted substep forms are all caught; the narrow guard (direction word required) is preserved. Closes #253.

## [4.3.8] - 2026-04-20

### Fixed

- `scripts/test-check-bump-version.sh` — Section 5 body comments cited `skills/implement/SKILL.md Rebase + Re-bump Sub-procedure step 4` (line 383 call-site example) and `SKILL.md step 4 "Pre-check STATUS guard"` (lines 430-431 test rationale), but PR #229 extracted the sub-procedure to `skills/implement/references/rebase-rebump-subprocedure.md`. Replace both with the canonical `rebase-rebump-subprocedure.md step 4` anchor. Prose-only; zero runtime behavior change. Same class of stale anchor as #235 (which targeted 4 script headers) but in a test-script body comment that was deliberately left out of #235's enumerated scope. Closes #248.

## [4.3.7] - 2026-04-20

### Changed

- `.claude/skills/relevant-checks/SKILL.md` — polish pass from `/loop-improve-skill` iter-2 (#245): frontmatter description gains `pre-commit` and `agent-lint` as explicit trigger tokens and scopes "modified files" to the pre-commit phase only; `## Mindset` gains a **Maintenance rule** paragraph covering observable banners, exit paths, `WARNING:`/`ERROR:` lines, and script comment labels / branch names (e.g., the `files[] empty but MODIFIED_FILES non-empty` branch); `## How it works` drops the inline 5-bullet linter roster (which was incomplete — missing `lint-skill-invocations` and `agent-lint`) in favour of a single pointer to `.pre-commit-config.yaml`. Doc-only; `scripts/run-checks.sh` untouched.

## [4.3.6] - 2026-04-20

### Changed

- `/loop-improve-skill` + `/loop-improve-skill-iter` — termination contract is now grade-gated: the loop strives for per-dimension grade A on every `/skill-judge` dimension D1..D8 (integer thresholds D1>=18/20, D2-D6+D8>=14/15, D7>=9/10) and exits happy when achieved. The three existing halt paths (`no_plan` / `design_refusal` / `im_verification_failed`) are now treated as infeasibility halts that MUST produce a written justification (`iter-${ITER}-infeasibility.md`); on iter-cap the outer's Step 5 runs one final `/skill-judge` for post-cap grade capture and may reclassify as a happy post-cap-A exit. The close-out tracking-issue comment becomes a multi-section body (summary + Grade History + Infeasibility Justification + Final Assessment). New shared parser `scripts/parse-skill-judge-grade.sh` (fail-closed contract: any non-ok PARSE_STATUS forces GRADE_A=false; bash 3.2 compatible) with companion 17-case harness `scripts/test-parse-skill-judge-grade.sh` wired into `make lint`. The `/design` prompt at Step 3.d now includes a Non-A dimensions focus block listing per-dim deficits when grade parsing succeeds — directly counters the historical failure mode where Non-A findings were deemed "not worth implementing". Preserves: iter cap 10, per-iter sentinel verification, security boundaries, exactly-one anti-halt banner per SKILL.md, #231 halt-detection, idempotent resume.

## [4.3.5] - 2026-04-20

### Changed

- `.claude/skills/relevant-checks/SKILL.md` — added `## Mindset` frame (phase-based changed-file vs full-repo split), `## Failure-mode taxonomy` 4-row decision table keyed to observable `run-checks.sh` banners and exit paths, and `## Anti-patterns (NEVER)` section with three bullets (no `--no-verify` bypass, deletions-only branches still run the full-repo phase, exit 0 does not guarantee every phase ran — enumerates the three reduced-coverage exit-0 outcomes). Trimmed the `/lint, /test, /format` migration note from the frontmatter description. Appended one sentence to `## How it works` naming `.pre-commit-config.yaml` as the authoritative hook catalogue. Doc-only — no changes to `scripts/run-checks.sh`. Part of the iterative `/loop-improve-skill` pass on `/relevant-checks` (closes #245).

## [4.3.4] - 2026-04-20

### Added

- `scripts/test-implement-structure.sh` — structural regression harness for `skills/implement/SKILL.md` and `skills/implement/references/` topology (closes #234). Nine assertions: three top-level headings (Load-Bearing Invariants / NEVER List / Rebase Checkpoint Macro), MANDATORY occurrence floor + per-reference filename binding, three byte-pinned verbosity literals, CI-parity focus-area enum check (mirrors `.github/workflows/ci.yaml` `agent-sync` job per-line enforcement), four expected `references/*.md` files exist, Consumer/Contract/When-to-load header triplet on every reference, and zero `see Step N below|above` patterns (case-insensitive) in any `references/*.md`. Wired into `make lint` via new `test-implement-structure` target. Companion to `scripts/test-implement-rebase-macro.sh`: macro harness owns Rebase Checkpoint Macro placement/registry; this harness owns top-level headings, MANDATORY ↔ reference binding, focus-area CI-parity, contract headers, and progressive-disclosure invariants in references/*.md.

## [4.3.3] - 2026-04-20

### Fixed

- `scripts/lib-count-commits.sh`, `scripts/check-bump-version.sh`, `scripts/git-force-push.sh`, `scripts/git-sync-local-main.sh` — header comments cited `skills/implement/SKILL.md` as the inline home of the Rebase + Re-bump Sub-procedure, but PR #229 extracted it to `skills/implement/references/rebase-rebump-subprocedure.md`. Append the reference-file path as a parenthetical anchor adjacent to each existing step-number citation (preserving step numbers 3/4/5 which map 1:1 to the extracted file's numbering). Prose-only; zero runtime behavior change. Also makes `check-bump-version.sh`'s header carry an explicit `step 4` anchor so it matches the `step N (path)` pattern of the other three headers (plan-review FINDING_2, 2 YES / 1 NO). Closes #235.

## [4.3.1] - 2026-04-20

### Fixed

- `.claude/skills/bump-version/scripts/classify-bump.sh` — fix silent SIGPIPE 141 abort on large SKILL.md files. The `extract_frontmatter` awk function exits after matching the closing `---` frontmatter delimiter; `printf '%s\n' "$FILE" | extract_frontmatter` then receives SIGPIPE while still writing hundreds of KB on large files. Under `set -euo pipefail` the pipefail-propagated 141 silently aborted the whole script with no stdout and no stderr, causing `/implement` Step 8 to misclassify the bump. Replaces the pipe with a herestring (`extract_frontmatter <<< "$FILE"`) so awk reads from stdin without an intermediate writer that can be SIGPIPE-killed; awk function body unchanged. The four subsequent `printf | awk` extractions for `OLD_NAME`/`NEW_NAME`/`OLD_ARG_HINT`/`NEW_ARG_HINT` operate on already-extracted small frontmatter blocks (well under the 64KB pipe buffer) and do not trigger the bug — left as-is. Closes #240.

## [4.3.0] - 2026-04-20

### Added

- `/loop-improve-skill-iter` — new inner skill that runs exactly one `/skill-judge` → `/design` → `/im` iteration for a target skill. Writes a per-substep `.done` sentinel ledger under a caller-supplied `LOOP_TMPDIR` (validated as under `/tmp/` or `/private/tmp/` with `..` rejection) and emits `ITER_STATUS=<value>` plus a non-empty completion sentinel. Invoked only by `/loop-improve-skill` via the Skill tool — not a standalone user-facing skill.

### Changed

- `/loop-improve-skill` — refactored into an outer loop controller that delegates each of up to 10 improvement rounds to `/loop-improve-skill-iter`. After each inner return, a mechanical `scripts/verify-skill-called.sh --sentinel-file` gate reads the inner's non-empty completion sentinel. This converts the old "parent halted after child returned" failure mode (issue #231) into an observable missing-sentinel diagnostic with a specific `EXIT_REASON`. New `scripts/test-loop-improve-skill-continuation.sh` structural lint (wired into `make lint`) asserts the split's gate + sentinel literals + banner-density cap in both SKILL.md files. `scripts/test-anti-halt-banners.sh` ORCHESTRATORS array and `skills/shared/subskill-invocation.md` Scope list updated with the new inner skill (D3-honoring Scope-list catalog sync — no new normative prose). Companion updates: `LARCH_RESERVED` in validate-args.sh, `.claude/settings.json` Skill permissions, README Skills catalog + strict-permissions snippet, `docs/workflow-lifecycle.md` topology, `AGENTS.md` canonical-source bullet, `agent-lint.toml` exclude. Closes #231.

## [4.2.14] - 2026-04-20

### Added

- `scripts/test-subskill-anchors.sh` — regression harness that verifies every backticked `` `<path>/SKILL.md § <heading>` `` citation in `skills/shared/subskill-invocation.md` resolves to a `## <heading>` or `### <heading>` line in the referenced file (exact string match via `grep -Fxq`, both `##` and `###` accepted, trailing whitespace tolerated on target lines). Fail-closed on parse/IO errors; fence-aware parser skips any 3+ backtick opener (including the doc's quadruple-backtick banner examples); minimum-citation floor of 10 guards against extractor regressions. Wired into `make lint` via a new `test-subskill-anchors` target; added to `agent-lint.toml` exclude list. Contract orthogonal to `scripts/lint-skill-invocations.py` (which enforces invocation wording). Also fixes 3 pre-existing citation drifts (`Step 6 — Implement` → `Step 6 — Execute`; `Step 9a.1 — Create OOS GitHub Issues` → `9a.1 — Create OOS GitHub Issues`; `Step 0` → `Step 0 — Session Setup`) and expands 2 continuation-shorthand citations to full-path form so all 14 citations resolve mechanically. Closes #236 (follow-up from #227 / PR #229).

## [4.2.13] - 2026-04-20

### Changed

- `/implement` — add `### Follow-up Work Principle` subsection at the top of `## Execution Issues Tracking` generalizing the rule: durable, actionable follow-up work identified during design, implementation, or review MUST be tracked as a GitHub issue (auto-filed via Step 9a.1 when the item fits the OOS pipeline, or manually via `/issue` otherwise) and the PR body references that issue — not buried as prose alone. Retitle the existing `Mandatory dual-write` subsection as `Mechanical enforcement of the principle: Pre-existing Code Issues dual-write` (schema, dedup rule, sanitize rule, worked example byte-identical); update two in-file cross-references to the new title. Add one reminder line pointing back to the principle inside the Implementation Deviations PR-body block (the three carve-out-covered blocks — Rejected Plan Review Suggestions, Rejected Code Review Suggestions, Non-accepted OOS observations — explicitly exclude the reminder to respect the voting panel's rejection decisions). Explicit carve-outs for non-accepted/rejected findings staying as PR-narrative, `repo_unavailable=true` as blocked-filing state for both auto and manual paths, and security findings routed exclusively through SECURITY.md's private disclosure flow. `skills/shared/voting-protocol.md:217` reframed to call the main-agent dual-write path the mechanical enforcement of the principle for the `Pre-existing Code Issues` category; trigger scope preserved (no mechanical extension). Closes #237.

## [4.2.12] - 2026-04-20

### Changed

- `/implement` — dedup 4 near-identical rebase-checkpoint blocks at Steps 1.r, 4.r, 7.r, 7a.r (~60 lines of duplication) into a single `## Rebase Checkpoint Macro` section parameterized on `<step-prefix>` and `<short-name>`. Each former block is now a single-line `Apply the Rebase Checkpoint Macro with ...` invocation. Preserves: uniform `debug_mode` gate at all 4 sites, three byte-pinned Verbosity Control literals, Step 7.r `FILES_CHANGED=true` guard at its call site, and byte-identical breadcrumb output (🔃 start, ⏩ debug, ✅ success). Macro procedure steps labeled M1-M4 to avoid collision with outer Step 0-18 numbering. New `scripts/test-implement-rebase-macro.sh` (wired into `make lint`) asserts 9 structural invariants (A-I) guarding the macro section, the 4 call-site registry rows, the 4 Apply invocations, the Verbosity Control literals, the Step 7.r guard placement, the macro placement between Verbosity Control and Step 0, the macro body's rebase-push invocation + bail string, the total rebase-push call-site counts (1 `--no-push --skip-if-pushed` + 2 plain `--no-push`), and the macro body's placeholder-pinned SKIPPED format strings. Closes #232 (follow-up to #227 / PR #229 FINDING_1).

## [4.2.11] - 2026-04-20

### Changed

## [4.2.10] - 2026-04-20

### Changed

- `/design` — strengthen `description:` frontmatter with additional trigger keywords (design, architecture planning, scope definition, approach validation) while preserving the "Use when..." trigger pattern required by agent-lint S017 and staying within the 250-character S015 cap. Closes the D4 Specification-Compliance nit from iteration-2 `/skill-judge` review (follow-up to PR #228; tracking issue #224). No runtime behavior change.

## [4.2.9] - 2026-04-20

### Changed

- `/design` — refactor SKILL.md per `/skill-judge` findings (Grade C → expected B). Three orthogonal edits: add a `## Design Mindset` section near the top transferring the orchestrator's thinking pattern via 5 "Before X, ask yourself" prompts; replace the 5 flag-description paragraphs with a compact 4-column table followed by a `MANDATORY` pointer to the new `skills/design/references/flags.md` (declared the single normative source), placed adjacent to the flag block before Step 0 so it is read before flag parsing begins; hybrid-extract Step 2a.5 — keep inline the GH#98 debate-phase carve-out, bucket assignment, and zero-externals guardrail while extracting per-decision rendering, parallel launch, collection, judge re-probe, ballot construction, judge launch, tally, and `dialectic-resolutions.md` writing to the new `skills/design/references/dialectic-execution.md`. Dual `Do NOT load` guards prevent debate-instruction leakage on the `NO_CONTESTED_DECISIONS` and zero-externals short-circuit paths. New `scripts/test-design-structure.sh` (wired into `make lint` via `test-design-structure`) asserts the four structural invariants: flag-MANDATORY placement before Step 0, dual skip-branch guards, `dialectic-execution.md` header MANDATORY naming `dialectic-debate.md`, and `references/flags.md` load-bearing literals (`--branch-info` 4-key rule + `--step-prefix` `::` delimiter). Updates `references/dialectic-debate.md` example line-refs from `SKILL.md:340` to `SKILL.md:1` (stable file-level pointer after refactor line drift).

## [4.2.8] - 2026-04-20

### Changed

- README.md — append a parenthetical pointer to `skills/shared/skill-design-principles.md` on the `/create-skill` catalog row so consumers reading the Skills feature matrix have a discovery path to the canonical skill-design principles doc. Closes #217.

## [4.2.7] - 2026-04-20

### Changed

- `/research` — relax the always-deny `scripts/deny-edit-write.sh` PreToolUse hook to a `/tmp`-only allow policy so `/research` may write scratch artifacts via `Write`/`Edit`/`NotebookEdit` and invoke `/issue` via the Skill tool (e.g., to file research-result issues). `allowed-tools` now lists `Skill, Write, Edit, NotebookEdit`; the hook is the sole mechanical enforcer of the `/tmp`-only confinement (residual risk if hook `permissionDecision` semantics vary by Claude Code version — see `SECURITY.md`). Hook mirrors `scripts/block-submodule-edit.sh`'s stdin-JSON / bounded-symlink-walk / `pwd -P` / jq-absent-printf-fallback discipline and handles macOS `/tmp` → `/private/tmp` aliasing; extraction uses a length-aware `map(select(type == "string" and length > 0))` selector so an empty `file_path` does not shadow a valid `notebook_path`. `/research` is registered as an orchestrator in `scripts/test-anti-halt-banners.sh` (banner + per-site micro-reminder). Updated `SECURITY.md`, `AGENTS.md`, `README.md`, `docs/workflow-lifecycle.md`. Test harness rewritten to a 13-case table-driven matrix (repo-deny, `/tmp` allow for new and existing files, traversal-deny, relative-deny, `notebook_path` allow/deny, empty-`file_path`-with-valid-`notebook_path` allow, fail-closed empty-path deny, malformed-JSON deny, idempotency, jq-absent byte-identity). Closes #215.

## [4.2.6] - 2026-04-20

### Changed

- `skills/create-skill/scripts/render-skill-md.sh` — emit a single-line pointer to `${CLAUDE_PLUGIN_ROOT}/skills/shared/skill-design-principles.md` at the top of both scaffold body variants (multi-step and minimal), right after the opening TODO HTML comment, so scaffold authors encounter the canonical principles doc at creation time. `skills/create-skill/scripts/test-render-skill-md.sh` — add contract assertion (7) guarding regression and reusing the empty-plugin-token rooted-path guard. Closes #216.

## [4.2.5] - 2026-04-20

### Fixed

- `/loop-improve-skill` — prevent silent exit after iteration 1 on minor `/skill-judge` findings or self-judged token/context budget pressure (closes #214). Expanded top banner with an **Anti-self-curtailment** clause enumerating the four authoritative exits. Strengthened Step 3.d's `/design` prompt with three contract clauses requiring a plan for minor/nit findings, forbidding budget-based self-curtailment, and forbidding no-plan sentinels when findings exist. Tightened the no-plan sentinel detector so a first-line sentinel match is terminal only when no structured plan marker (`^#{1,6}\s`, `^[1-9]\d?\.\s`, `^[-*+]\s`) follows — the 5 sentinel strings remain byte-identical. Added a one-shot rescue re-invocation of `/design --auto` when the first response is non-empty, non-sentinel, non-refusal prose with no plan shape; replacement semantics ensure at most one plan comment per iteration. Added explicit Step 3.d ordering invariant and a dedicated `EXIT_REASON` for the `/design` refusal/error exit.

## [4.2.4] - 2026-04-20

### Changed

- `/create-skill` — factor the inline `## Principles` section into a new canonical doc at `skills/shared/skill-design-principles.md` (~120 lines, 9 sections) merging the battle-tested larch A/B/C mechanical rules with higher-level principles extrapolated from the `skill-judge` and `skill-creator` plugins (knowledge delta, progressive disclosure, anti-patterns with WHY, description-as-activation-surface, freedom calibration, pattern recognition, verifiable quality criteria). The new doc declares Section III (larch mechanical rules) overrides Section IV (general writing-style guidance) to resolve the collision between `skill-creator`'s "avoid rigid MUSTs" advice and larch's harness-enforced A/B/C invariants.
- `skills/create-skill/SKILL.md` — body `## Principles` shrinks to a pointer paragraph (heading preserved for grep friendliness); Step 3 `/im` feature-description template keeps the compact A/B/C one-liners (HYBRID resolution from dialectic — mechanical invariants survive context pressure) AND adds an explicit `MUST read skills/shared/skill-design-principles.md (full file) before writing any code` line; replaces the stale `sourced from /create-skill's ## Principles section` attribution with the full `${CLAUDE_PLUGIN_ROOT}` path to the new doc.
- `AGENTS.md` — add an Editing-rules bullet for `skills/shared/skill-design-principles.md` (scope, precedence, consumers, update trigger — Section III edits must mirror the Step 3 compact A/B/C excerpt in the same PR) and a Canonical-sources bullet. Generator path (`render-skill-md.sh`, `post-scaffold-hints.sh`) and README deliberately untouched — scaffold-pointer and README-link deferred to follow-up issues per dialectic DECISION_2. Closes #206.

## [4.2.3] - 2026-04-20

### Changed

- `/alias` reclassified from pure delegator to hybrid orchestrator: validates, delegates to `/implement`, then performs a mechanical sentinel-file verification (new Step 4 via `scripts/verify-skill-called.sh --sentinel-file`) that `.claude/skills/<alias-name>/SKILL.md` was actually written. `skills/alias/SKILL.md` Step 2.2 replaces the static 12-name reserved list with a dynamic two-root `test -d` probe against `${CLAUDE_PLUGIN_ROOT}/skills/<n>` and `${CLAUDE_PLUGIN_ROOT}/.claude/skills/<n>` (fail-closed on unset `CLAUDE_PLUGIN_ROOT`), eliminating drift when new skills ship. Step 3 replaces the "research the codebase and discover `generate-alias.sh`" hand-wave with an explicit generator contract naming the script path, its four required flags (`--name`, `--target`, `--flags`, `--version`), the pinned version source (`jq -r .version ${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`), and the write target. Adds the canonical anti-halt banner + micro-reminder required of orchestrators. Step 4 emits branched fail-closed error text for the `--merge` vs non-`--merge` paths.
- `scripts/test-anti-halt-banners.sh` — move `skills/alias/SKILL.md` from `DELEGATORS` to `ORCHESTRATORS` to reflect the reclassification.
- `skills/shared/subskill-invocation.md` — remove `/alias` from pure-delegator lists (Pattern A example citation, allowed-tools tier, Post-invocation verification scope, Anti-halt scope, Scope list); add to orchestrator/hybrid category with sentinel-file verification as the concrete mechanical check.
- `skills/create-skill/scripts/render-skill-md.sh` — drop `/alias` from the two scaffold-emitted pure-delegator exemption checklists so newly scaffolded skills see accurate reminders.
- `skills/create-skill/scripts/validate-args.sh` — update the stale "mirrors skills/alias/SKILL.md Step 2" comment to describe the actual relationship (static pre-check before the dynamic plugin-skills probe); add `loop-improve-skill` to the static `LARCH_RESERVED` list; update the header comment's reserved-name enumeration.
- `docs/workflow-lifecycle.md` — update the Skill Orchestration Hierarchy intro, Delegation Topology prose, `/alias` bullet, and post-invocation-verification exemption paragraph to reflect `/alias`'s hybrid classification.
- `AGENTS.md` — update the `scripts/test-anti-halt-banners.sh` bullet counts (four→six orchestrators, four→three delegators) and note `/alias`'s reclassification rationale.

## [4.2.2] - 2026-04-20

### Changed

- `/design` — refactor for progressive disclosure: extract the 4 personality prompts (`ARCH_PROMPT`/`EDGE_PROMPT`/`INNOVATION_PROMPT`/`PRAGMATIC_PROMPT`) into `skills/design/references/sketch-prompts.md`, the Thesis/Antithesis debate templates into `skills/design/references/dialectic-debate.md`, and the Competition notice + voter prompts + ballot handling + FINDING_N/OOS/rejected-findings format blocks into `skills/design/references/plan-review.md`. Each reference file is loaded via a MANDATORY directive at the correct call site (Step 2a.2 for sketch prompts, between Step 2a.5 steps 5-6 for debate templates, top of Step 3 for plan-review artifacts). Reviewer launch shell blocks and numeric invariants remain inline in SKILL.md to preserve the CI agent-sync focus-area-enum check and `timeout: 1860000`/`--write-health "${SESSION_ENV_PATH}.health"` contracts. Byte-preserved all relocated prompt bodies, template bodies, and shell commands — zero behavioral change.
- `/design` — add consolidated `## Anti-patterns` section after Verbosity Control with 6 NEVER rules (skip Step 2a; substitute Claude into dialectic debate bucket; mutate orchestrator-wide `codex_available`/`cursor_available` inside Step 2a.5; pass `--caller-env`/`--write-health` to `session-setup.sh` when `SESSION_ENV_PATH` empty; call `collect-agent-results.sh` with zero positional args; conflate the sketch-phase vs. plan-review+dialectic timeout families). Each rule states the WHY so edits can respect the original constraint; inline step-local mentions remain where they carry load-bearing context.
- `/design` — strengthen frontmatter description with explicit "Use when..." trigger phrasing + 5-sketch + voting-panel keywords (within the 250-character agent-lint limit).

## [4.2.1] - 2026-04-20

### Changed

- `/create-skill` — delegate via `/im` instead of `/implement` so scaffold PRs auto-merge by default. `--merge` on `/create-skill` is now a backward-compat no-op (the flag still parses; the behavior change is in the default path). Switched the Skill tool call from `"implement"` / `"larch:implement"` to `"im"` / `"larch:im"`.
- `/create-skill` — add a `## Principles` section (A: express logic as bash scripts with shared/private reuse; B: no direct Bash commands — wrap in scripts; C: no consecutive Bash tool calls — combine via coordinator script). Principles are forwarded verbatim into the feature description handed to `/im` so they propagate to the implementing agent. Not mechanically enforced.
- `skills/create-skill/scripts/post-scaffold-hints.sh` — emit an expanded doc-sync reminder set for plugin-dev scaffolds: `docs/workflow-lifecycle.md` orchestration-hierarchy / delegation-topology / standalone-usage updates, `docs/agents.md` and `docs/review-agents.md` (with "when applicable" wording), and `AGENTS.md` Canonical sources (when the new skill introduces a shared script or is itself canonical). Existing README catalog + `.claude/settings.json` permission reminders unchanged.
- `scripts/test-post-scaffold-hints.sh` — add contract-token assertions for the new reminders and a negative assertion verifying the `--plugin false` branch does not leak them.
- `docs/workflow-lifecycle.md` — restructure the Skill Orchestration Hierarchy to include `/fix-issue` and `/loop-improve-skill` as orchestrators; add a new "Delegation Topology" subsection covering `/im`, `/imaq`, `/alias`, `/create-skill` as pure forwarders with their delegation edges; expand Standalone Usage with `/fix-issue`, `/loop-improve-skill`, `/create-skill`, `/issue`.
- `skills/shared/subskill-invocation.md` — update the Pattern A cited source-example citation from `/create-skill § Step 3 — Delegate to /implement` to `§ Step 3 — Delegate to /im`; add a note explaining the chained delegation.
- `skills/create-skill/scripts/parse-args.sh` — refresh the `--merge` header comment to state the flag is accepted for backward compatibility but no longer forwarded (since `/im` already prepends `--merge`).
- `README.md` — update the `/create-skill` skill-catalog row to describe the new `/im` delegation target and auto-merge default.
- `AGENTS.md` — expand the `skills/create-skill/scripts/post-scaffold-hints.sh` bullet to document the new reminder tokens and the paired harness contract.

## [4.2.0] - 2026-04-20

### Added

- `/implement --draft` — creates a draft PR and skips Step 14 local cleanup so the feature branch is retained for further iteration. Mutually exclusive with `--merge`. Forwarded from `create-pr.sh` to `gh pr create --draft`.

## [4.1.0] - 2026-04-20

### Added

- `/loop-improve-skill <skill-name>` — iteratively improve an existing larch skill. Creates a tracking GitHub issue, then loops `/skill-judge` → post judgment → `/design` → (exit if no plan materializes) → post plan → `/im`, up to 10 iterations. Each iteration's judgment and design plan are posted as issue comments for an audit trail. Registered in README Skills catalog, `.claude/settings.json` permissions, and the anti-halt banner harness.

## [4.0.21] - 2026-04-19

### Changed

- `.gitignore` — ignore `.agents/` and `skills-lock.json`.

## [4.0.20] - 2026-04-19

### Changed

- `.claude/settings.json` — enable `skill-judge` and `caveman` plugins; register `caveman` marketplace (`github:JuliusBrussee/caveman`).
- `CLAUDE.md` — set default caveman output mode to `full`.

## [4.0.19] - 2026-04-19

### Changed

## [4.0.18] - 2026-04-19

### Fixed

- `skills/fix-issue/scripts/fetch-eligible-issue.sh` — the GO-sentinel check at two sites (explicit-issue path and auto-pick loop) used `gh api --paginate "repos/…/comments" --jq '.[-1].body // empty' | tail -1`. Because `--jq` runs per page, `.[-1]` returned the last element of each page, not the last of the full history — the `tail -1` was only accidentally correct (pages arrive in order, so the final page's last element coincides with the globally-last comment, but the logic is brittle to any jq/paginate behavior change and `tail -1` also truncates multi-line last comments to their final line). Both sites now use the `gh api --paginate --slurp … | jq -r 'add // [] | .[-1].body // empty'` pattern already used by `prose_open_blockers` at line 135-136 — `--slurp` concatenates all pages into one JSON array-of-arrays, `add // []` flattens to a single array, `.[-1].body` unambiguously addresses the globally-last comment. Closes #184.

## [4.0.17] - 2026-04-19

### Fixed

- Orchestrator SKILL.md files (`fix-issue`, `implement`, `review`, `loop-review`) now carry a prominent top-of-file "Anti-halt continuation reminder" banner plus per-Skill-call-site micro-reminders, so the main agent does not halt on a child skill's cleanup output and skip the parent's remaining steps. The canonical wording lives in `skills/shared/subskill-invocation.md`'s new "Anti-halt continuation reminder" section (complementary to the existing "Post-invocation verification" section — "did the child run?" vs "did the parent continue?"). The `skills/create-skill/scripts/render-skill-md.sh` scaffold checklist gains a 6th item so new orchestrators inherit the convention. New regression harness `scripts/test-anti-halt-banners.sh` asserts banner presence in the 4 orchestrators, absence in the 4 pure-delegator skills, and micro-reminder presence in each orchestrator — wired into `make lint` via the `test-anti-halt` target. Closes #177.

## [4.0.16] - 2026-04-19

### Changed

- `scripts/lint-skill-invocations.py` now enforces the sub-skill-invocation style guide at two levels (closes #180). The existing total-omission check is preserved unchanged. A new line-local per-invocation check flags lines matching `INVOCATION_LINE_REGEX` — direct imperative `Invoke`/`re-invoke` (optionally `the` + a bounded `**bold-span**`) immediately followed by a backticked `` `/<name>` ``, optionally followed by `skill` — that lack `via the Skill tool` on the same line. Sub-procedure references and helper-script citations are exempt by construction; lines inside fenced code blocks are exempt. Per-invocation messages emit absolute file line numbers (frontmatter offset preserved) so editor jump-to-line works. `lint_file()` returns `list[str]` instead of `str | None`; `extract_frontmatter_and_body()` additionally returns the body's absolute file start line.
- `scripts/test-lint-skill-invocations.sh` adds 9 black-box cases (m–u) covering pure Pattern A, Pattern B per-invocation passes, bare invoke with absolute line assertion, multiple violations, code-fence exemption, total-omission + per-invocation in same file, helper-script citation exemption, sub-procedure exemption, and `re-invoke` in scope.
- `skills/implement/SKILL.md` (8 lines) and `skills/loop-review/SKILL.md` (1 line) updated to add `via the Skill tool` to direct-invocation phrasings the new check surfaces. `AGENTS.md` documents the two-check contract; `skills/shared/subskill-invocation.md` carries a one-line note about line-local enforcement.

## [4.0.15] - 2026-04-19

### Changed

- `/fix-issue` now honors prose-stated dependency relationships in addition to GitHub's native `blocked_by` API. `skills/fix-issue/scripts/fetch-eligible-issue.sh` unions two blocker sources before declaring an issue eligible: (1) the existing native-dependencies check, and (2) a new `prose_open_blockers()` function that extracts same-repo issue numbers from the issue body and every comment body using the conservative case-insensitive keyword set (`Depends on #N`, `Blocked by #N`, `Blocked on #N`, `Requires #N`, `Needs #N`). A native-first short-circuit skips the prose path when the native check already flags the candidate, capping API volume at the cost of a documented diagnostic gap in skip/error messages. Every boundary is fail-open, mirroring the pre-existing native-dep contract. Motivating case: issue #152's body used `Depends on **#150 (bypass fix) only**` but the native `blocked_by` endpoint had no dependency registered, so `/fix-issue` picked it up as eligible despite the prose-declared open blocker.
- `skills/fix-issue/scripts/parse-prose-blockers.sh` is the new pure text-in / numbers-out parser (takes one document body at a time, no network). Emphasis wrappers (`*`, `_`) are normalized before matching so `**#150**` formatting is caught; link-target forms (`[#150](url)`) and cross-repo references (`owner/repo#N`) remain NON-matches by parser construction. `skills/fix-issue/scripts/test-parse-prose-blockers.sh` is its 43-assertion offline regression harness — wired into `make lint` via the new `test-parse-prose-blockers` target and added to `agent-lint.toml`'s exclude list per the Makefile-only harness convention. `skills/fix-issue/SKILL.md` Step 1 and Known Limitations are updated accordingly; `README.md`'s `/fix-issue` row is updated to mention both native and prose keyword scanning.

## [4.0.14] - 2026-04-19

### Fixed

- `.claude/settings.json` no longer mirrors the `PreToolUse` submodule-guard registration; `hooks/hooks.json` (with `${CLAUDE_PLUGIN_ROOT}` paths) is now the single source of truth, eliminating possible double-invocation, policy drift between the two copies, and the `$PWD`-vs-anchored path question. Contributors developing in this repo should load larch as a plugin (`claude --plugin-dir .` or the local marketplace) to pick up the guard — `AGENTS.md` carries a one-line note to that effect. Closes #152.

## [4.0.13] - 2026-04-19

### Fixed

- `.pre-commit-config.yaml`'s `shellcheck` hook gains `args: [-x]` so pre-commit instructs shellcheck to follow `source` directives, eliminating the SC1091 false-positive that fired when `/relevant-checks` (via `pre-commit run --files <subset>`) scoped shellcheck to consumers of `scripts/lib-count-commits.sh` (`scripts/check-bump-version.sh`, `scripts/verify-skill-called.sh`) without also including the library itself. CI's `make lint` (via `pre-commit run --all-files`) was unaffected because all files were always present. With `-x`, the file-subset path now matches the all-files behavior on source-following. Reproduces on unmodified main via `pre-commit run shellcheck --files scripts/check-bump-version.sh`. Closes #178.

## [4.0.12] - 2026-04-19

### Added

- `scripts/lint-skill-invocations.py` — minimal-guardrail lint that flags public and dev `SKILL.md` files which declare `Skill` in their `allowed-tools` frontmatter but omit both canonical invocation phrases (`Invoke the Skill tool`, `via the Skill tool`) anywhere in the body. Catches *total omission* only; per-invocation alignment is intentionally out of scope and tracked as follow-up issue #180. Accepts `--root <dir>` (defaults to the script's parent directory) so the regression harness can isolate fixtures under a temp tree. Uses `PyYAML` for frontmatter parsing, normalizes leading UTF-8 BOM and CRLF before the `---` prefix test, and distinguishes internal errors (unreadable or non-UTF-8 files → exit 2) from policy violations (→ exit 1); exit 2 takes priority when both occur.
- `scripts/test-lint-skill-invocations.sh` — 12-case black-box regression harness (a through l) covering Pattern A, Pattern B, YAML-list and quoted-string `allowed-tools` shapes, exact-token discipline (`SkillCheck` must not satisfy a `Skill` requirement), multi-violation runs, CRLF/BOM normalization, non-UTF-8 files exercising the exit-2 internal-error path, and the mixed error+violation priority rule. Wired into `make lint` via the new `test-lint-skill-invocations` target and added to `agent-lint.toml`'s exclude list.
- `.pre-commit-config.yaml` gains a `lint-skill-invocations` local hook with `additional_dependencies: ['pyyaml==6.0.2']`, `always_run: true`, `pass_filenames: false`. The hook runs in its own isolated venv and fires uniformly from `make lint`, `/relevant-checks`, and CI's existing lint job. `.github/workflows/ci.yaml`'s lint step additionally installs `pyyaml==6.0.2` into the ambient Python so the `test-lint-skill-invocations` harness (which invokes the script directly with `python3`, outside the pre-commit venv) can import it; the pyyaml version is pinned identically in both locations. Closes #159.

### Changed

- `skills/review/SKILL.md` Step 3e rewrites "invoke `/relevant-checks`" to "invoke `/relevant-checks` via the Skill tool" (Pattern B), addressing pre-existing non-compliance with the sub-skill invocation style guide that the new lint uncovers.

## [4.0.11] - 2026-04-19

### Fixed

- `scripts/check-bump-version.sh` now surfaces a `STATUS=ok|missing_main_ref|git_error` field on stdout in both `--mode pre` and `--mode post`, plumbed from `scripts/lib-count-commits.sh`'s `COUNT_COMMITS_STATUS_FILE` side channel. In `--mode post`, `VERIFIED=true` is emitted ONLY when `STATUS=ok` AND the numeric commit-delta matches — any non-`ok` status forces `VERIFIED=false` at the script level, closing the #172 silent-zero false-pass window where a symmetric `git rev-list` failure on both pre- and post-calls coerced counts to 0 on each side and spuriously matched. Any unknown or empty token received from the side channel is normalized to `STATUS=git_error` (fail-closed, mirrors `verify-skill-called.sh`'s default branch). Existing KEY=VALUE contract (HAS_BUMP, COMMITS_BEFORE, VERIFIED, COMMITS_AFTER, EXPECTED) is preserved — the new line is additive. `scripts/test-check-bump-version.sh` is the new 43-assertion black-box regression harness covering all three status paths × both modes, the `origin/main`-only fallback, unknown-token normalization, a pre-degraded + post-recovered caller sequence, and a dedicated fail-closed regression guard that proves delta-0 + expected-0 under non-ok STATUS cannot spuriously pass. Uses a PATH shim forcing `git rev-list` to fail while leaving `git rev-parse` intact as the deterministic git_error fixture. Wired into `make lint` via `test-check-bump-version`; added to `agent-lint.toml`'s exclude list. `skills/implement/SKILL.md` Step 8 and Rebase + Re-bump Sub-procedure step 4 restructure their VERIFIED/COMMITS decision trees so `STATUS != ok` is evaluated as prior branches BEFORE the numeric comparison: Step 12 (step12 family, pre-merge last-chance) hard-bails on non-`ok` STATUS from either the pre-check or the post-check with distinct actionable messages; Step 10 (step10 family) and Step 8 log warnings and proceed permissively per their existing semantics, with a HAS_BUMP=false short-circuit in the step10 pre-STATUS guard to avoid invoking a non-existent skill. The instruction to grep stderr for the `WARN: ... neither local 'main' nor 'origin/main' exists` line is removed — `STATUS=` is now authoritative. `skills/shared/subskill-invocation.md`'s `/bump-version` example is updated to parse STATUS and note the check-STATUS-before-counts rule. Closes #172.

## [4.0.10] - 2026-04-20

### Fixed

- `scripts/block-submodule-edit.sh` closes the cd-into-submodule bypass (#150): `REPO_ROOT` now resolves via a two-step anchor — try `CLAUDE_PROJECT_DIR` first, fall through to `$PWD` when the first attempt does not yield a git repo — so a session that has `cd`'d into a submodule still detects the superproject, and a stale/broken `CLAUDE_PROJECT_DIR` cannot silently downgrade the guard to fail-open when `$PWD` is a healthy superproject. `scripts/test-block-submodule-edit.sh` case 3 auto-flips from KNOWN-FAIL to PASS via the existing tri-state fingerprint (retained as defense-in-depth against future regressions); the harness also unsets any inherited `CLAUDE_PROJECT_DIR` at startup for hermeticity and gains new case 3b covering the broken-anchor + healthy-`$PWD` fallback scenario. `SECURITY.md` gains a one-paragraph note in the Trust Model section documenting the `CLAUDE_PROJECT_DIR` anchor and the bypass it closes. Closes #150.

## [4.0.9] - 2026-04-19

### Added

- `scripts/verify-skill-called.sh` — generic mechanical post-invocation verifier for `Skill` tool calls, with three mutually-exclusive modes: `--sentinel-file <path>` (file exists, regular, non-empty), `--stdout-line <regex> --stdout-file <path>` (captured stdout has a matching line via `LC_ALL=C grep -E -q -- …`; empty regex rejected as argument error; grep exit 2 treated as internal fault per fail-closed contract), and `--commit-delta <N> --before-count <B>` (commit count ahead of main increased by exactly N). Emits `VERIFIED=true|false` and `REASON=<token>` on stdout; exit 0 for pass/fail outcomes, exit 1 only for argument errors or internal faults. Reason tokens are a stable enum: `ok`, `missing_path`, `not_regular_file`, `empty_file`, `missing_stdout_file`, `no_match`, `commit_delta_mismatch`, `missing_main_ref`, `git_error`. Intended as a defense-in-depth gate for `Skill` calls whose child skills have no dedicated domain-specific verifier.
- `scripts/lib-count-commits.sh` — sourced-only shell library (no shebang, not invokable directly) extracting the shared `count_commits` function used by both `scripts/check-bump-version.sh` and the new verifier. Distinguishes `ok` / `missing_main_ref` / `git_error` via a file-based status side channel (`COUNT_COMMITS_STATUS_FILE`) so the `$(count_commits)` subshell's result can be classified without losing the status. Preserves the existing `WARN: check-bump-version.sh:` stderr prefix for log parity with operators' existing grep patterns. Explicitly documents that `.claude/skills/bump-version/scripts/classify-bump.sh`'s merge-base logic is a structurally different concept intentionally not migrated.
- `scripts/test-verify-skill-called.sh` — 53-assertion black-box regression harness covering all three modes' pass/fail paths, argument-error paths (exit 1 with no KEY=VALUE), stdout-contract assertions, exit-code assertions on every non-argument-error path, malformed-ERE regression (grep exit 2 → exit 1 fail-closed), and the cwd-neutral source chain via `check-bump-version.sh`. Wired into `make lint` via the new `test-verify-skill-called` target. Added to `agent-lint.toml`'s exclude list alongside `scripts/lib-count-commits.sh`.
- `skills/implement/SKILL.md` Step 8 and Step 12 Rebase + Re-bump Sub-procedure step 4 migrate to call `verify-skill-called.sh --sentinel-file "$BUMP_REASONING_FILE"` alongside the existing `check-bump-version.sh --mode post` commit-delta check, with an empty-path guard. The sentinel check is advisory (warn-and-continue; commit-delta remains the hard gate) and complementary. `scripts/check-bump-version.sh` refactored to source `lib-count-commits.sh`; no behavior change. Closes #160.

## [4.0.8] - 2026-04-19

### Added

- Canonical sub-skill invocation style guide: `skills/shared/subskill-invocation.md` documents the six conventions larch skills already follow implicitly — two first-class invocation patterns (Pattern A bulleted bare-name fallback, Pattern B inline "Invoke `/X` via the Skill tool"), the `allowed-tools` narrowing heuristic (pure delegator → `Skill` only, delegator-that-validates → `Bash, Skill`, hybrid orchestrator → `Skill` plus whatever the parent needs), post-invocation verification expectation (scoped to orchestrators that continue based on child side effects — pure forwarders exempt), session-env handoff with safe-parse rule (do NOT `source` the file; parse line-by-line; writer does not escape so constrain the value set at the source), anti-conditional-phrasing for Skill-tool calls, and the bare-name-then-fully-qualified (`larch:<name>`) fallback. `skills/create-skill/scripts/render-skill-md.sh` now emits a `## Sub-skill Invocation` checklist block unconditionally in both minimal and multi-step scaffold variants, placed after `## Progress Reporting` and before `## Step 0` in multi-step and at the bottom of MINIMAL_BODY, so every newly scaffolded skill inherits the conventions with a pointer to the canonical guide. `skills/create-skill/scripts/post-scaffold-hints.sh` gains a reminder line pointing at the guide. `skills/create-skill/scripts/test-render-skill-md.sh` is the new 3-case regression harness asserting `RENDERED=` stdout line, frontmatter name + YAML-quoted description, `## Sub-skill Invocation` section presence, a `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` citation with non-empty prefix (guards against empty `--plugin-token` producing a rooted path), and empty-`--plugin-token` rejection. Wired into `make lint` via the new `test-render-skill` target. `AGENTS.md` declares the shared file as canonical (Editing rules + Canonical sources). `agent-lint.toml` excludes the new harness from the G004/dead-script rule (Makefile-only reference, matching the `test-deny-edit-write.sh` precedent). Closes #158.

## [4.0.7] - 2026-04-19

### Fixed

- `scripts/block-submodule-edit.sh` now resolves `tool_input.file_path` through any symlink chain before repo classification, closing the bypass where a symlink in the superproject pointing into a submodule was allowed (the hook previously canonicalized only the containing directory via `pwd -P` and never resolved the `file_path` itself). Implementation is a bounded-depth (40-hop) pure-bash `readlink` loop inserted after `REPO_ROOT` canonicalization and before the ancestor walk — non-symlink inputs pass through unchanged, so all prior allow / deny behavior is preserved. macOS ships without `readlink -f` / `realpath` so the loop avoids them; relative readlink targets are rebased against the link's own directory. Fail-closed via the existing `block()` helper on depth-cap exhaustion (possible cycle), `readlink` failure, or empty target. `scripts/test-block-submodule-edit.sh` gains three strict regression cases: case 11 (absolute symlink into submodule → deny), case 12 (self-referential symlink cycle → deny via depth cap), case 13 (relative symlink into submodule → deny, exercises the `$(dirname "$resolved")/$target` rebasing branch); the top-of-file fixture comment block lists the three new symlinks. Closes #166.

## [4.0.6] - 2026-04-19

### Added

- Strict-permissions consumer guidance: README.md gains a `### Strict-permissions consumers — Skill permission entries` subsection documenting that `Skill(name)` is exact-match and does NOT authorize `Skill(larch:name)` (per Claude Code's official permissions docs), that `Skill(larch:*)` wildcards are not currently supported, and that consumers running without `"defaultMode": "bypassPermissions"` must grant both the bare and fully-qualified form for each larch skill. Includes a copy-paste `settings.allow` snippet covering all 11 public plugin skills in strict ASCII code-point order, the shadowing caveat (bare names may resolve to project-local skills before reaching the plugin), and links to upstream Claude Code docs. `skills/create-skill/SKILL.md` Step 3 and `skills/create-skill/scripts/post-scaffold-hints.sh` now emit both `Skill(<NAME>)` and `Skill(larch:<NAME>)` when scaffolding plugin-mode skills, with a cross-reference to the README subsection for rationale. `scripts/test-post-scaffold-hints.sh` is the new 20-assertion regression harness covering `--plugin true/false` branches, dual-Skill output, literal-`$PWD` Bash entry, `sort -u` instruction, and the single-line README subsection title (verified across a normal skill name and the ASCII-edge-case `loop-review`); wired into `make lint` via the new `test-post-scaffold-hints` target. `SECURITY.md` gains a one-sentence pointer to the new README subsection in the Trust Model section. `AGENTS.md` documents the harness contract alongside the other `test-*` entries. `agent-lint.toml` adds the new test script to the G004/dead-script exclude list (Makefile-only reference, matching the `test-deny-edit-write.sh` precedent). `README.md` install paragraph also gains the missing `/create-skill` entry in the slash-command list. Closes #161. Cross-references #158.

## [4.0.5] - 2026-04-19

### Added

- Skill-scoped PreToolUse deny hook for `/research`: `skills/research/SKILL.md` frontmatter now declares a `hooks:` block that registers a PreToolUse deny on `Edit|Write|NotebookEdit` matchers, executing the new `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh`. The hook emits a fixed `hookSpecificOutput` JSON deny envelope and always exits 0 — when `jq` is on PATH it composes the JSON via `jq -cn`, otherwise it falls back to a byte-identical static `printf` (matches the precedent in `scripts/block-submodule-edit.sh`). This is a defense-in-depth second mechanical layer; the `allowed-tools` frontmatter omitting `Edit`/`Write`/`Skill` remains the primary mechanical control because hook JSON `permissionDecision` semantics may vary by Claude Code version. External Codex/Cursor reviewers and Bash-mediated writes from `/research` itself remain prompt-enforced — the issue text and SECURITY.md document this gap. `scripts/test-deny-edit-write.sh` is the 7-assertion regression harness (exit code, valid JSON, hookEventName, permissionDecision, permissionDecisionReason non-empty, idempotency, and `env -i PATH=$STUB_DIR` byte-identity check across the jq and printf branches), wired into `make lint` via the new `test-deny-edit-write` target. `agent-lint.toml` excludes the test script (Makefile-only reference, matches the `test-sessionstart-health.sh` precedent); the hook script itself is structurally referenced from the SKILL.md `hooks:` block. `SECURITY.md`, `AGENTS.md`, and `README.md` updated per repo convention. Closes #154.

## [4.0.4] - 2026-04-19

### Changed

- `scripts/block-submodule-edit.sh` deny channel now uses Anthropic's documented `hookSpecificOutput` JSON shape (`hookEventName=PreToolUse`, `permissionDecision=deny`, `permissionDecisionReason=<why>`) emitted on stdout with exit 0, replacing the prior exit-2 + stdout-reason behavior that directly contradicted the PreToolUse spec (where exit 2 routes stderr, not stdout, to Claude). `block()` is hardened with a static-JSON fallback for rare `jq` runtime failures so a broken `jq` never degrades to exit 0 + empty stdout (which the runtime interprets as allow, silently weakening the submodule-edit policy). The `jq` availability probe moves ahead of every `block()` call and emits a hardcoded deny JSON literal on the missing-`jq` path. `scripts/test-block-submodule-edit.sh` gains an `assert_deny_json` helper (with an empty-needle guard) and rewrites every deny-case assertion to parse stdout with `jq` and check all three fields; case 3's tri-state fingerprint is updated to match the new contract; case-7 mini-bin comments are rewritten to reflect the jq-first probe ordering. Closes #151.

## [4.0.3] - 2026-04-19

### Added

- `scripts/test-block-submodule-edit.sh` regression harness for `scripts/block-submodule-edit.sh` (the PreToolUse hook that denies edits to files inside submodules), covering 11 cases: allow (superproject, nested non-submodule repo, symlink, non-repo cwd, out-of-repo file_path), deny (submodule file, ancestor-walk into new subdir, non-absolute path, bad JSON, missing jq), and a known-failing bypass case (cwd inside submodule) whose tri-state fingerprint logic auto-flips to PASS when #150 lands. Wired into `make lint` via the new `test-block-submodule` target. `AGENTS.md` and `README.md` document the harness. `scripts/block-submodule-edit.sh` gains a header comment pointing at the test. Closes #149.

## [4.0.2] - 2026-04-19

### Added

- `scripts/audit-edit-write.sh` — dev-only opt-in `PostToolUse` audit hook that appends one JSONL line per `Edit` / `Write` tool invocation to `.claude/hook-audit.log`. Shipped in the plugin install tree but **not registered by default** in `hooks/hooks.json` or `.claude/settings.json`; contributors opt in locally via the gitignored `.claude/settings.local.json`. Uses `set -uo pipefail` (no `-e`), always exits 0, `|| true` on the append — a PostToolUse hook must never block Edit/Write, even on disk full / read-only fs. `jq -ec --arg ts … 'select(type=="object") | {ts, event, payload: .}'` composes the log line; empty / invalid / non-object stdin exits non-zero and the `|| true` swallows it, so no corrupted or empty-payload line is ever appended. `scripts/test-audit-edit-write.sh` is the 12-assertion regression harness (tmpdir + `CLAUDE_PROJECT_DIR` override, happy-path + append-order + empty-stdin + invalid-JSON-stdin coverage), wired into `make lint` via the new `test-audit-edit-write` phony target. `docs/dev-hook-audit.md` documents enable / rotate / privacy / concurrency with two enablement snippets (`$PWD/…` for in-repo dev, `${CLAUDE_PLUGIN_ROOT}/…` for plugin consumers). `SECURITY.md` gains a dev-only-audit-log subsection per AGENTS.md's security-documentation contract. `.gitignore` adds `.claude/hook-audit.log`. `agent-lint.toml` adds the two scripts to the G004/dead-script exclude list alongside the existing `scripts/test-sessionstart-health.sh` entry — all three are dev-infrastructure scripts structurally referenced from Makefile/docs/AGENTS.md but not from the SKILL.md / hooks.json / settings.json files agent-lint scans. Closes #155.

## [4.0.1] - 2026-04-19

### Added

- New `SessionStart` hook `scripts/sessionstart-health.sh` probes `jq` and `git` on `PATH` at session start/resume/clear/compact and injects a spec-compliant `hookSpecificOutput.additionalContext` advisory when either is missing. Non-blocking (always exits 0) and silent on the happy path — converts the existing reactive-block-at-first-edit pattern in `scripts/block-submodule-edit.sh` into a proactive session-start advisory. JSON is emitted via `printf` only (no `jq` dependency inside the hook) so the warning reaches Claude's session context even when `jq` itself is missing. Regression test `scripts/test-sessionstart-health.sh` covers 4 cases (both present, jq missing, git missing, both missing) using a stub-only PATH via `env -i PATH="$STUB_DIR" "$BASH_BIN"` for strict isolation. Wired into `make lint` via the new `test-sessionstart` target. README.md feature matrix updated; AGENTS.md editing rules updated with the fixed-ASCII-literal invariant. Closes #153.

## [4.0.0] - 2026-04-19

### Changed

- **BREAKING**: `/loop-review` now files GitHub issues via `/issue` instead of creating PRs via `/implement`. Every actionable finding becomes a deduplicated issue labeled `loop-review` (reusing `/issue`'s 2-phase LLM dedup against open + recently-closed issues). The IMPLEMENT/DEFER classification collapses into a single FILE gate; `LOOP_REVIEW_DEFERRED.md` is no longer created, maintained, or committed (legacy files in consumer repos are left untouched). `--debug` propagation to downstream skills is dropped (`/issue` has no such flag). Step Name Registry rewritten: Step 4 "Final Deferred Commit" removed; Step 3 renamed from "implement/defer" to "review + file issues". Downstream tooling that parsed loop-review's output expecting PR URLs, merge status, CI results, or the deferred-doc file will break — switch to the `label:loop-review` GitHub filter. Closes #148.
- Security-tagged findings are held locally in `$LR_TMPDIR/security-findings.md` (never auto-filed as public GitHub issues, per SECURITY.md's vulnerability-disclosure policy). Step 4 final summary prints the full contents of that file inline in the transcript so operators see them before Step 5 cleanup removes the tmpdir. All three reviewer lanes (Claude Code Reviewer subagent, Cursor, Codex) are now prompted with the same 5-focus-area taxonomy (including `security`) with EXACT-label tagging required, so security findings route consistently regardless of reviewer.
- `/loop-review` Step 0c adds a preflight check that the `loop-review` GitHub label exists in the target repo. Missing label → warning appended to `warnings.md` and surfaced in the final summary (issues are still filed, just unlabeled). Previously `/issue` emitted the label-drop warning only on stderr, which loop-review's stdout-only flush parser never saw.
- Partial `/issue` failures no longer silently drop loop-review findings. After each flush, loop-review parses per-item `ITEM_<i>_*` stdout lines and retains only unresolved entries (failed or missing) in `findings-accumulated.md` for the next flush.
- Tracking files in `skills/loop-review/scripts/init-session-files.sh` renamed: `deferred-accumulated.md`, `pr-count.txt`, `impl-count.txt`, `defer-count.txt` removed; `findings-accumulated.md`, `security-findings.md`, `issue-count.txt`, `issue-dedup-count.txt`, `issue-failed-count.txt` added.
- `SECURITY.md` documents the new hold-local policy for security-tagged findings in `/loop-review`.
- `docs/workflow-lifecycle.md` updated: mermaid edge now shows `/loop-review → /issue`; `/loop-review --debug` documented as local-only (no downstream propagation).
- `README.md` Features bullet and `/loop-review` skill-table row reworded from PR-creation to issue-filing.
- `skills/loop-review/diagram.svg` regenerated to match the new flow (review → classify → FILE gate → HOLD LOCAL / DROP / accumulate → `/issue` flush).
- `skills/issue/scripts/test-parse-input.sh` gains Case 16 (10 assertions) guarding the exact generic batch shape loop-review commits to. 121 → 133 assertions, all pass.

## [3.4.10] - 2026-04-19

### Fixed

- `skills/issue/scripts/parse-input.sh` no longer silently swallows an author-intended new item into an in-progress OOS body. When a plain `### <title>` line appears inside an OOS Description that has not yet seen a closing structured field (Reviewer / Vote tally / Phase), the parser now defers the absorb decision via a pending-heading state (`PENDING_HEADING` / `PENDING_BODY`). Resolution happens at the first disambiguating signal: Reviewer/Vote tally/Phase fires → `resolve_pending_foldback` merges pending content back into `CURRENT_BODY` (preserves the #129 `### Notes` subheading-absorption behavior byte-for-byte); `### OOS_N:` line or EOF arrives → `resolve_pending_split` emits the current OOS as MALFORMED with its non-empty body, then emits the pending heading + body as a new generic item. `emit_item` gains a `force_malformed` parameter so a MALFORMED item can carry a populated BODY. `flush_item` clears pending state alongside the other per-item resets. `skills/issue/SKILL.md` line 75 now describes the expanded MALFORMED trigger per unanimous dialectic vote. `test-parse-input.sh` rewrites case 6 from "documented absorb limitation" to the #138 contract and adds three regression locks: case 13 (multi-subheading OOS accumulation before Reviewer), case 14 (EOF split), case 15 (mid-stream `### OOS_N:` split). 83 → 121 assertions, all pass. Closes #138.

## [3.4.9] - 2026-04-19

### Fixed

- `skills/issue/scripts/create-one.sh` no longer merges `gh` stderr into the success-path variable used for URL extraction. Previously `ISSUE_URL=$(gh … 2>&1)` captured both stdout and stderr into one variable, and the downstream `grep -oE 'https?://…/issues/N'` parsed the combined blob; any future stderr line (progress or warning) on success could corrupt the extraction. The fix redirects stderr to a dedicated temp file (`ERR_TMP`) so `ISSUE_URL` holds only stdout on the success branch, and the failure branch reads `ERR_TMP` for the error message still piped through `redact`/flatten/`head -c 500`. `ERR_TMP` is registered in the existing `cleanup()` EXIT trap alongside `BODY_TMP`, so every exit path — including `emit_redaction_failure` on the no-URL branch — removes the stderr temp file, closing a potential durable-disk exposure for token-bearing error text. `scripts/test-redact-secrets.sh` grows a new section 3d case that stubs `gh` to emit a URL on stdout and a warning on stderr, asserting `ISSUE_NUMBER=137` is still extracted and stderr noise does not leak into `ISSUE_URL`. Closes #137.

## [3.4.8] - 2026-04-19

### Changed

- `skills/issue/scripts/test-parse-input.sh` is now wired into `make lint` via a new `test-parse-input` Makefile target, mirroring the existing `test-redact` target for `scripts/test-redact-secrets.sh`. The 83-assertion parser regression harness runs on every PR through the existing `lint` CI job in `.github/workflows/ci.yaml`, closing the gap where regressions in `skills/issue/scripts/parse-input.sh` could previously ship undetected. Documentation updated in `skills/issue/SKILL.md`, `AGENTS.md`, and the script header. Closes #136.

## [3.4.7] - 2026-04-19

### Fixed

- `scripts/test-redact-secrets.sh` no longer triggers GitHub secret-scanning's `sk-ant-*` heuristic as a false positive. The synthetic `SK_TOKEN` fixture on line 33 previously appeared as a contiguous `sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD` substring that GitHub's scanner flagged as an OpenAI API key (alert #1). The fix splits the `sk-ant-` prefix in the source via adjacent single-quoted bash strings (`'sk-''ant-…'`), which concatenate at runtime to the identical 47-character test value but contain no contiguous `sk-ant-` substring in the repo source. Three other sites in the same file that also contained contiguous `sk-ant-*` substrings (`dry_title_raw` literal on line 137, the `GHZERO` heredoc stub's `printf` on line 285, and the `assert_not_contains` needle on line 303) are likewise rewritten to build their token-shaped values from the canonical `SK_TOKEN` fixture via `${SK_TOKEN}` and `${SK_TOKEN:0:35}` expansions; the `GHZERO` heredoc is switched from quoted (`<<'GHZERO'`) to unquoted (`<<GHZERO`) with `\$1` escaping to allow the expansion. All 45 assertions still pass with byte-identical runtime values.

## [3.4.6] - 2026-04-19

### Fixed

- `skills/issue/scripts/parse-input.sh` applies the symmetric mode-guard to the OOS heading branch so that a literal `### OOS_N: ...` line inside a generic item's body is absorbed as body continuation rather than flushing the generic item and starting a new OOS item. Before this fix, the OOS-heading regex fired unconditionally — the #129 mode-guard only covered the plain `### <title>` branch, so pasting a nested OOS-shaped heading into a generic issue body silently split the item and mis-classified the body below. The new guard uses `CURRENT_MODE=generic && IN_BODY=true` plus a meaningful-body check (`${CURRENT_BODY//[[:space:]]/}` non-empty) to align semantics with the OOS→generic direction, where `IN_BODY=true` is always paired with non-whitespace content populated by `**Description**:`. Parameter expansion (not `=~`) is used so the outer OOS-heading regex's `BASH_REMATCH[1]` capture is not clobbered before the `else` branch reads it. `test-parse-input.sh` grows three cases: case 10 (nested `### OOS_42: nested example` inside real body prose — the #132 reproducer), case 11 (bodyless generic title immediately followed by a real OOS item — the degenerate split case), and case 12 (whitespace-only body followed by a real OOS item — the meaningful-body guard at work); 7 new assertions pass alongside the existing 76. In-branch comment documents the asymmetry rationale, the `BASH_REMATCH` clobbering caveat, and the deliberate difference between the absorb predicate (meaningful body) and `emit_item`'s MALFORMED predicate (`[[ -z "$body" ]]`). Fixes #132.

## [3.4.5] - 2026-04-19

### Changed

- Phase 4 cleanup for the dialectic debate overhaul: docs (`docs/voting-process.md`, `docs/agents.md`, `docs/external-reviewers.md`, `docs/workflow-lifecycle.md`, `README.md`) refreshed to reflect Phase 1-3 behavior — the 5-decision dialectic cap, external Cursor/Codex debaters with same-tool bucketing, bucket-skipped (no Claude substitution) debate semantics, 3-judge replacement-first panel, attribution-stripped ballot with position-order rotation, and the four-valued Disposition enum (`voted`, `fallback-to-synthesis`, `bucket-skipped`, `over-cap`). `docs/external-reviewers.md` gains an explicit Dialectic-specific behavior section cross-referencing `skills/shared/dialectic-protocol.md`. `docs/voting-process.md` gains a Relationship to Dialectic Protocol section that states semantic independence and the mechanical "no Claude debaters" rule (debate execution only, not judge adjudication).
- `skills/design/diagram.svg` redrawn: Step 2a.5 Dialectic Debate node expanded into a visual subgraph (contested decisions → bucketed Cursor/Codex debater pairs → attribution-stripped ballot → 3-judge panel → resolutions), and the stale plan-review label `(2 Claude + 2 Codex + Cursor)` corrected to `(1 Claude + 1 Codex + 1 Cursor)`.
- New offline regression guard: `scripts/dialectic-smoke-test.sh` is a bash-3.2-compatible fixture-driven parser/tally/structural-invariant validator. Loads fixtures from `tests/fixtures/dialectic/` (new top-level non-runtime tree), parses debater + ballot + judge artifacts, computes per-decision dispositions via the protocol's `Threshold Rules` matrix, and compares against a per-fixture `expected.txt` manifest. Six fixture variants cover: happy-path-5-decisions, two-judge-quorum (unanimous + 1-1 tie rows), bucket-skipped, over-cap, fallback-quorum-failure, and parser-tolerance (em-dash-or-hyphen separator, duplicate DECISION_N first-valid-wins, per-decision abstention). Validates ballot anonymity case-insensitively (`Cursor`/`Codex`/`Claude` must not appear anywhere in the body) and enforces a protocol drift guard that greps `skills/shared/dialectic-protocol.md` for the stable `Recognize exactly these four Disposition values` anchor and the four canonical values. `bucket-skipped` / `over-cap` dispositions require explicit structural absence (no debate-N files, no `DECISION_N:` in any judge file, no `### DECISION_N:` ballot heading) in addition to the 0/0 fallback tally, so a broken fixture cannot masquerade as correct coverage. Wired into the build as `make smoke-dialectic` and a dedicated `smoke-dialectic` CI job.

## [3.4.4] - 2026-04-19

### Fixed

- `skills/issue/scripts/parse-input.sh` Description bullet regex now accepts an empty inline value. Previously, `^-[[:space:]]+\*\*Description\*\*:[[:space:]]+(.+)$` required non-empty inline content, so a bullet written as `- **Description**:` with body on continuation lines only failed to match, `IN_BODY` never transitioned to `true`, and both the bullet line and all its continuations were silently dropped from `CURRENT_BODY`. The regex is relaxed to `^-[[:space:]]+\*\*Description\*\*:[[:space:]]*(.*)$` — both trailing quantifiers become zero-or-more, so an empty inline value captures as `""`, `IN_BODY` flips to `true`, and the existing fallback branch populates the body from subsequent continuation lines. `test-parse-input.sh` grows a new case 9 that feeds this shape (empty inline + multi-line continuation including a blank line) and asserts the decoded body, tallied vote count, reviewer, phase, and absence of `ITEM_1_MALFORMED`. Header grammar comment updated to document that the inline value may be empty. Closes #131.

## [3.4.3] - 2026-04-19

### Fixed

## [3.4.2] - 2026-04-19

### Fixed

- `skills/issue/scripts/parse-input.sh` now tracks an explicit per-item `CURRENT_MODE` (`oos` / `generic` / empty) to prevent two bugs where OOS and generic item parsing conflated structure. (a) A markdown subheading like `### Notes` inside an OOS item's Description body no longer triggers a premature `flush_item`; the new generic-heading branch absorbs the line as body continuation when `CURRENT_MODE=oos` AND `IN_BODY=true`, so OOS descriptions may contain `### …` subheadings. (b) Bullet lines `- **Description**:`, `- **Reviewer**:`, `- **Vote tally**:`, and `- **Phase**:` inside a generic item's body are no longer parsed as OOS metadata; the four OOS field branches now fire only when `CURRENT_MODE=oos`, so in generic items those bullets fall through to the `IN_BODY` continuation branch and remain verbatim in `ITEM_<i>_BODY`. `flush_item` resets `CURRENT_MODE` so per-item mode never leaks across items. The top-of-file grammar comment is rewritten to document mode transitions, the `###` absorption rule inside OOS descriptions, and the documented boundary limitation (an incomplete OOS item — Description only, no trailing Reviewer/Vote tally/Phase — followed by a `### …` line absorbs the following line as continuation; feed well-formed 4-field OOS inputs to terminate the body explicitly). New self-contained regression harness at `skills/issue/scripts/test-parse-input.sh` with 8 cases covering both bug reproducers, three well-formed baselines (OOS, generic, mixed complete OOS + generic), a back-to-back complete OOS case (the primary `/implement` Step 9a.1 production shape), a back-to-back generic case, and an executable contract for the documented incomplete-OOS absorption behavior — 52 assertions, all passing. Harness uses a portable `b64_decode()` helper (`-d` / `-D` fallback for macOS BSD base64) and invokes the parser via `bash "$PARSER"` so the exec bit is not required. Not wired into automated CI (deferred as out-of-scope per plan and code review voting); developers run it manually via `bash ${CLAUDE_PLUGIN_ROOT}/skills/issue/scripts/test-parse-input.sh`. Fixes #129.

## [3.4.1] - 2026-04-18

### Changed

- `/design` Step 2a.5 (dialectic Phase 3) now delegates contested-decision adjudication to a **3-judge binary panel** (Claude Code Reviewer subagent + Codex + Cursor) replacing the orchestrator's prior "debate quorum + winner-selection" block (`skills/design/SKILL.md:457-491`). New shared protocol file `skills/shared/dialectic-protocol.md` is structurally parallel to `voting-protocol.md` but semantically independent — uses `DECISION_N` ballot IDs with binary `THESIS | ANTI_THESIS` tokens (no EXONERATE), attribution-stripped `Defense A / Defense B` labels with deterministic position-order rotation (odd decision index → `CHOSEN` is Defense A, even → `ALTERNATIVE` is Defense A), and binary thresholds (3 judges → 2+ majority; 2 judges → unanimous with 1-1 tie → synthesis fallback; <2 judges → synthesis fallback). Judge panel uses repo-wide replacement-first: Claude Code Reviewer subagent replaces any unhealthy external to keep the panel at 3 — the "no Claude substitution" rule applies only to debate execution, not to adjudication. Judge panel re-probes tool health via `scripts/check-reviewers.sh --probe` immediately before launching, with explicit two-key rule (`AVAILABLE=true AND HEALTHY=true`) and judge-local flags that never mutate orchestrator-wide availability. `dialectic-resolutions.md` schema rewritten with structured fields: `Resolution`, `Disposition` (`voted | fallback-to-synthesis | bucket-skipped | over-cap`), `Vote tally`, `Thesis summary`, `Antithesis summary`, and a disposition-specific `Why …` justification. Step 2b parser branches on `Disposition` (only `voted` is binding; other dispositions mean synthesis stands and no antithesis-engagement prose is fabricated). Step 3.5 "still contested" criterion is now Disposition-based (both Behavior block at line 677 and Short-circuit at line 685 updated). Zero-external-judges guard added to both protocol doc and SKILL.md so the all-Claude-inline fallback path does not invoke `collect-agent-results.sh` with zero positional args. `docs/collaborative-sketches.md` differentiates debate handling (no Claude substitution) from judge-panel handling (replacement-first at 3) and updates the "How It Works" narrative to reflect Phase 3. `docs/workflow-lifecycle.md` node label updated. `skills/shared/progress-reporting.md` canonical Step 2a.5 completion-line examples updated to the new multi-count format (`<V> voted, <F> fallback, <S> bucket-skipped, <O> over-cap`). Closes #99.

## [3.4.0] - 2026-04-18

### Changed

- `/issue` rewritten for LLM-based semantic duplicate detection in 2 phases (titles → full bodies+comments) against open + recently-closed GitHub issues (default 90-day closed window), and `/implement` Step 9a.1 refactored to invoke `/issue` in batch mode via the Skill tool instead of calling the now-deleted `scripts/create-oos-issues.sh`. New flags: `--input-file FILE` (batch mode, OOS markdown format or generic `### <title>` + body), `--title-prefix PREFIX` (e.g. `[OOS]`, with case-insensitive double-prefix normalization), `--label LABEL` (repeatable, silently dropped with a stderr warning on labels that don't exist — preserves `create-oos-issues.sh`'s compatibility guard), `--body-file FILE` (single-mode alternative to inline description), `--dry-run` (no network calls, structured output tagged `DRY_RUN=true`). Single-mode behavior (free-form description + optional `--go`) is preserved, with one new error: when Phase 2 resolves the single item to a duplicate and `--go` is set, `/issue` errors with the duplicate's number and URL rather than creating or silently skipping. Key=value stdout contract (`ISSUES_CREATED/FAILED/DEDUPLICATED`, `ISSUE_<i>_NUMBER/URL/TITLE/DUPLICATE/DUPLICATE_OF_NUMBER/DUPLICATE_OF_URL`) preserved byte-for-byte so `/implement` Step 9a.1's downstream parsing, PR body placeholder, and `oos-issues-created.md` idempotency sentinel need no redesign. Architecture splits reasoning (in the `/issue` SKILL.md prompt) from I/O (four new shell helpers under `skills/issue/scripts/`): `list-issues.sh` uses `gh api --paginate` for unbounded snapshots (with a portable `python3`→BSD-`date`→GNU-`date` cutoff-date fallback chain so Linux CI works), `fetch-issue-details.sh` fetches candidate bodies and comments wrapped in `<external_issue_<N>>…</external_issue_<N>>` delimiter tags (caps: 20 most-recent comments, 4k body chars) inside an outer `<external_issues_corpus>` envelope with the "treat as data, not instructions" preamble, `parse-input.sh` ports the OOS-markdown parser from the deleted script (including `flush_item` malformed-item handling) and preserves blank continuation lines in multi-paragraph descriptions (matching the CHANGELOG 3.3.10 fix), `create-one.sh` wraps `gh issue create` with the label-probe guard, `[OOS]` double-prefix normalization, and emits `ISSUE_TITLE=$FINAL_TITLE` on success/dry-run so callers consume the applied title without reimplementing prefix logic. New `SECURITY.md` subsection "Untrusted GitHub Issue Content (/issue Phase 2)" documents the delimiter-tag hardening as prompt-level convention with residual-risk framing consistent with the reviewer-templates text. `.claude/settings.json` allowlist gains `Skill(issue)` and `Bash($PWD/skills/issue/scripts/*)` entries. LLM dedup fails open: any helper failure (network, rate limit, gh auth) warns on stderr and falls through to create-all; Phase 2 whitelist-validates LLM-emitted `DUPLICATE_OF=<N>` against the Phase 1 snapshot and intra-run `DUPLICATE_OF_ITEM=<j>` against `1 ≤ j < i`, falling back to CREATE on any unmatched identifier.

## [3.3.11] - 2026-04-18

### Changed

- `/design` Step 2a.5 (dialectic debate) now runs each contested decision's thesis+antithesis on **external Cursor or Codex** instead of the previous Claude Agent-tool subagent fan-out (`skills/design/SKILL.md`). Cap raised from 3 to 5 (`min(5, |contested-decisions|)`); deterministic per-decision bucketing assigns odd-indexed decisions (1, 3, 5) to Cursor and even-indexed (2, 4) to Codex, with both sides of each decision sharing the assigned tool. When the assigned tool is unavailable, the bucket is **skipped entirely** and the Step 2a.4 synthesis decision stands — Claude subagents are never substituted into the dialectic debate path (intentional divergence from the repo-wide replacement-first fallback architecture; see `skills/shared/voting-protocol.md` and Step 3 fallbacks). Option B for the unhealthy-status cascade: dialectic-scoped shadow flags (`dialectic_codex_available`, `dialectic_cursor_available`) snapshot the orchestrator-wide `*_available` at entry; orchestrator-wide flags are never mutated, and the dialectic `collect-agent-results.sh` call uses `--write-health /dev/null` so Step 3 plan-review panel integrity is preserved by construction. Per-decision rendered prompts are written to files under `$DESIGN_TMPDIR` and referenced by path in the launch prompt (mirrors the voting-protocol pattern, avoids `cat`-based shell patterns that trigger Claude Code permission prompts). The quorum rule now has a mandatory STATUS pre-check that immediately fails any decision where either side returned `STATUS != OK` from the collector, preventing one-sided binding resolutions from partial-launch cases. Phase 1's tagged-output prompt template bodies, debate quorum rule, winner-selection rule, and `dialectic-resolutions.md` schema are preserved byte-for-byte. `docs/collaborative-sketches.md` is updated with the new cap (3→5), tool-routing description, and a new "Dialectic debate" row in the "Fallback Behavior by Phase" table that documents the no-Claude-substitution rule. Closes #98.

## [3.3.10] - 2026-04-18

### Fixed

- `scripts/create-oos-issues.sh` parser no longer silently drops blank lines inside a multi-line `Description` block. The continuation branch previously guarded on `[[ -n "${line// }" ]]`, which skipped every blank line — so any multi-paragraph OOS description produced by `/design`, `/review`, or (after #118 landed) main-agent dual-write collapsed into a single run-together paragraph in the filed issue body. `IN_DESCRIPTION` is already cleared only by a recognized field marker (`Reviewer:`, `Vote tally:`, `Phase:`) or a new `### OOS_N:` header, so removing the non-blank guard is sufficient to preserve paragraph breaks without capturing structural lines. Fixes #123.

## [3.3.9] - 2026-04-18

### Changed

- `/implement` now files GitHub issues for main-agent-discovered out-of-scope (OOS) pre-existing bugs unconditionally, regardless of mode (`--quick`, `--auto`, `--merge`, `--debug`, `--no-merge`). Previously Step 9a.1 was gated on `quick_mode=false`, so pre-existing code issues discovered by the main agent in quick mode (logged only to `execution-issues.md` under "Pre-existing Code Issues") got buried in the PR body's `<details><summary>Execution Issues</summary>` block and never reached the issue tracker (e.g., `scripts/drop-bump-commit.sh` Guard 4 bug discovered during `/fix-issue 110` / PR #115). The fix introduces a mandatory dual-write contract in `skills/implement/SKILL.md` "Execution Issues Tracking": whenever the main agent appends a `Pre-existing Code Issues` entry to `execution-issues.md`, it MUST also append a corresponding `### OOS_N:` block to a new artifact `oos-accepted-main-agent.md` carrying the same five-field schema (`title`, `Description` with file:line and reproduction context and suggested fix, `Reviewer: Main agent`, `Vote tally: N/A — auto-filed per policy`, `Phase: implement`) used by `/design` and `/review` for reviewer-voted OOS — converging the two pipelines into a single accepted-OOS path. The dual-write rule includes a MUST-strength in-file dedup guard (case-insensitive title match) before append and a MUST-strength sanitization rule for secrets, internal URLs, and PII; correction of an existing entry uses in-place replacement of the same `OOS_N` block, not a second append. Step 9a.1 now reads all three OOS artifacts (`oos-accepted-design.md`, `oos-accepted-review.md`, `oos-accepted-main-agent.md`), dedupes across phases by exact normalized title (matching `create-oos-issues.sh`'s `normalize_title()` algorithm), and feeds the merged set to `create-oos-issues.sh` which already handles dedup against open GitHub issues. The only legitimate hard-skip on Step 9a.1 is now `repo_unavailable=true`. Each early-exit branch (`repo_unavailable=true`, all-empty, idempotent rerun) updates the PR body's "Accepted OOS (GitHub issues filed)" subsection and `| OOS issues filed |` Run Statistics cell directly, eliminating the prior forward-reference bug where early exits left placeholders unfilled. Quick-mode PR body guidance for the Out-of-Scope Observations section is rewritten so the Accepted OOS subsection is populated from main-agent-surfaced items and the Non-accepted subsection carries generic boilerplate that no longer falsely claims items were filed when none existed. `scripts/create-oos-issues.sh` documents `Phase: design|review|implement` in its header (was `design|review`); the issue-body footer is reworded to source-agnostic ("surfaced as an out-of-scope observation during the workflow") instead of falsely asserting "received majority YES votes" for main-agent items; a new `redact_secrets()` shell helper provides a deterministic defense-in-depth backstop for common token patterns (`sk-*`, `ghp_*`, `AKIA*`, `xox*`, JWT, PEM private keys) before `gh issue create` runs. `skills/shared/voting-protocol.md` OOS Reporting bullet is split into two paths (reviewer-voting vs. main-agent dual-write) and a unified-filing summary so the protocol document no longer overstates the "2+ YES" gate as the only path to a filed OOS issue. `/design` and `/review` are unchanged — their existing structured discovery-time writes already follow the canonical pattern and standalone behavior is out of scope for this PR. Closes #118.

## [3.3.8] - 2026-04-18

### Fixed

- `scripts/drop-bump-commit.sh` Guard 4 `ALLOWED_TWO` constant reordered to match `sort`'s ASCII byte ordering (`.claude-plugin/plugin.json` before `CHANGELOG.md`, since `.`=0x2E < `C`=0x43), so the two-file bump+CHANGELOG shape produced by `/implement` Step 8a now matches and the `DROPPED=true` happy path is reachable. Previously the constant's letter-before-dot order meant Guard 4 always rejected two-file bump commits, forcing `/implement`'s Rebase + Re-bump Sub-procedure down the expensive `rebase-push.sh` + Phase 1–4 conflict fallback every time `main` advanced during the CI+merge loop. Also pins the `sort` invocation to `LC_ALL=C` so the documented ASCII-order invariant is enforced rather than assumed, adds a comment on the `ALLOWED_*` constants warning future editors not to "fix" the order back to alphabetical-by-filename, and updates the file header's Guard 4 bullet to state the real contract (`plugin.json`, optionally together with `CHANGELOG.md`). Fixes #117.

## [3.3.7] - 2026-04-18

### Changed

- `/design` Step 2a.5 dialectic debater prompts rewritten per research-backed best practices (Anthropic prompt-engineering docs, multi-agent-debate literature, Karpathy guidance). Each debater template now opens with a narrow role-with-stakes preamble; requires a steelman clause before arguing; demands `file:line` evidence grounding via Read/Grep/Glob at argument time; emits structured tagged output (`<claim>`, `<evidence>`, `<strongest_concession>`, `<counter_to_opposition>`, `<risk_if_wrong>`) with a terminal `RECOMMEND: THESIS|ANTI_THESIS` token; enforces a 250-word prose cap; names anti-patterns to avoid (sycophancy, consensus collapse, vagueness, straw-manning, speculative future-proofing); and tells debaters to "assume the opponent will read your argument." The antithesis template additionally carries the sharpened proportionality instruction. Both templates wrap `{SYNTHESIS_TEXT}` and `{DECISION_BLOCK}` in namespaced `<debater_synthesis>` / `<debater_decision>` delimiters (mirrors the existing `<reviewer_*>` convention) with a split three-clause instruction that preserves required output-tag emission while blocking copy-through from the reference blocks. The orchestrator quorum rule in Step 2a.5 now gates binding resolution on presence of all 5 tags, normalized `RECOMMEND:` line detection (trim + strip `**...**` / `__...__` wrappers before prefix match), case-insensitive enum check with underscore preservation, role-vs-RECOMMEND consistency, a `file:line` citation in `<evidence>`, and retained substantive-output predicate — all as a conjunct. A new winner-selection rule picks the side whose argument is more compelling; resolution maps THESIS→{CHOSEN}, ANTI_THESIS→{ALTERNATIVE}. Fallback warnings are reason-coded. `dialectic-resolutions.md` schema, `skills/shared/voting-protocol.md`, scripts, and all downstream consumers are unchanged. Closes #97.

## [3.3.6] - 2026-04-18

### Changed

- OOS (out-of-scope observation) scoring is now asymmetric (reward-only): accepted OOS items (2+ YES votes) still earn +1 point and file a GitHub issue, but unanimously-rejected OOS now scores 0 instead of -1. Aligns scoring with the reviewer-side instruction to "surface OOS freely" so reviewers are never penalized when voters dismiss an observation in good faith. Updates the canonical scoring table in `skills/shared/voting-protocol.md`, both narrative mirrors (`docs/point-competition.md`, `docs/voting-process.md`), and both runtime reviewer Competition notices (`skills/design/SKILL.md`, `skills/review/SKILL.md`). Also qualifies the EXONERATE "spares a penalty" wording across those files — penalty-sparing now applies only to in-scope findings. Adds a one-sentence OOS quality-gate hint to the voter prompt template so voters can distinguish file-worthy from dismissible observations. Fixes #102.

## [3.3.5] - 2026-04-18

### Changed

- Collapsed `/research` Step 2 (Findings Validation) and `/loop-review` Step 3c (Slice Review) from their dual-Codex / 5-reviewer panels to the canonical 3-reviewer panel used by `/design`, `/review`, and `/implement`: 1 Claude Code Reviewer subagent + 1 Codex + 1 Cursor. `/loop-review` additionally gains a same-slice Runtime Timeout Fallback so a failed external is replaced in-slice (not just in future slices), and switches its collect call to the same dynamic `COLLECT_ARGS=()` pattern `/research` uses so unavailable externals no longer cause sentinel-wait timeouts. Output files consolidate to `codex-validation-output.txt` (research) and `codex-output-slice-N.txt` (loop-review); negotiation files become `codex-negotiation-*.txt` / `cursor-negotiation-*.txt`. Shared docs updated so every reviewer panel in the repo shares the `Code` / `Codex` / `Cursor` attribution shape. Closes #85.

## [3.3.4] - 2026-04-18

### Fixed

- `/fix-issue` auto-pick mode no longer silently caps candidate scanning at the first 100 open issues. `skills/fix-issue/scripts/fetch-eligible-issue.sh` now calls `gh api --paginate repos/{owner}/{repo}/issues?state=open&per_page=100`, filtering PRs out with `select(.pull_request == null)` and slurping the JSONL stream with `jq -s` before the oldest-first sort. Matches the pagination pattern already used by `open_blockers` and the comment fetchers in the same file. Fixes #110.

## [3.3.3] - 2026-04-18

### Fixed

- `docs/review-agents.md` Quality gate paragraph now faithfully summarizes the canonical uniform gate from `skills/shared/reviewer-templates.md` (applies to both In-Scope and Out-of-Scope findings; three-part check of justification, proportionality, and concrete evidence; plus an OOS-specific requirement of a concrete failure mode or breakage path). Previously the doc described the pre-Phase-1 behavior (in-scope only, OOS exempt), directly contradicting reviewer behavior. Closes #103.

## [3.3.2] - 2026-04-18

### Fixed

- `/issue` Step 6 now emits a dedicated URL-only success line (`✅ Created issue — <ISSUE_URL>`) when `gh issue view` fails to resolve the new issue's number. Previously the resolution-failure path routed to Step 6 with only `$ISSUE_URL` available, but all three existing variants embedded `#<ISSUE_NUMBER>` and produced a malformed `✅ Created issue # — <URL>` line. Step 4's cross-reference is updated to point at the new variant.

## [3.3.1] - 2026-04-18

### Changed

- Strengthened `/implement` Step 2 prompt with six research-backed edits to `skills/implement/SKILL.md`: (1) quick-mode inline plan schema at SKILL.md:185 now requires testing strategy and failure modes to match `/design`'s output; (2) new root-cause-discipline bullet in Step 2; (3) new incremental-`/relevant-checks` bullet in Step 2; (4) mode-aware Step 2 lead-in sentence; (5) auto-mode clause at SKILL.md:230 now instructs the agent to log mid-coding interpretations under the "Implementation Deviations" PR-body section; (6) TDD bullet tail now includes a concrete non-TDD verification fallback. Closes #96.

## [3.3.0] - 2026-04-18

### Added

- New `/create-skill` public slash command (`skills/create-skill/SKILL.md`) that scaffolds a new larch-style skill from a name and a description, then delegates to `/implement --quick --auto` for the full pipeline (code review, version bump, PR). Default writes under `.claude/skills/<name>/` (consumer mode); `--plugin` writes under `skills/<name>/` for plugin-dev mode. `--multi-step` selects a multi-step scaffold template; default is minimal single-step. `--merge` and `--debug` forward to `/implement`.
- New scripts under `skills/create-skill/scripts/`: `parse-args.sh` (flag + positional parsing, leading-`/` strip), `validate-args.sh` (name regex + reserved-name union of Anthropic `{anthropic, claude}` ∪ larch's static list ∪ dynamic `${CLAUDE_PLUGIN_ROOT}/skills` ∪ dynamic `$PWD/.claude/skills`, all case-insensitive; description length, no XML tags, no backticks, no `$(...)`, no heredoc terminators, no newlines or control chars), `render-skill-md.sh` (heredoc-in-shell renderer with atomic `.tmp` + `mv`, two path tokens for consumer-vs-plugin mode, YAML-safe description escaping including backslashes), and `post-scaffold-hints.sh`.
- New entry in `SECURITY.md` documenting `/create-skill`'s description-sanitization design (which patterns are rejected and why they matter for YAML-frontmatter and heredoc-rendering safety).
- Two new permission entries in `.claude/settings.json` (`Bash($PWD/skills/create-skill/scripts/*)` and `Skill(create-skill)`) in strict ASCII code-point order.

### Changed

- `README.md` Skills catalog and feature matrix now list `/create-skill`.

## [3.2.0] - 2026-04-18

### Added

- New `§5 Security` focus area in the Code Reviewer archetype (`skills/shared/reviewer-templates.md` + generated `agents/code-reviewer.md`) covering injection, authN/authZ, secret scanning (with regex hints: `.env`, `AWS_`, `PRIVATE_KEY`, `sk-`, `Authorization: Bearer`), crypto, deserialization, SSRF, path traversal, and dependency CVEs. Review findings may now be tagged with a new `security` focus-area value, extending the enum from 4 to 5 tags (all four prior tags remain valid).
- New `## Adapt scope` section in the archetype instructing reviewers to tailor reviews to doc-only / test-only / revert / rename-only / large-diff / generated-code PRs, plus a security-elevation trigger for changes touching auth, secrets, shelling out, parsing, deserialization, permissions, network boundaries, cryptography, or untrusted input.
- New `## Calibration examples` section with two synthetic few-shot examples (one well-formed `**Important**` finding with evidence, one false-positive suppression) using fake `example://` paths and an explicit "evidence for real findings must come ONLY from the provided review context" instruction.
- New `scripts/generate-code-reviewer-agent.sh` bash generator that emits `agents/code-reviewer.md` from `skills/shared/reviewer-templates.md` (extracts body between `<!-- BEGIN/END GENERATED_BODY -->` markers, strips outer fence by position, substitutes `{REVIEW_TARGET}` = `"code, plans, or conflict resolutions"`, omits `{CONTEXT_BLOCK}`, and performs section-keyed replacement of the two `{OUTPUT_INSTRUCTION}` placeholders). Supports `--check` mode for CI drift detection.
- New `agent-sync` CI job in `.github/workflows/ci.yaml` that runs the generator in `--check` mode and asserts that both the backticked enum (in template + agent + `docs/review-agents.md`) and the unquoted slash-separated enum (in voting-panel SKILL.md prompts) include `security`.

### Changed

- `{CONTEXT_BLOCK}` is now wrapped in namespaced `<reviewer_*>` XML tags (`<reviewer_diff>`, `<reviewer_plan>`, `<reviewer_feature_description>`, `<reviewer_file_list>`, `<reviewer_commits>`, `<reviewer_research_question>`, `<reviewer_research_findings>`, `<reviewer_conflict_context>`) with a prepended instruction sentence that the tags are literal input delimiters. Applied at every call site in `skills/review/SKILL.md`, `skills/design/SKILL.md`, `skills/implement/SKILL.md` (quick-mode + conflict-review), and `skills/research/SKILL.md`. The wrapping is a model-level prompt-injection mitigation, not a parser-enforced security boundary — see `docs/review-agents.md` and `SECURITY.md` for the residual-risk discussion.
- `agents/code-reviewer.md` is now a **generated artifact** — hand edits are forbidden and CI enforces sync with `skills/shared/reviewer-templates.md`. `AGENTS.md` is updated to replace the previous "edit both files in lockstep" rule with "edit the template; regenerate the agent."
- `skills/review/SKILL.md`, `skills/design/SKILL.md`, and `skills/implement/SKILL.md` inline Cursor/Codex prompts now include `(5) Security: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs` and enumerate all five focus-area tags for reviewers.
- `docs/review-agents.md`, `docs/agents.md`, `README.md`, and `SECURITY.md` updated to document the new Security lane, the generator-enforced single source of truth, and the XML wrapping with its residual-risk framing.
- `skills/loop-review/SKILL.md` and `skills/research/SKILL.md` external-reviewer prose is intentionally left on the 4-perspective taxonomy (Negotiation Protocol) in this release; editorial rebalancing to the 5-tag vocabulary is tracked as a focused follow-up. The Claude subagent lanes in those skills inherit the 5-tag archetype automatically via `subagent_type: code-reviewer`.

## [3.1.1] - 2026-04-18

### Changed

- Raised the `/implement --quick` single-reviewer code-review loop cap from 5 rounds to 7. The quick-mode re-review gate (`skills/implement/SKILL.md` Step 5.8) now loops while `round_num <= 7` and prints the non-convergence warning when `round_num > 7`; the `--quick` flag description, Step 5 header, body, warning copy, execution-issues log text, and the quick-mode PR-body guidance for the Code Review Voting Tally are updated in lockstep. Reviews that previously exhausted the cap with unresolved findings now have two additional iterations to converge before the warning is emitted. `/review`'s independent normal-mode 5-round cap is unchanged.

## [3.1.0] - 2026-04-18

### Added

- New `/issue` skill (`skills/issue/SKILL.md`) that creates a GitHub issue in the current repository from a free-form description. With the optional `--go` flag, it additionally posts a final `GO` comment on the new issue so it becomes immediately eligible for `/fix-issue` automation without manual approval. `skills/alias/SKILL.md` now reserves the `issue` name so project-level aliases cannot collide with the shipped skill. README install blurb, Skills summary row, and skills table updated to document `/issue`.

## [3.0.7] - 2026-04-18

### Changed

- `/fix-issue` now skips candidates with currently-open blocking dependencies. After an issue passes the `GO` sentinel check, `fetch-eligible-issue.sh` queries GitHub's native issue-dependencies API (`repos/{owner}/{repo}/issues/{N}/dependencies/blocked_by`); if any blocker is still in the `open` state, auto-pick mode continues scanning and explicit `--issue` mode reports ineligible with the blocker list. The dependency lookup uses `gh api --paginate --jq` so results across multiple pages are merged correctly. API errors (404 on repos without the feature, 5xx, transient gh failures) degrade silently to the prior GO-only behavior so dependency-API availability never hard-blocks the automation; the degradation is documented under the skill's Known Limitations.

## [3.0.6] - 2026-04-18

### Changed

- Code Reviewer archetype (`agents/code-reviewer.md` and `skills/shared/reviewer-templates.md`) tuned with severity tags (`**Important**` / `**Nit**` / `**Latent**`, with a PR-introduced-defect tiebreaker), a conservatism header ("when in doubt, say nothing"), an explicit "Do NOT report" exclusion list, a context-sensitive proof-before-report clause for `**Important**` findings (failing scenario or concrete breakage path), a Nit cap of 5 with a required "count plus categories" overflow summary, a tightened Quality gate that applies uniformly to In-Scope and Out-of-Scope findings with review-mode-appropriate evidence (file:line for code review; plan/validation anchors otherwise), Style consistency and red-green-TDD-that-should-have-happened both demoted to `**Nit**`-only, Backward compatibility and Thread safety folded into §2 Breaking changes and §3 Race conditions via cross-references that preserve legacy vocabulary, and the 5-step "Review process" softened into "Review priorities (in order, not a sequence)" to reduce premature stopping or anchoring. Phase 1 is Claude-lane-only — external Codex/Cursor reviewers still run their inline prompts from the individual skill SKILL.md files, so severity tags and the conservatism/exclusion rules reach Claude reviewers and Claude fallbacks only; external-lane alignment is deferred to a follow-up phase. Closes #91.

## [3.0.5] - 2026-04-18

### Changed

- `/research` refactored from a 5+5 lane composition to 3+3. Phase 1 (Research) now launches 3 agents — Claude inline + Cursor + Codex — all running a single uniform `RESEARCH_PROMPT` that requires alternative perspectives, edge cases/gaps, architectural patterns, and risks/feasibility. Phase 2 (Validation) now launches 3 lanes — Codex deep + Codex broad + Cursor generic. Claude Code Reviewer subagent fallbacks preserve the 3-lane invariant in each phase when an external tool is unavailable, with per-slot attribution (Cursor-unavailable → 1 generic Claude lane; Codex-unavailable → 2 Claude lanes, deep + broad). Both phases build a `COLLECT_ARGS` list from only actually-launched externals and skip `collect-agent-results.sh` entirely when zero externals are launched. Runtime external timeouts trigger an immediate same-phase Claude fallback so the 3-lane invariant holds at synthesis/negotiation time. Docs, diagram, and progress-reporting examples are synced across `README.md`, `docs/agents.md`, `docs/review-agents.md`, `docs/workflow-lifecycle.md`, `docs/external-reviewers.md`, `docs/collaborative-sketches.md`, `skills/shared/progress-reporting.md`, `skills/shared/voting-protocol.md`, and `skills/research/diagram.svg`.

## [3.0.4] - 2026-04-18

### Changed

- `/implement --quick` code review now uses a single-reviewer loop with the Cursor → Codex → Claude Code Reviewer subagent fallback chain, re-reviewing up to 5 rounds when a round's fixes introduce significant changes. Previously, quick mode ran a single Claude subagent for one round with no re-review. The fallback chain re-evaluates per round so runtime timeouts cascade to the next tier. Step 0 now explicitly sets the `cursor_available`/`codex_available` mental flags consumed by the new Step 5 selection logic.

## [3.0.3] - 2026-04-18

### Fixed

- `/implement` and `/bump-version` no longer touch `$PWD/.git/`. The classify-bump.sh reasoning-log default path moved from `$PWD/.git/bump-version-reasoning.md` to `${TMPDIR:-/tmp}/bump-version-reasoning.md`, and `/implement` Step 8 now parses the absolute path from `classify-bump.sh`'s `REASONING_FILE=<path>` stdout line instead of reconstructing it from `IMPLEMENT_TMPDIR`. Fixes a permission-prompt storm that occurred when the Skill tool invocation lost the env var and `/implement` fell back to copying the reasoning file out of `.git/`.

### Added

- Ten git wrapper scripts under `scripts/` that replace direct `git` commands in `skills/implement/SKILL.md`: `git-current-branch.sh`, `git-amend-add.sh`, `git-force-push.sh` (with internal fetch/compare/retry recovery), `git-sync-local-main.sh`, `git-rebase-skip.sh`, `git-conflict-files.sh`, `git-show-stage.sh`, `git-checkout-ours.sh`, `git-stage.sh`, and `git-push.sh`. Each is pre-approved by `settings.json`'s `Bash($PWD/scripts/*)` rule, so invoking them does not trigger per-command permission prompts. `skills/implement/SKILL.md` updated at every call site (Step 1 branch capture, Step 8a CHANGELOG amend, Rebase + Re-bump Sub-procedure steps 3/4a/5/6, Conflict Resolution Procedure Phase 1 + Phase 4 Exit 3, Step 10/12c CI fix handlers).

## [3.0.2] - 2026-04-18

### Changed

- Renamed the top-level heading in `KARPATHY_CLAUDE.md` from `# CLAUDE.md` to `# KARPATHY_CLAUDE.md` to match the filename.

## [3.0.1] - 2026-04-18

### Added

- `KARPATHY_CLAUDE.md` at repo root — verbatim copy of Andrej Karpathy's coding guidelines (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution).
- `@KARPATHY_CLAUDE.md` include added to root `CLAUDE.md` after the existing `@AGENTS.md` include, loading the guidelines into developer context when working inside this repo.

## [3.0.0] - 2026-04-18

### Changed

- Reviewer consolidation: `/design` plan review, `/review` code review, and `/implement` Phase 3 conflict-review now run a unified 3-reviewer panel (1 Claude Code Reviewer subagent + 1 Codex + 1 Cursor) instead of the previous 5-reviewer panel (2 Claude + 2 Codex + 1 Cursor). `/implement` quick-mode drops from 2 Claude subagents to 1.
- Sketch phase composition changed from 3 Claude + 1 Cursor + 1 Codex to 1 Claude General + 2 Cursor + 2 Codex. The four non-general personalities (Architecture/Standards, Edge-cases/Failure-modes, Innovation/Exploration, Pragmatism/Safety) now live on the external slots (Cursor: Arch + Edge; Codex: Innovation + Pragmatism), with per-slot Claude fallbacks preserving the 5-agent invariant when a tool is unavailable.
- Unified Code Reviewer archetype in `skills/shared/reviewer-templates.md` replaces the previous Reviewer A (General) and Reviewer B (Deep Analysis) archetypes. The new archetype covers code quality, risk/integration, correctness, and architecture in one prompt with mandatory per-finding focus-area tagging.
- Voter 1 canonical label is now `Claude Code Reviewer subagent` in both `/design` and `/review` (previously split between Deep Analysis and General names).
- Attribution strings in round summaries and reviewer competition scoreboards collapse from `General / Deep-Analysis / Codex-General / Codex-Deep-Analysis / Cursor` to `Code / Codex / Cursor`.
- Output file paths for the single Codex review launch are now `codex-plan-output.txt` (design) and `codex-output.txt` (review); the old `codex-general-*` / `codex-deep-*` names are no longer emitted by these skills.
- `skills/research/SKILL.md` and `skills/loop-review/SKILL.md` retained a 5-reviewer composition under the Negotiation Protocol at this version; their two Claude lanes are attributed as `Code Reviewer (broad perspective)` and `Code Reviewer (deep perspective)`, both invoking the unified archetype. (`/research` was later refactored to a 3-lane composition — see subsequent changelog entries.)
- `scripts/agent-model-args.sh` gained a `--with-effort` opt-in flag. When passed, it emits `-c model_reasoning_effort="$EFFORT"` for Codex, where EFFORT resolves from `LARCH_CODEX_EFFORT` → `CLAUDE_PLUGIN_OPTION_CODEX_EFFORT` → default `high`. Default (no flag) behavior is unchanged — health probes and negotiation callers do not pass `--with-effort` and therefore remain at Codex's default effort.
- `.claude-plugin/plugin.json` adds `codex_effort` userConfig (default `high`). The plugin-level description is updated to reflect the new reviewer composition.

### Added

- New `agents/code-reviewer.md` agent definition (unified Code Reviewer archetype, model: sonnet, Read/Grep/Glob tools).
- New `LARCH_CODEX_EFFORT` environment variable and `codex_effort` plugin userConfig knob.

### Removed

- `agents/general-reviewer.md` and `agents/deep-analysis-reviewer.md` — replaced by the unified `code-reviewer` agent. **Migration note**: consumers that referenced `general-reviewer` or `deep-analysis-reviewer` directly (via `--agents` or subagent_type references in downstream docs/scripts) must switch to `code-reviewer`.

## [2.3.5] - 2026-04-17

### Added

- Integrated agnix linter for AI agent configuration validation (pre-commit hook, Makefile target, CI job)
- Created `.agnix.toml` config suppressing file-length rules and false positives for this plugin repo
- Fixed all agnix warnings in `AGENTS.md` and `.claude/settings.json`
- Added hook timeout to shipped `hooks/hooks.json` for consumer parity

## [2.3.4] - 2026-04-16

### Changed

- Split `CLAUDE.md` into a thin `@AGENTS.md` include and a new `AGENTS.md` with terse agent-generic editing guidance
- Upgraded agent-lint from v2.2.4 to v2.3.2 and aligned pre-commit, CI, and config syntax (`ignore` → `suppress`)

## [2.3.3] - 2026-04-15

### Added

- Added `agent-lint` v2.2.4 as a pre-commit hook with `--pedantic` flag
- Added `agent-lint` Make target for standalone invocation
- Aligned `--pedantic` flag across all agent-lint invocations (CI action, `/relevant-checks` post-check)

## [2.3.2] - 2026-04-15

### Changed

- Dropped the Description column from the Aliases table in README.md for a leaner two-column layout

## [2.3.1] - 2026-04-15

### Changed

- Changed `/imaq` `argument-hint` from `<feature-description>` to `<arguments>` to match `/im`, signaling that extra flags are forwarded to `/implement`
- Fixed `generate-alias.sh` to emit `<arguments>` as the argument-hint for newly generated aliases

## [2.3.0] - 2026-04-15

### Changed

- Added `.diag` diagnostic files to `run-external-agent.sh` for timeout, failure, and empty output cases
- Health check failure banners in `session-setup.sh` now include the specific cause of failure
- `collect-agent-results.sh` emits `FAILURE_REASON` field explaining why each non-OK reviewer failed
- Updated `external-reviewers.md` and `voting-protocol.md` to instruct including failure reasons in all user-facing messages

## [2.2.0] - 2026-04-15

### Added

- Migrated `/im` and `/imaq` aliases from project-level (`.claude/skills/`) to plugin-exported (`skills/`) so they ship to all consumers
- Added `Aliases` subsection in README.md Skills section documenting both shortcuts
- Added `/im` and `/imaq` to all skill inventory locations (README, CLAUDE.md, settings.json)
- Added `im` and `imaq` to `/alias` reserved-name list

## [2.1.3] - 2026-04-15

### Added

- `/imaq` project-level alias for `/implement --merge --auto --quick`
- `argument-hint` field emission in `generate-alias.sh` for agent-lint compliance

## [2.1.2] - 2026-04-14

### Added

- `/im` project-level alias for `/implement --merge`
- `Skill(im)` permission entry in `.claude/settings.json` for development harness consistency

## [2.1.1] - 2026-04-14

### Changed

- `/fix-issue` now accepts issue number or URL as a positional argument (e.g., `/fix-issue 42`) instead of requiring the `--issue` flag
- Deprecated `--issue` flag with backward compatibility and runtime deprecation warning
- Added guard against multiple positional arguments in `fetch-eligible-issue.sh`

## [2.1.0] - 2026-04-14

### Changed

- `/alias` now delegates to `/implement --quick --auto` for the full pipeline (code review, version bump, PR) instead of writing files directly
- Added `--merge` flag to `/alias` to optionally merge the PR after CI passes
- Renamed `claude-lint` CI job to `agent-lint` and upgraded to `zhupanov/agent-lint@v2`
- Renamed `claude-lint.toml` to `agent-lint.toml` and updated all references across codebase

## [2.0.10] - 2026-04-13

### Changed

- Replaced `▶` step start icon with `🔶` (large orange diamond) across all skills for improved visibility
- Added blockquote wrapping (`>`) to step start lines for color differentiation
- Updated all inline `Print:` directives to include full `> **🔶 ...**` format for consistency with the shared progress reporting contract

## [2.0.9] - 2026-04-13

### Changed

- Moved lock step before triage in `/fix-issue` (Step 2 → before read details and triage) to eliminate race conditions where concurrent runs could claim the same issue during triage
- Enhanced triage close to include detailed research summary explaining why the issue is no longer material
- Combined `update-body` + `close` into a single `issue-lifecycle.sh close --pr-url` call, eliminating a consecutive Bash call anti-pattern in Step 7
- Fixed `cmd_update_body` using `exit` instead of `return` for error paths, which would bypass `cmd_close`'s error guard when called as an internal function

## [2.0.8] - 2026-04-13

### Changed

- Replaced `▸` step start icon with `▶` (filled, more visible) across all skills
- Added 80-char `━` separator line and bold formatting for step start lines
- Expanded elapsed time to all terminal lines: `⏩`, `⏭️`, `❌` (status tables), and step-ending `⚠` — not just `✅`
- Clarified "step-ending ⚠" definition in progress reporting contract

## [2.0.7] - 2026-04-13

### Fixed

- Fixed multi-line description truncation in `scripts/create-oos-issues.sh` — the parser now accumulates continuation lines between `- **Description**:` and the next structured field, preserving full multi-line descriptions in filed GitHub issues

## [2.0.6] - 2026-04-13

### Changed

- Added elapsed time reporting to all `✅` completion indicators — step completion lines show `(<elapsed>)` and compact status tables show timing after each `✅`
- Defined elapsed time format rules in `skills/shared/progress-reporting.md` (central contract)
- Updated all `Print:` directives across all 7 skills to include `(<elapsed>)` placeholders

## [2.0.5] - 2026-04-13

### Changed

- Added deduplication to `create-oos-issues.sh` — fetches open issues before creating new ones and skips creation when a normalized-title match already exists
- Updated SKILL.md Step 9a.1 to document new `ISSUES_DEDUPLICATED` output field and dedup reporting in PR body

## [2.0.4] - 2026-04-13

### Changed

- Replaced OOS promotion with GitHub issue filing — accepted OOS items are filed as issues instead of being implemented in the PR
- Switched OOS scoring from floor-of-0 to symmetric -1/0/+1, matching in-scope finding scoring
- Added `scripts/create-oos-issues.sh` for automated OOS issue creation at PR time
- Updated voter prompt template with OOS-specific vote semantics and output format examples

## [2.0.3] - 2026-04-13

### Removed

- Deleted `scripts/validate-plugin-structure.sh` (25 bash validators) and `scripts/smoke-test.sh` wrapper, superseded by claude-lint
- Removed `plugin-structure` CI job; claude-lint is now the sole structural linter in CI
- Updated GitHub ruleset to require `claude-lint` instead of `plugin-structure`

## [2.0.2] - 2026-04-13

### Fixed

- Added 1-retry to Codex and Cursor health check probes to tolerate transient timeouts

## [2.0.1] - 2026-04-13

### Changed

- Added quality-improvement instructions across all reviewer archetypes: strengthened test coverage emphasis, TDD guidance for implementation, and a proportionality quality gate ("Is it justified? Is it over-engineered?") for reviewers, voters, and the antithesis agent

## [2.0.0] - 2026-04-13

### Changed

- **BREAKING**: Renamed `/fix-issues` skill to `/fix-issue` (singular) to match its single-iteration semantics
- Added `--issue <number-or-url>` flag to `/fix-issue` for targeting a specific GitHub issue instead of auto-picking the oldest eligible one

## [1.4.0] - 2026-04-13

### Added

- New `/fix-issues` skill that processes one approved GitHub issue per invocation: fetches issues with `GO` sentinel, triages against codebase, classifies complexity (SIMPLE/HARD), and delegates to `/implement`
- Added `claude-lint` to `/relevant-checks` validation pipeline (runs after plugin structure validation when available on PATH)

### Fixed

- Added explicit flag-parsing defaults to all 5 skill SKILL.md files to prevent cross-flag contamination where parsing one flag (e.g. `--merge`) could cause the agent to incorrectly set another (e.g. `auto_mode=true`). Each flag now has an explicit `Default:` sentinel and a shared preamble states all boolean flags default to `false` and are independent.

## [1.3.10] - 2026-04-13

### Fixed

- Fixed `mktemp`/`mv` failure when `--write-session-env /dev/null` or `--write-health /dev/null` is passed to session setup scripts. Both `mktemp` and `mv` fail on device nodes on macOS.

## [1.3.9] - 2026-04-13

### Changed

- Updated author/contact email from `sergey@zhupanov.com` to `zhupanov@yahoo.com` in plugin manifests and security policy.

## [1.3.8] - 2026-04-13

### Changed

- Cursor reviewer now defaults to `--model composer-2-fast` when `LARCH_CURSOR_MODEL` is unset, since `cursor agent` CLI does not honor `~/.cursor/cli-config.json` and would otherwise fall back to a potentially rate-limited model.

## [1.3.7] - 2026-04-13

### Added

- `LARCH_CURSOR_MODEL` and `LARCH_CODEX_MODEL` environment variables for controlling which models Cursor and Codex use as external reviewers.
- New `scripts/agent-model-args.sh` script that centralizes model flag injection for both tools.
- Plugin `userConfig` entries (`cursor_model`, `codex_model`) as alternative to environment variables.
- Prominent `═══` banner-style warnings in terminal output when Cursor or Codex health checks fail.

## [1.3.6] - 2026-04-13

### Fixed

- Resolved all claude-lint errors: added trigger context to skill descriptions (S017), shortened long descriptions to ≤250 chars (S015), and rewrote descriptions in third person (S016).
- Removed `continue-on-error: true` from claude-lint CI step now that all errors are resolved.

### Added

- `claude-lint.toml` config file disabling the `body-too-long` rule for intentionally long SKILL.md bodies.

## [1.3.5] - 2026-04-13

### Added

- CI job running `claude-lint` via `zhupanov/claude-lint@v1` GitHub Action with explicit `github-token` for version resolution.

## [1.3.4] - 2026-04-12

### Changed

- Replaced per-step emoji progress lines with breadcrumb-style step paths across all 5 skill SKILL.md files (e.g., `▸ 1.2a: design plan | sketches` instead of `🤝 Step 1.2a — Collaborative sketches...`).
- Created `skills/shared/progress-reporting.md` shared formatting contract defining icon taxonomy, breadcrumb format, and `--step-prefix` `::` encoding.
- Extended `--step-prefix` to carry both numeric prefix and textual breadcrumb path (e.g., `"1.::design plan"`), with backward-compatible fallback for numeric-only values.
- Added Step Name Registry tables (<=20-char short names per step) to all 5 skill SKILL.md files.
- Preserved `⏭️`/`⏩` semantic distinction for precondition vs. sub-step skips.

## [1.3.3] - 2026-04-12

### Changed

- Renamed "grilling"/"grill" terminology to "discussion"/"discuss" throughout `/design` skill, `docs/workflow-lifecycle.md`, and prior CHANGELOG entries for clarity.

## [1.3.2] - 2026-04-12

### Changed

- Consolidated skill setup: all 5 skills now call `session-setup.sh` with `--check-reviewers` instead of separate `create-session-tmpdir.sh` + `check-reviewers.sh` + health file write sequences.
- Created `collect-agent-results.sh` to consolidate post-launch reviewer output validation, retry, and health tracking across all skills.
- Extended `session-setup.sh` with `--skip-preflight`, `--check-reviewers`, `--write-health`, `--write-session-env` flags.
- Added `.meta` file support to `run-external-agent.sh` for retry capability in `collect-agent-results.sh`.

### Removed

- Deleted `create-session-tmpdir.sh` (all callers migrated to `session-setup.sh`).

## [1.3.1] - 2026-04-12

### Changed

- Removed pure "done" step-completion announcements from `/implement`, `/design`, and `/review`; only result-bearing completions (with counts/outcomes) and conditional-skip markers are preserved.
- Added internal `--step-prefix` flag to `/design` and `/review` for hierarchical step numbering when called from `/implement` (e.g., Step 1.0, Step 5.2).
- Added internal `--branch-info` flag to `/design` to skip redundant `create-branch.sh --check` when invoked from `/implement`.
- Suppressed rebase-skip messages (`⏩ Rebase skipped — ...`) in non-debug mode in `/implement`.

## [1.3.0] - 2026-04-12

### Added

- External reviewer health probe: `check-reviewers.sh --probe` sends a trivial prompt to each external reviewer (Codex/Cursor) with a 60-second timeout at session startup, catching outages before wasting time on long review timeouts.
- Runtime timeout fallback: when an external reviewer times out during any step, it is replaced by a Claude subagent with similar persona for all subsequent invocations in the session.
- Cross-skill health propagation: reviewer health state flows from `/implement` → `/design` → `/review` via `--session-env` and structured health status files.
- `--session-env <path>` flag for `/review` skill (MINOR: new flag in `argument-hint`).
- `--skip-codex-probe` / `--skip-cursor-probe` flags for `check-reviewers.sh` to avoid re-probing tools already known unhealthy.

### Changed

- `write-session-env.sh`: added `--codex-healthy`/`--cursor-healthy` flags, atomic writes via temp+mv, conditional health key emission.
- `session-setup.sh`: parses and re-emits `CODEX_HEALTHY`/`CURSOR_HEALTHY` from caller-env.
- `external-reviewers.md`: renamed "Binary Check" to "Binary Check and Health Probe", added "Runtime Timeout Fallback" section.

## [1.2.0] - 2026-04-12

### Added

- `--debug` flag for all 5 workflow skills (`/implement`, `/design`, `/review`, `/research`, `/loop-review`). Default (no `--debug`) uses compact output: empty Bash tool descriptions, suppressed explanatory prose, compact reviewer status tables. `--debug` restores verbose output.
- Compact reviewer status table in `/review`, `/design`, and `/research` — replaces per-reviewer individual completion messages with a single reprinted line showing all reviewer statuses.
- Progress Reporting sections for `/review` and `/loop-review` (previously missing).
- Auto-propagation: `/implement` forwards `--debug` to `/design` and `/review`; `/loop-review` forwards to `/implement`.

## [1.1.12] - 2026-04-12

### Added

- Two-round design discussion steps in `/design` skill: Step 1d (pre-sketch, scope/requirements interrogation) and Step 3.5 (post-review, covers decisions not addressed in round 1 or deemed suboptimal by reviewers). Both rounds walk the decision tree one question at a time with recommended answers, explore the codebase first, and are skipped in `--auto` mode.
- New `accepted-plan-findings.md` artifact written during plan review finalization, bridging Step 3 and Step 3.5.

### Changed

- Updated `docs/workflow-lifecycle.md` mermaid diagram to include both discussion nodes in the design phase.

## [1.1.11] - 2026-04-12

### Added

- Validators 24-25 in `validate-plugin-structure.sh`: every `userConfig` entry must have a non-empty `title` string field (V24) and a non-empty `type` string field (V25).

## [1.1.10] - 2026-04-12

### Fixed

- Added missing `title` and `type: "string"` fields to all three `userConfig` entries in `plugin.json` to conform to the Claude CLI plugin manifest schema.

## [1.1.9] - 2026-04-10

### Fixed

- Moved V23 (`validate_userconfig_sensitive_type`) function definition to after V22 to match numeric and `main()` call order.
- Updated `smoke-test.sh` advisory comment to remove stale `$schema`/`description` examples.

## [1.1.8] - 2026-04-10

### Fixed

- V23: extracted from V18 into standalone `validate_userconfig_sensitive_type()` function with own `main()` call, matching the 1-function-per-validator pattern.

### Removed

- Removed `$schema` and top-level `description` from `marketplace.json` — rejected by Claude CLI schema validator. Removed corresponding V12 checks.

## [1.1.7] - 2026-04-10

### Added

### Changed

- Enhanced V16 with bidirectional count check (reviewer-template sections must match agent file count).
- Enhanced V18 with `sensitive` field boolean type validation.
- Narrowed V22 scope to only the Canonical sources section of CLAUDE.md.
- Improved V20 key normalization to handle camelCase and kebab-case keys.

## [1.1.6] - 2026-04-09

### Added

- Four new validators (15-18) in `validate-plugin-structure.sh`: shared markdown reference integrity, agent-template alignment ("Derived from" marker), email format validation, userConfig structure validation.

### Changed

- Cleaned `.claude/settings.json`: removed repo-specific entries (gcloud, kubectl, argocd, K8S_WORK, KUBECONFIG, codeql, temporal, Go tooling, etc.) and PostToolUse auto-goimports hook. Kept `bypassPermissions` for development.
- Deduplicated CI: removed standalone `validate-plugin-structure.sh` step, kept only `smoke-test.sh` as sole entry point.
- Generified `loop-review/SKILL.md`: replaced Go-specific partition examples and file extensions with language-agnostic alternatives across both Step 1 discovery and Step 3b collection.

### Removed

- `scripts/auto-goimports.sh` — Go-specific PostToolUse hook no longer referenced.

## [1.1.5] - 2026-04-09

### Added

- Dialectic debate step (Step 2a.5) in `/design` skill: structured thesis/antithesis debates on contested decisions between synthesis and plan writing.
- Structured contested-decisions schema with `NO_CONTESTED_DECISIONS` sentinel, debate quorum rule, and binding resolution format.
- Documentation for the dialectic debate phase in `docs/collaborative-sketches.md` and `docs/workflow-lifecycle.md`.

## [1.1.4] - 2026-04-09

### Added

- `SECURITY.md` with minimal security policy, trust model, and external tool delegation documentation.
- `scripts/smoke-test.sh` validation-only smoke test wrapping `validate-plugin-structure.sh` plus advisory `claude plugin validate .`.
- Three new validators (12-14) in `validate-plugin-structure.sh`: marketplace enriched metadata, plugin.json enriched metadata, SECURITY.md presence.
- Prerequisites section in `README.md` split by use case (installation, workflow automation, optional integrations, contributor development).
- `--admin` merge behavior documentation in `README.md` with safety invariants.
- `/relevant-checks` consumer dependency guidance with setup instructions in `README.md`.

### Changed

- Fixed fallback behavior documentation in `docs/external-reviewers.md` and `docs/collaborative-sketches.md` to accurately describe Claude replacement agents maintaining constant participant counts and step-function voting thresholds.
- Replaced dangling cross-references to non-existent `/admin-upgrade-clients` and `/admin-add-user` skills in `scripts/merge-pr.sh` and `skills/implement/SKILL.md` with canonical implementation notes.
- Updated `CLAUDE.md` to reference 14 validators, document `SECURITY.md` as a protected file, and note `userConfig` env var convention.

## [1.1.3] - 2026-04-09

### Added

- `/implement` Step 8a: automatically updates `CHANGELOG.md` (if present) with a brief summary after the version bump, amending it into the bump commit.
- Backfilled CHANGELOG entries for versions 1.0.3 through 1.1.2.

### Changed

- Updated `drop-bump-commit.sh` Guard 4 to accept `CHANGELOG.md` alongside `plugin.json` in the bump commit, preventing re-bump failures when Step 8a has amended the changelog.
- Added CHANGELOG re-update (step 4a) to the Rebase+Re-bump sub-procedure so changelog entries survive rebases.

## [1.1.2] - 2026-04-09

### Changed

- Added `actions/cache@v4` for pre-commit tool cache in CI, reducing lint job time from ~44s to ~2s on cache hits.
- Flattened `skills/shared/larch/` to `skills/shared/` and updated all path references across 14 files.

## [1.1.1] - 2026-04-09

### Changed

- Increased external reviewer timeouts from 15 to 30 minutes (review/plan review) and 10 to 20 minutes (sketch/voting).
- Added Claude subagent fallbacks for all skills when Cursor/Codex are unavailable, ensuring total reviewer count (5) and voter count (3) remain constant.

## [1.1.0] - 2026-04-09

### Added

- `/alias` skill for creating project-level alias shortcuts that forward to existing larch skills with preset flags. Generates `.claude/skills/<name>/SKILL.md` and commits.

## [1.0.6] - 2026-04-09

### Changed

- Switched `.claude/settings.json` to `bypassPermissions` mode for local development.
- Fixed CLAUDE.md shipped-vs-runtime classification for supplementary files.

## [1.0.5] - 2026-04-09

### Added

- `CLAUDE.md` with editing-agent invariants, repository layout documentation, golden rules for edits, and canonical source references.

## [1.0.4] - 2026-04-09

### Changed

- `/implement` now re-runs `/bump-version` after every rebase in Steps 10 and 12 (the Rebase + Re-bump Sub-procedure), ensuring the merged version reflects `origin/main` at merge time rather than at PR-creation time.

## [1.0.3] - 2026-04-09

### Added

- Plugin structure validator (`scripts/validate-plugin-structure.sh`) with 11 validators covering manifests, frontmatter, path hygiene, script references, executability, and dead-script detection.
- Extended `/relevant-checks` to run the plugin structure validator after pre-commit passes.

## [1.0.2] - 2026-04-08

### Removed

- **Temporary compatibility symlinks introduced in v1.0.1.** Deleted `scripts/larch` (a directory of per-file symlinks pointing back into `../scripts/`, added so that cached skill-prompt references to `${CLAUDE_PLUGIN_ROOT}/scripts/larch/<script>.sh` would still resolve to `${CLAUDE_PLUGIN_ROOT}/scripts/<script>.sh` during the v1.0.1 migration session) and `.claude/scripts/generic/larch` (a symlink pointing at `../../../scripts`, added so that cached `.claude/settings.json` PreToolUse/PostToolUse hook command paths would keep resolving during the migration session). Also removed the now-empty parent directories `.claude/scripts/generic/` and `.claude/scripts/`. The `.claude/settings.json` hook commands were already rewritten in v1.0.1 to `$PWD/scripts/block-submodule-edit.sh` and `$PWD/scripts/auto-goimports.sh`, and all SKILL.md path references were flattened to `${CLAUDE_PLUGIN_ROOT}/scripts/` — so these compatibility shims have no remaining consumers once sessions have restarted. The v1.0.1 follow-up is now complete.
- Corresponding assertions in the `.github/workflows/ci.yaml` `plugin-structure` job that verified the existence of the two compatibility shims.

## [1.0.1] - 2026-04-08

### Added

- `/bump-version` private skill (`.claude/skills/bump-version/`). Classifies and applies a semantic version bump based on the branch diff against `origin/main`. **Only inspects the public plugin surface** (`skills/**` and `agents/**`); changes under `.claude/**`, `scripts/**`, `hooks/**`, `docs/**`, `.github/**`, `CHANGELOG.md`, etc. default to PATCH. Uses deterministic shell + `jq` heuristics (MAJOR on skill/agent deletion or rename, `name:` frontmatter change, or flag removal; MINOR on new skill/agent or new flag) with an **escalation-only** caveat clause: after the classifier runs, the main agent may escalate PATCH → MINOR → MAJOR if a behavioral change would be judged backward-incompatible by a reasonable client, but may never downgrade. The classifier is idempotent — it detects an already-bumped branch (via `^Bump version to X.Y.Z$` commit subject) and emits `BUMP_TYPE=NONE` to skip double-bumps. Writes decision reasoning to `${IMPLEMENT_TMPDIR:-$PWD/.git}/bump-version-reasoning.md` for embedding in the PR body.
- `<details><summary>Version Bump Reasoning</summary>` section in `/implement` Step 9a PR body template, populated from the reasoning file written by `/bump-version`.

### Changed

- **Flattened scripts layout.** Moved all 38 scripts from `scripts/larch/*` to `scripts/*` and rewrote every `${CLAUDE_PLUGIN_ROOT}/scripts/larch/` reference across skill docs (`skills/{design,implement,review,research,loop-review}/SKILL.md`), shared docs (`skills/shared/larch/{external-reviewers,voting-protocol}.md`), `hooks/hooks.json`, `.claude/settings.json`, and `.github/workflows/ci.yaml`. Added a temporary compatibility shim `scripts/larch/` (a directory of 38 per-file symlinks, each pointing back into `../scripts/` — e.g. `scripts/larch/session-setup.sh -> ../session-setup.sh`) to preserve path resolution for in-flight `/implement` sessions whose cached skill prompts still reference the old path. To be removed in a follow-up PR.
- **Removed legacy `.claude/` compatibility symlinks.** Deleted `.claude/skills/{design,implement,review,research,loop-review,shared}` and `.claude/agents/{deep-analysis-reviewer,general-reviewer}.md`. The plugin is discovered via `${CLAUDE_PLUGIN_ROOT}` when launched with `claude --plugin-dir .` or via the local marketplace, so these legacy symlinks are no longer load-bearing. `.claude/skills/` remains as a real directory for private repo-specific skills (`relevant-checks`, `bump-version`).
- **Repointed `.claude/scripts/generic/larch`** from `../../../scripts/larch` to `../../../scripts` so that cached hook command paths in the running Claude Code session (loaded at startup from `.claude/settings.json`) continue to resolve to `scripts/block-submodule-edit.sh` and `scripts/auto-goimports.sh` after the scripts migration. To be removed in a follow-up PR after all sessions have restarted.
- **Updated `.claude/settings.json`.** Rewrote PreToolUse/PostToolUse hook command paths from `$PWD/.claude/scripts/generic/larch/*` to `$PWD/scripts/*`. Consolidated the Bash permission allowlist: replaced `Bash($PWD/scripts/larch/*)` and `Bash($PWD/.claude/scripts/generic/larch/*)` with `Bash($PWD/scripts/*)`. Added `Skill(bump-version)` and `Bash($PWD/.claude/skills/bump-version/scripts/*)` for the new skill. Removed stale entries for `$PWD/.claude/skills/implement/scripts/*` and `$PWD/.claude/skills/loop-review/scripts/*` (the underlying symlinks were deleted).
- **Simplified CI `plugin-structure` job** (`.github/workflows/ci.yaml`). Removed the `.claude/skills/*` and `.claude/agents/*.md` symlink verification loop. Replaced the `scripts/larch/block-submodule-edit.sh` path check with `scripts/block-submodule-edit.sh`. Added checks for the two remaining compatibility symlinks (`scripts/larch` and `.claude/scripts/generic/larch`).
- **Updated `docs/agents.md` and `docs/review-agents.md`** to reference `agents/*.md` and `skills/shared/larch/reviewer-templates.md` instead of the deleted `.claude/*` paths.

## [1.0.0] - 2026-04-08

Initial release of larch as a Claude Code plugin.

### Added

- `.claude-plugin/plugin.json` manifest declaring the plugin name, version, and metadata.
- `.claude-plugin/marketplace.json` local marketplace catalog for `claude plugin marketplace add .`.
- `hooks/hooks.json` registering a PreToolUse hook that runs `block-submodule-edit.sh` for Edit and Write tool calls. The hook prevents Claude Code from editing files inside any git submodule of the user's repo.
- `CHANGELOG.md` (this file).
- New CI job `plugin-structure` that validates the plugin layout without requiring the `claude` CLI.

### Changed

- **Repo restructured for plugin layout.** Skills, agents, and scripts have moved from `.claude/` to the repo root:
  - `.claude/skills/{design,implement,review,research,loop-review,shared}` → `skills/{...}`
  - `.claude/agents/*.md` → `agents/*.md`
  - `.claude/scripts/generic/larch/*` → `scripts/larch/*`
  - Symlinks under `.claude/` (`.claude/skills/*`, `.claude/agents/*`, `.claude/scripts/generic/larch`) preserve the legacy paths for existing tooling and for the private `/relevant-checks` skill.
- Path references in plugin-exported SKILL.md files and shared docs rewritten from `$PWD/.claude/scripts/generic/larch/` and `` `.claude/skills/shared/larch/`` to `${CLAUDE_PLUGIN_ROOT}/scripts/larch/` and `${CLAUDE_PLUGIN_ROOT}/skills/shared/larch/`. Paths in `.claude/skills/implement/` and `.claude/skills/loop-review/` also switched to `${CLAUDE_PLUGIN_ROOT}/skills/{implement,loop-review}/scripts/`.
- `.claude/settings.json` gained three defensive Bash permissions to cover the new canonical script locations: `$PWD/scripts/larch/*`, `$PWD/skills/implement/scripts/*`, and `$PWD/skills/loop-review/scripts/*`.
- `README.md` installation section replaced with a plugin-based install flow covering GitHub and local development paths.

### Removed

- `setup-larch.sh` (legacy git-submodule installer, superseded by the Claude Code plugin flow).
- `tests/test-setup-larch.sh` integration test and the CI job that invoked it.

### Notes for contributors (repo self-use)

Contributors working on larch itself should launch Claude Code with `--plugin-dir .` from the repo root so that `${CLAUDE_PLUGIN_ROOT}` resolves to the repo root and plugin-exported skills can find their scripts:

```bash
cd larch
claude --plugin-dir .
```

Alternatively, register the repo as a local marketplace and install:

```bash
claude plugin marketplace add .
claude plugin install larch@larch-local
```

The private `/relevant-checks` skill (at `.claude/skills/relevant-checks/`) is intentionally not exported as part of the plugin; each consuming repo maintains its own version.
