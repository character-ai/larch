## Goal
Replace LLM-orchestrated /review with bash-driven review-core.sh and add review-and-fix skill

## Implementation Plan

### Goal

Extract the `/review` orchestration prose from `skills/review/SKILL.md` into a bash state machine
(`skills/review/scripts/review-core.sh`), replace `SKILL.md` with a thin ~50-line wrapper, add a
new `skills/review-and-fix/` skill directory for fix application, add two new orchestration
agents (`agents/orchestrator-aggregator.md`, `agents/orchestrator-judge.md`), and extend
`skills/review/scripts/dispatch-panel.sh` with a `--panel simple|hard` flag. `/implement` is NOT
touched; backward-compatible artifact paths are preserved.

### Constraints

- `skills/review/SKILL.md` must stay <= 200 lines (test-review-structure.sh assertion 1).
- The new `SKILL.md` wrapper must preserve: anti-halt continuation reminder substring,
  mandatory-read lines for `domain-rules.md` and `voting.md`, focus-area enum on
  quick-review prompt lines, two-mode activation grammar (--diff / description), verbatim
  abort messages for --diff+description and no-args cases, `--pieces-json` in Step 4b,
  `### In-Scope Findings` / `### Out-of-Scope Observations` dual-list contract hints.
- All existing script contracts under `skills/review/scripts/` are preserved unchanged except
  `dispatch-panel.sh` (which gets the `--panel` flag added).
- `/implement`'s dependency on nested `/review` producing `$IMPLEMENT_TMPDIR/review-round-summary.md`,
  `$IMPLEMENT_TMPDIR/review-summary.json`, `$IMPLEMENT_TMPDIR/rejected-findings.md`,
  `$IMPLEMENT_TMPDIR/review-dirty-tree-summary.env`, `$IMPLEMENT_TMPDIR/oos-accepted-review.md`,
  and the `### review-result` footer must be preserved.
- `agents/orchestrator-aggregator.md` and `agents/orchestrator-judge.md` are named OUTSIDE
  the `reviewer-*` glob to avoid the pre-rendered reviewer prompt generator picking them up.
- No new `--timing-task-kind` literals are introduced (review-core.sh delegates to existing
  scripts which already carry their own timing entries).
- `test-review-structure.sh` must be updated in lockstep with all SKILL.md and script changes.

---

### Step 1 — Create `skills/review/scripts/review-core.sh`

Create `skills/review/scripts/review-core.sh` as a **single-round state machine** (NOT a
long-running loop). The SKILL.md wrapper owns the outer round loop and calls `review-core.sh`
once per round.

**Accepted flags:**
`--mode diff|description`, `--output-dir DIR` (maps to REVIEW_TMPDIR; passes `--output-dir`
to `gather-context.sh`), `--session-env-path PATH`, `--codex-available true|false`,
`--cursor-available true|false`, `--diff-file PATH`, `--commit-count N`,
`--scope-files PATH`, `--plan-file PATH`, `--feature-file PATH`, `--description-text TEXT`,
`--panel simple|hard` (default: hard), `--run-id ID`, `--round-num N` (default: 1).

**Stage 1 — Gather context:**
Call `gather-context.sh --mode <diff|description> --output-dir "$REVIEW_TMPDIR" [...]` (note:
`gather-context.sh` uses `--output-dir`, NOT `--review-tmpdir`).

**Stage 2 — Dispatch panel:**
Call `dispatch-panel.sh --mode "$MODE" --review-tmpdir "$REVIEW_TMPDIR" --panel "$PANEL"
--codex-available "$codex_available" --cursor-available "$cursor_available" [...]`.

**Stage 3 — Collect, vote, emit tally:**
Call `collect-findings.sh`, `tally-votes.sh`, `detect-wholesale-rejection.sh`, `emit-tally.sh`
in sequence. After collection, run **dirty-tree recovery** (Stage 3a below).

**Stage 3a — Dirty-tree recovery (always runs after collection):**
For every `${output}.dirty-tree` sidecar from launched reviewers:
- Scan for `STATUS=dirty` or `STATUS=unknown`; treat missing sidecars as unknown.
- Run `check-mid-run-dirty-tree.sh --mode checkpoint`.
- Aggregate `ANY_DIRTY`, `LAUNCHERS_DIRTY` (comma-list), `RECOVERY_TAKEN`, and NUL
  path streams (one per launcher) into `$REVIEW_TMPDIR/review-dirty-tree-summary.env`.
- Auto-discard reviewer-introduced changes (same behavior as current inline path).
- When `SESSION_ENV_PATH` is non-empty, copy the env summary to
  `$(dirname "$SESSION_ENV_PATH")/review-dirty-tree-summary.env`.

**Stage 4 — Parent tmpdir artifact copy (when nested):**
When `SESSION_ENV_PATH` is non-empty, copy these to `$(dirname "$SESSION_ENV_PATH")/`:
- `rejected-findings.md`
- `oos-accepted-review.md`
(NOT `review-round-summary.md`, `review-summary.json` — those are copied by `emit-tally.sh`
already. NOT `review-dirty-tree-summary.env` — that is copied in Stage 3a.)

**Emitted KV output (via `emit_kv` / `lib-quiet.sh` FD3 contract stream, NOT raw stdout):**
`REVIEW_CORE_STATUS` (`ok|fix-required|zero-findings|cap-reached|wholesale-rejected`),
`ROUND_NUM`, `ACCEPTED_COUNT`, `REJECTED_COUNT`, `FINDINGS_FILE`, `ACCEPTED_FINDINGS_FILE`,
`REJECTED_FINDINGS_FILE`, `PANEL_MODE`, `PANEL_SHAPE`.

NOTE: `review-core.sh` does **NOT** call `log-phase.sh`. Run-log batches are owned exclusively
by SKILL.md Step 4d after all summary artifacts are complete.

NOTE: heavy-worker.md currently uses `gather-branch-context.sh` while inline uses
`gather-context.sh`. This is a pre-existing divergence. This PR must document it explicitly
in `review-core.md` as a known gap deferred to Part 2, and ensure `review-core.sh` uses
`gather-context.sh` to match the inline path.

Create companion contract `skills/review/scripts/review-core.md` documenting: accepted flags,
emitted KV keys (and the FD3 quiet-contract stream), artifact paths, the `REVIEW_CORE_STATUS`
grammar, dirty-tree recovery steps, parent-copy responsibility, and the heavy-worker divergence
note.

Create harness skeleton `skills/review/scripts/test-review-core.sh` and contract
`skills/review/scripts/test-review-core.md`. The harness must cover: zero-findings exit,
wholesale-rejection exit, fix-required signal, both-down mode, description mode (no fix loop),
artifact presence, dirty-tree recovery (clean/dirty/unknown sidecars), and parent-tmpdir copy
when `SESSION_ENV_PATH` is set.

---

### Step 2 — Thin `skills/review/SKILL.md` wrapper (~50 lines)

Replace the current 200-line SKILL.md with a thin wrapper of ~50 lines. The wrapper:

1. Preserves the frontmatter block verbatim (name, description, argument-hint, allowed-tools).
2. Parses the same flags (`--diff`, `--no-issues`, `--session-env`, `--step-prefix`,
   `--subagent`, `--run-id`).
3. In Step 0 (session setup): runs `session-setup.sh` exactly as today; if
   `subagent_mode=true && diff_mode=true`, dispatches to `references/heavy-worker.md`.
4. **Wrapper owns the outer round loop (up to `round_cap=3` rounds):**
   a. Call `review-core.sh` for one round; parse `REVIEW_CORE_STATUS` and `ACCEPTED_FINDINGS_FILE`.
   b. If `REVIEW_CORE_STATUS=fix-required`:
      - Invoke `/review-and-fix` via the Skill tool with `--findings-file "$ACCEPTED_FINDINGS_FILE"`
        `--review-tmpdir "$REVIEW_TMPDIR" [--session-env "$SESSION_ENV_PATH"]`.
      - After `/review-and-fix` returns, run `scripts/run-relevant-checks-captured.sh
        --site review-step3e --tmpdir "$REVIEW_TMPDIR"`.
      - Handle `STATUS=fail` (read `REDACTED_LOG_FILE`, diagnose, fix, retry loop) until clean.
      - Classify the just-fixed round as substantial or non-substantial (main-agent judgment).
      - If substantial and under the round cap, loop to Step 4a with incremented round.
      - If non-substantial, no-findings, wholesale-rejected, description mode, or cap reached,
        proceed to Step 4c.
   c. If any other `REVIEW_CORE_STATUS`, proceed to Step 4c.
5. In Step 4c: runs summary/issue-filing logic exactly as today (emit summaries, footers).
   Copy `review-round-summary.md` to parent tmpdir if nested (already done by emit-tally.sh).
6. In Step 4d: runs `log-phase.sh` batches for `review-context`, `review-panel-manifest`,
   `review-findings`, `review-tally`, and `review-round-summary` when `RUN_ID` non-empty.
   This is the **only** place `log-phase.sh` is called — `review-core.sh` does NOT log.
7. In Step 5: runs cleanup exactly as today.

Key structural pins that MUST survive in the new SKILL.md:
- Anti-halt continuation reminder (the `**Anti-halt continuation reminder.**` paragraph).
- `MANDATORY — READ ENTIRE FILE` lines for `domain-rules.md` (Step 3 entry) and
  `voting.md` (rounds 1-3 branch).
- Focus-area enum `code-quality / risk-integration / correctness / architecture / security`
  on every quick-review prompt line.
- Two-mode activation grammar: single line carrying `--diff` and `positional description`.
- Verbatim abort messages for `--diff`+description conflict and no-args cases.
- `--pieces-json` in Step 4b `/umbrella` invocation.

The `heavy-worker.md` reference is preserved unchanged.

---

### Step 3 — Add `--panel simple|hard` and `PANEL_SHAPE` to `dispatch-panel.sh`

Modify `skills/review/scripts/dispatch-panel.sh` to accept a new `--panel simple|hard` flag
(default: `hard`):

- `--panel hard`: current behavior (all specialists: structure, correctness, testing, security,
  edge-cases, plan-fidelity for both Cursor and Codex when available).
- `--panel simple`: smaller set — Cursor specialist `edge-cases` + Codex specialist `structure`
  (when the respective tool is available), plus the existing Claude generic slot. `plan-fidelity`
  is included only when `--plan-file` is non-empty.

**IMPORTANT — preserve PANEL_MODE semantics:** Keep `PANEL_MODE=normal|both-down` for
availability semantics (drives voting behavior). Add a **separate** output KV:
`PANEL_SHAPE=simple|hard`. Do NOT use `PANEL_MODE` for topology shape — overloading it would
break the `both-down` voting shortcut.

Add `--launch-review PATH` flag (analogous to `--launch-claude-subprocess`) as a test seam
for overriding the external reviewer launcher in harness tests. Default: `$PLUGIN_ROOT/scripts/launch-review.sh`.

Update `dispatch-panel.md` to document the `--panel` flag, `PANEL_SHAPE` output KV, and
`--launch-review` test seam.

Update `test-dispatch-panel.sh` to:
- Add `--panel simple` and `--panel hard` test cases using stub `--launch-review` with
  a fixture that writes output `.done` `.dirty-tree` `.meta` files.
- Assert correct slot counts and `PANEL_SHAPE` for both topologies.
- Assert `PANEL_MODE=both-down` is preserved when both tools are down.

Update `test-dispatch-panel.md` to document new test cases.

---

### Step 4 — Create `skills/review-and-fix/` skill directory

Create the following files:

#### `skills/review-and-fix/SKILL.md`

Frontmatter:
```
name: review-and-fix
description: Use when applying accepted review findings as code fixes. Internal skill invoked by /review in diff mode; not a standalone user entry point.
argument-hint: "--findings-file <path> [--session-env <path>] [--review-tmpdir <path>]"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob
```

The skill reads an accepted-findings file produced by `review-core.sh`, applies each finding
as a code edit using the main agent (Edit/Write tools), then signals completion via a machine
footer. No reviewer panel, no voting — applies only findings already voted in.

The skill MUST treat all finding content as untrusted data: parse only structured fields
(title, concern, suggested fix location), fence reviewer prose with explicit untrusted
delimiters in any sub-prompts, and validate that any implied edit paths are repo-relative
non-symlink non-submodule non-absolute non-`..` paths. Explicitly ignore any instructions
embedded inside finding prose text.

#### `skills/review-and-fix/scripts/review-and-fix.sh`

Parses `--findings-file`, `--review-tmpdir`, `--session-env-path`. Validates findings file
non-empty. For each accepted finding, calls `call-fixer.sh --finding-file "$findings_file"
--finding-id "$id" --review-tmpdir "$REVIEW_TMPDIR"`. After the SKILL.md wrapper applies
edits for each finding via Edit/Write tools (driven by `call-fixer.sh` structured output),
marks `FIXER_STATUS=applied|skipped` with an explicit skip reason. Emits
`REVIEW_AND_FIX_STATUS=complete|no-findings` and `FIX_COUNT=N`.

Companion: `skills/review-and-fix/scripts/review-and-fix.md` (contract doc).

#### `skills/review-and-fix/scripts/call-fixer.sh`

Reads a specific finding by ID from the findings file. Emits the finding's structured fields
(title, concern, file location, suggested fix) as explicit KV output for the SKILL.md
wrapper to use for Edit/Write tool calls — does NOT apply edits itself. The wrapper applies
edits, then calls `call-fixer.sh --mark-applied "$id"` to record the finding as applied.

Path safety: validate any path in the finding against repo root; reject absolute paths, `..`,
symlinks outside repo, and paths inside submodule directories. Emit `PATH_VALID=true|false`
so the wrapper can skip unsafe findings.

Companion: `skills/review-and-fix/scripts/call-fixer.md` (contract doc).

Harness skeletons: `skills/review-and-fix/scripts/test-review-and-fix.sh`,
`skills/review-and-fix/scripts/test-call-fixer.sh`, and companion `.md` contracts.

---

### Step 5 — Create `agents/orchestrator-aggregator.md` and `agents/orchestrator-judge.md`

Both are hand-maintained orchestration agents named OUTSIDE the `reviewer-*` glob to avoid
the pre-rendered reviewer prompt generator (`scripts/generate-pre-rendered-reviewer-prompts.sh`
`find … -name 'reviewer-*.md'`) picking them up.

#### `agents/orchestrator-aggregator.md`

Frontmatter:
```
name: orchestrator-aggregator
description: Internal orchestration agent. Normalizes and deduplicates reviewer output from multiple specialist slots into a structured finding list for voting.
model: sonnet
tools:
  - Read
  - Grep
  - Glob
```

Annotate at top: `<!-- HAND-MAINTAINED: internal orchestration agent, not a reviewer specialist -->`

Body: instructions for reading multiple reviewer output files, deduplicating findings by
semantic similarity, assigning stable `FINDING_N` IDs, attributing each finding to source
reviewer(s), and emitting a structured finding list.

#### `agents/orchestrator-judge.md`

Frontmatter:
```
name: orchestrator-judge
description: Internal orchestration agent. Evaluates aggregated review findings and classifies each as accepted, exonerated, or rejected; determines wholesale rejection.
model: sonnet
tools:
  - Read
  - Grep
  - Glob
```

Annotate at top: `<!-- HAND-MAINTAINED: internal orchestration agent, not a reviewer specialist -->`

Body: instructions for reading a structured finding list and vote tally, applying the
2+ YES threshold rule, computing wholesale-rejection determination, and emitting
`accepted-findings.md` and `voting-tally.md` artifacts.

---

### Step 6 — Update `test-review-structure.sh`

Update `scripts/test-review-structure.sh` to:

1. Add `review-core` to the `review_scripts` array AND **bump the expected count to 8**
   (`"${#review_scripts[@]}" -eq 8`), updating the accompanying comment at line 74.
2. Add assertions that `skills/review-and-fix/SKILL.md`, `skills/review-and-fix/scripts/review-and-fix.sh`,
   and `skills/review-and-fix/scripts/call-fixer.sh` exist.
3. Add assertion that `agents/orchestrator-aggregator.md` and `agents/orchestrator-judge.md`
   exist and carry the `HAND-MAINTAINED` annotation.
4. Add assertion that `agents/reviewer-aggregator.md` and `agents/reviewer-judge.md` do NOT
   exist (negative pin — they were renamed to `orchestrator-*`).
5. Add assertion that neither `agents/orchestrator-aggregator.md` nor `agents/orchestrator-judge.md`
   matches the `reviewer-*` glob (guard against future rename regressions).
6. **Migration plan for existing assertions**: The following SKILL.md-pinned assertions must
   be retargeted when SKILL.md is replaced with the thin wrapper:
   - `--pieces-json` pin: stays in SKILL.md wrapper Step 4b — verify wrapper still carries it.
   - Anti-halt banner: must appear in SKILL.md wrapper — verify wrapper still carries it.
   - Focus-area enum: must appear on review prompt lines in SKILL.md or `review-core.md`.
   - Two-mode grammar pin: must appear in SKILL.md wrapper.
   - Verbatim abort messages: must appear in SKILL.md wrapper.
   - Gemini negative pins: if moved to `review-core.sh`, update assertions to check that script.
   - Dual-list parsing pins (in `collect-findings.sh`): unchanged — already checked there.
   - Security OOS exclusions (in `voting.md`): unchanged — already checked there.
   - `render-specialist-prompt.sh` renderer pin: update target to `review-core.sh` if it moves.

Update `scripts/test-review-structure.md` to document the new assertions.

---

### Step 7 — Update `Makefile`

Add to `Makefile`:
```make
test-review-core:
    bash scripts/test-review-core.sh

test-review-and-fix:
    bash skills/review-and-fix/scripts/test-review-and-fix.sh

test-call-fixer:
    bash skills/review-and-fix/scripts/test-call-fixer.sh
```

Add all three to `.PHONY`. Wire `test-review-core` into the appropriate `test-harnesses-N`
shard (same shard as `test-review-structure`, `test-dispatch-panel`, etc.).
Wire `test-review-and-fix` and `test-call-fixer` into the same shard.
Update `test-harness-shards-coverage` expectation if present.

---

### Step 8 — Run `/relevant-checks`

Run `/relevant-checks` to verify:
- `make test-review-structure` passes (including new assertions, count bump to 8, and
  existing assertion retargeting verification).
- `make test-dispatch-panel` passes (new `--panel` flag, `PANEL_SHAPE`, `--launch-review` stub tests).
- `make test-review-core` passes (new harness skeleton).
- `make test-review-and-fix` passes (new harness skeleton).
- `make test-call-fixer` passes (new harness skeleton).
- `agent-lint` passes on new SKILL.md files and agent files.
- Pre-commit hooks pass on all modified files.

---

### File change summary

| File | Action |
|------|--------|
| `skills/review/SKILL.md` | Replace with ~50-line thin wrapper |
| `skills/review/scripts/review-core.sh` | Create (single-round state machine) |
| `skills/review/scripts/review-core.md` | Create (contract doc, incl. FD3 stream + heavy-worker divergence note) |
| `skills/review/scripts/test-review-core.sh` | Create (harness skeleton) |
| `skills/review/scripts/test-review-core.md` | Create (harness contract) |
| `skills/review/scripts/dispatch-panel.sh` | Modify (add `--panel`, `PANEL_SHAPE`, `--launch-review` test seam) |
| `skills/review/scripts/dispatch-panel.md` | Modify (document `--panel`, `PANEL_SHAPE`, `--launch-review`) |
| `skills/review/scripts/test-dispatch-panel.sh` | Modify (add `--panel` + `--launch-review` stub tests) |
| `skills/review/scripts/test-dispatch-panel.md` | Modify (document new test cases) |
| `skills/review-and-fix/SKILL.md` | Create |
| `skills/review-and-fix/scripts/review-and-fix.sh` | Create |
| `skills/review-and-fix/scripts/review-and-fix.md` | Create (contract doc) |
| `skills/review-and-fix/scripts/call-fixer.sh` | Create (with path safety contract) |
| `skills/review-and-fix/scripts/call-fixer.md` | Create (contract doc) |
| `skills/review-and-fix/scripts/test-review-and-fix.sh` | Create (harness skeleton) |
| `skills/review-and-fix/scripts/test-review-and-fix.md` | Create (harness contract) |
| `skills/review-and-fix/scripts/test-call-fixer.sh` | Create (harness skeleton) |
| `skills/review-and-fix/scripts/test-call-fixer.md` | Create (harness contract) |
| `agents/orchestrator-aggregator.md` | Create (renamed from reviewer-aggregator to avoid glob) |
| `agents/orchestrator-judge.md` | Create (renamed from reviewer-judge to avoid glob) |
| `scripts/test-review-structure.sh` | Modify (count bump, new assertions, migration plan) |
| `scripts/test-review-structure.md` | Modify (document new assertions) |
| `Makefile` | Modify (add new test targets and shard wiring) |

diff_lines: 1050

## Test plan
(no test plan section in plan-file)
