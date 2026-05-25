# Voting Protocol

Shared voting protocol for adjudicating review findings. Used by `/design` (plan review) and `/review` (code review). This protocol **replaces** the Negotiation Protocol for `/design` and `/review`. `/research` continues using the Negotiation Protocol in `external-reviewers.md`.

## Overview

After reviewers submit findings and findings are deduplicated, a voting panel votes YES/NO/EXONERATE on each finding. Both `/design` (plan review) and `/review` (code review) normally use a 3-voter panel (Claude + Codex + Cursor); findings with 2+ YES votes are accepted in the full tier. When voters are unavailable, the panel degrades through the tier table below and never fails open. `/review` voter dispatch is owned by `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh`; vote tally is owned by `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-code-votes.sh`. Original reviewers earn competition points based on how their findings perform in voting. EXONERATE is a third option meaning "legitimate concern, but not worth implementing in this PR" — it spares the proposing reviewer from losing a point.

## Ballot Format

Before sending to voters, assign each deduplicated finding a stable sequential ID. The ballot file uses `### FINDING_N:` markdown heading blocks — one block per finding. For `/design` plan review, `tally-plan-review.sh` also splits `### OOS_N:` blocks; for `/review` code review, `ballot-parse.sh` exports per-finding fields from `### FINDING_N:` blocks only:

```markdown
### FINDING_1: <short title>
- **Reviewer**: <reviewer attribution>
- **Concern**: <finding description>
- **Suggested revision**: <what to change>

### FINDING_2: <short title>
- **Reviewer**: <reviewer attribution>
- **Concern**: <finding description>
- **Suggested revision**: <what to change>
```

Prepend the voter instructions as free prose before the first `### FINDING_N:` block (they are ignored by the parsers). Include the reviewer attribution so voters have context, but instruct voters to evaluate each finding on its merits regardless of who proposed it. Attribution labels are skill-specific: `/design` uses `Code` / `Codex` / `Cursor` (3-reviewer panel); `/review` uses specialist labels (`Structure`, `Correctness`, `Testing`, `Security`, `Edge-cases`, `Plan-fidelity`, `Codex-Structure`, `Codex-Correctness`, `Codex-Testing`, `Codex-Security`, `Codex-Edge-cases`, `Codex-Plan-fidelity`) for its hard panel. Simple panels add `Claude-Generic` and use a reduced external-specialist set. `/research` does not participate in voting — it uses the Negotiation Protocol instead.

## Voter Output Format

Each voter must output one line per ballot item, **using the same ID that appears on the ballot heading for this run**. The ID form depends on the skill:

- **`/design` plan review**: in-scope headings are `### FINDING_N:`, OOS headings are `### OOS_N:` — vote lines use `FINDING_N:` and `OOS_N:` respectively.
- **`/review` code review**: all headings (including OOS-tagged ones) are `### FINDING_N:` — vote lines always use `FINDING_N:`, even for `[OUT_OF_SCOPE]` rows. `tally-vote.sh` only matches `FINDING_<n>` patterns; `OOS_N:` lines are ignored.

YES votes require no reason; NO and EXONERATE votes require a one-line reason:

```
FINDING_1: YES
FINDING_2: NO — <one-line reason>
FINDING_3: EXONERATE — <one-line reason>
OOS_1: YES
OOS_2: NO — <one-line reason>
OOS_3: EXONERATE — <one-line reason>
...
```

Valid vote tokens are `YES`, `NO`, and `EXONERATE`. If a voter's output contains valid votes for some findings but is missing votes for others, use the valid votes; missing ballot entries produce `JUDGE_ERROR` at the per-voter level (parser fallback). `JUDGE_ERROR` does not reduce the panel tier; the quorum basis is the number of available voter files for the round.

## Threshold Rules

| Eligible Voters | YES Votes Required | Notes |
|---|---|---|
| 3 | 2+ | Standard majority |
| 2 | 2 (unanimous) | When one voter unavailable/timed out |
| 1 | 1 | Binding single-judge decision; YES accepts, EXONERATE exonerates for scoring, NO rejects |
| 0 | Main agent decides | No automated vote; main agent reads ballot as untrusted data and adjudicates |

Dispatchers emit degraded-panel warnings when effective voters drop below the expected panel size. `effective` means status is not `failed` and the voter output is substantive enough to contribute valid vote lines after any retry path settles.

After the acceptance threshold, each finding is classified into **operator-facing outcomes** `accepted`, `rejected`, or informational **`exonerated` as a subset of `rejected`** (every exonerated finding is also counted in the rejected total). The underlying vote-pattern classifier in `scripts/lib-vote-tally.sh::classify_result` still uses internal labels for scoreboard math; tally scripts map those labels to KV and JSON at the emission boundary.

Non-accepted tie-breaks (after the acceptance-threshold check fails), in order:

- `YES > 0` and `YES == NO` → **rejected** for reporting; scoreboard treats this as a **split-panel** pattern (0 points to the proposing reviewer — at least one YES, but the panel did not clear NO).
- Otherwise, when `EXONERATE > 0` **and** `YES > 0` **and** `NO == 0` → **rejected** with informational **exonerated** sub-count (0 points — legitimate concern, not actionable in this PR).
- All remaining cases → **rejected** (including all-exonerate panels with `YES == 0` and mixed `NO`/`EXONERATE` panels such as `0Y/1N/1E`; scoreboard may assign −1 when `YES == 0` per the points table below).

## Voter Panel Composition

**For plan review** (`/design` Step 3):
- **Voter 1**: Claude Code Reviewer subagent — launched as a fresh Agent tool invocation (subagent_type: `larch:code-reviewer`) with a focused voting prompt (separate from the reviewer subagents)
- **Voter 2**: Codex — via `run-external-agent.sh`
- **Voter 3**: Cursor — via `run-external-agent.sh`

**For code review** (`/review` Step 3) — `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh` launches all three voters every round:
- **Voter 1**: Claude opus — via `launch-claude-subprocess.sh --model claude-opus-4-7` (always launched)
- **Voter 2**: Codex — via `run-external-agent.sh`. When `codex-available=false`, a Claude voter is launched in its place (`VOTER_2_STATUS=fallback`, `VOTER_2_TOOL=claude`).
- **Voter 3**: Cursor — via `run-external-agent.sh`. When `cursor-available=false`, a Claude voter is launched in its place (`VOTER_3_STATUS=fallback`, `VOTER_3_TOOL=claude`).

All voters vote on **all** findings — no self-voting exclusion. Voters are instructed to evaluate each finding objectively regardless of who proposed it.

## Voter Prompt Template

Customize the `{VOTER_ROLE}` and `{REVIEW_CONTEXT}` per skill:

<!-- OOS voter rubric: canonical text is emitted at runtime by skills/shared/scripts/render-voter-prompt.sh. Keep the following paragraph in sync with skills/design/SKILL.md (Step 3 MAV), skills/implement/SKILL.md (Step 5 MAV), and skills/design/references/plan-review.md (Voter 1); scripts/test-render-voter-prompt.sh greps the shared substring across all four. -->

For items prefixed with `[OUT_OF_SCOPE]`: vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy.

```
You are a {VOTER_ROLE} participating in a voting panel. You will be presented with a list of proposed changes to {REVIEW_CONTEXT}. For each finding, vote YES, NO, or EXONERATE:
- **YES**: The finding is correct, important, and worth implementing.
- **NO**: The finding is incorrect, trivial, duplicative, or would cause more harm than good.
- **EXONERATE**: The finding raises a legitimate concern worth noting, but is not worth implementing in this PR. This spares the proposing reviewer from a penalty on in-scope findings.

Be scrupulous — only vote YES for findings that genuinely improve the {REVIEW_CONTEXT}. Use EXONERATE when a concern is valid but not actionable now.

**OOS / `[OUT_OF_SCOPE]` / plan `OOS_N:` rows:** Runtime prompts use `skills/shared/scripts/render-voter-prompt.sh` for grammar-specific OOS wording (see the prose paragraph immediately above this fenced template for the canonical lowest-common-denominator clause). In this template's structural shape: YES files a GitHub issue for future tracking; NO means trivial/incorrect; EXONERATE means legitimate but not issue-worthy. OOS items are never implemented in this PR — YES means "file an issue," not "implement now." Vote YES only when the observation is concrete and important enough to justify a durable GitHub issue (typical signals: specific file:line or a reproducible failure mode); use EXONERATE for legitimate concerns that are not issue-worthy, and NO for trivial or incorrect observations.

{BALLOT}

For each ballot item, output exactly one line using the same ID from the ballot heading:
FINDING_N: YES
or
FINDING_N: NO — <one-line reason>
or
FINDING_N: EXONERATE — <one-line reason>
or
OOS_N: YES
or
OOS_N: NO — <one-line reason>
or
OOS_N: EXONERATE — <one-line reason>

Note: for /review code review, all rows (including [OUT_OF_SCOPE] ones) use FINDING_N: vote lines since the ballot only contains ### FINDING_N: headings.

You must vote on every item. Do NOT skip any. Do NOT modify files.
```

## Launching Voters

**For `/design` plan review**: call `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-plan-voters.sh` for Voter 2 (Codex) and Voter 3 (Cursor), then launch Voter 1 and any Claude replacement voters indicated by `VOTER_2_STATUS=fallback` / `VOTER_3_STATUS=fallback`. The dispatcher launches available external voters in parallel, waits for sentinels, and emits the external output paths. When external tools are unavailable, launch Claude replacement voters instead so the total voter count always remains 3.

**For code review**: `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh` launches Claude (always), Codex (when available), and Cursor (when available) in parallel; when an external is unhealthy a Claude replacement fills the slot. The orchestrator does not invoke voters directly — `review-core.sh` calls the dispatch script.

**Generic Cursor voter argv contract** (mirrored by `dispatch-plan-voters.sh` for `/design`; use the skill-specific launch instructions before copying this block):

```bash
# Build the conditional --api-key argv segment via the shared helper. Empty
# when CURSOR_API_KEY is unset/whitespace-only (preserves cursor login
# fallback); two elements (--api-key "$KEY") when set.
# Use a temp file (NOT process substitution) so a non-zero exit from
# agent-model-args.sh — e.g., LARCH_CURSOR_MODEL contains [[:cntrl:]] or is
# blank — propagates and aborts the launch, instead of being swallowed and
# producing an empty MODEL_ARGS array. The defensive `${ARR[@]+"${ARR[@]}"}`
# expansion is required for Bash 3.2 compatibility under `set -u`.
CURSOR_AUTH_FLAGS=()
while IFS= read -r line; do CURSOR_AUTH_FLAGS+=("$line"); done < <("${CLAUDE_PLUGIN_ROOT}/scripts/cursor-auth-flags.sh")
CURSOR_MODEL_ARGS_TMP=$(mktemp)
trap 'rm -f "$CURSOR_MODEL_ARGS_TMP"' EXIT
"${CLAUDE_PLUGIN_ROOT}/scripts/agent-model-args.sh" --tool cursor --with-effort > "$CURSOR_MODEL_ARGS_TMP" || exit $?
CURSOR_MODEL_ARGS=()
while IFS= read -r arg; do CURSOR_MODEL_ARGS+=("$arg"); done < "$CURSOR_MODEL_ARGS_TMP"

${CLAUDE_PLUGIN_ROOT}/scripts/run-external-agent.sh --tool cursor --output "<tmpdir>/cursor-vote-output.txt" --timeout 1200 --capture-stdout -- \
  cursor agent -p --trust --mode plan ${CURSOR_MODEL_ARGS[@]+"${CURSOR_MODEL_ARGS[@]}"} ${CURSOR_AUTH_FLAGS[@]+"${CURSOR_AUTH_FLAGS[@]}"} --workspace "$PWD" \
    "$("${CLAUDE_PLUGIN_ROOT}/scripts/cursor-wrap-prompt.sh" "<voter prompt with ballot>.")"
```

Use `run_in_background: true` and `timeout: 1260000` only for skill-specific direct-launch paths. `/design` plan review gets this behavior from `dispatch-plan-voters.sh`.

**Cursor voter replacement** (plan review and code review; if `cursor_available` is false): Launch a Claude voter in its place. For plan review this happens via the Agent tool; for code review `dispatch-code-voters.sh` launches a Claude subprocess automatically. The total voter count always remains 3.

**Generic Codex voter argv contract** (mirrored by `dispatch-plan-voters.sh` for `/design`; use the skill-specific launch instructions before copying this block):

```bash
# Same temp-file pattern as the Cursor block above — propagate
# agent-model-args.sh failures and use the Bash 3.2-safe expansion.
CODEX_MODEL_ARGS_TMP=$(mktemp)
trap 'rm -f "$CODEX_MODEL_ARGS_TMP"' EXIT
"${CLAUDE_PLUGIN_ROOT}/scripts/agent-model-args.sh" --tool codex --with-effort > "$CODEX_MODEL_ARGS_TMP" || exit $?
CODEX_MODEL_ARGS=()
while IFS= read -r arg; do CODEX_MODEL_ARGS+=("$arg"); done < "$CODEX_MODEL_ARGS_TMP"

${CLAUDE_PLUGIN_ROOT}/scripts/run-external-agent.sh --tool codex --output "<tmpdir>/codex-vote-output.txt" --timeout 1200 -- \
  codex exec --sandbox read-only -C "$PWD" ${CODEX_MODEL_ARGS[@]+"${CODEX_MODEL_ARGS[@]}"} \
    --output-last-message "<tmpdir>/codex-vote-output.txt" \
    "<voter prompt with ballot>."
```

Use `run_in_background: true` and `timeout: 1260000` only for skill-specific direct-launch paths. `/design` plan review gets this behavior from `dispatch-plan-voters.sh`.

**Codex voter replacement** (plan review and code review; if `codex_available` is false): Launch a Claude voter in its place. For plan review this happens via the Agent tool; for code review `dispatch-code-voters.sh` launches a Claude subprocess automatically. The total voter count always remains 3.

**Claude voter**: Launch via Agent tool with the voter prompt.

Wait for external voter sentinels using `wait-for-reviewers.sh` (use the same tmpdir as the review phase — do not create a new temp directory for voting). Only include sentinel paths for voters that were actually launched:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-reviewers.sh --timeout 1260 \
  "<tmpdir>/cursor-vote-output.txt.done" \
  "<tmpdir>/codex-vote-output.txt.done"
```

Use `timeout: 1260000` on the Bash tool call. Set `run_in_background: true` on the long-script Bash tool call and pair with foreground `breadcrumb-monitor.sh`. Note: voter output files use the `-vote-` infix to avoid collision with reviewer output files (`-plan-output` or `-output`).

**Collecting voter results**: Use `collect-agent-results.sh` to validate external voter outputs (same as for reviewer outputs). Parse `STATUS` and `FAILURE_REASON` for each voter. If a voter fails (`STATUS != OK`), print: `**⚠ <Voter> voter failed — <FAILURE_REASON>. Proceeding with <N> voters (<remaining voter names>).**` Always include the `FAILURE_REASON` so the user can see why the voter failed (e.g., timeout, crash, empty output). Reduce the eligible voter count accordingly and apply the threshold rules above.

## Competition Scoring

After tallying votes, compute a score for each **original reviewer** (not voters):

| Vote pattern (non-accepted) | Points | Description |
|---|---|---|
| Finding accepted (2+ YES) | +1 | Reviewer's finding was validated by the panel |
| Rejected with split-panel pattern (exactly 1 YES and YES == NO) | 0 | Panel disagreement — not enough support to accept, but not a unanimous dismissal |
| Rejected with exonerated pattern (YES > 0, NO == 0, 1+ EXONERATE) | 0 | Legitimate concern, not actionable now |
| Rejected with dismissed pattern (0 YES and 0 EXONERATE among counted votes) | −1 | Finding was unanimously dismissed by the panel |

If a deduplicated finding was proposed by multiple reviewers (merged during deduplication), **all** contributing reviewers receive the same points for that finding.

## Scoreboard

After voting, print the scoreboard. Branch on `SESSION_ENV_PATH`:

- **When `SESSION_ENV_PATH` is empty (standalone run)**: print the full scoreboard table to the session.
- **When `SESSION_ENV_PATH` is non-empty (nested run under `/implement`)**: print only a one-line count summary of the form `Round <N>: <A> accepted, <R> rejected (<E> exonerated)` (in-scope findings only; `E` counts the exonerated subset and is always `≤ R`). The full scoreboard is suppressed at all levels in nested mode — per-round printing here and the Step 4a final summary (both inline and via `review-round-summary.md` in subagent runs).

Full scoreboard format (used in standalone mode):

```
## Reviewer Competition Scoreboard

| Reviewer | Findings | Accepted | Exonerated | Rejected | OOS Proposed | OOS Accepted | OOS-Exonerated | OOS-Rejected | Score |
|----------|----------|----------|--------|----------|--------------|--------------|----------------|--------------|-------|
| _label1_ | 3        | 2        | 1      | 0        | 1            | 0            | 1              | 0            | +2    |
| _label2_ | 2        | 1        | 1      | 0        | 0            | 0            | 0              | 0            | +1    |
| _label3_ | 2        | 1        | 1      | 1        | 1            | 0            | 0              | 1            | 0     |
```

The **Exonerated** column counts all non-accepted findings that award **0** points to the proposer (split-panel and exonerated vote patterns). The **Rejected** column counts non-accepted findings that cost **−1** point (dismissed vote pattern). A single finding is counted in **at most one** of these two columns.

Attribution labels are skill-specific (e.g., `/design` uses `Code`/`Codex`/`Cursor`; `/review` hard panel uses `Structure`/`Correctness`/`Testing`/`Security`/`Edge-cases`/`Plan-fidelity`/`Codex-Structure`/`Codex-Correctness`/`Codex-Testing`/`Codex-Security`/`Codex-Edge-cases`/`Codex-Plan-fidelity`). One row per independent reviewer. In future iterations, token allocation will be weighted proportionally to reviewer scores.

## Out-of-Scope Observations

Reviewers may return a second list of **out-of-scope observations** — pre-existing issues or concerns beyond the PR's scope that are worth surfacing for future attention. These are handled alongside in-scope findings but with different semantics:

### OOS on the Ballot

The ballot format for OOS items depends on the skill:

- **`/design` plan review** (`tally-plan-review.sh`): OOS items get `OOS_` prefixed IDs (e.g., `OOS_1`, `OOS_2`) and appear as `### OOS_N:` heading blocks on the ballot:

  ```markdown
  ### OOS_1: <short title of pre-existing issue>
  - **Reviewer**: <reviewer attribution>
  - **Concern**: <description of pre-existing issue>
  ```

- **`/review` code review** (`ballot-parse.sh` / `tally-vote.sh`): `collect-findings.sh` writes OOS items using sequential `FINDING_N` IDs with `[OUT_OF_SCOPE]` (or `[OOS]`) in the title (e.g., `### FINDING_N: [OUT_OF_SCOPE] <title>`). Voters vote with `FINDING_N:` lines, not `OOS_N:` lines — `tally-vote.sh` only matches `FINDING_<n>` patterns.

### OOS Vote Semantics

For out-of-scope items, the vote meanings are:
- **YES**: This observation deserves a GitHub issue for future attention.
- **NO**: Not worth tracking — the observation is trivial or incorrect.
- **EXONERATE**: Legitimate observation worth documenting, but not worth filing a GitHub issue.

If an OOS item receives 2+ YES votes, it is **accepted** and will be filed as a GitHub issue by `/implement` Step 9a.1 (`/issue` batch mode). In `/review` description mode, accepted OOS items are recorded in local artifacts for the operator to file manually via `/issue` (no automatic filing in this mode). Otherwise it remains an observation reported in the PR body.

**OOS items are never implemented in the current PR** — accepted OOS items result in issue creation only. This cleanly separates "fix now" (in-scope findings) from "fix later" (OOS observations).

### OOS Scoring

Out-of-scope items use the same score shape as in-scope findings: accepted OOS earns +1, non-accepted OOS with a split-panel or exonerated vote pattern scores 0, and dismissed OOS costs −1:

| OOS vote pattern | Points | Description |
|---|---|---|
| OOS accepted (2+ YES) | +1 | Reviewer surfaced an issue worth tracking |
| OOS rejected — split panel (exactly 1 YES and YES == NO) | 0 | Insufficient support, but not dismissed |
| OOS rejected — exonerated pattern (0 YES, 1+ EXONERATE) | 0 | Legitimate observation, but not worth an issue |
| OOS rejected — dismissed (0 YES, 0 EXONERATE) | −1 | Observation was unanimously dismissed by the panel |

### OOS Scoreboard

The scoreboard includes additional columns for OOS items:

```
| Reviewer | ... | OOS Proposed | OOS Accepted | OOS-Exonerated | OOS-Rejected | ...
```

### OOS Security Tag

Accepted OOS items can be tagged as **security findings** that are held locally and never filed as public GitHub issues. The detection contract is shared between `/design` plan review (`tally-plan-review.sh`) and `/review` code review (`tally-code-votes.sh`) via `scripts/lib-vote-tally.sh::is_security_block`:

- **Canonical token**: a block is security-tagged when its body contains at least one **unfenced** occurrence of `focus-area\s*=\s*security` (case-insensitive, optional whitespace around `=`).
- **Match discrimination (false-positive guard)**: occurrences inside backtick or triple-backtick regions are fenced and do not count — only unfenced occurrences mark a finding as security-tagged.
- **Security counter-invariant**: a real security finding MUST include at least one unfenced occurrence of the canonical token; otherwise it will not be held locally.
- Accepted OOS items where the block matches are written ONLY to the local `oos-accepted-*.md` artifact and to the local-only artifact path; security-tagged findings (focus-area=security) are held locally and NEVER filed publicly — the canonical filing pipeline (`/implement` Step 9a.1 → `/issue` batch mode) is skipped for them.

### OOS Reporting

OOS items are **not** written to `rejected-findings.md`. They follow a separate pipeline:

- **Accepted OOS items — reviewer voting path** (2+ YES): Plan-review OOS accepted by the `/design` panel is written to `$DESIGN_TMPDIR/oos-accepted-design.md` (and visibility text to `$DESIGN_TMPDIR/oos.md`) during `/design` Step 3 tally/finalize. Code-review OOS accepted by the `/review` panel is written to `$REVIEW_TMPDIR/oos-accepted-review.md` during review tally; `review-core.sh` mirrors a copy at `$IMPLEMENT_TMPDIR/oos-accepted-review.md` for `/implement` Step 9a.1 and disposition gates.
- **Accepted OOS items — main-agent dual-write path** (no vote required): Written to `oos-accepted-main-agent.md` in `$IMPLEMENT_TMPDIR` by the main agent at discovery time, every time it logs a `Pre-existing Code Issues` entry to `execution-issues.md`. This is the mechanical enforcement of `/implement`'s Follow-up Work Principle for the `Pre-existing Code Issues` category — see `/implement` SKILL.md → "Follow-up Work Principle" and "Mechanical enforcement of the principle: `Pre-existing Code Issues` dual-write". Durable follow-up work outside that category is not auto-filed via this path — the main agent files it manually via `/issue` per the principle. This path is unconditional and runs in every mode (`--quick`, `--merge`, `--draft`, `--no-merge`, or any future flag). It does NOT pass through a voting panel — main-agent classification is the policy gate.
- **Unified filing**: `/implement` Step 9a.1 reads accepted OOS from the main-agent artifact, the plan-review artifact (`$DESIGN_TMPDIR/oos-accepted-design.md` when `/design` ran in-session, with implement-local fallbacks documented in `/implement` SKILL.md for disposition gates and ship-pr), and `$IMPLEMENT_TMPDIR/oos-accepted-review.md`, deduplicates across phases, and creates GitHub issues via `/issue` (batch mode) with LLM-based semantic duplicate detection against open + recently-closed GitHub issues. All three artifacts share the same `### OOS_N:` schema (Description, Reviewer, Vote tally, Phase). Main-agent items use Reviewer=`Main agent`, Vote tally=`N/A — auto-filed per policy`, Phase=`implement`.
- **Non-accepted OOS items**: Collected and reported in a dedicated `<details><summary>Out-of-Scope Observations</summary>` section in the PR body for future reference.

External reviewers **in diff mode** differ by slot type. **Specialist external slots** (Cursor and Codex specialists loaded from `agents/reviewer-*.md`) use dual-list output (with `### In-Scope Findings` and `### Out-of-Scope Observations` section headers) and can contribute OOS items via voting. **In `/review` description mode**, all external reviewers produce dual-list output matching the Claude subagent contract and contribute OOS observations via voting — see `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` Step 3a. Claude subagent reviewers (which use the dual-list templates from `reviewer-templates.md`) produce OOS items via voting in both modes; the main agent's dual-write path produces OOS items without voting.

## Zero Accepted Findings

If voting filters out **all** in-scope findings (every in-scope finding rejected by the panel), print: `**ℹ Voting panel rejected all in-scope findings. No changes to implement.**` and skip the implementation/revision step. Proceed directly to the rejected findings report. (OOS items accepted for issue filing are processed separately — by `/implement` Step 9a.1 — and do not count as implementation work.)
