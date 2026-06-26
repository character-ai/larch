# /design Step 5 finalization body

**Consumer**: `/design` Step 5.

**Contract**: Normative Step 5 finalization body prose for OOS filing, post-approval diagram composition, plan composition/publish decisions, warning replay, and footer selection. `SKILL.md` retains the routing skeleton, Bash fences, Step 5b dispatch-read adjacency, immediate-background parameters, and final-summary marker bindings.

**When to load**: **MANDATORY READ ENTIRE FILE** at Step 5 entry, after the Step 5 banner/invariant and before the Step 5b skeleton.

## Ordering contract

The Step 5 order is: prepare fence in `SKILL.md` → read `oos-step5b-dispatch.md` in `SKILL.md` → parse `NEXT_ACTION` in `SKILL.md` → branch. Use `oos-step5b-dispatch.md` for the fallback table. Use this file for branch body detail.

## Step 5b OOS filing body

**Privacy guardrail.** OOS Descriptions are filed as **public** GitHub issues by `/larch:issue`, so reviewer-supplied `path:line` hints in those Descriptions become public on filing. Reviewers should follow `SECURITY.md` and avoid naming high-risk paths or pasting secret-adjacent material in OOS Descriptions; `python/larch/core/redact.py` inside `issue create-one` is the mechanical backstop, but the prose anchor catches reviewer-prompt regressions.

Mechanical staging + cap + file-conflict pre-pass run in Bash; the `/larch:issue` Skill call is prompt-side. Contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/python/cli.py design file-oos-prepare|file-oos-annotate` (sibling `file-design-oos.md`); offline harness `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-python/cli.py design file-oos-prepare|file-oos-annotate` (sibling `test-file-design-oos.md`; Makefile target `test-file-design-oos`).

Cross-session idempotency: after a successful `annotate` with `ISSUES_FAILED=0`, the helper best-effort copies `$DESIGN_TMPDIR/oos-issues-created.md` to `~/.cache/larch/design-oos-filed/<ISSUE_NUMBER>.md` (atomic `mktemp` + `mv` in that directory). A later `/design` on the same issue with a fresh `$DESIGN_TMPDIR` consults the cross-session cache only after confirming the in-session sentinel is missing or empty: if the cache file exists, is non-empty, and `$DESIGN_TMPDIR/oos-issues-created.md` is absent or empty, the URLs are restored and `oos-accepted-design.md` is annotated from them without calling `/larch:issue` again (a non-empty in-session sentinel still wins). Operators can pass `--clear-cross-session-cache` on `prepare` to delete the cache entry for that issue and force a normal re-file when prior GitHub issues were closed or deleted. `ISSUE_NUMBER` is taken from the environment after the usual session prelude, or from `--issue-number` when tests or tooling invoke the helper directly.

If the prepare wrapper itself exits non-zero, parse `NEXT_ACTION=` and `STEP5B_STATUS=` from `$DESIGN_TMPDIR/oos-filing-prepare.env` (ignore unrelated lines). When `NEXT_ACTION=unknown-oos-status` or `STEP5B_STATUS=unknown-oos-status`, preserve the emitted warning and stop for repair; do not continue to Step 5b.5. Otherwise append the captured stderr via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log append-failure` to `$DESIGN_TMPDIR/execution-issues.md` under `Tool Failures` with site `design Step 5b`, print a user-visible warning that OOS filing was skipped due to helper failure, and continue to Step 5b.5 without invoking `/larch:issue`.

When prepare output has `STEP5B_STATUS=prepare-failed-continue`, preserve the emitted warning and continue to Step 5b.5 without invoking `/larch:issue`.

### `NEXT_ACTION=skip-pipeline`

Do not call `/larch:issue`.

- Re-emit `OOS_SKIP_BREADCRUMB` when non-empty.
- When `FILE_DESIGN_OOS_STATUS=skip-already-filed-sentinel` or prepare stdout / `oos-filing-prepare.env` still carries `WARN=` for that status, parse `WARN=`. If non-empty, append a `Warnings` entry to `$DESIGN_TMPDIR/execution-issues.md` via `run-log append-failure` (site `design Step 5b`, tool `python/cli.py design file-oos-prepare`, category `Warnings`, exit code 0).
- Check `STEP5B_NEEDS_ANNOTATE=true` after warning handling. If annotate is needed, call `design-step5b-annotate.sh` only when `$DESIGN_TMPDIR/oos-issue.stdout.txt` exists and is non-empty. Treat annotate as best-effort on this skip path: append non-zero annotate exits as `Tool Failures`, then continue to Step 5b.5.
- When annotate is not needed, continue to Step 5b.5 without the file-issues annotate sequence. Prepare already wrote `.completed/step-5b` for `skip-already-filed-sentinel` without annotate.
- Do not route `skip-already-filed-sentinel` through the annotate-before-issue manual recovery path.

### `NEXT_ACTION=file-issues`

Parse `FILE_DESIGN_OOS_COMBINED=`, `FILE_DESIGN_OOS_DEPS_TSV=`, and `FILE_DESIGN_OOS_DEPS_AVAILABLE=` from `oos-filing-prepare.env`.

If `FILE_DESIGN_OOS_DEPS_AVAILABLE=true` **and** `FILE_DESIGN_OOS_DEPS_TSV` points at a non-empty readable file, invoke **`/larch:issue`** in batch mode with `--input-file` set to `FILE_DESIGN_OOS_COMBINED`, `--title-prefix "[OOS]"`, `--blocked-by-issue "$ISSUE_NUMBER"`, `--sentinel-file "$DESIGN_TMPDIR/oos-issue-sentinel"`, **`--intra-batch-deps-file`** set to `FILE_DESIGN_OOS_DEPS_TSV`, and **`--no-dep-llm`** (caller-supplied serialization edges are authoritative). Otherwise invoke the same Skill call **without** `--intra-batch-deps-file` / `--no-dep-llm` (graceful-degrade path — log a `Warnings` entry that the file-conflict pre-pass failed or produced an empty TSV; mirror the `/implement` Step 9a.1 degraded-mode warning).

Capture **stdout only** from the Skill tool to `$DESIGN_TMPDIR/oos-issue.stdout.txt` (machine `ISSUE_*` / `ISSUES_*` lines — see `skills/issue/SKILL.md` Step 7). **This write is MANDATORY** regardless of how `/issue` was invoked. If the Skill tool returns output inline rather than writing it to a file automatically, the orchestrator MUST use the Write tool to write the exact captured `/larch:issue` stdout to `$DESIGN_TMPDIR/oos-issue.stdout.txt` before calling `annotate`. The `annotate` step MUST NOT be skipped or reordered relative to this write — `oos-issues-created.md` is written only by `cmd_annotate`, and `python/cli.py design render-final-summary` reads OOS count exclusively from that file.

Run annotate and capture its stdout to `$DESIGN_TMPDIR/oos-filing-annotate.stdout.txt`. On exit 0, parse annotate stdout for `FILE_DESIGN_OOS_STATUS=`. When the value is `annotate-skipped-empty-stdout`, parse `WARN=` from annotate stdout; if non-empty, append a `Warnings` entry to `$DESIGN_TMPDIR/execution-issues.md` via `run-log append-failure` (site `design Step 5b annotate-skip`, tool `python/cli.py design file-oos-annotate`, category `Warnings`, exit code 0); print `**⚠ /design: annotate skipped (empty issue stdout) — OOS filing status unclear; see execution-issues**` and continue to Step 5b.5.

On non-zero `_oos_ann_rc` when `ISSUES_FAILED>0` in `$DESIGN_TMPDIR/oos-issue.stdout.txt` (partial `/issue` failure): append under `Tool Failures` via `run-log append-failure` (site `design Step 5b`, include stderr), print `**⚠ /design: OOS filing completed with ISSUES_FAILED>0 — see execution-issues and oos-issue.stdout.txt**`, and continue to Step 5b.5 (per-block `Filed URL` lines are written only for successful items).

On non-zero `_oos_ann_rc` without a partial-failure contract, treat as annotate/parse failure: append `Tool Failures` and continue to Step 5b.5.

**Manual OOS recovery when annotate ran before `/larch:issue`** (`STEP5B_STATUS=annotate-failed`, rc=1, `oos-issue.stdout.txt` empty or missing — sequencing error): the Step 5b sentinel was not written; re-run the `/larch:issue` + annotate sequence manually before continuing to Step 5b.5:

1. `/larch:issue --no-dedup --input-file <oos-combined.md> --title-prefix "[OOS]" --label "enhancement"` — do **not** use `--blocked-by-issue` (mutually exclusive with `--no-dedup`).
2. Capture stdout to `$DESIGN_TMPDIR/oos-issue.stdout.txt`.
3. Apply the blocker edge: `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" issue add-blocked-by --client-issue <OOS_NUM> --blocker-issue <TRACKING_NUM> --repo <REPO>`.
4. Re-run annotate: `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-annotate.sh`.

`.completed/step-5b` is written by the Step 5b prepare/annotate wrappers on every successful annotate path (exit 0: `annotate-complete`, `annotate-skipped-empty-stdout`, and the prepare skip paths). Non-zero annotate exits also write `.completed/step-5b` when `oos-issue.stdout.txt` is present and non-empty, so partial `/larch:issue` failures and skip-already annotate retries can continue to Step 5b.5.

## Step 5b.5 diagram composition

**MANDATORY — READ ENTIRE FILE before composing architecture diagram prose: `skills/design/references/readability-style.md`.**

If `DIAGRAM_REQUIRED=true`, the wrapper removed stale diagram files and exited for orchestrator authoring. Generate a Mermaid Architecture Diagram from the finalized approved plan, and obey `${CLAUDE_PLUGIN_ROOT}/skills/shared/mermaid-safe-content.md`. Write `$DESIGN_TMPDIR/architecture-diagram.candidate.md` with a `## Architecture Diagram` heading and Mermaid fence. Do not print the candidate or final diagram body to chat.

On generation failure before a candidate is written, print `**⚠ 5b.5: arch diagram — generation failed, proceeding without diagram (<elapsed>)**`. Optional full capture may be written to `$DESIGN_TMPDIR/architecture-diagram-generation.failure.log` for local repair only. Append only a bounded warning to `execution-issues.md` via `design_diagram_log.write_bounded_diagram_failure_log`; never append raw Mermaid, generator stdout/stderr, sanitizer stdout, or candidate bodies.

Step 5b.5 diagram generation and sanitizer rejection paths append bounded warnings only. The sanitizer silently promotes accepted candidates to `architecture-diagram.md` and writes `.completed/step-5b.5`. On missing candidate or rejection, it deletes stale accepted/candidate files, writes `architecture-diagram.skipped`, appends a bounded warning, writes `.completed/step-5b.5`, and exits 0. It does not run FINALIZE and does not emit diagram bodies.

## Step 5c compose and publish

**MANDATORY — READ ENTIRE FILE before composing the final plan block: `skills/design/references/readability-style.md`.**

Compose `$DESIGN_TMPDIR/composed-plan.md` containing `## Plan`, `## Acceptance`, and a trailing `diff_lines: <N>` line (integer from `$DESIGN_TMPDIR/diff-lines.txt` or best-effort estimate).

The Step 5c driver delegates to `python/cli.py design step5c`, which calls the publish tail in-process. The publish tail reads `.step3-review-result.env`, writes `review_status:` and `rounds_completed:` to the plan block payload, and refuses `panel-init-failed`, `panel-skipped`, or `rounds_completed=0` before redaction. It validates the metadata-bearing composed plan unconditionally before redaction and exits 4 with `.design-publish-result.env` populated when `VALIDATE_STATUS=defects-found`; on that exit, execute **### Plan command validator failure (shared)** with `--site` context `design Step 5c` and **Cancel** semantics: preserve `$DESIGN_TMPDIR`, skip Step 6 cleanup, and do not publish, rename, or redact on this exit branch.

A missing or empty `$DESIGN_TMPDIR/composed-plan.md` also exits 4 with `VALIDATE_STATUS=defects-found`. Fix-and-retry for this defect must re-run composition first, then re-invoke `design-step5c.sh`. Override is not offered for this defect. For ordinary composed-plan validator defects where the file exists and is non-empty, Fix-and-retry re-invokes `design-step5c.sh`; Override re-invokes it with `--skip-validate`.

When `_publish_rc=4`, execute **### Plan command validator failure (shared)** using the parsed `VALIDATE_*` keys with `--site` context `design Step 5c`. When `[[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]]`, skip auto-repair and offer only Fix-and-retry and Cancel. When `VALIDATE_LOG_FILE` is empty and `VALIDATE_MISSING_SCRIPT_COUNT` is `0` or unset, treat this as review-provenance refusal: skip auto-repair, skip Override, and offer only Fix-and-retry (re-run `/design`) and Cancel.

**Driver WARN replay (top chat):** After the Bash block, when `_publish_rc` ∈ {0, 1, 3} and driver WARN bodies were parsed, emit each distinct WARN `_value` verbatim to top chat (same visibility as external-reviewer warnings — do not leave them only as `WARN=` machine lines inside Bash output).

Only when `_publish_rc` is 0, 1, or 3 and driver output was parsed (file and/or stdout): On `PLAN_WRITE_OK=true`, print `⏩ 5c.5: status=${UPSERT_STATUS:-unknown} arch=${ARCHITECTURE_SOURCE:-unknown}`. The `python/cli.py design step5c` fence has already written `step-5c` under the `PLAN_WRITE_OK=true` gate before leaving the fence. Rename (`RENAMED`) and Step 6 cleanup remain gated on `PUBLISH_OK` separately.

Only when `_publish_rc` is 0, 1, or 3 and driver output was parsed (or stdout fallback populated `PLAN_WRITE_OK`): When `PLAN_WRITE_OK=false` (explicitly false after parse — not merely unset), print `**⚠ 5: plan-block-write failed — preserving $DESIGN_TMPDIR**` and skip Step 6 cleanup. Do not write `step-5c`.

## Step 5d warning replay and footer

**Repeat any external reviewer warnings** from earlier steps (Step 0 reviewer-availability checks via `session setup`, Step 3 runtime failures, or Step 5b.5 diagram generation failure) and any **driver WARN bodies** replayed from Step 5c (e.g. empty `SESSION_ID`, rename failures) so they are visible at the end of the workflow. Examples:

- `**⚠ Codex not available: <reason>**`
- `**⚠ Cursor review failed: <reason>**`
- `**⚠ Cursor plan review failed / produced empty output**`
- `**⚠ Codex plan review failed / produced empty output**`
- `**⚠ 5b.5: arch diagram — generation failed, proceeding without diagram (<elapsed>)**`

The rigid `larch:final-summary` body is produced by `python/cli.py design render-final-summary` inside `python/cli.py design step5c` after the publish outcome is known. Step 5c owns the once-per-handoff orchestrator emit through the shared marker-first profile. Do not add token/timing chat tails, extra recap prose, or farewell wording outside that rendered block and the machine footer.

When `PLAN_WRITE_OK=true`, repeat the external-reviewer warnings, then emit exactly one terminal machine footer as the last human-visible output line of Step 5. When `PLAN_WRITE_OK=false`, Step 5c already ran the summary before the `**⚠ 5: plan-block-write failed**` line. Do not invoke `python/cli.py design render-final-summary` again.
