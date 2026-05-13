---
name: fix-issue
description: "Use when fixing open GitHub issues. Processes one approved issue per invocation: skips issues with open blockers, triages, classifies intent, then either delegates to /implement or follows the issue's instructions inline for research/review tasks."
argument-hint: "[--auto] [--no-admin-fallback] [--no-logs-commit] [--coder=<value>] [--inline] [--hard] [--issue <number-or-url>] [<number-or-url>]"
allowed-tools: Bash, Read, Grep, Glob, Skill
---

# Fix Issue

Process one open GitHub issue per invocation. Scans for open issues (or targets a specific one), skips any whose GitHub issue-dependencies list includes an open blocker, triages the remaining candidate against the codebase, classifies **intent** (PR-producing vs. non-PR task) and (for PR work) **complexity**, and either delegates to `/implement` or executes the issue's instructions inline. Non-PR tasks — e.g., "research topic X and summarize findings as issues", "code-review module Y and file issues for each problem" — are followed without `/implement`; any output issues are created via `/issue` and the source issue is closed with a work summary instead of a PR link.

**Single-iteration design**: Each invocation handles at most one issue, then exits. The caller (cron, `/loop`, or manual invocation) is responsible for repeated execution.

**Anti-halt continuation reminder.** After every child tool call returns — both child `Skill` tool calls (e.g., `/design`, `/review`, `/relevant-checks`, `/bump-version`, `/issue`, `/implement`) AND child Bash tool calls into the canonical `/fix-issue` script set (`issue-lifecycle.sh`, `tracking-issue-write.sh`, `round-trip-detect.sh`, `cleanup-tmpdir.sh`, `find-lock-issue.sh`, `session-setup.sh`, `write-session-env.sh`, `get-issue-details.sh`) — IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on the child's cleanup output, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. The Bash-tool-call coverage is unique to this `/fix-issue` skill. The terminal Step 6 → Step 7 → Step 8 sequence has no intervening Skill tool calls. Step 6 always invokes `issue-lifecycle.sh close` (and additionally invokes `tracking-issue-write.sh rename` on the NON_PR sub-branch 6b); Step 8 invokes `cleanup-tmpdir.sh` when a temp dir was created (otherwise it is prose-only); on the PR path Step 7 is itself a prose-only skip with no Bash call at all. The same Skill-free **close/cleanup tail** pattern recurs in Step 3's not-material closure flow (close + best-effort rename + skip-to-cleanup) and in the Step 6b → Step 7b → Step 8 NON_PR close path. Step 5b's NON_PR body is separate from this tail pattern: it may call `/issue` (covered by the Skill-tool reminder above) and run additional Bash (covered by the same Bash-tool reminder above, applied to its full scope as stated next). The enumerated script list is the always-covered minimum scope; the rule applies equally to **any** Bash tool call invoked as part of a `/fix-issue` step's primary work — including Step 5b's inline `gh` queries, shell `test` invocations, and ad-hoc Bash. The Read / Grep / Glob tools are first-class Claude Code tools, not Bash subprocesses — their returns are not directly governed by this Bash extension, but the same continuation discipline applies: do not treat a tool return inside `/fix-issue`'s step sequence as a turn boundary — continue to the next sequenced step unless this file's explicit control-flow directives (`skip to Step N`, `bail to cleanup`, etc.) tell you otherwise. The rule is strictly subordinate to any explicit non-sequential control-flow directive in THIS file (e.g., `skip to Step N`, `bail to cleanup`, `jump back`, `loop back`, `fall through`, `break out`). A normal sequential `proceed to Step N+1` instruction is the default continuation this rule reinforces, NOT an exception. Every `/relevant-checks` invocation anywhere in this file is covered by this rule. → shared/subskill-invocation.md#anti-halt — note: shared rule covers Skill tool calls only; Bash-call coverage above is /fix-issue-local.

**Flags**: Parse flags from the start of `$ARGUMENTS`.

- `--auto`: Set `auto_mode=true`. Forward bare `--auto` to `/implement` in Step 5a when set; do NOT forward when unset. Default: `auto_mode=false`. When forwarded, `/implement` runs autonomously per its own `--auto` semantics — `/design` skips its interactive checkpoints, Step 2 opportunistic questions are suppressed, and Step 12 merge-conflict resolution uses best-effort instead of `AskUserQuestion`. `/fix-issue` itself does not currently issue interactive prompts in its own steps; the flag is purely a pass-through. Independent of all other flags.
- `--no-admin-fallback`: Set `no_admin_fallback=true`. Forward `--no-admin-fallback` to `/implement` in Step 5a. Default: `no_admin_fallback=false`. When `true`, the delegated `/implement` run instructs `merge-pr.sh` to skip the default `--admin`-first attempt once the admin-eligible gate (CI good + branch fresh) is reached, try only a plain squash merge, emit `MERGE_RESULT=policy_denied` if that plain merge fails, and bail to Step 12d with a documented reason. See `skills/implement/SKILL.md` `--no-admin-fallback` for the full semantics.
- `--no-logs-commit`: Set `no_logs_commit=true`. Forward bare `--no-logs-commit` to `/implement` in Step 5a when set; do NOT forward when unset. Default: `no_logs_commit=false`. When forwarded, `/implement` skips the `larch-log.sh commit` calls that flush log files into git. See `skills/implement/SKILL.md` `--no-logs-commit` for the full semantics. Independent of all other flags.
- `--coder=<value>`: Set `coder=<value>`. Forward `--coder=$coder` to `/implement` in Step 5a exactly as provided, with no validation or interpretation by `/fix-issue`. Only the `--coder=<value>` form (single token, `=`-separated) is recognized — the space-separated `--coder <value>` form is NOT supported, so a positional issue argument like `/fix-issue --coder codex 42` would treat `codex` as the issue identifier; pass `--coder=codex 42` instead. Default: empty (flag absent, or `--coder=` with an empty value → not forwarded). `/implement`'s own `--coder` flag validates the value (`claude` / `codex` / `cursor` / `gemini` accepted).
- `--inline`: Set `inline_mode=true`. Forward bare `--inline` to `/implement` in Step 5a **only when `hard_mode=true`**; do NOT forward when unset or when `hard_mode=false`. Default: `inline_mode=false`. Per `skills/implement/SKILL.md` `--inline`, the flag controls whether `/design`'s heavy phase runs in an isolated subagent (`--inline` absent, default) or in `/design`'s in-turn context (`--inline` present). When `--hard` is not set, `/implement` decides its own workflow (it may auto-choose SIMPLE, skipping `/design` entirely), so forwarding `--inline` would be a no-op and is omitted. **After parsing all flags**: if `inline_mode=true` AND `hard_mode=false`, print `**ℹ '--inline' requires '--hard' to take effect — '/design' only runs when '--hard' is set. Either add '--hard' to force the full pipeline, or omit '--inline'.**` and continue (do not abort). Independent of all other flags.
- `--hard`: Set `hard_mode=true`. Default: `hard_mode=false`. Forwards `--hard` to `/implement` in Step 5a, which forces `/implement` to use the HARD workflow (full `/design` + 11-reviewer `/review` panel, skipping its own simplicity auto-classification). When unset, no HARD/SIMPLE control flag is forwarded to `/implement` — it decides the workflow via its own simplicity classification. Has no effect on the `INTENT=NON_PR` path. When both `--hard` and `--inline` are set, `--inline` is forwarded alongside `--hard`. Independent of all other flags.
- `--quick`: **Removed** — recognized for backward compatibility. SIMPLE is now the default; `--quick` is no longer needed to select it. When this flag is encountered, print: `**ℹ '--quick' is no longer needed; SIMPLE is now the default workflow. Use '--hard' to force the full /design + /review pipeline.**` Strip `--quick` from `$ARGUMENTS` before further parsing so it does not corrupt the issue-number or feature-description token.
- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).
- `--issue <number-or-url>`: **Deprecated** — recognized for backward compatibility. Prefer passing the issue number or URL as a positional argument (e.g., `/fix-issue 42`). When this flag is encountered, print: `**ℹ '--issue' is deprecated; pass the issue number or URL as a positional argument instead (e.g., /fix-issue 42).**`

## Mindset

Before processing each invocation, hold these four questions.

**Is the issue still real?** Codebases move. A two-week-old bug may already be fixed; a "refactor X" request may reference deleted code. Triage (Step 3) is the cheap first-line filter — closing a stale issue with a research-summary comment is always cheaper than drafting a no-op PR.

**What shape of output does the issue want back?** A code change (merged PR) vs. new GitHub issues or a written summary (NON_PR). Classification (Step 4) is a low-variance binary call; most issues are unambiguous. Default to `PR` **only when the issue is genuinely ambiguous** — a mis-classified `NON_PR` may sometimes surface during `/implement`'s `/review` phase (which reviews code changes, not the shape-of-work contract), in which case the operator may need to stop the run. When the issue text explicitly forbids a PR or mandates research/issues as the deliverable, pick `NON_PR` regardless of the default — overriding the stated deliverable is not recoverable downstream. A mis-classified `PR` (picking `NON_PR` for a genuine code-change request) silently skips real work.

**How fragile is the change?** When the operator passes `--hard` to `/fix-issue`, Step 5a forwards `--hard` to `/implement`, which forces the full `/design` + `/review` pipeline. Otherwise, `/implement` decides the workflow via its own simplicity classification — defaulting to SIMPLE (reduced review loop) unless the task appears to benefit from the full design process.

**Where does a crash leave the issue?** `IN PROGRESS` is a lock, not a status. Once Step 0 reports `LOCK_ACQUIRED=true`, any later crash leaves `IN PROGRESS` as the last comment AND the title prefixed with `[IN PROGRESS]` until a human clears them; a crash mid-Step-0 (when GO was present: after `GO` is deleted but before `IN PROGRESS` posts) can leave the issue with neither sentinel. Consult Known Limitations for each recovery path before deviating from the step sequence.

## Progress Reporting

Follow shared/progress-reporting.md rules.

**MANDATORY at session start**: Read `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/step-name-registry.tsv` to get the Step Name Registry (step number → short name mapping for progress breadcrumbs).

**MANDATORY at session start — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/shared/orchestrator-never.md`. Contains cross-skill NEVER rules that apply to this skill in addition to the skill-specific Anti-patterns below.

## Anti-patterns

Each rule states **Why** (the specific consequence of breaking the rule) and **How to apply** (where the invariant is load-bearing). Rules marked **CI-backed: yes** are mechanically enforced by `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` via an `awk` extraction over the `### 5a` block (under Step 5 — Execute); the remaining rules are editorial invariants that depend on the SKILL.md text being unambiguous.

1. **NEVER run Step 1+ on an unlocked issue.** **Why**: the `IN PROGRESS` lock acquired at Step 0 is how concurrent runners avoid stepping on each other — `find-lock-issue.sh` skips candidates whose last comment is `IN PROGRESS`, so posting `IN PROGRESS` installs the lock at the comment-stream tail (same tail semantics the find filter reads) AND prepends `[IN PROGRESS]` to the title so the visual lifecycle reflects the active run immediately. Duplicate detection is best-effort, not fully atomic — see Known Limitations "Single-runner assumption". Stepping past Step 0 unlocked races every other `/fix-issue` invocation on the same repo. **How to apply**: treat Step 0 as structural; do not re-order the step sequence or skip it under any flag. **CI-backed**: no (editorial invariant).

2. **NEVER drop the `--issue $ISSUE_NUMBER` forward from the Step 5a `/implement` invocation.** **Why**: `--issue $ISSUE_NUMBER` causes `/implement` Step 0.5 Branch 2 to adopt the already-locked tracking issue rather than creating a duplicate via Branch 4. Dropping the forward splits tracking onto two different issues, breaks the `Closes #<N>` PR-body recovery on resumed runs, and leaves the `/fix-issue`-side issue locked under `IN PROGRESS` with no auto-close on merge. **How to apply**: keep `--issue $ISSUE_NUMBER` in the Step 5a `/implement` invocation. **CI-backed**: yes — assertion (a1) in `test-fix-issue-bail-detection.sh`.

3. **NEVER remove the `IMPLEMENT_BAIL_REASON=adopted-issue-closed` literal or its accompanying `/implement bailed: issue #` warning-prefix literal from Step 5a.** **Why**: when `/implement` adopts a tracking issue that was closed externally between lock and execution, it emits the bail token on stdout; Step 5a's branch scans captured output for that exact literal. Dropping either literal from SKILL.md routes Step 5a to the generic-failure branch ("remains locked with IN PROGRESS") instead of the adopted-issue-closed branch that reports the specific externally-closed condition. **How to apply**: preserve both literal strings verbatim inside the `### 5a` block. **CI-backed**: yes — assertions (b) and (c).

4. **NEVER paraphrase the Step 5a adopted-issue-closed directive ``Do NOT call `issue-lifecycle.sh close` ``.** **Why**: when the adopted issue is already closed, a second `issue-lifecycle.sh close` would double-post a DONE comment on top of the externally-written closing comment and run the PR-backfill with an empty `PR_URL` (since `/implement` bailed before producing a PR) — visible doubled noise on the closed issue. The directive is phrased with the specific script name, not a bare "Do NOT call" fragment, because the harness's `awk` window also includes Step 5b (whose "Do NOT call `/implement`" sentence would otherwise mask the deletion). **How to apply**: preserve the full phrase verbatim; if `issue-lifecycle.sh` is ever renamed, update the harness in the same PR. **CI-backed**: yes — assertion (d).

5. **NEVER implement fixes inline at Step 5a using Edit/Write/Bash file-modification tools instead of delegating to `/implement` via the Skill tool.** **Why**: implementing inline bypasses `/implement`'s full lifecycle — branch creation, commit, CI, review, and merge — and leaves changes uncommitted in the working tree with no PR and no tracking-issue adoption (`--issue $ISSUE_NUMBER` is never forwarded). The observed failure produced uncommitted working-tree edits and a premature Step 6 close (no `PR_URL`) because the orchestrator classified the task as "simple enough to do inline" and never invoked `/implement`. `COMPLEXITY=SIMPLE` controls the workflow *inside* `/implement` (whether `/design` and the full reviewer panel run) — it is **not** permission to bypass `/implement` entirely; implementing directly also skips the version bump, larch-log tracking, and branch cleanup that `/implement` owns. **How to apply**: on `INTENT=PR`, Step 5a has exactly one action — invoke `/implement` via the Skill tool with the prescribed flags. `COMPLEXITY=SIMPLE` is a flag forwarded to `/implement`; it does not authorize direct editing regardless of how simple the change appears. Read/Grep/Glob are permitted for composing the feature description; Edit/Write/Bash modifications to source files are not. If the change genuinely does not warrant a PR, re-classify as `NON_PR` and follow Step 5b instead — but do not implement and skip delegation. **CI-backed**: yes — assertion (f) in `test-fix-issue-bail-detection.sh`.

6. **NEVER allow the NON_PR path (Step 5b) to modify working-tree files.** **Why**: `NON_PR` tasks are defined by producing GitHub issues, research summaries, or comment output rather than code changes. Writing to the working tree on this path opens a cascade of unanswered questions: what to commit, what branch to use, whether to push, whether to create a PR — none of which the NON_PR workflow addresses. The invariant is editorial (the runtime does not block edits) and depends on the SKILL.md text making the rule unambiguous. **How to apply**: keep the "Do NOT call `/implement`. Do NOT modify files in the working tree" sentence inside Step 5b (in SKILL.md, not only in the reference). `--input-file` markdown for `/issue` batch mode lives under `$FIX_ISSUE_TMPDIR` per `skills/fix-issue/references/non-pr-execution.md`. **CI-backed**: no (editorial invariant).

7. **NEVER auto-pick umbrellas in the no-arg find-lock-issue scan.** **Why**: the umbrella-PR design dialectic (DECISION_1, voted 2-1 ANTI_THESIS) chose explicit-target-only umbrella handling. Folding umbrella handling into the bulk sweep multiplies decision-surface complexity (umbrella resolution is a distinct state machine with non-GO locking, child-pick semantics, and finalization paths) and increases operator surprise (umbrellas can be passive long-lived planning trackers). **How to apply**: `umbrella-handler.sh` is invoked ONLY in the explicit-issue path of `find-lock-issue.sh`. Operators who want umbrella-tracked work to drain must explicitly pass the umbrella number (e.g., `/fix-issue <umbrella#>` once per dispatch cycle). **CI-backed**: yes — `test-find-lock-issue.sh` carries an `auto-pick-skips-umbrella` regression fixture.

8. **NEVER improvise ScheduleWakeup outside skill-script direction.** See `${CLAUDE_PLUGIN_ROOT}/skills/shared/orchestrator-never.md` (loaded via MANDATORY above). **CI-backed**: yes — `scripts/test-anti-improvised-wakeup.sh` pins the literal in the shared file.

## Step 0 — Find and Lock

```bash
${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/find-lock-issue.sh ["$ISSUE_ARG"]
```

Only include `"$ISSUE_ARG"` as a positional argument if `ISSUE_ARG` is non-empty (the user provided an issue number/URL via positional argument or the deprecated `--issue` flag).

The script combines four operations in sequence: (1) eligibility scan or explicit-issue verification, (2) local dirty-tree probe by delegating to `${CLAUDE_PLUGIN_ROOT}/scripts/check-clean-tree.sh --fail-closed`, (3) comment-lock acquisition by delegating to `issue-lifecycle.sh comment --lock` (if last comment is `GO`: deletes GO, posts `IN PROGRESS`, post-checks for duplicate `IN PROGRESS` races) or `issue-lifecycle.sh comment --lock-no-go` (if GO is absent: posts `IN PROGRESS`, post-checks for races — no GO deletion), (4) best-effort title rename to `[IN PROGRESS] <title>` by delegating to `tracking-issue-write.sh rename --state in-progress`. The dirty-tree probe runs inside `find-lock-issue.sh` immediately before lock acquisition, and does NOT call `preflight.sh` (no fetch, no rebase, no tmpdir setup, no `larch-stalled-run.txt` mutation). It is intentionally fail-closed on `git status` failure; `preflight.sh` also calls the same helper with `--fail-closed` (wrapped in `|| true` for `set -e` compatibility), so both callers share fail-closed semantics. The comment lock is the **correctness invariant**; the title rename is purely a visual lifecycle marker. A rename failure does NOT undo the lock — `find-lock-issue.sh` still exits 0 with `LOCK_ACQUIRED=true RENAMED=false`. `/implement` Step 0.5 Branch 2's idempotent rename serves as the safety net (re-attempts on the next run-segment).

Candidates are required to be open, not locked by a prior `IN PROGRESS` comment, not carry a managed lifecycle title prefix (`[IN PROGRESS]` / `[DONE]` / `[STALLED]`), not match the `[... Report]` title pattern, and **have no currently-open blocking dependencies** from either of two sources: (1) GitHub's native issue-dependencies feature, queried via `repos/{owner}/{repo}/issues/{N}/dependencies/blocked_by`, and (2) prose-stated dependencies in the issue body and every comment body, matched against the conservative case-insensitive keyword set `Depends on #N`, `Blocked by #N`, `Blocked on #N`, `Requires #N`, `Needs #N` (each keyword followed by whitespace + `#<digits>`; emphasis wrappers like `**#150**` are tolerated, link-target forms like `[#150](url)` and cross-repo `owner/repo#N` are deliberately NOT matched). A `GO` comment is no longer required; when present it is removed at lock time to keep the sentinel semantics for future runs. Auto-pick also skips archival research/investigation titles (<code>research </code>, <code>[research] </code>, <code>investigate </code>, <code>[investigate] </code>, <code>[research report] </code> after leading-whitespace trim + lowercase); explicit-target mode is unaffected by the archival filter. An issue whose listed blockers are all closed is eligible; an issue with even one open blocker (from either source) is skipped in auto-pick mode and reported as ineligible in explicit positional-target mode. **Auto-pick selection order**: candidates are evaluated with issues whose title matches the whole word `urgent` (case-insensitive regex bounded by an explicit non-word lookaround that treats `-` as word-internal, anywhere in the title) FIRST; within each tier (Urgent vs. non-Urgent) ordering falls back to oldest-first by issue number. The match deliberately rejects substrings inside other words — `non-urgent`, `insurgent`, and `urgently` do NOT count as Urgent — to avoid the false positive a plain substring match would create on titles that mean the opposite of urgent (or use the letters incidentally). The Urgent preference is a soft signal — it only re-orders evaluation; a non-Urgent eligible issue is still picked when no Urgent eligible issue exists. The preference applies only to auto-pick (no positional argument); explicit-target mode picks exactly the issue named regardless of its title. If either dependency check fails at any boundary (API unavailability, parser error, transient `gh` failure), it degrades silently to "no blockers known from that source" so API availability never hard-blocks the automation. Prose parsing is implemented by `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/parse-prose-blockers.sh`, guarded by the offline regression harness `test-parse-prose-blockers.sh` (run via `make lint`).

**Umbrella-issue exception** (explicit-target path only — auto-pick never selects umbrellas, per the umbrella-PR design dialectic's DECISION_1): when the explicit issue is detected as an umbrella (two independent signals — either is sufficient: (1) a leading `[UMBRELLA]` bracket-block in the title per #1612, OR (2) after stripping zero or more leading bracket-blocks of the form `[...]` and/or `(...)` per #819, the remainder begins with <code>Umbrella: </code> or <code>Umbrella — </code>; body is NOT consulted post-#846), the umbrella's existence serves as the approval signal and the chosen child is dispatched without a `GO` requirement. Per #819 DECISION_1 (voted, 2-1), umbrella detection runs BEFORE the managed-prefix early-reject in the explicit-target path so umbrella titles carrying a managed lifecycle prefix (e.g. `[IN PROGRESS] [UMBRELLA] foo`, `[DONE] Umbrella: foo`, `[STALLED] Umbrella: foo` — typically from a prior crashed `/fix-issue` run) remain explicitly targetable. Auto-pick is intentionally NOT mirrored: auto-pick excludes umbrellas regardless of order. The umbrella's own blocker check still applies — a blocked umbrella exits 2. Children selected by `umbrella-handler.sh pick-child` inherit approval from the umbrella's existence (no per-child GO required). Eligibility for a chosen child = open + no managed lifecycle prefix + last comment ≠ `IN PROGRESS` + no open native/prose blockers. See `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/umbrella-handler.md` for the detection / child-enumeration / pick-child contracts and `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/finalize-umbrella.md` for the finalization (rename → comment → close) contract used by the Step 0 exit-4 path and the Step 3 / 5a / 6 finalize hooks.

`find-lock-issue.sh` resolves the repo identity itself via `${CLAUDE_PLUGIN_ROOT}/scripts/resolve-repo.sh` (which prefers `gh repo view` then falls back to `scripts/github-remote-repo.sh` / `git remote`) and does not depend on any session-setup-derived state — making this step safe to run before Step 1 setup. See `skills/fix-issue/scripts/find-lock-issue.md` for the full stdout contract (`ELIGIBLE` / `ISSUE_NUMBER` / `ISSUE_TITLE` / `LOCK_ACQUIRED` / `RENAMED` / `ERROR`) and exit code semantics.

Handle exit codes:

- **Exit 0**: Parse `ISSUE_NUMBER`, `ISSUE_TITLE`, `LOCK_ACQUIRED=true`, `RENAMED`, plus the umbrella-only keys (`IS_UMBRELLA`, `UMBRELLA_NUMBER`, `UMBRELLA_TITLE`, `UMBRELLA_ACTION`) when present. **Hold `$UMBRELLA_NUMBER` as a session variable across Steps 1-7** so Steps 3, 5a, and 6 can run the umbrella-finalization hook (FINDING_1).
  - **Non-umbrella path** (`IS_UMBRELLA` absent or empty): If `RENAMED=true`, print `✅ 0: find & lock — found and locked #$ISSUE_NUMBER: $ISSUE_TITLE, titled [IN PROGRESS] (<elapsed>)`. If `RENAMED=false`, the title rename failed best-effort — print `**⚠ 0: find & lock — found and locked #$ISSUE_NUMBER: $ISSUE_TITLE; title rename failed, /implement Branch 2 will retry. (<elapsed>)**`. Continue to Step 1.
  - **Umbrella-dispatched path** (`IS_UMBRELLA=true UMBRELLA_ACTION=dispatched`): If `RENAMED=true`, print `✅ 0: find & lock — found and locked child #$ISSUE_NUMBER of umbrella #$UMBRELLA_NUMBER: $ISSUE_TITLE, titled [IN PROGRESS] (<elapsed>)`. If `RENAMED=false`, print `**⚠ 0: find & lock — found and locked child #$ISSUE_NUMBER of umbrella #$UMBRELLA_NUMBER: $ISSUE_TITLE; title rename failed, /implement Branch 2 will retry. (<elapsed>)**`. The literal substring `found and locked` is preserved in both sub-cases so callers recognize the success path with a single sentinel — see FINDING_2 from the umbrella-PR code-review panel. Continue to Step 1 — `$ISSUE_NUMBER` refers to the chosen child; downstream `/implement` adopts the CHILD via `--issue $ISSUE_NUMBER`.
- **Exit 1**: Print `✅ 0: find & lock — no eligible issues found (<elapsed>)`. Skip to Step 8. **Note**: `FIX_ISSUE_TMPDIR` is unset on this path; Step 8's cleanup guard handles the no-tmpdir case.
- **Exit 2**: Parse `ERROR` from stdout. Print `**⚠ 0: find & lock — error: $ERROR (<elapsed>)**`. Skip to Step 8. Dirty-tree pre-lock abort is one exit-2 sub-case: operator action is commit or stash local changes, then re-run; no manual unlock is needed because no GitHub state was touched. This differs from a narrow post-lock TOCTOU dirty tree that Step 1 preflight catches after lock acquisition; that path still follows the Stale-IN-PROGRESS recovery guidance below. **Note**: `FIX_ISSUE_TMPDIR` is unset on this path; Step 8's cleanup guard handles the no-tmpdir case.
- **Exit 3**: Eligibility passed but lock acquisition failed (concurrent runner won the race, or `gh` API failed mid-sequence; for umbrella-dispatched paths, the failure is on the chosen child and the `ERROR` carries umbrella context — `Failed to lock chosen child #C of umbrella #U: <reason>`). Parse `ISSUE_NUMBER` and `ERROR`. Print `**⚠ 0: find & lock — lock failed for #$ISSUE_NUMBER: $ERROR. Another run may have claimed this issue, or the IN PROGRESS comment stream may have been partially mutated — see Known Limitations "Stale IN PROGRESS lock" for recovery before re-running. (<elapsed>)**`. Skip to Step 8. The candidate may NOT be cleanly recoverable: when GO was present, `issue-lifecycle.sh comment --lock` deletes GO BEFORE posting `IN PROGRESS`, so a `gh issue comment` failure between those two writes leaves the issue with no comment sentinel; a duplicate-`IN PROGRESS` post-check failure leaves both `IN PROGRESS` comments present. Both states require manual recovery per Known Limitations "Stale IN PROGRESS lock".
- **Exit 4** (umbrella complete — all parsed children CLOSED): parse `UMBRELLA_NUMBER` and `UMBRELLA_TITLE`. Print `> **🔶 0: find & lock — umbrella #$UMBRELLA_NUMBER all-closed; finalizing**`. Invoke:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/finalize-umbrella.sh finalize --issue $UMBRELLA_NUMBER
  ```
  Parse `FINALIZED`, `ALREADY_FINALIZED`, `RENAMED`, `CLOSED`, `ERROR`. On `FINALIZED=true`: print `✅ 0: find & lock — umbrella #$UMBRELLA_NUMBER finalized ([DONE] + closed) (<elapsed>)`. On `ALREADY_FINALIZED=true`: print `✅ 0: find & lock — umbrella #$UMBRELLA_NUMBER already finalized (<elapsed>)`. On `FINALIZED=false` non-idempotent failure: print `**⚠ 0: find & lock — umbrella #$UMBRELLA_NUMBER finalize failed: $ERROR (<elapsed>)**`. In all three sub-cases, skip to Step 8.
- **Exit 5** (umbrella detected but no eligible child): parse `UMBRELLA_NUMBER` and `ERROR`. Print `**⚠ 0: find & lock — umbrella #$UMBRELLA_NUMBER has no eligible child: $ERROR (<elapsed>)**`. Skip to Step 8. The umbrella stays open; the next `/fix-issue` invocation re-evaluates its children.

## Step 1 — Setup

Runs only after Step 0 successfully locked the issue. A failure here leaves the issue locked with `IN PROGRESS` (and the title prefixed `[IN PROGRESS]`) — same recovery semantics as any mid-run crash (manual `IN PROGRESS` comment clearance + title-prefix strip).

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-fix-issue --skip-branch-check
```

If `REPO_UNAVAILABLE=true`, print `**⚠ Could not determine repository. GitHub issue access requires a valid repo. Aborting.**` and skip to Step 8.

Write session-env for forwarding to `/implement`:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/write-session-env.sh --output "$FIX_ISSUE_TMPDIR/session-env.sh" \
  --repo "$REPO" \
  --repo-unavailable "$REPO_UNAVAILABLE" \
  --codex-healthy true --cursor-healthy true --gemini-healthy true
```

## Step 2 — Read Issue Details

```bash
${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/get-issue-details.sh \
  --issue $ISSUE_NUMBER --output "$FIX_ISSUE_TMPDIR/issue-details.txt"
```

Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/get-issue-details.md`.

Read `$FIX_ISSUE_TMPDIR/issue-details.txt` to get the full issue content.

## Step 3 — Triage

Print `> **🔶 3: triage**`

**MANDATORY — load digest first**: `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/references/triage-classification.digest.md` covers the common triage and classification path. Load full `${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/references/triage-classification.md` only when composing the not-material closure explanation (need detailed rationale) or when genuinely uncertain about a classification edge case. Contains the triage check list, the not-material closure flow detail (rationale composition with research summary), and the Step 4 classification detail that shares the same file. **Do NOT load** outside Steps 3 and 4 — this file is not consumed anywhere else. **Do NOT load** on any path that has already branched to Step 8 (Steps 3 and 4 do not run there). Concrete examples: Step 0 returned exit 1 (no candidate), exit 2 (error / ineligible / pre-lock dirty-tree abort), or exit 3 (eligible but lock failed after eligibility); Step 1 setup aborted with `REPO_UNAVAILABLE=true`.

Decide whether the issue is still material against the codebase (see the reference for the check list and the triage-targets rule for investigation/review-only issues).

**Round-trip detection for terminal renames**: before any Step 3 / Step 6 terminal `tracking-issue-write.sh rename --state done`, run `${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh` and pass its `ROUND_TRIP=true|false` value as `--round-trip "$ROUND_TRIP"`. Use `$FIX_ISSUE_TMPDIR/issue-details.txt` from Step 2 as the canonical issue text source and pass `$ISSUE_TITLE` via `--text-string` only because it is short. For PR-path Step 6a, also fetch PR text into a temp file with `gh pr view "$PR_NUMBER" --repo "$REPO" --json title,body --jq '(.title // "") + "\n" + (.body // "")'` and include that as an additional `--text-file`. Bodies and PR descriptions MUST be file-backed, not argv-backed. Best-effort: on any `gh` or detector failure, log a warning under `Tool Failures`, set `ROUND_TRIP=false`, and still run the rename. See `${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.md` and `${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.md`.

**If the issue is no longer material** (already fixed, invalid, or no longer relevant): compose a detailed explanation with a research summary per the reference, then:

1. Pick the `--close-class` value at decision time from the triage rationale: `already-fixed → done`, `duplicate-of → duplicate`, `superseded-by → superseded`, `invalid` / `false-positive` / `not-a-bug` → `false-positive`. Close with the explanation as the comment and the inferred class:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/issue-lifecycle.sh close \
     --issue $ISSUE_NUMBER --comment "Closing: <detailed explanation with research summary>" \
     --close-class <inferred-class>
   ```
   This close path adds the `[FALSE-POSITIVE]` title marker for `false-positive`, `duplicate`, and `superseded`; `done` skips the marker. The closing comment is NOT scanned — the enum is the sole signal, set by the orchestrator at triage decision time. See `skills/fix-issue/scripts/issue-lifecycle.md` for the full contract.
2. **Best-effort terminal title rename** to clear the `[IN PROGRESS]` prefix Step 0 applied at lock time, replacing it with `[DONE]` so the closed issue's title accurately reflects that automated processing concluded:
   ```bash
   ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
     --text-string "$ISSUE_TITLE" \
     --text-file "$FIX_ISSUE_TMPDIR/issue-details.txt" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
   ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
   case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
   ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename \
     --issue $ISSUE_NUMBER --state done --round-trip "$ROUND_TRIP"
   ```
   Idempotent and best-effort: on `FAILED=true` or non-zero exit, log to `Tool Failures` and continue. Without this rename, a closed not-material issue would persist with the misleading `[IN PROGRESS]` title prefix until manually edited (because `/implement` Step 12a/12b/18 terminal renames only run on the PR delegation path).
   ```bash
   PICK_OUT=$(${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/umbrella-handler.sh pick-child --issue $UMBRELLA_NUMBER 2>&1)
   ALL_CLOSED=$(echo "$PICK_OUT" | awk -F= '/^ALL_CLOSED=/ { v=$2 } END { print v }')
   if [ "$ALL_CLOSED" = "true" ]; then
       ${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/finalize-umbrella.sh finalize --issue $UMBRELLA_NUMBER
   fi
   ```
   Best-effort: on `FAILED=true` / non-zero exit / `FINALIZED=false` non-idempotent error, log to `Tool Failures` and continue. The next `/fix-issue <umbrella#>` invocation will re-attempt finalization via the Step 0 exit-4 path.
   ```bash
     --issue-number "$ISSUE_NUMBER" --status closed --repo "$REPO" \
     --detail "<one-sentence reason>"
   ```
   On non-zero exit, log to `Tool Failures` and continue. Do not abort.
5. Print `✅ 3: triage — issue #$ISSUE_NUMBER closed, not material (<elapsed>)`. Skip to Step 8.

**If the issue is still actual**, print `✅ 3: triage — issue is active, proceeding (<elapsed>)` and continue.

## Step 4 — Classify Intent and Complexity

Print `> **🔶 4: classify**`

The triage-classification reference loaded at Step 3 (digest or full `triage-classification.md`) owns the decision rules for both dimensions — do not re-load it here. If only the digest was loaded and a classification edge case is genuinely uncertain, load full `triage-classification.md` at this step.

- **Intent** (`PR` vs `NON_PR`): does this issue prescribe work whose natural output is a pull request, or something else (new issues, a written report)? Default to `PR` only when the issue is genuinely ambiguous; when the issue text explicitly forbids a PR or mandates research/issues as the deliverable, pick `NON_PR` regardless of the default.
- **Complexity** (`SIMPLE` vs `HARD`, only when `INTENT=PR`): default to `SIMPLE`; classify as `HARD` only when the approach is genuinely uncertain or the work introduces a major new shared abstraction. When `hard_mode=true`, skip the evaluation and set `COMPLEXITY=HARD` directly. See the triage-classification reference for the full decision rules.

Set `INTENT` (and `COMPLEXITY` when `INTENT=PR`) per those rules using the issue details and Step 3's codebase exploration.

When `INTENT=PR` and `hard_mode=false`: print `✅ 4: classify — INTENT=**$INTENT** COMPLEXITY=**$COMPLEXITY** (<elapsed>)`. When `INTENT=PR` and `hard_mode=true`: print `✅ 4: classify — INTENT=**$INTENT** COMPLEXITY=**$COMPLEXITY** (forced by --hard) (<elapsed>)`. When `INTENT=NON_PR`: print `✅ 4: classify — INTENT=**$INTENT** (<elapsed>)`. The `**...**` bold around both `$INTENT` and `$COMPLEXITY` (when printed) is required — it makes the classification values visually prominent in the Claude Code transcript.

## Step 5 — Execute

Print `> **🔶 5: execute**`

Branch on `INTENT` from Step 4.

### 5a — `INTENT=PR` path (delegate to `/implement`)

Compose the feature description from the issue content: use the issue title as the primary description, with key details from the issue body and comments as context.

> **Continue after child returns.** When the child Skill returns, execute the NEXT step of this skill — do NOT end the turn, and do NOT write a summary, handoff, or "returning to parent" message. → shared/subskill-invocation.md#anti-halt

> ⚠ **Do NOT implement the change directly, regardless of how simple `COMPLEXITY` appears. `COMPLEXITY=SIMPLE` is a flag forwarded to `/implement` — it does not authorize direct editing. Always invoke `/implement` via the Skill tool.**

Invoke `/implement` via the Skill tool. Forwarding `--issue $ISSUE_NUMBER` makes `/implement` adopt the queue issue as its tracking issue (Phase 3 Branch 2 adoption), so the two skills converge on the same tracking issue and `/fix-issue` avoids a duplicate tracking-issue on its path:

`/implement --merge [--hard if hard_mode] --session-env $FIX_ISSUE_TMPDIR/session-env.sh --issue $ISSUE_NUMBER [--auto if auto_mode] [--no-admin-fallback if no_admin_fallback] [--no-logs-commit if no_logs_commit] [--coder=$coder if coder set] [--inline if inline_mode and hard_mode] <feature description>`

After `/implement` completes, capture the PR URL and PR number from its output. Save as `PR_URL` and `PR_NUMBER`.

> **Continue after child returns (success path only).** If `/implement` succeeded and `PR_URL` / `PR_NUMBER` are captured, your next user-facing output MUST be the Step 6 breadcrumb (`> **🔶 6: close issue**`) — do NOT end the turn (neither silently nor after text output), and do NOT write a summary, status recap, or "returning to caller" message first. If `/implement` failed or bailed, ignore this directive and follow the failure-path branch below. → shared/subskill-invocation.md#anti-halt

If `/implement` exits non-zero, branch on whether the captured output (stdout + transcript surface) contains the literal token `IMPLEMENT_BAIL_REASON=adopted-issue-closed` (emitted by `/implement` Step 0.5 Branch 2 when the adopted tracking issue is closed):

- **Bail detected** (token present): the adopted issue was closed externally after `/fix-issue` locked it. Print `**⚠ 5: execute — /implement bailed: issue #$ISSUE_NUMBER was closed externally after /fix-issue locked it. Cannot recover automatically. (<elapsed>)**`. Do NOT call `issue-lifecycle.sh close` — the issue is already closed and there is no successful run to pair with a DONE comment / PR backfill. **Umbrella finalize hook** (FINDING_8): before skipping to Step 8, if `$UMBRELLA_NUMBER` is set, check whether the externally-closed child was the umbrella's last open child and finalize if so:
   ```bash
   PICK_OUT=$(${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/umbrella-handler.sh pick-child --issue $UMBRELLA_NUMBER 2>&1)
   ALL_CLOSED=$(echo "$PICK_OUT" | awk -F= '/^ALL_CLOSED=/ { v=$2 } END { print v }')
   if [ "$ALL_CLOSED" = "true" ]; then
       ${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/finalize-umbrella.sh finalize --issue $UMBRELLA_NUMBER
   fi
   ```
   Best-effort: log to `Tool Failures` on failure. Skip to Step 8 cleanup.
- **Generic failure** (token absent): print `**⚠ 5: execute — /implement failed. Issue #$ISSUE_NUMBER remains locked with IN PROGRESS comment and [IN PROGRESS] title prefix. (<elapsed>)**`. Skip to Step 8. The IN PROGRESS comment serves as an indicator that manual intervention is needed. Note: `/implement` Step 18 may have renamed the issue title to `[STALLED] ...` (managed lifecycle prefix); see Known Limitations "Title-prefix interaction on adopted-issue retry" for the recovery flow before re-running `/fix-issue` against the same issue.

### 5b — `INTENT=NON_PR` path (follow instructions inline)

Read the issue details from Step 2 and execute the instructions directly using Read, Grep, Glob, and Bash. Do NOT call `/implement`. Do NOT modify files in the working tree — `NON_PR` tasks deliver their output as new GitHub issues, a written summary comment, or both.

> **Continue after child returns.** When any child Skill (`/issue`, `/research`, ...) returns, execute the NEXT step of this skill — do NOT end the turn, and do NOT write a summary, handoff, or "returning to parent" message. → shared/subskill-invocation.md#anti-halt

If the work cannot be completed (e.g., `/issue` fails repeatedly, the issue's instructions are infeasible, or required external access is unavailable), print `**⚠ 5: execute — non-PR task failed. Issue #$ISSUE_NUMBER remains locked with IN PROGRESS comment and [IN PROGRESS] title prefix. (<elapsed>)**` and skip to Step 8. The IN PROGRESS comment serves as an indicator that manual intervention is needed — same recovery semantics as the `/implement` failure path.

## Step 6 — Close Issue

Print `> **🔶 6: close issue**`

`issue-lifecycle.sh close` is **idempotent**: if the issue was auto-closed externally before Step 6 runs (e.g., GitHub's `Closes #<N>` PR-merge auto-close from a `/implement --merge` invocation), the call still succeeds cheaply — the DONE comment and `--pr-url` body backfill still run, only the `gh issue close` call is skipped. The stdout contract (`CLOSED=true` on success) is identical across the open and already-closed paths, so this step does not need to branch on whether the issue was already closed (stderr carries a diagnostic `INFO` or `WARNING` signal when relevant). See `skills/fix-issue/scripts/issue-lifecycle.md` for the full contract including probe-failure fallback and partial-success semantics.

Branch on `INTENT`.

### 6a — `INTENT=PR`

Update the issue body with the PR link and close with a DONE comment (single call):

```bash
${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/issue-lifecycle.sh close \
  --issue $ISSUE_NUMBER --pr-url "$PR_URL" --comment "DONE"
```

The `[IN PROGRESS]` title prefix Step 0 applied at lock time has usually already been flipped to `[DONE]` by `/implement` Step 12a/12b on PR merge. Run a best-effort marker refresh anyway so `/fix-issue` can add `[ROUND-TRIP]` when the merged PR text carries a marker and `/implement` did not already apply it:

```bash
PR_ROUND_TRIP_FILE=$(mktemp "$FIX_ISSUE_TMPDIR/round-trip-pr.XXXXXX")
gh pr view "$PR_NUMBER" --repo "$REPO" --json title,body --jq '(.title // "") + "\n" + (.body // "")' > "$PR_ROUND_TRIP_FILE"
ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
  --text-file "$FIX_ISSUE_TMPDIR/issue-details.txt" \
  --text-file "$PR_ROUND_TRIP_FILE" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename \
  --issue $ISSUE_NUMBER --state done --round-trip "$ROUND_TRIP"
```

Best-effort: on `FAILED=true` / non-zero exit / detector failure, log to `Tool Failures` and continue.

### 6b — `INTENT=NON_PR`

Close the issue with `WORK_SUMMARY` as the closing comment, passing `--close-class done` so the enum deterministically suppresses the `[FALSE-POSITIVE]` marker (no `--pr-url`, no body update):

```bash
${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/issue-lifecycle.sh close \
  --issue $ISSUE_NUMBER --comment "$WORK_SUMMARY" \
  --close-class done
```

`--close-class done` is the structured replacement for the v1 keyword-inference suppression: the enum is set at decision time, not inferred from `WORK_SUMMARY` prose, so legitimate completion narrative containing words like "duplicate" or "superseded" can never misclassify the close. Do NOT pass `--mark-false-positive-if-keyword` on the NON_PR path — the enum is authoritative. See `skills/fix-issue/references/non-pr-execution.md` for the rationale.

**Best-effort terminal title rename** to clear the `[IN PROGRESS]` prefix Step 0 applied at lock time, replacing it with `[DONE]` so the closed issue's title accurately reflects that automated processing concluded:

```bash
ROUND_TRIP_OUT=$(${CLAUDE_PLUGIN_ROOT}/scripts/round-trip-detect.sh \
  --text-string "$ISSUE_TITLE" \
  --text-file "$FIX_ISSUE_TMPDIR/issue-details.txt" 2>&1) || ROUND_TRIP_OUT="ROUND_TRIP=false"
ROUND_TRIP=$(echo "$ROUND_TRIP_OUT" | awk -F= '/^ROUND_TRIP=/ { v=$2 } END { print v }')
case "$ROUND_TRIP" in true|false) ;; *) ROUND_TRIP=false ;; esac
${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh rename \
  --issue $ISSUE_NUMBER --state done --round-trip "$ROUND_TRIP"
```

Idempotent and best-effort: on `FAILED=true` or non-zero exit, log to `Tool Failures` and continue. Without this rename, a closed NON_PR issue would persist with the misleading `[IN PROGRESS]` title prefix until manually edited (because `/implement` Step 12a/12b/18 terminal renames only run on the PR delegation path).

### 6c — Umbrella finalize hook (both 6a and 6b)

After Step 6a / 6b completes (the just-processed child has been closed), if `$UMBRELLA_NUMBER` is set (Step 0 dispatched this child from an umbrella), check whether the umbrella is now empty and finalize if so:

```bash
PICK_OUT=$(${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/umbrella-handler.sh pick-child --issue $UMBRELLA_NUMBER 2>&1)
ALL_CLOSED=$(echo "$PICK_OUT" | awk -F= '/^ALL_CLOSED=/ { v=$2 } END { print v }')
if [ "$ALL_CLOSED" = "true" ]; then
    ${CLAUDE_PLUGIN_ROOT}/skills/fix-issue/scripts/finalize-umbrella.sh finalize --issue $UMBRELLA_NUMBER
fi
```

Best-effort: on `FAILED=true` / non-zero exit / `FINALIZED=false` non-idempotent error, log to `Tool Failures` and continue. The next `/fix-issue <umbrella#>` invocation will re-attempt finalization via the Step 0 exit-4 path. The `finalize-umbrella.sh` idempotency guard ensures concurrent or repeated invocations do not double-comment (FINDING_2). If `$UMBRELLA_NUMBER` is empty, this hook is a no-op.

Print `✅ 6: close issue — #$ISSUE_NUMBER closed (<elapsed>)` (mention umbrella-finalized when applicable: `✅ 6: close issue — #$ISSUE_NUMBER closed; umbrella #$UMBRELLA_NUMBER finalized (<elapsed>)`).

> **Continue to Step 8 IMMEDIATELY.** Closing the issue is not terminal — cleanup still must run. → shared/subskill-invocation.md#step-boundary

## Step 8 — Cleanup

**This step ALWAYS runs**, regardless of the outcome of prior steps (success, failure, early exit, or abort). "Always runs" is a control-flow guarantee — the cleanup-tmpdir.sh invocation itself is gated on `FIX_ISSUE_TMPDIR` being set, since Step 0 find-and-lock may short-circuit before Step 1 setup creates the tmpdir.

If `FIX_ISSUE_TMPDIR` is set and non-empty:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-tmpdir.sh --dir "$FIX_ISSUE_TMPDIR"
```

Otherwise (Step 0 exited 1 / 2 / 3 — i.e., no eligible issue, error, or lock-failed-after-eligibility-pass — or Step 1 setup failed before mktemp), print `⏭️ 8: cleanup — skipped (no temp dir created) (<elapsed>)`. (`cleanup-tmpdir.sh` rejects empty `--dir` with exit 1 as a backstop, so the guard is defense in depth, not the only line.)

Then unconditionally print `✅ 8: cleanup — fix-issue complete! (<elapsed>)`

## Known Limitations

- **Stale IN PROGRESS lock**: Step 0 posts `IN PROGRESS` (deleting the `GO` comment first if present) and prepends `[IN PROGRESS]` to the title. If the skill crashes after Step 0 completes, the issue's last comment is `IN PROGRESS` AND the title carries the `[IN PROGRESS]` prefix — recovery: manually delete the `IN PROGRESS` comment and strip the title prefix (`gh issue edit <N> --title "<user-title>"`). If it crashes mid-Step-0 when GO was present (between deleting GO and posting `IN PROGRESS`), the issue has no comment sentinel — recovery: re-add `GO` (or leave it clean for the next auto-pick cycle since GO is no longer required). If it crashes between the `IN PROGRESS` post and the title rename (or if the rename failed best-effort, signaled by `RENAMED=false` on `find-lock-issue.sh`'s stdout), the comment lock is in place but the title is unchanged — `/implement` Step 0.5 Branch 2's idempotent rename will recover this on the next run-segment, but a crashed run leaves the issue with the `IN PROGRESS` comment and original title; recovery: manually delete the `IN PROGRESS` comment.
- **Lock-before-setup behavioral delta**: under the `find-and-lock → setup` ordering, dirty-tree-class setup failures are caught by `find-lock-issue.sh` before lock acquisition, leaving the remote issue untouched. The remaining Step 1 setup failures happen after the issue is locked with `IN PROGRESS` (comment + title prefix) and require the same manual recovery as any post-lock failure. Representative remaining modes: (a) a transient `git fetch origin main` failure inside `preflight.sh` (run by `session-setup.sh` before mktemp) — network-bound and the more likely transient cause; (b) `REPO_UNAVAILABLE=true` after `gh repo view` and the `git remote get-url` fallback both fail to yield an `owner/repo` — non-network. A narrow TOCTOU window remains between the pre-lock dirty-tree probe and the lock delegate: if another process modifies the tree in that window, Step 1 preflight catches the dirty tree after the issue has already been locked, and recovery follows the existing post-lock Stale-IN-PROGRESS path rather than exit 3's partial-mutation story. The earlier `fetch → setup → lock` ordering (pre-PR #468) would have aborted before posting `IN PROGRESS` on all setup failures, leaving the `GO` sentinel intact. The current trade preserves no-eligible-issue speed while moving the common dirty-tree failure class ahead of GitHub mutation.
- **Single-runner assumption**: The comment-based locking (Step 0) includes duplicate detection but is not fully atomic. For reliable operation, run one instance of `/fix-issue` at a time per repository.
- **Dependency check degrades silently on API failure**: The blocked-by check (Step 0) treats unreachable or erroring dependency-API responses as "no blockers known" to avoid hard-blocking the automation. If GitHub's issue-dependencies endpoint is returning 5xx or an unexpected payload, a blocked issue could temporarily be eligible.
- **Prose-dependency check shares the same fail-open posture**: A parser regression, body/comment fetch failure, or per-reference state lookup failure all degrade to "no prose blockers known" for that candidate. The offline harness (`test-parse-prose-blockers.sh`, run via `make lint`) is the primary guard against parser regressions.
- **Prose-dep check uses a strict keyword grammar**: The five recognized phrases (`Depends on`, `Blocked by`, `Blocked on`, `Requires`, `Needs`) must be immediately followed by whitespace + `#<digits>`. Typos like `Depends on#150` (no space), cross-repo references (`owner/repo#150`), URL forms (`https://github.com/…/150`), and bare `#150` mentions are deliberately NOT matched. Emphasis wrappers (`**#150**`, `_#150_`) ARE matched. Link-target wrappers (`[#150](url)`) are NOT matched, so link targets can never smuggle cross-repo references through the parser.
- **Short-circuit when native blockers exist — user-visible messages may omit prose blockers**: When an issue has BOTH native and prose open blockers, the prose path is short-circuited for rate-limit efficiency. The skip/error message will list only the native blocker numbers. Closing all listed native blockers and re-running `/fix-issue` will surface any remaining prose blockers on the next run.
- **External close while `/fix-issue` holds IN PROGRESS**: `/implement`'s Step 0.5 detects a closed adopted issue and bails with `IMPLEMENT_BAIL_REASON=adopted-issue-closed`; `/fix-issue` Step 5a reports the condition but does not unlock, since a closed issue cannot be re-locked. Recovery: re-open the issue manually and re-run `/fix-issue`.
- **Title-rename failure on Step 0 is non-fatal but visible**: when `find-lock-issue.sh`'s best-effort `tracking-issue-write.sh rename --state in-progress` call fails (transient `gh` API failure, rate limiting, etc.), the script emits `LOCK_ACQUIRED=true RENAMED=false` and continues; SKILL.md Step 0 logs a warning. The comment lock is still held, and `/implement` Step 0.5 Branch 2's idempotent rename re-attempts the title rename when the PR path runs. On the not-material (Step 3) and NON_PR (Step 5b → Step 6b) close paths, the title rename failure means the issue closes with the original (un-prefixed) title — operationally fine.
- **Bail-token detection depends on output preservation**: the adopted-issue-closed branch in Step 5a scans the captured `/implement` output for the exact literal `IMPLEMENT_BAIL_REASON=adopted-issue-closed`. If the runtime summarizes the child skill's output and the literal token is lost, Step 5a falls through to the generic-failure branch and prints the "remains locked with IN PROGRESS" message — misleading for an externally-closed issue, but operator recovery is identical (re-open and re-run). The harness at `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` guards against accidental removal of the token literal from this SKILL.md, but cannot guarantee runtime preservation of the token.
- **Title-prefix interaction on adopted-issue retry**: Step 0's `find-lock-issue.sh` applies `[IN PROGRESS]` immediately on lock; `/implement` Step 0.5 Branch 2's idempotent rename hits a `RENAMED=false` no-op on this path. On `--merge` success `/implement` Step 12a/12b flips the title to `[DONE]`; on Step 18 stall it flips to `[STALLED]`. The eligibility filter (`find-lock-issue.sh`) rejects ANY title starting with a managed lifecycle prefix (`[IN PROGRESS]` / `[DONE]` / `[STALLED]`) in both auto-pick and explicit `/fix-issue <N>` modes — so after a generic `/implement` failure the issue is left at `[STALLED] <user title>` and is no longer pickable by `/fix-issue` until the prefix is cleared. Recovery: (1) delete the `IN PROGRESS` comment, (2) clear the title prefix using `gh issue edit <N> --title "<original-title>"`. This is the documented manual flow until `/fix-issue` learns to accept `[STALLED]`-prefixed titles in explicit-retry mode.
- **Archival title prefixes are auto-pick-only exclusions**: the no-arg auto-pick scan skips research/investigation archival titles using the same trailing-space-sensitive prefix grammar as `/issue` Phase 1 dedup (<code>research </code>, <code>[research] </code>, <code>investigate </code>, <code>[investigate] </code>, <code>[research report] </code> after leading-whitespace trim + lowercase). Explicit `/fix-issue <N>` remains allowed for those titles when an operator intentionally targets one.

- **Umbrella support is explicit-target-only**: `/fix-issue <umbrella#>` accepts an umbrella issue and dispatches to the next eligible child. The auto-pick scan (no-arg `/fix-issue`) NEVER selects umbrellas — operators must explicitly target the umbrella, by design (umbrella-PR DECISION_1, voted 2-1). Detection is **title-only post-#846** (the prior body-literal detection caused false positives on issues like #753 that merely *quoted* the marker `Umbrella tracking issue.` in code or prose): per #819/#1612 the title grammar accepts two independent signals — either is sufficient: (1) a leading `[UMBRELLA]` bracket-block anywhere in the peel sequence, or (2) after stripping zero or more leading bracket-blocks of the form `[...]` and/or `(...)`, the remainder begins with <code>Umbrella: </code> or <code>Umbrella — </code>. Positive examples: `[UMBRELLA] foo`, `[IN PROGRESS] [UMBRELLA] foo`, `Umbrella: foo`, `[IN PROGRESS] Umbrella: foo`, `(urgent) Umbrella: foo`, `[IN PROGRESS] (urgent) Umbrella: foo`. Negative cases (all rejected): `[IN PROGRESS] Do something umbrella related` (Umbrella mid-title, not at front after the prefix strip), `/umbrella ...` (lowercase command syntax), any title without the `[UMBRELLA]` block or <code>Umbrella: </code> / <code>Umbrella — </code> marker — regardless of body content. Per #819 DECISION_1 the explicit-target path runs umbrella detection BEFORE the managed-prefix early-reject so all three managed prefixes (`[IN PROGRESS]`, `[DONE]`, `[STALLED]`) on umbrella titles bypass the gate; auto-pick is intentionally NOT mirrored. Title-grammar limitations (intentional): non-nesting (a block with an inner closing delimiter, e.g. `[outer [inner] outer]`, is NOT parsed as a single block), iteration cap of 16 leading bracket blocks, and fail-closed on unbalanced/unclosed leading brackets. Children are dispatched without their own `GO` comment — they inherit approval from the umbrella's existence. To run umbrella-tracked work to completion, invoke `/fix-issue <umbrella#>` once per child you want processed; the umbrella finalizes automatically (rename to `[DONE]`, post closing comment, close) when its last open child closes (Steps 0, 3, 5a, 6 all carry the finalization hook). Hand-authored umbrellas with neither a `[UMBRELLA]` bracket-block nor <code>Umbrella: </code> in their title will not be detected; add `[UMBRELLA]` to the title to restore detection.

- **Umbrella child enumeration is task-list-only**: `umbrella-handler.sh` parses children from the umbrella body using a markdown task-list regex (`- [ ] #N` or `- [x] #N`, with leading whitespace allowed; see `skills/fix-issue/scripts/umbrella-handler.md` for the full grammar). This catches `/umbrella`-rendered children (`- [ ] #N — title`) and hand-authored operator checklists (`- [ ] /fix-issue executes #N` as in #348). It does NOT match table-format umbrellas (e.g., `| #N | … |` rows) or prose `#N` references. Cross-repo references (`owner/repo#N`) are deliberately filtered out at parse time. Umbrella authors who use a table or free-form prose for their children list must add a parallel `- [ ]` checklist (or migrate to `/umbrella` rendering) to be machine-parseable.

- **Umbrella with zero parseable children does NOT auto-close**: if `/fix-issue <umbrella#>` is invoked on an issue that satisfies the umbrella detection signal (title prefix) but has zero parseable task-list child references, `find-lock-issue.sh` exits 5 with `Umbrella #N has no eligible child: no parseable children found in umbrella body` — the umbrella is NOT destructively renamed/closed. This is FINDING_3 from the umbrella-PR plan review: vacuous-truth `ALL_CLOSED` would otherwise let any open issue accidentally matching the detection signal be irreversibly closed.

- **Umbrella concurrent finalize is comment-idempotent**: when two `/fix-issue` runners reach the umbrella-finalization hook simultaneously (e.g., both close their respective last-children at the same time), `finalize-umbrella.sh`'s pre-finalization guard probes the umbrella's state, title prefix, and existing comment marker (`<!-- larch:fix-issue:umbrella-finalized -->` embedded in the closing comment body) and branches on three cases consistent with `skills/fix-issue/scripts/finalize-umbrella.md` Idempotency-guard section: (a) **state=CLOSED** is the only strict short-circuit — emits `FINALIZED=false ALREADY_FINALIZED=true REASON=already CLOSED` and exits 0 with no further mutation; (b) **state=OPEN with `[DONE]` title prefix** is a partial-success signal (prior rename succeeded, prior `gh issue close` did not) — skip the rename API call, proceed to the close path (which still posts the closing `--comment` when the marker is absent), emit `FINALIZED=true CLOSED=true RENAMED=false`; (c) **state=OPEN with the marker comment present** is a partial-success signal (prior comment-post succeeded) — skip the comment-post step (avoid double-comment under concurrency), drive a close-only retry via `issue-lifecycle.sh close --issue N` (no `--comment`), emit `FINALIZED=true CLOSED=true RENAMED=<bool>`. Cases (b) and (c) are independent and may co-occur (rename + comment both done from a prior attempt); in either OPEN case the close call still runs to drive the umbrella to CLOSED, otherwise every retry would loop on `ALREADY_FINALIZED=true` and the umbrella would stay OPEN forever. If both runners race the marker probe and both proceed past the guard, the second runner's `issue-lifecycle.sh close` call is idempotent on `state == CLOSED` and skips the `gh issue close` itself, but the comment is posted-before-probe in `cmd_close` — so a strict double-comment requires both runners to clear the marker probe before either has posted the comment. With `gh issue comment` taking ~200-500ms in practice, the window is small but not zero; operators noticing duplicate comments on the umbrella can manually delete one.

- **Umbrella's own blockers gate dispatch**: when `/fix-issue <umbrella#>` is invoked on an umbrella that itself has open native or prose blockers (excluding the umbrella's own children, which would otherwise deadlock since `/umbrella` wires every open child as a `child→umbrella` blocker per #716), the umbrella branch in `find-lock-issue.sh` exits 2 with an error naming the umbrella's blockers. Per #819 DECISION_1 the umbrella's own blocker check runs INSIDE the umbrella branch — that is, AFTER `umbrella-handler.sh detect` returned `IS_UMBRELLA=true`, and BEFORE `handle_umbrella` would dispatch a child. The check intentionally bypasses the generic `all_open_blockers` helper (which short-circuits on any native blocker without consulting prose) so an umbrella with native child-blockers + a separate prose blocker is correctly classified as blocked rather than dispatched. The sequence inside the umbrella branch: `native_open_blockers` → strip parsed children from the native set → `prose_open_blockers` → union → exit 2 with named blockers, or fall through to `handle_umbrella` when the union is empty. Children's blockers are checked separately in the umbrella dispatch path (after `pick-child` returns a `CHILD_NUMBER` and before the child lock attempt). Pre-#819, the SKILL.md text said the umbrella's own blocker check exited "before umbrella detection runs" — that wording reflected the pre-#819 ordering where the **non-umbrella** `all_open_blockers` ran in the generic path before the umbrella branch was reached; under the new ordering umbrella detection runs first and the umbrella-specific blocker check (with child filtering) runs inside the umbrella branch.

- **Umbrella `pick-child` API cost scales with prose-blocked siblings**: per #768 the eligibility check inside `umbrella-handler.sh pick-child` now runs the full native+prose `all_open_blockers` check on every walked child (instead of native-only), so `pick-child` correctly skips prose-blocked siblings to find the next ready child. The native-first short-circuit in `all_open_blockers` keeps the cost at one `gh api .../dependencies/blocked_by` call per child when any native blocker is present; when native is empty the prose path additionally fetches the child's body, all comments (paginated), and one `gh issue view --json state` call per referenced number — repeated for each prose-blocked sibling until a ready child wins. Worst case: an umbrella with N children all of whom carry only-prose blockers does ~3N + Σ-refs `gh` calls per `pick-child` invocation. The post-pick `all_open_blockers` defense-in-depth re-check in `find-lock-issue.sh handle_umbrella` adds one more pass on the chosen child. Operationally fine for typical umbrellas (a few children, mostly native or no blockers); operators noticing latency on large many-prose-blocked umbrellas should expect occasional slow `pick-child` calls. No memoization between siblings is performed in this version.
