# Voting Protocol

Shared voting protocol for adjudicating review findings. Used by `/design` (plan review) and `/review` (code review). This protocol **replaces** the Negotiation Protocol for `/design` and `/review`. `/research` continues using the Negotiation Protocol in `external-reviewers.md`.

## Overview

After reviewers submit findings and findings are deduplicated, a voting panel votes YES/NO on each finding. Both `/design` (plan review) and `/review` (code review) normally use a 3-voter panel (Claude + Codex + Cursor); findings with 2+ YES votes are accepted in the full tier. When voters are unavailable, the panel degrades through the tier table below and never fails open. `/review` voter dispatch is owned by `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh`; vote tally is owned by `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-code-votes.sh`. Original reviewers earn competition points based on how their findings perform in voting.

## Ballot Format

Before sending to voters, assign each deduplicated finding a stable sequential ID. The ballot file uses `### FINDING_N:` markdown heading blocks — one block per finding. For `/design` plan review, `tally-plan-review.sh` also splits `### OOS_N:` blocks; for `/review` code review, `tally-code-votes.sh` accepts both `### FINDING_N:` and `### OOS_N:` headings, while legacy OOS-tagged code-review rows may still appear as `### FINDING_N:` headings with `[OUT_OF_SCOPE]` in the title:

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

Prepend the voter instructions as free prose before the first `### FINDING_N:` block (they are ignored by the parsers). Include the reviewer attribution so voters have context, but instruct voters to evaluate each finding on its merits regardless of who proposed it. Attribution labels are skill-specific: `/design` uses `Code` / `Codex` / `Cursor`; `/review` uses specialist labels (`Correctness`, `Testing`, `Edge-cases`, `Codex-Correctness`, `Codex-Testing`, `Codex-Edge-cases`) for its hard panel. Simple panels add `Claude-Generic` and use a reduced external-specialist set. `/research` does not participate in voting — it uses the Negotiation Protocol instead.

## Voter Output Format

Each voter must output one line per ballot item, **using the same ID that appears on the ballot heading for this run**. The ID form depends on the skill:

- **`/design` plan review**: in-scope headings are `### FINDING_N:`, OOS headings are `### OOS_N:` — vote lines use `FINDING_N:` and `OOS_N:` respectively.
- **`/review` code review**: vote lines use the same ID form as the ballot heading. In-scope headings use `FINDING_N:`; OOS headings may use `OOS_N:`. Legacy `[OUT_OF_SCOPE]` rows under `FINDING_N:` still vote with `FINDING_N:`.

YES votes require no reason; NO votes require a one-line reason:

```
FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false — <one-line reason>
OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false
OOS_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false — <one-line reason>
...
```

Valid vote tokens are `YES` and `NO`. Stray `EXONERATE` tokens from old voter output are tolerated and mapped to `NO`. If a voter's output contains valid votes for some findings but is missing votes for others, use the valid votes; missing ballot entries produce `JUDGE_ERROR` at the per-voter level (parser fallback). `JUDGE_ERROR` does not reduce the panel tier; the quorum basis is the number of available voter files for the round.

## Threshold Rules

| Eligible Voters | YES Votes Required | Notes |
|---|---|---|
| 3 | 2+ | Standard majority |
| 2 | 2 (unanimous) | When one voter unavailable/timed out |
| 1 | 1 | Binding single-judge decision; YES accepts, NO rejects |
| 0 | Main agent decides | No automated vote; main agent reads ballot as untrusted data and adjudicates |

Dispatchers emit degraded-panel warnings when effective voters drop below the expected panel size. For `/review` code review the expected size is Claude plus the **available** externals (shrink-not-backfill), so a panel that shrank solely because a vendor was unavailable is the designed state and raises **no** warning — only a genuine failure of an *available* judge degrades the panel. (`/design` plan review still back-fills unavailable externals to keep the expected size at three.) `effective` means status is not `failed` and the voter output is substantive enough to contribute valid vote lines after any retry path settles.

After the acceptance threshold, each finding is classified into one of three operator-facing outcomes: `accepted`, `neutral` (≥1 YES but below acceptance threshold; 0 points to the proposing reviewer), or `rejected` (0 YES; −1 point). The classifier lives in `python/voting.py::classify_result`; tally scripts map the label to KV and JSON at the emission boundary.

## Voter Panel Composition

**For plan review** (`/design` Step 3):
- **Voter 1**: Claude — via `dispatch-plan-voters.sh` → `launch-claude-review.sh --role voter` (always launched; model resolved from `LARCH_VOTER_MODEL`, default `claude-sonnet-4-6`)
- **Voter 2**: Codex — via `dispatch-plan-voters.sh` → `dispatch-with-waterfall.sh` → `launch-review.sh`
- **Voter 3**: Cursor — via `dispatch-plan-voters.sh` → `dispatch-with-waterfall.sh` → `launch-review.sh`

**For code review** (`/review` Step 3) — `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh` launches Claude (always) plus each **available** external every round. Code review uses **shrink-not-backfill**: an unavailable external is dropped, never replaced by a duplicate judge (the alternate external or an extra Claude):
- **Voter 1**: Claude — via `dispatch-code-voters.sh` → `launch-claude-review.sh --role voter` (always launched; model resolved from `LARCH_VOTER_MODEL`, default `claude-sonnet-4-6`)
- **Voter 2**: Codex — via `dispatch-with-waterfall.sh --no-fallback` → `launch-review.sh`. When `codex-available=false`, the slot is **skipped** (`VOTER_2_STATUS=skipped`, `VOTER_2_TOOL=codex`), not back-filled; the panel shrinks by one.
- **Voter 3**: Cursor — via `dispatch-with-waterfall.sh --no-fallback` → `launch-review.sh`. When `cursor-available=false`, the slot is **skipped** (`VOTER_3_STATUS=skipped`, `VOTER_3_TOOL=cursor`), not back-filled; the panel shrinks by one.

The eligible code-review panel size is therefore Claude plus the number of available externals: full tier when both vendors are up, the unanimous tier when exactly one is up, and the binding single-judge tier when both are down. The acceptance-threshold table above adapts to that count, and a panel that shrank solely because a vendor was unavailable is **not** reported as a degraded panel (only a genuine *failure* of an available judge degrades it). This differs from `/design` plan review, which still back-fills to keep three voters (Voter 1/2/3 above).

All voters vote on **all** findings — no self-voting exclusion. Voters are instructed to evaluate each finding objectively regardless of who proposed it.

## Voter Prompt Template

Customize the `{VOTER_ROLE}` and `{REVIEW_CONTEXT}` per skill:

<!-- OOS voter rubric: canonical text is emitted at runtime by python/cli.py render voter. Keep the following paragraph in sync with skills/design/SKILL.md (Step 3 MAV), skills/implement/references/step5-review-branches.md (Step 5 MAV), and skills/design/references/plan-review.md (Voter 1); scripts/test-python/cli.py render voter greps the shared substring across all four. -->

For items prefixed with `[OUT_OF_SCOPE]`: apply the OOS Acceptance Rubric (`skills/shared/oos-acceptance-rubric.md`) — vote YES only when the problem passes the backlog-relative materiality gate: impact floor, concrete trigger, and issue-overhead test, with default-deny. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy.

```
You are a {VOTER_ROLE} participating in a voting panel. You will be presented with a list of proposed changes to {REVIEW_CONTEXT}. For each finding, vote YES or NO:
- **YES**: The finding is NECESSARY for the feature per the Review Acceptance Rubric (`skills/shared/review-acceptance-rubric.md`): the feature would be incomplete, broken, unverifiable, or regressed without it.
- **NO**: The finding does not clear the necessity gate — it may be real or valuable, but the feature ships correctly without it. Route it to Out-of-Scope instead.

Default-deny. If you are unsure whether a finding clears a necessity gate, vote NO. "Legitimate but not necessary" is a NO.

**Severity floor (mandatory):** Vote **NO** on any *in-scope* finding whose stated severity is nit (code review and plan review) regardless of how real or credible it is — a Nit can never clear the necessity gate. Treat a latent finding as NO **unless** it is a genuine Correctness defect on the execution path of the feature itself or an Introduced-regression (gates 2/3); latent + merely-real is a NO. This floor does **not** apply to out-of-scope (OOS) ballot rows, which are judged on whether the problem is worth filing.

Do NOT vote YES because the change would be cleaner, more robust, more consistent, more flexible, more idiomatic, "best practice", a performance / micro-optimization when the feature already meets its stated performance requirement, or cross-shell / cross-OS / tool-version portability speculation — those are Out-of-Scope signals, not acceptance signals.

**OOS / `[OUT_OF_SCOPE]` / plan `OOS_N:` rows:** Runtime prompts use `python/cli.py render voter` for grammar-specific OOS wording (see the prose paragraph immediately above this fenced template for the canonical lowest-common-denominator clause). In this template's structural shape: YES files a GitHub issue for future tracking; NO means trivial/incorrect or not worth tracking. OOS items are never implemented in this PR — YES means "file an issue," not "implement now." Vote YES only when the observation is concrete and important enough to justify a durable GitHub issue (typical signals: specific file:line or a reproducible failure mode); use NO for trivial, incorrect, or not-issue-worthy observations.

{BALLOT}

For each ballot item, output exactly one line using the same ID from the ballot heading:
FINDING_N: YES
or
FINDING_N: NO — <one-line reason>
or
OOS_N: YES
or
OOS_N: NO — <one-line reason>

Note: for /review code review, use `OOS_N:` only when the ballot heading itself is `### OOS_N:`; `[OUT_OF_SCOPE]` rows under `### FINDING_N:` still use `FINDING_N:`.

You must vote on every item. Do NOT skip any. Do NOT modify files.
```

## Launching Voters

**For `/design` plan review**: call `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-plan-voters.sh`. The dispatcher launches the Claude Voter 1 lane plus available Codex/Cursor lanes in parallel, waits for sentinels, and emits the voter output paths/statuses for the tally.

**For code review**: `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh` launches Claude (always), Codex (when available), and Cursor (when available) in parallel. An **unavailable** external is skipped (shrink-not-backfill) — no Claude or alternate-external replacement fills the slot — so the panel is Claude plus the available externals. A genuine *failure* of an available external still reduces the effective panel and is reported as degraded. The orchestrator does not invoke voters directly — `review-core.sh` calls the dispatch script.

**Generic Cursor voter argv contract** (mirrored by `dispatch-plan-voters.sh` for `/design`; use the skill-specific launch instructions before copying this block):

```bash
# Cursor authenticates via the CURSOR_API_KEY environment variable (issue
# #3375) — no `--api-key` argv element, so the key never reaches the cursor
# command line, run-external-agent.sh `.meta` CMD_JSON, or `ps`. The call below
# is a Darwin preflight gate: it prints an actionable stderr message when
# neither CURSOR_API_KEY nor a cursor keychain entry is available (cursor would
# otherwise emit a cryptic keychain error) and prints no argv flags; its exit
# is advisory here (the cursor launch / sentinel handling below detects an
# unusable auth state). The `cursor agent` child inherits CURSOR_API_KEY from
# this shell.
"${CLAUDE_PLUGIN_ROOT}/scripts/cursor-auth-flags.sh" || true
# Use a temp file (NOT process substitution) so a non-zero exit from
# agent-model-args.sh — e.g., LARCH_CURSOR_MODEL contains [[:cntrl:]] or is
# blank — propagates and aborts the launch, instead of being swallowed and
# producing an empty MODEL_ARGS array. The defensive `${ARR[@]+"${ARR[@]}"}`
# expansion is required for Bash 3.2 compatibility under `set -u`.
CURSOR_MODEL_ARGS_TMP=$(mktemp)
trap 'rm -f "$CURSOR_MODEL_ARGS_TMP"' EXIT
"${CLAUDE_PLUGIN_ROOT}/scripts/agent-model-args.sh" --tool cursor --with-effort > "$CURSOR_MODEL_ARGS_TMP" || exit $?
CURSOR_MODEL_ARGS=()
while IFS= read -r arg; do CURSOR_MODEL_ARGS+=("$arg"); done < "$CURSOR_MODEL_ARGS_TMP"

${CLAUDE_PLUGIN_ROOT}/scripts/run-external-agent.sh --tool cursor --output "<tmpdir>/cursor-vote-output.txt" --timeout 1200 --capture-stdout -- \
  cursor agent -p --trust --mode plan ${CURSOR_MODEL_ARGS[@]+"${CURSOR_MODEL_ARGS[@]}"} --workspace "$PWD" \
    "$("${CLAUDE_PLUGIN_ROOT}/scripts/cursor-wrap-prompt.sh" "<voter prompt with ballot>.")"
```

Use `run_in_background: true` and `timeout: 1260000` only for skill-specific direct-launch paths. `/design` plan review runs `dispatch-plan-voters.sh` in the foreground via `plan-review-loop.sh`; do not background that dispatcher.

**Cursor voter availability**: `/design` plan review delegates Cursor-slot launch/skip status to `dispatch-plan-voters.sh`; code review delegates it to `dispatch-code-voters.sh`, where an unavailable Cursor slot is skipped (`VOTER_3_STATUS=skipped`) and the panel shrinks by one (shrink-not-backfill).

**Generic Codex voter argv contract** (mirrored by `dispatch-plan-voters.sh` for `/design`; use the skill-specific launch instructions before copying this block):

```bash
# launch-codex-exec.sh owns Codex model args, trust, auth, and retry metadata.
"${CLAUDE_PLUGIN_ROOT:?}/scripts/launch-codex-exec.sh" \
  --output "<tmpdir>/codex-vote-output.txt" \
  --timeout 1200 \
  --workdir "$PWD" \
  --add-dir "$PWD" \
  --sandbox read-only \
  --with-effort \
  --prompt "<voter prompt with ballot>."
```

Use `run_in_background: true` and `timeout: 1260000` only for skill-specific direct-launch paths. `/design` plan review runs `dispatch-plan-voters.sh` in the foreground via `plan-review-loop.sh`; do not background that dispatcher.

**Codex voter availability**: `/design` plan review delegates Codex-slot launch/skip status to `dispatch-plan-voters.sh`; code review delegates it to `dispatch-code-voters.sh`, where an unavailable Codex slot is skipped (`VOTER_2_STATUS=skipped`) and the panel shrinks by one (shrink-not-backfill).

**Claude voter dispatch**: `/design` plan review uses `dispatch-plan-voters.sh` to launch the Claude lane; code review uses `dispatch-code-voters.sh`, which launches the Claude lane inside the dispatcher. Do not launch Claude voters directly from the orchestrator on either path.

Wait for external voter sentinels using `wait-for-reviewers.sh` (use the same tmpdir as the review phase — do not create a new temp directory for voting). Only include sentinel paths for voters that were actually launched:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-reviewers.sh --timeout 1260 \
  "<tmpdir>/cursor-vote-output.txt.done" \
  "<tmpdir>/codex-vote-output.txt.done"
```

Use `timeout: 1260000` on the Bash tool call. Use a foreground Bash tool call with a sufficiently large timeout. Note: voter output files use the `-vote-` infix to avoid collision with reviewer output files (`-plan-output` or `-output`).

**Collecting voter results**: Use `collect-agent-results.sh` to validate external voter outputs (same as for reviewer outputs). Parse `STATUS` and `FAILURE_REASON` for each voter. If a voter fails (`STATUS != OK`), print: `**⚠ <Voter> voter failed — <FAILURE_REASON>. Proceeding with <N> voters (<remaining voter names>).**` Always include the `FAILURE_REASON` so the user can see why the voter failed (e.g., timeout, crash, empty output). Reduce the eligible voter count accordingly and apply the threshold rules above.

## Competition Scoring

After tallying votes, compute a score for each **original reviewer** (not voters):

| Vote pattern | Points | Description |
|---|---|---|
| Finding accepted (meets YES threshold for the tier) | +1 | Reviewer's finding was validated by the panel |
| Neutral (≥1 YES, not accepted) | 0 | Insufficient support, but not unanimously dismissed |
| Rejected (0 YES) | −1 | Finding was unanimously dismissed by the panel |

If a deduplicated finding was proposed by multiple reviewers (merged during deduplication), **all** contributing reviewers receive the same points for that finding.

## Scoreboard

After voting, print the scoreboard. Branch on `SESSION_ENV_PATH`:

- **When `SESSION_ENV_PATH` is empty (standalone run)**: print the full scoreboard table to the session.
- **When `SESSION_ENV_PATH` is non-empty (nested run under `/implement`)**: print only a one-line count summary of the form `Round <N>: <A> accepted, <R> rejected (<N> neutral)` (in-scope findings only). The full scoreboard is suppressed at all levels in nested mode — per-round printing here and the Step 4a final summary (both inline and via `review-round-summary.md` in subagent runs).

Full scoreboard format (used in standalone mode):

```
## Reviewer Competition Scoreboard

| Reviewer | Findings | Accepted | Neutral | Rejected | OOS Proposed | OOS Accepted | OOS-Neutral | OOS-Rejected | Score |
|----------|----------|----------|---------|----------|--------------|--------------|-------------|--------------|-------|
| _label1_ | 3        | 2        | 1       | 0        | 1            | 0            | 1           | 0            | +2    |
| _label2_ | 2        | 1        | 1       | 0        | 0            | 0            | 0           | 0            | +1    |
| _label3_ | 2        | 1        | 0       | 1        | 1            | 0            | 0           | 1            | 0     |
```

The **Neutral** column counts all non-accepted findings that award **0** points to the proposer (≥1 YES but below acceptance threshold). The **Rejected** column counts non-accepted findings that cost **−1** point (0 YES). A single finding is counted in **at most one** of these two columns.

Attribution labels are skill-specific (e.g., `/design` uses `Code`/`Codex`/`Cursor`; `/review` hard panel uses `Correctness`/`Testing`/`Edge-cases`/`Codex-Correctness`/`Codex-Testing`/`Codex-Edge-cases`). One row per independent reviewer. In future iterations, token allocation will be weighted proportionally to reviewer scores.

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

- **`/review` code review** (`collect-findings.sh` / `tally-code-votes.sh`): ballots may contain legacy `### FINDING_N: [OUT_OF_SCOPE] <title>` blocks or direct `### OOS_N:` blocks. Voters must use the matching ballot ID (`FINDING_N:` for legacy OOS headings, `OOS_N:` for direct OOS headings), and `tally-code-votes.sh` accepts both forms.

### OOS Vote Semantics

For out-of-scope items, the vote meanings are:
- **YES**: This observation deserves a GitHub issue for future attention.
- **NO**: Not worth tracking — the observation is trivial or incorrect.

If an OOS item receives 2+ YES votes, it is **accepted** and will be filed as a GitHub issue by `/implement` Step 9a.1 (`/issue` batch mode). In `/review` description mode, accepted OOS items are recorded in local artifacts for the operator to file manually via `/issue` (no automatic filing in this mode). Otherwise it remains an observation reported in the PR body.

**OOS items are never implemented in the current PR** — accepted OOS items result in issue creation only. This cleanly separates "fix now" (in-scope findings) from "fix later" (OOS observations).

### OOS Scoring

Out-of-scope items use the same score shape as in-scope findings: accepted OOS earns +1, non-accepted OOS with a split-panel or exonerated vote pattern scores 0, and dismissed OOS costs −1:

| OOS vote pattern | Points | Description |
|---|---|---|
| OOS accepted (meets YES threshold for the tier) | +1 | Reviewer surfaced an issue worth tracking |
| OOS neutral (≥1 YES, not accepted) | 0 | Insufficient support, but not dismissed |
| OOS rejected (0 YES) | −1 | Observation was unanimously dismissed by the panel |

### OOS Scoreboard

The scoreboard includes additional columns for OOS items:

```
| Reviewer | ... | OOS Proposed | OOS Accepted | OOS-Exonerated | OOS-Rejected | ...
```

### OOS Security Tag

Accepted OOS items can be tagged as **security findings** that are held locally and never filed as public GitHub issues. The detection contract is shared between `/design` plan review (`tally-plan-review.sh`) and `/review` code review (`tally-code-votes.sh`) via `python/voting.py::is_security_block`:

- **Canonical token**: a block is security-tagged when its body contains at least one **unfenced** occurrence of `focus-area\s*=\s*security` (case-insensitive, optional whitespace around `=`).
- **Dedicated field token**: a line-start `focus-area` field also routes as security when its value begins with `security` (including `security-hardening` style values), with optional bold/backtick markup around the label or value and either `:` or `=` as the separator.
- **Heading tag token**: the block-opening heading may start its title with `[security]` or `<security>` (optionally after `[OUT_OF_SCOPE]` / `[OOS]`). Later `### ... [security] ...` headings inside prose are not routing tags.
- **Match discrimination (false-positive guard)**: canonical-token occurrences inside backtick or triple-backtick regions are fenced and do not count — only unfenced occurrences mark a finding as security-tagged.
- **Security counter-invariant**: a real security finding MUST carry at least one routing token recognized by `is_security_block` — an unfenced canonical token, a dedicated `focus-area` field line, or a block-opening heading tag; otherwise it will not be held locally.
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
