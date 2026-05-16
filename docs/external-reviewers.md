# External Agents

## Availability Checks

At the start of each skill, a binary check determines which external tools are installed:

- If **Codex** is not found, a warning is printed and the skill proceeds without it
- If **Cursor** is not found, a warning is printed and the skill proceeds without it

**Exception: dialectic debate buckets (`/design` Step 2a.5) do NOT use replacement-first.** When the assigned external tool (Cursor for odd-indexed decisions, Codex for even) is unavailable, the bucket is **skipped entirely** and a `Disposition: bucket-skipped` resolution is written — Claude subagents are never substituted into the debate path. This carve-out applies only to the **debate execution phase** of dialectic; the post-debate **judge panel** uses replacement-first normally. See [Dialectic-specific behavior](#dialectic-specific-behavior) below and `skills/shared/dialectic-protocol.md` for the full rationale.

## Trust boundary (filesystem access)

## Launching External Reviewers

External reviewers are launched via the `run-external-agent.sh` wrapper script, which provides:

- **Timeout enforcement** — Kills the process after a configurable timeout
- **Sentinel file creation** — Writes a `.done` file containing the exit code when the process completes
- **Output capture** — two patterns, opt-in per invocation:
  - **stdout capture under `--capture-stdout`** — when the reviewer writes its results to stdout, pass `--capture-stdout` and the wrapper redirects the tool's stdout/stderr to `--output`. Cursor pattern; canonical examples at `skills/review/SKILL.md:146-148, 177-179`.
  - **tool-managed output path** — when the reviewer takes its own output-path argument (e.g., Codex's `--output-last-message`), omit `--capture-stdout`; the wrapper does not capture stdout and the reviewer writes results directly to the file. The `--output` flag still names the expected destination so downstream readers know where to look. Codex pattern; canonical examples at `skills/review/SKILL.md:160-163, 186-190`.
- **Elapsed time tracking** — Reports how long the review took

During review and voting phases, reviewers are launched with `run_in_background: true` so they run concurrently with other work. (Negotiation rounds in `/research` run synchronously.)

## Launch Order

External reviewers are always launched in a specific order to maximize parallelism — **slowest first**:

1. **Cursor** (slowest) — launched first
2. **Codex** — launched second
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
4. If the initial row is `FAILED`, `TIMED_OUT`, or `SENTINEL_TIMEOUT` with a transient-network diagnostic, retry once through the same `.meta` replay path.
5. If still empty after retry, if retry also fails, or if the initial failure is not retry-eligible, emit `STATUS=EMPTY_OUTPUT` / `STATUS=FAILED` / `STATUS=TIMED_OUT` / `STATUS=SENTINEL_TIMEOUT` and the caller falls back per its skill-specific contract (typically Runtime Timeout Fallback — see `skills/shared/external-reviewers.md`).

Treat `STATUS=OK` with empty `FAILURE_REASON` as the success signal; do not use `EXIT_CODE` alone. `EXIT_CODE=0` can still appear on retry-failure rows when the retry sentinel was `0` but the retry output stayed empty (`STATUS=EMPTY_OUTPUT`). See `scripts/collect-agent-results.md` for the full retry-row exit-code semantics.

### Opt-in substantive-content check

When the collector is invoked with `--substantive-validation`, it additionally calls `scripts/validate-research-output.sh` on each `STATUS=OK` output. Validator failure is rewritten to `STATUS=NOT_SUBSTANTIVE` with `HEALTHY=false`, and the caller treats it identically to a timeout (Claude-subagent fallback). This catches outputs that pass sentinel + non-empty + retry but contain only banner text (e.g., `Authentication required`) or other non-substantive content.

The optional `--validation-mode` modifier forwards `--validation-mode` to the validator, which (a) lowers the body-word floor from 200 to 30, (b) accepts the canonical JSON no-findings sentinel `{"no_issues_found": true}` and legacy `NO_ISSUES_FOUND` token as substantive without further checks, (c) maps `CURSOR_EMPTY_RESPONSE` to its own status, and (d) keeps the citation requirement unchanged. This preset is for short reviewer-style outputs whose no-findings contract is the JSON sentinel; the plain-text token is deprecated but still accepted for compatibility.

**Currently opted in by:**

| Caller | Flags |
|--------|-------|
| `/research` research phase (Standard / Deep) | `--substantive-validation` (no `--validation-mode`; 200-word floor + citation requirement; outputs are 2-3-paragraph research prose) |
| `/research` validation phase (Step 2.4) | `--substantive-validation --validation-mode` (30-word floor + no-findings sentinel short-circuit + `CURSOR_EMPTY_RESPONSE` mapping + citation requirement; outputs are short numbered findings) |
| `/review` Step 3a code review | `--substantive-validation --validation-mode` |
| `/design` Step 3 plan review | `--substantive-validation --validation-mode` |

The dialectic-phase (`/design` Step 2a.5 debaters and judges) collectors deliberately do NOT pass these flags — their output contracts (debate prose with structured tags / vote line) differ from the reviewer-style numbered-findings shape.

Authoritative flag documentation lives in the `--substantive-validation` / `--validation-mode` stanza of the `scripts/collect-agent-results.sh` header comment block; update both this section and that header in lockstep when adding a new caller.

## Timeout Handling

- The process is killed by the wrapper script
- The sentinel file records a non-zero exit code
- A warning is printed and the skill proceeds without that reviewer

## Roles Across the Workflow

External reviewers participate in multiple phases:

| Phase | Role | Skills | Fallback behavior |
|---|---|---|---|
| [Collaborative sketches](collaborative-sketches.md) | Propose architectural approaches | `/design` | Replacement-first (Claude subagent fills slot) |
| Plan review | Review implementation plans | `/design` | Replacement-first |
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
