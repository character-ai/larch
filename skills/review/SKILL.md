---
name: review
description: "Use when reviewing code changes (--diff for branch diff, or positional text for existing code review). Description mode files findings as issues by default (--no-issues suppresses)."
argument-hint: "[--diff] [--full] [--subagent] [--no-issues] [--session-env <path>] [--step-prefix <prefix>] [<description>]"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob, Agent, Task, WebFetch, Skill
---

# Code Review Skill

Review code changes using a 7-reviewer specialist panel (5 Cursor specialists + 1 Codex generic + 1 Claude generic). Two modes: **diff mode** (`--diff`) reviews the current branch diff vs `main` and implements accepted suggestions; **description mode** (positional `<description>`) reviews existing code matching the description and files accepted findings as GitHub issues by default (`--no-issues` to suppress). Claude participates as the `Claude-Generic` reviewer; it also acts as a conditional tie-breaker voter in the 2-voter adjudication panel when Cursor and Codex split 1Y/1N.

**Anti-halt continuation reminder.** After every child `Skill` tool call (e.g., `/design`, `/review`, `/bump-version`, `/issue`, `/implement`) returns AND after every `Bash` tool call that completes a numbered step or sub-step, including `run-relevant-checks-captured.sh`, IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on the child's cleanup output, on a Bash result, or on a status message, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. This applies to ALL step boundaries from Step 0 through Step 5, and to ALL sub-step transitions within Step 3's review loop (3a→3b→3c→3d→3e→3f→loop back to Step 1). **Critical: in diff mode, the review loop (Steps 1→2→3) repeats until convergence (0 findings, or Step 3f classifies the just-fixed round as non-substantial — a main-agent classification of accepted-and-fixed work, not a reading of reviewer prose) or the 7-round safety limit — completing one round's substantial fixes does NOT mean the review is done.** The rule is strictly subordinate to any explicit non-sequential control-flow directive in THIS file (e.g., `skip to Step N`, `bail to cleanup`, `jump back`, `loop back`, `fall through`, `break out`). A normal sequential `proceed to Step N+1` instruction is the default continuation this rule reinforces, NOT an exception. Every relevant-checks helper call anywhere in this file is covered by this rule. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Anti-halt continuation reminder for the canonical rule.

**Flags**: Parse flags from `$ARGUMENTS`. Flags may appear in any order; stop at the first non-flag token. After stripping all flags, the remainder (joined as a single string) is the **positional description** — it activates description mode. **All flags MUST appear before the positional description.** Because the parser stops at the first non-flag token, any flag-looking token appearing AFTER the positional description is silently absorbed into the description text rather than parsed as a flag — there is no warning. Example correct order: `/review --no-issues my description`. **All boolean flags default to `false`. Only set a flag to `true` when its `--flag` token is explicitly present in the arguments. Flags are independent — the presence of one flag must not influence the default value of any other flag.**

- `--diff`: Set a mental flag `diff_mode=true`. Activates **diff mode** (branch diff vs `main`). Mutually exclusive with positional description text. Default: `diff_mode=false`.
- `--no-issues`: Set a mental flag `no_issues=true`. Suppresses issue filing in description mode. In diff mode, silently ignored (diff mode never files issues). Default: `no_issues=false`.
- `--session-env <path>`: Set `SESSION_ENV_PATH` to the given path. This file contains already-discovered session values from a caller skill (e.g., `/implement`) including reviewer health state (`CODEX_HEALTHY`, `CURSOR_HEALTHY`, `GEMINI_HEALTHY`). If not provided, `SESSION_ENV_PATH` is empty (standalone invocation — full health probe at Step 0).
- `--step-prefix <prefix>`: Encodes both numeric prefix and textual breadcrumb path using `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for the full encoding spec. Examples: `"5.::code review"` (numeric `5.`, path `code review`), `"5."` (numeric only, backward compat). Default: empty (standalone numbering). Internal orchestration flag.
- `--subagent`: Set `subagent_mode=true`. Default: `subagent_mode=false`. When set AND `diff_mode=true`, the token-heavy Steps 1-3 (gather context, launch reviewers, recursive review+fix loop) run in an isolated Agent-tool subagent dispatched from `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md`. The parent handles Step 0 (session setup) and Steps 4-5 (final summary + cleanup), reading file-backed artifacts from `$REVIEW_TMPDIR/` after the subagent returns. Silently ignored when `diff_mode=false` (description mode stays inline; subagent benefit is minimal for read-only review). Operators running in environments without `SendMessage` should NOT use `--subagent` — a worker yield in those environments becomes a fatal stall. See `AGENTS.md` and `heavy-worker.md` for the project-wide reference.
- `--full`: Set `full_mode=true`. Default: `full_mode=false`. When set, reverts the non-substantial round termination thresholds to their pre-tightening values: LOC threshold >= ~30 (instead of the default >= ~60), and medium-to-high severity findings (instead of high-severity only) trigger another review round. Silently ignored in description mode (Step 3f does not run there). Use when the tighter defaults cause premature convergence on complex changes.

Reviewer dirty-tree changes are automatically discarded and logged — no operator prompt is issued and no stash is created.

## Anti-patterns

- **NEVER emit inline prose when `SESSION_ENV_PATH` is non-empty.** **Why:** nested `/review` runs under `/implement` (or any parent orchestrator), whose parent-visible transcript must obey the artifact-only return contract. **How to apply:** write summaries, tallies, scoreboards, rejected findings, and warning details to file-backed artifacts such as `$REVIEW_TMPDIR/review-round-summary.md` or `$IMPLEMENT_TMPDIR/execution-issues.md`, then emit only the terminal `### review-result` KV footer and required artifact paths.

## Mode activation

Mode is determined by the parser state machine (fail-closed, evaluated in order):

1. If `--diff` present AND positional description text present → **ERROR**: print `**⚠ --diff cannot be combined with a description. Use --diff alone for branch diff review, or provide a description without --diff. Aborting.**` and exit.
2. If `--diff` present (no positional text) → **diff mode**. Reviews current branch diff vs `main`, implements accepted suggestions. No issue filing.
3. If positional description text present (no `--diff`) → **description mode**. Resolves description to a canonical file list, reviews existing code, files accepted findings as GitHub issues by default (`--no-issues` suppresses). Security-tagged findings are never filed publicly (held locally per SECURITY.md).
4. If neither `--diff` nor positional description text → **ERROR**: print `**⚠ /review requires either --diff (branch diff review) or a description of what to review. Examples: /review --diff, /review implementation of auth module, /review --no-issues error handling in scripts/. Aborting.**` and exit.

**Description mode** replaces the former "slice mode": Step 1 replaces `gather-branch-context.sh` with a description-resolve step, Step 2 reviewer prompts use description-mode bodies, Step 3 skips the implement-fixes path, and Step 4 emits a `### review-result` KV footer. Issue filing via `/umbrella` is the default unless `--no-issues` is set.

**Diff mode** reviews the current branch diff vs `main`, implements accepted fixes in a recursive loop, and does not file issues.

## Progress Reporting

**Every step MUST print clearly visible breadcrumb status lines** so the user can instantly see where execution is and which parent steps they are inside. Follow the formatting rules in `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md`.

- Print a **start line** when entering a step: e.g., `> **🔶 2: launch reviewers**` (standalone) or `> **🔶 5.2: code review | launch reviewers**` (nested from `/implement`)
- Print a **completion line** only when it carries informational payload. Pure "step complete" announcements without payload are not needed.
- When `STEP_NUM_PREFIX` is non-empty, prepend it to step numbers. When `STEP_PATH_PREFIX` is non-empty, prepend it to breadcrumb paths. **This rule overrides the literal step numbers and names in `Print:` directives and examples throughout this file.** Examples shown below assume standalone mode; when nested, prepend the parent context.

Step Name Registry:
| Step | Short Name |
|------|------------|
| 0 | setup |
| 1 | gather context |
| 2 | launch reviewers |
| 3 | review cycle |
| 4 | final summary |
| 5 | cleanup |

### Reviewer status table

After launching all reviewers (Step 2), maintain a mental tracker of each reviewer's status. Print a compact table at two points per round only: (1) after launching all reviewers (all ⏳ or ⊘), and (2) after `collect-agent-results.sh` returns (all external reviewers resolved):

```
📊 Reviewers: | Structure: ✅ 3m12s | Correctness: ⏳ | Testing: ⏳ | Security: ⏳ | Edge-cases: ⏳ | Codex: ⏳ | Claude-Generic: ✅ 2m30s |
```

Icons: ✅ done (with elapsed time since launch), ⏳ pending/in-progress, ❌ failed/timeout (with elapsed time since launch), ⊘ skipped (unavailable for replacement-style reviewers only). See `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for elapsed time and step start formatting rules.

Use empty `description` parameter on Bash tool calls and terse 3-5 word descriptions on Agent tool calls. Do not produce explanatory prose between tool call outputs — only print: step breadcrumb lines (start `🔶`, completion `✅`, skip `⏩`), all warning/error lines (`**⚠ ...`), structured summaries (voting tallies, scoreboards, round summaries, findings lists, final summary), and the reviewer status table.

When `SESSION_ENV_PATH` is non-empty, follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Artifact-only return contract (nested mode): suppress parent-visible breadcrumbs, round summaries, voting tallies, reviewer scoreboards, and explanatory prose; write human-readable content to artifacts and emit only the terminal machine footer plus artifact paths required by the parent.

## Description Mode

When positional description text is present (no `--diff`), `/review` operates in **description mode** instead of diff mode:

- Step 1 (Gather Context): replaced by a **description-resolve** step that maps the verbal description to a canonical file list at `$REVIEW_TMPDIR/scope-files.txt` via Glob/Grep/Read. The canonical list anchors OOS classification.
- Step 2 (Launch Reviewers): reviewer prompts instruct the panel to review the canonical file list (existing code, not a diff). Reviewers may explore further via Glob/Grep/Read for context but OOS classification is anchored to the canonical list.
- Step 3 (Review Cycle): runs ONE round only (no recursive re-review loop). After voting, compose a findings batch and invoke `/umbrella` via the Skill tool (default), or just print the findings (if `--no-issues`).
- Step 3e (Implement Fixes): SKIPPED in description mode — description mode is read-only review for issue filing, not implement-fixes.
- Step 4 (Final Summary): writes accepted security findings to `$REVIEW_TMPDIR/security-findings.md` (printed to terminal before cleanup; never filed publicly per SECURITY.md); emits a `### review-result` KV footer.

## Step 0 — Session Setup

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 0 — session setup" || true
```

Run the shared session setup script. This handles temp directory creation, reviewer health probe, and health status file in a single call:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-review --skip-preflight --skip-branch-check --skip-repo-check --check-reviewers [--caller-env "$SESSION_ENV_PATH"] [--skip-codex-probe] [--skip-cursor-probe] [--write-health "${SESSION_ENV_PATH}.health"]
```

Only include `--caller-env "$SESSION_ENV_PATH"` and `--write-health "${SESSION_ENV_PATH}.health"` if `SESSION_ENV_PATH` is non-empty. If `SESSION_ENV_PATH` provides a non-empty `CODEX_HEALTHY` or `CURSOR_HEALTHY` value (either `true` or `false`), the script auto-sets the corresponding `--skip-codex-probe` / `--skip-cursor-probe` flag and propagates the caller value. `GEMINI_HEALTHY` is always hard-coded `false` by `session-setup.sh` (#1720 Part 1).

If the script exits non-zero, print the error and abort.

Parse the output for `SESSION_TMPDIR`, `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `GEMINI_AVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`, `GEMINI_HEALTHY`, `LARCH_TOKEN_SESSION_ID`, and `LARCH_CLAUDE_SOURCE_FILE`. Set `REVIEW_TMPDIR` = `SESSION_TMPDIR`. Substitute the actual path in every command below.

If `SESSION_ENV_PATH` is non-empty, rehydrate token context before launching reviewers. Empty values are valid for standalone `/review`; do not fail when either key is absent:

```bash
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
```

Every Bash block that invokes a review launcher MUST have these two variables in its environment. The launchers tolerate empty values and fall back to legacy token-ledger resolution when `/review` is standalone.

Set mental flags `codex_available` and `cursor_available` based on the output:
- If `CODEX_AVAILABLE=false`: `codex_available=false`. Print: `**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**`
- Else if `CODEX_HEALTHY=false`: `codex_available=false`. Print: `**⚠ Codex installed but not responding (health check failed). Using Claude replacement.**`
- Else: `codex_available=true`
- Same logic for Cursor.

## Subagent Dispatch (diff mode only, when `--subagent`)

When `subagent_mode=true` AND `diff_mode=true`, dispatch the heavy-phase work (Steps 1-3) to an Agent-tool subagent **immediately after Step 0 completes**. The parent then skips Steps 1-3 and proceeds directly to reading artifacts for Step 4.

**MANDATORY — READ ENTIRE FILE** before dispatching: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md`. Contains the subagent contract, artifact contract, wait discipline, and return-value grammar.

Dispatch the subagent via the Agent tool with `subagent_type: larch:reviewer-correctness` — use any available reviewer subagent type as the execution host, or use a general-purpose agent. Pass to the subagent prompt:

```
REVIEW_TMPDIR=<$REVIEW_TMPDIR>
SESSION_ENV_PATH=<$SESSION_ENV_PATH>
codex_available=<true|false>
cursor_available=<true|false>

Follow the instructions in ${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md exactly.
```

> **Continue after subagent returns.** When the Agent tool returns, parse the return text for `REVIEW_HEAVY=complete` or `REVIEW_HEAVY=failed REASON=<token>`. Do NOT end the turn, write a summary, or produce a handoff message — proceed immediately per the branch below.

- **`REVIEW_HEAVY=complete`**: Read `$REVIEW_TMPDIR/review-round-summary.md` (exists when the subagent succeeded). The code edits made by Step 3e are already in the git working tree. `$REVIEW_TMPDIR/review-dirty-tree-summary.env` is already written by the subagent. Proceed to Step 4 using the file-backed artifacts: Step 4a prints `review-round-summary.md` only for standalone invocations; nested diff mode copies it to the parent tmpdir and emits only the `### review-result` footer. Step 5a reads `review-dirty-tree-summary.env` as-is (already aggregated). **Skip Steps 1-3 entirely.**
- **`REVIEW_HEAVY=failed REASON=<token>`**: Print `**⚠ /review subagent failed: $REASON. Falling back to inline review.**`, set `subagent_mode=false`, and continue to Step 1 below (inline fallback).
- **Return text missing `REVIEW_HEAVY=`** (subagent stalled or suspended): Print `**⚠ /review subagent returned without REVIEW_HEAVY sentinel. Falling back to inline review.**`, set `subagent_mode=false`, and continue to Step 1.

## Step 1 — Gather Context

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 1 — gather context" || true
```

### Diff mode (`--diff`)

Run the gather script to collect the diff and context:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/gather-branch-context.sh --output-dir "$REVIEW_TMPDIR"
```

Parse the output for `DIFF_FILE`, `FILE_LIST_FILE`, and `COMMIT_LOG_FILE`. Read these files to get the full diff, file list, and commit log — you will pass these to each subagent.

### Description mode (positional description text)

Skip `gather-branch-context.sh`. Resolve the verbal description to a canonical file list:

1. **Load the verbal description**: use `DESCRIPTION_TEXT` (the positional remainder captured by the flag parser, joined as a single string).
2. **Resolve to canonical file list**: use `Glob`, `Grep`, and `Read` tools to identify the files that match the verbal description. The orchestrating agent applies semantic judgment — for "implementation of /research skill", that means `skills/research/SKILL.md` and `skills/research/references/*.md` and any sibling scripts; for "all hook scripts under hooks/", that means `hooks/*.sh` and `hooks/hooks.json`; for "complete contents of foo library", that means every file under `foo/`.
3. **Write to `$REVIEW_TMPDIR/scope-files.txt`**: one file path (repo-relative) per line. This file is the **canonical anchor for OOS classification** — reviewers MUST treat this as the authoritative scope for the description.
4. If the resolved file list is empty, print `**⚠ Description resolved to zero files. Nothing to review. Exiting.**`, emit a `### review-result` footer with `PARSE_STATUS=ok ISSUES_CREATED=0 ISSUES_DEDUPLICATED=0 ISSUES_FAILED=0 SECURITY_FINDINGS_HELD=0`, and proceed to Step 5 (cleanup).

Set `DIFF_FILE` to empty (no diff in description mode). Set `FILE_LIST_FILE` to `$REVIEW_TMPDIR/scope-files.txt`. Set `COMMIT_LOG_FILE` to empty.

## Step 2 — Launch Reviewer Panel in Parallel

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 2 — reviewer panel" || true
```

### Reviewer panel composition

The panel has 7 reviewers: **5 specialist reviewers** + **1 generic Codex reviewer** + **1 Claude generic reviewer**. Each specialist concentrates on a narrow focus area using personality definitions from `${CLAUDE_PLUGIN_ROOT}/agents/reviewer-*.md`, rendered into tool-specific prompts by `${CLAUDE_PLUGIN_ROOT}/scripts/render-specialist-prompt.sh`.

The 5 specialists and their attribution labels:

| Specialist | Agent file | Attribution label |
|---|---|---|
| Structure/KISS/Maintainability | `agents/reviewer-structure.md` | `Structure` |
| Correctness/Logic/Error-paths | `agents/reviewer-correctness.md` | `Correctness` |
| Tests/CI/Regression | `agents/reviewer-testing.md` | `Testing` |
| Security/Trust-boundaries | `agents/reviewer-security.md` | `Security` |
| Edge-cases/Failure-recovery | `agents/reviewer-edge-cases.md` | `Edge-cases` |

The generic Codex reviewer uses attribution label `Codex`. The Claude generic reviewer uses attribution label `Claude-Generic`.

**Description mode is unchanged**: single round, no implement loop, not affected by the round-state machine below. Description mode launches the full 7-reviewer panel for its single round.

### Fallback matrix

| Cursor | Codex | Specialist slots (5) | Required generic slot | Claude generic | Total |
|---|---|---|---|---|---|
| ✅ | ✅ | 5x Cursor specialist (`cursor-specialist-{name}-output.txt`) | 1x Codex generic (`codex-output.txt`) | 1x Claude generic (Agent tool) | 7 |
| ❌ | ✅ | — | 1x Codex generic (`codex-output.txt`) | 1x Claude generic (Agent tool) | 2 |
| ✅ | ❌ | 5x Cursor specialist (`cursor-specialist-{name}-output.txt`) | — | 1x Claude generic (Agent tool) | 6 |
| ❌ | ❌ | — | — | 1x Claude generic (Agent tool, `larch:code-reviewer`, `"sonnet"`) | 1 |

**Partial specialist failure**: if `collect-agent-results.sh` reports `STATUS != OK` for an individual specialist slot, follow Runtime Timeout Fallback for that slot's tool only — flip the tool to unavailable for the session. The round proceeds with whichever specialists returned valid output. Do NOT retry individual slots within the same round.

### Launch procedure

Launch **all reviewers in a single message**. Spawn order: specialist slots first (slowest), then Codex generic, then Claude generic.

**5 specialist slots** — for each specialist (`structure`, `correctness`, `testing`, `security`, `edge-cases`), only launch when `cursor_available`. When `cursor_available` is false, skip all specialist slots (use only the generic Codex + Claude generic). The wrappers handle prompt rendering (`render-specialist-prompt.sh`), model args (`agent-model-args.sh`), and prompt wrapping (`cursor-wrap-prompt.sh` for Cursor) internally:

**Cursor specialist** (if `cursor_available`; set `CURSOR_SPECIALIST_TIMING_KIND=cursor-specialist-<name>` with `<name>` replaced by `structure`, `correctness`, `testing`, `security`, or `edge-cases`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$REVIEW_TMPDIR/cursor-specialist-<name>-output.txt" --timeout 1800 --agent-file "${CLAUDE_PLUGIN_ROOT}/agents/reviewer-<name>.md" --mode <diff|description> [--diff-file "$DIFF_FILE" in diff mode] [--description-text "${DESCRIPTION_TEXT}" --scope-files "$REVIEW_TMPDIR/scope-files.txt"] --competition-notice --timing-task-kind "$CURSOR_SPECIALIST_TIMING_KIND"
```

Use `run_in_background: true` and `timeout: 1860000` on each specialist Bash tool call.

**1 generic Codex slot** (if `codex_available`):

**Diff mode**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$REVIEW_TMPDIR/codex-output.txt" --timeout 1800 --timing-task-kind codex-review-generic --prompt "Review all code changes on the current branch vs main. The diff has been pre-computed at $DIFF_FILE — read that file to see the changes (context is capped at 20 lines per hunk; use the Read tool to read a full file when you need more context). Run git log $(git merge-base HEAD main)..HEAD --oneline for commits. Walk five focus areas: (1) Code Quality: bugs, logic, reuse, tests, backward compat, style. (2) Risk/Integration: breaking changes, side effects, thread safety, deployment risks, regressions, CI. (3) Correctness: logic errors, off-by-one, nil handling, type mismatches, races, error paths. (4) Architecture: separation of concerns, contract boundaries, invariants, semantic boundaries. (5) Security: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs. Tag each finding with its focus area (one of code-quality / risk-integration / correctness / architecture / security). Return numbered findings with focus-area tag, file:line, issue, and suggested fix. When emitting [OUT_OF_SCOPE] findings, include affected repo-relative file paths and line ranges (e.g., skills/foo/bar.sh:120-150) in the finding's issue text when applicable, so /implement Step 9a.1's file-conflict pre-pass can emit serialization edges. If NO issues, output exactly NO_ISSUES_FOUND. Do NOT modify files. Work at your maximum reasoning effort level."
```

**Description mode**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$REVIEW_TMPDIR/codex-output.txt" --timeout 1800 --timing-task-kind codex-review-generic --prompt "Review existing code described as: '${DESCRIPTION_TEXT}'. The canonical file list is at $REVIEW_TMPDIR/scope-files.txt — read that file first to see exactly which files are in scope. Read each listed file in full. You may also explore via Glob/Grep/Read for additional context, but in-scope vs out-of-scope (OOS) classification MUST be anchored to the canonical file list — findings about files NOT in scope-files.txt are OOS, even if they look related. Walk five focus areas: (1) Code Quality: bugs, logic, reuse, tests, backward compat, style. (2) Risk/Integration: breaking changes, side effects, thread safety, deployment risks, regressions, CI. (3) Correctness: logic errors, off-by-one, nil handling, type mismatches, races, error paths. (4) Architecture: separation of concerns, contract boundaries, invariants, semantic boundaries. (5) Security: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs. Tag each finding with its focus area (one of code-quality / risk-integration / correctness / architecture / security). Mark any finding about a file NOT in scope-files.txt as OOS. Return findings in two clearly delimited sections: a section starting with the line '### In-Scope Findings' for findings about files in scope-files.txt, and a section starting with the line '### Out-of-Scope Observations' for findings about files NOT in scope-files.txt. Each finding: focus-area tag, file:line, issue, and suggested fix. For findings placed under '### Out-of-Scope Observations' (and any in-scope finding whose issue text references repo files), include affected repo-relative file paths and line ranges (e.g., skills/foo/bar.sh:120-150) in the finding's issue text when applicable, so /implement Step 9a.1's file-conflict pre-pass can emit serialization edges. If you have neither in-scope findings nor out-of-scope observations, output exactly NO_ISSUES_FOUND. Do NOT modify files. Work at your maximum reasoning effort level."
```

Use `run_in_background: true` and `timeout: 1860000`.

**Generic Codex fallback** (if `codex_available` is false): when Codex is unavailable, skip the generic Codex slot entirely. The Claude generic reviewer (always launched) covers this gap.

**1 Claude generic reviewer** (always launched, regardless of Cursor/Codex availability): Agent tool (subagent_type: `larch:code-reviewer`, model: `"sonnet"`) with the unified archetype from `${CLAUDE_PLUGIN_ROOT}/skills/shared/reviewer-templates.md`. Use mode-appropriate `{REVIEW_TARGET}` and `{CONTEXT_BLOCK}`, and append the competition notice. Attribution label: `Claude-Generic`.

**Both-down path** (both `cursor_available` and `codex_available` are false): Only the Claude generic reviewer runs (no specialists, no generic Codex). Print: `**⚠ Both Cursor and Codex unavailable. Proceeding with 1 Claude generic reviewer. Voting will be skipped (insufficient reviewers).**`

Append the following competition context to each reviewer's prompt (specialist and generic, all modes):

> **Competition notice**: Your findings will be voted on by a 2-voter primary panel (Codex + Cursor) using YES/NO/EXONERATE; on a 1Y/1N split, Claude is invoked as a conditional tie-breaker. Exception: if every active reviewer flags the same in-scope finding, it is auto-accepted before the panel vote and earns you +1 automatically. Each finding voted on that receives 2+ YES votes earns you +1 point. Findings with exactly 1 YES earn 0 points. Findings with 0 YES but at least 1 EXONERATE earn 0 points (the panel recognized your concern as legitimate). Findings with 0 YES and 0 EXONERATE cost you -1 point. Focus on high-quality, actionable findings. Out-of-scope observations use **asymmetric scoring** — accepted OOS items (2+ YES) earn +1 point and are filed as GitHub issues; all other OOS outcomes (including unanimous rejection) score 0.

### Collecting External Reviewer Results

External reviewer output collection, validation, and retry are handled by the shared collection script — see the **Collecting External Reviewer Results** section in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md`. The explicit `collect-agent-results.sh` invocation is in Step 3a below.

## Step 3 — Collect, Deduplicate, and Implement (Recursive Loop in diff mode; ONE round in description mode)

**MANDATORY — READ ENTIRE FILE** before executing any sub-step of Step 3: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md`. It contains the Settings.json permissions ordering rule and the skill/script genericity rule that the orchestrating agent applies when evaluating findings and reviewing the diff/description across Step 3 (collect, dedup, voting, fix application). Loaded unconditionally on every Step 3 entry.

### Round-state machine (diff mode)

**In diff mode**, this step repeats until reviewers find no more issues, the just-fixed round is classified non-substantial at Step 3f, or the round cap is hit. Track the current **round number** starting at 1. Also track `pre_fix_sha=""` (HEAD SHA captured before each round's Step 3e fix implementation; empty for round 1) and `prev_had_security_correctness=false` (set when an accepted finding in the current round has focus area `security` or `correctness`; reset to `false` at the start of each new round so the override reflects only the immediately preceding round's findings).

At the top of each Step 3 round iteration, reset `prev_had_security_correctness=false` (so only the immediately preceding round's findings affect the next round's cap check), then invoke the bash timing block (before `### 3a — Collect` for round N):

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 3 round ${round_num} — review cycle" || true
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 5 — review Step 3 round ${round_num} voting cycle" || true
```

Use the round counter already tracked by the round state machine.

| Rounds | Reviewer panel | Voting | OOS collection | Stop condition |
|--------|---------------|--------|----------------|----------------|
| 1-3 | Full 7-reviewer panel (5 Cursor specialists + 1 Codex generic + 1 Claude generic) | 2-voter panel (Cursor + Codex); Claude tie-breaker on 1Y/1N splits | Yes | 0 findings accepted by vote, OR Step 3f classifies the just-fixed round as non-substantial, OR round 3 reached |
| 4-7 | Single generic reviewer per round, chain `Cursor → Codex → Claude` | No voting (auto-accept) | No | 0 findings, OR Step 3f classifies the just-fixed round as non-substantial, OR round 7 reached |

**Description mode is unchanged**: single round, no implement loop. After Step 3d's round summary, jump directly to Step 4 (skip Step 3e implement-fixes and Step 3f re-review).

Symmetric `/review` ↔ `/implement` chain rule: rounds 4+ use `Cursor → Codex → Claude`.

### 3a — Collect

**Rounds 1-3 (full 7-reviewer panel):** Collect and validate all external reviewer outputs using the shared collection script. Include output paths for all specialist and generic Codex reviewers that were actually launched as external tools. The Claude generic reviewer output is parsed directly from the Agent tool return (do not include it in `collect-agent-results.sh`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode [--write-health "${SESSION_ENV_PATH}.health"] \
  "$REVIEW_TMPDIR/cursor-specialist-structure-output.txt" \
  "$REVIEW_TMPDIR/cursor-specialist-correctness-output.txt" \
  "$REVIEW_TMPDIR/cursor-specialist-testing-output.txt" \
  "$REVIEW_TMPDIR/cursor-specialist-security-output.txt" \
  "$REVIEW_TMPDIR/cursor-specialist-edge-cases-output.txt" \
  "$REVIEW_TMPDIR/codex-output.txt"
```

Only include `--write-health` if `SESSION_ENV_PATH` is non-empty. Only include output paths for reviewers that were actually launched as external tools (adjust paths per the fallback matrix — e.g., omit all cursor-specialist-* paths and codex-output.txt when both are down; when Cursor is down, omit specialist paths and include only codex-output.txt when Codex is available). The Claude generic reviewer is always parsed directly from the Agent tool result — never passed to `collect-agent-results.sh`.

Parse the structured output for each reviewer's `STATUS` and `REVIEWER_FILE`. For any reviewer with `STATUS` not `OK`, follow the **Runtime Timeout Fallback** procedure. Read valid output files. **In description mode**, reviewers produce **dual-list output** with '### In-Scope Findings' and '### Out-of-Scope Observations' section headers — parse both sections. Section-header fail-open rules: (1) if exactly one section header is present, the missing section is interpreted as empty (NOT a parse error); (2) if both section headers are absent AND the entire output is the literal 'NO_ISSUES_FOUND', the reviewer reported nothing — proceed; (3) if both section headers are absent AND the output is not 'NO_ISSUES_FOUND' (legacy unsectioned output), treat the entire body as in-scope. **In diff mode**, output shape depends on the slot kind. **Specialist slots** (`cursor-specialist-*`) follow the same two-section template as description mode (their agent files mandate `### In-Scope Findings` / `### Out-of-Scope Observations`) — apply the same section-header fail-open rules. **Generic slots** (`codex-output.txt` and Claude generic) produce single-list output: treat findings whose first line carries an `[OUT_OF_SCOPE]` prefix as OOS observations and route them to the OOS bucket; treat all other findings as in-scope. OOS findings (from either slot kind) have their accepted form filed via `oos-accepted-review.md` for `/implement` Step 9a.1, not implemented as code edits this PR.

Immediately after each `collect-agent-results.sh` return, scan every launched external output's `${OUTPUT}.dirty-tree` sidecar. Treat missing, empty, dirty, or unknown sidecars as `STATUS=unknown` unless a checkpoint probe proves the tree clean. On `STATUS=dirty` or `STATUS=unknown`, automatically log and discard the reviewer-introduced changes — do NOT stash them and do NOT prompt the operator. Identify the reviewer from the output filename (specialist label or generic slot name). If `SESSION_ENV_PATH` is non-empty (running under `/implement`), append a `Warnings` entry to `$IMPLEMENT_TMPDIR/execution-issues.md`:

```
- **Step 5 (review round) — reviewer dirty tree discarded:** <reviewer-label>; STATUS=<STATUS>. Changes automatically discarded (git stash NOT used).
```

If `SESSION_ENV_PATH` is empty (standalone `/review`), emit `**⚠ review Step 3a — <reviewer-label> left uncommitted changes; discarding automatically.**` to the transcript. Then discard: validate repo-relative paths, reject absolute paths, `..`, and `.git/`; run `git restore --pathspec-from-file=- --pathspec-file-nul -- < TRACKED_PATHS_FILE` for tracked changes, and `[ -s NEW_UNTRACKED_PATHS_FILE ] && xargs -0 git clean -f -- < NEW_UNTRACKED_PATHS_FILE` for new untracked files (`git clean` does NOT accept `--pathspec-from-file` / `--pathspec-file-nul`; the portable stdin form `xargs -0 ... < FILE` works on both GNU and BSD xargs, while `xargs -0 -a FILE ...` is GNU-only and fails on macOS); never run a blanket clean. Mark `RECOVERY_TAKEN=true`.

Merge findings from all launched reviewers, attributing each finding to its specialist label (`Structure`, `Correctness`, `Testing`, `Security`, `Edge-cases`, `Codex`, `Claude-Generic`). When deduplicating, credit all proposing reviewers. If the same issue appears in both in-scope and OOS from different reviewers, merge under in-scope.

**Rounds 4-7 (diff mode only, single generic reviewer):** Launch a single Cursor generic reviewer (if `cursor_available`; else Codex generic if `codex_available`; else Claude Code Reviewer subagent). Use tool-qualified output paths: `$REVIEW_TMPDIR/cursor-round${round_num}-output.txt` or `$REVIEW_TMPDIR/codex-round${round_num}-output.txt`. Collect its output via `collect-agent-results.sh` with a single output path. If `STATUS` is not `OK`, follow Runtime Timeout Fallback and retry the round with the next available tool in the chain.

OOS observations are only collected in rounds 1-3 — rounds 4-7 use a single generic reviewer without OOS collection.

### 3b — Check for Zero Findings

If **all reviewers** report no issues (e.g., "No issues found.", "No in-scope issues found.", "NO_ISSUES_FOUND"), the loop is done — IMMEDIATELY skip to **Step 4** without writing a summary or status message. If reviewers DID find issues, IMMEDIATELY continue to Step 3c (Deduplicate) — do NOT print a summary or stop.

### 3c — Deduplicate

Merge findings from all reviewers into a single deduplicated list, grouped by file. If two reviewers flag the same issue, keep the more specific suggestion. Assign each deduplicated finding a stable sequential ID (`FINDING_1`, `FINDING_2`, etc. for in-scope; `OOS_1`, `OOS_2`, etc. for OOS) and note which reviewer(s) proposed each.

### 3c.1 — Voting Panel (rounds 1-3)

**In rounds 1-3 — both-down path** (both `cursor_available` and `codex_available` are false, so only the Claude generic reviewer ran): Do NOT load `${CLAUDE_PLUGIN_ROOT}/skills/review/references/voting.md`. Auto-accept all deduplicated in-scope Claude findings directly (no competition scoring, no ballot files). Write any OOS findings to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` when `SESSION_ENV_PATH` is non-empty AND description mode is OFF, using the same `### OOS_N:` schema and security-tag exclusion as the voted-rounds path. Proceed to Step 3d.

**In rounds 1-3** (when at least one of Cursor or Codex ran): **MANDATORY — READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/review/references/voting.md` and execute its body — the pre-voting filter (unanimity auto-accept for in-scope findings proposed by all active reviewers; nit-only auto-exonerate when `SESSION_ENV_PATH` is non-empty), two-voter setup (Cursor + Codex) with conditional Claude tie-breaker on 1Y/1N splits, proportionality guidance, ballot file handling rule (Write tool, not `cat`-heredoc), parallel launch order (Cursor → Codex; Claude only on 1Y/1N tie), threshold rules + competition scoring per `${CLAUDE_PLUGIN_ROOT}/skills/shared/voting-protocol.md`, the zero-accepted-findings short-circuit to **Step 4**, the OOS-accepted-by-vote artifact write to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` (only when `SESSION_ENV_PATH` is non-empty AND description mode is OFF — description mode bypasses this artifact and files directly via /umbrella at Step 4), and the save-not-accepted-IDs rule used to suppress re-raised findings in rounds 4+ (diff mode only). Accepted OOS Descriptions should include affected repo-relative file paths and line ranges when applicable; `/implement` Step 9a.1 serializes same-file OOS issues unless the exposed ranges are parseable and non-overlapping.

**In rounds 4-7 (diff mode only)**: Skip voting — accept all single-reviewer findings directly, **except** findings that match findings rejected or exonerated by voting in rounds 1-3. **Do NOT load** `${CLAUDE_PLUGIN_ROOT}/skills/review/references/voting.md` in rounds 4+ — the body is for rounds 1-3 and would waste tokens. Same `Do NOT load` guidance applies on the Step 3b zero-findings short-circuit.

### 3d — Print Round Summary

Print to the user:
- `## Review Round {N}` header
- Bullet list of **accepted** findings with reviewer attribution (`Structure` / `Correctness` / `Testing` / `Security` / `Edge-cases` / `Codex` / `Claude-Generic`, or `Claude` for the both-down fallback)
- If rounds 1-3: vote counts per finding, accepted OOS items, and any findings not accepted by vote
- Total count of accepted findings for this round

After printing the round summary, IMMEDIATELY continue. **In diff mode**: if 0 findings were accepted this round, skip to Step 4; if >0 findings were accepted, proceed to Step 3e (Implement Fixes). **In description mode**: always skip to Step 4 after 3d (Step 3e is read-only skipped). Do NOT treat the summary as a stopping point. **Churn-cap tracking** (diff mode only): if any accepted finding has focus area `security` or `correctness`, set `prev_had_security_correctness=true` so the next round's Step 3f diff-churn cap is bypassed.

### 3e — Implement Fixes

**SKIPPED in description mode.** Description mode is read-only — proceed directly to Step 4 after Step 3d.

**In diff mode**, before applying fixes, capture `pre_fix_sha=$(git rev-parse HEAD 2>/dev/null || echo "")` — this SHA anchors Step 3f's diff-churn cap, which compares it against the working tree (not HEAD, since review fixes are uncommitted between rounds). Then for each **accepted in-scope** finding (`FINDING_*` items only — exclude `OOS_*` items, which are processed separately for issue filing by `/implement`):

1. Apply the suggested fix by editing the relevant file.
2. If the fix involves creating new tests, write them.
3. If the fix involves CI workflow changes, edit the workflow YAML.

> **Continue after child returns.** On `RELEVANT_CHECKS_OK=true`, IMMEDIATELY continue to Step 3f. On `STATUS=fail`, first check for `FAILURE_REASON` (structural — e.g. `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `missing-check-script`, `redaction-failed`; act on the reason, no log file is produced); otherwise read `REDACTED_LOG_FILE` (checks failure — NOT raw `LOG_FILE`); diagnose, fix, and re-invoke the helper. Do NOT end the turn, and do NOT write a summary, handoff, or "returning to parent" message. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Anti-halt continuation reminder.

After all fixes are applied, run validation checks:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-relevant-checks-captured.sh" --site review-step3e --tmpdir "$REVIEW_TMPDIR"
```

### 3f — Re-review

> **CRITICAL: Fixing substantial findings does NOT mean the review has converged.** Convergence requires the reviewers to report no new issues in a fresh round, or the main agent classifies the just-fixed round's accepted-and-fixed work as non-substantial (`round_substantial=false`) per the definition below — not just the orchestrator believing its fixes are clean, and not a reading of reviewer prose ("they only reported nits"). After implementing substantial fixes, you MUST re-launch reviewers to verify. Do NOT skip this step for substantial rounds.

**SKIPPED in description mode.** Proceed to Step 4.

**Substantial round definition**: A round's accepted findings are substantial if at least one accepted finding is a high-severity bug (correctness, security, race, data corruption, broken contract, or comparable — medium severity does NOT trigger another round unless `--full` is set), OR the applied fixes are significant in size (a non-trivial code change; as a judgment-call convention, a single fix touching >= ~60 LOC of non-comment code or aggregate fixes that meaningfully change structure — use >= ~30 LOC when `--full` is set), OR the accepted-fix count is large (`>= 5`). A round is not substantial only when no accepted finding reaches the applicable severity threshold (no high-severity finding by default; no medium-or-higher finding with `--full` set), the applied fixes are small (below the applicable LOC threshold), and the accepted-fix count is `< 5`. This is a main-agent judgment call parallel to the OOS triage thresholds; precise bookkeeping is not required, but the boundary directions (`>= 5`, `< 5`, and `>= ~60 LOC` — or `>= ~30 LOC` with `--full`) are fixed.

**In diff mode**, classify the just-fixed round as `round_substantial=true|false` before incrementing the round number. Use the accepted-finding count from Step 3d plus the severity and fix-size judgment from Steps 3d-3e. If `round_substantial=false`, print `✅ 3f: re-review — round $round_num findings were not substantial; review converged` and IMMEDIATELY skip to Step 4. Do NOT launch another reviewer round for non-substantial findings.

> **Continue to Step 4 IMMEDIATELY.** A non-substantial re-review convergence line is not terminal — final summary and cleanup still must run. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Step-boundary anti-halt.

If `round_substantial=true`, increment the round number. IMMEDIATELY re-execute **Step 1** (gather the updated diff) then **Step 2** (launch reviewers again) then **Step 3** (collect, deduplicate, vote/evaluate, implement) as a fresh iteration of the review loop — do NOT halt, summarize, or wait for user input between rounds. The loop continues until reviewers report 0 findings, the last round produced only non-substantial findings (convergence), or the safety limit is reached (Step 3g).

**Rounds 2-3 (diff-churn cap check first)**: Before re-launching the full panel, check whether the fix was trivial. When `pre_fix_sha` is non-empty, compute:

```bash
CHURN_LOC=$(git diff --numstat "${pre_fix_sha}" 2>/dev/null | awk '{add+=$1; del+=$2} END {print add+del+0}')
```

(`pre_fix_sha` was captured against the working tree, so the `HEAD`-less form measures uncommitted edits since that snapshot.)

If `CHURN_LOC` < 10 AND `prev_had_security_correctness=false`: print `⚡ 3f: re-review — round $round_num diff-churn ${CHURN_LOC} LOC (<10, no security/correctness override); using single reviewer` and launch only a single Cursor generic reviewer (fallback: Codex generic if `codex_available`; else Claude Code Reviewer subagent) instead of the full panel — the same chain as rounds 4-7. The security/correctness override ensures one-line changes to critical invariants still get full panel coverage.

Otherwise (`CHURN_LOC >= 10` OR `prev_had_security_correctness=true`): Re-launch the full 7-reviewer panel per Step 2's launch procedure. Voting runs per Step 3c.1. The competition notice is included. This ensures multi-round specialist coverage with proper adjudication. If voting accepts 0 findings in any of rounds 1-3, the review loop terminates early.

**Rounds 4-7 (single generic reviewer)**: Only launch **Cursor generic** (if `cursor_available`; else Codex generic if `codex_available`; else 1 Claude Code Reviewer subagent as fallback). Use the same generic diff-mode prompt from Step 2 (without the competition notice — there is no voting panel in rounds 4+), appending 'Findings may be reviewed for quality.' at the end. In rounds 4-7 Step 3a, collect from whichever single reviewer was launched: external output via `collect-agent-results.sh` (with Runtime Timeout Fallback on failure — retry the round with the next tool in the chain), or Claude subagent output directly. Findings that were rejected or exonerated by voting in rounds 1-3 are suppressed per Step 3c.1.

### 3g — Safety Limit

**Diff mode only.** If the loop has run **7 rounds** without converging (3 full-panel rounds + 4 single-reviewer rounds), stop and print a warning, then IMMEDIATELY proceed to Step 4 — do NOT halt or wait for user input.

## Step 4 — Final Summary (and description-mode /umbrella filing)

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 4 — final summary" || true
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 5 — review Step 4 final summary" || true
```

### 4a — Print summary (both modes)

`$REVIEW_TMPDIR/review-round-summary.md` is the file-backed source for Step 4 human-readable summary content.

**Subagent path** (`subagent_mode=true` AND `REVIEW_HEAVY=complete`): the heavy worker already wrote the summary directly to `$(dirname "$SESSION_ENV_PATH")/review-round-summary.md` (the stable parent-tmpdir path). No copy is needed; the file at the parent-tmpdir path is already present.

**Inline path** (inline mode or subagent fallback): compose the final summary below, write it to `$REVIEW_TMPDIR/review-round-summary.md`, and when `SESSION_ENV_PATH` is non-empty also copy it to `$(dirname "$SESSION_ENV_PATH")/review-round-summary.md` (the stable parent-tmpdir path that `/implement` reads and that survives Step 5 cleanup).

Summary content:
- Total number of review rounds (always 1 in description mode)
- Findings per round (with per-reviewer breakdown: `Structure` / `Correctness` / `Testing` / `Security` / `Edge-cases` / `Codex` / `Claude-Generic`, or `Claude` for fallback)
- Voting summary (rounds 1-3): total findings voted on, accepted (2+ YES), neutral (1 YES), exonerated (0 YES + 1+ EXONERATE), rejected (0 YES + 0 EXONERATE) (skip when both `cursor_available` and `codex_available` are false — no voted rounds)
- Reviewer Competition Scoreboard (cumulative across all voted rounds, one row per independent reviewer; skip when both `cursor_available` and `codex_available` are false — no voted rounds)
- Total fixes applied across all rounds (diff mode only)
- Build/test status (pass/fail)
- **External reviewer warnings** (repeat any preflight or runtime warnings from Codex/Cursor here so they are visible at the end; also include any Gemini health/probe banners surfaced by `session-setup.sh` even though the Gemini reviewer lane is dormant)

If `SESSION_ENV_PATH` is empty, print `$REVIEW_TMPDIR/review-round-summary.md` verbatim after it exists.

If `SESSION_ENV_PATH` is non-empty AND diff mode is ON, suppress all Step 4 prose and emit only the terminal nested-mode footer:

```text
### review-result
PARSE_STATUS=ok
ROUNDS=<n>
ACCEPTED=<n>
REJECTED=<n>
REVIEW_ROUND_SUMMARY_FILE=<path>
```

Substitute `ROUNDS` with the total diff-mode review rounds completed, `ACCEPTED` with the total accepted in-scope findings across all rounds, `REJECTED` with the total rejected or exonerated in-scope findings across all rounds, and `REVIEW_ROUND_SUMMARY_FILE` with `$(dirname "$SESSION_ENV_PATH")/review-round-summary.md`. Do not print `review-round-summary.md`, voting details, scoreboards, round summaries, breadcrumbs, or explanatory prose in nested diff mode; `/implement` reads the summary artifact directly.

### 4b — Description-mode /umbrella filing (default in description mode; skipped when --no-issues)

If description mode is OFF or `no_issues=true`, skip this sub-step.

Compose a findings batch markdown at `$REVIEW_TMPDIR/findings-batch.md`. Include:
- For each in-scope-accepted finding (2+ YES): a generic `### <terse title>` block with `**Description**`, `**File**`, `**Reviewer**`, `**Focus area**`, `**Problem**`, `**Suggested fix**` body.
- For each OOS-accepted finding (2+ YES, NOT focus-area=security): an OOS schema block per `/issue`'s OOS-format parser:
  ```markdown
  ### OOS_N: <short title>
  - **Description**: <full description; include affected repo-relative file paths and line ranges when applicable>
  - **Reviewer**: <attribution>
  - **Vote tally**: <YES/NO/EXONERATE counts>
  - **Phase**: review
  ```
- **Exclude** any finding tagged `security` — those are handled by Step 4c.

If the batch is empty (zero accepted findings, or all accepted findings were security-tagged), skip the `/umbrella` invocation. Set `ISSUES_CREATED=0`, `ISSUES_DEDUPLICATED=0`, `ISSUES_FAILED=0` for the KV footer.

Otherwise, compose a 1-2 sentence umbrella summary paragraph at `$REVIEW_TMPDIR/umbrella-summary.txt` derived from the review context (description text + accepted-finding count + reviewer attribution summary). The summary becomes the lead paragraph of the umbrella issue body if `/umbrella` produces one (≥2 distinct resolved children). **Apply compose-time sanitization** before writing — the umbrella body becomes a public GitHub issue:

- Strip ASCII control characters (except whitespace `\t`, `\n` is already disallowed by the line grammar).
- Replace newlines and tabs with single spaces; collapse internal whitespace runs to one space.
- Redact secrets / API keys / OAuth / JWT / passwords / certificates → `<REDACTED-TOKEN>`.
- Redact internal hostnames / URLs / private IPs → `<INTERNAL-URL>`.
- Redact PII (emails, account IDs tied to a real user) → `<REDACTED-PII>`.
- Cap at ~200 characters (truncate at a word boundary if longer).

Then invoke `/umbrella` via the Skill tool:

> **Continue after child returns.** When `/umbrella` returns, parse its stdout machine lines per `/umbrella`'s Step 4 emit-output grammar — `UMBRELLA_VERDICT=`, `CHILDREN_CREATED=`, `CHILDREN_DEDUPLICATED=`, `CHILDREN_FAILED=`, `UMBRELLA_NUMBER=`, `UMBRELLA_URL=` (and optional `UMBRELLA_DOWNGRADE=`, `UMBRELLA_FAILURE_REASON=`) — and continue to Step 4c — do NOT end the turn or write a summary. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Anti-halt continuation reminder.

**Compose `pieces.json` for inter-finding dependency edges**: before invoking `/umbrella`, build a `pieces.json` at `$REVIEW_TMPDIR/pieces.json` encoding inter-finding `depends_on` edges derived from file-overlap metadata. For each accepted finding, the `**File**` field names one or more paths. Two findings have a dependency edge when: (a) they share at least one overlapping file path (after canonicalizing paths — strip leading `./`, resolve `..` segments, case-preserve), AND (b) one finding's description or suggested fix explicitly references sequential dependency on the other (e.g., "this requires the refactor in finding N to land first", "depends on the API change above", "must run after the schema migration"). File overlap alone is necessary but NOT sufficient — it indicates potential conflict, not proven dependency. The `depends_on` array for each piece uses 1-based indices matching the batch markdown's `### <title>` order. Write the JSON array to `$REVIEW_TMPDIR/pieces.json` using the Write tool. If no inter-finding dependencies are detected (common case — most review findings are independent), write a JSON array with empty `depends_on` arrays for each entry and still pass `--pieces-json` (the validator accepts all-empty deps).

Skill invocation:
- Try skill `"umbrella"` first (bare name). If no skill matches, try `"larch:umbrella"`.
- args: `--input-file $REVIEW_TMPDIR/findings-batch.md --umbrella-summary-file $REVIEW_TMPDIR/umbrella-summary.txt --pieces-json $REVIEW_TMPDIR/pieces.json`

Do NOT forward `--auto`, `--merge`, or other flags `/umbrella` does not accept.

Parse `/umbrella`'s stdout. Map to the review-result counters (per dialectic DECISION_2 — uniform "any GitHub issue created counts" semantic — see Step 4d below for the footer schema):

- `ISSUES_CREATED` = `CHILDREN_CREATED` + (1 if `UMBRELLA_NUMBER` is non-empty else 0)
- `ISSUES_DEDUPLICATED` = `CHILDREN_DEDUPLICATED`
- `ISSUES_FAILED` = `CHILDREN_FAILED` + (1 if `UMBRELLA_VERDICT=multi-piece` AND `UMBRELLA_NUMBER` is empty AND `CHILDREN_FAILED=0` else 0).

The umbrella-failure structural signal is `UMBRELLA_VERDICT=multi-piece` AND `UMBRELLA_NUMBER` empty AND `CHILDREN_FAILED=0` (umbrella creation was actually attempted and failed). The `CHILDREN_FAILED=0` gate is essential: per `/umbrella`'s Step 3B.2 abort condition (`skills/umbrella/SKILL.md`), when `ISSUES_FAILED >= 1` from the `/issue` batch, `/umbrella` skips Step 3B.3 entirely (umbrella creation never attempted) and emits `UMBRELLA_VERDICT=multi-piece` plus an empty `UMBRELLA_NUMBER`. Without the gate, `/review` would double-count: N child failures plus a phantom +1 for an umbrella that was never attempted. We do NOT key off `UMBRELLA_FAILURE_REASON` presence — `/umbrella` documents that field as optional even on real umbrella-create failures. Save the mapped counters for the KV footer at Step 4d.

Print an informational line summarizing the outcome (above the KV footer): `filed N children + umbrella #M (<url>)` (when umbrella created), `filed N child issue(s)` (one-shot path), `all findings deduped to existing issues` (downgrade), or omit (empty batch).

### 4c — Write security findings (description mode only)

If description mode is ON, collect any accepted security-tagged findings (focus-area=security; both in-scope-accepted and OOS-accepted with 2+ YES). Write them verbatim to `$REVIEW_TMPDIR/security-findings.md` (printed verbatim to terminal before tmpdir cleanup). Security-tagged findings are NEVER filed publicly via `/umbrella` or `/issue` (per SECURITY.md).

Format each entry:
```markdown
### <focus-area=security> — <short title>
- **File**: <path:line>
- **Reviewer(s)**: <attribution>
- **Vote tally**: <YES/NO/EXONERATE>
- **Concern**: <full description>
- **Suggested fix**: <full text>
```

Set `SECURITY_FINDINGS_HELD` = number of entries written. After writing, IMMEDIATELY continue to the terminal print and then Step 4d — do NOT halt after writing the file.

Print the file's contents verbatim to terminal under a clearly-labeled block:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Security-tagged findings (held locally per SECURITY.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<contents of security-findings.md>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then print: `**⚠ Handle these findings per SECURITY.md's vulnerability-disclosure procedure. They are NOT filed as public GitHub issues.**` IMMEDIATELY continue to Step 4d — do NOT halt after the security warning.

> **Continue to Step 4d IMMEDIATELY.** Security-findings output is not terminal — the description-mode KV footer still must be emitted.

### 4d — Description-mode KV footer (description mode only)

Print the `### review-result` KV footer immediately before exiting Step 4.

```
### review-result
ISSUES_CREATED=<n>
ISSUES_DEDUPLICATED=<n>
ISSUES_FAILED=<n>
SECURITY_FINDINGS_HELD=<n>
PARSE_STATUS=ok
```

Substitute `ISSUES_CREATED`, `ISSUES_DEDUPLICATED`, `ISSUES_FAILED` from Step 4b (or zero each if Step 4b was skipped — i.e., `no_issues=true` or the findings batch was empty). Substitute `SECURITY_FINDINGS_HELD` from Step 4c independently (zero only if Step 4c found no security findings — Step 4c always runs in description mode regardless of whether Step 4b ran). `PARSE_STATUS=ok` always (any error path emits a different `PARSE_STATUS` value or aborts before reaching here). After printing the KV footer, IMMEDIATELY continue to Step 5 (Cleanup) — do NOT halt after the footer.

> **Continue to Step 5 IMMEDIATELY.** The review-result footer is not terminal — cleanup still must run.

## Step 5 — Cleanup

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 5 — cleanup" || true
```

### 5a — Update Health Status File

Health status file updates are handled automatically by `collect-agent-results.sh --write-health` during reviewer collection (Step 3a). No additional cleanup-time write is needed unless a reviewer was marked unhealthy outside of a `collect-agent-results.sh` call. If `SESSION_ENV_PATH` is non-empty and any such untracked health change occurred, re-write the health status file at `${SESSION_ENV_PATH}.health` with the final health state before cleanup.

If running under `/implement` (`SESSION_ENV_PATH` is non-empty and its directory is `$IMPLEMENT_TMPDIR`), aggregate launcher dirty markers before cleanup into `$IMPLEMENT_TMPDIR/review-dirty-tree-summary.env` with stable keys: `ANY_DIRTY=true|false|unknown`, `LAUNCHERS_DIRTY=<comma-list>`, and `RECOVERY_TAKEN=true|false`. Write this before deleting `$REVIEW_TMPDIR` so `/implement` Step 5 can backstop any unhandled dirty/unknown signal.

**Path-stream preservation** (added per round-2 finding R2_6 — addresses the gap where `/implement` Step 5's scoped recovery referenced `TRACKED_PATHS_FILE` and `NEW_UNTRACKED_PATHS_FILE` sidecars that lived under `$REVIEW_TMPDIR` and were destroyed by Step 5b's cleanup before `/implement` could read them). Before deleting `$REVIEW_TMPDIR`, when `ANY_DIRTY=true` or `ANY_DIRTY=unknown` AND `RECOVERY_TAKEN=false`, copy each launcher's `${OUTPUT}.dirty-tree` sidecar plus the referenced `TRACKED_PATHS_FILE` and `NEW_UNTRACKED_PATHS_FILE` (when present and non-empty) into a stable subdirectory `$IMPLEMENT_TMPDIR/review-dirty-tree-streams/` (atomic copy via `cp -p` is sufficient — these are NUL-delimited path streams, not source-of-truth git state). Then append a per-launcher `LAUNCHER_<n>_TRACKED_PATHS_FILE=<absolute-path-under-IMPLEMENT_TMPDIR>` and `LAUNCHER_<n>_NEW_UNTRACKED_PATHS_FILE=<absolute-path>` line to `review-dirty-tree-summary.env` for every launcher in `LAUNCHERS_DIRTY` so `/implement`'s scoped recovery can reach them. When `RECOVERY_TAKEN=true` (auto-discard already completed inside `/review`), path-stream preservation is skipped — recovery happened against the live tree and the streams are no longer needed. When `ANY_DIRTY=false`, no preservation is needed.

### 5b — Remove Temp Directory

Remove the session temp directory and all files within it:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-tmpdir.sh --dir "$REVIEW_TMPDIR"
```
