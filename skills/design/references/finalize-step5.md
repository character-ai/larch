# /design Step 5 finalization body

**Consumer**: `/design` Step 5.

**Contract**: Normative Step 5 prose for OOS filing, post-approval diagrams, plan compose/publish decisions, warning replay, and footer. `SKILL.md` keeps routing skeleton, Bash fences, background params, and final-summary marker bindings.

**When to load**: **MANDATORY READ ENTIRE FILE** at Step 5 entry, after the Step 5 banner/invariant and before the Step 5b skeleton.

## Ordering contract

Step 5 order: prepare emits `NEXT_ACTION`; `SKILL.md` branches; Step 5b.5 writes skip marker or candidate; Step 5c sanitizes diagrams before publish.

**MANDATORY: READ ENTIRE FILE before Step 5 diagram, final plan, summary, or Gate C prose composition: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

## Step 5b OOS filing body

**Privacy guardrail.** OOS Descriptions and reviewer `path:line` hints become **public** GitHub issues through `/larch:issue`. Reviewers must follow `SECURITY.md` and avoid high-risk paths or secret-adjacent material. `python/larch/core/redact.py` inside `issue create-one` is only a mechanical backstop.

Bash stages, caps, and pre-checks file conflicts; prompt calls `/larch:issue`. Helpers: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/python/cli.py design file-oos-prepare|file-oos-annotate` (sibling `file-design-oos.md`). Harness: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-python/cli.py design file-oos-prepare|file-oos-annotate` (`test-file-design-oos.md`; Makefile `test-file-design-oos`).

Cross-session idempotency: after successful `annotate` with `ISSUES_FAILED=0`, the helper best-effort atomically caches `$DESIGN_TMPDIR/oos-issues-created.md` at `~/.cache/larch/design-oos-filed/<ISSUE_NUMBER>.md`. Later `/design` restores those URLs only when the in-session sentinel is missing or empty and the cache is non-empty; a non-empty in-session sentinel wins. `--clear-cross-session-cache` deletes the issue cache and priority-label sidecars. `ISSUE_NUMBER` comes from the environment, or `--issue-number` for tests.

Priority labels: after `/larch:issue` succeeds, `python/cli.py design file-oos-annotate` writes `oos-issues-created.md`, ensures `oos-correctness`, and applies it only to filed OOS with `focus-area: correctness` or `focus-area: regression`. Label `gh` calls use `--repo <REPO>` from prepare or session state and fail closed when `REPO` is missing.

When a priority label is outstanding, annotate writes `.oos-priority-label-pending` and durable cache sidecars before the first `gh label create` or `gh issue edit`. Sidecars hold sentinel URLs, post-cap combined text, and filing order. Later `NEXT_ACTION=label-only` labels from them without calling `/larch:issue`; `oos-accepted-design.md` and `oos-issue.stdout.txt` are not required.

If the prepare wrapper exits non-zero, parse only `NEXT_ACTION=` and `STEP5B_STATUS=` from `$DESIGN_TMPDIR/oos-filing-prepare.env`. For `NEXT_ACTION=unknown-oos-status` or `STEP5B_STATUS=unknown-oos-status`, preserve the warning and stop for repair. Otherwise append captured stderr with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log append-failure` to `$DESIGN_TMPDIR/execution-issues.md` under `Tool Failures` with site `design Step 5b`, warn that OOS filing was skipped due to helper failure, and continue to Step 5b.5 without invoking `/larch:issue`.

When prepare output has `STEP5B_STATUS=prepare-failed-continue`, preserve the warning and continue to Step 5b.5 without invoking `/larch:issue`.

### `NEXT_ACTION=skip-pipeline`

Do not call `/larch:issue`.

- Re-emit `OOS_SKIP_BREADCRUMB` when non-empty.
- For `FILE_DESIGN_OOS_STATUS=skip-already-filed-sentinel`, or prepare stdout / `oos-filing-prepare.env` still carrying `WARN=` for that status, parse `WARN=`. If non-empty, append a `Warnings` entry to `$DESIGN_TMPDIR/execution-issues.md` via `run-log append-failure` with site `design Step 5b`, tool `python/cli.py design file-oos-prepare`, category `Warnings`, exit code 0.
- Check `STEP5B_NEEDS_ANNOTATE=true` after warning handling. If annotate is needed, call `design-step5b-annotate.sh` only when `$DESIGN_TMPDIR/oos-issue.stdout.txt` exists and is non-empty. Treat annotate as best-effort on this skip path: append non-zero annotate exits as `Tool Failures`, then continue to Step 5b.5.
- When annotate is not needed, continue to Step 5b.5 without the file-issues annotate sequence. Prepare already wrote `.completed/step-5b` for `skip-already-filed-sentinel` without annotate.
- Do not route `skip-already-filed-sentinel` through the annotate-before-issue manual recovery path.

### `NEXT_ACTION=file-issues`

Parse `FILE_DESIGN_OOS_COMBINED=`, `FILE_DESIGN_OOS_DEPS_TSV=`, and `FILE_DESIGN_OOS_DEPS_AVAILABLE=` from `oos-filing-prepare.env`. Accepted non-security OOS plus Gate C approval authorizes `/larch:issue`; no confirmation or `AskUserQuestion`, including retry.

If `FILE_DESIGN_OOS_DEPS_AVAILABLE=true` **and** `FILE_DESIGN_OOS_DEPS_TSV` points at a non-empty readable file, invoke **`/larch:issue`** in batch mode with `--input-file` set to `FILE_DESIGN_OOS_COMBINED`, `--title-prefix "[OOS]"`, `--blocked-by-issue "$ISSUE_NUMBER"`, `--sentinel-file "$DESIGN_TMPDIR/oos-issue-sentinel"`, **`--intra-batch-deps-file`** set to `FILE_DESIGN_OOS_DEPS_TSV`, and **`--no-dep-llm`** because caller-supplied serialization edges are authoritative. Otherwise invoke the same Skill call **without** `--intra-batch-deps-file` / `--no-dep-llm`, log a `Warnings` entry for the degraded path, and mirror the `/implement` Step 9a.1 warning.

Capture **stdout only** from the Skill tool to `$DESIGN_TMPDIR/oos-issue.stdout.txt`. **This write is MANDATORY** for every `/issue` invocation. If the Skill tool returns output inline, use the Write tool to write the exact captured `/larch:issue` stdout to that file before `annotate`. Never skip or reorder annotate relative to this write: `cmd_annotate` is the only writer of `oos-issues-created.md`, and `python/cli.py design render-final-summary` reads OOS count only from that file.

Run annotate and capture stdout to `$DESIGN_TMPDIR/oos-filing-annotate.stdout.txt`. On `FILE_DESIGN_OOS_STATUS=annotate-failed-empty-stdout` with `NEXT_ACTION=retry-file-and-annotate`, retry the file-and-annotate sequence once. Use `$DESIGN_TMPDIR/.oos-issue-retry-used` as the once-only sentinel. If the sentinel already exists, append `Tool Failures`, print a non-retryable failure, and do not write `.completed/step-5b`.

For the retry, re-run `/larch:issue` with the same arguments used for `NEXT_ACTION=file-issues`, capture stdout to `$DESIGN_TMPDIR/oos-issue.stdout.txt`, then re-run `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-annotate.sh`. If the second annotate returns `annotate-failed-empty-stdout`, stop before Step 5b.5. Do not loop.

On non-zero `_oos_ann_rc` with `FILE_DESIGN_OOS_STATUS=annotate-label-failed` or `.oos-priority-label-pending`, append under `Tool Failures`, print the label-failure status, and stop before Step 5b.5. Do not write `.completed/step-5b`. The next retry must run label-only annotate or re-prepare to get `NEXT_ACTION=label-only`.

On non-zero `_oos_ann_rc` when `ISSUES_FAILED>0` in `$DESIGN_TMPDIR/oos-issue.stdout.txt`, append under `Tool Failures` via `run-log append-failure`, including stderr. Print `**⚠ /design: OOS filing completed with ISSUES_FAILED>0; see execution-issues and oos-issue.stdout.txt**`, then continue to Step 5b.5. Per-block `Filed URL` lines are written only for successful items.

On non-zero `_oos_ann_rc` without the retry, label, or partial-failure contract, treat it as annotate or parse failure: append `Tool Failures` and continue to Step 5b.5.

**Manual OOS recovery when annotate ran before `/larch:issue`** (`STEP5B_STATUS=annotate-failed`, rc=1, `oos-issue.stdout.txt` empty or missing): the Step 5b sentinel was not written; re-run the `/larch:issue` + annotate sequence manually before continuing to Step 5b.5. Manual recovery files accepted non-security OOS; no confirmation/`AskUserQuestion`. Never file security-routed OOS here:

1. `/larch:issue --no-dedup --input-file <oos-combined.md> --title-prefix "[OOS]" --label "enhancement"`; do **not** use `--blocked-by-issue` (mutually exclusive with `--no-dedup`).
2. Capture stdout to `$DESIGN_TMPDIR/oos-issue.stdout.txt`.
3. Apply the blocker edge: `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" issue add-blocked-by --client-issue <OOS_NUM> --blocker-issue <TRACKING_NUM> --repo <REPO>`.
4. Re-run annotate: `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-annotate.sh`.

### `NEXT_ACTION=label-only`

Do not call `/larch:issue`. Run `design-step5b-annotate.sh` in label-only mode. It reads `oos-issues-created.md`, `oos-combined.md`, optional `oos-design-filing-order.txt`, and `REPO`; it skips empty-stdout and missing-accepted sequencing errors. URL mapping is 1-based by original `ISSUE_n` filing slot, including failed-slot gaps. Cap rollup labels the sole surviving URL when any post-cap combined block is high-risk.

`.completed/step-5b` is written by the Step 5b prepare/annotate wrappers on successful annotate paths: `annotate-complete`, `annotate-label-complete`, and prepare skip paths with no pending labels. Non-zero annotate exits write `.completed/step-5b` only for the documented partial `/larch:issue` carve-out without a label-retry subset. Exclude `annotate-label-failed`, `.oos-priority-label-pending`, and `STEP5B_STATUS=annotate-label-failed` from any non-zero stdout completion rule.

## Step 5b.5 diagram composition

If `DIAGRAM_REQUIRED=true`, the wrapper removed stale diagram files and exited for orchestrator authoring. Generate a Mermaid Architecture Diagram from the finalized approved plan, obey `${CLAUDE_PLUGIN_ROOT}/skills/shared/mermaid-safe-content.md`, and write `$DESIGN_TMPDIR/architecture-diagram.candidate.md` with a `## Architecture Diagram` heading and Mermaid fence. Do not print candidate or final diagram bodies to chat.

On generation failure before a candidate is written, print `**⚠ 5b.5: arch diagram: generation failed, proceeding without diagram (<elapsed>)**`. Optional full capture may be written to `$DESIGN_TMPDIR/architecture-diagram-generation.failure.log` for local repair only. Append only a bounded warning to `execution-issues.md` via `design_diagram_log.write_bounded_diagram_failure_log`; never append raw Mermaid, generator stdout/stderr, sanitizer stdout, or candidate bodies.

Step 5b.5 diagram generation paths append bounded warnings only. Step 5c sanitizes the candidate before publish. It silently promotes accepted candidates to `architecture-diagram.md` and writes `.completed/step-5b.5`. On missing candidate or rejection, it deletes stale accepted/candidate files, writes `architecture-diagram.skipped`, appends a bounded warning for Step 5c warning replay, writes `.completed/step-5b.5`, and continues without emitting diagram bodies.

## Step 5c compose and publish

Compose `$DESIGN_TMPDIR/composed-plan.md` containing `## Plan`, `## Acceptance`, and a trailing `diff_lines: <N>` line from `$DESIGN_TMPDIR/diff-lines.txt` or a best-effort estimate.

The Step 5c driver delegates to `python/cli.py design step5c`, which calls the publish tail in-process. The tail writes review provenance, re-runs `plan check-size --design-tmpdir "$DESIGN_TMPDIR" --plan-file "$DESIGN_TMPDIR/plan.txt"`, and refuses incomplete review, oversize without override, or size-check failure before redaction. It validates the composed plan and exits 4 with `.design-publish-result.env` when `VALIDATE_STATUS=defects-found`. On that exit, execute **### Plan command validator failure (shared)** with `--site` `design Step 5c`: preserve `$DESIGN_TMPDIR`, skip Step 6 cleanup, and do not publish, rename, or redact.

A missing or empty `$DESIGN_TMPDIR/composed-plan.md` also exits 4 with `VALIDATE_STATUS=defects-found`. Fix-and-retry for this defect must re-run composition first, then re-invoke `design-step5c.sh`. Override is not offered. For ordinary composed-plan validator defects where the file exists and is non-empty, Fix-and-retry re-invokes `design-step5c.sh`; Override re-invokes it with `--skip-validate`.

When `_publish_rc=4`, execute **### Plan command validator failure (shared)** using parsed `VALIDATE_*` and `PUBLISH_REFUSE_REASON` keys with `--site` `design Step 5c`. Missing `composed-plan.md` offers only Fix-and-retry / Cancel. Before review-provenance, `PUBLISH_REFUSE_REASON=oversize-no-override|size-check-failed` offers Decompose / Override / Cancel; Override writes the trailer, deletes `composed-plan.md`, and re-runs `design-step5c.sh`. Empty `VALIDATE_LOG_FILE` with zero missing scripts is review-provenance refusal: Fix-and-retry re-runs `/design`, or Cancel.

When `_publish_rc=2` or an unexpected non-zero value outside `{0,1,3,4}` appears, abort after best-effort `python/cli.py design stage-terminal-state` staging as `failed-publish-tail`. This includes `_publish_rc=5`. Parse `FINAL_SUMMARY_PATH=<path>` from final `bgjob wait` `DONE` stdout or `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`, follow the `/design` Read-always readiness profile, then stop before Step 5c items 5-7, Step 5d, or Step 6.

When `_publish_rc=3`, the publish tail may have completed but `.design-publish-result.env` could not be written. Parse the captured stdout fallback (`_publish_stdout_file`) and continue Step 5c items 5-7 with the warning above. Do not treat exit 3 as publish-tail incomplete.

When `_publish_rc` is in `{0, 1, 3, 4}`, parse through `python/cli.py design read-result-env --input "$DESIGN_TMPDIR/.design-step5c-status.env"` after bgjob `DONE`; the helper prefers `$DESIGN_TMPDIR/bgjob/design-step5c.result.env` and falls back to the legacy status env only when absent. Gate success on `BGJOB_RC=0`. Exit 1 is the normal plan-block-write failure path. Do not abort solely because `_publish_rc=1`.

**Driver WARN replay (top chat):** After the Bash block, when `_publish_rc` ∈ {0, 1, 3} and driver WARN bodies were parsed, emit each distinct WARN `_value` verbatim to top chat. Do not leave them only as `WARN=` machine lines inside Bash output.

Only when `_publish_rc` is 0, 1, or 3 and driver output was parsed from file and/or stdout: on `PLAN_WRITE_OK=true`, print `⏩ 5c.5: status=${UPSERT_STATUS:-unknown} arch=${ARCHITECTURE_SOURCE:-unknown}`. The `python/cli.py design step5c` fence already wrote `step-5c` under the `PLAN_WRITE_OK=true` gate before leaving the fence. Rename (`RENAMED`) and Step 6 cleanup remain gated on `PUBLISH_OK` separately.

Only when `_publish_rc` is 0, 1, or 3 and driver output was parsed, or stdout fallback populated `PLAN_WRITE_OK`: when `PLAN_WRITE_OK=false`, print `**⚠ 5: plan-block-write failed: preserving $DESIGN_TMPDIR**` and skip Step 6 cleanup. Do not write `step-5c`.

## Step 5d warning replay and footer

Repeat any external reviewer warnings from earlier steps, including Step 0 reviewer-availability checks via `session setup`, Step 3 runtime failures, Step 5b.5 diagram generation failure, and driver WARN bodies replayed from Step 5c, so they are visible at the end of the workflow. Examples:

- `**⚠ Codex not available: <reason>**`
- `**⚠ 5b.5: arch diagram: generation failed, proceeding without diagram (<elapsed>)**`

The rigid `larch:final-summary` body is produced by `python/cli.py design render-final-summary` inside `python/cli.py design step5c` after the publish outcome is known. Parse `FINAL_SUMMARY_PATH` from final bgjob `DONE` stdout or result env, then use the shared Read-always readiness profile. Do not add token/timing chat tails, extra recap prose, or farewell wording outside that rendered block and the machine footer.

When `PLAN_WRITE_OK=true`, repeat the external-reviewer warnings, then emit exactly one terminal machine footer as the last human-visible output line of Step 5. When `PLAN_WRITE_OK=false`, Step 5c already ran the summary before the `**⚠ 5: plan-block-write failed**` line. Do not invoke `python/cli.py design render-final-summary` again.

## /design auto error reporting

`python/cli.py design failure-report` owns the teardown report gate. It can file a terminal-failure report for `failed-plan-write`, `failed-publish`, `failed-postplan`, `failed-clarify`, `failed-judge-panel`, and `failed-publish-tail`, or an escalation-success report only when the final outcome is `approved` or `approved-partition`.

Sentinel precedence is terminal report, escalation-success report, then operator-action skip. Terminal failures win over escalation evidence on failed outcomes. Stale terminal state is ignored on successful outcomes. Operator-action and all `cancelled-*` outcomes do not file, but they must write `design-failure-operator-action.env`, `design-failure-operator-action-chat.md`, and a run-log audit.

`python/cli.py design stage-terminal-state` is the mechanical writer for prompt-owned hard halts. It writes `design-failure-terminal-state.env` after validating tokens through `python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery validate-token --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR"` and validating the completed state through `python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery validate-terminal-state ...`. Generic helper calls from /design always pin `--implement-tmpdir "$DESIGN_TMPDIR"` and pass state overrides for terminal classify and compose.

Step 3 panel degradation statuses `panel-failed`, `tally-error`, and `degraded-empty-collector` are non-terminal Gate B bypass degradation when at least one reviewer round launched. `panel-init-failed` means zero reviewers launched; it is a terminal hard stop before Gate C and Step 5. Step 2b.5 decompose-panel retry exhaustion is terminal `failed-judge-panel` and is owned by Split-path, not `design-step3-review.sh`.
