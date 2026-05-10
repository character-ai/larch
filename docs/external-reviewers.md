# External Agents

Codex and Cursor participate alongside Claude subagents as reviewers, voters, and sketch authors in the Larch workflow. Gemini reviewer call sites in `/review` and `/implement --quick` have been removed; the launcher (`scripts/launch-gemini-review.sh`), policy file, regression harness, and health-probe machinery remain so the lane can be re-enabled without re-deriving the contract. Gemini is still active as an explicit `/implement --coder=gemini` implementer. The "Launch Order", "Timeout handling", and "Roles Across the Workflow" sections below describe the historical / re-enableable Gemini reviewer shape — they are not the default panel after call-site removal. This document covers the shared integration procedures.

## Availability Checks

At the start of each skill, a binary check determines which external tools are installed:

- If **Codex** is not found, a warning is printed and the skill proceeds without it
- If **Cursor** is not found, a warning is printed and the skill proceeds without it
- If **Gemini** is not found or unhealthy, the `--coder=gemini` implementer falls back to the main-agent code-edit path (`STATUS=claude_fallback`); the dormant Gemini reviewer machinery is unaffected because no skill currently invokes it

Skills gracefully degrade when external tools are unavailable. When Codex or Cursor is not found, Claude replacement subagents fill their slots to maintain the per-skill lane shapes across most phases. Gemini's degradation depends on the slot: the `--coder=gemini` implementer falls back to the main-agent code-edit path (`STATUS=claude_fallback`) when unhealthy or unavailable. The historical Gemini reviewer lane was strictly additive (skipped, no Claude backfill) — that lane is now dormant in `/review` and `/implement --quick`. The authoritative topologies live with their phase docs: `/design` sketch and plan review in [Collaborative Sketches](collaborative-sketches.md) and [Review Agents](review-agents.md), `/review` in [Review Agents](review-agents.md), `/research` in [Agent System](agents.md) and the research skill, and voting / dialectic thresholds in [Voting Process](voting-process.md) plus `skills/shared/dialectic-protocol.md`. Voting uses a step-function threshold: 3 voters require 2+ YES votes, 2 voters require unanimous YES, and fewer than 2 eligible voters causes voting to be skipped with all findings accepted automatically. Gemini never votes.

**Exception: dialectic debate buckets (`/design` Step 2a.5) do NOT use replacement-first.** When the assigned external tool (Cursor for odd-indexed decisions, Codex for even) is unavailable, the bucket is **skipped entirely** and a `Disposition: bucket-skipped` resolution is written — Claude subagents are never substituted into the debate path. This carve-out applies only to the **debate execution phase** of dialectic; the post-debate **judge panel** uses replacement-first normally. See [Dialectic-specific behavior](#dialectic-specific-behavior) below and `skills/shared/dialectic-protocol.md` for the full rationale.

## Trust boundary (filesystem access)

External agents in `/review` and `/research` launch directly against the working tree. **`/review` (and other skills routing through `scripts/launch-cursor-review.sh` / `scripts/launch-codex-review.sh` — `/design` plan-review, `/design` sketch lanes, `/design` dialectic debaters, `/implement --quick` Step 5)** are mechanically sandboxed at the CLI level by default (issue #1529): Codex runs as `codex exec --sandbox read-only -C "$PWD"` and Cursor runs as `cursor agent -p --trust --mode plan --workspace "$PWD"` (no `--sandbox enabled` — issue #1583 removed it to avoid crashes on hosts where the cursor-agent sandbox runtime is unavailable), plus a HARD CONSTRAINTS read-only preamble prepended to every prompt. Cursor read-only enforcement relies on `--mode plan` plus the prompt preamble and the post-run `${OUTPUT}.dirty-tree` sidecar. See `SECURITY.md` § External tool delegation for the full caveats. **`/research`** still launches Cursor and Codex through call paths that inherit the user's filesystem privileges; for those research tasks, the prompt asks them not to modify files — this is a behavioral constraint, not a sandbox. **Gemini reviewer (dormant):** the Gemini reviewer call sites in `/review` and `/implement --quick` have been removed; the launcher `scripts/launch-gemini-review.sh` and its admin-tier (priority 5999) Policy Engine deny rule (`scripts/gemini-reviewer-policy.toml` blocking `write_file`, `replace`, `edit`, `edit_file`, `delete_file`), the read-only prompt preamble, and the repo-root snapshot guard remain as machinery for future re-enablement. If the launcher is re-introduced, the same caveats apply: it narrows native write-tool exposure and catches shell-write bypasses after the fact, but does **not** make Gemini reviewer a full sandbox — shell remains under yolo, and the snapshot guard is fail-open outside git worktrees or on snapshot timeout. The mechanical guarantee depends on gemini-cli continuing to honor `--admin-policy` from arbitrary file paths and on the deny-list tool names matching the actual gemini-cli surface; see [`SECURITY.md` § Gemini reviewer delegation](../SECURITY.md), the policy file at `scripts/gemini-reviewer-policy.toml`, and `scripts/launch-gemini-review.md` for the full caveats. The Gemini implementer (`launch-gemini-implement.sh`) intentionally does NOT carry this admin-policy — implementers are expected to write. `/implement` Step 2 implementation parses `--coder=codex` as the default (Codex implementer), but Step 1's Coder simplicity override may auto-flip the resolved coder to `claude` for small surgical plans when `--coder` was omitted (see `skills/implement/SKILL.md` § Coder simplicity override; pass `--coder=codex` to suppress); `--coder=cursor` selects the Cursor implementer; `--coder=gemini` selects the Gemini implementer; `--coder=claude` routes the orchestrator to the main-agent Edit/Write code-edit path. All four flow through the dispatcher `skills/implement/scripts/step2-implement.sh`. When `--coder=cursor` or `--coder=gemini` is requested but that tool is unhealthy or unavailable, the dispatcher emits `STATUS=claude_fallback` and the orchestrator runs the main-agent code-edit path — symmetric to passing `--coder=claude`. Codex runs under `workspace-write`; Cursor and Gemini have full filesystem access, so the dispatcher uses a shared `HEAD == BASELINE_SHA` assertion before committing on their behalf and bails with `cursor-modified-history` or `gemini-modified-history` if either tool created or amended commits. All external implementers return the same JSON manifest shape (schema: `skills/implement/references/codex-manifest-schema.md`) which the dispatcher validates mechanically (path normalization, branch / `.claude-plugin/plugin.json` / submodule unchanged checks, plus unsandboxed-tool history checks) and sanitizes (`scripts/redact-secrets.sh` over commit message, summary bullets, todos, OOS observations) before downstream Steps 4 / 8a / 9a / 9a.1 consume it. Implementer transcripts stay on disk; Claude does NOT inspect them or run `git diff` to figure out what changed. On `STATUS=needs_qa`, the implementer writes a `qa-pending.json` companion file; the orchestrator collects answers (`AskUserQuestion` when `auto_mode=false`) and re-invokes the dispatcher with `--answers`, preserving partial work across resume cycles. Resume cycles are capped at 5 (6th `--answers` invocation auto-bails with `qa-loop-exceeded`). See [`SECURITY.md` § External tool delegation](../SECURITY.md) for the full enumeration of post-implementer mechanical checks and the residual filesystem-access risk. The `/research` skill carries a skill-scoped `PreToolUse` hook (`scripts/deny-edit-write.sh`) that mechanically guards Claude's own `Edit | Write | NotebookEdit` tool surface to canonical `/tmp` only; the hook does **not** cover Bash or subprocess-spawned external agents. See [`SECURITY.md` § External reviewer write surface in /research](../SECURITY.md#external-reviewer-write-surface-in-research) for the full trust-model framing and [`docs/review-agents.md` § External reviewer trust boundary](review-agents.md#external-reviewer-trust-boundary-skills-using-cursor--codex-against-pwd) for the skill-author-facing summary.

## Launching External Reviewers

External reviewers are launched via the `run-external-agent.sh` wrapper script, which provides:

- **Timeout enforcement** — Kills the process after a configurable timeout
- **Sentinel file creation** — Writes a `.done` file containing the exit code when the process completes
- **Output capture** — two patterns, opt-in per invocation:
  - **stdout capture under `--capture-stdout`** — when the reviewer writes its results to stdout, pass `--capture-stdout` and the wrapper redirects the tool's stdout/stderr to `--output`. Cursor pattern; canonical examples at `skills/review/SKILL.md:146-148, 177-179`.
  - **stdout-only capture under `--capture-stdout-only`** — when the reviewer writes machine-readable JSON to stdout, pass `--capture-stdout-only` and the wrapper redirects stdout to `--output` while stderr goes to `<output>.diag`. Gemini pattern; `launch-gemini-review.sh` normalizes `.response` before the collector sees it.
  - **tool-managed output path** — when the reviewer takes its own output-path argument (e.g., Codex's `--output-last-message`), omit `--capture-stdout`; the wrapper does not capture stdout and the reviewer writes results directly to the file. The `--output` flag still names the expected destination so downstream readers know where to look. Codex pattern; canonical examples at `skills/review/SKILL.md:160-163, 186-190`.
- **Elapsed time tracking** — Reports how long the review took

During review and voting phases, reviewers are launched with `run_in_background: true` so they run concurrently with other work. (Negotiation rounds in `/research` run synchronously.)

Cursor, Codex, and Gemini review launchers all publish a post-invocation dirty-tree sidecar at `${OUTPUT}.dirty-tree` before `${OUTPUT}.done`. The sidecar uses the `scripts/check-mid-run-dirty-tree.sh` contract: `STATUS=clean|dirty|unknown`, `MODE=baseline`, `UNTRACKED_BASELINE=present|missing`, optional NUL-delimited `TRACKED_PATHS_FILE` / `NEW_UNTRACKED_PATHS_FILE`, and `REASON` for dirty or unknown outcomes. Empty-output retries re-enter the outer launcher, so retry outputs get their own sidecar next to the retry file, for example `codex-retry.txt.dirty-tree`. `STATUS=unknown` is treated like dirty. On `STATUS=dirty` or `STATUS=unknown`, any reviewer-introduced working-tree changes are automatically logged and discarded — no operator prompt is issued and no stash is created. The log entry (in `execution-issues.md` under `Warnings` in `/implement` runs, or to the transcript in standalone `/review` runs) identifies the specific reviewer by name. The guard is post-hoc detection, not sandboxing; Cursor, Codex, and Gemini still run with the user's filesystem privileges while the reviewer is active. Gemini reviewer call sites are dormant per `SECURITY.md` (no skill currently launches the reviewer); the sidecar emission is preparatory machinery so `/review` Step 5 sidecar consultation picks up Gemini coverage automatically when the call sites are reintroduced (issue #1487; matches the Cursor/Codex contract introduced by #1437). The dirty-tree sidecar is additive to Gemini's repo-root snapshot guard — both run, covering overlapping but not identical surfaces.

## Launch Order

External reviewers are always launched in a specific order to maximize parallelism — **slowest first**:

1. **Cursor** (slowest) — launched first
2. **Codex** — launched second
3. **Gemini** — historical / re-enableable: launched after Codex when call sites are wired back into a skill (no current skill invokes the reviewer launcher)
4. **Claude subagents** (fastest) — launched last

All launches happen in a single message to ensure true parallel execution.

## Sentinel File Monitoring

The wrapper script writes a `.done` sentinel file when the process completes. This is the only reliable way to detect completion:

- **Do not read output files until the sentinel exists** — Cursor buffers all stdout until exit, so its output file is empty until the process finishes
- **Poll for sentinels** using the `wait-for-reviewers.sh` script, which checks every 5 seconds and prints compact progress dots
- Sentinel files contain the exit code (e.g., `0` for success)

## Output Validation

Validation happens in two layers. The first layer (default collector behavior) always runs; the second layer (substantive-content check) is **opt-in** via collector flags.

### Default collector behavior (always on)

After the sentinel file exists, `scripts/collect-agent-results.sh` performs:

1. Read the output file.
2. Check that it is non-empty.
3. If empty despite exit code 0, **retry once** with a fresh invocation (output file gets a `-retry` suffix).
4. If still empty after retry, or if the exit code is non-zero, emit `STATUS=EMPTY_OUTPUT` / `STATUS=FAILED` / `STATUS=TIMED_OUT` / `STATUS=SENTINEL_TIMEOUT` and the caller falls back per its skill-specific contract (typically Runtime Timeout Fallback — see `skills/shared/external-reviewers.md`).

Treat `STATUS=OK` with empty `FAILURE_REASON` as the success signal; do not use `EXIT_CODE` alone. `EXIT_CODE=0` can still appear on retry-failure rows when the retry sentinel was `0` but the retry output stayed empty (`STATUS=EMPTY_OUTPUT`). See `scripts/collect-agent-results.md` for the full retry-row exit-code semantics.

### Opt-in substantive-content check

When the collector is invoked with `--substantive-validation`, it additionally calls `scripts/validate-research-output.sh` on each `STATUS=OK` output. Validator failure is rewritten to `STATUS=NOT_SUBSTANTIVE` with `HEALTHY=false`, and the caller treats it identically to a timeout (Claude-subagent fallback). This catches outputs that pass sentinel + non-empty + retry but contain only banner text (e.g., `Authentication required`) or other non-substantive content.

The optional `--validation-mode` modifier forwards `--validation-mode` to the validator, which (a) lowers the body-word floor from 200 to 30, (b) accepts the literal `NO_ISSUES_FOUND` token as substantive without further checks, and (c) keeps the citation requirement unchanged. This preset is for short reviewer-style outputs whose contract is *"numbered findings ... If NO issues, output exactly NO_ISSUES_FOUND"*.

**Currently opted in by:**

| Caller | Flags |
|--------|-------|
| `/research` research phase (Standard / Deep) | `--substantive-validation` (no `--validation-mode`; 200-word floor + citation requirement; outputs are 2-3-paragraph research prose) |
| `/research` validation phase (Step 2.4) | `--substantive-validation --validation-mode` (30-word floor + `NO_ISSUES_FOUND` short-circuit + citation requirement; outputs are short numbered findings) |
| `/review` Step 3a code review | `--substantive-validation --validation-mode` |
| `/implement` Step 5 quick-mode review | `--substantive-validation --validation-mode` |
| `/design` Step 3 plan review | `--substantive-validation --validation-mode` |

The dialectic-phase (`/design` Step 2a.5 debaters and judges) collectors deliberately do NOT pass these flags — their output contracts (debate prose with structured tags / vote line) differ from the reviewer-style numbered-findings shape.

Authoritative flag documentation lives in the `--substantive-validation` / `--validation-mode` stanza of the `scripts/collect-agent-results.sh` header comment block; update both this section and that header in lockstep when adding a new caller.

## Timeout Handling

External reviewers have configurable timeouts (typically 1200 seconds for voting and 1800 seconds for code review). The dormant Gemini reviewer launcher (`launch-gemini-review.sh`) hard-caps any future Gemini code-review launch at 600 seconds, on the rationale that Gemini was additive and should not hold the panel open as long as replacement-style lanes; that cap applies if the call sites are re-enabled. If a reviewer exceeds its timeout:

- The process is killed by the wrapper script
- The sentinel file records a non-zero exit code
- A warning is printed and the skill proceeds without that reviewer

## Roles Across the Workflow

External reviewers participate in multiple phases:

| Phase | Role | Skills | Fallback behavior |
|---|---|---|---|
| [Collaborative sketches](collaborative-sketches.md) | Propose architectural approaches | `/design` | Replacement-first (Claude subagent fills slot) |
| Plan review | Review implementation plans | `/design` | Replacement-first |
| Code review | Review code changes | `/review` | Cursor/Codex replacement-first; Gemini reviewer dormant (call sites removed; launcher retained as machinery) |
| Implementation | Edit working tree from an implementation plan | `/implement` (omitted `--coder` starts at `codex`, auto-routes to `claude` for small surgical plans — see `skills/implement/SKILL.md` § Coder simplicity override; pass `--coder=codex` to suppress), `/implement --coder=cursor`, `/implement --coder=gemini` | Codex is the parsed default; small-plan auto-route runs in the main-agent code-edit path (`STATUS=claude_fallback`); Cursor/Gemini fall back to the main-agent path when unhealthy |
| [Voting](voting-process.md) | Vote on findings | `/design`, `/review` | Replacement-first |
| Negotiation | Multi-round dispute resolution | `/research` | Replacement-first |
| **Dialectic debate** (`/design` Step 2a.5) | Defend / attack contested decisions | `/design` | **Bucket skipped — no Claude substitution** |
| Dialectic judge panel (`/design` Step 2a.5) | Adjudicate between pre-authored defenses | `/design` | Replacement-first (panel shape stays intact) |

## Dialectic-specific behavior

`/design` Step 2a.5 runs a **dialectic debate + judge panel** phase whose fallback semantics differ from every other reviewer phase. Both the debate phase and the judge panel are specified in detail at `skills/shared/dialectic-protocol.md`; the integration points with the shared external-reviewer infrastructure are:

1. **Debaters never fall back to Claude** (carve-out): Cursor runs both sides of odd-indexed decisions; Codex runs both sides of even-indexed decisions; if the assigned tool is unavailable at launch time, the bucket is skipped and a `Disposition: bucket-skipped` resolution is written — the synthesis decision stands for that point. This is intentional divergence (see GitHub issue #98): debater outputs are adversarial prose whose style can leak tool identity; substituting a Claude subagent into the debate path would bias the downstream judge panel.
2. **Dialectic-scoped shadow flags**: the dialectic phase uses `dialectic_codex_available` / `dialectic_cursor_available` flags snapshotted at entry. These flags are **never written back** to the orchestrator-wide `codex_available` / `cursor_available` flags. A Cursor or Codex timeout during a dialectic debate therefore does not lock that tool out of Step 3 plan review.
3. **`--write-health /dev/null`**: every `collect-agent-results.sh` invocation in the dialectic phase (both debate collection and judge collection) passes `--write-health /dev/null` so the dialectic phase **never updates** `${SESSION_ENV_PATH}.health`. Debate-time failures stay scoped to this phase.
4. **Judge panel uses replacement-first**: when Cursor or Codex is unhealthy at judge launch time, a Claude Code Reviewer subagent replaces that slot so the judge-panel shape remains intact. Judges adjudicate between pre-authored defenses and don't write adversarial prose, so the debater carve-out doesn't apply here.
5. **Judge-phase health re-probe**: `scripts/check-reviewers.sh --probe` is run synchronously immediately before launching judges. Debate-time failures must not lock a tool out of the judge role — judgment happens minutes after debate, and tool state can recover.

### Regression guard

`scripts/dialectic-smoke-test.sh` is the offline regression guard for the dialectic parser, tally rules, and structural invariants documented in `skills/shared/dialectic-protocol.md`. Fixtures live under `tests/fixtures/dialectic/`. Run locally via `make smoke-dialectic`; CI runs the same command in the `smoke-dialectic` job. When changing the protocol's Parser tolerance or Threshold Rules sections, update the smoke test and/or fixtures in the same PR.
