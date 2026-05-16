---
name: implement
description: "Use when shipping a feature end-to-end: design, implement, review, version bump, PR, CI-green merge. Triggers: 'ship X', 'land PR', 'merge this'. See /research, /design, /im (merge), /imaq (auto-merge)."
argument-hint: "[--quick] [--auto] [--forked] [--design-only] [--no-issues] [--inline] [--merge | --draft] [--no-admin-fallback] [--coder=claude|codex|cursor] [--session-env <path>] [--issue <N>] <feature description>"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob, Agent, Task, WebFetch, WebSearch, Skill
---

# Implement Skill

End-to-end: design, plan review, code, validate, commit, code review, validate, commit, code flow diagram, version bump, PR, CI monitor, cleanup. With `--merge`: also CI+rebase+merge loop, local branch delete, main verification.

**Protocol Execution Directive.** You are now the `/implement` orchestrator. After parsing flags and checking for mutually exclusive options, your FIRST external action MUST be Step 0: first `${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check`, then `${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh`, then `${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh` with `--skip-branch-check` toggled by the entry gate. When `--forked` was parsed, `${CLAUDE_PLUGIN_ROOT}/scripts/implement-fork-env.sh` is the only permitted pre-setup exception and runs before those three setup calls.

**Anti-halt continuation reminder.** After every child `Skill` tool call (e.g., `/design`, `/review`, `/bump-version`, `/issue`, `/implement`) returns AND after every `Bash` tool call that completes a numbered step or sub-step, including `run-relevant-checks-captured.sh`, IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on the child's cleanup output, on a Bash result, or on a status message, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. This applies to ALL step boundaries from Step 0 through Step 18. The rule is strictly subordinate to any explicit non-sequential control-flow directive in THIS file (e.g., `skip to Step N`, `bail to cleanup`, `jump back`, `loop back`, `fall through`, `break out`). A normal sequential `proceed to Step N+1` instruction is the default continuation this rule reinforces, NOT an exception. Every relevant-checks helper call anywhere in this file is covered by this rule. **Critical boundary: after Step 9b (PR creation) completes, IMMEDIATELY proceed to Step 10 (CI monitor) — PR creation is NOT the end of the run.** **Critical boundary: after `ship-pr.sh` exits (any exit code), do NOT print `✅ 8: version bump`, `⏩ 8: version bump`, or any other Step 8 breadcrumb as orchestrator text output — `ship-pr.sh` emits these lines to its own stdout (issue #1944). Parse `ship-pr-state.sh` silently and re-invoke per the Step 8+ exit-code table. See NEVER #11.** **Critical boundary: after `/design` returns (its output ends with the `➡️ 5: cleanup — manifest written; NEXT REQUIRED:` directive — or, from an older run without the directive, with a bare `MANIFEST_WRITTEN=<path>` line), the FIRST and ONLY permitted next action is the mandatory `post-design-boundary` Bash wrapper call — do NOT end the turn or write any prose before it. See NEVER #12.** → shared/subskill-invocation.md#anti-halt

**Skill-name fallback reminder.** When invoking a child skill via the Skill tool from this file, ALWAYS try the bare name first (`"bump-version"`, `"design"`, `"review"`, `"issue"`, `"implement"`). Only fall back to the fully-qualified `larch:` form (`"larch:design"`, etc.) when the bare-name lookup returns `Unknown skill` — and conversely, in a consumer repo that installs the plugin under a non-`larch` namespace the bare name may miss and the fully-qualified form (with that repo's actual namespace) becomes the working fallback. `/implement` does not invoke `/relevant-checks` through the Skill tool on the green path; it uses the captured Bash helper so success returns one bounded machine line. **`/bump-version` is intentionally project-local under `.claude/skills/` and is NOT shipped with the plugin** — `larch:bump-version` does not resolve, so a `larch:`-first attempt fails outright. Do NOT mirror this skill's own namespaced invocation (`larch:implement`) onto child Skill calls. → shared/subskill-invocation.md#bare-name-fallback

## Load-Bearing Invariants

Four invariants enforced across multiple steps. Anchor cross-step questions here; do not re-derive inline.

1. **Version Bump Freshness** — the terminal bump commit on HEAD MUST be based on latest `origin/main` at merge time. **Enforcement**: Step 12's Rebase + Re-bump Sub-procedure, step12-family hard-bail to 12d on any failure; Step 10 uses the same sub-procedure with step10-family best-effort semantics (warn + break to Step 11); Step 8 is pre-PR and permissive. **Why**: merging a stale bump publishes a version that does not reflect latest main, violating the plugin's version contract.

2. **Step 9a.1 OOS Sentinel Idempotency** — re-running `/implement` in the same session MUST NOT double-file OOS issues. **Enforcement**: the `$IMPLEMENT_TMPDIR/oos-issues-created.md` sentinel detected at Step 9a.1 entry; prior URLs + tallies are recovered from it with no `/issue` call. **Why**: `/issue`'s LLM-based semantic dedup is a second backstop but not deterministic; the sentinel is the byte-exact deterministic guard.

**Fork-mode carve-out for Invariants #1 and #2**: when `forked_target=true`, version bump and OOS issue-filing surfaces are intentionally disabled. Freshness compares against `upstream/main` through `rebase-push.sh --base-remote upstream --base-ref main` and `ci-status.sh --base-remote upstream --base-ref main`; no `/bump-version`, CHANGELOG amend, or Rebase + Re-bump Sub-procedure runs. Step 9a.1 does not call `/issue`; accepted OOS items are carried as final-report text only.

3. **Degraded-Git Fail-Closed** — `check-bump-version.sh STATUS != ok` MUST force `VERIFIED=false` at Step 12 regardless of `COMMITS_AFTER`. **Enforcement**: STATUS-first evaluation ordering in the Rebase + Re-bump Sub-procedure step 4 (see `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bump-verification.md` Block β); Step 8 permissive, Step 12 strict (bail to 12d). **Why**: a coerced 0 baseline from a transient git error routes to a bogus "wrong commit count" mis-diagnosis — the fail-closed rule prevents silently wrong merged versions.

4. **Tracking-Issue Sentinel Idempotency** (umbrella #348) — re-running `/implement` in the same session MUST NOT double-create a tracking issue or double-adopt the wrong issue. **Enforcement**: the `$IMPLEMENT_TMPDIR/parent-issue.md` sentinel detected at Step 0.5 entry; prior `ISSUE_NUMBER` and `RUN_ID` are recovered from it so no `tracking-issue-write.sh create-issue` call (Branch 4 path, which runs at Step 0.5 on first remote write) runs twice. Ordering invariant on Branch 4 first-creation: `create-issue` -> `larch-log.sh init` -> `tracking-issue-summary.sh upsert-summary` for the `larch:metadata` comment -> write sentinel last. The sentinel is written ONLY after `ISSUE_NUMBER`, `RUN_ID`, and the metadata summary comment have resolved successfully. If create-issue fails: `deferred=true`, skip sentinel. If `larch-log.sh init` (manifest write) fails: `deferred=true`, `STALL_TRACKING=true`, skip sentinel, skip to Step 18 — **preserve `$ISSUE_NUMBER`** so Step 18 can rename the created issue to `[STALLED]`. If metadata summary upsert fails: `deferred=true`, skip sentinel, proceed to Step 1. **Why**: `tracking-issue-summary.sh` searches by the marker literal for each of the four slim comments, but the local sentinel is still the byte-exact session-scope guard against double-creation on retry or resume. Parallel to Invariant #2 — sentinel-based byte-exact idempotency guards for distinct session artifacts.

## NEVER List

Each rule states WHY; per-site reminders reference by anchor name.

1. **NEVER simply "log and return" on push failure in the step12 family of the Rebase + Re-bump Sub-procedure.** **Why**: `ci-wait.sh` and `merge-pr.sh` operate on remote PR state only; a log-and-return would let the merge loop proceed to `ACTION=merge` on a remote branch lacking the fresh bump commit. **How to apply**: only step10 family may degrade gracefully; step12 family MUST bail to 12d.

2. **NEVER second-guess `VERIFIED=false` when `check-bump-version.sh` reports `STATUS != ok`.** **Why**: the script has already fail-closed on a coerced 0 baseline; the numeric comparison is meaningless. **How to apply**: STATUS-first evaluation ordering in `references/bump-verification.md` is authoritative.

3. **NEVER use the `ours`/`theirs` git labels when describing conflict sides during rebase.** **Why**: during rebase their semantics are inverted vs. merge (`--ours` = base being rebased onto = upstream main); labels cause silent resolution errors. **How to apply**: always use "upstream (main)" and "feature branch commit" in Phase 1 commentary and user prompts.

4. **NEVER skip the code-review step regardless of the nature of changes.** **Why**: all changes — code, skills, documentation, data files, configuration — require reviewer-panel vetting. **How to apply**: Step 5 always invokes `skills/review-and-fix/scripts/review-and-fix.sh`; quick mode passes `--panel simple`, normal mode passes `--panel hard`, and both modes keep the multi-round review/fix gate.

5. **NEVER let the Step 9a.1 sentinel short-circuit silently skip the larch-log OOS update.** **Why**: idempotency recovery MUST write the recovered accepted-OOS URLs to the `oos-issues` log batch and refresh the terminal summary content; silent skip breaks the committed run-log contract. **How to apply**: the idempotent-rerun branch in Step 9a.1 performs the same `larch-log.sh append --log-root "$IMPLEMENT_TMPDIR/larch-logs" --batch oos-issues` / `larch-log.sh write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --batch run-statistics` operations using URLs recovered from `oos-issues-created.md` as the normal create-script branch steps. **Fork-mode carve-out**: when `forked_target=true`, tracking-issue lifecycle and OOS issue creation are disabled, so Step 9a.1 skips issue filing and larch-log Accepted-OOS updates; accepted OOS items are emitted in the final report as text only.

6. **NEVER let the focus-area enum drift out of checked review prompt surfaces.** **Why**: `.github/workflows/ci.yaml` inspects the canonical review/design prompt files for the unquoted focus-area enum; Step 5 now delegates prompt construction to review scripts instead of embedding prompt strings here. **How to apply**: when moving review prompt text between scripts or skill files, update the CI file list in the same PR so the surface containing `code-quality / risk-integration / correctness / architecture / security` remains checked.

7. **NEVER bail mid-run on orchestrator-judgment "scope" or "capacity" concerns without a mechanical justification.** **Why**: `/implement` is designed for long autonomous runs end-to-end. Subjective "this feels like a lot of remaining work" judgments are NOT valid bail reasons. The only sanctioned non-error halt paths between Step 1 and Step 18 are: (a) Step 12d under one of its documented judgment conditions; (b) explicit user halt mid-run via a fresh interactive turn; (c) hard tool failure. **How to apply**: continue according to the next explicit control-flow directive unless a sanctioned halt path applies. **Post-merge sub-clause (highest-stakes halt boundary)**: the `✅ 12: CI+merge loop status=complete outcome=merged pr=<N> elapsed=<elapsed>` line at Step 12b (and the analogous `✅ 12: CI+merge loop status=complete outcome=force-merged-externally pr=<N> elapsed=<elapsed>` line at Step 12a's `already_merged` branch) is the single most halt-prone moment in the orchestrator — the celebratory "merged!" tone makes the run feel complete, but Steps 14, 15, 16, 17, 18 still must run. Halting at the post-merge boundary, ending the turn after the merge breadcrumb, posting a done recap, or composing any handoff/summary message between the merge breadcrumb and Step 14's first action is a NEVER #7 violation regardless of how natural the boundary feels. The `pr_closed=true` and `DONE_RENAME_APPLIED=true` flags set by 12a/12b are PRE-conditions consumed by Steps 14-18, not POST-conditions of a finished run.

8. **NEVER use `step12_rebase` or `step10_rebase` (or any other non-`step8b_rebase` token) as the `caller_kind` when invoking the Rebase + Re-bump Sub-procedure from Step 8b's conflict handler.** **Why**: step10/step12 caller families have wrong post-success control flow for Step 8b — `step12_rebase` re-invokes `ci-wait.sh` (no PR exists at Step 8b, so `ci-wait.sh` would fail), `step10_rebase` falls through to a Step 10 → Step 11 path that is unreachable from Step 8b, and the failure semantics route to 12d (no PR to bail under) or break out of a non-existent CI loop. **How to apply**: `implement-finalize.sh postbump` emits `CALLER_KIND=step8b_rebase` on the conflict envelope, and the orchestrator must invoke the sub-procedure with that same token. The sub-procedure's step 7 has a dedicated `step8b_rebase` return branch that returns control to `postbump`'s checkpointed force-push phase without sleeping or re-invoking `ci-wait.sh`.

9. **NEVER call `ScheduleWakeup` anywhere in the `/implement` orchestrator.** **Why**: `step2-implement.sh` blocks until the external implementer returns; `ci-wait.sh` likewise runs synchronously. A non-sentinel `prompt` re-fires on wakeup as a `/loop` input and can perpetuate follow-up turns past Step 18 (spurious `/review --diff` on empty diff, etc.). **How to apply**: do not call `ScheduleWakeup` from the `/implement` orchestrator at any step; use foreground Bash completion and the Bash tool's task notification for one-shot waits. See `skills/implement/scripts/step2-implement.md` orchestrator wait contract.

11. **NEVER call `/bump-version` as a direct Skill invocation from the Step 8+ orchestrator, and NEVER print `✅ 8: version bump` or `⏩ 8: version bump` as orchestrator text output.** **Why**: `ship-pr.sh` handles the version bump internally (calling `classify-bump.sh` and `apply-bump.sh` as shell commands) and emits the `✅ 8:` / `⏩ 8:` breadcrumb lines to its own stdout. Printing the breadcrumb as orchestrator text output creates a turn boundary at the post-bump point — when the context is full, context compaction fires and the recap requires user input (issue #1944). The `.bump-version-armed` Stop-hook sentinel is not written in the `ship-pr.sh` path. **How to apply**: in Step 8+, the orchestrator's ONLY action related to version bump is writing `ship-pr-state.sh` and calling `ship-pr.sh`. Do NOT add any `/bump-version` Skill calls or emit `✅ 8:` / `⏩ 8:` as orchestrator text output at any point in the Step 8+ flow.

12. **NEVER end the turn after `/design`'s Skill tool return, even when its output ends with the `➡️ 5: cleanup — manifest written; NEXT REQUIRED:` directive or (from an older run without the directive) with a bare `MANIFEST_WRITTEN=<path>` line.** **Why**: the exact observable symptom this rule targets is a turn that ends immediately after `/design` returns — whether the last visible line is the `➡️ 5: cleanup — manifest written; NEXT REQUIRED: parent /implement must invoke post-design-boundary.sh immediately as a Bash tool call — do NOT end the orchestrator turn` directive (current) or the bare `MANIFEST_WRITTEN=<path>` line (older runs) — instead of invoking the mandatory `post-design-boundary` wrapper as the next action. Both terminal patterns are inputs to the wrapper, not run-exit signals. Ending the turn here leaves `.boundary-gate-passed` unwritten, `BRANCH_NAME` / `PLAN_FILE` / all manifest variables unbound, larch-log batches unwritten, and the tracking issue's plan summary unposted — stalling the run until the user manually types "continue". The Stop hook guards against a session-termination event but does NOT fire on a turn-boundary halt (where the orchestrator ends its response without triggering a session Stop event). The PostToolUse hook injects a backstop directive into the turn context, but the orchestrator Bash call is the load-bearing gate. **How to apply**: after the `/design` Skill tool call, the FIRST and ONLY permitted next orchestrator action is the mandatory `post-design-boundary` Bash wrapper call (Step 1 Normal Mode) — do NOT end the turn and do NOT write orchestrator-authored prose, summary, recap, handoff, or "returning to parent" message before it. See the post-/design boundary checkpoint section in Step 1 Normal Mode and the post-/design legal next-actions matrix.

13. **NEVER write, recreate, or modify `$IMPLEMENT_TMPDIR/finalize-state.sh` from prompt-side orchestrator code.** **Why**: on runs that invoke `ship-pr.sh` (every non-design-only, non-bail path), the file is atomically written by `write_finalize_state()` during the postmerge phase and carries 20 keys; `implement-finalize.sh teardown` validates 15 of them via `require_state_keys` and reads the rest for branch cleanup and session verification. Clobbering the file with an orchestrator-reconstructed subset causes a cascade of `state-file missing required key` errors during teardown, leaving the session tmpdir un-cleaned and stale tmpdirs accumulating under `~/.cache/larch/sessions/`. **How to apply**: do NOT write `$IMPLEMENT_TMPDIR/finalize-state.sh` by any means from prompt-side orchestrator code — `cat > … <<EOF`, `printf > …`, `echo > …`, the Write tool, `sed -i`, `tee`, or any other mechanism. The sole sanctioned writer is `scripts/restore-finalize-state.sh`, which Step 18 calls via Bash before teardown; that call is the mechanical recovery path, not a prompt-side improvisation. If `implement-finalize.sh teardown` fails with `state-file missing required key` AND `ship-pr-state.sh` is absent (so restore cannot help), surface the error and stop — do NOT compose the file from prompt-side shell variables. See Step 18 teardown block.

**Single-runner assumption**: `/implement` assumes one runner per repository at a time. Concurrent `/implement` sessions on the same clone can interleave working-tree mutations and produce false-positive dirty-tree probes, or attribute one runner's mutations to another. For reliable operation, run one instance of `/implement` at a time per repository. The dirty-tree guards reduce blast radius but do not serialize repository writes. Between Step 0 and any documented checkpoint probe, `/implement` and child skills must write only to session tmpdirs (`$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, `$REVIEW_TMPDIR`) until the implementation step intentionally edits the repo.

**Mode matrix**:

| Mode | PR target | Tracking issue lifecycle | Version bump | CI base comparison | Merge |
|---|---|---|---|---|---|
| Default | `$REPO` from session setup | enabled | enabled when available | `origin/main` | skipped |
| `--merge` | `$REPO` from session setup | enabled | enabled when available | `origin/main` | enabled |
| `--forked` | `$FORK_REPO` from origin | disabled | skipped | `upstream/main` | disabled |
| `--design-only` | none | enabled except `--forked` | skipped | n/a | disabled |
| `--design-only --no-issues` | none | disabled (Steps 0.5, 9a.1, 11 skipped) | skipped | n/a | disabled |

## Progress Reporting

Every step MUST print breadcrumb status lines per shared/progress-reporting.md. Print a start line (`> **🔶 /implement 2: implementation**`) on entry. Long-running steps print intermediate progress (`⏳ 12: CI+merge loop — CI running (2m elapsed), main unchanged`).

**MANDATORY at session start**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-name-registry.tsv` to get the Step Name Registry (step number → short name mapping for progress breadcrumbs).

### Verbosity Control

Use empty `description` on Bash calls; terse 3-5-word `description` on Agent calls; no explanatory prose between tool outputs beyond the preserved categories below.

**Preserved:** step breadcrumb lines (start `🔶`, skip `⏩`/`⏭️`); warning / error lines (`**⚠ ...`); structured summaries (voting tallies, scoreboards, round summaries, final reports); diagrams; implementation plans; dialectic resolutions; accepted / rejected findings; out-of-scope observations; PR body sections.

**Suppressed:** explanatory prose, script paths, inter-call rationale, per-reviewer individual completion messages (replaced by status table in child skills). Rebase-skip cases at Steps 1.m, 1.r, 4.r, 7.r, 7a.r, and 8b silently continue (no `⏩` line) because the rebase had no effect. Non-rebase `⏩` skip messages and rebase outcomes inside the Rebase + Re-bump Sub-procedure (Steps 10/12) are NOT suppressed — they carry CI-debugging semantics.

Verbosity suppression is prompt-enforced and best-effort; may degrade in very long sessions.

## Rebase Checkpoint Macro

Standardizes the four post-step rebase checkpoints (Steps 1.r, 4.r, 7.r, 7a.r). Call sites invoke with `<step-prefix>` and `<short-name>`. Step 7.r's `FILES_CHANGED=true` guard stays at the call site — the macro owns HOW to rebase and report; call sites own WHETHER.

**Invocation form** (exact, one line per call site): `Apply the Rebase Checkpoint Macro with <step-prefix>=<X> and <short-name>=<Y>.`

**Procedure** (M1-M3 labels avoid collision with outer Step 0-18 numbering):

- **M1 — Run rebase**:
```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict [--base-remote upstream --base-ref main when forked_target=true]
```
  Capture stdout and exit code as `rc`.

- **M2 — On non-zero exit**, branch on `rc`:
  - **Exit 1** (rebase conflict): print `🔃 <step-prefix>: <short-name> | rebase — conflict detected, invoking Conflict Resolution Procedure (caller_kind=early_rebase)`. Parse `CONFLICT_FILES=<comma-separated list>` from M1's captured stdout; `--keep-on-conflict` leaves the rebase in progress so this list is authoritative for Phase 1. (If the line is missing — defensive only — fall back to `git diff --name-only --diff-filter=U` to enumerate the in-progress rebase's unmerged paths.) **MANDATORY — READ ENTIRE FILE** before executing the Conflict Resolution Procedure: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md`. Invoke the Conflict Resolution Procedure with `caller_kind=early_rebase` and the parsed `CONFLICT_FILES`. On success, continue to M3. On hard failure, the procedure runs `${CLAUDE_PLUGIN_ROOT}/scripts/git-rebase-abort.sh`, sets `STALL_TRACKING=true` (signals Step 18 to rename the tracking issue to `[STALLED]` — see "Title-prefix lifecycle" below), and skips to Step 18.
  - **Exit 3** (non-conflict rebase failure — fetch error, detached HEAD, etc.; `REBASE_ERROR=...` printed on stderr): print `**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**`, set `STALL_TRACKING=true`, and skip to Step 18.
  - **Other non-zero exit**: print `**⚠ Rebase onto main failed unexpectedly (exit $rc). Bailing to cleanup.**`, set `STALL_TRACKING=true`, and skip to Step 18.

- **M3 — On success**, branch on stdout (check `SKIPPED_ALREADY_PUSHED` BEFORE `SKIPPED_ALREADY_FRESH` — `rebase-push.sh` exits early on already-pushed before fetch):
  - If stdout contains `SKIPPED_ALREADY_PUSHED=true`: silently continue.
  - If stdout contains `SKIPPED_ALREADY_FRESH=true`: silently continue.
  - Otherwise, continue.

**Call-site registry** (the four authorized instantiations; `scripts/test-implement-rebase-macro.sh` pins these rows):

| Step | `<step-prefix>` | `<short-name>`   |
|------|-----------------|------------------|
| 1.r  | `1.r`           | `design plan`    |
| 4.r  | `4.r`           | `commit (impl)`  |
| 7.r  | `7.r`           | `commit (review)`|
| 7a.r | `7a.r`          | `code flow`      |

## Flags

The feature to implement is described by `$ARGUMENTS` after flag stripping.

**Flags**: Parse flags from the start of `$ARGUMENTS` before treating the remainder as the feature description. Flags may appear in any order; stop at the first non-flag token. After stripping, save the remainder as `FEATURE_DESCRIPTION` (use this — not raw `$ARGUMENTS` — everywhere the human description is needed). **All boolean flags default to `false`. Only set a flag to `true` when its `--flag` token is explicitly present. Flags are independent — presence of one must not alter the default of another.**

- `--quick`: `quick_mode=true`. Step 1 skips `/design` (inline plan instead); Step 5 uses `review-and-fix.sh --panel simple` for a review loop of up to 5 rounds with no voting panel; Step 7a skips the Code Flow Diagram. All other steps run normally. Independent of `--merge`. Step 1 normal mode may also flip `quick_mode=true` at runtime via simplicity classification (see Step 1 "Simplicity classification" — auto-switch is unilateral, no user prompt, but skipped on resumed sessions where a reusable design manifest is present).
- `--hard`: `hard_mode=true`. Forces the HARD workflow by skipping the simplicity classification preamble — the task always proceeds with `/design` (collaborative sketches, plan review, voting) and Step 5 uses `review-and-fix.sh --panel hard` regardless of apparent scope. Default: `hard_mode=false`. Use this when the task clearly warrants the full design ceremony. Has no meaningful effect when `quick_mode=true` (quick mode already bypasses the simplicity classification and `/design`). Independent of all other flags.
- `--auto`: `auto_mode=true`. (a) forward `--auto` to `/design` in Step 1, suppressing its interactive checkpoints; (b) suppress this skill's Step 2 opportunistic questions; (c) in Step 12 merge-conflict resolution, suppress `AskUserQuestion` and use best-effort (bail if confidence too low). When `--quick` also set and `/design` skipped, `--auto` still suppresses Step 2 questions. Reviewer dirty-tree changes recovered by `review-core.sh` are always auto-discarded regardless of `--auto` — no `AskUserQuestion` is fired for reviewer dirty trees.
- `--forked`: `forked_target=true`. Run the workflow as a fork-CI dry-run: target fork PR operations at `origin` (`FORK_REPO`), compare freshness against `upstream/main`, disable tracking-issue lifecycle, skip version bump / CHANGELOG / merge, and print a final upstream-PR command for the operator. Compatible with `--quick`, `--draft`, `--design-only`, `--auto`, `--no-logs-commit`, `--issue`, and `--coder=...`. **Mutually exclusive with `--merge`**; if both are present, print `**⚠ --forked and --merge are mutually exclusive. Aborting.**` and exit without Step 0.
- `--merge`: `merge=true`. Steps 12–15 run (CI+rebase+merge loop, local cleanup, main verification). Otherwise those steps are skipped — PR is created and workflow stops after initial CI wait, rejected findings, final report, and temp cleanup. **Mutually exclusive with `--draft`.**
- `--design-only`: `design_only=true`. Run Step 0 / 0.5 / 1, publish the plan, plan-review tally, diagrams when available, and OOS fragments to the tracking issue, then stop without implementation, review, version bump, PR creation, CI, or merge. **Mutually exclusive with `--merge`**; if both are present, print `**⚠ --design-only and --merge are mutually exclusive. Aborting.**` and exit without Step 0. **Mutually exclusive with `--quick`** (quick mode bypasses /design's sketch+review machinery and produces a degraded inline plan that has no plan-review tally; combining the two would publish an empty/degraded review section to the tracking issue with no signal); if both are present, print `**⚠ --design-only and --quick are mutually exclusive (quick mode skips plan-review). Aborting.**` and exit without Step 0. Compatible with `--no-issues`; when combined, Steps 0.5, 9a.1, and 11 are skipped entirely — see that flag.
- `--no-issues`: `no_issues=true`. When combined with `--design-only`, skips Step 0.5 (tracking issue creation), Step 9a.1 (OOS issue filing), and Step 11 (execution-issues summary refresh) entirely. Design output is ephemeral — no GitHub tracking issue is created and no marker-keyed summary comments are maintained. `$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail (removed at Step 18). Default: `no_issues=false`. **Requires `--design-only`**; if `--no-issues` is present without `--design-only`, print `**⚠ --no-issues requires --design-only. Aborting.**` and exit without Step 0. **Mutually exclusive with `--issue <N>`**; if both are present, print `**⚠ --no-issues and --issue are mutually exclusive. Aborting.**` and exit without Step 0.
- `--inline`: `inline_mode=true`. Default: `inline_mode=false`. **Execution topology only — does not change parent verbosity suppression.** Controls how /design's heavy non-interactive phase (sketches → plan → plan review → optionally Step 3b/4) executes. When `inline_mode=false` (default), /implement appends `--subagent` to its Step 1 /design invocation, so the heavy phase runs in an isolated Agent-tool subagent and only the nested machine footer plus artifact paths reach the parent. When `inline_mode=true`, /implement omits `--subagent`, so the heavy phase runs in /design's own in-turn context (richer tool transcript visible in the design step's output, higher token cost in the parent context). **Parent verbosity suppression is unchanged** — bulky inline artifact bodies remain file-backed via the manifest because /design's suppression rules are gated on `SESSION_ENV_PATH` (non-empty whenever /implement invokes /design). A separate verbosity flag would be required to actually unsuppress inline artifact prints; that is out of scope for this PR. Orthogonal to all other flags including `--design-only` (`--design-only --inline` is allowed). **No effect under `--quick`** — quick mode skips /design entirely, so the inline-vs-subagent distinction is moot.
- `--draft`: `draft=true`. Step 9b creates the PR in draft state (`create-pr.sh --draft`); Step 14 is skipped so the local branch stays. `draft=true` implies `merge=false`. **Mutually exclusive with `--merge`.** If both are present, print `**⚠ --draft and --merge are mutually exclusive. Aborting.**` and exit without Step 0.
- `--no-admin-fallback`: `no_admin_fallback=true`. Default: `no_admin_fallback=false`. When `true`, forwarded into Step 12b's `merge-pr.sh` invocation; the script then tries only a plain squash merge once the admin-eligible gate (CI good + branch fresh) is reached, emits `MERGE_RESULT=policy_denied` if that plain merge fails, and Step 12b bails to Step 12d. Default behavior tries `--admin` first after the same gate, then retries without `--admin` if the privileged attempt is rejected. Applies to ALL admin-eligible `mergeStateStatus` values (`CLEAN`, `UNSTABLE`, `HAS_HOOKS`, `BLOCKED`) — not just review-required denials. Independent of all other flags (in particular: no special coupling with `--auto`).
- `--no-logs-commit`: `no_logs_commit=true`. Default: `no_logs_commit=false`. When `true`, suppresses larch-log flush commits. In the `ship-pr.sh` subprocess tree this is exported as `LARCH_NO_LOGS_COMMIT=true`, which makes commit primitives skip their `scripts/larch-log-flush.sh` tail calls. Prompt-side direct wrappers such as the pre-bump flush, `scripts/refresh-run-logs.sh`, and session-transcript capture also skip their explicit commit calls when this flag is true. Log files are still written to `$IMPLEMENT_TMPDIR/larch-logs/` for local inspection; they are simply not committed to the branch. Useful when operators want to suppress larch-log commits from the PR. Independent of all other flags.
- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).
- `--no-merge`: **Deprecated** no-op. On encounter, print `**ℹ '--no-merge' is now the default and no longer needed; the flag is recognized as a no-op for backward compatibility.**`
- `--session-env <path>`: sets `SESSION_ENV_PATH`. Forwarded to `session-setup.sh` via `--caller-env` and to `/design` via `--session-env`. Empty = standalone invocation (full discovery).
- `--issue <N>`: sets `ISSUE_ARG=<N>`. Default: empty. When non-empty, Step 0.5 Branch 2 adopts the given tracking issue instead of Branch 4 creating a new one. Compatible with all other flags except `--no-issues` (which skips Step 0.5 entirely, discarding `--issue`). If the target issue is CLOSED, Step 0.5 emits `IMPLEMENT_BAIL_REASON=adopted-issue-closed` on stdout and exits non-zero (cleanup still runs).

<!-- step:0 — Session Setup -->
## Step 0 — Session Setup

Print: `> **🔶 /implement 0: setup**`

If `forked_target=true`, run the single fork pre-setup helper before the standard three-call sequence. Do NOT pass `--tmpdir`: at this point in Step 0, `$IMPLEMENT_TMPDIR` is not yet set (`session-setup.sh` has not run), so the helper allocates its own bootstrap tmpdir via `mktemp -d`. Round 1 plan-review FINDING_1 mandates this ordering — passing `--tmpdir "$IMPLEMENT_TMPDIR"` here would expand to an empty path and silently misroute the caller-env write.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/implement-fork-env.sh
```

Check the current branch before any setup side effects:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check
```

Parse `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, and `USER_PREFIX` from stdout. If `CURRENT_BRANCH` is empty, treat it as detached HEAD; do not special-case it here. The default preflight below will fail closed. Do not print a separate `create-branch.sh --check failed` branch from Step 0; `IMPLEMENT_TMPDIR` does not exist yet for Tool Failures logging.

Run the shared entry gate helper using the parsed branch facts. Its contract lives at `${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.md`.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh \
  --mode implement \
  --current-branch "$CURRENT_BRANCH" \
  --is-main "$IS_MAIN" \
  --is-user-branch "$IS_USER_BRANCH" \
  --user-prefix "$USER_PREFIX"
```

Parse `ENTRY_GATE` and `SKIP_BRANCH_CHECK` from this script's stdout in isolation. Do not concatenate it with `create-branch.sh --check` output for a single `eval`. On non-zero exit, print the raw `GATE_ERROR=...` line first, then print the normalized internal-contract message and abort:

**⚠ /implement: internal Step 0 contract violation in session-entry-gate.sh. Aborting.**

Do NOT print the clean-main banner for `GATE_ERROR`; that banner is reserved for `session-setup.sh` `PREFLIGHT_ERROR`.

Set `continue_from_current=true` iff `SKIP_BRANCH_CHECK=true`. This alias is retained for downstream Step 1.m compatibility; `SKIP_BRANCH_CHECK` is the authoritative key for assembling `session-setup.sh` argv.

If `SKIP_BRANCH_CHECK=true`, run setup with `--skip-branch-check`:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-implement --skip-branch-check --check-reviewers [--caller-env "$SESSION_ENV_PATH" OR "$CALLER_ENV_PATH" under forked_target=true] [--skip-codex-probe] [--skip-cursor-probe]
```

If `SKIP_BRANCH_CHECK=false`, run setup without `--skip-branch-check`:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-implement --check-reviewers [--caller-env "$SESSION_ENV_PATH" OR "$CALLER_ENV_PATH" under forked_target=true] [--skip-codex-probe] [--skip-cursor-probe]
```

On non-zero exit, always print the raw `PREFLIGHT_ERROR=...` line first. Then print the normalized skill-level message and abort:

**⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run (the branch naming convention is the explicit opt-in to continue from current state); (c) commit or stash uncommitted changes on `main` first.**

Key any future sub-message on the substring inside `PREFLIGHT_ERROR` (for example, `Not on main branch` or `Working tree is not clean`), not on the prior `IS_MAIN` value from `create-branch.sh --check`; detached HEAD can report `IS_MAIN=true` with an empty `CURRENT_BRANCH`.

Then:
- Ensure a per-run session id exists for design-manifest freshness checks. `session-setup.sh` already wrote the value; this call is preserved as an idempotent no-op for older harnesses and fallback paths (see `scripts/write-session-id.md` for the contract):
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/write-session-id.sh --output "$IMPLEMENT_TMPDIR/session-id"
  export IMPLEMENT_TMPDIR
  export LARCH_TOKEN_SESSION_ID="$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)"
  export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"
  # Snapshot the live Claude transcript path BEFORE later concurrent
  # /implement or /design Claude sessions can race the resolver. The
  # exported LARCH_CLAUDE_SOURCE_FILE points downstream
  # token-claude-source.sh / token-report.sh invocations at this fixed
  # transcript instead of "newest .jsonl by mtime", which would otherwise
  # attribute tokens to the wrong run when concurrent sessions write
  # transcripts under the same project dir. Best-effort: a snapshot
  # failure leaves the env unset, records a Warnings entry, and later
  # transcript capture falls back to discovery.
  if "${CLAUDE_PLUGIN_ROOT}/scripts/token-claude-source.sh" \
          > "$IMPLEMENT_TMPDIR/claude-source.env" \
          2>"$IMPLEMENT_TMPDIR/claude-source-error.log"; then
      export LARCH_CLAUDE_SOURCE_FILE="$IMPLEMENT_TMPDIR/claude-source.env"
  else
      _source_exit=$?
      "${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" \
          --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
          --site "Step 0" \
          --tool "token-claude-source.sh" \
          --exit-code "$_source_exit" \
          --category Warnings \
          --output-file "$IMPLEMENT_TMPDIR/claude-source-error.log" \
          --redact || true
  fi
  session_env_args=(
    --output "$IMPLEMENT_TMPDIR/session-env.sh"
    --repo <value>
    --repo-unavailable <value>
    --codex-healthy <value>
    --cursor-healthy <value>
    --timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv"
    --token-session-id "$LARCH_TOKEN_SESSION_ID"
    --prev-implement-tmpdir "$IMPLEMENT_TMPDIR"
  )
  [[ -n "${LARCH_CLAUDE_SOURCE_FILE:-}" ]] && session_env_args+=(--claude-source-file "$LARCH_CLAUDE_SOURCE_FILE")
  "${CLAUDE_PLUGIN_ROOT}/scripts/write-session-env.sh" "${session_env_args[@]}"
  "${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 0 — preflight" || true
  "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 0 — preflight" || true
  # token-mark Step 0 — preflight
  # timing-mark Step 0 — preflight
  ```
  Step 1 compares this value to the design manifest's `SESSION_ID` before reusing any exported plan.
- If `REPO_UNAVAILABLE=true`: print `**⚠ Could not determine repository name. CI monitoring (Steps 10, 12) and merge (Step 12b) will be skipped.**` Set `repo_unavailable=true`.
- If `CODEX_AVAILABLE=false`: print `**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**` Else if `CODEX_HEALTHY=false`: print `**⚠ Codex installed but not responding (health check failed). Using Claude replacement.**` Same for Cursor (only check `*_HEALTHY` when `*_AVAILABLE=true`).

The session-env file is passed to `/design` (Step 1) and `review-and-fix.sh` (Step 5) via `--session-env-path`. It also carries `LARCH_CLAUDE_PLUGIN_ROOT` so later Bash blocks can recover `${CLAUDE_PLUGIN_ROOT}` without sourcing the file.

Every Bash block after Step 0 that touches `token-ledger.sh` / `token-report.sh` / `timing-ledger.sh` / `timing-report.sh` MUST rehydrate `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` via `read-session-env-key.sh` before invoking the script. It MUST also assign and export `IMPLEMENT_TMPDIR` so `timing-ledger.sh` accepts the per-run ledger path as an allowed session root:

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
```

### Cross-Skill Health Propagation

## Phantom Untracked Probe

At selected `/implement` boundaries, detect non-ignored untracked files that
appeared after the Step 0.5 session baseline. This is advisory only: phantoms
are logged to Execution Issues, never cleaned automatically.

Call form:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
PHANTOM_OUT=$("${CLAUDE_PLUGIN_ROOT}/scripts/check-phantom-dirty.sh" \
  --baseline "$IMPLEMENT_TMPDIR/untracked-baseline.z" \
  --step <step-id> \
  --phantom-paths-dir "$IMPLEMENT_TMPDIR")
```

Parse `STATUS`, `REASON`, `PHANTOM_COUNT`, and `PHANTOM_PATHS_FILE` without
`eval`/`source`. On `STATUS=phantom`, append this Warnings entry and continue:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/append-execution-issue.sh" \
  --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
  --category Warnings \
  --entry "- **Step <step-id> — phantom untracked files:** $PHANTOM_COUNT file(s) appeared since session baseline (inspect $IMPLEMENT_TMPDIR/phantom-paths-<step-id>.z locally)"
```

On `STATUS=unknown`, append this Warnings entry and continue:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/append-execution-issue.sh" \
  --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
  --category Warnings \
  --entry "- **Step <step-id> — phantom detection inconclusive:** STATUS=unknown REASON=${REASON:-unknown}"
```

If `append-execution-issue.sh` fails at a probe site, log a secondary Warnings
entry if possible (`Step <step-id> — phantom warning append failed: <ERROR>`)
and continue. On `STATUS=clean` or `STATUS=tracked-only`, continue silently.

Probe locations:
- After Step 2 dispatch returns on the external-implementer `STATUS=complete`
  path only: `--step 2-post-dispatch`. Do not probe when
  `STATUS=claude_fallback`; Claude-fallback implementation files are
  uncommitted until Step 4.
- After Step 4.r: `--step 4.r-post-rebase`.
- After Step 7.r, only when `FILES_CHANGED=true`: `--step 7.r-post-rebase`.
- After Step 7a.r: `--step 7a.r-post-rebase`.
- Immediately before `ship-pr.sh` first invocation (Step 8+ entry): `--step 8-pre-bump`.

There is intentionally no post-Step-6 probe. When `FILES_CHANGED=true`,
review-created files are legitimately untracked until Step 7 commits them; a
post-Step-6 probe would false-positive. The post-Step-7.r probe covers the
committed review-fix state.

## Execution Issues Tracking

### Follow-up Work Principle

Durable, actionable follow-up identified during design / implementation / review is tracked through one of three paths, selected by the OOS triage policy below: (a) folded inline into the current PR's commits (no separate GitHub issue), (b) auto-filed via Step 9a.1 as an OOS GitHub issue, or (c) manually filed via `/issue`. The committed `larch-logs/implement/<RUN_ID>/execution-issues.ndjson` batch is the durable store for execution content for paths (b) and (c). Path (a)'s audit trail is the union of the commit message, the relevant `execution-issues.md` category entry (`Pre-existing Code Issues` for main-agent-discovered defects per the dual-write rule below; `Warnings` for Step 5.5 inline-triage breadcrumbs and for Step 9a.1 manifest-harvest security-routing breadcrumbs — note that Step 9a.1 manifest harvest does NOT perform rules-1-2 inline triage), and — when `$ISSUE_NUMBER` is set — the terminal summary comment which points readers at the committed run log. Filing-path details:

1. **Auto-filed via Step 9a.1** — items fitting the OOS pipeline that survive triage as filed-OOS candidates (accepted OOS from `/design` or Step 5 review voting, or main-agent items via the dual-write below). Step 9a.1 creates issues via `/issue` batch mode.
2. **Manually filed via `/issue`** — durable follow-up not fitting OOS schema (e.g., a process-level gap surfaced by a warning). After `/issue` returns the number, reference it in the originating `execution-issues.md` entry: append `→ filed as #<N>` to the entry's description line in place. Step 11 converts the entry into the `execution-issues` larch-log batch.

**Actionability drives filing**, not category. `Pre-existing Code Issues` are always logged in `execution-issues.md` (the durable audit trail) but only dual-write to the OOS artifact when the entry survives triage as a filed-OOS candidate — see the dual-write subsection below for the gate. `Tool Failures` / `CI Issues` / `Warnings` — file when the failure exposes a recurring / systemic defect; log-only for one-off transients. `External Reviewer Issues` / `Permission Prompts` — typically log-only (operational telemetry); file only when the pattern is persistent across sessions.

**Carve-outs**: Non-accepted OOS (voting rejected) land in the `oos-issues` larch-log batch under the "Rejected / Out-of-Scope Observations (not filed)" sub-block. Rejected review findings land in `$IMPLEMENT_TMPDIR/rejected-findings.md` and are written to the `plan-review-tally` / `code-review-tally` batches under dedicated `## Rejected Plan Review Findings` / `## Rejected Code Review Findings` sub-headers — the committed run log is the single source of truth. Step 4 (plan review rejected) and Step 16 (code review rejected) emit only one-line breadcrumbs and do NOT reprint the full findings to the terminal transcript. `repo_unavailable=true` blocks BOTH paths: Step 9a.1 keeps the entry in `oos-accepted-main-agent.md` and reports `Skipped — repo unavailable` in the `oos-issues` batch; manual `/issue` keeps the item in `execution-issues.md` — do NOT call `/issue` manually when `repo_unavailable=true`. **Security findings are NEVER filed via this principle** — route through SECURITY.md's private disclosure flow.

**Sanitize before filing from execution context.** Any issue body or larch-log record composed from execution-session-derived content (execution-issues.md, oos-accepted-main-agent.md, reviewer prose, any session-derived source) MUST apply the dual-write redaction rules below (secrets → `<REDACTED-TOKEN>`, internal URLs → `<INTERNAL-URL>`, PII → `<REDACTED-PII>`) plus SECURITY.md's outbound-redaction subsection. `/issue`'s outbound shell scrubber covers secrets but not internal hostnames / URLs or PII — prompt-level sanitization is required. `/issue` batch mode forwards Description verbatim into public issue bodies; `larch-log.sh` applies shell-level tmpdir/secrets redaction before committing run payloads.

Log noteworthy issues to `$IMPLEMENT_TMPDIR/execution-issues.md` throughout execution. **Any step** may append. Log pre-existing code issues not fixed, tool failures, permission prompts, external reviewer failures, CI transients, and any uncategorized `⚠` warning.

For tool, Bash, helper, or agent failures where stdout/stderr or a returned error body exists, capture the full content into a step-local file under `$IMPLEMENT_TMPDIR` and append it with:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" \
  --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
  --site "<step-id>" \
  --tool "<tool label>" \
  --exit-code "<exit-code>" \
  --category "<Tool Failures|External Reviewer Issues|CI Issues|Warnings>" \
  --output-file "$IMPLEMENT_TMPDIR/<failure-capture>.log" \
  --redact || true
```

Do not summarize, truncate, or replace the captured body with only an `ERROR=` token. Existing one-line `append-execution-issue.sh` calls remain appropriate for synthetic warnings that do not have tool output, but any real failed invocation must preserve its captured output through `append-tool-failure.sh`.

**Entry format** — entries grouped by category. If the category header exists, insert the bullet at the end of its list; else add header + bullet at EOF.

```markdown
### <Category>
- **Step <N>**: <description with enough detail for later investigation>
```

**Categories** (exact headers; entries chronological within a category; categories not intermixed): `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings` (for `⚠` not fitting a more specific category; do NOT duplicate), `Q/A` (Step 2 opportunistic questions + mid-coding ambiguity resolutions — see Step 2 for schema and progressive-upsert rule).

### File-conflict rule for OOS dependency emission

**Best-effort when the pre-pass succeeds.** Two OOS issues that may run in parallel SHOULD NOT modify the same file unless their Descriptions expose explicit, parseable, non-overlapping line ranges for that file under the inclusive-overlap rule. Step 9a.1's combine pass (Step 9a.1 step 3.4) writes the working batch to `$IMPLEMENT_TMPDIR/oos-combined.md`; after `oos-issue-cap.sh` capping at step 3.4b, both `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-file-conflict-deps.sh` and the `/issue` batch-mode invocation read that path as `--input-file`. The helper emits `--intra-batch-deps-file` rows enforcing the no-same-file-parallel-edits rule; the helper contract lives at `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-file-conflict-deps.md`. The deterministic tie-break is lower 1-based batch index blocks higher. The TSV is numeric-only, so sanitization is preserved and no reviewer prose gains a new public surface.

The rule is mechanically enforced ONLY when the pre-pass exits 0 with a non-empty TSV. On exit 0 with non-empty TSV, Step 9a.1 forwards `--intra-batch-deps-file` to `/issue`; Phase-2 LLM dep-analysis still runs for semantic deps between non-conflicting entries (the pre-pass supplies only same-file conflict edges). On exit 0 with empty TSV, `--intra-batch-deps-file` is omitted and Phase-2 LLM dep-analysis runs as the sole dep-detection path. On any non-zero helper exit (Tier-2 cap exceeded, parser failure, missing regex lib, invalid env caps, etc.) Step 9a.1 forwards the batch to `/issue` WITHOUT `--intra-batch-deps-file` (and without `--no-dep-llm`), surfaces a `**⚠ /implement: oos-file-conflict pre-pass failed (exit <N>) — proceeding without caller-supplied serialization edges; review accepted-OOS Descriptions before greenlighting parallel workers**` warning to the user, AND appends a `Tool Failures` entry to `$IMPLEMENT_TMPDIR/execution-issues.md`. `/issue`'s Phase-2 LLM dep-analysis still runs but is non-deterministic, so file-conflict serialization becomes operator-supervised in this degraded mode.

Caller TSV edges are merged (unioned) with `/issue` Phase-2 LLM dep-analysis when `--no-dep-llm` is not set; neither source has precedence. Acyclicity is delegated to `/issue`'s SCC cycle resolution: "For any SCC with more than one node, drop the lowest-priority outbound edge to break the cycle: among the SCC's nodes, pick the one with the lowest input index, and within its `BLOCKED_BY` list pick the lexically-earliest entry; remove that single entry, then re-run SCC detection." Known limitation: file-conflict TSV edges are silently dropped on `/issue`'s Step-5-skip paths (`LIST_STATUS=failed`, allocator failure, empty-CANDIDATES + `N<2`); track that as a follow-up issue if it matters for the current batch.

**Privacy guardrail.** OOS Descriptions are filed as PUBLIC GitHub issues by `/issue`, so reviewer-supplied `path:line` hints in those Descriptions become public on filing. Reviewers should follow `SECURITY.md` and avoid naming high-risk paths or pasting secret-adjacent material in OOS Descriptions; machine ordering relies on the numeric-only TSV, so sanitizing prose costs nothing in conflict-detection fidelity.

### OOS triage policy

Before accepting any finding at one of the controlled acceptance points, triage it:

1. Documentation drift (any size): do NOT file an OOS issue. The workflow that detects the drift fixes it as part of the current work (i.e., folded into the current PR). Drift means a stale or now-incorrect doc statement that needs corrective alignment with current behavior — it is identified by what is wrong, not by line count, so rule 1 takes precedence over rule 4 when both could apply (a 40-line doc-drift fix folds inline; it is NOT batched into rule 4).
2. A bug whose fix is < ~30 lines of code: do NOT file an OOS issue. Fold the fix into the current PR.
3. Multiple medium-sized bug fixes (each individually >= ~30 LOC): combine them all into ONE filed OOS issue (not one issue per item).
4. Multiple moderate-sized documentation changes (each individually ~30-100 lines, NOT drift): combine them all into ONE filed OOS issue. Applies to substantive non-drift doc work (e.g., new sections, intentional rewrites of non-stale content) that is genuinely out-of-scope for the current PR.

Threshold convention: rules 2 and 3 use `< ~30` and `>= ~30` respectively, with rule 3 inclusive at the ~30-LOC boundary; the combine-pass criteria 5/6 at Step 9a.1 step 3.4 use the same convention. Rule B's SIMPLE classifier reuses the same `~30` LOC convention. The threshold is identical across triage rules 2-3, combine-pass criterion 5/6, and combine-pass Rule B's SIMPLE judgment. The `~` is intentional — the LOC estimate is a natural-language judgment, precise bookkeeping is not required, but the inclusive/exclusive direction at the boundary is fixed.

Actionable consequence: rules 1-2 do NOT enter accepted-OOS artifacts; fix them inline in the current PR. Noteworthy inline fixes that operators may want to audit later (e.g. a non-trivial pre-existing-code touch that was not part of the user's prompt) should be logged under the `Warnings` category in `$IMPLEMENT_TMPDIR/execution-issues.md` so Step 11 can append them to the run's `execution-issues` log batch without filing. Rules 3-4 may enter accepted-OOS artifacts; Step 9a.1's combine pass MUST collapse each class to one filed issue when at least two entries in that class are present. **Rules A and B and criteria 5/6** at Step 9a.1 step 3.4 take precedence over the carve-out. Rule A collapses LLM-judged thematic groups; Rule B collapses leaked SIMPLE entries; criteria 5/6 collapse medium-bug and moderate-doc classes. Security findings are NEVER folded inline and NEVER filed via this OOS path regardless of size; route through SECURITY.md's private disclosure flow. If a finding cannot safely land in the current branch (for example, it would require reverting the core feature, exceed the Step 12d fix budget, or otherwise conflict with the accepted plan), file it as a single OOS item even when the small-bug rule would otherwise apply.

### Mechanical enforcement: `Pre-existing Code Issues` dual-write

Whenever the main agent identifies a Pre-existing code issue, log it under `Pre-existing Code Issues` in `execution-issues.md` regardless of triage outcome (the log is the durable audit trail). Then apply the OOS triage policy above: if and only if the item survives triage as a filed-OOS candidate (i.e. NOT doc drift and NOT a < ~30 LOC bug), the agent MUST also append a corresponding `### OOS_N:` block to `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md` so Step 9a.1 can file it. Items classified by triage as "fold inline" are logged under `Pre-existing Code Issues` but are NOT dual-written to the OOS artifact; the inline fix lands in the current PR's commits. This dual-write rule is mechanical, runs in every mode, and converges main-agent-discovered bugs into the same accepted-OOS pipeline as reviewer-surfaced OOS from `/design` and Step 5. For durable follow-up outside this category, enforcement is prescriptive (principle above), not mechanical — use `/issue` directly.

**Schema** (matches `/issue`'s batch-mode parser at `${CLAUDE_PLUGIN_ROOT}/skills/issue/scripts/parse-input.sh`):

```markdown
### OOS_<N>: <short title — one line>
- **Description**: <file path and line number(s)>; <what is wrong>; <concrete reproduction context>; <suggested fix — one or more options>. May span multiple non-blank lines.
- **Reviewer**: Main agent
- **Vote tally**: N/A — auto-filed per policy
- **Phase**: implement
```

`<N>` is a per-session sequential index from 1. To correct an existing entry, use **in-place replacement**: locate by `<N>` and overwrite, preserving `<N>`. Do NOT append on correction (duplicates). The dedup guard below applies only to **new** entries: scan for a block whose title matches case-insensitively (after whitespace strip); if matched, do NOT append. `/issue` provides an LLM-based semantic duplicate backstop but it is not deterministic — the in-file dedup runs first for byte-exact duplicates.

**Sanitize the description before append.** Redact secrets / API keys / OAuth / JWT / passwords / certificates → `<REDACTED-TOKEN>`; internal hostnames / URLs / private IPs → `<INTERNAL-URL>`; PII (emails, names, account IDs linked to a real user) → `<REDACTED-PII>`. The Description is forwarded verbatim into a public GitHub issue — paraphrase reproduction context rather than copying log lines when in doubt.

If `oos-accepted-main-agent.md` does not exist, create it with the new entry. If `repo_unavailable=true`, still append (Step 9a.1 skips filing). **Repo-unavailable audit-loss disclosure**: in `repo_unavailable=true` mode, neither tracking-issue summary comments nor the PR body's Execution Issues block exist (Phase 3 slim PR body dropped the Execution Issues block, and without repo access no summary comments can be created). `$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail and is removed at Step 18. Operators running with `repo_unavailable=true` must preserve the tmpdir manually if an audit trail is required.

<!-- step:0.5 — Resolve Tracking Issue -->

Print: `> **🔶 /implement 0.5: tracking issue**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 0.5 — tracking issue" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 0.5 — tracking issue" || true
# token-mark Step 0.5 — tracking issue
# timing-mark Step 0.5 — tracking issue
```

Resolve a stable `ISSUE_NUMBER` and `RUN_ID` for the session. Committed `larch-logs/implement/<RUN_ID>/` files are the single source of truth for Phase 3+ report content (voting tallies, version bump reasoning, OOS list, execution issues, run statistics, token reports, and timing reports); the tracking issue carries only four slim marker-keyed summary comments, and the PR body remains a slim projection.

**MANDATORY — READ ENTIRE FILE** before composing any tracking-issue summary comment at Steps 0.5, 1, 9a.1, 11, or 18: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/summary-comment-template.md`. It defines the four allowed marker literals (`larch:metadata`, `larch:diagrams`, `larch:plan`, `larch:final-summary`) and the rule that bulky payloads live in `larch-logs/`, not in GitHub comments.

**Early exit — `design_only=true` AND `no_issues=true`**: check this before all branches. If both are set: set `deferred=true`, leave `$ISSUE_NUMBER` unset. Local artifacts may still be prepared under `$IMPLEMENT_TMPDIR`, but no tracking issue is created, no sentinel is written, and `$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail (removed at Step 18). Print `⏩ 0.5: tracking issue status=skip reason=design-only-no-issues elapsed=<elapsed>`. Proceed to Step 1.

**`RUN_ID` initialization**: if `--run-id <ID>` was provided at flag-parse time, use that value unchanged. Otherwise derive from the session ID file written at Step 0:

```bash
RUN_ID=$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
# intentionally non-stable: without --run-id, fallbacks below use uuidgen(1) and date(1) when session-id is empty (identifiers for this run; not literal-stable).
[ -n "$RUN_ID" ] || RUN_ID=$(uuidgen 2>/dev/null | tr -d '\r\n' || true)
[ -n "$RUN_ID" ] || RUN_ID=$(od -vAn -N16 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n' || true)
[ -n "$RUN_ID" ] || RUN_ID="unknown-$(date +%s)"
```

This sets the canonical `RUN_ID` for new runs (Branches 2–4). Branch 1 (resume) overrides this by reading `RUN_ID` from `parent-issue.md` — the sentinel's value is authoritative for resumed runs because larch-logs were already committed under that ID. Branches 2–4 MUST NOT independently invent a `RUN_ID` value; they use the value initialized here.

**Decision order** (top-to-bottom; first match wins):

**Step 0.5 entry default**: set `deferred=false`. Branches 1 / 2 / 3 succeed → `deferred` stays `false`. Branch 4 on success → `deferred` stays `false`. Branch 4 failure routing: `create-issue` fails → `deferred=true`, proceed to Step 1; `larch-log.sh init` (manifest write) fails → `deferred=true`, `STALL_TRACKING=true`, skip to Step 18 (do NOT clear `$ISSUE_NUMBER`); metadata summary upsert fails → `deferred=true`, proceed to Step 1; sentinel write fails → `deferred=true`, proceed to Step 1. This establishes a clean binary state for Steps 1 / 2 / 5 / 7a / 8 / 9a / 9a.1 / 11 / 18 — there is no tri-state "unset" to handle.

**Round-trip detection at Step 0.5**: whenever a Branch 1 / 2 / 3 / 4 path has resolved `ISSUE_NUMBER` and is about to rename the tracking issue to `in-progress`, run `${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh` and pass the resulting `ROUND_TRIP=true|false` as `--round-trip "$ROUND_TRIP"` to `tracking-issue-write.sh rename`. Issue bodies and feature descriptions MUST be written to temp files under `$IMPLEMENT_TMPDIR` and passed via `--text-file`; only short trusted titles may use `--text-string`. Best-effort: if a body/title fetch or the detector fails, log to `Tool Failures`, set `ROUND_TRIP=false`, and continue with the rename. `tracking-issue-write.sh` owns sticky preservation of any pre-existing marker; callers pass only the fresh detector result. See `${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.md` and `${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.md`.

**Branch 1 — sentinel exists** (`$IMPLEMENT_TMPDIR/parent-issue.md` present):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-read.sh --sentinel "$IMPLEMENT_TMPDIR/parent-issue.md"
```

Parse stdout for `ISSUE_NUMBER`, `RUN_ID`, `ADOPTED`.

- **Mismatch guard**: if `ISSUE_ARG` is non-empty AND `ISSUE_NUMBER_in_sentinel != ISSUE_ARG`: print `**⚠ 0.5: tracking issue — sentinel mismatch (sentinel has #$ISSUE_NUMBER_in_sentinel, --issue requested #$ISSUE_ARG). Clearing sentinel and re-adopting.**`, remove the sentinel file, preserve any existing `larch-logs/` files, and fall through to Branch 2.
- **Reuse**: set `ISSUE_NUMBER` and `RUN_ID` from sentinel. Ensure the manifest still exists with `larch-log.sh init --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --issue "$ISSUE_NUMBER"`; this is idempotent and emits `UNCHANGED=true` on an existing manifest.
- **No hydration step**: marker-keyed summary comments are projections only. Never fetch GitHub comment bodies to reconstruct run state; resume state comes from the committed `larch-logs/implement/<RUN_ID>/` tree plus session tmpdir artifacts.

  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh init --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --issue "$ISSUE_NUMBER"
  ```

- **Resume rename safety net**: if `ISSUE_NUMBER` is set, run a best-effort idempotent rename to `[IN PROGRESS]`. This recovers from the case where a prior session wrote the sentinel but its Branch 2 / Branch 3 / Branch 4 rename failed (best-effort, logged but non-blocking) — without this, a resumed run could complete with merge/Step 18 renames while the GitHub title never received `[IN PROGRESS]`:

  ```bash
  ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
    --text-file "$IMPLEMENT_TMPDIR/round-trip-input-issue-body.txt" \
    --text-file "$IMPLEMENT_TMPDIR/round-trip-input-feature-desc.txt" \
    --text-string "$ISSUE_TITLE" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
  ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
  case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
  ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename --issue $ISSUE_NUMBER --state in-progress --round-trip "$ROUND_TRIP"
  ```

  Best-effort: on `FAILED=true` or non-zero exit, log `Step 0.5 — Branch 1 resume rename to in-progress failed: $ERROR` to `Tool Failures` and continue. The rename is idempotent (`RENAMED=false` when the title already starts with the target lifecycle prefix and the round-trip marker state already matches the desired `--round-trip` value after sticky preservation; see `scripts/tracking-issue-write.md`), so the common resume case is a single cheap `gh issue view` round-trip with no edit.

Proceed to Step 1.

**Branch 2 — `--issue <N>` provided** (`ISSUE_ARG` non-empty, no usable sentinel after Branch 1 mismatch-clear):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/get-issue-state.sh --issue "$ISSUE_ARG"
```

Parse `STATE`, `URL`, `IS_PR` (or `FAILED=true` + `ERROR=` on `gh` failure). On `FAILED=true`, print `**⚠ 0.5: tracking issue — get-issue-state failed: $ERROR. Aborting.**` and skip to Step 18.

Detect PR-vs-issue: if `IS_PR=true`, print `**⚠ 0.5: tracking issue — #$ISSUE_ARG is a pull request, not an issue. Aborting.**` and skip to Step 18.

If `STATE=CLOSED`: print `**⚠ 0.5: tracking issue — adopted issue #$ISSUE_ARG is CLOSED. Aborting.**`, emit `IMPLEMENT_BAIL_REASON=adopted-issue-closed` on stdout, skip to Step 18. (`/fix-issue` Step 5a consumes this bail token and branches to a specific warning + skip-to-cleanup path without calling `issue-lifecycle.sh close`.)

Else (`STATE=OPEN`): adopt the issue, initialize the run manifest, and publish the metadata summary comment. No existing tracking-issue comment is read or hydrated; marker-keyed summary comments are projections and `tracking-issue-summary.sh` is responsible for upserting the one comment matching the marker literal.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh init --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --issue "$ISSUE_ARG"
LARCH_VER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}')
[ -n "$LARCH_VER" ] || LARCH_VER="unknown"
printf 'Run `%s` adopted issue #%s. Logs: `larch-logs/implement/%s/`.\nAgent: `%s` | Larch: `%s`\n' \
  "$RUN_ID" "$ISSUE_ARG" "$RUN_ID" "${coder:-claude}" "$LARCH_VER" > "$IMPLEMENT_TMPDIR/summary-metadata.md"
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary \
  --issue "$ISSUE_ARG" \
  --marker "<!-- larch:metadata v1 runid=$RUN_ID -->" \
  --content-file "$IMPLEMENT_TMPDIR/summary-metadata.md"
```

On `LOG_WRITTEN=false` with `ERROR=` from `larch-log.sh`, or `FAILED=true` from `tracking-issue-summary.sh`, print `**⚠ 0.5: tracking issue — metadata publication failed: $ERROR. Aborting.**` and skip to Step 18.

On either sub-branch, **rename the adopted issue to `[IN PROGRESS]`** so the title reflects the active run (matches the title-prefix lifecycle applied to fresh-created issues in Branch 4 — see `scripts/tracking-issue-write.md` "Title-prefix lifecycle"):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
  --text-string "$ISSUE_TITLE" \
  --text-file "$IMPLEMENT_TMPDIR/round-trip-input-issue-body.txt" \
  --text-file "$IMPLEMENT_TMPDIR/round-trip-input-feature-desc.txt" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename --issue $ISSUE_ARG --state in-progress --round-trip "$ROUND_TRIP"
```

Best-effort: on `FAILED=true` or non-zero exit, log `Step 0.5 — Branch 2 rename to in-progress failed: $ERROR` to `Tool Failures` and continue. The rename is idempotent (`RENAMED=false` when the title already starts with the target lifecycle prefix and the round-trip marker state already matches the desired `--round-trip` value after sticky preservation; see `scripts/tracking-issue-write.md`); failure does not affect adoption correctness — it only loses the visual-indicator benefit. Step 12a/12b's terminal rename to `[DONE]` and Step 18's stalled-rename apply to adopted issues uniformly (no `ADOPTED=` guard).

Then write `$IMPLEMENT_TMPDIR/parent-issue.md`:

```
ISSUE_NUMBER=$ISSUE_ARG
RUN_ID=$RUN_ID
ADOPTED=true
```

`ADOPTED=true` per the `scripts/tracking-issue-read.md` contract: Phase 3 Branch 2 adopts an existing open issue. Set `ISSUE_NUMBER=$ISSUE_ARG`. Proceed to Step 1.

**Branch 3 — PR on current branch with `Closes #<N>`** (no sentinel, no `--issue`):

Check for an existing PR on the current branch; if present, extract the first `Closes #<N>` line from its body:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/extract-closes-issue-from-pr.sh
```

If a number emerges as `RECOVERED_N`: validate the target issue via `${CLAUDE_PLUGIN_ROOT}/scripts/get-issue-state.sh --issue "$RECOVERED_N"` (same PR-vs-issue + CLOSED checks as Branch 2). On `FAILED=true`, log `Step 0.5 — Branch 3 get-issue-state failed: $ERROR` to `Tool Failures` and fall through to Branch 4. If target is a PR URL (`IS_PR=true`) or CLOSED (`STATE=CLOSED`), fall through to Branch 4. Else (`STATE=OPEN`, `IS_PR=false`): adopt the issue and publish metadata without reading existing summary comments.

Initialize the run manifest and publish the metadata summary comment using the same marker-keyed flow as Branch 2:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh init --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --issue "$RECOVERED_N"
LARCH_VER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}')
[ -n "$LARCH_VER" ] || LARCH_VER="unknown"
printf 'Run `%s` recovered issue #%s from the current PR body. Logs: `larch-logs/implement/%s/`.\nAgent: `%s` | Larch: `%s`\n' \
  "$RUN_ID" "$RECOVERED_N" "$RUN_ID" "${coder:-claude}" "$LARCH_VER" > "$IMPLEMENT_TMPDIR/summary-metadata.md"
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary \
  --issue "$RECOVERED_N" \
  --marker "<!-- larch:metadata v1 runid=$RUN_ID -->" \
  --content-file "$IMPLEMENT_TMPDIR/summary-metadata.md"
```

On `LOG_WRITTEN=false` with `ERROR=` from `larch-log.sh`, or `FAILED=true` from `tracking-issue-summary.sh`, print `**⚠ 0.5: tracking issue — metadata publication failed: $ERROR. Aborting.**` and skip to Step 18.

Then **rename the recovered issue to `[IN PROGRESS]`** so the title reflects the active run (matches Branch 2 / Branch 4):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
  --text-string "$ISSUE_TITLE" \
  --text-file "$IMPLEMENT_TMPDIR/round-trip-input-issue-body.txt" \
  --text-file "$IMPLEMENT_TMPDIR/round-trip-input-feature-desc.txt" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename --issue $RECOVERED_N --state in-progress --round-trip "$ROUND_TRIP"
```

Best-effort: on `FAILED=true` or non-zero exit, log `Step 0.5 — Branch 3 rename to in-progress failed: $ERROR` to `Tool Failures` and continue. Idempotent (`RENAMED=false` when the title already starts with the target lifecycle prefix and the round-trip marker state already matches the desired `--round-trip` value after sticky preservation; see `scripts/tracking-issue-write.md`).

Then write sentinel with `ADOPTED=true` (Phase 3 Branch 3 adopts an existing open issue via PR-body recovery; per the `scripts/tracking-issue-read.md` contract). Set `ISSUE_NUMBER=$RECOVERED_N`. Proceed to Step 1.

If no PR exists, no `Closes #<N>` match, or the match is not a valid adoptable issue: fall through to Branch 4.

**Branch 4 — truly fresh run** (no sentinel, no `--issue`, no PR-body recovery):

Create the tracking issue **immediately** so subsequent summary comments and committed run logs are discoverable from the moment the run starts. On any failure, fall back to deferred/absent tracking issue (`deferred=true`) and continue — do NOT bail.

1. **Derive the tracking-issue title** from `FEATURE_DESCRIPTION`: take the first line if present (everything before the first `\n`), else the first 80 characters; strip leading/trailing whitespace; collapse internal whitespace runs to a single space. Do NOT use any PR-related identifier — the PR is not created until Step 9.

   **Prepend `[IN PROGRESS]` (followed by a space)** to the derived title. This is the tracking-issue title-prefix lifecycle (see `scripts/tracking-issue-write.md` "Title-prefix lifecycle"): `[IN PROGRESS]` signals an active run, later flipped to `[DONE]` on confirmed merge (Step 12a/12b), or `[STALLED]` on failure paths (Step 18). `/fix-issue`'s `find-lock-issue.sh` excludes any title starting with a managed prefix from auto-pick, so prefixed tracking issues never appear as candidates. Adopted issues (Branch 2/3) get the same prefix applied at adoption time so the title reflects the active run uniformly across all branches; when `/fix-issue` invokes `/implement` with `--issue $ISSUE_NUMBER`, the issue is already pre-renamed to `[IN PROGRESS]` by `find-lock-issue.sh` at lock time, so this Branch 2/3 rename hits the idempotent `RENAMED=false` no-op path; the call is preserved for standalone `/implement --issue` invocations against non-pre-marked issues. `/implement` owns the title prefix during the run while the rest of the title stays user-authored. Distinct from `/fix-issue`'s comment-based "IN PROGRESS" lock (concurrency control on the subject issue, also acquired by `find-lock-issue.sh`); the two mechanisms coexist.

2. **Sanitize `FEATURE_DESCRIPTION` at compose time** (MANDATORY, and a strict gate because the issue body is a public GitHub surface). Apply prompt-level redaction to the prompt text BEFORE it is written to the issue body:
   - Secrets / API keys / OAuth / JWT / passwords / certificates → `<REDACTED-TOKEN>`
   - Internal hostnames / URLs / private IPs → `<INTERNAL-URL>`
   - PII (emails, names, account IDs tied to a real user) → `<REDACTED-PII>`

   `scripts/redact-secrets.sh` (invoked inside `tracking-issue-write.sh create-issue`) is the shell-layer backstop for the secrets family, but does NOT cover internal URLs or PII — prompt-level sanitization here is the first-line defense.

3. **Compose the issue body** with the SANITIZED prompt wrapped in a blockquote (not a fenced code block — blockquote is fence-injection-proof for any tilde or backtick content in the prompt). Write to `$IMPLEMENT_TMPDIR/tracking-issue-body.md`:

   ```markdown
   Tracking issue for *<derived-title>*. Runtime artifacts are committed under `larch-logs/implement/<RUN_ID>/`; marker-keyed comments below carry slim status summaries maintained by /implement as the run progresses.

   ## Original prompt

   > <sanitized FEATURE_DESCRIPTION — each line prefixed with "> ">

   > **Note**: the prompt above was sanitized at compose time (secrets / internal URLs / PII redacted where detected). Operators should still avoid pasting sensitive content into the /implement prompt because sanitization is best-effort and not comprehensive.
   ```

4. **Create the tracking issue** with the `[IN PROGRESS]` prefix (plus a trailing space) applied to the title (see step 1):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh create-issue --title "[IN PROGRESS] <derived-title>" --body-file "$IMPLEMENT_TMPDIR/tracking-issue-body.md"
   ```
   Parse `ISSUE_NUMBER` and `ISSUE_URL` from stdout. On `FAILED=true` OR non-zero exit, print `**⚠ 0.5: tracking issue — Branch 4 create-issue failed: $ERROR. Continuing with deferred/absent tracking issue.**`, log to `Tool Failures`, set `deferred=true`, leave `$ISSUE_NUMBER` unset, and proceed to Step 1. Downstream: Step 9a omits the `Closes #<N>` line entirely and replaces it with `_No tracking issue — auto-close N/A._`; Step 11 branch 3 skips cleanly; Step 18 URL print is silently skipped.

4b. **Immediately apply round-trip detection to the fresh issue title**: after `ISSUE_NUMBER` resolves, write the just-composed issue body and sanitized feature description to temp files under `$IMPLEMENT_TMPDIR`, run `round-trip-detect.sh` over those files plus the short derived title (parsing the same `ROUND_TRIP_OUT`/`awk`/`case` validation chain as the Branch 1/2/3 blocks above), then run:
   ```bash
   ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
     --text-string "$DERIVED_TITLE" \
     --text-file "$IMPLEMENT_TMPDIR/round-trip-input-issue-body.txt" \
     --text-file "$IMPLEMENT_TMPDIR/round-trip-input-feature-desc.txt" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
   ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
   case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
   ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename --issue "$ISSUE_NUMBER" --state in-progress --round-trip "$ROUND_TRIP"
   ```
   This is idempotent and cheap when `ROUND_TRIP=false`; it also lets Branch 4 add `[ROUND-TRIP]` before the sentinel is written.

5. **Initialize larch-log manifest and publish metadata summary** as a marker-keyed comment on the newly-created issue:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh init --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --issue "$ISSUE_NUMBER"
   LARCH_VER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}')
   [ -n "$LARCH_VER" ] || LARCH_VER="unknown"
   printf 'Run `%s` created issue #%s. Logs: `larch-logs/implement/%s/`.\nAgent: `%s` | Larch: `%s`\n' \
     "$RUN_ID" "$ISSUE_NUMBER" "$RUN_ID" "${coder:-claude}" "$LARCH_VER" > "$IMPLEMENT_TMPDIR/summary-metadata.md"
   ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary \
     --issue "$ISSUE_NUMBER" \
     --marker "<!-- larch:metadata v1 runid=$RUN_ID -->" \
     --content-file "$IMPLEMENT_TMPDIR/summary-metadata.md"
   ```
   On `LOG_WRITTEN=false` with `ERROR=` from `larch-log.sh init`, print `**⚠ 0.5: tracking issue — Branch 4 manifest initialization failed: $ERROR. Stalling to Step 18.**`, log to `Tool Failures`, set `deferred=true`, set `STALL_TRACKING=true`, and skip to Step 18 (skipping the sentinel write in step 6). **Do NOT clear `$ISSUE_NUMBER`** — the tracking issue was already created on GitHub at step 4, and Step 18 teardown needs `$ISSUE_NUMBER` to rename it from `[IN PROGRESS]` to `[STALLED]`.

   On `FAILED=true` from `tracking-issue-summary.sh`, print `**⚠ 0.5: tracking issue — Branch 4 metadata publication failed: $ERROR. Continuing with deferred/absent tracking issue.**`, log to `Tool Failures`, set `deferred=true`, clear `$ISSUE_NUMBER`, and proceed to Step 1 (skipping the sentinel write in step 6).

6. **Write the sentinel LAST**, only after `$ISSUE_NUMBER` and `$RUN_ID` are non-empty and step 5 succeeded (Load-Bearing Invariant #4 ordering):
   ```
   ISSUE_NUMBER=$ISSUE_NUMBER
   RUN_ID=$RUN_ID
   ADOPTED=false
   ```
   Write to `$IMPLEMENT_TMPDIR/parent-issue.md`. `ADOPTED=false` per the `scripts/tracking-issue-read.md` contract: Branch 4 CREATED a fresh tracking issue, not adopted an existing one. Skip this step on any step-4/step-5 failure per the deferred-fallback wiring above.

7. **Leave `deferred=false`** (the Step 0.5 entry default is unchanged on Branch 4 success — larch-log writes and summary updates in subsequent steps are enabled) and proceed to Step 1.

**Orphan-issue recovery note**: if a session crashes between step 4 (issue created on GitHub) and step 6 (sentinel written locally), a rerun will Branch-4 again and create a duplicate. Recovery: the operator passes `--issue <N>` on rerun to adopt the originally-created issue via Branch 2 (same behavior as the pre-change deferred-creation orphan case — not a regression).

### repo_unavailable=true

If `repo_unavailable=true`: skip all Step 0.5 branches, do NOT invoke `gh issue view` / `tracking-issue-write.sh`. No tracking issue is created, no sentinel is written, and `$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail (removed at Step 18). Print `⏩ 0.5: tracking issue status=skip reason=repo-unavailable elapsed=<elapsed>`.

### forked_target=true

If `forked_target=true`: skip Branches 1, 3, and 4 entirely; no tracking issue is created, adopted, renamed, summarized, or written to a sentinel. Set `deferred=true`, leave `ISSUE_NUMBER` unset, and keep fork metadata in orchestrator-local variables (`FORK_REPO`, `UPSTREAM_REPO`, `FORK_OWNER`).

When `ISSUE_ARG` is non-empty, do not adopt it as a tracking issue. Instead set `UPSTREAM_DESIGN_ISSUE=$ISSUE_ARG`, then fetch upstream context:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/get-issue-context.sh --issue "$ISSUE_ARG" --repo "$UPSTREAM_REPO" --tmpdir "$IMPLEMENT_TMPDIR"
```

Parse `TITLE_FILE` and `BODY_FILE`. If the user-supplied `FEATURE_DESCRIPTION` is empty, replace it with the contents of `$BODY_FILE`; otherwise the user description wins. On helper failure, print `**⚠ 0.5: tracking issue — upstream issue context fetch failed: $ERROR. Aborting.**` and skip to Step 18. `ISSUE_NUMBER` MUST remain unset under fork mode so Step 9a cannot inject `Closes #N` into the fork PR body. Print `⏩ 0.5: tracking issue status=skip reason=forked-dry-run elapsed=<elapsed>`.

### /fix-issue coordination

`/fix-issue` Step 5a forwards `--issue $ISSUE_NUMBER` to `/implement` so the two skills converge on the same tracking issue via Branch 2 by construction — `/implement` adopts the issue `/fix-issue` already locked, avoiding a duplicate tracking issue on the `/fix-issue` path. On `IMPLEMENT_BAIL_REASON=adopted-issue-closed` (Branch 2 CLOSED early-exit above), `/fix-issue` Step 5a branches to a specific warning and skips its close call. GO/IN PROGRESS lock-check logic in `/fix-issue` is unaffected by marker-keyed summary comments: `/implement`'s metadata comment carries the `<!-- larch:metadata v1 runid=<R> -->` first-line marker, and `tracking-issue-read.sh` filters those summary markers from aggregated task content.

### Larch-log Batches and Summary Comments

Steps 1, 2, 5, 7a, 8, 9a.1, 11, and 18 write durable run payloads through `scripts/larch-log.sh` with `--log-root "$IMPLEMENT_TMPDIR/larch-logs"`. Replacement batches use `write --batch <slug> --input-file <file>`; append batches use `append --batch <slug> --record-file <file>`. `scripts/larch-log-batches.sh` is the canonical slug table and defines each batch's extension, mode, and sanitizer. `larch-log.sh` redacts tmpdir paths and secrets before writing, and emits the standard `LOG_WRITTEN`, `LOG_PATH`, `BYTES`, `SHA256`, `COMMIT_SHA`, and `UNCHANGED` envelope. Diagrams are not written through a larch-log batch; they are posted only to the tracking issue via the `larch:diagrams` summary comment, with Mermaid validation happening at Step 7a compose time (`sanitize-mermaid-fragment.sh`).

**Batch mapping**:

| Step | Batch |
|------|------------|
| Step 1 (after `/design` exports the implementation plan artifact, revised when superseded by plan review) | `plan-goals-test` |
| Step 1 tail (after `/design` exports the voting tally artifact) | `plan-review-tally` |
| Step 2 (after each Q/A append) | `execution-issues` |
| Step 5 (after `review-and-fix.sh` writes `review-and-fix-summary.json`) | `code-review-tally` and `review-findings-full` |
| Step 7a tail (pre-bump log flush) | `token-report`, `timing-report`, and log-flush commit |
| Step 8+ mid-run (`ship-pr.sh` Triggers A-C via `scripts/refresh-run-logs.sh`: before each rebase force-push, before each CI-fix push, before each bump postbump push) | `token-report`, `timing-report`, and refresh commit — skipped when `--no-logs-commit` |
| Step 8 (after `ship-pr.sh` bump phase writes `BUMP_REASONING_FILE` to state) | `version-bump-reasoning` |
| Step 9a.1 (after OOS filing) | `oos-issues`, `run-statistics`, `token-report`, and `timing-report` |
| Step 11 (post-execution) | `execution-issues` |
| Step 18 (terminal summary) | manifest `status=done` |

**Summary comments** are slim projections only. Use `tracking-issue-summary.sh upsert-summary --issue "$ISSUE_NUMBER" --marker "<!-- larch:<name> v1 runid=$RUN_ID -->" --content-file <file>` for the four markers defined in `summary-comment-template.md`. Do not assemble a monolithic comment, do not fetch summary comments back into local state, and do not publish bulky reviewer or token payloads to GitHub comments.

**Compose-time sanitization**: every larch-log input file and every summary comment content file composed from session-derived content MUST apply prompt-level sanitization (secrets → `<REDACTED-TOKEN>`, internal URLs → `<INTERNAL-URL>`, PII → `<REDACTED-PII>`). `larch-log.sh` and `tracking-issue-summary.sh` provide shell-layer secrets redaction, but prompt-level sanitization is still the first-line defense for internal URLs and PII.

### Session untracked baseline

Before leaving Step 0.5, capture the session-wide untracked baseline used by
the Phantom Untracked Probe:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/snapshot-untracked.sh" --output "$IMPLEMENT_TMPDIR/untracked-baseline.z" --nul || true
```

Use `snapshot-untracked.sh`, not a raw pipeline, so a `git ls-files` failure
removes the output file instead of leaving an empty readable baseline that
would misclassify pre-existing untracked files as phantoms on later probes.

<!-- step:1 — Ensure Design Plan Exists -->
## Step 1 — Ensure Design Plan Exists

Print: `> **🔶 /implement 1: design plan**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 1 — design plan" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 1 — design plan" || true
# token-mark Step 1 — design plan
# timing-mark Step 1 — design plan
```

Determine the user's branch prefix:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check
```

Parse `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`.

### Ensure local main is fresh before branch creation

Runs only when `CURRENT_BRANCH == "main"`. Detached HEAD also reports `IS_MAIN=true` but a rebase on detached HEAD would fail; fall through to mode-specific branch creation (a new branch is created from `origin/main`). Skip for `IS_USER_BRANCH=true` (the feature-branch rebase at Step 1's end handles freshness) and the non-main / non-user-branch warning path (`create-branch.sh --branch` fetches and creates directly from `origin/main`).

Print: `🔃 1.m: design plan | update main`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/rebase-push.sh --no-push
```

When `forked_target=true`, append `--base-remote upstream --base-ref main` to the command above so freshness compares against the upstream base (defaults preserve `origin/main`). `--skip-if-pushed` is intentionally NOT used here: `main` is always on origin so that flag would always short-circuit. `SKIPPED_ALREADY_FRESH=true` keeps this call cheap when local `main` already matches `origin/main`.

When Step 0 ran with `continue_from_current=false`, its default preflight already fetched and rebased `main`, so this Step 1.m call should normally short-circuit with `SKIPPED_ALREADY_FRESH=true`. Keep the macro here for the `continue_from_current=true` path and for idempotent protection if Step 0's freshness work was already satisfied.

On non-zero exit, print `**⚠ Failed to ensure local main is fresh. Bailing to cleanup.**`, set `STALL_TRACKING=true` (parallels Rebase Checkpoint Macro M2 and Step 12d — signals Step 18 to rename the tracking issue to `[STALLED]` when Step 0.5 Branch 4 has already created one), and skip to Step 18. On success, continue.

### Quick mode (`quick_mode=true`)

Skip `/design`. Handle branch creation here, then produce an inline plan.
For the explicit `--quick` branch, first record the workflow path (the auto-simple branch records its own SIMPLE row immediately before re-entering this procedure):

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "SIMPLE" || true
```

**Branch handling** (replicated from `/design` Step 1 since `/design` is skipped):
- `IS_MAIN=true`: derive a short kebab-case name from the feature description; create via `${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --branch <USER_PREFIX>/<branch-name>`.
- `IS_USER_BRANCH=true`: verify `CURRENT_BRANCH` aligns with the feature. If unrelated, print `**⚠ Current branch '<branch-name>' may not match the requested feature. Creating a new branch from main.**` and create a new branch. Else use the existing branch.
- Otherwise: print `**⚠ Currently on branch '<branch-name>' which doesn't match the expected '<USER_PREFIX>/*' pattern. Creating a new branch from main.**` and create a new branch.

**Inline design**: research the codebase (Read / Grep / Glob), then produce a concrete plan under `## Implementation Plan`: files to modify, approach, edge cases, testing strategy (TDD where applicable; else a concrete verification — `/relevant-checks`, grep, dry-run, or manual repro), failure modes. Same content `/design` would produce, without collaborative sketches, plan review, or voting. Print: `⚡ 1: design plan — quick mode, inline plan`

Create the export directory if needed (`mkdir -p "$IMPLEMENT_TMPDIR/design-export"`), then write the inline plan to `$IMPLEMENT_TMPDIR/design-export/plan.txt` (basename exactly `plan.txt`) and set `PLAN_FILE` to that path. Also write `$IMPLEMENT_TMPDIR/design-export/voting-tally.md` containing `Quick mode — no plan review voting.` and set `PLAN_REVIEW_TALLY_FILE` to that path so the Step 1 `plan-review-tally` batch composer (and downstream PR-body composition) have a file-backed source. The Step 1 batch composer MUST call `${CLAUDE_PLUGIN_ROOT}/scripts/write-tally.sh --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --phase plan-review --mode simple --body-file "$PLAN_REVIEW_TALLY_FILE"`, which composes the JSON record and writes the `plan-review-tally` batch atomically; never write `voting-tally.md` directly to the `.json` batch.

Skip `### Normal mode` and the post-`/design` sections. Run the following Step 1 tail in order: **`### Capture branch name`** (bind `BRANCH_NAME` from branch creation above) → **`### Larch-log batches`** (write `plan-goals-test` + `plan-review-tally` batches and post the `larch:plan` summary to the tracking issue when `$ISSUE_NUMBER` is set) → **`### Coder simplicity override`** → **`### Rebase onto latest main`** → Step 2.

### Normal mode (`quick_mode=false`)

> **Continue after child returns.** When the child Skill returns, execute the NEXT step — do NOT end the turn, and do NOT write a summary, handoff, or "returning to parent" message. → shared/subskill-invocation.md#anti-halt (Branch-specific: applies only to the `/design` invocation in normal mode.)

**Manifest reuse (resumed sessions — runs first)**: before any other normal-mode sub-step, check for a reusable design manifest. This guard runs BEFORE simplicity classification and BEFORE the both-externals-down inline-plan branch so a resumed session never overwrites the prior `/design` artifact set or design classification.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/read-design-manifest.sh --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

Parse stdout without `eval`/`source`. The reuse heuristic is a two-way conjunction:
1. `MANIFEST_OK=true`.
2. `PLAN_FILE` is non-empty and points to an existing non-empty file, AND `SESSION_ID` matches the value in `$IMPLEMENT_TMPDIR/session-id`.

(Session binding is enforced by `SESSION_ID` equality alone — `TIMESTAMP` is informational only and MUST NOT gate reuse, since the session-tmpdir lifetime already bounds the manifest's validity window.)

If both are true, reuse the manifest and proceed to Step 2 with **all manifest file variables** set from the reader output — not just `PLAN_FILE`, but also `PLAN_REVIEW_TALLY_FILE`, `CONTESTED_CRITERIA_FILE`, `OOS_FILE`, `REJECTED_FINDINGS_FILE`, `ACCEPTED_PLAN_FINDINGS_FILE`, and `ARCHITECTURE_DIAGRAM_FILE` (when present). Same surface as the post-`/design` success branch below; without this, downstream steps lose plan-review tally / rejected findings / architecture diagram on a resumed run. Because `/design` did not return on this reuse path, the post-design boundary wrapper is not invoked; branch capture is handled by the shared `BRANCH_NAME` subsection below. Do not run the pre-design router or overwrite a reused classification. `run-params.json` is internal to the `/design` session and is NOT exported to `design-export/`; do not attempt to read it on the manifest-reuse path.

Before jumping to Step 2 on the manifest-reuse path, run `${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint`. Parse `STATUS` without `eval`/`source`. If `STATUS=dirty` or `STATUS=unknown`, fire `AskUserQuestion` regardless of `auto_mode` with restore / labeled stash / bail-to-STALLED options using the recovery rules below. This covers resumed sessions that skip both `/design` and the post-design boundary wrapper.

At the start of this reuse branch, record:

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "HARD" || true
```

Otherwise (no reusable manifest), continue with the normal-mode flow below (simplicity classification preamble, then the both-externals-down branch or the standard `/design` invocation).

**Simplicity classification preamble — skip condition**: classification runs only when `design_only=false` AND `hard_mode=false`; otherwise skip it entirely and continue with the normal-mode flow below. (`--design-only` is mutually exclusive with quick mode and must not auto-switch into the degraded inline-plan path. When `hard_mode=true`, set `ROUTER_CLASSIFICATION=HARD`, print `**⚡ 1: design plan — HARD workflow forced by --hard; skipping simplicity classification.**`, record `"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "HARD" || true`, and continue in the normal-mode flow — no auto-switch to quick mode.)

**Simplicity classification**: when the preamble condition holds, classify the task before invoking `/design`. Use `FEATURE_DESCRIPTION` plus a light codebase scan (Read / Grep / Glob of the obvious target files) to decide whether the work is SIMPLE or HARD. Store the result as `ROUTER_CLASSIFICATION` so the normal `/design` path can pass it via `--design-classification`; do not persist it in session-env.

**Default to SIMPLE.** A task is HARD only when running `/design` — with competing sketches, a voting panel, and a full reviewer suite — would produce meaningfully better outcomes than just implementing the obvious approach. That bar is high.

A task is HARD when at least one of these is true:
- The correct approach is genuinely uncertain: reasonable engineers would propose substantially different architectures, and the choice between them has meaningful long-term consequences.
- The work introduces a major new shared abstraction whose interface must be carefully designed (e.g., a new cross-skill workflow contract, data model, or protocol — NOT just a new helper function or script).
- A mistake would be very hard to detect or revert, or would silently corrupt data or break a non-obvious invariant.

Explicitly NOT sufficient for HARD:
- Multi-file changes (even 20+ files), when the individual edits follow a clear pattern described in the issue.
- "Architectural decisions" that the issue body or existing codebase patterns already resolve.
- Needing to add tests or follow parity rules — these are known requirements, not ambiguous design choices.
- Mechanical edits across many call sites (e.g., renaming a flag, removing a prose string from N launchers).

When in doubt, classify SIMPLE — the cost of a lighter review on a genuinely hard task is manageable; unnecessary design ceremony on a simple task is pure waste and significantly delays delivery.

When the task is SIMPLE: set `ROUTER_CLASSIFICATION=SIMPLE`, print `**⚡ 1: design plan — task classified as SIMPLE; auto-switching to quick workflow.**`, record `"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "SIMPLE" || true`, set `quick_mode=true`, and re-enter the Quick mode branch above (`### Quick mode (quick_mode=true)`). From there, handle branch creation, produce the inline plan, write `plan.txt` + `voting-tally.md`, and proceed to Step 2 exactly as ordinary quick mode does. The existing SIMPLE auto-switch is unchanged and still skips `/design` entirely.

When the task is not SIMPLE: set `ROUTER_CLASSIFICATION=HARD`, leave `quick_mode=false`, and continue with the normal-mode flow below.

**Both-externals-down inline-plan branch**: if `codex_available=false AND cursor_available=false AND design_only=false`, do NOT invoke `/design` via the Skill tool. The full `/design` pipeline expands to 4 Claude-subagent sketches + 4 Claude-subagent reviewers + judge panels — token-expensive and architecturally brittle when no external can produce independent perspectives anyway. Take the same inline-plan path as quick mode (`### Quick mode (quick_mode=true)` above) — same branch handling, same inline plan composition, same `$IMPLEMENT_TMPDIR/design-export/plan.txt` + `voting-tally.md` writes — except the breadcrumb is `⚡ 1: design plan — both-externals-down, inline plan` and the voting-tally fallback text is `Both externals unavailable — no plan review voting.` (replaces the quick-mode `Quick mode — no plan review voting.`). Print `**⚠ 1: design plan — both Codex and Cursor unavailable; skipping /design and producing inline plan in main agent.**`, then record `"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "HARD" || true`, then skip `### Normal mode` and the post-`/design` sections and run the same Step 1 tail as quick mode: **`### Capture branch name`** → **`### Larch-log batches`** (write `plan-goals-test` + `plan-review-tally` batches and post the `larch:plan` summary when `$ISSUE_NUMBER` is set) → **`### Coder simplicity override`** → **`### Rebase onto latest main`** → Step 2.

The `design_only=false` gate is load-bearing: `--design-only`'s contract is to publish design artifacts (plan, plan-review tally, diagrams, OOS) to the tracking issue as the run's deliverable. It is mutually exclusive with `--quick` precisely because quick mode produces a degraded plan with no plan-review voting. Inheriting that degradation here when externals are down would silently violate the same contract. When `codex_available=false AND cursor_available=false AND design_only=true`, do NOT skip /design — print `**⚠ 1: design plan — both Codex and Cursor unavailable but --design-only requires external-backed plan-review. Bailing to cleanup.**`, set `STALL_TRACKING=true`, and skip to Step 18.

On the design-only normal path (external-backed `/design` proceeds), record the HARD path before the Skill invocation:

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "HARD" || true
```

Otherwise (at least one of `codex_available` / `cursor_available` is `true`, OR `design_only=true` and the bail above did not fire), record `"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" workflow-path "HARD" || true`, persist the run mode for post-/design hooks, then invoke `/design` via the Skill tool. The sidecar contains exactly `true` or `false` followed by a newline:

```bash
printf '%s\n' "$design_only" > "$IMPLEMENT_TMPDIR/.design-only"
```

Canonical invocation order: `[--auto] [--subagent] [--design-classification "$ROUTER_CLASSIFICATION"] --step-prefix "1.::design plan::/implement" --branch-info "IS_MAIN=$IS_MAIN IS_USER_BRANCH=$IS_USER_BRANCH USER_PREFIX=$USER_PREFIX CURRENT_BRANCH=$CURRENT_BRANCH" --session-env $IMPLEMENT_TMPDIR/session-env.sh <FEATURE_DESCRIPTION>`. Prepend `--auto` only if `auto_mode=true`. Append `--subagent` (after `--auto`, before `--design-classification` in argv order) only if `inline_mode=false` (default); when `inline_mode=true`, omit `--subagent` so /design's heavy phase runs in /design's in-turn context (execution topology only — parent verbosity suppression unchanged). Append `--design-classification "$ROUTER_CLASSIFICATION"` only when `ROUTER_CLASSIFICATION` is non-empty; `/design` trusts the value only because this invocation also passes complete `--branch-info`.

After `/design` returns, the FIRST and MANDATORY orchestrator action is this Bash wrapper call. No orchestrator-authored prose, summary, recap, handoff, or "returning to parent" message may appear before it:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/post-design-boundary.sh \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --session-env "$IMPLEMENT_TMPDIR/session-env.sh" \
    --design-only "$design_only"
```

Wrapper contract: `skills/implement/scripts/post-design-boundary.md`. Wrapper integration harness: `skills/implement/scripts/test-post-design-boundary.sh` with sibling contract `skills/implement/scripts/test-post-design-boundary.md`.

Parse the wrapper stdout without `eval`/`source`. If it emits `MANIFEST_FAILED=true`, print `**⚠ 1: design plan — design manifest unavailable: $ERROR. Bailing to cleanup.**`, set `STALL_TRACKING=true`, and skip to Step 18. The error-message text remains `design manifest unavailable` for backward compatibility; `ERROR=<token>` distinguishes manifest-unavailable, invalid tmpdir, branch-capture failure, or another fail-closed cause for log inspection. On success, require `MANIFEST_OK=true` and `POST_DESIGN_BOUNDARY_OK=true`, set `PLAN_FILE` and all manifest file variables from the wrapped reader output, and bind `BRANCH_NAME` from the wrapper's `BRANCH=<name>` line.

> **Continue after child returns.** When `/design` returns, execute the post-design boundary wrapper + larch-log batch writes + Step 1.r rebase checkpoint + Step 2 breadcrumb in order — do NOT end the turn (neither silently nor after text output), and do NOT write a summary, handoff, or "returning to parent" message first. → shared/subskill-invocation.md#anti-halt

> **Post-/design boundary checkpoint.** After `/design` returns and its Step 5 cleanup completes, the wrapper above is the load-bearing mechanical gate and must be the first action. The wrapped reader still emits the verification breadcrumb `📥 1: design plan — manifest loaded (plan=<basename>)` as the reader-subprocess trailing line; the wrapper's combined trailing line is the imperative breadcrumb `➡️ 1: design plan — boundary gate passed; NEXT REQUIRED: …`, which is now the orchestrator-facing first mid-Step-1 continuation signal. The only orchestrator-authored output lines permitted before the Step 1.r rebase breadcrumb (`🔃 1.r: design plan | rebase`) — or the Step 2 breadcrumb (`> **🔶 /implement 2: implementation**`) when 1.r is silent-skipped because the working tree is already on tip-of-main — are the wrapper's preserved reader output, wrapper envelope, wrapper `➡️` directive, the larch-log batch writes, and the **Coder simplicity override** breadcrumb (`**⚡ 1: design plan — diff_lines < 30; coder auto-set to claude (no explicit --coder).**`) when the `diff_lines < 30` carve-out at `### Coder simplicity override + implementer waterfall` fires. Printing "design phase complete," "returning control," "handing off," or any other recap/handoff message anywhere between `/design`'s return and the 1.r/Step-2 breadcrumb is a **halt in disguise** and is a NEVER #12 violation: it makes the turn look done at a natural-feeling boundary that is in fact mid-Step-1. The `📥` breadcrumb remains internal verification; the `➡️` breadcrumb carries the continuation directive. **Hook vs. orchestrator tokens**: the PostToolUse hook passes `--hook-mode true` to `post-design-boundary.sh`, which emits `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` (not `POST_DESIGN_BOUNDARY_OK=true`) and does NOT write `.boundary-gate-passed`; the orchestrator's mandatory Bash invocation above (without `--hook-mode`) emits `POST_DESIGN_BOUNDARY_OK=true` and writes the sentinel. The Stop hook is armed (blocking) until the sentinel is written, so a halt between the PostToolUse hook firing and the orchestrator Bash call is caught and blocked. Seeing `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` in context does NOT mean the boundary is passed — the orchestrator must still invoke the Bash wrapper to produce `POST_DESIGN_BOUNDARY_OK=true` and write the sentinel. Mechanical enforcement: a PostToolUse hook on the `Skill` tool auto-runs `post-design-boundary.sh --hook-mode true` and re-injects its stdout into the next assistant turn, and a Stop hook refuses session stop while `manifest.env` is present without the `.boundary-gate-passed` / `.run-cleaned-up` sentinels (with `stop_hook_active` continuation-loop guard); the orchestrator-driven Bash invocation above remains the load-bearing gate and the hooks are additive backstops that do not change stdout grammar. → NEVER #12; shared/subskill-invocation.md#anti-halt

Immediately after the wrapper succeeds and its envelope is parsed, run `${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint` before Step 1.r. This ordering is fixed: `post-design-boundary.sh` first, parse envelope second, dirty-tree checkpoint third. Treat `STATUS=dirty` and `STATUS=unknown` as recovery-required and ask the operator even when `auto_mode=true`; if a launcher sidecar already triggered auto-discard or a recovery prompt at this logical boundary (`RECOVERY_TAKEN=true`), skip the duplicate checkpoint prompt.

### Post-plan router

At Step 1 tail, after `post-design-boundary.sh` has loaded `PLAN_FILE` (or after the manifest-reuse branch has bound `PLAN_FILE`), classify the resolved plan for downstream implementation/review routing only. This is separate from `/design`'s `design_classification` and must not overwrite `run-params.json`.

Use plan size and file count from `PLAN_FILE`: choose `POST_PLAN_WORKFLOW_PATH=SIMPLE` when the plan describes a small, obvious implementation (roughly ≤ ~100 LOC, no new abstractions, no broad refactor, no new cross-skill contract); otherwise choose `POST_PLAN_WORKFLOW_PATH=HARD`. Persist the key to `$IMPLEMENT_TMPDIR/session-env.sh` atomically: filter out any prior `POST_PLAN_WORKFLOW_PATH=` line using `grep -v '^POST_PLAN_WORKFLOW_PATH='` (anchored prefix, NOT a partial match) to a tmp file under `$IMPLEMENT_TMPDIR`, append the new `POST_PLAN_WORKFLOW_PATH=<SIMPLE|HARD>` line, and `mv` the tmp file in place. The `grep -v` pattern MUST be anchored to `^POST_PLAN_WORKFLOW_PATH=` — a looser pattern risks stripping unrelated keys. Downstream review/round logic may read this key; no existing `design_classification`, `sketch_budget`, or manifest variable is changed.

**Also persist plan and feature file paths** for use by review specialists: using the same atomic pattern, write `PLAN_FILE=$PLAN_FILE` and `FEATURE_FILE=$IMPLEMENT_TMPDIR/feature-description.txt` to `$IMPLEMENT_TMPDIR/session-env.sh` — filter out any prior `PLAN_FILE=` or `FEATURE_FILE=` lines (anchored with `^PLAN_FILE=` and `^FEATURE_FILE=`), append the new values, and `mv` the tmp file in place. This makes the paths available through `read-session-env-key.sh` at Step 5. Feature file path is the fixed conventional path `$IMPLEMENT_TMPDIR/feature-description.txt` regardless of how the plan was produced.

### post-/design legal next-actions matrix

This matrix is authoritative after the wrapper returns. It is informational prose for the orchestrator; it does not introduce a new parsed envelope key. The wrapper's imperative `➡️` line remains the load-bearing continuation directive.

| Wrapper output | `--design-only` | Permitted next-actions | Forbidden |
|---|---|---|---|
| `MANIFEST_OK=true` + `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` + ➡️ hook-injected (from PostToolUse hook context) | any | Invoke the mandatory Bash wrapper call (`post-design-boundary.sh` without `--hook-mode`) as the FIRST orchestrator action — do NOT proceed to larch-log writes or Step 1.r yet | Treating `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` as a substitute for `POST_DESIGN_BOUNDARY_OK=true`; skipping the Bash wrapper; ending the turn after seeing the hook-injected context |
| `MANIFEST_OK=true` + `POST_DESIGN_BOUNDARY_OK=true` + ➡️ default | false | Bind `BRANCH_NAME` from `BRANCH=` → write `plan-goals-test` + `plan-review-tally` larch-log batches → post the `larch:plan` summary when `$ISSUE_NUMBER` is set → Coder simplicity override (may flip `coder=claude` per the section above) → Step 1.r rebase → Step 2 entry | New orchestrator-authored prose between `/design` return and the wrapper Bash call; re-running `git-current-branch.sh`; manual repeat of the Cross-Skill Health Update procedure (the wrapper owns it); free-form recap / handoff / "design phase complete" prose anywhere between `/design` return and Step 1.r |
| `MANIFEST_OK=true` + `POST_DESIGN_BOUNDARY_OK=true` + ➡️ design-only | true | Bind `BRANCH_NAME` from `BRANCH=` → write `plan-goals-test` + `plan-review-tally` larch-log batches → post `larch:plan` and `larch:diagrams` summaries when `$ISSUE_NUMBER` is set → Step 9a.1 OOS pipeline → set `DESIGN_ONLY_DONE=true` → Step 16 → Step 18 | Same forbidden list as above; additionally: Steps 2 / 3 / 4 / 5 / 6 / 7 / 7a / 8 / 8a / 8b / 9 / 9b (per the existing design-only short-circuit) |
| `MANIFEST_FAILED=true ERROR=<token>` | any | Print `**⚠ 1: design plan — design manifest unavailable: $ERROR. Bailing to cleanup.**` → set `STALL_TRACKING=true` → skip to Step 18 | Setting `MANIFEST_PATH`; entering Step 1.r / Step 2; treating `WARN=…` lines (if any) as failure (warnings are non-fatal) |

**Always-permitted writes regardless of row**: writes under `$IMPLEMENT_TMPDIR/**`, `/relevant-checks` invocations, and reads of the wrapper's stdout for parsing. The "forbidden" column scopes to ORCHESTRATOR-AUTHORED prose between `/design` return and Step 1.r (or Step 18 on failure), not to all Bash/Write. If a downstream paragraph appears to disagree, the matrix wins. See NEVER #7; NEVER #12.

### Cross-Skill Health Update (after /design)

Health propagation is performed mechanically inside `post-design-boundary.sh`. Do not repeat the Step 0 procedure here.

### Capture branch name (`BRANCH_NAME`)

After Step 1's branch resolution (whichever mode, new or existing branch):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/git-current-branch.sh
```

Parse `BRANCH=<name>` and save as `BRANCH_NAME`. Referenced by Step 14 (`local-cleanup.sh --branch $BRANCH_NAME`) and by Steps 4 / 14 / 18 status messages. Step 1 is responsible for ensuring `BRANCH_NAME` reflects the branch where implementation will happen. On the post-`/design` path, the wrapper at the start of that section emits `BRANCH=<name>` on its envelope using the same token as `git-current-branch.sh`. Parse `BRANCH=` from the wrapper's stdout and bind it to `BRANCH_NAME`. Do NOT re-run `git-current-branch.sh` there — the wrapper has already done so with retry-and-fail-closed semantics; see `post-design-boundary.md`.

### Larch-log batches — `plan-goals-test` + `plan-review-tally`

Write two larch-log batches from file-backed design artifacts. See Step 0.5 "Larch-log Batches and Summary Comments" for the mechanism.

1. **`plan-goals-test` batch** — compose by reading `PLAN_FILE` (manifest path in normal mode, `$IMPLEMENT_TMPDIR/design-export/plan.txt` in quick mode). Treat the file's full body as the implementation plan — do NOT assume it begins with or contains a literal `## Implementation Plan` heading; `/design` writes plain plan content to `plan.txt` and any normative wrapping is provided by this batch, not the source file. Run:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/compose-plan-goals-test.sh --plan-file "$PLAN_FILE" \
     --goal-text "<one-sentence objective>" > "$IMPLEMENT_TMPDIR/plan-goals-test.md"
   ```
   The script fails closed when the plan body is absent, short, or pointer-only. Write the output with `larch-log.sh write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch plan-goals-test --input-file "$IMPLEMENT_TMPDIR/plan-goals-test.md"`.
2. **`plan-review-tally` batch** — compose a JSON object from `PLAN_REVIEW_TALLY_FILE` (manifest path in normal mode, `$IMPLEMENT_TMPDIR/design-export/voting-tally.md` in quick mode). Use fallback text only if the file is missing on a degraded quick-mode path. First build a temporary body file under `$IMPLEMENT_TMPDIR/larch-log-batches-input/`: copy the tally source into it, then if `REJECTED_FINDINGS_FILE` exists and contains `[Plan Review]` entries, append those rejected findings under a `## Rejected Plan Review Findings` sub-header. Then run `${CLAUDE_PLUGIN_ROOT}/scripts/write-tally.sh --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --phase plan-review --mode <simple|hard> --body-file <body-file>`, using `--mode simple` for quick/SIMPLE paths and `--mode hard` for normal design-backed or both-externals-down paths. The wrapper composes the JSON record and writes the `plan-review-tally` batch atomically; never write the raw markdown tally body directly to the `.json` batch.
3. If `$ISSUE_NUMBER` is set, compose `$IMPLEMENT_TMPDIR/summary-plan.md` as a slim pointer to `larch-logs/implement/$RUN_ID/plan-goals-test.md` plus the current plan-review tally status, then run `tracking-issue-summary.sh upsert-summary --issue "$ISSUE_NUMBER" --marker "<!-- larch:plan v1 runid=$RUN_ID -->" --content-file "$IMPLEMENT_TMPDIR/summary-plan.md" || true`. On non-zero exit, log `Step 1 — larch:plan upsert failed` to `Tool Failures` and continue — the plan is still committed in `larch-logs/`. If `deferred=true` or `repo_unavailable=true`, skip only the summary upsert.

If `design_only=true`:

1. If `ISSUE_NUMBER` is set, compose and post the `larch:diagrams` summary comment using Bash file operations to keep diagram content out of the orchestrator's context (same approach as Step 7a's Bash block):
   ```bash
   {
     if [ -n "${ARCHITECTURE_DIAGRAM_FILE:-}" ] && [ -f "${ARCHITECTURE_DIAGRAM_FILE:-}" ]; then
       cat "$ARCHITECTURE_DIAGRAM_FILE"
     else
       printf 'Architecture diagram not available.'
     fi
     printf '\n\n(Code Flow Diagram unavailable — --design-only run, no implementation)'
   } > "$IMPLEMENT_TMPDIR/summary-diagrams.md"
   ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary \
     --issue "$ISSUE_NUMBER" \
     --marker "<!-- larch:diagrams v1 runid=$RUN_ID -->" \
     --content-file "$IMPLEMENT_TMPDIR/summary-diagrams.md" || true
   ```
   Do NOT write a `diagrams` larch-log batch.
2. Skip the Step 1.r Rebase Checkpoint below — design-only does not modify code, so a rebase to latest main is unnecessary churn.
3. Skip Steps 2 / 3 / 4 / 5 / 6 / 7 / 7a / 8 / 8a / 8b / 9 / 9b entirely. Proceed directly to Step 9a.1 so accepted OOS observations are filed and the Step 9a.1 log batches are refreshed.

### Coder simplicity override + implementer waterfall

Runs unconditionally in both quick and normal modes (i.e. all `Proceed to Step 2` paths, including the manifest-reuse fast path) UNLESS `design_only=true` — design-only never reaches Step 2, so the override is moot.

When `coder_explicit=true`, the explicit value wins. Do not apply the `diff_lines < 30` carve-out, do not apply the Codex → Cursor → Claude waterfall, and do not modify `coder_explicit` itself.

When `coder_explicit=false` AND `design_only=false`, read `$IMPLEMENT_TMPDIR/design-export/diff-lines.txt` if it exists. The file is written by `/design` Step 2b and contains only an integer estimate of total planned diff lines. Treat an absent, empty, non-integer, or `>=30` value as "no carve-out"; this is the quick-mode and missing-design-export behavior. If the parsed integer is `<30`, set `coder=claude` and print:

`**⚡ 1: design plan — diff_lines < 30; coder auto-set to claude (no explicit --coder).**`

When the `diff_lines < 30` carve-out does not fire, route by availability:

- If `codex_available=true`, set `coder=codex`. This is the default implementer when `--coder` is omitted.
- If `codex_available=false` AND `cursor_available=true`, set `coder=cursor` and `coder_fallback_target=cursor`, print `**⚠ Codex unavailable — falling back to Cursor implementer.**`, and append `Step 1 — Codex unavailable: waterfall fallback to cursor` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`. Do NOT set `coder_fallback=true` on this path; Cursor is an external implementer, not a degraded fallback.
- If `codex_available=false` AND `cursor_available=false`, set `coder=claude` and `coder_fallback_target=claude`, print `**⚠ /implement Step 2: Codex and Cursor both unavailable. Falling back to Claude main agent for implementation — this is more expensive (~$1-6/run on Claude meter). Re-running with a healthy Codex or Cursor is preferred.**`, append `Step 1 — Codex and Cursor unavailable: waterfall fallback to claude` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`, and best-effort update the run manifest with `coder_fallback=true`.

The manifest update, when `RUN_ID` and the larch-log manifest are available, is:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh manifest \
  --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
  --skill implement \
  --run-id "$RUN_ID" \
  --field coder_fallback=true || true
```

**Legacy `--codex-available` interaction**: the deprecated `--codex-available true|false` flag is dispatcher-only and does NOT set `coder_explicit`. To suppress the `diff_lines < 30` carve-out and waterfall routing on legacy invocations, pass `--coder=codex` (or whichever implementer is desired) explicitly; the legacy knob alone leaves `coder_explicit=false` and the carve-out or waterfall may fire.

**Manifest-reuse interaction**: this override runs unconditionally on the manifest-reuse fast path even though Step 1's "Simplicity classification preamble" is skipped there. The asymmetry is intentional — the preamble's job is to flip `quick_mode` (an irreversible workflow choice), while the override's job is to choose the implementer for THIS run; running it on resume keeps implementer selection responsive to the resumed plan.

Routing consequence: the Step 2 dispatcher receives the resolved `--coder` value from this section. For `coder=claude`, the dispatcher immediately emits `STATUS=claude_fallback` + `ORCHESTRATOR_EDIT_AUTHORITY=allowed`, taking the existing main-agent code-edit path at Step 2.4. For `coder=cursor`, the dispatcher uses the existing Cursor implementer path. No new Step 2 dispatcher branch is introduced.

### Rebase onto latest main (before implementation)

Runs unconditionally in both modes UNLESS `design_only=true` (per the design-only short-circuit above, which jumps past this section). Both `Proceed to Step 2` paths lead here first.

Apply the Rebase Checkpoint Macro with `<step-prefix>=1.r` and `<short-name>=design plan`.

<!-- step:2 — Implement the Feature -->

Print: `> **🔶 /implement 2: implementation**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 2 — implementation" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 2 — implementation" || true
# token-mark Step 2 — implementation
# timing-mark Step 2 — implementation
```

<!-- step:2 entry preconditions — legal next-actions matrix -->

This matrix is authoritative for Step 2. After parsing the dispatcher's stdout in 2.1 AND completing envelope validation in 2.1.5, the orchestrator's permitted next-actions are exactly the rows below — no others. **If a downstream paragraph in 2.2 / 2.4 appears to disagree, the matrix wins.** See NEVER #10.

| Resolved `STATUS` | `ORCHESTRATOR_EDIT_AUTHORITY` | Permitted next-actions | Forbidden |
|---|---|---|---|
| `complete` | `forbidden` (required) | Set `MANIFEST_PATH=$MANIFEST`; proceed to Step 3 | Edit, Write, repo-mutating Bash against the **git working tree**; `git diff`-based reconstruction; transcript inspection for diff replay |
| `needs_qa` | `forbidden` (required) | Run Q/A loop in 2.3 (read `$QA_PENDING`, ask via `AskUserQuestion`, **write answers JSON to `$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json` — permitted**, re-invoke dispatcher with `--answers`) | Edit, Write, repo-mutating Bash against the **git working tree** unrelated to redispatch |
| `bailed` | `forbidden` (required) | Log `Step 2 — $TOOL_LABEL bailed: $REASON` to `Warnings`; bail per 2.2's REASON-set routing (Step 12d) | Edit, Write, repo-mutating Bash against the **git working tree**; do NOT attempt to "recover" by editing |
| `claude_fallback` | `allowed` (required) | Run Step 2.4 (opportunistic questions when `auto_mode=false`; main-agent Edit/Write/Bash code edits per the plan) | None additional |
| any envelope failure (validation in 2.1.5) | n/a | Synthesize orchestrator-local bail with `REASON=orchestrator-envelope-invalid` (see 2.1.5); route as Step 2 → Step 12d hard-bail | Setting `MANIFEST_PATH`; entering 2.3 / 2.4 / Step 3 |

**Always-permitted writes regardless of row**: `$IMPLEMENT_TMPDIR/**` (Q/A artifacts, larch-log input records, execution-issues), larch-log and summary publication calls in 2.5, `/relevant-checks` invocations, and reads of `TRANSCRIPT` / `SIDECAR_LOG` for warning text extraction (NOT for diff reconstruction). The "forbidden" column scopes to the **git working tree**, not to all Write/Bash.

**No mid-run scope re-litigation.** Once Step 2 begins with a plan in hand, the orchestrator does not relitigate scope, capacity, or "should I stop" via its own `AskUserQuestion`; if the plan is too large, that should have surfaced at earlier planning checkpoints (`/design` Step 1c/1d when normal mode runs, or `/design` Step 3.5). Mid-implementation, the dispatcher (or, on Claude fallback, the orchestrator) executes the plan or hits a concrete Step 12d bail condition; the orchestrator does not invent a third halting path. This rule does NOT suppress `AskUserQuestion` calls in the Codex Q/A loop below or in the Claude-fallback branch's opportunistic questions. See NEVER #7.

<!-- step:2 dispatch — coder selection -->

Regression harnesses for this dispatcher surface are `skills/implement/scripts/test-codex-implementer.sh`, `skills/implement/scripts/test-codex-implementer.md`, `skills/implement/scripts/test-cursor-implementer.sh`, and `skills/implement/scripts/test-cursor-implementer.md`.

**2.1 — First dispatch invocation**:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
cursor_healthy=$(${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_HEALTHY --default false)
implement_workflow=$( [[ "$quick_mode" == "true" ]] && echo SIMPLE || echo HARD )

${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step2-implement.sh \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --plan-file "$PLAN_FILE" \
    --feature-file "$FEATURE_FILE" \
    --auto-mode "$auto_mode" \
    --coder "$coder" \
    --cursor-healthy "$cursor_healthy" \
    --workflow "$implement_workflow"
```

**Do NOT poll or print sidecar output while dispatching.** Invoke `step2-implement.sh` as a foreground-blocking Bash call (no `run_in_background: true`). While the external implementer runs, do NOT read the sidecar log and do NOT print intermediate output to the user — polling floods the terminal with non-actionable messages. The dispatcher blocks; parse its stdout as KV after it exits.

`$PLAN_FILE` is the path written at Step 1 (`/design`'s plan, or the inline quick-mode plan). `$FEATURE_FILE` is `$IMPLEMENT_TMPDIR/feature-description.txt` (created at Step 0). Parse the dispatcher's stdout into local KV variables: `STATUS`, `TOOL`, `MANIFEST`, `QA_PENDING`, `REASON`, `TRANSCRIPT`, `SIDECAR_LOG`, `ORCHESTRATOR_EDIT_AUTHORITY`. Then run the envelope-validation block in 2.1.5 BEFORE branching on `STATUS` in 2.2. Derive:

```bash
case "$TOOL" in
    codex) TOOL_LABEL="Codex" ;;
    cursor) TOOL_LABEL="Cursor" ;;
    *) TOOL_LABEL="external implementer" ;;
esac
```

**2.1.5 — Envelope validation (fail-closed)**:

After parsing 2.1's KV envelope and BEFORE the 2.2 `STATUS` switch, validate:

1. `STATUS` is exactly one of `complete`, `needs_qa`, `bailed`, `claude_fallback`.
2. `ORCHESTRATOR_EDIT_AUTHORITY` is exactly one of `allowed` or `forbidden`, and appears **exactly once** on stdout. Zero or duplicate `ORCHESTRATOR_EDIT_AUTHORITY=` lines are illegal and trigger `orchestrator-envelope-invalid` (mirrors the `grep -c '^ORCHESTRATOR_EDIT_AUTHORITY=' == 1` invariant pinned by `test-step2-dispatch.sh` Test 11a/11b).
3. The pair is **legal**: `ORCHESTRATOR_EDIT_AUTHORITY=allowed` iff `STATUS=claude_fallback`. Any other combination is illegal.
4. Status-keyed manifest readability (mirrors the dispatcher contract in `skills/implement/scripts/step2-implement.md` stdout grammar):
   - If `STATUS=complete`: `MANIFEST` is non-empty and points to a readable file. `QA_PENDING` MUST be absent.
   - If `STATUS=needs_qa`: `QA_PENDING` is non-empty and points to a readable file, AND `MANIFEST` is non-empty and points to a readable file.
   - If `STATUS=bailed` or `STATUS=claude_fallback`: this check does not apply (no required manifest path on these branches).

If any check fails, synthesize an orchestrator-local bail: set `STATUS=bailed`, `REASON=orchestrator-envelope-invalid`, log `Step 2 — orchestrator-envelope-invalid: STATUS=<raw> AUTH=<raw> reason=<which-check-failed>` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`, set `FINAL_BAIL_REASON=orchestrator-envelope-invalid` and `STALL_TRACKING=true`, do NOT consume `MANIFEST`, do NOT enter 2.3 or Step 3, and bail to Step 12d. **`orchestrator-envelope-invalid` is an orchestrator-local synthetic reason**, not a dispatcher-emitted REASON token — the dispatcher's REASON enumeration in `references/codex-manifest-schema.md` and `step2-implement.md` does not include it.

**2.2 — Branch on `STATUS`**:

- `STATUS=complete` → set `$MANIFEST_PATH=$MANIFEST`, run the Phantom Untracked Probe with `--step 2-post-dispatch`, and proceed to Step 3. Steps 4 / 8a / 9a / 9a.1 read this manifest; the orchestrator does not run `git diff` to figure out what changed. This probe runs only on the external-implementer complete path, after the dispatcher has committed; do not run it on `STATUS=claude_fallback`.
- `STATUS=needs_qa` → run the Q/A loop in 2.3. Note: the dispatcher may have repaired a non-standard `qa-pending.json` (e.g., `items[]` → `questions[]`) before emitting this status; the Q/A loop always reads canonical `questions[]` format from `$QA_PENDING`.
- `STATUS=claude_fallback` (with `ORCHESTRATOR_EDIT_AUTHORITY=allowed`, validated mechanically in 2.1.5) → run the Claude-fallback branch in 2.4. If `ORCHESTRATOR_EDIT_AUTHORITY != allowed`, treat as envelope failure per 2.1.5 (do NOT enter 2.4).

**2.3 — Q/A loop** (when `STATUS=needs_qa`):

1. Read `$QA_PENDING` (a JSON file containing `{"questions": [{"id": "q1", "text": "..."}, ...]}`).
2. **If `auto_mode=false`**: pose the questions to the operator via `AskUserQuestion` in a single batched call (one prompt per question, preserving the `id`). **If `auto_mode=true`**: derive best-effort answers from the plan + codebase + `CLAUDE.md`. Either way, log every Q/A pair to `$IMPLEMENT_TMPDIR/execution-issues.md` under `### Q/A` per the schema in 2.5 below.
3. Compose an answers file `$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json` with shape `{"answers": [{"id": "q1", "text": "<answer>"}, ...]}` (`$RESUME_N` is the 1-indexed resume cycle counter the orchestrator tracks locally). The filename retains `codex-` for historical compatibility; the dispatcher accepts it for Cursor resumes too.
4. Re-invoke the dispatcher with the same flags as §2.1 (including `--workflow "$implement_workflow"`) plus the additional flag `--answers "$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json"`. **On every dispatcher return — including each `--answers` redispatch cycle — re-parse the KV envelope and run the §2.1.5 envelope-validation block in full BEFORE re-branching on `STATUS` per §2.2.** Q/A redispatch is not exempt from envelope validation: a malformed or AUTH-illegal envelope on a resume invocation must still fail-closed via `orchestrator-envelope-invalid` exactly as on the first dispatch. The dispatcher itself enforces the 5-cycle cap; on the 6th `--answers` invocation it returns `STATUS=bailed REASON=qa-loop-exceeded` automatically.

> **Continue to Step 3 IMMEDIATELY after re-dispatch returns.** The Q/A loop re-dispatch is not a halting point — proceed to Step 3 checks as soon as the dispatcher exits. → shared/subskill-invocation.md#step-boundary

Print one of the following based on which path landed here, evaluated **in this exact order** (first match wins — both `(coder=claude, coder_explicit=false)` cases below are disjoint by construction because earlier bullets consume their respective parse-time signals):
- When `coder=cursor` was the resolved choice but the dispatcher fell back to claude because Cursor was unhealthy or unavailable: `**⚠ Cursor unavailable — implementing with main agent.**` Also log `Step 2 — Cursor unhealthy/unavailable: fell back to claude` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`.
- When the orchestrator earlier reported Codex unavailable / unhealthy AND `coder=codex` was NOT explicitly requested (legacy / pre-`--coder` callers that mapped through `--codex-available false`): `**⚠ Codex unavailable — implementing with main agent.**`
- When `coder=claude` AND `coder_explicit=true` (explicit operator selection via `--coder=claude`): `**ℹ Implementing with main agent (coder=claude).**`
- When `coder=claude` AND `coder_explicit=false` AND `coder_fallback_target=claude`: `**⚠ Codex and Cursor unavailable — implementing with main agent.**`
- When `coder=claude` AND `coder_explicit=false` (auto-routed by Step 1's `diff_lines < 30` carve-out; reached only after the legacy / health-fallback bullets above did not match): `**ℹ Implementing with main agent (auto-routed: diff_lines < 30, no explicit --coder).**`

**Opportunistic questions** (`auto_mode=false` only): before edits, if the plan leaves genuinely ambiguous choices, batch 1-4 into a single `AskUserQuestion`. Only ask when the ambiguity cannot be resolved from the plan, codebase, or CLAUDE.md. When `auto_mode=true`, proceed with best judgment.

Implement per Step 1's plan using Edit/Write tools. Follow CLAUDE.md: read existing code before modifying; match style and patterns; avoid duplication; don't over-engineer (each abstraction justified by a concrete current need). Prefer TDD when the project has test infrastructure (failing test first, then implement to pass). For pure configuration / documentation / prompt-text edits, skip TDD but state one concrete post-change verification (the relevant-checks helper, grep, dry-run, or minimal manual repro). Address root causes; do not suppress errors. Use the same captured-check helper described in Step 3 promptly after each non-trivial logical sub-step when you need validation before Step 3 — Step 3 is the final check, not the only one.

After the implementation commit (Step 4), the orchestrator constructs an in-memory manifest equivalent (computed from `git diff --name-only $BASELINE..HEAD` and the commit message) for Steps 8a / 9a / 9a.1 to consume. `$MANIFEST_PATH` is left empty on this branch.

### 2.5 — Q/A logging + larch-log append

**MANDATORY — READ ENTIRE FILE** before composing any public summary text from Q/A: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/summary-comment-template.md`. **Do NOT load** outside Step 2 Q/A logging and Step 11 execution-issues refresh.

After each `AskUserQuestion` return (Codex Q/A loop in 2.3, Claude-fallback opportunistic in 2.4, or mid-coding ambiguity in 2.4) AND after each mid-coding ambiguity resolution (pick the interpretation most consistent with plan + existing patterns), append to `$IMPLEMENT_TMPDIR/execution-issues.md` under the `### Q/A` category header using this schema:

```markdown
- **Step 2 (<question|ambiguity>)**: <question or ambiguity description>
  **A**: <user answer OR chosen interpretation + one-sentence rationale>
```

**Sanitize the Q/A entry at compose time** (same rule as other session-derived records — secrets → `<REDACTED-TOKEN>`; internal URLs → `<INTERNAL-URL>`; PII → `<REDACTED-PII>`) because user answers may contain sensitive content and `execution-issues.md` content flows into the committed execution log.

**Progressive log append**:
1. Compose an NDJSON record with `phase="implement"`, `step="2"`, `category="Q/A"`, and a sanitized markdown `body`.
2. Append it with:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh append --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch execution-issues --record-file "$IMPLEMENT_TMPDIR/execution-issue-record.ndjson"
   ```
3. On `LOG_WRITTEN=false` with `ERROR=`, log `Step 2 — Q/A larch-log append failed: $ERROR` to `Warnings` and continue. Non-fatal.

If `RUN_ID` is unavailable for a degraded local-only path, keep the `$IMPLEMENT_TMPDIR/execution-issues.md` append; Step 11 remains the catch-all.

Material answers that change scope or approach also log here (same `Q/A` category).

> **Continue to Step 3 IMMEDIATELY.** Implementation is not the end of the run — checks, commit, review, bump, PR, CI, and merge still must run.

<!-- step:3 — Relevant Checks (first pass) -->

Print: `> **🔶 /implement 3: checks (1)**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 3 — checks first pass" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 3 — checks first pass" || true
# token-mark Step 3 — checks first pass
# timing-mark Step 3 — checks first pass
```

> **Continue after child returns.** On `RELEVANT_CHECKS_OK=true`, execute Step 4's commit (impl) breadcrumb next — the next user-facing output is either `⏩ 4: commit (impl) status=skip reason=dispatcher-committed sha=<short-sha> elapsed=<elapsed>` on the external implementer path or the Step 4 implementation-commit flow on Claude fallback. On `STATUS=fail`, first check for `FAILURE_REASON` (structural — e.g. `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `missing-check-script`, `redaction-failed`; act on the reason, no log file is produced); otherwise read `REDACTED_LOG_FILE` (checks failure — NOT raw `LOG_FILE`), diagnose, fix, and re-invoke the helper until clean BEFORE Step 4 — the failure path is in-Step-3, not a halt. In either case, do NOT end the turn, summarize, or write a handoff message.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
# > **Continue after child returns.** On checks failures read REDACTED_LOG_FILE (checks failure — NOT raw `LOG_FILE`); prose block above has full triage.
"${CLAUDE_PLUGIN_ROOT}/scripts/run-relevant-checks-captured.sh" --site step3 --tmpdir "$IMPLEMENT_TMPDIR"
```

After the helper returns clean (or after failure triage has made it clean), close Step 3 telemetry:

<!-- step:4 — First Commit (implementation) -->

Print: `> **🔶 /implement 4: commit (impl)**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 4 — commit implementation" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 4 — commit implementation" || true
# token-mark Step 4 — commit implementation
# timing-mark Step 4 — commit implementation
```

**On the external implementer path** (`$MANIFEST_PATH` is non-empty, i.e. Step 2 returned `STATUS=complete`): the dispatcher has already committed `$TOOL_LABEL`'s working-tree edits using `manifest.commit_message` (`git add -A && git commit -F …`, with `commit_message` piped through `scripts/redact-secrets.sh` first so secrets do not land in git history). There is no Claude-side diff verification — `commit_message` is consumed as-is modulo the secrets-family redaction; the canonical on-disk manifest is sanitized by the same scrubber for downstream Steps 8a / 9a / 9a.1. Skip the `git-commit.sh` invocation. Print `⏩ 4: commit (impl) status=skip reason=dispatcher-committed sha=$(git rev-parse --short HEAD) elapsed=<elapsed>`.

**On the Claude-fallback path** (Step 2 returned `STATUS=claude_fallback` AND `ORCHESTRATOR_EDIT_AUTHORITY=allowed` — the same dual predicate enforced by NEVER #10, the Step 2 entry preconditions matrix, and §2.1.5; if the AUTH key is missing, mismatched, or `forbidden`, Step 2 has already bailed via `orchestrator-envelope-invalid` and Step 4 is unreachable on this branch): stage and commit:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/git-commit.sh -m "<descriptive commit message>" <specific-files>
```

Commit message describes WHAT was implemented and WHY, not HOW.

### Rebase onto latest main (after implementation commit)

Apply the Rebase Checkpoint Macro with `<step-prefix>=4.r` and `<short-name>=commit (impl)`.

After the macro returns successfully or silently skips, run the Phantom
Untracked Probe with `--step 4.r-post-rebase`.

> **Continue to Step 5 IMMEDIATELY.** The implementation commit is not the end of the run — code review, checks (2), commit, code flow diagram, bump, and PR still must run.

<!-- step:5 — Code Review -->
## Step 5 — Code Review

If `quick_mode=false`, print: `> **🔶 /implement 5: code review**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 5 — code review" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 5 — code review" || true
# token-mark Step 5 — code review
# timing-mark Step 5 — code review
```

### Scripted review loop

**IMPORTANT: Code review must ALWAYS run.** Never skip regardless of the nature of changes — code, skills, documentation, data files, configuration — all changes require review. Step 5 now invokes `${CLAUDE_PLUGIN_ROOT}/skills/review-and-fix/scripts/review-and-fix.sh` directly for both quick and normal modes. Quick mode passes `--panel simple`; normal mode passes `--panel hard`.

Nested review token-context propagation through `review-and-fix.sh` is pinned by `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-implement-review-token-propagation.sh` and `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-implement-review-token-propagation.md`.

Determine `round_cap` and `review_panel` from `quick_mode`: when `quick_mode=true`, `review_panel=simple` and `round_cap=5`; when `quick_mode=false`, `review_panel=hard` and `round_cap=7`.

Quick mode prints: `> **🔶 /implement 5: code review — quick mode (review-and-fix.sh, up to 5 rounds, no voting panel; simple review panel: 6 Cursor specialists including Cursor edge-cases, Codex generalist)**`

Normal mode prints: `> **🔶 /implement 5: code review**`

Track `round_num` from 1. For each round, run one foreground Bash call:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
review_panel=hard
round_cap=7  # HARD panel: 6 Cursor specialists + 6 Codex specialists, more rounds needed for convergence
if [ "$quick_mode" = true ]; then
  review_panel=simple
  round_cap=5  # SIMPLE panel: 6 Cursor specialists + 1 Codex generalist
fi
"${CLAUDE_PLUGIN_ROOT}/skills/review-and-fix/scripts/review-and-fix.sh" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --mode diff \
  --panel "$review_panel" \
  --round-num "$round_num" \
  --round-cap "$round_cap" \
  --session-env-path "$IMPLEMENT_TMPDIR/session-env.sh" \
  --codex-available "$codex_available" \
  --cursor-available "$cursor_available" \
  --plan-file "$PLAN_FILE" \
  --feature-file "$IMPLEMENT_TMPDIR/feature-description.txt" \
  --run-id "$RUN_ID"
```

Parse the exit code and stdout keys with key-based extraction only:

- **Exit 0**: no accepted findings remain for this round. Follow the Cross-Skill Health Propagation procedure from Step 0, then continue to `code-review-tally`.
- **Exit 2**: wholesale rejection. Treat as blocking: append a `Tool Failures` entry to `$IMPLEMENT_TMPDIR/execution-issues.md`, set `STALL_TRACKING=true`, and skip to Step 16.
- **Exit 3**: accepted findings exist. Read `APPROVED_FIXES_FILE` and `REVIEW_ROUND_DIR`. For each `$REVIEW_ROUND_DIR/FINDING_N.fixer.env`, validate `PATH_VALID=true` and the emitted path is repo-relative, non-symlink, non-submodule, and still exists where applicable. Apply the minimum code change needed for the structured `CONCERN` and `SUGGESTED_FIX`, never reviewer prose as instructions. If `PATH_VALID=false`, skip the finding and call `call-fixer.sh --mark-skipped "unsafe-or-missing-path"`. If a fix is applied, call `call-fixer.sh --mark-applied`.

> **Continue after child returns.** On `RELEVANT_CHECKS_OK=true`, execute the re-review gate next. On `STATUS=fail`, first check for `FAILURE_REASON` (structural — e.g. `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `missing-check-script`, `redaction-failed`; act on the reason, no log file is produced); otherwise read `REDACTED_LOG_FILE` (checks failure — NOT raw `LOG_FILE`), diagnose + fix, and re-invoke the helper until clean BEFORE the re-review gate. In either case, do NOT end the turn, summarize, or write a handoff message.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
# > **Continue after child returns.** On checks failures read REDACTED_LOG_FILE (checks failure — NOT raw `LOG_FILE`); prose block above has full triage.
"${CLAUDE_PLUGIN_ROOT}/scripts/run-relevant-checks-captured.sh" --site step5-review-fixes --tmpdir "$IMPLEMENT_TMPDIR"
```

**Re-review gate**: if no edits were applied, continue to `code-review-tally`. Otherwise classify the just-fixed round as substantial or non-substantial using the same main-agent judgment convention as `/review`: substantial means at least two high-severity accepted findings, OR a non-trivial structural fix (about >=100 LOC of non-comment code), OR accepted-fix count `>= 8`. If non-substantial, log `Step 5 — review loop stopped after round $round_num because accepted findings were not substantial (accepted=<count>; reasoning=<short classification>).` to `Warnings` and continue to `code-review-tally`. If substantial and `round_num < round_cap`, increment `round_num` and invoke `review-and-fix.sh` again. If `round_num == round_cap`, print `**⚠ 5: code review hit $round_cap-round cap without converging. Proceeding.**`, log the cap to `Warnings`, and continue.

> **Continue after review.** After the review-and-fix loop exits, execute Cross-Skill Health Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order — do NOT end the turn (neither silently nor after text output), and do NOT write a summary, handoff, or "returning to parent" message first. → shared/subskill-invocation.md#anti-halt

### Larch-log batch — `code-review-tally`

After the `review-and-fix.sh` loop completes, compose the `code-review-tally` batch. Source priority:

1. Validate `$IMPLEMENT_TMPDIR/review-and-fix-summary.json`: it must be a non-symlink regular file, size ≤4 KB, `jq .` must parse, and `.schema_version == 1`. When valid, use top-level `accepted_count`, `rejected_count`, and `rounds_completed` to compose the tally header line.
2. Use `$IMPLEMENT_TMPDIR/review-round-summary.md` as the latest narrative source when it exists and is non-empty; otherwise concatenate any non-empty `$IMPLEMENT_TMPDIR/round-*/review-round-summary.md` files in round order.
3. Otherwise use fallback text `"Review-and-fix loop completed without a file-backed round summary."`.

**After the tally content**, if `$IMPLEMENT_TMPDIR/rejected-findings.md` exists and is non-empty, include its full contents under a `## Rejected Code Review Findings` sub-header in the record body. This ensures rejected findings are committed to the run log (not just printed to the terminal at Step 16). Write the complete body to a temporary file under `$IMPLEMENT_TMPDIR/larch-log-batches-input/`, then run `${CLAUDE_PLUGIN_ROOT}/scripts/write-tally.sh --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --phase code-review --mode <simple|hard> --rounds <N> --accepted <N> --rejected <N> --body-file <body-file>`. Use counts from the structured summary or footer KV when available; otherwise use zeroes. Use `--mode simple` for quick/SIMPLE paths and `--mode hard` for normal design-backed paths. The wrapper composes the JSON record and writes the `code-review-tally` batch atomically; never write the raw markdown tally body directly to the `.json` batch.

### Track Rejected Code Review Findings

`review-and-fix.sh` copies rejected in-scope findings from the latest round to `$IMPLEMENT_TMPDIR/rejected-findings.md`. If the main agent skips any accepted fixer item during Step 5, append that skipped item to the same file using this format. **Do not include OOS items** — those follow a separate pipeline (accepted OOS → Step 9a.1 GitHub issues; non-accepted OOS → `oos-issues` log batch Rejected sub-block):

```markdown
### [Code Review] <Reviewer Name>
**Finding**: <thorough description of the finding — include the specific file(s) and line(s) affected, what the reviewer identified as the issue, and what change they suggested. Must be detailed enough to serve as an actionable TODO item if later prioritized. Do NOT use a terse one-liner — a reader who has never seen the original review must be able to understand the issue and act on it.>
**Reason not implemented**: <complete justification for why this finding was not addressed — include the specific technical reasoning, any relevant context about project conventions or design decisions, and why the current code is acceptable despite the finding. Do NOT abbreviate — preserve all important details from the evaluation.>
```

### Larch-log batch — `review-findings-full`

After the `code-review-tally` batch is written above, compose the `review-findings-full` markdown sections that persist per-finding payloads (id, phase, outcome, reviewer, and verbatim prose body) for plan-review accepted, plan-review rejected, and code-review entries found under `$IMPLEMENT_TMPDIR/round-*/`. This batch carries the load-bearing miner content per issue #1402.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/compose-review-findings.sh" \
    --design-artifacts-dir "$IMPLEMENT_TMPDIR/design-export" \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --issue "${ISSUE_NUMBER:-0}" \
    --output "$IMPLEMENT_TMPDIR/review-findings-full.md"
```

Best-effort: parse `COMPOSED=true` / `FINDINGS_TOTAL=<N>` from stdout. On `FAILED=true` or non-zero exit, log `Step 5 — review-findings-full compose failed: $ERROR` to `Warnings` and continue without writing the batch. If composed, replace `review-findings-full` with `larch-log.sh write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch review-findings-full --input-file "$IMPLEMENT_TMPDIR/review-findings-full.md"`.

Comment: accepted code-review findings are now captured from `$IMPLEMENT_TMPDIR/round-*/accepted-findings.md`; rejected code-review findings are read from `$IMPLEMENT_TMPDIR/round-*/rejected-findings.md` and the parent `$IMPLEMENT_TMPDIR/rejected-findings.md` fallback.

<!-- step:6 — Relevant Checks (second pass) -->

Print: `> **🔶 /implement 6: checks (2)**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 6 — checks second pass" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 6 — checks second pass" || true
# token-mark Step 6 — checks second pass
# timing-mark Step 6 — checks second pass
```

**Post-/review boundary sentinel**: the three required post-/review actions (Cross-Skill Health Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb) are all complete once this step is reached. Write `.review-boundary-passed` immediately at Step 6 entry to release `hook-stop-fail-close.sh`'s post-/review Stop hook guard (which blocks session stop while `review-round-summary.md` exists without this sentinel — issue #1862):

```bash
touch "$IMPLEMENT_TMPDIR/.review-boundary-passed"
```

Check whether Step 5 modified files (both modes). Detection covers staged + unstaged + (current untracked − pre-/review snapshot, when the snapshot is present):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/check-review-changes.sh --baseline "$IMPLEMENT_TMPDIR/pre-review-untracked.txt"
```

Parse all three stdout keys with key-based extraction (e.g., `awk -F= '$1=="FILES_CHANGED"{print $2}'`) — all keys are always emitted on every invocation in stable order: `FILES_CHANGED` first, `UNTRACKED_BASELINE` second, `GIT_PROBE_FAILED` third. Do NOT `eval`/`source` the script's stdout. If `UNTRACKED_BASELINE=missing` (snapshot was never written or got cleaned up after a Step 5 failure), log to `Warnings` (`Step 6 — pre-/review untracked baseline missing; untracked delta not computed for this run`) and continue — `FILES_CHANGED` is still authoritative for staged + unstaged. If `GIT_PROBE_FAILED=true` (one or more git probes returned non-zero — transient git outage, missing `.git` directory, etc.), log to `Warnings` (`Step 6 — git probe failed during review-change detection; FILES_CHANGED may have missed review-induced edits`) and continue. Step 6 does NOT pass `--strict` by default: today's contract is to preserve the historical graceful-degradation behavior on the `/implement` Step 6 path. The `--strict` flag exists for callers that want to fail-closed (treat a probe failure as `FILES_CHANGED=true`); adopting it project-wide is a separate decision tracked outside this PR. Issue #1485 added the `GIT_PROBE_FAILED` key and `--strict` flag.

If `FILES_CHANGED=false`: print `⏩ 6: checks (2) status=skip reason=no-review-changes elapsed=<elapsed>` and IMMEDIATELY skip to Step 7a (Code Flow Diagram runs unconditionally) — do NOT halt after the skip breadcrumb.

Else (`FILES_CHANGED=true`):

> **Continue after child returns.** On `RELEVANT_CHECKS_OK=true`, execute Step 7's commit (review) flow next — the next user-facing output is the review-fixes commit invocation, followed by `> **🔶 /implement 7a: code flow**` when Step 7a starts. On `STATUS=fail`, first check for `FAILURE_REASON` (structural — e.g. `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `missing-check-script`, `redaction-failed`; act on the reason, no log file is produced); otherwise read `REDACTED_LOG_FILE` (checks failure — NOT raw `LOG_FILE`), diagnose + fix, and re-invoke the helper until clean BEFORE Step 7 — the re-invoke loop is in-Step-6, not a halt. In either case, do NOT end the turn, summarize, or write a handoff message.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
# > **Continue after child returns.** On checks failures read REDACTED_LOG_FILE (checks failure — NOT raw `LOG_FILE`); prose block above has full triage.
"${CLAUDE_PLUGIN_ROOT}/scripts/run-relevant-checks-captured.sh" --site step6 --tmpdir "$IMPLEMENT_TMPDIR"
```

After the helper returns clean (or after failure triage has made it clean), close Step 6 telemetry:

<!-- step:7 — Second Commit (review fixes) -->

Print: `> **🔶 /implement 7: commit (review)**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 7 — commit review fixes" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 7 — commit review fixes" || true
# token-mark Step 7 — commit review fixes
# timing-mark Step 7 — commit review fixes
```

If any files changed during review / checks (Steps 5–6):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/git-commit.sh -m "Address code review feedback" <specific-files>
```

If no files changed, skip.

### Rebase onto latest main (after review fixes commit)

Only if `FILES_CHANGED=true` from Step 6 (Step 7 created a commit). If Steps 6–7 were skipped, skip this rebase — the pre-Step-8 rebase provides the safety net.

Apply the Rebase Checkpoint Macro with `<step-prefix>=7.r` and `<short-name>=commit (review)`.

After the macro returns successfully or silently skips, run the Phantom
Untracked Probe with `--step 7.r-post-rebase`. This probe is inside the
`FILES_CHANGED=true` guard with the Step 7.r rebase; if Steps 6-7 were skipped,
do not run it.

<!-- step:7a — Code Flow Diagram -->

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 7a — code flow diagram" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 7a — code flow diagram" || true
# token-mark Step 7a — code flow diagram
# timing-mark Step 7a — code flow diagram
```

Print: `> **🔶 /implement 7a: code flow**`

Runs unconditionally after Step 7 (regardless of Steps 6-7 skip).

**MANDATORY — READ ENTIRE FILE** before writing diagram summary comments under `quick_mode=true`: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/summary-comment-template.md`. **Do NOT load** outside quick-mode paths.

If `quick_mode=true`: print `⏩ 7a: code flow status=skip reason=quick-mode elapsed=<elapsed>`, still post the `larch:diagrams` summary comment (Architecture Diagram + Code-Flow-skipped placeholder per the `Diagrams summary comment` sub-section below), then proceed to the Pre-bump log flush subsection below (which leads into the 7a.r rebase checkpoint and then Step 8).

If `quick_mode=false`: first check whether the committed diff is small and non-runtime. Compute the merge-base, then enumerate changed files relative to `origin/main`:

```bash
MERGE_BASE=$(git merge-base HEAD origin/main 2>/dev/null) || MERGE_BASE=""
if [ -n "$MERGE_BASE" ]; then
  CHANGED_FILES=$(git diff --name-only "${MERGE_BASE}..HEAD" 2>/dev/null)
else
  CHANGED_FILES=""
fi
CHANGED_COUNT=$(printf '%s\n' "$CHANGED_FILES" | grep -c . 2>/dev/null || echo 0)
```

If `MERGE_BASE` is empty, or `CHANGED_COUNT` is 0 (diff failed or branch has no commits vs main), treat this check as inconclusive and proceed with normal generation. Otherwise check whether `CHANGED_COUNT` is 1 or 2 AND every path in `CHANGED_FILES` is non-runtime: all files reside under `docs/`, are named `CHANGELOG` or `CHANGELOG.md`, or have extension `.txt` or `.tsv` (note: `.md` files outside `docs/` — including `skills/**`, `agents/**`, and `SKILL.md` — are not automatically non-runtime and do not qualify). If both conditions hold: print `⏩ 7a: code flow status=skip reason=small-non-runtime-change elapsed=<elapsed>`, still post the `larch:diagrams` summary comment (Architecture Diagram + placeholder `"(Code Flow Diagram skipped — small/non-runtime change)"` for Code Flow — see the `diagrams` sub-section below), and proceed to the Pre-bump log flush subsection below (which leads into the 7a.r rebase checkpoint and then Step 8).

Otherwise, generate a mermaid Code Flow Diagram from the actual committed implementation. Focus on **runtime behavior** — function call sequences, data flow, control flow. Do NOT duplicate the Architecture Diagram's structural view. Choose the appropriate mermaid type (`sequenceDiagram`, `flowchart`, `stateDiagram`, `graph`, etc.). Diagram contents must obey `${CLAUDE_PLUGIN_ROOT}/skills/shared/mermaid-safe-content.md`. Write the diagram to `$IMPLEMENT_TMPDIR/code-flow-diagram.candidate.md` first, including the `## Code Flow Diagram` heading and mermaid fence; validate it with `${CLAUDE_PLUGIN_ROOT}/scripts/sanitize-mermaid-fragment.sh --input "$IMPLEMENT_TMPDIR/code-flow-diagram.candidate.md" --from-md --warnings-step "7a"`, then promote it to `$IMPLEMENT_TMPDIR/code-flow-diagram.md` only on `STATUS=ok`.

On success, continue.

On generation failure (too abstract to diagram): `**⚠ 7a: code flow — generation failed, proceeding without diagram (<elapsed>)**` and log to `Warnings` with the full captured generator output via `append-tool-failure.sh` when any output exists. On sanitizer rejection or exit 2, delete the candidate, do not promote it, print `**⚠ 7a: code flow — rejected by mermaid sanitizer (REASON_TOKEN=<token>), proceeding without diagram (<elapsed>)**`, capture the sanitizer's full stdout/stderr to `$IMPLEMENT_TMPDIR/code-flow-sanitizer.failure.log`, and append that file under `### Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md` via `${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh --site "Step 7a" --tool "sanitize-mermaid-fragment.sh code-flow" --exit-code <exit-code-or-2> --category Warnings --output-file "$IMPLEMENT_TMPDIR/code-flow-sanitizer.failure.log" --redact || true`. Do not log the raw diagram content unless it is already part of the sanitizer failure output; the capture is for tool diagnostics.

### Diagrams summary comment — `larch:diagrams`

Compose the diagrams content using Bash file operations (not Read/Write tools) to keep diagram content out of the orchestrator's context. Determine `CODE_FLOW_SKIP_REASON` from the earlier Step 7a path: empty string when the diagram file was generated successfully (`$IMPLEMENT_TMPDIR/code-flow-diagram.md` exists; the file is used directly below); `"(Code Flow Diagram skipped — quick mode)"` when `quick_mode=true`; `"(Code Flow Diagram skipped — small/non-runtime change)"` when the small/non-runtime-change skip fired; `"Code flow diagram not available."` when generation failed or was rejected by the sanitizer.

```bash
CODE_FLOW_SKIP_REASON="<set per above>"
{
  if [ -n "${ARCHITECTURE_DIAGRAM_FILE:-}" ] && [ -f "${ARCHITECTURE_DIAGRAM_FILE:-}" ]; then
    cat "$ARCHITECTURE_DIAGRAM_FILE"
  else
    printf 'Architecture diagram not available.'
  fi
  printf '\n\n'
  if [ -f "$IMPLEMENT_TMPDIR/code-flow-diagram.md" ]; then
    cat "$IMPLEMENT_TMPDIR/code-flow-diagram.md"
  else
    printf '%s' "$CODE_FLOW_SKIP_REASON"
  fi
} > "$IMPLEMENT_TMPDIR/summary-diagrams.md"
```

Do NOT write a `diagrams` larch-log batch. If `$ISSUE_NUMBER` is set, post the `larch:diagrams` summary comment (best-effort):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary \
  --issue "$ISSUE_NUMBER" \
  --marker "<!-- larch:diagrams v1 runid=$RUN_ID -->" \
  --content-file "$IMPLEMENT_TMPDIR/summary-diagrams.md" || true
```

On non-zero exit, log `Step 7a — larch:diagrams upsert failed` to `Tool Failures` and continue. In quick mode, Step 7a is skipped entirely for Code Flow generation but the summary comment is still posted with the Architecture Diagram + skipped placeholder.

### Rebase onto latest main (before version bump)

Safety net before version bump. `--skip-if-pushed` short-circuits this when the branch is already on origin; Step 8b (a separate inline rebase that does NOT use `--skip-if-pushed`) ensures already-pushed branches still rebase onto fresh main right before PR creation, with Step 12 remaining the last-chance enforcement at merge time.

Apply the Rebase Checkpoint Macro with `<step-prefix>=7a.r` and `<short-name>=code flow`.

After the macro returns successfully or silently skips, run the Phantom
Untracked Probe with `--step 7a.r-post-rebase`.

> **Continue to Step 8 IMMEDIATELY.** The code flow diagram is not the end of the run — version bump, PR creation, CI monitoring, and merge still must run.

### Pre-bump log flush

Before the version bump, write the current token/timing reports to the committed log so the flush commit rides inside the PR when the branch is pushed at Step 9b. `larch-log.sh commit` does not push; the branch push carries the commit.

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 8 — version bump" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 8 — version bump" || true
# token-mark Step 8 — version bump
# timing-mark Step 8 — version bump
"${CLAUDE_PLUGIN_ROOT}/scripts/token-report.sh" --full --format json --output "$IMPLEMENT_TMPDIR/token-report-rendered.json" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-report.sh" --full --format json --output "$IMPLEMENT_TMPDIR/timing-report-rendered.json" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh" write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch token-report --input-file "$IMPLEMENT_TMPDIR/token-report-rendered.json" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh" write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch timing-report --input-file "$IMPLEMENT_TMPDIR/timing-report-rendered.json" || true
if [ "${no_logs_commit:-false}" != "true" ]; then
  "${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh" commit --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" || true
fi
```

Best-effort: failures are non-fatal, but each non-zero `token-report.sh`, `timing-report.sh`, `larch-log.sh write`, or `larch-log.sh commit` result must first be captured to `$IMPLEMENT_TMPDIR/pre-bump-log-flush-<tool>.log` and appended with `append-tool-failure.sh` under `Tool Failures` (use `Warnings` only for report rendering that is known to be documentation-only). Do not leave a bare `|| true` on these calls without the adjacent capture and append.

On each retry (CI failure, merge conflict, rebase in Steps 10/12), `scripts/refresh-run-logs.sh` (Triggers A-C in `ship-pr.sh`) re-renders and commits the `token-report` and `timing-report` batches before each push, so the merged PR carries up-to-date token/timing data.

<!-- step:8+ — Ship PR State Machine -->
## Step 8+ — Ship PR State Machine

Steps 8, 8a, 8b, 9, 10, 11, 12, 13.5, and 14 are mechanically delegated to `${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh`. Step 6 relevant checks remain documented above for prompt-side review-change handling, but the delegated state machine reruns the Step 6 helper as its first phase so resumed post-review runs have one deterministic entrypoint. Step 16, Step 17, and Step 18 remain prompt-side because they replay rejected findings, final notes, and the terminal token/timing cap.

Before invoking the script, write `$IMPLEMENT_TMPDIR/ship-pr-state.sh` with uppercase `KEY=value` records only. Required keys:

- `PHASE=checks`, `BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, `REPO`, `REPO_UNAVAILABLE`, `FORKED_TARGET`
- `HAS_BUMP=true`, `BUMP_TYPE=NONE`, `NEW_VERSION=`, `MERGE`, `DRAFT`, `DEFERRED`
- `PR_CLOSED=false`, `DONE_RENAME_APPLIED=false`, `STALL_TRACKING=false`, `STALL_STEP=`
- `BAIL_NEEDS_USER_INPUT=false`, `BAIL_REASON=`, `CI_PASSED=false`, `OOS_PENDING=false`
- `PR_NUMBER=`, `PR_URL=`, `PR_TITLE=`, `RESUME_PHASE=`, `CALLER_KIND=`
- `REBASE_COUNT=0`, `FIX_ATTEMPTS=0`, `ITERATION=0`, `TRANSIENT_RETRIES=0`, `FAILED_RUN_ID=`
- `MANIFEST_PATH`, `TOOL_LABEL`, `DESIGN_ONLY_DONE=false`, `EXPECTED_SESSION_ID`, `EXPECTED_TMPDIR_BASENAME_PREFIX`
- `NO_LOGS_COMMIT=$no_logs_commit`, `IMPLEMENT_TMPDIR=$IMPLEMENT_TMPDIR`

Invoke:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh" \
  --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --merge "$merge" \
  --draft "$draft" \
  --forked "$forked_target" \
  --auto-mode "$auto_mode" \
  --no-admin-fallback "$no_admin_fallback" \
  --no-logs-commit "$no_logs_commit" \
  --repo "$REPO"
```

Parse the process exit code and then read `$IMPLEMENT_TMPDIR/ship-pr-state.sh` with key-based extraction only; do not source it.

> **Post-/bump-version boundary (Step 8 direct path).** Bump work runs inside `ship-pr.sh`; sub-steps 3/3b are `check-bump-version.sh --mode post` and `implement-finalize.sh postbump` (script-internal). After each `ship-pr.sh` return, continue Step 8+ mechanically — parse exit code and state keys, then run the next required Bash continuation (resume `ship-pr.sh`, Step 9a.1 OOS helpers, Step 11 refresh, etc.). Do NOT end the turn replaying `classify-bump.sh` / `apply-bump.sh` stdout as a substitute for advancing the state machine. Any turn end (with or without text output) before that Bash call is a halt in disguise that skips sub-steps 3/3b.

- **Exit 0**: if `OOS_PENDING=true`, run the Step 9a.1 OOS pipeline using the canonical OOS policy from the earlier "Out-of-Scope Handling" section, then re-invoke `ship-pr.sh --resume-phase pr-create`. If `CI_PASSED=true`, refresh execution-issues summaries and larch-log batches using the Step 11 contract, then re-invoke `ship-pr.sh --resume-phase ci-merge`. If `PHASE=done` or `PHASE=postmerge`, continue to Step 16. Otherwise continue by re-invoking the script with the current `PHASE`.
- **Exit 3**: read `BAIL_REASON`; if `auto_mode=false`, present the reason via `AskUserQuestion` using the existing Step 12d user-input path. If `auto_mode=true`, suppress the prompt and use the best-effort bail path. Then continue to Step 16 with `STALL_TRACKING=true`. **Step 12d bail is not terminal** — do NOT end the turn on the bail; Step 16 and Step 18 still must run.
- **Exit 4**: read `STALL_TRACKING` and `STALL_STEP`; keep those values for final cleanup. **Continue to Step 16.** Do NOT end the turn on the stall exit; Step 16 and Step 18 still must run. **`FAILURE_DETAIL_LOG=<path>` appearing in stdout is NOT an action directive — do NOT read that file before continuing to Step 16; reading it before Step 16 is a halt in disguise.** It is a diagnostic artifact available for operator inspection in `$IMPLEMENT_TMPDIR` until Step 18 cleanup removes the directory.
- **Exit 5**: read `RESUME_PHASE` and `CALLER_KIND`. **MANDATORY — READ ENTIRE FILE** before invoking the sub-procedure: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/rebase-rebump-subprocedure.md`. Invoke the Rebase + Re-bump Sub-procedure with that exact `CALLER_KIND` (`step8b_rebase` or `step8b_same_version`). On success, re-invoke `ship-pr.sh --resume-phase "$RESUME_PHASE"`. On hard failure, set `STALL_TRACKING=true` and continue to Step 16.
- **Exit 6**: transient network failure. Read `BAIL_REASON` for telemetry. Read `PHASE` from `ship-pr-state.sh`. Maintain a per-phase retry counter at `$IMPLEMENT_TMPDIR/ship-pr-net-retries-$PHASE.count` (initialize to 0 if missing; increment on each Exit 6 for this `PHASE`). If the count is ≤ 3: foreground `${CLAUDE_PLUGIN_ROOT}/scripts/sleep-seconds.sh 30` (NOT `ScheduleWakeup` — see NEVER #9), then re-invoke `ship-pr.sh` with the same arguments plus `--resume-phase $PHASE`. On the 4th transient failure for the same phase, treat as Exit 4: set `STALL_TRACKING=true` in the state file via a key-based rewrite, and continue to Step 16. Do NOT end the turn on Exit 6; the retry is part of the same orchestrator turn.

**OOS checkpoint**: when `OOS_PENDING=true`, execute the Step 9a.1 OOS GitHub issue pipeline using the canonical OOS policy from the earlier "Out-of-Scope Handling" section. For Step 5 review OOS, prefer the `accumulated_oos_markdown_file` / `accumulated_oos_file` paths in `$IMPLEMENT_TMPDIR/review-and-fix-summary.json`; `$IMPLEMENT_TMPDIR/oos-accepted-review.md` is a compatibility mirror written from the same accumulated markdown. The script owns PR-body creation and PR creation; the prompt owns `/issue` Skill calls because they are interactive skill invocations. After the OOS pipeline completes, set `OOS_PENDING=false` in the state file and re-enter with `--resume-phase pr-create`.

The OOS cap helper contract remains `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-issue-cap.md`; apply it before any `/issue --input-file` batch emission so per-run issue count limits and excerpt behavior stay unchanged.

**Execution-issues checkpoint**: when `CI_PASSED=true`, execute the existing Step 11 execution-issues refresh from this file. After the refresh completes, set `CI_PASSED=false` in the state file and re-enter with `--resume-phase ci-merge`.

Step 11 refresh contract: convert the current `$IMPLEMENT_TMPDIR/execution-issues.md` into one or more `execution-issues` NDJSON records, append them with `larch-log.sh append`, and write the SHA-256 of the exact markdown source to `$IMPLEMENT_TMPDIR/.execution-issues-flushed.sha` only after the append succeeds. Include `source_sha256` in each record payload using the normalized body hash: strip any leading `### Category` header line and leading/trailing blank lines (matching `normalize_body_for_hash` in `implement-finalize.sh`), then sha256 the result. This normalized hash lets the safety-net's per-section dedup correctly identify duplicate sections even when whitespace differs between the Step 11 record and the safety-net re-emission. If the append fails, capture the full `larch-log.sh append` output and log it back to `execution-issues.md` with `append-tool-failure.sh` under `Tool Failures`; the teardown safety net will retry before cleanup.

The state machine writes `postbump-state.sh` for `implement-finalize.sh postbump`, writes `finalize-state.sh` for `postmerge`/`teardown`, parses postbump `STATUS=` from stdout, preserves `CALLER_KIND=step8b_rebase` for Step 8b conflicts, treats Step 10 `ACTION=merge` as a CI-passed checkpoint, and treats Step 12 `ACTION=merge` as permission to call `merge-pr.sh`. If CI failure metadata lacks a failed run id, use `${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-checks.sh` as the fallback diagnostic path before deciding whether to stall. Within `PHASE=ci-merge`, after merge succeeds ship-pr.sh delegates local cleanup (Step 14 equivalent) to `implement-finalize.sh postmerge`; after that returns, **Continue to Step 15.** (main verification, also inside postmerge). Do NOT end the turn between the merge output and the postmerge delegation.

> **Continue to Step 16 after ship-pr reaches `PHASE=done`.** Do NOT stop after PR creation, merge, local cleanup, or teardown output; Steps 16 and 18 still own prompt-side rejected-findings replay and final token/timing caps.

<!-- step:16 — Rejected Code Review Findings Report -->

Print: `> **🔶 /implement 16: rejected findings**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 16 — rejected findings" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 16 — rejected findings" || true
# token-mark Step 16 — rejected findings
# timing-mark Step 16 — rejected findings
```

Report unimplemented code review suggestions without reprinting the full findings inline. Check `$IMPLEMENT_TMPDIR/rejected-findings.md`. If non-empty, the full content was already written through the `code-review-tally` log batch.

> **Continue to Step 17.** Do NOT end the turn after printing rejected findings.

<!-- step:17 — Final Report -->

Print: `> **🔶 /implement 17: final report**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 17 — final report" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 17 — final report" || true
# token-mark Step 17 — final report
# timing-mark Step 17 — final report
```

If `DESIGN_ONLY_DONE=true`, continue to the token summary.

If `forked_target=true` and `DESIGN_ONLY_DONE` is not true: print a fork CI dry-run report with:
- `## Fork CI Dry-Run Complete` header, then `Fork PR: <PR_URL>`
- Upstream PR values: `UPSTREAM_REPO`, `FORK_OWNER`, `BRANCH`, `BASE_REF` (upstream default branch, fallback main)
- `gh pr create` command template substituting those four values
- Caveats (5 bullets): Actions must be enabled; secrets skip; `github.repository` guard skips; green on fork ≠ green upstream; `FORK_CI_NO_CHECKS=true` means no CI signal observed

If `UPSTREAM_DESIGN_ISSUE` is set, append: `You may include Closes #<UPSTREAM_DESIGN_ISSUE> in the upstream PR body when you compose it manually.` If accepted-OOS items were skipped by Step 9a.1, append them under `## Out-of-Scope Observations` as text only. **Precedence**: `DESIGN_ONLY_DONE=true` wins over fork-mode report; never print fork-CI / fork-PR language on design-only completion.

If `quick_mode=true` and `DESIGN_ONLY_DONE` is not true, continue to the token summary.

If `quick_mode=false` and `DESIGN_ONLY_DONE` is not true: print a summary noting plan review findings were written by `/design` into larch-log batches and code review findings by `review-and-fix.sh` (visible above).

Print a token summary to chat. When `LARCH_VERBOSE_TOKENS=true`, print the full per-step table; otherwise print a single grand-total line. The full breakdown is appended to the `token-report` and `timing-report` log batches at the pre-bump log flush (Step 7a tail); on each retry `scripts/refresh-run-logs.sh` (Triggers A-C in `ship-pr.sh`) re-renders and commits the batches before each push so the merged PR carries the most recent data (unless `--no-logs-commit` is set, in which case log files stay in the session tmpdir only).

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
if [ "${LARCH_VERBOSE_TOKENS:-false}" = "true" ]; then
  "${CLAUDE_PLUGIN_ROOT}/scripts/token-report.sh" --full --markdown || true
  "${CLAUDE_PLUGIN_ROOT}/scripts/timing-report.sh" --full --markdown || true
else
  "${CLAUDE_PLUGIN_ROOT}/scripts/token-report.sh" --summary || true
  "${CLAUDE_PLUGIN_ROOT}/scripts/timing-report.sh" --summary || true
fi
```

> **Continue to Step 18.** Do NOT end the turn after the final report.

<!-- step:18 — Cleanup and Final Warnings -->

Print: `> **🔶 /implement 18: cleanup**`

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 18 — cleanup" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 18 — cleanup" || true
# token-mark Step 18 — cleanup
# timing-mark Step 18 — cleanup
```

Repeat any external reviewer warnings from earlier (from `/design`, Step 5 review, or runtime-fallback flips). Examples: `**⚠ Codex not available: <reason>**`, `**⚠ Cursor review failed: <reason>**`.

If `DESIGN_ONLY_DONE=true` AND `no_issues=true`, remind: `**Note: --design-only --no-issues was set. No PR was created and no tracking issue was opened. Design artifacts are ephemeral and were removed with the session tmpdir.**` Else if `DESIGN_ONLY_DONE=true`, remind: `**Note: --design-only was set. No PR was created. The tracking issue's summary comments point to the committed plan, plan-review tally, and accepted/rejected findings; diagrams (if any) were posted to the larch:diagrams summary comment.**` Otherwise, if `draft=true`, remind: `**Note: --draft was set. Draft PR created; local branch retained. Mark the PR ready-for-review and merge manually when ready.**` Otherwise if `merge=false`, remind: `**Note: --merge was not set. PR was created but not merged. Merge manually when ready.**`

Before teardown, refresh the token report artifact (the log batches and flush commit were already written at the pre-bump log flush step):

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-report.sh" --full --format json --output "$IMPLEMENT_TMPDIR/token-report-rendered.json" || true
if [ "${forked_target:-false}" != "true" ] && [ -n "${ISSUE_NUMBER:-}" ] && [ "${repo_unavailable:-false}" != "true" ]; then
  printf 'Status: %s | PR: %s\nLogs: larch-logs/implement/%s/\n' \
    "${STALL_TRACKING:-false}" "${PR_URL:-N/A}" "$RUN_ID" \
    > "$IMPLEMENT_TMPDIR/summary-final.md"
  ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary --issue "$ISSUE_NUMBER" --marker "<!-- larch:final-summary v1 runid=$RUN_ID -->" --content-file "$IMPLEMENT_TMPDIR/summary-final.md" --repo "${REPO:-}" || true
fi
```

For Step 18's `token-report.sh` and `tracking-issue-summary.sh upsert-summary`, preserve the best-effort behavior but capture any non-zero stdout/stderr to `$IMPLEMENT_TMPDIR/step18-<tool>.failure.log` and append with `append-tool-failure.sh` before continuing.

Capture and commit the session transcript (best-effort — never fatal):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/capture-session-transcript.sh" \
  --source-file "$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" \
    --file "$IMPLEMENT_TMPDIR/session-env.sh" \
    --key LARCH_CLAUDE_SOURCE_FILE --default "")" \
  --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
  --skill implement \
  --run-id "$RUN_ID" \
  --no-logs-commit "${no_logs_commit:-false}" \
  --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md" || true
```

The transcript path was snapshotted at Step 0 via `token-claude-source.sh` and stored in `$IMPLEMENT_TMPDIR/claude-source.env`. `capture-session-transcript.sh` reads that source safely, writes the `session-transcript` batch through `larch-log.sh` (which applies `redact-tmpdir-paths.sh` and `redact-secrets.sh`), and commits unless `--no-logs-commit` is set. After the PR has merged, the post-merge sentinel written by `ship-pr.sh` makes this commit path fail closed, so Step 18 does not create or push larch-log-only commits to `main`. For every outcome, including `captured`, the wrapper records `SESSION_TRANSCRIPT_STATUS=<status>` in `Warnings` so source/write/commit skips remain visible.

Run the consolidated teardown subcommand after the prompt-side warnings/notes and token artifact refresh above. **See NEVER #13 — do NOT write or recreate `$IMPLEMENT_TMPDIR/finalize-state.sh` from prompt-side orchestrator code; on non-design-only runs the file is produced by `ship-pr.sh`'s `write_finalize_state()`, and the sanctioned `restore-finalize-state.sh` call below is the only blessed pre-teardown writer. If teardown fails with `state-file missing required key` and restore could not help (e.g. `ship-pr-state.sh` itself is absent), surface the error and stop.** Under `forked_target=true`, skip only the tracking-issue rename / summary-refresh portions by leaving `ISSUE_NUMBER` unset; still run `implement-finalize.sh teardown` so `$IMPLEMENT_TMPDIR` is cleaned up and final warnings are repeated. It performs the title-prefix terminal transition first: Branch A renames to `[STALLED]` only when `STALL_TRACKING=true` and the issue state is exactly `OPEN`; Branch B renames to `[DONE]` when `STALL_TRACKING=false`, `DONE_RENAME_APPLIED!=true`, and `$PR_NUMBER` is set OR `DESIGN_ONLY_DONE=true`; Branch C is a no-op. Finalize-time round-trip detection runs inside `scripts/implement-finalize.sh` immediately before Branch A/B renames. On stalled paths, it then best-effort stashes leftover working-tree edits with a `larch-stalled-...` label and writes `.git/larch-stalled-run.txt` so the next SessionStart/preflight can surface or clear the leftover state. Before `cleanup-tmpdir.sh` runs (and before `verify_cleanup_target`, so even a refused cleanup releases the Stop hook), teardown writes `$IMPLEMENT_TMPDIR/.run-cleaned-up`. Teardown then best-effort kills stale background processes from this session whose argv references `$IMPLEMENT_TMPDIR` (fixed-string match via `awk index()` against lexical and physical tmpdir paths; current process and its direct parent are excluded; SIGTERM + 1s wait + SIGKILL backstop; emits a warning breadcrumb if any were killed). Before tmpdir removal, it verifies the tmpdir basename prefix and `session-id` against the Step 14 state file. When both match, cleanup proceeds. When only the session-id matches (prefix mismatch), it emits a warning and still invokes cleanup — this handles prefix bugs fixed in #1563/#1572. When the session-id doesn't match (or is absent), it logs a Tool Failures entry, emits the documented refusal warning, skips `rm -rf`, and continues. It then prints the tracking-issue URL when resolvable and prints the final Step 18 breadcrumb. Mechanical SSOT: `${CLAUDE_PLUGIN_ROOT}/scripts/implement-finalize.md` § `teardown`.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
# Only when ship-pr-state.sh exists (design-only and bail paths that never enter
# Step 8+ leave it absent). Rebuild finalize-state.sh from ship-pr-state.sh before
# teardown. If restore fails, print a warning but still run teardown so the tmpdir
# and Stop-hook sentinel are cleaned up; restore already emits diagnostics on stderr.
if [ -f "$IMPLEMENT_TMPDIR/ship-pr-state.sh" ]; then
  if ! "${CLAUDE_PLUGIN_ROOT}/scripts/restore-finalize-state.sh" \
      --implement-tmpdir "$IMPLEMENT_TMPDIR"; then
    printf '%s\n' "**⚠ Step 18: restore-finalize-state.sh failed; proceeding to teardown.**" >&2
  fi
fi
"${CLAUDE_PLUGIN_ROOT}/scripts/implement-finalize.sh" teardown \
  --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

Relay the script's tracking issue URL line and Step 18 breadcrumb verbatim. Tail records document the mechanical outcome: `RENAME_BRANCH=...`, `RENAME_STATUS=...`, `ISSUE_URL=...`, `STASH_REF=...`, `SENTINEL_WRITTEN=...`, `FINALIZE_SUBCOMMAND=teardown`, `FINALIZE_WARNINGS=...`.

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
"${CLAUDE_PLUGIN_ROOT}/scripts/token-report.sh" --since-last-mark --terse > /dev/null || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-report.sh" --since-last-mark --terse > /dev/null || true
# token-step-end Step 18
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 18 — done" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 18 — done" || true
```

The closing `Step 18 — done` mark caps the `Step 18 — cleanup` window. `scripts/token-report.sh`'s `vendor_table` slices the LAST mark with `$end == null`; without the cap, vendor records logged after Step 18 in the same JSONL ledger (e.g., from a subsequent `/implement` run that falls back to the `pwd | sha256_hex` session id in `scripts/token-ledger.sh resolve_session_id()`) accrue to the prior run's `Step 18 — cleanup` bucket. The mark MUST be emitted from the orchestrator (not from `scripts/implement-finalize.sh teardown`) and only AFTER the `--since-last-mark --terse` calls above, so those calls slice the actual cleanup window rather than an empty post-`Step 18 — done` slice. The `--since-last-mark --terse` calls are redirected to `/dev/null` — their output no longer appears in chat; the full token and timing data was already written to larch-log batches earlier in Step 18. By the time this block runs, `cleanup-tmpdir.sh` (inside teardown) has already removed `$IMPLEMENT_TMPDIR/session-env.sh` and `$IMPLEMENT_TMPDIR/session-id`, so `LARCH_TOKEN_SESSION_ID` resolution falls through to the `pwd-hash` fallback and the closing mark lands in `larch-tokens-<pwd-hash>.jsonl`. That landing site is intentional and load-bearing: the cross-run leakage being capped also flows through the same `pwd-hash` fallback in subsequent runs, so the cap and the leakage land in the same physical ledger file.
