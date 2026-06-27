# Voting Protocol

Shared voting protocol for adjudicating review findings. Used by `/design` (plan review) and `/review` (code review). This protocol **replaces** the Negotiation Protocol for `/design` and `/review`. `/research` continues using the Negotiation Protocol in `external-reviewers.md`.

## Overview

After reviewers submit findings and findings are deduplicated, a voting panel votes YES/NO on each finding. `/design` (plan review) normally uses a 3-voter panel (Claude + Codex + Cursor). `/review` and `/implement` Step 5 (code review) use three fixed slots: `cursor-validity`, `codex-plan-fidelity`, and `codex-pragmatism`. Voter 1 is Cursor-only with Claude replacement when Cursor is unavailable. Voters 2 and 3 use Codex-primary external waterfall dispatch. Findings with 2+ YES votes are accepted in the full tier. When voters are unavailable, the panel degrades through the tier table below and never fails open. `/review` voter dispatch is owned by `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent dispatch-voters`; vote tally is owned by `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" review tally-code-votes`. Original reviewers earn competition points based on how their findings perform in voting.

## Ballot Format

Before sending to voters, assign each deduplicated finding a stable sequential ID. The ballot file uses `### FINDING_N:` markdown heading blocks — one block per finding. For `/design` plan review, `python/cli.py plan-review tally` (implementation: `python/plan_review.py`) also splits `### OOS_N:` blocks; for `/review` code review, `review tally-code-votes` accepts both `### FINDING_N:` and `### OOS_N:` headings, while legacy OOS-tagged code-review rows may still appear as `### FINDING_N:` headings with `[OUT_OF_SCOPE]` in the title:

```markdown
### FINDING_1: <short title>
- **Reviewer**: anonymous
- **Concern**: <finding description>
- **Suggested revision**: <what to change>

### FINDING_2: <short title>
- **Reviewer(s)**: anonymous
- **Concern**: <finding description>
- **Suggested revision**: <what to change>
```

Prepend the voter instructions as free prose before the first `### FINDING_N:` block (they are ignored by the parsers). Voter-facing ballots must not reveal proposer identity. Reviewer lines keep the stable `Reviewer` / `Reviewer(s)` shape but use `anonymous`; proposer attribution is retained out of band in `proposer-map.tsv` for scoring and audit. Body text is not scrubbed. Attribution labels remain skill-specific after tally: `/design` uses `Code` / `Codex` / `Cursor`; `/review` uses specialist labels (`Correctness`, `Testing`, `Edge-cases`, `Codex-Correctness`, `Codex-Testing`, `Codex-Edge-cases`) for its hard panel. Simple panels add `Claude-Generic` and use a reduced external-specialist set. `/research` does not participate in voting. It uses the Negotiation Protocol instead.

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

Dispatchers emit degraded-panel warnings when effective voters drop below the expected panel size. For `/review` and `/implement` Step 5 code review the expected size is the three-slot code-review panel when Cursor or Codex voter lanes are available, or **one Claude fallback voter** when Cursor is unavailable and no external voter 2/3 lane is active. Voter 1 is Cursor-only on the external path and is replaced by Claude when Cursor is unavailable. Voters 2 and 3 use Codex-primary labels with external waterfall behavior. A single-Claude fallback is the designed state and raises **no** warning; only a genuine failure of an *expected* judge degrades the panel. (`/design` plan review still back-fills unavailable externals to keep the expected size at three.) `effective` means status is not `failed` and the voter output is substantive enough to contribute valid vote lines after any retry path settles. On the three-slot code-review path, `ELIGIBLE_VOTERS` and `EFFECTIVE_VOTERS` count only substantive non-empty voter files after parse-rate removal; empty placeholder slots keep their `vN_tool` attribution but do not inflate the quorum.

After the acceptance threshold, each finding is classified into one of three operator-facing outcomes: `accepted`, `neutral` (≥1 YES but below acceptance threshold; -0.25 points to the proposing reviewer), or `rejected` (0 YES; −1 point). The classifier lives in `python/voting.py::classify_result`; tally scripts map the label to KV and JSON at the emission boundary.

## Voter Panel Composition

**For plan review** (`/design` Step 3):
- **Voter 1**: Claude — via `python/cli.py plan-review voter-dispatch` → `launch-claude-review.sh --role voter` (always launched; model resolved from `LARCH_VOTER_MODEL`, default `claude-sonnet-4-6`)
- **Voter 2**: Codex — via `python/cli.py plan-review voter-dispatch` → `agent dispatch-waterfall` → `launch-review.sh`
- **Voter 3**: Cursor — via `python/cli.py plan-review voter-dispatch` → `agent dispatch-waterfall` → `launch-review.sh`

**For code review** (`/review` Step 3 and `/implement` Step 5): `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent dispatch-voters` launches three fixed voter slots, using **canonical slot indexing** (`v1`/`v2`/`v3` always map to validity/plan-fidelity/pragmatism, never to compacted surviving voters). Voter 1 is Cursor-only on the external path. Voters 2 and 3 use Codex-primary waterfall dispatch and may fall through to the configured external fallback labels:
- **Voter 1** (`v1`): `cursor-validity` — `render voter --archetype validity-correctness`
- **Voter 2** (`v2`): `codex-plan-fidelity` — `render voter --archetype plan-fidelity-completeness`
- **Voter 3** (`v3`): `codex-pragmatism` — `render voter --archetype pragmatism-cost`

When Cursor is unavailable and no external voter 2/3 lane is active, the panel falls back to a **single Claude floor voter** at slot 1 (`agent launch-claude-review --role voter`, binding-single tier); slots 2-3 are empty placeholders that keep their `vN_tool` attribution but do not count toward quorum. The active per-slot archetype label is recorded in the `vN_tool` cells (`cursor-validity`/`codex-plan-fidelity`/`codex-pragmatism`, fallback semantic labels, or `claude` on fallback) even when a slot's vote file is empty or failed. The code-review classification TSV has **22 columns** (`reviewer_slots`, three voter groups of five rating cells plus `vN_tool`, and trailing `scope`; no `body_severity`). `/design` plan review uses the separate **23-column** schema (`finding_reviewers`, the same voter groups, `body_severity`, and trailing `scope`). The canonical headers are `python/cli.py voting code-review-classification-header` and `python/cli.py voting findings-classification-header`. `scope` is `in_scope` or `oos`; consumers prefer explicit `scope=oos` over ballot id prefixes. Legacy TSVs without `scope` remain readable with flat accepted +1 scoring and `OOS_` prefix fallback.

**MAV/legacy tally exception:** the fixed length-3 `--voter-files` + `--voter-tools` contract applies only on the normal three-slot dispatch path. When `--voter-tools` is omitted, `review tally-code-votes` keeps compacted multi-voter semantics for one to three `--voter-files` entries (main-agent-vote re-tally, zero-findings, and other legacy callers) and the legacy 18-column rows; those callers are unchanged.

All voters vote on **all** findings. No self-voting exclusion. Neutralized ballots are the structural mitigation: voters see `anonymous` reviewer lines while tally code restores proposer attribution from the sidecar after voting.

## Voter Prompt Template

Customize the `{VOTER_ROLE}` and `{REVIEW_CONTEXT}` per skill:

<!-- OOS voter rubric: canonical runtime voter text is emitted by python/cli.py render voter. Keep OOS paragraph parity across skills/design/SKILL.md (Step 3 MAV), skills/implement/references/step5-review-branches.md (Step 5 MAV), and this voting-protocol template manually. -->

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

Voter dispatch is owned by Python dispatchers, not prompt-side launch scaffolding.

- `/design` plan review voter dispatch is owned by `python/cli.py plan-review voter-dispatch`.
- `/review` and `/implement` Step 5 code-review voter dispatch is owned by `python/cli.py agent dispatch-voters`.
- Tally ownership remains with the existing Python tally verbs, including `python/cli.py plan-review tally` and `python/cli.py review tally-code-votes`.
- The live Codex dispatch surface and output stem are documentary tokens here only: `${CLAUDE_PLUGIN_ROOT:?}/python/cli.py agent launch-codex-exec` and `codex-vote-output.txt`.

Do not launch voters directly from the orchestrator on `/design`, `/review`, or `/implement` Step 5 paths. The dispatchers own availability checks, fallbacks, sentinel waits, external result validation, and status emission.

## Competition Scoring

After tallying votes, compute a score for each **original reviewer** (not voters):

| Vote pattern | Points | Description |
|---|---|---|
| Accepted in-scope finding with a strict majority of YES voters rating `blocker` or `major` on their `vN_severity` cell | +2 | High-impact finding validated by YES voters |
| Other accepted in-scope finding | +1 | Finding was validated by the panel |
| Neutral (≥1 YES, not accepted) | -0.25 | Insufficient support, but not unanimously dismissed |
| Rejected (0 YES) | −1 | Finding was unanimously dismissed by the panel |

Severity for competition points comes from panel `vN_severity` cells attached to recorded panel votes. `body_severity` never affects points. If a deduplicated finding was proposed by multiple reviewers, **all** contributing reviewers receive the same weighted points for that finding. Reviewer pruning remains unweighted accepted-minus-rejected count math and does not apply the neutral penalty.

`LARCH_UNIQUE_FINDER_BONUS` is an experimental additive bonus and is off by default. A positive float enables the bonus and sets its size; the suggested experimental value is `0.25`. It applies only when an accepted in-scope finding has exactly one restored proposer. Deduplicated multi-reviewer findings keep shared base credit and receive no uniqueness bonus. OOS scoring remains flat and unaffected. Reviewer pruning remains unweighted accepted-minus-rejected math and does not use this bonus.

## Scoreboard

After voting, print the scoreboard. Branch on `SESSION_ENV_PATH`:

- **When `SESSION_ENV_PATH` is empty (standalone run)**: print the full scoreboard table to the session.
- **When `SESSION_ENV_PATH` is non-empty (nested run under `/implement`)**: print only a one-line count summary of the form `Round <N>: <A> accepted, <R> rejected (<N> neutral)` (in-scope findings only). The full scoreboard is suppressed at all levels in nested mode — per-round printing here and the Step 4a final summary (both inline and via `review-round-summary.md` in subagent runs).

Full scoreboard format (used in standalone mode):

```
## Reviewer Competition Scoreboard

| Reviewer | Findings | Accepted | Neutral | Rejected | OOS Proposed | OOS Accepted | OOS-Neutral | OOS-Rejected | Score |
|----------|----------|----------|---------|----------|--------------|--------------|-------------|--------------|-------|
| _label1_ | 3        | 2        | 1       | 0        | 1            | 0            | 1           | 0            | +2.75 |
| _label2_ | 2        | 1        | 1       | 0        | 0            | 0            | 0           | 0            | +0.75 |
| _label3_ | 2        | 1        | 0       | 1        | 1            | 0            | 0           | 1            | 0     |
```

The **Neutral** column counts all non-accepted in-scope findings that cost **-0.25** points to the proposer (≥1 YES but below acceptance threshold). The **Rejected** column counts non-accepted findings that cost **−1** point (0 YES). A single finding is counted in **at most one** of these two columns.

When `LARCH_UNIQUE_FINDER_BONUS` is active and rewards at least one accepted in-scope finding, print one note below the reviewer scoreboard with the bonus value and rewarded sole-finder finding count. Do not add a scoreboard column.

Attribution labels are skill-specific (e.g., `/design` uses `Code`/`Codex`/`Cursor`; `/review` hard panel uses `Correctness`/`Testing`/`Edge-cases`/`Codex-Correctness`/`Codex-Testing`/`Codex-Edge-cases`). One row per independent reviewer. Future token allocation should use precision-value, not cumulative reviewer `Score`: measure in-scope `net-score-per-finding` as `(accepted_weight - Rejected) ÷ Proposed` on scoreboard columns, where `Proposed` is the in-scope `Findings` count and OOS is excluded from both numerator and denominator.

## Out-of-Scope Observations

Reviewers may return a second list of **out-of-scope observations** — pre-existing issues or concerns beyond the PR's scope that are worth surfacing for future attention. These are handled alongside in-scope findings but with different semantics:

### OOS on the Ballot

The ballot format for OOS items depends on the skill:

- **`/design` plan review** (`python/cli.py plan-review tally`): OOS items get `OOS_` prefixed IDs (e.g., `OOS_1`, `OOS_2`) and appear as `### OOS_N:` heading blocks on the ballot:

  ```markdown
  ### OOS_1: <short title of pre-existing issue>
  - **Reviewer**: anonymous
  - **Concern**: <description of pre-existing issue>
  ```

- **`/review` code review** (`review collect-findings` / `review tally-code-votes`): ballots may contain legacy `### FINDING_N: [OUT_OF_SCOPE] <title>` blocks or direct `### OOS_N:` blocks. Voters must use the matching ballot ID (`FINDING_N:` for legacy OOS headings, `OOS_N:` for direct OOS headings), and `review tally-code-votes` accepts both forms.

### OOS Vote Semantics

For out-of-scope items, the vote meanings are:
- **YES**: This observation deserves a GitHub issue for future attention.
- **NO**: Not worth tracking — the observation is trivial or incorrect.

If an OOS item receives 2+ YES votes, it is **accepted** and will be filed as a GitHub issue by `/implement` Step 9a.1 (`/issue` batch mode). In `/review` description mode, accepted OOS items are recorded in local artifacts for the operator to file manually via `/issue` (no automatic filing in this mode). Otherwise it remains an observation reported in the PR body.

**OOS items are never implemented in the current PR** — accepted OOS items result in issue creation only. This cleanly separates "fix now" (in-scope findings) from "fix later" (OOS observations).

### OOS Scoring

Out-of-scope items stay flat in the live voting classifier: accepted OOS earns a provisional +1, non-accepted OOS with a split-panel or OOS neutral (≥1 YES, not accepted) vote pattern scores 0, and dismissed OOS costs −1. `python/voting.py::classify_result` is the live classifier and does not inspect GitHub issue fate.

| OOS vote pattern | Points | Description |
|---|---|---|
| OOS accepted (meets YES threshold for the tier) | +1 provisional | Reviewer surfaced an issue worth tracking |
| OOS neutral (≥1 YES, not accepted) | 0 | Insufficient support, but not dismissed |
| OOS rejected (0 YES) | −1 | Observation was unanimously dismissed by the panel |

`/analyze-issues` can render a separate fate-adjusted OOS report after the fact. In that diagnostic report, open filed OOS issues remain provisional, PR-closed filed OOS issues keep +1, and filed OOS issues closed unfixed or combined away score 0. The fate-adjusted report adds no retroactive −1 penalty and does not change live voting outputs.

### OOS Scoreboard

The scoreboard includes additional columns for OOS items:

```
| Reviewer | ... | OOS Proposed | OOS Accepted | OOS-Neutral | OOS-Rejected | ...
```

### OOS Security Tag

Accepted OOS items can be tagged as **security findings** that are held locally and never filed as public GitHub issues. The detection contract is shared between `/design` plan review (`python/cli.py plan-review tally` / `python/voting.py`) and `/review` code review (`review tally-code-votes`) via `python/voting.py::is_security_block`:

- **Canonical token**: a block is security-tagged when its body contains at least one **unfenced** occurrence of `focus-area\s*=\s*security` (case-insensitive, optional whitespace around `=`).
- **Dedicated field token**: a line-start `focus-area` field also routes as security when its value begins with `security` (including `security-hardening` style values), with optional bold/backtick markup around the label or value and either `:` or `=` as the separator.
- **Heading tag token**: the block-opening heading may start its title with `[security]` or `<security>` (optionally after `[OUT_OF_SCOPE]` / `[OOS]`). Later `### ... [security] ...` headings inside prose are not routing tags.
- **Match discrimination (false-positive guard)**: canonical-token occurrences inside backtick or triple-backtick regions are fenced and do not count — only unfenced occurrences mark a finding as security-tagged.
- **Security counter-invariant**: a real security finding MUST carry at least one routing token recognized by `is_security_block` — an unfenced canonical token, a dedicated `focus-area` field line, or a block-opening heading tag; otherwise it will not be held locally.
- Accepted OOS items where the block matches are written ONLY to the local `oos-accepted-*.md` artifact and to the local-only artifact path; security-tagged findings (focus-area=security) are held locally and NEVER filed publicly — the canonical filing pipeline (`/implement` Step 9a.1 → `/issue` batch mode) is skipped for them.

### OOS Reporting

OOS items are **not** written to `rejected-findings.md`. They follow a separate pipeline:

- **Accepted OOS items — reviewer voting path** (2+ YES): Plan-review OOS accepted by the `/design` panel is written to `$DESIGN_TMPDIR/oos-accepted-design.md` (and visibility text to `$DESIGN_TMPDIR/oos.md`) during `/design` Step 3 tally/finalize. Code-review OOS accepted by the `/review` panel is written to `$REVIEW_TMPDIR/oos-accepted-review.md` during review tally; `review core` mirrors a copy at `$IMPLEMENT_TMPDIR/oos-accepted-review.md` for `/implement` Step 9a.1 and disposition gates.
- **Accepted OOS items — main-agent dual-write path** (no vote required): Written to `oos-accepted-main-agent.md` in `$IMPLEMENT_TMPDIR` by the main agent at discovery time, every time it logs a `Pre-existing Code Issues` entry to `execution-issues.md`. This is the mechanical enforcement of `/implement`'s Follow-up Work Principle for the `Pre-existing Code Issues` category — see `/implement` SKILL.md → "Follow-up Work Principle" and "Mechanical enforcement of the principle: `Pre-existing Code Issues` dual-write". Durable follow-up work outside that category is not auto-filed via this path — the main agent files it manually via `/issue` per the principle. This path is unconditional and runs in every mode (`--quick`, `--merge`, `--draft`, `--no-merge`, or any future flag). It does NOT pass through a voting panel — main-agent classification is the policy gate.
- **Unified filing**: `/implement` Step 9a.1 reads accepted OOS from the main-agent artifact, the plan-review artifact (`$DESIGN_TMPDIR/oos-accepted-design.md` when `/design` ran in-session, with implement-local fallbacks documented in `/implement` SKILL.md for disposition gates and ship-pr), and `$IMPLEMENT_TMPDIR/oos-accepted-review.md`, deduplicates across phases, and creates GitHub issues via `/issue` (batch mode) with LLM-based semantic duplicate detection against open + recently-closed GitHub issues. All three artifacts share the same `### OOS_N:` schema (Description, Reviewer, Vote tally, Phase). Main-agent items use Reviewer=`Main agent`, Vote tally=`N/A — auto-filed per policy`, Phase=`implement`.
- **Non-accepted OOS items**: Collected and reported in a dedicated `<details><summary>Out-of-Scope Observations</summary>` section in the PR body for future reference.

External reviewers **in diff mode** differ by slot type. **Specialist external slots** (Cursor and Codex specialists loaded from `agents/reviewer-*.md`) use dual-list output (with `### In-Scope Findings` and `### Out-of-Scope Observations` section headers) and can contribute OOS items via voting. **In `/review` description mode**, all external reviewers produce dual-list output matching the Claude subagent contract and contribute OOS observations via voting — see `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` Step 3a. Claude subagent reviewers (which use the dual-list templates from `reviewer-templates.md`) produce OOS items via voting in both modes; the main agent's dual-write path produces OOS items without voting.

## Zero Accepted Findings

If voting filters out **all** in-scope findings (every in-scope finding rejected by the panel), print: `**ℹ Voting panel rejected all in-scope findings. No changes to implement.**` and skip the implementation/revision step. Proceed directly to the rejected findings report. (OOS items accepted for issue filing are processed separately — by `/implement` Step 9a.1 — and do not count as implementation work.)
