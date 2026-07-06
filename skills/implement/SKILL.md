---
# Referenced implement script files:
# skills/implement/scripts/step-architectural-guidelines-write-compose.md
# skills/implement/scripts/test-architectural-guidelines-step.sh
# skills/implement/scripts/test-architectural-guidelines-step.md
name: implement
description: "Use when implementing from a GitHub issue with a vetted in-body plan (run /design first). Materialize, implement, validate, review, PR, CI. See /research, /design, /im, /implement --merge."
argument-hint: "[--merge] [--forked] [--draft] [--no-admin-fallback] [--no-logs-commit] [--coder <claude|codex|cursor>] [--run-id <ID>] [--force|-f] [--self-review] [--self-implement] [--difficulty <TRIVIAL|MODERATE|HARD>] <issue-N>"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob, Agent, Task, WebFetch, WebSearch, Skill
---

# Implement Skill

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

End-to-end: fetch the vetted `larch:plan`, materialize artifacts, implement, validate, commit, review, ship the PR, monitor CI, and clean up. With `--merge`: also run CI+rebase+merge, delete the local branch, verify main, and have the active Step 8+ driver flush `run-log manifest` to `status=done` plus `python/cli.py final-report write` before exit. The tmpdir/tracking summary may reflect `MERGE_RESULT` without any post-merge `git commit` (NEVER #16). Step 18 still owns teardown, token/timing refresh, and terminal safety nets.

**Protocol Execution Directive.** You are the `/implement` orchestrator. After flag parsing and mutual-exclusion checks, your FIRST external actions MUST be: (1) when `forked_target=true`, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" admission fork-env` once and parse `UPSTREAM_REPO` plus sibling fork KV lines from stdout; (2) run exactly one `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight` call as the sole mechanical surface for Preflight items 1-3, passing `--repo "$UPSTREAM_REPO"` when forked; (3) after prompt-side Preflight judgment, run Step 0 unchanged through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh --mode initial`. Prompt-side judgment starts only after helper exit `0`. Item 4 is the main-agent plan-adequacy audit when `force_requested=false`; force skips it and proceeds to item 6. Item 6 remains the semantic materiality judgment after `AUDIT=pass` or force skip. When `forked_target=true` and `UPSTREAM_REPO` is already set from (1), **do not** re-run `python/cli.py admission fork-env`; reuse the fork metadata to avoid a second bootstrap tmpdir.

**Anti-halt continuation reminder.** After each child `Skill` call (`/review`, `/issue`, `/implement`) and each numbered or sub-step `Bash` helper, including `python/cli.py checks run-relevant`, IMMEDIATELY continue to this skill's NEXT numbered step. Do NOT stop on cleanup output, Bash stdout, status, summary, handoff, recap, or "returning to parent" prose. For Immediate-background Bash, wait for `<task-notification>` before parsing stdout, reading result files, or advancing. Applies from Preflight through Step 18 except explicit non-sequential directives in THIS file (`skip to Step N`, `bail to cleanup`, `jump back`, `loop back`, `fall through`, `break out`). Every relevant-checks helper call is covered. **Critical boundary: Step 9b PR creation → Step 10 CI monitor immediately; PR creation is NOT the end.** **Critical boundary: when the active Step 8+ driver (`python3 …/python/cli.py ship pr`) exits, route only from process exit code + JSON stdout per the Python driver selector; do not parse `ship-pr-state.sh` or the retired bash exit matrix.** **Critical boundary: after `route-exit` emits `NEXT_ACTION=ci-fix`, do NOT end the turn; run the ci-fix repair procedure in the same turn.** **Critical boundary: after preflight audit passes (`AUDIT=pass`), continue through Preflight items 6-7, then run Step 0 `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh --mode initial`; do NOT end the turn on the audit-pass envelope. Critical boundary: after the force plan-adequacy audit skip breadcrumb prints, continue through Preflight items 6–7, then run Step 0; do NOT halt waiting for an `AUDIT=pass` envelope on the force skip path.** **Terminal boundary: after the combined Step 16-17 wrapper, follow NEVER #17; emit the extracted marker body verbatim when present, then continue to Step 18.** → shared/subskill-invocation.md#anti-halt

**Skill-name fallback reminder.** When invoking a child skill via the Skill tool from this file, ALWAYS try the bare name first (`"design"`, `"review"`, `"issue"`, `"implement"`). Use the fully qualified `larch:` form (`"larch:design"`, etc.) only after bare-name lookup returns `Unknown skill`; in a consumer repo with a different plugin namespace, use that namespace as the fallback. `/implement` does not invoke relevant-checks through the Skill tool on the green path; it uses the captured Python checks helper so success returns one bounded machine line, or `RELEVANT_CHECKS_SKIPPED=true` only on explicit `--allow-skip` test paths. Phase 1 (#3364) does not invoke `/release`; versioning moves to `/release` (Phase 3). Do NOT mirror this skill's own namespaced invocation (`larch:implement`) onto child Skill calls. → shared/subskill-invocation.md#bare-name-fallback

## Load-Bearing Invariants

Two invariants enforced across multiple steps. Anchor cross-step questions here; do not re-derive inline.

1. **Step 9a.1 OOS Sentinel Idempotency** — re-running `/implement` in the same session MUST NOT double-file the unifying `[OOS]` issue for vote-accepted non-security OOS. **Enforcement**: Step 9a.1 checks `$IMPLEMENT_TMPDIR/oos-issues-created.md`, recovers prior URLs and tallies from it, and avoids a second `/issue` call. **Why**: `/issue` semantic dedup is a nondeterministic backstop; the sentinel is the byte-exact guard.

**Fork-mode carve-out for Invariant #1**: when `forked_target=true`, Step 9a.1 does not call `/issue`; accepted OOS items stay in final-report text. CI comparison uses `upstream/main` via `python/cli.py push rebase --base-remote upstream --base-ref main` and `python/cli.py ci status --base-remote upstream --base-ref main`.

2. **Tracking-Issue Sentinel Idempotency** (umbrella #348) — re-running `/implement` in the same session MUST NOT double-adopt the wrong issue or corrupt `RUN_ID`. **Enforcement**: Step 0 checks `$IMPLEMENT_TMPDIR/parent-issue.md`; on retry it recovers prior `ISSUE_NUMBER` and `RUN_ID`, skipping Branch 2 adoption, `run-log init`, and `python/cli.py tracking post-issue`. Write the sentinel ONLY after `ISSUE_NUMBER`, `RUN_ID`, and the metadata summary comment resolve. If `run-log init` fails, set `IMPLEMENT_BAIL_REASON=tracking-init-failed`, `STALL_TRACKING=true`, skip the sentinel, skip to Step 18, and **preserve `$ISSUE_NUMBER`** so Step 18 can rename the issue to `[STALLED]` when applicable. Reserve `DEFERRED=true` for the non-stalled metadata-publication defer path (`POSTED=false` / no sentinel, then continue within Step 0). **Why**: `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary` uses marker literals for the four slim comments, but the local sentinel remains the byte-exact session guard, parallel to Invariant #1.

## NEVER List

Each rule states WHY; per-site reminders reference by anchor name.

1. **NEVER simply "log and return" on push failure in the Step 12 merge loop inside the active Step 8+ driver.** **Why**: `python/cli.py ci wait` and `python/cli.py merge pr` operate on remote PR state only; a log-and-return would let the merge loop proceed to `ACTION=merge` on a remote branch that never received the fix push. **How to apply**: Step 10 CI-fix paths may degrade gracefully; Step 12 family MUST bail to 12d.

2. **(removed in Phase 1 #3364 — bump verification on the ship path; see `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md` retirement stub.)**

3. **NEVER use the `ours`/`theirs` git labels when describing conflict sides during rebase.** **Why**: during rebase their semantics are inverted vs. merge (`--ours` = base being rebased onto = upstream main); labels cause silent resolution errors. **How to apply**: always use "upstream (main)" and "feature branch commit" in Phase 1 commentary and user prompts.

4. **NEVER skip the code-review step regardless of the nature of changes.** **Why**: code, skills, docs, data, and config all require reviewer-panel vetting. **How to apply**: on the standard path, Step 5 invokes `skills/implement/scripts/step-5-review.sh` once per Step 5 entry; that launcher prints the banner, forwards session-env and tmpdir context, and launches the file-backed `review-and-fix CLI` review loop **without** any `--panel` token (see `python/test_review_and_fix.py`). `review-and-fix step5` uses `$IMPLEMENT_TMPDIR/plan.txt` and a fixed cap of 2 for every tier; degraded rounds consume the active budget, and escalated rounds skip pruning. The review panel is applied only inside `review-and-fix CLI` → `review core`. **`--self-review` exception**: when `self_review=true`, Step 5 skips `review-and-fix step5` and the main agent performs thorough inline self-review; review still runs.

5. **NEVER let the Step 9a.1 sentinel short-circuit silently skip the larch-log OOS update.** **Why**: idempotency recovery MUST write recovered accepted-OOS URLs to the `oos-issues` log batch and refresh terminal summary content; silent skip breaks committed run-log output. **How to apply**: the idempotent-rerun branch only `run-log append --log-root "$IMPLEMENT_TMPDIR/larch-logs" --batch oos-issues` with URLs recovered from `oos-issues-created.md`, plus terminal-summary refresh when applicable. On the active Python path, `python/cli.py oos file` emits `run-statistics` through `python/oos_filer.py`; the legacy bash fallback writes `run-statistics` only after post-checkpoint Step 8+ `python/cli.py oos disposition-checkpoint` exits 0 (NEVER #14). **Fork-mode carve-out**: when `forked_target=true`, tracking-issue lifecycle and OOS issue creation are disabled; Step 9a.1 skips issue filing and larch-log Accepted-OOS updates, and final-report text carries accepted OOS items.

6. **NEVER let the focus-area enum drift out of checked review prompt surfaces.** **Why**: `.github/workflows/ci.yaml` inspects the canonical review/design prompt files for the unquoted focus-area enum; Step 5 now delegates prompt construction to review scripts instead of embedding prompt strings here. **How to apply**: when moving review prompt text between scripts or skill files, update the CI file list in the same PR so the surface containing `code-quality / risk-integration / correctness / architecture / security` remains checked.

7. **NEVER bail mid-run on orchestrator-judgment "scope" or "capacity" concerns without a mechanical justification.** **Why**: `/implement` is designed for long autonomous runs. Subjective remaining-work judgments are NOT valid bail reasons. The only sanctioned non-error halt paths between Step 2 and Step 18 are: (a) Step 12d under documented judgment conditions; (b) explicit user halt in a fresh interactive turn; (c) hard tool failure. **How to apply**: follow the next explicit control-flow directive unless a sanctioned halt path applies. **Post-merge sub-clause (highest-stakes halt boundary)**: the `✅ 12: CI+merge loop status=complete outcome=merged pr=<N> elapsed=<elapsed>` line at Step 12b, and the analogous `✅ 12: CI+merge loop status=complete outcome=force-merged-externally pr=<N> elapsed=<elapsed>` line at Step 12a's `already_merged` branch, is the most halt-prone point. The run is not done: Steps 14, 15, 16, 17, and 18 still must run. Ending the turn, posting a recap, or writing a handoff between that breadcrumb and Step 14's first action violates NEVER #7. `pr_closed=true` and `DONE_RENAME_APPLIED=true` are PRE-conditions for Steps 14-18, not POST-conditions of a finished run.

8. **NEVER call `ScheduleWakeup` anywhere in the `/implement` orchestrator.** **Why:** improvised wakeups re-fire as `/loop` input and can extend turns past Step 18. **How to apply:** do not call `ScheduleWakeup` at any step. Do not spawn a Monitor or a Bash polling loop (`for`/`while`/`until` + `sleep`) to watch another `run_in_background` job finish. For long helpers (>= 30 s; e.g., `run-step-checks.sh`, `review-and-fix step5`, `python/cli.py implement step-7a`, `step-8-ship.sh`), use immediate-background Bash and wait for one `<task-notification>`. See `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step2-dispatch.md` for the normal wait contract. **NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator.** Hook `scripts/hook-bg-poll-guard.sh` denies Monitor and TaskOutput during active bg-waits for `/implement` markers (`implement-step3-checks`, `implement-step5-review`, `implement-step8-ship`) and release sentinels (`.completed/step-3-terminal`, `.completed/step-5-terminal`, `.step-8-ship-handoff.rc`). Before the `<task-notification>`, make no progress probes. The hook may still allow a live `Read` of `tasks/*.output` on the running task; treat that as diagnostic only and do not use it to advance the step. On premature notification while the child is still running, read `${CLAUDE_PLUGIN_ROOT}/skills/shared/orchestrator-never.md` only when that recovery condition is active. End the turn, and do not use `ps`, Monitor, TaskOutput, or background recovery waiters. If a live `Read` of the just-completed Step 3 or Step 5 task output is denied immediately after that same step's genuine completion notification, run one foreground non-sleeping same-step sentinel probe only: `test -f "$IMPLEMENT_TMPDIR/.completed/step-3-terminal"` for `implement-step3-checks`, or `test -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal"` for `implement-step5-review`. The braced forms `test -f "${IMPLEMENT_TMPDIR}/.completed/step-3-terminal"` and `test -f "${IMPLEMENT_TMPDIR}/.completed/step-5-terminal"` are equivalent, and a single leading `IMPLEMENT_TMPDIR=<absolute-path>;` prefix is allowed when the variable is unexported. When the same-step sentinel is present, retry the just-denied output read once. For Step 5 only, absent `.completed/step-5-terminal` together with a regular, non-symlink `$IMPLEMENT_TMPDIR/.step5-wrapper-detached` marker is expected signal detach, not hook inconsistency or `stall-step-5`; re-invoke the Step 5 immediate-background launcher fence and wait again. When it is absent after a genuine completion notification, do not wait for another notification; treat it as a tool/hook inconsistency and route through that step's existing failure or stall handling. Step 8 uses one foreground non-sleeping `IMPLEMENT_TMPDIR=$(awk 'BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null); test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` at notification time, hook-allowed only while `implement-step8-ship` is live and clamped when rc stays absent. If the Step 8 rc is absent, the notification is premature; end the turn. If present, continue to `route-exit` in the same turn. NEVER launch a background recovery waiter (`until [ -f … ]; do sleep 60; done`). Do NOT fall back to Monitor. Do NOT spawn multiple Monitor calls watching logs or PID exits.

9. **NEVER branch Step 2 on `STATUS` before completing §2.1.5 envelope validation.** **Why**: the dispatcher emits `ORCHESTRATOR_EDIT_AUTHORITY=allowed|forbidden`, with `allowed` iff `STATUS=claude_fallback`; any illegal pairing or malformed envelope lets the main agent mutate the tree while an external implementer owns commits (issue #1058). **How to apply**: after parsing §2.1 KV stdout, always run all §2.1.5 checks before §2.2 branches on `STATUS`. On failure, synthesize `orchestrator-envelope-invalid`; do not enter Step 3 or consume `MANIFEST`.

10. **(removed — see issues #2485 / #2487; the post-/design boundary halt rule and its archival hook scripts were deleted after the issue-anchored cutover.)**

11. **NEVER write, recreate, or modify `$IMPLEMENT_TMPDIR/finalize-state.sh` from prompt-side orchestrator code.** **Why**: `python/ship.py` writes it on terminal driver outcomes before returning JSON; a prompt-side subset triggers `state-file missing required key` teardown cascades and stale session tmpdirs. **How to apply**: do NOT write it by `cat`, `printf`, `echo`, Write, `sed -i`, `tee`, or any other means. The only pre-teardown reconstructor is conditional `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session restore-finalize-state`, per Step 18. If `python/cli.py implement-finalize teardown` reports `state-file missing required key` and `ship-pr-state.sh` is absent, surface the error and stop; do NOT compose the file from prompt-side shell variables. See Step 18 teardown.

12. **NEVER write, append to, or recreate `$IMPLEMENT_TMPDIR/session-env.sh` from prompt-side orchestrator code.** **Why**: child scripts read it on each invocation; prompt-side `>>`, heredoc rewrites, or `printf` fixups bypass the writer's anchored filter and post-condition assertion, reproducing issue #2326's incomplete Step 1 materialization. **How to apply**: sanctioned writers are `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session write-env`, `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session setup`, `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session persist-run-flags`, and `_persist_larch_run_id()` in `python/bootstrap.py`. The plan file is always `$IMPLEMENT_TMPDIR/plan.txt`; child scripts do not read `PLAN_FILE` from `session-env.sh`. If plan logging or Step 5 fails because that path is missing, repair Step 1 materialization. The orchestrator may only READ via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key` or invoke the sanctioned writers.

13. **(removed — see issue #3111 Stage 4; Family-B background+monitor pairs are deleted.)**

14. **NEVER silently drop a voted-in OOS finding.** **Why**: accepted OOS blocks are the durable contract between reviewers, manifests, and Step 9a.1 disposition. Losing them breaks auditability and follow-up tracking. **How to apply**: non-security accepted OOS is filed by the pre-driver `${CLAUDE_PLUGIN_ROOT}/python/cli.py oos file` path before `step-8-ship.sh`; that path owns disposition-checkpoint, run-statistics, and manifest `steps_ran.step9a1` stamping via `python/oos_filer.py:_after_checkpoint`. Bash `/issue` batch filing is legacy Step 9a.1 only. On `NEXT_ACTION=oos-pipeline`, read `$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` `## Security Findings in OOS Workflows` privately with no public `/issue`, clear the sidecar only after private disposition completes, then run the Step 8 checkpoint wrapper with no `/issue` call. Do not run prompt-side direct `oos disposition-checkpoint`, compose run statistics, or patch `OOS_PENDING=false` outside that wrapper.

15. **NEVER set `OOS_PENDING=false` outside `python/cli.py implement step-8-oos-checkpoint` success** (fork-mode and `repo_unavailable=true` skip this gate intentionally). **Why**: `OOS_PENDING` gates ship-pr progress until accepted OOS blocks have filed issue URLs, `Inline-triage rule N:` breadcrumbs, rejection markers, or private security disposition. **How to apply**: invoke the checkpoint wrapper after security-sidecar disposition when applicable and before or at the Step 8 OOS checkpoint wrapper on the `oos-pipeline` branch, or after pre-driver `oos file` on the normal path. Only checkpoint `NEXT_ACTION=reship` may write run statistics, stamp the manifest, and clear `OOS_PENDING=false` through the allowed-key patch helper.

16. **NEVER make any git commit after the PR has merged**, regardless of branch or path, including `larch-logs/`. **Why**: #2182 sets the trade-off: post-merge log content MAY be lost, but `/implement` MUST NOT advance repo history after merge, especially on `main`. Commits after `$IMPLEMENT_TMPDIR/post-merge-sentinel` strand on local main and can break later cleanup or pulls. Past regressions: #2120, #2128, #2140, #2182, #2552. **How to apply**: all post-merge git commits are policy violations. `python/cli.py run-log` mechanically blocks `run-log commit` after the sentinel and honors no bypass env var. Do NOT add bypass env vars or callers that commit after the sentinel. Do NOT re-render and commit the final summary; re-render in tmpdir only. `python/cli.py final-report write --comment-only` must remain API-only. If merged-outcome data must land in `larch-logs/`, write it BEFORE squash-merge as speculative `OUTCOME=merged` in `final-summary.md` and roll back on merge failure. See `docs/run-log-cli.md` and Python ship driver docs.
17. **NEVER write a free-form natural-language recap summary at end of turn after Step 17**: including but not limited to a "Run complete." / "Implementation merged." prose line, a bullet list summarizing PR / Version / Changes / Code review / CI / Tracking issue, a parenthetical cost paraphrase (for example `~$10.46`, `~$X total`), or any natural-language replacement for the structured `## /implement run ...: <outcome>` block rendered into `summary-final.md` by `python/cli.py implement step-16-17` through `python/cli.py implement step-17 --no-print-stdout` and marker extraction. **Why**: free-form summaries either omit the canonical `- **Cost**:` line or paraphrase it as a TOTAL-only figure, dropping the per-agent breakdown (`Claude $X, Codex $X, Cursor $X`) users depend on. **How to apply**: follow the marker-first profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` with `/implement` markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`. Step 17 binds the source to captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout, not `<task-notification>` output. Step 18b binds the source to captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout on `NEXT_ACTION=finalize-done`, or captured foreground `step-18.sh --phase finalize` Bash wrapper stdout on the stall-recovery path, not `<task-notification>` output. Read fallback is `forbidden` for Step 17 and Step 18b. Sidecar follow-on is `forbidden`. After Step 17 top-chat emission, write `$IMPLEMENT_TMPDIR/.step17-emitted` as the top-chat-emission sentinel and immediately continue to Step 18. `python/cli.py implement step-16-17` owns `.step17-printed` after marker printing; the orchestrator owns `.step17-emitted` only after top-chat emission. Emit only warning repeats and the machine footer required by Step 18 prose. Do NOT add a closing recap, do NOT echo the structured block in your own words, and do NOT mention costs in your own prose. The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission from the shared marker-first profile using the Step 17 source or the branch-qualified Step 18b source. **Verbatim means the entire marker body without omission or condensing.** Do NOT wrap any section in `<details>`, collapse or omit `### Round N reviewer timing` ASCII bar charts, or drop the `**Top reviewers**` list. Every part of the marker body, including all Gantt timing sections, must appear as plain chat markdown exactly as it appears between the markers. The missing-marker warning is printed only when `EMIT_BODY=true` and `WFR_RC=0`. The wrapper writes `.step17-emitted` before Step 18b when `--step17-emitted true`, and touches it before teardown when emitting markers. The orchestrator does not write `.step17-emitted` after finalize returns.

18. **NEVER spawn Agent-tool subagents for code-writing work during Step 18a stall recovery.** **Why**: recovery is a single-runner continuation; Agent-tool code edits bypass stall classification, retry caps, and atomic `STALL_TRACKING` clear ordering. **How to apply**: for `step2-impl`, main Claude reads `$IMPLEMENT_TMPDIR/plan.txt`, edits inline, checks, commits, and continues in the current run. Review and ship wrappers may still use their documented external lanes.

19. **NEVER print code-flow diagram bodies to chat.** **Why**: diagram content belongs only in the issue-scoped `larch:diagrams` comment and PR body, and printing it bloats context. **How to apply**: do not print `$IMPLEMENT_TMPDIR/code-flow-diagram.md`, `$IMPLEMENT_TMPDIR/code-flow-section.md`, or any `## Code Flow Diagram` section body. Step 7a emits breadcrumbs and KVs only.

20. **NEVER copy diagram failure captures into committed implement run logs.** **Why**: generator or sanitizer captures may contain partial Mermaid. **How to apply**: do not copy or flush `code-flow-diagram.failure.log`, code-flow diagram body files, or generator/sanitizer stdout containing Mermaid into `larch-logs/implement/<RUN_ID>/`; durable diagnostics are bounded `execution-issues.md` warnings only.

21. **NEVER make Edit, Write, or repo-mutating Bash calls on git-tracked paths between Preflight item 6 and `BOOTSTRAP_NEXT=step2`.** **Why**: before `step-0-bootstrap.sh` returns `BOOTSTRAP_NEXT=step2`, repo edits can land on the pre-branch checkout and bypass the dirty-tree checkpoint, as in issue #5341. Partial exits (`dirty-recovery`, `degraded-prompt`) also keep edits forbidden until resume yields `BOOTSTRAP_NEXT=step2`. **How to apply**: Preflight item 6 is a **read-only bounded probe** for git-tracked paths (`test -f`, `test -e`, targeted `rg`/`grep`) except `$PREFLIGHT_TMPDIR/**` writes and the stale-notice `gh issue comment`. Deeper investigation waits for `BOOTSTRAP_NEXT=step2`. Do not call Edit, Write, or repo-mutating Bash on git-tracked paths until bootstrap returns exit 0 and `BOOTSTRAP_NEXT=step2`. **Carve-out — rebase-routing**: after Step 0 returns exit 0 with `BOOTSTRAP_NEXT=rebase-routing`, follow `rebase-checkpoint-routing.md`; conflict-resolution edits on the feature branch are permitted. Repeat this gate before every `step-0-bootstrap.sh` fence until `BOOTSTRAP_NEXT=step2`.

**Single-runner assumption**: run one `/implement` per repository at a time. Concurrent sessions can interleave working-tree mutations, corrupt dirty-tree probes, or attribute one runner's edits to another. Dirty-tree guards reduce blast radius but do not serialize writes. Between Step 0 and documented checkpoint probes, `/implement` and child skills write only to session tmpdirs (`$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, `$REVIEW_TMPDIR`) until implementation intentionally edits the repo.

**Mode matrix**:

| Mode | PR target | Tracking issue lifecycle | Version bump | CI base comparison | Merge |
|---|---|---|---|---|---|
| Default | `$REPO` from session setup | enabled | skipped (Phase 1) | `origin/main` | skipped |
| `--merge` | `$REPO` from session setup | enabled | skipped (Phase 1) | `origin/main` | enabled |
| `--forked` | `$FORK_REPO` from origin | disabled | disabled | `upstream/main` | disabled |

## Progress Reporting

Every step MUST print breadcrumb status lines per shared/progress-reporting.md: start lines on entry, bounded progress lines for long work, and completion lines from wrappers.

**MANDATORY at session start**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-name-registry.tsv` to get the Step Name Registry (step number → short name mapping for progress breadcrumbs).

**Phase 1 (#3364)**: Do not print orchestrator `🔶` / `⏩` / `✅` breadcrumbs for ship-pr substeps **8** — the ship PR state machine is Python-driver-owned; the Python ship driver owns any internal ship stdout only.

**Step 8b force-push-gate rebase conflicts (partial auto-resolution):** when the active Python driver hits a Step 8b rebase conflict, `postbump` auto-resolves conflicts confined to known regeneratable generated files (`config.REBASE_AUTORESOLVE_GENERATED_FILES`, currently `python/skill-closure-baseline.json`) by regenerating them and continuing the rebase. Any conflict outside that allow-list now keeps the rebase in progress, persists `RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`, and `CONFLICT_FILES`, then lets `ship route-exit` emit `NEXT_ACTION=conflict-fix`. Do not invent conflict metadata prompt-side beyond the driver-provided `CONFLICT_FILES`.

## Extracted Script Registry

Load `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/extracted-script-registry.md` only when editing or auditing extracted `/implement` script contracts.

## Bash block prelude

The Claude Code Bash tool does NOT preserve shell state between calls. Step 0 emits `$IMPLEMENT_TMPDIR/larch-run.sh` and the PID-keyed stable launcher, using the top-level Bash-tool `$PPID` captured by the Step 0 fence. Every post-Step-0 Bash fence that calls a plugin script MUST delegate through that stable launcher:

```text
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" <relative-script-path> ...
```

Post-Step-0 fences have exactly one nonblank, noncomment physical line. Do not source `plugin-root.env` inline, source session pointers, export variables, use continuations, or add inline shell logic. The `LARCH_CLAUDE_PID="$PPID"` prefix on the Step 0 fence is a plain environment-variable-prefix assignment, not post-Step-0 shell logic. Put foreground markers, anti-halt reminders, and rationale in prose outside fences. Each fence is a thin launcher invocation.

Pre-bootstrap fences keep their existing shapes. Step 0 initial bootstrap may keep the source guard plus the one-line `LARCH_CLAUDE_PLUGIN_ROOT=` awk fallback from `$IMPLEMENT_TMPDIR/session-env.sh`. The single Preflight helper fence may keep its inline `preflight_args` assembly. Do not generalize those old shapes to post-Step-0 fences.

Sourcing full `session-env.sh` remains forbidden because it imports the whole namespace and can shadow caller state. `python/bootstrap.py` emits the tmpdir-local launcher only after Step 0 `session write-env` succeeds, then `session write-implement-env` writes the PID-keyed stable launcher. All later script argv assembly belongs inside wrappers.

## Verbosity Control

Follow shared/verbosity-control.md rules.

**Preserved:** step breadcrumbs (`🔶`, `⏩`, `⏭️`), warning/error lines, structured summaries, plans, design decisions, code-review findings, and the final report.

**Suppressed:** explanatory prose, script paths, inter-call rationale, and per-reviewer completion messages. Rebase-skip cases at Steps 1.r, 4.r, 7.r, and 7a.r silently continue unless the referenced routing file says otherwise.

## Rebase Checkpoint Macro

Standardizes post-step rebase checkpoints 1.r, 4.r, 7.r, and 7a.r. Step 4.r is folded into Step 3 `checks-commit-route`; 7.r into Step 6 `step-6-entry`; 7a.r into `step-7a`. Each site routes through `rebase-checkpoint-routing.md` only when its composite emits `CHECKPOINT_NEXT=load-routing` or a malformed/missing routing KV.

**Thin implementation**: `${CLAUDE_PLUGIN_ROOT}/python/cli.py push checkpoint-probe` owns full argv, exit codes, and KV grammar in `skills/implement/references/rebase-checkpoint-routing.md`. Checkpoint **4.r** is folded into Step 3, **7.r** into Step 6, and **7a.r** into Step 7a. The absorbed **1.r** checkpoint is inside Step 0 bootstrap; route only on `BOOTSTRAP_NEXT=rebase-routing` and load the routing reference then.

**Registry identifiers:** `1.r` / `1.m` remain stable macro `<step-prefix>` tokens listed in `skills/implement/scripts/step-name-registry.tsv`; they label internal rebase checkpoints, not standalone orchestrator steps after plan materialization folded into Step 0.

**Conditional routing reference**: Absorbed `1.r`: branch only on `BOOTSTRAP_NEXT=rebase-routing` from the Step 0 bootstrap stdout envelope. Parse `ROUTE=`, `REBASE_RC=`, conflict detail KVs, and advisory `PHANTOM_*`. If `ROUTE=conflict` but no conflict files are present because the rebase auto-committed after earlier conflict resolution, follow `rebase-checkpoint-routing.md` phantom-probe instructions. When `DEGRADED_PROMPT_REQUIRED=true` on the absorbed `1.r` path, **MANDATORY: READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` for degraded-prompt handling before treating absent routing keys as rebase failure. Folded `4.r`, `7.r`, and `7a.r`: parse `CHECKPOINT_NEXT=continue|load-routing` from captured stdout. `CHECKPOINT_NEXT=continue` is the only macro no-op predicate (skip the routing reference). Missing or malformed `CHECKPOINT_NEXT` fails closed: **MANDATORY: READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/rebase-checkpoint-routing.md`. On `CHECKPOINT_NEXT=load-routing`, load that reference and branch on `ROUTE=`, `REBASE_RC=`, `REBASE_OUTCOME=`, and related KVs inside it. Do not use `ROUTE=continue` alone as the skip predicate when `CHECKPOINT_NEXT` is missing or malformed. The `7.r` macro skip is `CHECKPOINT_NEXT`-only. The `7a.r` macro skip is `CHECKPOINT_NEXT`-only.

## Checks Failure Entry Macro

Use this macro after Step 3 emits `STATUS=fail` or a folded composite emits `NEXT_ACTION=checks-failed`; the failure path remains in-step. Call sites should invoke **Checks Failure Entry Macro** by name with their pinned `--site` / `--checks-site` arguments instead of restating these read steps.
1. At folded sites, key-scan the full composite stdout for both `DIGEST_FILE` and `REDACTED_LOG_FILE`, not only the first physical composite line. Read `DIGEST_FILE` first when it is present and readable. Fall back to `REDACTED_LOG_FILE` when the digest is absent, unreadable, or insufficient. Never read raw `LOG_FILE`. `REDACTED_LOG_FILE` remains the input passed to `checks repair-loop`.
2. **MANDATORY: READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/checks-repair-loop.md`.
3. Follow that reference's pinned site split for the call site, including re-entry and folded-site recapture rules.

## Durable Bail to Step 18 Macro

**MANDATORY: READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step5-review-branches.md`; follow its **Durable Bail** section with pinned `STALL_STEP=5`.

## Flags

**Invocation contract**: `/implement` consumes one positional GitHub issue number (`<issue-N>` digits). `/design` owns plan authoring and writes the `larch:plan` block into the issue body.

**Flags**: Parse flags from the start of `$ARGUMENTS` before the positional issue. Flags may appear in any order. **All boolean flags default to `false`.** Set a mental flag to `true` only when its listed token appears. `--force` and `-f` both set `force_requested=true`. Strip recognized flags before binding the issue.

| Flag | Default | Purpose |
|------|---------|---------|
| `--merge` | `false` | Enable CI+rebase+merge loop (Steps 12–15) and related merge surfaces |
| `--no-admin-fallback` | `false` | Forward into Step 12b `python/cli.py merge pr` — plain merge only after admin-eligible gate |
| `--no-logs-commit` | `false` | Suppress larch-log flush commits under the Python ship driver / refresh helpers |
| `--forked` | `false` | Fork-CI dry-run against `origin` / `upstream/main`; disables tracking-issue lifecycle, merge |
| `--draft` | `false` | Create PR as draft; implies no merge loop |
| `--force` / `-f` | `false` | Skip the item 4 plan-adequacy audit entirely (no `AUDIT=refuse` result exists to downgrade). Downgrade the three remaining fail-closed Preflight gates — missing plan, malformed plan, and `missing-designed-prefix` — to warn-and-proceed; warn loudly on each triggered bypass. Keeps the helper-side plan-block fallback. Does not affect coder selection. |
| `--self-review` | `false` | Skip the external review panel; main agent performs a thorough inline self-review at Step 5 instead |
| `--self-implement` | `false` | Force `coder=claude` (main agent implements directly; external implementers are skipped), independent of `--force`. |
| `--difficulty <TRIVIAL\|MODERATE\|HARD>` | empty | Set the starting Step 5 review tier. The override beats rating and floors, logs `override_source=operator`, and the 1:30 audit can still upgrade a below-HARD run while preserving both fields. |
| `--coder` | unset | Pin external implementer to claude, codex, or cursor when set; otherwise availability waterfall. Ignored when `--self-implement` is active (always forces claude). |
| `--run-id <ID>` | empty | Optional stable run id |

**Mutual exclusion**: reject `--forked` with `--merge`, `--draft` with `--merge`, and `--force` / `-f` with `--draft`, printing the exact warning named by the pair and exiting before Preflight. (`--force` / `-f` and `--merge` are **compatible**: use both for a forced fix through CI and automatic merge.) The `--force` / `-f` and `--draft` together case uses the third warning. Exact warnings: `**⚠ --forked and --merge are mutually exclusive. Aborting.**`; `**⚠ --draft and --merge are mutually exclusive. Aborting.**`; `**⚠ --force and --draft are mutually exclusive. Aborting.**`.

**Positional `<issue-N>` (required)**:

1. After flag parse, **exactly one** positional token must remain and MUST match `^[0-9]+$`. Bind it as `TARGET_ISSUE_NUMBER` for Preflight and Step 0 tracking adoption (authoritative subject issue for the run).
2. If any **non-flag** token remains that is **not** all digits (a verbal feature description or extra args), print verbatim:

`**❌ /implement no longer accepts a verbal feature description. Run /design <issue-N> first to write a plan to the issue body, then re-run /implement <issue-N>.**`

and exit **2** (orchestrator stop — do not start Preflight or Step 0).

3. Removed argv surfaces (must not be accepted as flags here): `--auto`, `--quick`, `--inline`, `--design-only`, `--no-issues`, `--hard`, `--issue`, `--session-env`, `--subagent`, `--design-classification`, `--branch-info`, `--step-prefix`, `--full`, `--dynamic-archetypes`, `--no-dynamic-archetypes`, `--emergency` (replaced by `--force` / `-f`; when `--emergency` is present print `**⚠ /implement --emergency is removed. Use --force or -f instead. Aborting.**` and exit **2** before Preflight).

**`--forked`**: compatible with `--draft`, `--no-logs-commit`, and `--coder`, subject to `--merge` / `--draft` exclusions above. Disable tracking-issue lifecycle. Treat `TARGET_ISSUE_NUMBER`, when set, only as **`UPSTREAM_DESIGN_ISSUE`** context in Step 0 fork tracking resolution, not as a local tracking issue.

## Preflight — issue-anchored plan

Run **before Step 0** after `TARGET_ISSUE_NUMBER` is known and flag mutex checks pass. Use a shell `mktemp -d` preflight tmpdir, not `$IMPLEMENT_TMPDIR` (not created until Step 0). Keep `PLAN_TMP="$PREFLIGHT_TMPDIR/plan-from-issue.txt"` through Step 0 materialization. When `forked_target=true`, `UPSTREAM_REPO` MUST already come from Protocol `python/cli.py admission fork-env`. Run `admission fork-env`, then the preflight helper, then Step 0 bootstrap.

**Force mode (`--force`)**: when `force_requested=true`, read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/force-mode.md` completely before applying force behavior. Inline item 4 remains authoritative for the skip breadcrumb and no-read / no-audit-file / no-bypass-log contract.

1. **Mechanical Preflight helper (items 1-3)** — `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight` is the sole mechanical Preflight surface for admission, issue fetch, plan extraction, force missing/malformed fallback composition, and zero-review provenance refusal (`panel-init-failed`, `panel-skipped`, `rounds_completed: 0`). Invoke it through the Python CLI:
   ```bash
   [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
   export IMPLEMENT_TMPDIR

   preflight_args=(--issue "$TARGET_ISSUE_NUMBER" --preflight-tmpdir "$PREFLIGHT_TMPDIR")
   if [ -n "${UPSTREAM_REPO:-}" ]; then
     preflight_args=("${preflight_args[@]}" --repo "$UPSTREAM_REPO")
   fi
   if [ "${force_requested:-false}" = true ]; then
     preflight_args=("${preflight_args[@]}" --force)
   fi

   python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight "${preflight_args[@]}"
   ```
   The helper writes `$PREFLIGHT_TMPDIR/issue.json`, `$PREFLIGHT_TMPDIR/plan-from-issue.txt`, and `$PREFLIGHT_TMPDIR/force-bypass.log` only for bypasses.

   After the helper returns:
   - Capture stdout from the Bash tool result.
   - On non-zero exit, abort before item 4 and preserve the helper's exit semantics.
   - Do not parse or require an envelope on non-zero exit.
   - On exit `0`, parse the validated seven-key success envelope; `python/cli.py implement preflight` self-validates the success envelope and exits `2` before success parsing when malformed.
   - Parse one `KEY=value` record per line.
   - Split each envelope line at the first `=` only and preserve the remaining value verbatim.
   - Ignore non-envelope warning or prose lines that do not begin with an allowed envelope key plus `=`.
   - Parse only exact allowed preflight envelope keys: `ADMISSION_RESULT`, `RESUME`, `TITLE`, `BLOCK_PRESENT`, `PLAN_PATH`, `ISSUE_JSON_PATH`, and `BYPASS_COUNT`.
   - Bind `PLAN_TMP` from `PLAN_PATH`.

4. **Plan-adequacy audit (main agent, in-prompt only)** — **When `force_requested=true`, skip this audit entirely.** This force audit-skip branch is the first control-flow instruction in item 4 and runs before any mandatory read below: print one skip breadcrumb `⏭️ /implement --force: skipping plan-adequacy audit for issue #<N>; continuing to semantic materiality.`, then jump directly to item 6. On the force audit-skip branch, do **not** read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md`, do **not** create or overwrite `$PREFLIGHT_TMPDIR/audit.txt`, and do **not** append to `$PREFLIGHT_TMPDIR/force-bypass.log` — the audit skip is not a downgraded gate and writes no bypass-log entry.

   **When `force_requested=false` (only)** — **MANDATORY: READ ENTIRE FILE** at Preflight item 4: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md`. Read issue title/body from `$PREFLIGHT_TMPDIR/issue.json` and plan text from `$PLAN_TMP`. Do not fetch the issue live or rerun plan-block extraction. On `AUDIT=pass`, return the pass envelope in chat only and do not write `$PREFLIGHT_TMPDIR/audit.txt`. On `AUDIT=refuse`, write that file. Do **not** delegate to a subagent or external audit CLI.

5. **On `AUDIT=refuse`** — read `audit.txt` only on refuse. This non-force-only path follows `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md` for clarify state, comment, and label flow, then exits **3** before Step 0.

6. **On `AUDIT=pass` or the force audit skip — semantic materiality (read-only bounded probe — see NEVER #21)** — run one batched read-only Bash probe over plan-cited paths and symbols (`test -f` / `test -e`, plus targeted `rg` for named functions, flags, markers, or step anchors). Do not mutate git-tracked paths before `BOOTSTRAP_NEXT=step2`. `$PREFLIGHT_TMPDIR/**` writes and the stale-notice `gh issue comment` are the only carve-outs. If the bounded probe clearly shows the issue is stale (superseded design, removed surface, or no migration path), redact a short explanation into `$PREFLIGHT_TMPDIR/stale-notice.md`, post one `gh issue comment <N> --body-file "$PREFLIGHT_TMPDIR/stale-notice.md"` (with `--repo "$UPSTREAM_REPO"` when forked), and exit **2**. Retry the same comment once on failure; if both fail, say the stale-notice comment was **not** posted and exit **2**. Do not close or rename the issue. If staleness is not clear, continue to Step 0 without broader investigation.

7. **Preflight pass gate**: retain `PREFLIGHT_TMPDIR` and `plan-from-issue.txt`; proceed to Step 0.

**Preflight — admission gate known limitation (D3)**: `python/cli.py admission gate` inherits `python/blocker.py`'s historical **fail-open** posture on `gh` / API failures. API outages can yield zero detected blockers (`ADMISSION_RESULT=pass`) even when blockers are unknown. Operators needing strict fail-closed blocker reads must pause runs during outages; see `python/admission.py`. **Native-first short-circuit**: native dependency API blockers skip the prose scan for speed, so operator-visible lists may omit prose-only blockers until native blockers clear.

### `/implement` orchestrator exit codes (Preflight + argv)

| Code | When |
|------|------|
| **0** | Normal completion of the scripted skill path. |
| **2** | Flag mutual-exclusion, verbal/non-numeric argv tail, missing/malformed `larch:plan` when not bypassed by `--force`, empty issue body and empty title under `--force` (nothing to implement), `gh` / `python/cli.py plan-block read` / admission hard failures (except `missing-designed-prefix` when bypassed by `--force`), semantic stale notice posted at Preflight item 6, `persist-implement-run-flags` validation failures, and other operator-visible hard errors where this file specifies exit **2**. |
| **3** | **Preflight audit refused** — `AUDIT=refuse` exits **3**. Follow `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md` `## Clarify-request flow after AUDIT=refuse` for post, label, `STATE=ambiguous`, and `STATE=awaiting-response` behavior. **Force note**: `--force` skips the item 4 plan-adequacy audit before any `AUDIT=refuse` result exists, so this exit-**3** refuse path is unreachable under `--force`. |

<!-- step:0 — Session Setup -->
## Step 0 — Session Setup

Print: `> **🔶 /implement 0: setup**`

Step 0 is owned by `python/bootstrap.py` via `python/cli.py bootstrap invoke` (`--mode initial` / `--mode resume`). The foreground bootstrap handles setup, tracking adoption, plan materialization, dirty-tree checkpointing, branch capture, plan logging, and implementer selection (`phase_coder_select`). The wrapper forwards `/implement --force`, `/implement --self-review`, and `/implement --self-implement` via `case "${force_requested:-}" in` / `case "${self_review:-}" in` / `case "${self_implement:-}" in` so omitted flags stay omitted from bootstrap argv. Do not duplicate absorbed helper calls prompt-side. When `self_implement_requested=true`, `phase_coder_select` forces `coder=claude` regardless of `--coder` or tool availability; `--force` alone no longer affects coder selection. Use `SELF_REVIEW_REQUESTED` from the routing envelope to set `self_review` after parse when flag parsing did not already set it.

Wrapper reachability: `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh` forwards `--difficulty` when set and delegates to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bootstrap invoke`; the prompt-side entry remains the Step 0 wrapper below. `python/bootstrap.py` captures `BRANCH_NAME` after branch creation via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git current-branch`.

**Bootstrap edit gate (NEVER #21)**: do not call Edit, Write, or repo-mutating Bash on git-tracked paths until bootstrap exits 0 with `BOOTSTRAP_NEXT=step2`. The feature branch is created inside `step-0-bootstrap.sh`. On `dirty-recovery` or `degraded-prompt`, repo edits remain forbidden until resume yields `step2`. Repeat this gate before every `step-0-bootstrap.sh` fence (initial and `--mode resume`) until `BOOTSTRAP_NEXT=step2`. **Carve-out — rebase-routing**: when bootstrap returns `BOOTSTRAP_NEXT=rebase-routing`, follow `rebase-checkpoint-routing.md` for feature-branch conflict-resolution edits.

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
export IMPLEMENT_TMPDIR
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
export CLAUDE_PLUGIN_ROOT
# Foreground required
LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode initial --issue-number "$TARGET_ISSUE_NUMBER" --preflight-tmpdir "$PREFLIGHT_TMPDIR" --force-requested "${force_requested:-false}" --self-review-requested "${self_review:-false}" --self-implement-requested "${self_implement:-false}" --forked-target "${forked_target:-false}" --merge-requested "${merge:-false}" --draft-requested "${draft:-false}" --no-admin-fallback "${no_admin_fallback:-false}" --no-logs-commit "${no_logs_commit:-false}" --upstream-repo "${UPSTREAM_REPO:-}" --run-id "${RUN_ID:-}" --caller-env "${CALLER_ENV_PATH:-}" --session-env "${SESSION_ENV_PATH:-}" --coder "${coder:-}" --difficulty "${difficulty:-}"
```

Parse the current routing envelope from wrapper stdout. `$IMPLEMENT_TMPDIR/bootstrap-routing.env` is a durable helper cache; do not source it prompt-side as the current result. On `--mode resume`, `python/cli.py bootstrap invoke` preserves prior non-empty `coder` / `coder_fallback` values in cache and stdout if the resume tail does not rerun implementer selection. `python/bootstrap.py` is the bootstrap behavior contract; `step-0-bootstrap.sh` is the wrapper contract. Offline harnesses: `skills/implement/scripts/test-python/bootstrap.py` (+ `python/test_bootstrap.py`) and `skills/implement/scripts/test-python/cli.py bootstrap invoke` (+ `python/test_bootstrap.py`). On wrapper exit `0`, require `BOOTSTRAP_NEXT` in `step2|dirty-recovery|degraded-prompt|rebase-routing|cleanup`; if `BOOTSTRAP_NEXT` is absent or any other value, treat the bootstrap envelope as malformed and abort with exit `2` without legacy inference. Routing after parsing:

| `BOOTSTRAP_NEXT` | Routing |
|---|---|
| `BOOTSTRAP_NEXT=step2` | Proceed directly to Step 2 with `--coder "$coder"`. |
| `BOOTSTRAP_NEXT=degraded-prompt` | **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely. Execute the degraded-prompt branch. |
| `BOOTSTRAP_NEXT=rebase-routing` | **MANDATORY: READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/rebase-checkpoint-routing.md`. Parse `ROUTE`, `REBASE_RC`, conflict detail KVs, and advisory `PHANTOM_*` KVs from the Step 0 envelope; Python already selected conflict, bail, or malformed/absent post-1.r `ROUTE` details. |
| `BOOTSTRAP_NEXT=dirty-recovery` | **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely. Execute the dirty-recovery branch. |
| `BOOTSTRAP_NEXT=cleanup` | Do not enter Step 2; skip to Step 18 cleanup after required local-only cleanup. |

**Absorbed continue tail.** On the continue path (`IMPLEMENT_BAIL_REASON` empty, `STALL_TRACKING=false`, readable `PLAN_FILE`, non-empty `coder`), `python/cli.py bootstrap invoke` runs the degraded-tools gate and checkpoint `1.r` internally and folds KVs into Step 0 stdout. `step-0-bootstrap.sh` forwards `--non-interactive true|false` from the canonical predicate in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md`; do not rely on `LARCH_SKILL_NON_INTERACTIVE` alone. One-down bootstrap emits `DEGRADED_PROMPT_REQUIRED=true` and stops before 1.r until the explicit Continue sentinel exists. Both-down emits `DEGRADED_HARD_FAIL=true` and stops in every mode. Advisory `PHANTOM_*` KVs appear only on Step 0 stdout, not `$IMPLEMENT_TMPDIR/bootstrap-routing.env`. Do not use `CODEX_STATE` or `CURSOR_STATE` as the operator explanation when stderr relayed the full degraded block.

**Step 1.r routing.** For checkpoint `1.r`, enter rebase handling only when `BOOTSTRAP_NEXT=rebase-routing` appears in the Step 0 bootstrap envelope. In that branch, use `ROUTE=`, `REBASE_RC=`, conflict detail KVs, and advisory `PHANTOM_*` from the same envelope. Step `4.r` is folded into the Step 3 `checks-commit-route` composite; `7.r` is folded into the Step 6 `step-6-entry` composite and `7a.r` into `step-7a`, each relaying `CHECKPOINT_NEXT=continue|load-routing` for the same **Rebase Checkpoint Macro** routing (`continue` skips the reference; `load-routing` or missing/malformed values load it).

`phase_coder_select` is the only omitted-`--coder` authority for Step 0. Explicit `--coder=claude` does not set `coder_fallback=true`; only the implicit waterfall Codex → Cursor → Claude emits that flag when it reaches Claude. `diff_lines: <N>` in `plan.txt` is informational sizing context and does not route the implementer.

`session-env.sh` reaches `review-and-fix CLI` in Step 5 via `--session-env-path`. Later Bash fences delegate through `$IMPLEMENT_TMPDIR/larch-run.sh`; wrappers read token, timing, stall, and run-id keys internally from `$IMPLEMENT_TMPDIR/session-env.sh` via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key`. `LARCH_RUN_ID` is written by `_write_base_session_env()` after `_phase_tracking()` resolves `RUN_ID`, not by the initial Step 0 `session write-env` call.

### Cross-Skill Presence Propagation

No cross-skill presence propagation action is required; this anchor preserves the post-review boundary chain.

## Phantom Untracked Probe

Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/phantom-probe.md` only when changing probe call sites. Trailing `PHANTOM_*` KVs are advisory telemetry; do not act on them.

## Execution Issues Tracking

Progressive disclosure: do not load `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` at section entry. Load it only for active OOS triage, `Pre-existing Code Issues` dual-write, self-review step 3, or Step 8 `oos-pipeline` call sites.

<!-- step:2 — Implement the Feature -->

Print: `> **🔶 /implement 2: implementation**`

`python/cli.py implement run-dispatch` marks Step 2 token and timing telemetry internally on the first dispatch only. The mark happens after `dispatch.lock` acquisition and is skipped on `--answers` redispatch.

<!-- step:2 entry preconditions — legal next-actions matrix -->

This matrix is authoritative for Step 2. After parsing dispatcher stdout in 2.1 and completing 2.1.5 envelope validation, the orchestrator may take only the rows below. **If 2.2 / 2.4 prose appears to disagree, the matrix wins.** See NEVER #9.

| Resolved `STATUS` | `ORCHESTRATOR_EDIT_AUTHORITY` | Permitted next-actions | Forbidden |
|---|---|---|---|
| `complete` | `forbidden` (required) | Set `MANIFEST_PATH=$MANIFEST`; proceed to Step 3 | Edit, Write, repo-mutating Bash against the **git working tree**; `git diff`-based reconstruction; transcript inspection for diff replay |
| `needs_qa` | `forbidden` (required) | Run Q/A loop in 2.3 (read `$QA_PENDING`, ask via `AskUserQuestion`, **write answers JSON to `$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json` — permitted**, re-invoke dispatcher with `--answers`) | Edit, Write, repo-mutating Bash against the **git working tree** unrelated to redispatch |
| `bailed` | `forbidden` (required) | Log `Step 2 — $TOOL_LABEL bailed: $REASON` to `Warnings`; bail per 2.2's REASON-set routing (Step 12d) | Edit, Write, repo-mutating Bash against the **git working tree**; do NOT attempt to "recover" by editing |
| `claude_fallback` + `RECOVERY_FROM=manifest-schema-invalid` | `allowed` (required) | Run Step 2.4 recovery sub-branch only: plan-scope alignment, commit-message synthesis, no implementation edits | Opportunistic Q/A, main-agent re-implementation, Edit/Write against recovered files, `git add -A`, destructive git cleanup |
| `claude_fallback` | `allowed` (required) | Run Step 2.4 (opportunistic questions; main-agent Edit/Write/Bash code edits per the plan) | None additional |
| any envelope failure (validation in 2.1.5) | n/a | Synthesize orchestrator-local bail with `REASON=orchestrator-envelope-invalid` (see 2.1.5); route as Step 2 → Step 12d hard-bail | Setting `MANIFEST_PATH`; entering 2.3 / 2.4 / Step 3 |

**Always-permitted writes regardless of row**: `$IMPLEMENT_TMPDIR/**` (Q/A artifacts, larch-log records, execution-issues), larch-log and summary publication calls in 2.5, captured `python/cli.py checks run-relevant` helpers, and reads of `TRANSCRIPT` / `SIDECAR_LOG` for warning text extraction (NOT diff reconstruction). The forbidden column scopes to the **git working tree**.

**No mid-run scope re-litigation.** Once Step 2 begins with a plan, the orchestrator does not ask whether to stop for scope, capacity, or effort. Oversize plans should have failed `/design` or Preflight audit. Mid-run, the dispatcher or Claude fallback executes the plan or hits a concrete Step 12d bail. This does NOT suppress Codex Q/A loop questions or Claude-fallback opportunistic ambiguity questions. See NEVER #7.

<!-- step:2 dispatch — coder selection -->

Regression coverage for this dispatcher surface lives in `python/test_implement_dispatch.py`. The launcher and dispatcher contract is `skills/implement/references/step2-dispatch.md`.

**2.1 — First dispatch invocation**:

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement run-dispatch --implement-tmpdir "$IMPLEMENT_TMPDIR" --coder "$coder"
```

**Do NOT poll or print sidecar output while dispatching.** Invoke `python/cli.py implement run-dispatch` through the foreground `larch-run.sh` fence. It synchronously invokes `python/cli.py implement step2-dispatch`; while it runs, do NOT read sidecar logs or print intermediate output. Polling floods the terminal. Parse stdout as KV only after the dispatcher exits.

The launcher `python/cli.py implement run-dispatch` always passes `--plan-file "$IMPLEMENT_TMPDIR/plan.txt"` and no workflow flag; it does **not** assemble paths from `PLAN_FILE` keys in `session-env.sh`. It reads `CURSOR_BINARY_FOUND` / `CODEX_BINARY_FOUND` from `$IMPLEMENT_TMPDIR/session-env.sh` or fresh executable checks, uses `$IMPLEMENT_TMPDIR/feature-description.txt`, and if the Step 0 selected binary is missing, relays `STATUS=claude_fallback` with edit authority instead of hard-failing. Before relaying stdout, it resolves repo root and captures `step2-prelaunch-porcelain.nul` plus prelaunch digests for Step 2.4. Parse `STATUS`, `TOOL`, `MANIFEST`, `QA_PENDING`, `REASON`, `TRANSCRIPT`, `SIDECAR_LOG`, `ORCHESTRATOR_EDIT_AUTHORITY`, and optional recovery triplet `RECOVERY_FROM`, `RECOVERY_PRIOR_TOOL`, `RECOVERY_PATHS_FILE`. Advisory complete-path lines may include `WARN_CODEX_NONZERO_EXIT=true` and plan-file coverage warnings; they never gate 2.1.5. Coverage applies only to firm `### NEW:` / `### UPDATED:` / `### REWRITTEN:` headings, not `### MAY_UPDATE:`. Probe failures suppress coverage KVs and add warn-only execution-issues. Then run 2.1.5 before branching on `STATUS`. Derive:

Set `TOOL_LABEL` to `Codex` for `TOOL=codex`, `Cursor` for `TOOL=cursor`, and `external implementer` for any other tool token.

**2.1.5 — Envelope validation (fail-closed)**:

After parsing 2.1's KV envelope and BEFORE the 2.2 `STATUS` switch, validate:

1. `STATUS` is exactly one of `complete`, `needs_qa`, `bailed`, `claude_fallback`.
2. `ORCHESTRATOR_EDIT_AUTHORITY` is exactly one of `allowed` or `forbidden`, and appears **exactly once** on stdout. Zero or duplicate `ORCHESTRATOR_EDIT_AUTHORITY=` lines are illegal and trigger `orchestrator-envelope-invalid` (mirrors the `grep -c '^ORCHESTRATOR_EDIT_AUTHORITY=' == 1` invariant pinned by `python/test_implement_dispatch.py` Test 11a/11b).
3. The pair is **legal**: `ORCHESTRATOR_EDIT_AUTHORITY=allowed` iff `STATUS=claude_fallback`. Any other combination is illegal.
4. Recovery triplet integrity: if any of `RECOVERY_FROM`, `RECOVERY_PRIOR_TOOL`, or `RECOVERY_PATHS_FILE` is present, all three must be present; `RECOVERY_FROM` must equal `manifest-schema-invalid`; `RECOVERY_PRIOR_TOOL` must be `codex` or `cursor`; `RECOVERY_PATHS_FILE` must point to a readable non-empty file; and `STATUS` must be `claude_fallback`.
5. Status-keyed manifest readability (mirrors the dispatcher contract in `skills/implement/references/step2-dispatch.md` stdout grammar):
   - If `STATUS=complete`: `MANIFEST` is non-empty and points to a readable file. `QA_PENDING` MUST be absent.
   - If `STATUS=needs_qa`: `QA_PENDING` is non-empty and points to a readable file, AND `MANIFEST` is non-empty and points to a readable file.
   - If `STATUS=bailed` or `STATUS=claude_fallback`: this check does not apply (no required manifest path on these branches).

If any check fails, synthesize an orchestrator-local bail: set `STATUS=bailed`, `REASON=orchestrator-envelope-invalid`, log `Step 2 — orchestrator-envelope-invalid: STATUS=<raw> AUTH=<raw> reason=<which-check-failed>` to `$IMPLEMENT_TMPDIR/execution-issues.md` `Warnings`, set `FINAL_BAIL_REASON=orchestrator-envelope-invalid`, `IMPLEMENT_BAIL_REASON=orchestrator-envelope-invalid`, `STALL_STEP=2`, `PHASE=implementation`, `STALL_TRACKING=true`, do NOT consume `MANIFEST`, do NOT enter 2.3 or Step 3, and bail to Step 12d. **`orchestrator-envelope-invalid` is orchestrator-local**, not a dispatcher REASON token.

**2.2 — Branch on `STATUS`**:

- `STATUS=complete` → set `$MANIFEST_PATH=$MANIFEST`, then run the Step 2 post-dispatch wrapper as one foreground Bash invocation:

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-2-post-dispatch.sh --expected-branch "$BRANCH_NAME"
```

From the combined wrapper stdout capture, first token-scan all `PHANTOM_*` KVs per **Phantom Untracked Probe** (advisory), regardless of wrapper exit code. Optionally bind `BRANCH=` and `COMMIT_SHA=` for degraded display persistence. Then parse exactly one `POST_DISPATCH_NEXT=continue|bail`. Missing, duplicated, malformed, or `bail` output prints `**⚠ /implement Step 2: post-dispatch branch mismatch (expected $BRANCH_NAME).**`, appends a sanitized `main-branch-post-dispatch` warning via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log append-entry`, sets `FINAL_BAIL_REASON=main-branch-post-dispatch`, `IMPLEMENT_BAIL_REASON=main-branch-post-dispatch`, `STALL_STEP=2`, `PHASE=implementation`, `STALL_TRACKING=true`, and bails to Step 12d without Step 3. `BAIL_REASON=main-branch-post-dispatch` is required. Missing `COMMIT_SHA=` is not failure. Otherwise proceed to Step 3. Steps 4 / 9a / 9a.1 read this manifest; the orchestrator does not reconstruct changes with `git diff`. The probe runs only inside `skills/implement/scripts/step-2-post-dispatch.sh` on external `STATUS=complete`, after dispatcher commit; do not run it on `STATUS=claude_fallback`.
- `STATUS=needs_qa` → run the Q/A loop in 2.3. Note: the dispatcher may have repaired a non-standard `qa-pending.json` (e.g., `items[]` → `questions[]`) before emitting this status; the Q/A loop always reads canonical `questions[]` format from `$QA_PENDING`.
- `STATUS=bailed` → print and append protected-path or submodule warnings first when `REASON=protected-path-edit-required-out-of-scope` or `REASON=submodule-edit-required-out-of-scope`, using the exact warning strings in this bullet. Then log `Step 2 — $TOOL_LABEL bailed: $REASON` to `Warnings`, mirror `REASON` into `FINAL_BAIL_REASON` and `IMPLEMENT_BAIL_REASON`, set `STALL_STEP=2`, `PHASE=implementation`, `STALL_TRACKING=true`, and bail to Step 12d. Exact warnings: `**⚠ /implement: Codex bailed on protected path .claude-plugin/plugin.json; Main Claude will implement inline.**`; `**⚠ /implement: implementer bailed on submodule-restricted path; submodule edits are blocked for Main Claude too. No automatic inline recovery will run.**` Step 18a passes the in-memory step/phase/bail triplet to `python/cli.py stall-recovery classify`; that classifier sanitizes public bail rendering and prevents compound tokens such as `dirty-state-after-timeout` from substring-matching transient-infra.
- `STATUS=claude_fallback` with `RECOVERY_FROM=manifest-schema-invalid` (with `ORCHESTRATOR_EDIT_AUTHORITY=allowed`, validated mechanically in 2.1.5) → enter the Step 2.4 recovery sub-branch, not the ordinary Claude-fallback implementation branch.
- `STATUS=claude_fallback` without `RECOVERY_FROM` (with `ORCHESTRATOR_EDIT_AUTHORITY=allowed`, validated mechanically in 2.1.5) → run the ordinary Claude-fallback branch in 2.4. If `ORCHESTRATOR_EDIT_AUTHORITY != allowed`, treat as envelope failure per 2.1.5 (do NOT enter 2.4).

**Step 12d hard-bail routing**: when Step 2 bails to Step 12d, mirror `FINAL_BAIL_REASON` / `IMPLEMENT_BAIL_REASON` from dispatcher `REASON` or the synthesized source, set `STALL_TRACKING=true`, set `STALL_STEP` and `PHASE`, and skip Steps 3-15. Execution continues at Step 18, where Step 18a stall recovery runs **before** the Step 16/17 final report per the recover-then-report contract. **Step 12d bail is not terminal.** Step 18a classifies and gates recovery; Step 16/17 renders once at Step 18b for terminal stall or during the natural post-recovery pass, then Step 18b tears down.

**Branch enforcement on `claude_fallback`**: the `cli.py git current-branch` vs `BRANCH_NAME` assertion in the `STATUS=complete` bullet is scoped to `STATUS=complete` only (NEVER #9). On `claude_fallback`, the later `python/ship.py` branch guard compares state `BRANCH_NAME` to the checked-out symbolic branch and refuses `main` or `master` unless `FORKED_TARGET=true` in `ship-pr-state.sh` and checkout still matches. Forked upstream-target flows may use the default branch name in state; every other run stalls before PR prep.

**2.3 — Q/A loop** (when `STATUS=needs_qa`):

1. Read `$QA_PENDING` (a JSON file containing `{"questions": [{"id": "q1", "text": "..."}, ...]}`).
2. Pose the questions to the operator via `AskUserQuestion` in a single batched call (one prompt per question, preserving the `id`). Log every Q/A pair to `$IMPLEMENT_TMPDIR/execution-issues.md` under `### Q/A` per the schema in 2.5 below.
3. Compose an answers file `$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json` with shape `{"answers": [{"id": "q1", "text": "<answer>"}, ...]}` (`$RESUME_N` is the 1-indexed resume cycle counter the orchestrator tracks locally). The filename retains `codex-` for historical compatibility; the dispatcher accepts it for Cursor resumes too.
4. Re-invoke the dispatcher launcher with §2.1 flags plus `--answers "$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json"`. The launcher still derives `$PLAN_FILE`, `$FEATURE_FILE`, and cursor presence from `$IMPLEMENT_TMPDIR/session-env.sh` and conventional paths; `--answers` is the only redispatch addition. **On every dispatcher return, including `--answers` redispatch, re-parse KVs and run §2.1.5 envelope validation in full BEFORE §2.2 branching.** Malformed or AUTH-illegal resume envelopes fail closed as `orchestrator-envelope-invalid`. The dispatcher enforces the 5-cycle cap; the 6th `--answers` invocation returns `STATUS=bailed REASON=qa-loop-exceeded`.

> **Continue to Step 3 IMMEDIATELY after re-dispatch returns.** The Q/A loop re-dispatch is not a halting point — proceed to Step 3 checks as soon as the dispatcher exits. → shared/subskill-invocation.md#step-boundary

**Recovery sub-branch**: when `RECOVERY_FROM=manifest-schema-invalid`, do not ask opportunistic questions and do not re-implement. Preserve external implementer working-tree edits. Run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" dirty-tree scope-check --plan-file "$IMPLEMENT_TMPDIR/plan.txt" --paths-file "$RECOVERY_PATHS_FILE"`; on non-zero, set `FINAL_BAIL_REASON=recovery-out-of-scope`, `IMPLEMENT_BAIL_REASON=recovery-out-of-scope`, `STALL_STEP=2`, `PHASE=implementation`, `STALL_TRACKING=true`, and bail to Step 12d. Synthesize a concise redacted commit message into `$IMPLEMENT_TMPDIR/recovery-commit-message.txt`. The Step 3 composite owns fresh postlaunch capture, `step2-recovery-paths-final.nul`, and final plan-scope validation before commit. NEVER use `git reset --hard`, `git restore`, `git checkout -- <path>`, or `git add -A` against recovered edits.

Print one of the following based on which path landed here, evaluated **in this exact order** (first match wins):
- When `coder=claude` AND `coder_fallback=true`: `**⚠ Cursor and Codex unavailable — implementing with main agent.**`
- When `coder=codex`: `**⚠ Codex selection drifted after Step 0; Step 2 fell back to the main agent.**` Also log `Step 2 — codex selection drift: session-env no longer permits codex, dispatcher returned claude_fallback` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`.
- When `coder=claude`: `**ℹ Implementing with main agent (coder=claude).**`

If `coder=cursor` and Step 2 returned `STATUS=claude_fallback`, that is **not** a Step 2.4 messaging branch. Step 2 must already have failed closed before entering 2.4 because the bootstrap-selected Cursor path is not allowed to silently drift into Claude fallback.

**Architectural knowledge on Claude fallback**: before Step 2.4 edits, read valid present `ARCHITECTURAL_INVARIANTS.md` before valid present `ARCHITECTURAL_GUIDELINES.md`. Treat invariants as hard constraints and guidelines as judgment-tier principles only for the current plan scope; they do not authorize unrelated edits. Emit one line before editing: `architectural_acknowledgment: <ids or no parsed entries acknowledged>`. Do not rerun the Step 8 compose-time architectural-guidelines assessment early; Step 8 still owns compose-time guideline note materialization.

**Opportunistic questions**: before edits, if the plan leaves choices that codebase patterns do not resolve, consult `CLAUDE.md` when useful, then batch remaining 1-4 questions in one `AskUserQuestion`. Ask about plan ambiguities only. Do NOT ask whether to do the plan, scope, or capacity.

Implement per the Step 0 materialized plan using Edit/Write tools. If main agent finds a pre-existing code issue during Step 2.4, **MANDATORY: READ ENTIRE FILE** before logging it under `Pre-existing Code Issues` or dual-writing to `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md`. Follow CLAUDE.md: read before editing, match style, avoid duplication, avoid over-engineering, and justify each abstraction with a current need. Prefer TDD when test infrastructure exists. For config/docs/prompt edits, skip TDD but name one concrete post-change verification. Address root causes. Use the Step 3 captured-check helper after non-trivial sub-steps when validation is needed; Step 3 is the final check, not the only one.

Main-agent implementation is not complete until the difficulty rating is recorded and the coder-produced scout manifest is normalized; skipping the fence drops coder-produced dynamics and Step 5 runs static reviewers only; it does not relaunch scout dynamic-archetypes on /implement.

**Main-agent difficulty contract**: after edits and before Step 3, rate the implementation with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" difficulty render-rubric` as the anchor. Write `$IMPLEMENT_TMPDIR/implement-difficulty-rating.raw.json` with `predicted_tier`, `confidence`, and bounded `rationale`, then call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" difficulty write-record --output "$IMPLEMENT_TMPDIR/difficulty-rating.json" --rater implement --rater-tool claude --raw-rating-file "$IMPLEMENT_TMPDIR/implement-difficulty-rating.raw.json" --implement-raw-rating-file "$IMPLEMENT_TMPDIR/implement-difficulty-rating.raw.json" --design-tier "${DESIGN_DIFFICULTY:-}"` when a design prior is present. For `--self-review`, keep Step 5 skipping unchanged and pass `--panel-skipped self-review`. Difficulty now selects the Step 5 panel tier, round cap, Codex reviewer model role, audit-upgrade state, and escalation state; `--self-review` still records `panel_skipped=self-review` instead of launching the external panel.

**Main-agent scout manifest contract**: after edits and before Step 3, write raw JSON to `$IMPLEMENT_TMPDIR/scout-coder-manifest.raw.json`. Use `{"archetypes":[]}` when no dynamic specialists are useful. For non-empty manifests, follow `agents/_implementer-base.md` scout selection rules: short lowercase slugs, prefer `dyn-<topic>`, avoid static/reserved slugs (`correctness`, `edge-cases`, `testing`, `generic`, `structure`, `plan-fidelity`, `security`, and `REVIEW_RESERVED` / `python/plan_scout.py`), keep `rationale` single-line, and keep `prompt_body` 2-6 sentences focused on changed code. Use this compact schema:

```json
{"archetypes":[{"name":"slug","focus_area":"code-quality|risk-integration|correctness|architecture|security","weight":1,"rationale":"single-line reason","prompt_body":"2-6 sentence focus directive"}]}
```

**Pinned normalization fence (required, nonblocking)**: immediately after main-agent implementation and before Step 3, run exactly this one-line launcher fence:

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement normalize-coder-scout --tmpdir "$IMPLEMENT_TMPDIR" --input "$IMPLEMENT_TMPDIR/scout-coder-manifest.raw.json" --producer main-agent
```

If `scout-coder-manifest.raw.json` is absent, still run the helper with that expected path so it writes `missing-or-invalid` and an empty manifest. Invalid manifest output is nonblocking but loud. This fence is mandatory on every main-agent path, including `--force`, explicit `--coder claude`, and both-tools-unavailable fallback. External `STATUS=complete` is unchanged; the dispatcher normalizes after a complete manifest.

After main-agent implementation and `normalize-coder-scout`, write redacted Step 4 commit text to `$IMPLEMENT_TMPDIR/implementation-commit-message.txt`. Derive `$IMPLEMENT_TMPDIR/implementation-commit-paths.nul` from a fresh postlaunch capture with:

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement recovery-paths --repo-root "$REPO_ROOT" --tmpdir "$IMPLEMENT_TMPDIR" --capture-postlaunch --prelaunch-porcelain "$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul" --postlaunch-porcelain "$IMPLEMENT_TMPDIR/step2-postlaunch-porcelain.nul" --prelaunch-digests "$IMPLEMENT_TMPDIR/step2-prelaunch-content-digests.txt" --out-file "$IMPLEMENT_TMPDIR/implementation-commit-paths.nul"
```

Before re-launching the checks-repair composite after repair edits, refresh the postlaunch porcelain, pathspec, and commit message.

After the implementation commit (Step 4), the orchestrator constructs an in-memory manifest equivalent (computed from `git diff --name-only $BASELINE..HEAD` and the commit message) for Steps 9a / 9a.1 to consume. `$MANIFEST_PATH` is left empty on this branch.

### 2.5 — Q/A logging + larch-log append

After each `AskUserQuestion` return (Codex Q/A loop, Claude-fallback opportunistic question, or mid-coding ambiguity) and each chosen ambiguity resolution, append to `$IMPLEMENT_TMPDIR/execution-issues.md` under `### Q/A` using:

```markdown
- **Step 2 (<question|ambiguity>)**: <question or ambiguity description>
  **A**: <user answer OR chosen interpretation + one-sentence rationale>
```

**Sanitize Q/A at compose time** (secrets → `<REDACTED-TOKEN>`, internal URLs → `<INTERNAL-URL>`, PII → `<REDACTED-PII>`) because answers can contain sensitive content and `execution-issues.md` is committed into run logs.

**Progressive log append**:
1. Compose an NDJSON record with `phase="implement"`, `step="2"`, `category="Q/A"`, and a sanitized markdown `body`.
2. Append it with:
   ```bash
   "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py run-log append --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch execution-issues --record-file "$IMPLEMENT_TMPDIR/execution-issue-record.ndjson"
   ```
3. On `LOG_WRITTEN=false` with `ERROR=`, log `Step 2 — Q/A larch-log append failed: $ERROR` to `Warnings` and continue. Non-fatal.

If `RUN_ID` is unavailable on a degraded local-only path, keep the `$IMPLEMENT_TMPDIR/execution-issues.md` append; Step 7a and Step 18 safety net remain catch-alls.

Material answers that change scope or approach also log here (same `Q/A` category).

> **Continue to Step 3 IMMEDIATELY after the raw-manifest write and normalize-coder-scout fence complete.** Implementation is not the end of the run — checks, commit, review, PR, CI, and merge still must run.

<!-- step:3 — Relevant Checks (first pass) -->

Print: `> **🔶 /implement 3: checks (1)**`

> **Continue after child returns.** Parse composite stdout like Step 6. On `NEXT_ACTION=checks-failed`, apply **Checks Failure Entry Macro** with pinned `--site step3`. On `NEXT_ACTION=stall`, bail through Step 12d with the composite Step 4 stall state. On `NEXT_ACTION=continue`, parse `CHECKPOINT_NEXT=continue|load-routing` for folded `4.r` routing before Step 5. Failure path stays inside Step 3. Do NOT end the turn, summarize, or hand off.

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 15600000`.**

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}"
```

<!-- step:4 — First Commit (implementation) -->

Print: `> **🔶 /implement 4: commit (impl)**`

Step 4 is owned by the Step 3 composite. On external implementer path (`$MANIFEST_PATH` non-empty), the composite Step 4 leg returns `noop` because the dispatcher already committed `$TOOL_LABEL` edits using `manifest.commit_message`. Skip the `implement commit` invocation. Keep the skip breadcrumb: print `⏩ 4: commit (impl) status=skip reason=dispatcher-committed sha=$COMMIT_SHA elapsed=<elapsed>`. On Claude fallback, the composite invokes `python/cli.py implement commit` with the redacted message and NUL pathspec from Step 2.4. On recovery paths, it refreshes `step2-recovery-paths-final.nul` after checks and commits that pathspec. Commit messages describe WHAT and WHY, not HOW.

### Rebase onto latest main (after implementation commit)

Checkpoint `4.r` is folded into Step 3 composite stdout. Parse `CHECKPOINT_NEXT` and apply **Rebase Checkpoint Macro** with `<step-prefix>=4.r` and `<short-name>=commit (impl)`. The wrapper already performs the `4.r-post-rebase` phantom probe, so parse advisory `PHANTOM_*` from the same stdout.

> **Continue to Step 5 IMMEDIATELY.** The implementation commit is not the end of the run — code review, checks (2), commit, code flow diagram, and PR still must run.

<!-- step:5 — Code Review: review-and-fix step5 → review-and-fix CLI (dynamic-archetypes default=1 in implement tmpdir mode; maximum allowed cap=1) -->
## Step 5 — Code Review

### Self-review mode (`--self-review`)

When `self_review=true`, skip the scripted review loop below.

**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.

The reference owns inline review, the composite checks-commit route, `NEXT_ACTION=main-agent-edit` re-entry, tally write, and post-Step-5 continuation.

### Scripted review loop

**IMPORTANT: Code review must ALWAYS run.** Never skip for any change type. Step 5 invokes **one** `skills/implement/scripts/step-5-review.sh` call per Step 5 entry. The wrapper marks telemetry, resolves `dynamic_archetypes_cap`, prints the Step 5 banner (hard ceiling of 2 for every tier; TRIVIAL singles with Codex preferred and Cursor fallback; MODERATE/HARD pairs; escalated rounds skip pruning; prune-to-empty converges; no round-5 re-probe; specialists per vendor plus at most one dynamic archetype pair), and launches the file-backed `review-and-fix step5 --mode loop --starting-round 1` review loop. A signal-induced wrapper stop does not satisfy Step 5 completion: the wrapper detaches the loop, leaves `$IMPLEMENT_TMPDIR/.step5-wrapper-detached`, and withholds `.completed/step-5-terminal` until reentry normalizes the captured Step 5 envelope. `/implement` Step 5 does not launch a separate dynamic scout; it consumes the coder manifest when eligible, otherwise static reviewers only. The absorbed loop owns rounds, captured checks, lint-fix repair, substantiality, and bulk-skip gates. Rely on `<task-notification>`; never poll or launch Monitor. The launcher reads `$IMPLEMENT_TMPDIR/plan.txt`, uses the persisted difficulty override and resolved tier state, and does **not** forward `--panel`. The review panel is applied only inside `review-and-fix CLI` → `review core` with specialists per vendor plus at most one dynamic archetype pair; round 2 may launch a mechanically reduced reviewer panel from round-1 productivity, and an all-pruned round converges immediately.

Nested review token-context propagation through `review-and-fix CLI` is pinned by `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-implement-review-token-propagation.sh` and `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-implement-review-token-propagation.md`.

The Step 5 signal-aware wrapper contract — bg-wait marker publication, argv forwarding, signal detach that withholds a false `.completed/step-5-terminal`, and reattach normalization — is pinned by `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-step-5-review.sh` and `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-step-5-review.md`.

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 21600000`.**

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-5-review.sh
```

Wait for `<task-notification>` before parsing loop stdout or reading Step 5 result files. If `$IMPLEMENT_TMPDIR/.step5-wrapper-detached` is a regular, non-symlink file and `$IMPLEMENT_TMPDIR/.completed/step-5-terminal` is absent, re-invoke the same Step 5 immediate-background launcher fence and wait again; do not enter the preflight-failure or absent-sentinel stall path. If the wrapper exits non-zero and stdout lacks `STEP5_REVIEW_STATUS`, treat it as Step 5 preflight failure: log to `Warnings`, set `STALL_TRACKING=true`, `STALL_STEP=5`, and skip to Step 18. Do not fall through to status parsing or Step 6; without `STEP5_REVIEW_STATUS`, NEVER #4 is unsatisfied.

Only when stdout contains `STEP5_REVIEW_STATUS`, parse child stdout with **token-aware** extraction: each line may contain multiple `KEY=value` tokens. Extract at least `STEP5_REVIEW_STATUS`, `STALL_TRACKING`, `STALL_REASON`, `ROUNDS_COMPLETED`, `FINAL_ROUND_NUM`, `FINAL_REVIEW_AND_FIX_STATUS`, `CODER_STATUS`, `FILES_CHANGED_HINT`, and `EFFECTIVE_ROUND_CAP`.

**Branch order override**: when `STEP5_REVIEW_STATUS=self-review-required`, run the self-review procedure below to completion first. Only after self-review completes may you continue through the same post-self-review chain as `--self-review`. This branch overrides the generic non-stall continuation line.

> **Continue after the loop returns.** On any non-stall `STEP5_REVIEW_STATUS`, execute the Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order — do NOT end the turn, summarize, or write a handoff message before reaching Step 6. → shared/subskill-invocation.md#anti-halt

For `stall`, `main-agent-vote-required`, `coder-main-agent-required`, and `mav-resume-past-cap`, **MANDATORY: READ ENTIRE FILE** before executing the branch: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step5-review-branches.md`.

Branch on `STEP5_REVIEW_STATUS` (only when present — preflight failures without it terminate at Step 18 per above):

- **`complete`**: proceed with Cross-Skill Presence Propagation, then Track Rejected Code Review Findings, then the Step 6 breadcrumb (the absorbed loop already ran `python/cli.py checks run-relevant`, `python/cli.py checks lint-fix` when needed, and the substantiality / bulk-skip gates inside Bash).
- **`cap-hit`**: print `**⚠ 5: code review hit $EFFECTIVE_ROUND_CAP-round cap without converging. Proceeding.**`, log to `Warnings`, then run the same post-Step-5 chain as `complete`.
- **`self-review-required`**: print `**⚠ /implement Step 5: all external reviewers failed at runtime; falling back to main-agent self-review.**`, log a `Warnings` entry in `$IMPLEMENT_TMPDIR/execution-issues.md`, then **MANDATORY: READ ENTIRE FILE**: read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` and execute it exactly as the `--self-review` branch does. Do not call `review-and-fix step5` again. Do not stall as `panel-failed`. Do not reach Step 6 before self-review finishes.
<!-- # intentionally non-stable: step-5-resume.sh captures wall-clock time for round duration -->
- **`stall`**: follow the `stall` branch body in the Step 5 review-branches reference. Skip to Step 18 (stall recovery runs before the final report).
- **`main-agent-vote-required`**: follow the MAV branch body in the Step 5 review-branches reference, then run the composite checks/resume handoff against the MAV-applied fixes.

- **`coder-main-agent-required`**: follow the coder waterfall branch body in the Step 5 review-branches reference, then run the composite checks/resume handoff against the applied fixes.

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 32700000`.**

> **Continue after child returns.** On composite `NEXT_ACTION=checks-failed`, apply **Checks Failure Entry Macro** with pinned `--site step5-mav --checks-site step5-review-fixes`. On checks pass, apply the composite stdout parsing slice and full resume envelope contract below. On `NEXT_ACTION=main-agent-edit`, delegate through the macro/reference. Terminal `NEXT_ACTION=stall` from the repair loop is a routing summary only: do not skip to Step 18 here. First run the main-agent handoff terminal-stall timing capture and durable bail, then skip to Step 18. Do **not** re-invoke the Step 5 loop wrapper.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"
```

<!-- # intentionally non-stable: step-5-resume.sh captures wall-clock time for round duration -->
Before leaving the main-agent handoff terminal-stall path, record timing exactly once through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-5-resume.sh`. If checks/lint end in terminal stall, invoke the wrapper with `--final-round-num "$FINAL_ROUND_NUM" --record-only`, set `STALL_TRACKING=true` defensively, run **Durable Bail to Step 18 Macro** with pinned `STALL_STEP=5`, skip to Step 18, and do not continue to the composite resume success path or Step 6/16:

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only
```

After `checks-step5-resume` returns, capture full composite Bash stdout. Whitespace-token-scan only the first physical line for checks keys: `FAILURE_REASON`, `RELEVANT_CHECKS_OK`, `RELEVANT_CHECKS_SKIPPED`, `STATUS`, `EXIT_CODE`, and `PHASE`. Key-scan the full composite stdout for `DIGEST_FILE` and `REDACTED_LOG_FILE` so folded failure keys are not lost behind leading output. Parse exactly one line-anchored composite `NEXT_ACTION=` anywhere in the capture for `checks-failed` only. Ignore leading-line `NEXT_ACTION` tokens for resume authorization.

On resume, the loop evaluates substantiality and bulk-skip against the round-`FINAL_ROUND_NUM` artifacts before scheduling additional rounds. If `FINAL_ROUND_NUM == EFFECTIVE_ROUND_CAP`, the wrapper returns `STEP5_REVIEW_STATUS=mav-resume-past-cap`.

On checks pass, parse the relayed resume child exit code and full composite stdout. Use token-aware extraction for review-loop keys that may share a line, and parse line-anchored `NEXT_ACTION=`, `COMMITTED=`, `ERROR=`, `SHA=`, `COMMIT_OUTCOME=`, and `COMMIT_ROUTE_OUTCOME=` for diagnostics. Step 6 continuation requires `STEP5_REVIEW_STATUS`; without it, NEVER #4 is unsatisfied. When stdout contains `STEP5_REVIEW_STATUS=`, route by the Step 5 status table only. Do not map a normal Step 5 loop stall to `resume-handoff-commit-failed` because rc is non-zero or commit-route emitted `NEXT_ACTION=stall`.

When composite stdout lacks `STEP5_REVIEW_STATUS=` and lacks `NEXT_ACTION=checks-failed`, evaluate in order. First, `NEXT_ACTION=stall` means durable stall state is already seeded by commit-route; skip to Step 18. `NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` is not Step 6 continuation. `NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` is a preflight/resume failure: log, set `STALL_TRACKING=true` and `STALL_STEP=5`, and skip to Step 18. missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION` output is an invalid composite envelope and follows the same failure path. Do not proceed to Cross-Skill Presence Propagation, rejected-findings tracking, Step 6, or Step 8 on lacks-envelope paths. A non-zero resume child rc with parsed `NEXT_ACTION=continue` is also a preflight failure. `STEP5_REVIEW_STATUS=` is the only Step 6 authorization; commit-phase success (`NEXT_ACTION=continue`, `COMMIT_ROUTE_OUTCOME=continue`, or `COMMIT_OUTCOME=ok|noop`) alone does not satisfy NEVER #4.

<!-- # intentionally non-stable: step-5-resume.sh captures wall-clock time for round duration -->
- **`mav-resume-past-cap`**: follow the `mav-resume-past-cap` branch body in the Step 5 review-branches reference, then follow the same post-Step-5 chain as `complete`.

Note: `review-and-fix CLI` runs `flush_review_batches` after each successful `_implement_round_body` round, and best-effort once on many stall paths, writing `code-review-tally` and `review-findings-full`. `compose_review_findings_output` passes `--issue 0` as the contract; consumers join by `RUN_ID`. Step 5 needs no extra main-agent `python/cli.py voting write-tally` or `review compose-findings` call.

### Track Rejected Code Review Findings

**MANDATORY: READ ENTIRE FILE before composing rejected finding text or reasons not implemented: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

`review-and-fix CLI` copies rejected in-scope findings from the latest round to `$IMPLEMENT_TMPDIR/rejected-findings.md`. When coder output marks `SKIPPED:` or the round fails, reviewers can still reject findings; log them there for Step 16 instead of reprinting full findings inline.

```markdown
### [Code Review] <Reviewer Name>
**Finding**: <actionable description of the finding — include the specific file(s) and line(s) affected, what the reviewer identified as the issue, and what change they suggested. Use short sentences and bullets when helpful. Detail means enough content for a reader who never saw the original review to understand and act on the issue, not extra length.>
**Reason not implemented**: <clear justification for why this finding was not addressed — include the specific technical reasoning, relevant project conventions or design decisions, and why the current code is acceptable despite the finding. Preserve important details, but keep sentences short.>
```

<!-- step:6 — Relevant Checks (second pass) -->

Print: `> **🔶 /implement 6: checks (2)**`

The Step 6 composite writes `.review-boundary-passed` at entry after Cross-Skill Presence Propagation, rejected-findings tracking, and the Step 6 breadcrumb. That releases `hook-stop-fail-close.sh`'s post-review guard.

> **Continue after child returns.** Parse full composite stdout. On `NEXT_ACTION=skip-to-7a`, print `⏩ 6: checks (2) status=skip reason=no-review-changes elapsed=<elapsed>` and proceed to Step 7a immediately. Do NOT end the turn, summarize, or hand off. On `NEXT_ACTION=checks-failed`, apply **Checks Failure Entry Macro** with pinned `--site step6`. On `NEXT_ACTION=stall`, bail through Step 12d. On `NEXT_ACTION=continue`, parse `CHECKPOINT_NEXT=continue|load-routing` for folded `7.r` routing before Step 7a.

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 15600000`.**

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}"
```

Wait for `<task-notification>` before parsing composite stdout.

Parse `FILES_CHANGED`, `UNTRACKED_BASELINE`, `GIT_PROBE_FAILED`, and exactly one line-anchored composite `NEXT_ACTION=` record from the full composite capture. Do NOT `eval` or `source` stdout. If `UNTRACKED_BASELINE` is present, treat it as the pre-Step-6 untracked set. If `GIT_PROBE_FAILED=true`, continue with warning semantics already embedded by the wrapper; do not reconstruct paths prompt-side.

Route `NEXT_ACTION=skip-to-7a` directly to Step 7a. Route `NEXT_ACTION=continue` through folded `7.r` `CHECKPOINT_NEXT=continue|load-routing` handling from **Rebase Checkpoint Macro** using `<step-prefix>=7.r` and `<short-name>=commit (review)`. Missing or malformed `NEXT_ACTION` is Tool Failure.

<!-- step:7 — Second Commit (review fixes) -->

The `FILES_CHANGED=true` path runs Step 7's commit route inside the Step 6 composite fence above. The composite's `--emit-step7-breadcrumb` flag emits the Step 7 breadcrumb before the commit leg.

If no files changed, skip. `review-and-fix CLI` commits accepted fixes inline each round, so the common path is already clean. If `FILES_CHANGED=true`, the Step 6 composite owns Step 7 commit routing and emits the breadcrumb. On `NEXT_ACTION=stall`, skip to Step 18 (stall recovery runs before the final report; durable bail is already seeded by commit-route). If the Step 7 commit route lacks durable seed, set prompt-side `STALL_TRACKING=true` and `STALL_STEP=7` when durable seed is absent, and skip to Step 18.

<!-- step:7a — Code Flow Diagram -->

Print: `> **🔶 /implement 7a: pre-ship**`

Runs unconditionally after Step 7 (regardless of Steps 6-7 skip).

Step 7a composes no prompt-side public summary and never emits diagram fences. The helper owns silent `larch:diagrams` upsert through `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" diagrams upsert`; the orchestrator parses only KVs and breadcrumbs.

`python/cli.py implement step-7a` consolidates small/non-runtime classification, `python/cli.py diagram code-flow`, Code Flow section composition, shared `larch:diagrams` upsert, 7a.r checkpoint, and pre-ship log flush. It emits a KV tail; do not duplicate those calls prompt-side.
The helper upserts the stable issue-scoped `<!-- larch:diagrams v1 -->` comment only when `$IMPLEMENT_TMPDIR/code-flow-section.md` exists after successful generation. Regression harness: `skills/implement/scripts/test-step-7a.sh` (sibling contract: `skills/implement/scripts/test-step-7a.md`).

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1800000`.**

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement step-7a --implement-tmpdir "$IMPLEMENT_TMPDIR" --issue-number "${ISSUE_NUMBER:-}" --run-id "$RUN_ID" --no-logs-commit "${no_logs_commit:-false}" --forked-target "${forked_target:-false}"
```

Treat `python/cli.py implement step-7a` relay stdout as one KV stream. Scan `REBASE_OUTCOME` only for stream ordering, then read `CHECKPOINT_NEXT=continue|load-routing` and final KV tail for diagram/log status. The `7a.r` macro skip is `CHECKPOINT_NEXT`-only. Route `load-routing` via the **Rebase Checkpoint Macro** using `<step-prefix>=7a.r` and `<short-name>=pre-ship`.

> **Continue to Step 8 IMMEDIATELY.** Step 7a no longer authors or stages architectural-guidelines assessments. Step 8 compose-time gating owns guideline note materialization, authoring, durable writes, and refresh after any `HEAD` change. PR creation, CI monitoring, and merge still must run.

<!-- step:8+ — Ship PR State Machine -->
## Step 8+ — Ship PR State Machine

Steps 8-14 are driven by the **Python ship driver wrapper** inside `step-8-ship.sh`. The wrapper runs `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr`, delegates Python 3.11 checks to `step-8-python-guard.sh`, rehydrates state, runs advisory phantom probes, and writes the durable handoff sidecars for notification routing.

Run `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-driver` before reading the Step 8+ matrix.
**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-exit-matrix.md` completely.

**Post-ship durable handoff.** When `<task-notification>` fires for `step-8-ship.sh`, first resolve `IMPLEMENT_TMPDIR` from `$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh`, then run exactly one foreground non-sleeping probe: `IMPLEMENT_TMPDIR=$(awk 'BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null); test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"`. **If absent**, the notification is premature; end the turn immediately. **If present** but `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` is absent, treat it as setup failure per the matrix. Otherwise, read the rc/json handoff and continue to `route-exit` in the same turn. Do not poll, sleep, use Monitor, or inspect process state. The handoff is durable across turn breaks; after an unexpected turn end, resume by reading it before any Step 8+ branch action.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship route-exit --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

**Pre-driver predicate** (evaluate before choosing fences; read `$IMPLEMENT_TMPDIR/ship-pr-state.sh` when present): state file absent/empty, or `PHASE=checks` and `PR_NUMBER` is empty/absent. Seeded-but-no-PR state is still pre-driver. Run `ship pre-driver` only for this prompt-side predicate.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-driver
```

**Seeder authority.** `python/cli.py ship seed-initial-state` owns the canonical initial state contract; `step-8-seed-initial.sh` is the only shell argv-assembly wrapper.

Branch on pre-driver `NEXT_ACTION`:

- **`stall`**: Python guard failed. Set `STALL_TRACKING=true`, skip `step-8-ship.sh`, and go directly to Step 18 (stall recovery runs before the final report). Pre-driver `stall` never routes through post-driver Step 16 prose.
- **`halt-seed`**: initial seeding failed. Stop before `oos file` and `step-8-ship.sh`; the child output is already on stderr for Tool Failures logging.
- **`halt-oos`**: pre-driver OOS filing failed. Stop before `step-8-ship.sh`, log the failure under Tool Failures, and route to Step 18 per the normal stall path.
- **`oos-pipeline`**: security sidecar present before ship. Do not invoke `step-8-ship.sh` yet. Follow the same private-disposition flow as post-driver `oos-pipeline` below (read `$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` `## Security Findings in OOS Workflows`, then run the OOS checkpoint fence).
- **`ship`**: proceed to `step-8-ship.sh`. On `NEXT_ACTION=ship`, proceed to `step-8-ship.sh` (the wrapper runs the internal guard and advisory phantom probe before the driver). A pre-driver retry reruns guard and `oos file` while skipping the seeder when `ship-pr-state.sh` already has shell KV entries.

Invoke `step-8-ship.sh` in immediate-background mode.

Before every same-turn Step 8+ `step-8-ship.sh` background launch, run one separate foreground Bash call to clear stale handoff sidecars: `IMPLEMENT_TMPDIR=$(awk 'BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null); rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json" 2>/dev/null || true`.

This prevents prior reship/ci-fix rc/json from satisfying the notification probe before wrapper cleanup. Keep the clear outside the launcher fence. Apply it to initial ship, reship, ci-fix, conflict-resolution Phase 4, stall-recovery `step8-shippr`, `ship-pr-exit-matrix.md` re-entries, and every other Step 8+ relaunch. Wrapper entry cleanup remains defense in depth.

**Post-driver Step 8+ continuations:** when the pre-driver predicate no longer matches, invoke only `step-8-ship.sh`; do not rerun pre-driver. The wrapper still runs its guard and advisory phantom probe before the driver.

> **Long-running active driver call.** Set `run_in_background: true` and `timeout: 21600000`; wait for `<task-notification>`. **Recovery after unexpected turn end**: every Step 8+ re-entry goes through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` only for the active driver call, after the foreground stale-handoff clear above. The Python driver resumes from persisted `ship-pr-state.sh` and phase14 flag. If the **Pre-driver predicate** still matches, re-run `python/cli.py ship pre-driver` before `step-8-ship.sh`. Do not call `python/cli.py ship pr` directly from a separate foreground shell. Do not pass `--resume-phase`; resume is state-file driven.

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 21600000`.**

Invoke:

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-8-ship.sh
```

Regression harness: `skills/implement/scripts/test-step-8-ship.sh`.

**Post-driver branch skeleton** (details live in `ship-pr-exit-matrix.md` `## Branch semantics`):

- **`complete`**: continue to Step 16.
- **`guidelines-assessment`**: **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/architectural-guidelines-present.md` completely. Author the compose-time assessment from `$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt` and helper metadata, write `$IMPLEMENT_TMPDIR/architectural-guideline-assessment-draft.md`, run `step-architectural-guidelines-write-compose.sh`, then run the foreground stale-handoff clear and relaunch `step-8-ship.sh` in the same turn. Continue to Step 8, not Step 16. Do not recap.
- **`reship`**: If `.ship-route-exit-handoff.env` has `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, skip the pre-fix rebase. This is an existing conflict-resolution continuation. Proceed to the foreground stale-handoff clear, preserving those keys until conflict-resolution Phase 4 completes. For every other `reship`, run the foreground pre-fix rebase before the stale-handoff clear. Do not sleep.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

Branch on its stdout: When `PRE_FIX_REBASE_REQUIRED=true` is set in `.ship-route-exit-handoff.env` and `$IMPLEMENT_TMPDIR/.ship-pre-fix-rebase-ok` is absent (regular, non-symlink), route to Step 16 with `STALL_TRACKING`, then Step 18. Otherwise `NEXT_ACTION=continue` proceeds to the stale-handoff clear and `step-8-ship.sh`. `NEXT_ACTION=conflict-fix` loads `conflict-resolution.md`; `NEXT_ACTION=stall` routes like post-driver stall.

- **`oos-pipeline`**: security sidecar disposition only. Do not load `execution-issues-tracking.md`, do not load or run `oos-pipeline.md`, and do not call `/issue` on this branch. Read `$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` `## Security Findings in OOS Workflows` privately, and clear the sidecar only after private disposition completes. **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` completely before the `step-8-oos-checkpoint.sh` fence. Expect the checkpoint to stall while `security-oos-observations.md` remains non-empty or private SECURITY.md disposition is pending.
- **`ci-fix`**: If `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true`, skip autonomous edits and route to **operator-bail**. Otherwise, run the foreground pre-fix rebase before loading `ship-pr-ci-fix.md`. Branch on its stdout: `NEXT_ACTION=continue` loads `ship-pr-ci-fix.md` and continues; `NEXT_ACTION=conflict-fix` loads `conflict-resolution.md`; `NEXT_ACTION=stall` routes like post-driver stall.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

When `NEXT_ACTION=continue`, first verify that `.ship-route-exit-handoff.env` does not have `PRE_FIX_REBASE_REQUIRED=true` without a regular, non-symlink `$IMPLEMENT_TMPDIR/.ship-pre-fix-rebase-ok`; if the proof is missing, continue to Step 16 with `STALL_TRACKING`, then Step 18. Then **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-ci-fix.md` completely before autonomous repair / `step-8-ship.sh` re-entry.
- **`conflict-fix`** (post-driver only): Read `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` from `.ship-route-exit-handoff.env`. When `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md` completely, then run conflict-resolution first. Otherwise treat it as a malformed handoff and continue to Step 16 with `STALL_TRACKING`, then Step 18.
- **`operator-bail`**: use `AskUserQuestion` and the existing Step 12d path after ledger recording required by `ship-pr-exit-matrix.md`.
- **`stall`** (post-driver only): continue to Step 16 with `STALL_TRACKING`, then Step 18. Do not reuse pre-driver stall bullets.
- **`tool-failure`**: append Tool Failures and stop hard. Do not run Step 18 stall rename.

**OOS checkpoint fence.** After `NEXT_ACTION=oos-pipeline`, complete security-sidecar private disposition when applicable, then invoke the checkpoint wrapper. **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` completely before invoking the fence. Parse stdout for `NEXT_ACTION=`. Halt with Tool Failures only when `NEXT_ACTION` is missing after invoke. Do not halt merely because rc is non-zero when stdout contains `NEXT_ACTION=`.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-8-oos-checkpoint.sh
```

- **`NEXT_ACTION=reship`**: run the foreground stale-handoff clear, then re-invoke ship with the same `RESUME_PHASE` carve-out. Do not sleep.
- **`NEXT_ACTION=stall`** (OOS-checkpoint stall): halt Step 8+ until resolved. Do not write stats, do not clear `OOS_PENDING=false`, and do not route to the post-driver Step 16 stall path.

When `ship-pr-exit-matrix.md` requires tracking metadata projection refresh, run this fence; skip it when `ISSUE_NUMBER` is empty or `0`.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py execution-issues refresh --implement-tmpdir "$IMPLEMENT_TMPDIR" --best-effort
```

> **Continue to Step 15.** The active Python ship driver owns this transition after postmerge cleanup.

> **Continue to Step 16.** Do NOT stop after PR creation, merge, local cleanup, or teardown output. `ship-pr` reaching `PHASE=done` is not the run end; Steps 16 and 18 still own rejected-findings replay and final token/timing caps.

<!-- step:16 — Rejected Code Review Findings Report -->

Print: `> **🔶 /implement 16: rejected findings**`

`implement step-16-17` reads the compose-time durable architectural-guidelines note only when it is already current for `HEAD`. It performs no semantic reassessment.

Report unimplemented code review suggestions without reprinting the full findings inline.

**Recover-then-report contract (issue #5011).** Steps 16, 16a, and 17 render the final report on the green terminal path and after successful stall recovery re-enters the normal sequence. Stall paths and Step 12d bails set `STALL_TRACKING=true` and **skip to Step 18** so Step 18a recovery runs first. The final report renders exactly once: Step 18b emits it for terminal unrecoverable stall when `.step17-emitted` is absent, or this natural pass emits it after recovery succeeds. This avoids premature `— stalled` reports and duplicate renders.

> **Continue to Step 16a.** The composed wrapper handles this transition; do NOT end the turn after rejected findings.

<!-- step:16a — Slack Issue Announce -->

Print: `> **🔶 /implement 16a: notify**`

> **Continue to Step 17.** The composed wrapper handles this transition; do NOT end the turn after Slack notification.

<!-- step:17 — Final Report -->

Print: `> **🔶 /implement 17: final report**`

Run the composed wrapper for rejected findings, best-effort Slack notification, and terminal `larch:final-summary` projection. Do not branch around it on early bailouts that still have a tracking issue. On terminal stalls that skip here via recover-then-report, `python/cli.py final-report step18b` runs Step 16/16a side effects before emitting the final body.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17 --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

The markdown body comes from `${CLAUDE_PLUGIN_ROOT}/python/cli.py render run-summary`; optional per-lane USD comes from `${CLAUDE_PLUGIN_ROOT}/python/larch/report/report_tokens_cost.py`. The dollar-primary cost line lives in the `larch:final-summary` block written to `summary-final.md` by `final-report write` without `--print-stdout` on the active `python/cli.py implement step-16-17` path.

After the combined Step 16-17 fence returns, follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` marker-first profile. Binding: markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`; source captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout already in context, not `<task-notification>` output; in-context-only `true`; Read fallback `forbidden`; sidecar follow-on `forbidden`. When the shared profile emits a non-empty marker body as plain chat markdown, write `$IMPLEMENT_TMPDIR/.step17-emitted` only after that plain-chat emission. If markers are absent or body empty, emit no Step 17 body. Continue to Step 18 so Step 18b can decide via `EMIT_BODY`.

Internal Step 16, Slack, and Step 17 failures are logged inside the composed wrapper and `python/cli.py implement step-17`; the outer fence still continues to Step 18. Stale-summary guard: absent markers after failed Step 17 render are expected even when an old `summary-final.md` remains. do not Read that file on the Step 17 primary path. Marker emission is gated on captured Step 17 render success and a non-empty `summary-final.md`, not `summary-final.md` presence alone.

Step 18 status KVs and optional final summary body use branch-qualified sources. Green path (`NEXT_ACTION=finalize-done`): use captured composite stdout from `python/cli.py implement step-18-gate-finalize`. Stall-recovery breakout: use captured standalone finalize stdout from `step-18.sh --phase finalize`. Step 18b uses the same shared marker-first profile with `/implement` markers, Read fallback `forbidden`, and sidecar follow-on `forbidden`. Use `EMIT_BODY` and `WFR_RC` only for missing-marker warnings, not direct `summary-final.md` emission. Full token/timing data is committed to `larch-logs/implement/<run-id>/token-report.json` and `timing-report.json` via `run-log refresh`.

> **Continue to Step 18.** Do NOT end the turn after the final report.

<!-- step:18 — Stall Recovery, Cleanup, and Final Warnings -->

Print: `> **🔶 /implement 18: cleanup**`

**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18-cleanup.md` completely.

### Step 18a — Stall recovery gate

Step 18a runs first on every Step 18 entry, before teardown. Per recover-then-report, stall paths and Step 12d bails skip directly here, so recovery runs **before** the Step 16/17 final report. The composite fence reads stall layers, emits `STALL_TRACKING_*` plus `STALL_RECOVERY_REQUIRED`, runs `normalize-outcome`, evaluates green-path Step 18a.5 skips, and finalizes internally when no prompt-side branch is needed. Do not create `current-implement-env-$PPID.sh`.

Bind `STEP17_EMITTED_FOR_STEP18` before the composite fence because the no-stall green path finalizes inside it. Use `true` when `$IMPLEMENT_TMPDIR/.step17-emitted` exists or the Step 17 marker body was already emitted to top chat this run; otherwise use `false`.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement step-18-gate-finalize --implement-tmpdir "$IMPLEMENT_TMPDIR" --stall-tracking-memory "${STALL_TRACKING:-false}" --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"
```

Always retain captured composite stdout. Parse line-anchored `NEXT_ACTION`, `STALL_RECOVERY_REQUIRED`, four `STALL_TRACKING_*` KVs, Step 18b markers, status KVs, and teardown tail KVs from it even when rc is non-zero. Missing `NEXT_ACTION` is Tool Failure. On `NEXT_ACTION=finalize-done` with non-zero rc, still extract markers, print missing-marker warning when required, and relay teardown KVs from captured stdout; do not treat it as silent success.

Parse `STALL_RECOVERY_REQUIRED` and the four `STALL_TRACKING_*` KVs from captured composite stdout immediately after the composite fence returns. Branch primarily on `NEXT_ACTION=stall-recovery`; treat `STALL_RECOVERY_REQUIRED=true` as diagnostic confirmation. Four-layer interpretation lives in `step18-cleanup.md`.

Branch by the composite `NEXT_ACTION`:

- **`finalize-done`**: parse final summary markers, status KVs, and teardown tail relay from captured composite stdout, then finish.
- **`stall-recovery`**: **MANDATORY: READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/stall-recovery.md`, then execute its 9-sub-step active-stall procedure. During active recovery before `CLEARED=true`, do not run the standalone `--phase finalize` fence. After successful recovery (`CLEARED=true`), run the standalone `step-18.sh --phase finalize` fence. Proceed without re-running `python/cli.py implement step-18-gate-finalize` after terminal recovery completes.
- Missing `NEXT_ACTION`: treat as Tool Failure.

Step 18a helper/contract surface: `${CLAUDE_PLUGIN_ROOT}/python/cli.py stall-recovery`, `${CLAUDE_PLUGIN_ROOT}/python/larch/state/stall_recovery.py`, `${CLAUDE_PLUGIN_ROOT}/python/stall-recovery-report.md`, `${CLAUDE_PLUGIN_ROOT}/scripts/resolve-upstream-larch-repo.sh`, `${CLAUDE_PLUGIN_ROOT}/scripts/file-failure-report-cross-repo.sh`, `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-18.sh`, `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-18.md`, and `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-step-18.sh`. Terminal title-prefix handling happens in **Step 18b — Teardown** below.

**Escalation recording owners.** Prompt-side call sites record before Main Claude edits for Step 3 lint `main-agent-required`, Step 5 self-review lint `main-agent-required`, Step 5 `main-agent-vote-required`, Step 5 MAV/check lint `main-agent-required`, Step 6 lint `main-agent-required`, Step 8+ Python ship-pr CI handoffs, Step 18a `step2-impl`, and Step 18a `step8-shippr` code-editing repairs, but only when the Python ship driver emitted `ledger_ready=true` or Main Claude is editing code. Pure reship such as `transient-infra` records nothing. Parse exact `LINT_FIX_LEDGER_*`, `STEP5_REVIEW_LEDGER_*`, and Python ship driver JSON `ledger_ready` / `ledger_site` / `ledger_trigger` / `ledger_step` / `ledger_phase` / `ledger_dispatcher` / `ledger_exit_code` / `ledger_failure_detail_log` fields. Do not duplicate records owned by `review-and-fix step5` or child scripts. Preserve protected-path and submodule warning strings before Main Claude edits or terminal no-recovery routing.

Anti-halt continuation: after `init-attempts`, continue to classify; after classify, continue to retry or terminal routing; after each dispatch, continue to retry accounting; after success or terminal failure on the recovery branch, continue to Step 18b. Do not recurse into Step 18 from recovery, call `ScheduleWakeup`, write `$IMPLEMENT_TMPDIR/session-env.sh`, mutate `$IMPLEMENT_TMPDIR/finalize-state.sh`, or spawn Agent-tool subagents for code-writing recovery.

### Step 18b — Teardown

Repeat any external reviewer warnings from earlier from Step 5 review or runtime-fallback flips, e.g., `**⚠ Codex not available: <reason>**` or `**⚠ Cursor review failed: <reason>**`. See `step18-cleanup.md` for mode-specific warning and finalize-wrapper behavior.

Use the standalone finalize fence only on the stall-recovery breakout path.

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-18.sh --phase finalize --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"
```

On the green path (`NEXT_ACTION=finalize-done`), parse captured composite stdout only. On stall-recovery, parse standalone finalize stdout only. Follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` marker-first profile. Binding: markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`; source captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout on green path, or captured foreground `step-18.sh --phase finalize` Bash wrapper stdout on breakout; not `<task-notification>` output; in-context-only `true`; Read fallback `forbidden`; sidecar follow-on `forbidden`. When `EMIT_BODY=true`, `WFR_RC=0`, and markers are absent or invalid, print `**⚠ Step 18: EMIT_BODY=true but marker pair missing from composite stdout.**` on green path or `**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**` on breakout. Do not Read `summary-final.md` on the Step 18 path because teardown may have removed the tmpdir. Do not write `$IMPLEMENT_TMPDIR/.step17-emitted` after finalize returns. The wrapper writes `.step17-emitted` before Step 18b when `--step17-emitted true`, and touches it before teardown when it emits markers.

`STEP17_EMITTED_PRESENT` is informational-only. Emit gate is marker body from captured composite stdout on green path or captured standalone finalize stdout on breakout, with `EMIT_BODY=true` and `WFR_RC=0` used only for the missing-marker warning. Do not add free-form recap prose.

### Closing token/timing marks — before teardown

Cap the per-run token/timing ledgers **before** teardown removes them. See `step18-cleanup.md` for ordering rationale and finalize wrapper safeguards.

Relay teardown tail records verbatim from captured composite stdout on `NEXT_ACTION=finalize-done`, or from captured finalize stdout on the stall-recovery path. Tail records document the mechanical outcome: `RENAME_BRANCH=...`, `RENAME_STATUS=...`, `ISSUE_URL=...`, `STASH_REF=...`, `SENTINEL_WRITTEN=...`, `FINALIZE_SUBCOMMAND=teardown`, `FINALIZE_WARNINGS=...`, and sibling `FINALIZE_*` KVs.

<!-- larch:step18-teardown-tail-relay
Step 18 teardown tail relay is dual-source pinned: preserve both the final report tail
and the teardown tail as distinct relay sources.
-->
