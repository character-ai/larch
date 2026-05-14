---
name: design
description: "Use when designing non-trivial features, refactors, or architecture changes. Adaptive sketches (0 trivial, 2 quick/simple, 4 full) propose approaches; 10-reviewer panel (5 personalities × 2 tools) validates via 3-voter dialectic."
argument-hint: "[--auto] [--quick] [--full] [--subagent] [--session-env <path>] [--design-classification <value>] <feature description>"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob, Agent, Task, WebFetch, WebSearch
---

# Design Skill

Design an implementation plan for a feature and review it with a 10-reviewer panel (5 personalities × Cursor + Codex: Arch, Edge, Innovation, Pragmatic, Requirements — each personality runs on both tools), adjudicated by a 3-voter panel (Claude + Codex + Cursor). The sketch phase (Step 2a) reads `run-params.json` and runs 0 agents for codebase-scan-confirmed trivial doc-only work, 2 generic agents for quick/simple work, or 4 agents in full mode (Cursor-Arch + Cursor-Edge + Codex-Innovation + Codex-Pragmatic — one personality per vendor in a diagonal split).

**Flags**: Parse flags from the start of `$ARGUMENTS` before treating the remainder as the feature description. Flags may appear in any order; stop at the first non-flag token. **All boolean flags default to `false`. Only set a flag to `true` when its `--flag` token is explicitly present in the arguments. Flags are independent — the presence of one flag must not influence the default value of any other flag.**

| Flag | Default | Purpose | Load-bearing detail |
|------|---------|---------|---------------------|
| `--auto` | `false` | Skip interactive question checkpoints (1c, 1d, 3.5) | No-op when `/implement --quick` skips `/design` entirely; dirty-tree recovery prompts are not suppressed |
| `--quick` | `false` | Quick review mode; caps sketch fan-out at 2 unless `--full` is also set | Independent of `--auto`; see `flags.md` for `/implement --quick` vs `/design --quick` distinction |
| `--full` | `false` | Force full sketch fan-out | Sets `full_mode=true`; forces `sketch_budget=4` even with `--quick`; plan review still follows `quick_mode` |
| `--subagent` | `false` | Run Step 2a heavy phase in an isolated Agent-tool subagent (`heavy-worker.md`); writes artifacts only to `$DESIGN_TMPDIR/` and returns terse status; standalone (`--session-env` empty) parents replay artifacts before cleanup | No-op when `--quick` is set; orthogonal to `--session-env` |
| `--session-env <path>` | empty | Forward discovered session values to `session-setup.sh` | Empty = standalone invocation, full discovery |
| `--step-prefix <prefix>` | empty | Nested-numbering prefix from `/implement` | `::` delimiter splits numeric prefix, breadcrumb path, and optional parent skill path; `"1."` (bare numeric) is backward-compat |
| `--branch-info <values>` | — | Skip redundant branch-state check when called from `/implement` | 4 keys required: `IS_MAIN`/`IS_USER_BRANCH`/`USER_PREFIX`/`CURRENT_BRANCH`; fallback on validation failure to `create-branch.sh --check`; power-user / nested-call flag with no standalone value validation |
| `--design-classification <value>` | empty | Accept caller-forwarded `TRIVIAL_DOC_ONLY`/`SIMPLE`/`HARD` classification | Trusted only when `branch_info_supplied=true`; standalone `/design` ignores it and classifies locally |
| `--run-id <ID>` | empty | Optional run identifier | When set, used as the run ID for this invocation instead of the auto-generated one |

**MANDATORY — READ ENTIRE FILE before parsing argument flags**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` completely. This reference is the single normative source for flag semantics — validation rules, fallback behaviors, `::` delimiter encoding spec, 4-key `--branch-info` requirement, and backward-compat notes. The table above is a non-normative index.

The feature to design is described by the remainder of `$ARGUMENTS` after flags are stripped.

**Anti-halt continuation reminder.** After every `Bash` tool call that completes a numbered step or sub-step, and after every visible output (plans, diagrams, voting tallies, skip breadcrumbs), IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on a Bash result, a status message, or a deliverable-looking output, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. This applies to ALL step boundaries from Step 0 through Step 5, and to ALL sub-step transitions (1c→1d→2a→2a.5→2b→3→3.5→3b→4→5). **Critical: the implementation plan (Step 2b) and architecture diagram (Step 3b) are intermediate deliverables, NOT the end of the design — plan review (Step 3) and cleanup (Step 5) must still execute.** The rule is strictly subordinate to any explicit non-sequential control-flow directive in THIS file (e.g., `skip to Step N`, `bail to cleanup`, `jump back`, `proceed to Step N`). A normal sequential `proceed to Step N+1` instruction is the default continuation this rule reinforces, NOT an exception.

## Progress Reporting

**Every step MUST print clearly visible breadcrumb status lines** so the user can instantly see where execution is and which parent steps they are inside. Follow shared/progress-reporting.md rules.

- Print a **start line** when entering a step: e.g., `> **🔶 /design 1: branch**` (standalone) or `> **🔶 /implement:/design 1.1: design plan | branch**` (nested from `/implement`)
- Do not print step completion lines; start breadcrumbs are the visible step markers.
- When `STEP_NUM_PREFIX` is non-empty, prepend it to step numbers: `{STEP_NUM_PREFIX}{local_step}`. When `STEP_PATH_PREFIX` is non-empty, prepend it to breadcrumb paths: `{STEP_PATH_PREFIX} | {step_short_name}`. When `PARENT_SKILL_PATH` is non-empty, print the skill path as `{PARENT_SKILL_PATH}:/design`; otherwise print `/design`. **This rule overrides the literal skill paths, step numbers, and names in `Print:` directives and examples throughout this file.** Examples shown below assume standalone mode; when nested, prepend the parent context and parent skill path.

**MANDATORY at session start**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/step-name-registry.tsv` to get the Step Name Registry (step number → short name mapping for progress breadcrumbs).

### Verbosity Control

- Use empty string for the `description` parameter on all Bash tool calls.
- Use terse 3-5 word descriptions for Agent tool calls.
- Do not produce explanatory prose between tool call outputs — only print: step breadcrumb lines (start `🔶`, skip `⏩`), all warning/error lines (`**⚠ ...`), structured summaries (voting tallies, scoreboards, round summaries, findings lists, approach synthesis, dialectic resolutions, implementation plans, architecture diagrams), and the compact reviewer status table (see below).

**Suppressed output:** explanatory prose, script paths, rationale for decisions between tool calls, per-reviewer individual completion messages.

When `SESSION_ENV_PATH` is non-empty (nested under `/implement`), follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Artifact-only return contract (nested mode): suppress step breadcrumbs and bulky inline artifact bodies for the implementation plan, voting tally, architecture diagram, rejected findings, and discussion syntheses; rely on the files under `$DESIGN_TMPDIR/` plus the Step 5 design manifest. When `SESSION_ENV_PATH` is empty (standalone `/design`), preserve the existing verbose inline output and skip manifest export entirely.

**Compact reviewer status table**: After launching sketch agents (Step 2a) or plan reviewers (Step 3), maintain a mental tracker of each agent's status. Print a compact table after EACH status change:

```
📊 Sketches (regular): | Cursor-Arch: ⏳ | Cursor-Edge: ✅ 3m5s | Codex-Innovation: ❌ 8m3s | Codex-Pragmatic: ✅ 4m2s |

📊 Sketches (quick): | Cursor-Generic: ⏳ | Codex-Generic: ✅ 3m5s |

or for Step 3 plan review (10-reviewer panel):

📊 Reviewers: | Cursor-Arch: ✅ 4m12s | Cursor-Edge: ⏳ | Cursor-Innovation: ⏳ | Cursor-Pragmatic: ✅ 2m31s | Cursor-Requirements: ⏳ | Codex-Arch: ⏳ | Codex-Edge: ✅ 3m10s | Codex-Innovation: ⏳ | Codex-Pragmatic: ✅ 2m31s | Codex-Requirements: ⏳ |
```

Icons: ✅ done (with elapsed time since launch), ⏳ pending/in-progress, ❌ failed/timeout (with elapsed time since launch), ⊘ skipped (unavailable). This replaces individual per-agent completion messages. → shared/progress-reporting.md

**Limitation**: Verbosity suppression is prompt-enforced and best-effort.

## Design Mindset

Before invoking `/design`, the orchestrator should internalize these questions. They bias every subsequent choice — sketch synthesis, plan drafting, review-finding acceptance — and are the thinking pattern this skill transfers along with its mechanical procedures.

- **What is the smallest change that achieves the goal?** Resist adding abstractions, flags, or layers the feature description did not ask for. Every additional moving part is a new failure mode.
- **Where is anchoring risk highest?** The first plausible approach locks architectural direction unless the sketch phase forces alternatives. Do NOT skip Step 2a (anti-pattern rule #1).
- **What hidden constraints must this preserve?** Canonical sources, CI invariants, downstream parsers, contract tokens, byte-preserved reference files. Identify them before edits, not during plan review.
- **Which tradeoffs should surface to the user versus be quietly chosen?** Scope and hard-constraint decisions surface via Round 1 discussion; architectural preferences belong to the sketch phase — not to the user.
- **Which anti-patterns in the NEVER list below apply to this specific feature?** Re-read the Anti-patterns section for every non-trivial feature; muscle memory for the six rules is the expert delta this skill aims to transfer.

## Anti-patterns

Consolidated NEVER rules collected from the procedural steps below. Each rule states the WHY so edits can respect the original constraint. Inline step-local mentions remain where they carry load-bearing context.

1. **NEVER skip Step 2a** (the sketch phase), except for the router-confirmed trivial-task carve-out. **Why:** anchoring bias locks architectural direction before alternatives are considered. **How to apply:** normally run the configured `sketch_budget` slots (4 full or 2 quick/simple), with Claude fallbacks preserving the configured lane count when externals are unavailable. **Exception:** when the Step 0 router classifies `TRIVIAL_DOC_ONLY` after a codebase scan, `sketch_budget=0` is permitted. The router/Step 2a path must write sentinel stubs (`approach-synthesis.txt` = `NO_SKETCHES_CLASSIFIED_TRIVIAL`, `contested-decisions.md` = `NO_CONTESTED_DECISIONS`, and empty `dialectic-resolutions.md`) so downstream steps have stable inputs.

2. **NEVER substitute a Claude subagent into a dialectic debate bucket.** **Why:** the debate path is externals-only (Cursor/Codex) because model-specific writing style could encode tool identity into adversarial arguments; the judge path uses the repo-wide replacement-first pattern because judges merely adjudicate pre-authored defenses. See GitHub issue #98. **How to apply:** Step 2a.5 skips debate buckets whose assigned tool is unavailable — do NOT reassign to Claude. Judge-panel slots (after debate) DO use Claude replacements per `dialectic-protocol.md`.

3. **NEVER mutate orchestrator-wide `codex_available` / `cursor_available` inside Step 2a.5.** **Why:** Step 3 plan-review panel integrity depends on the Option B snapshot pattern — a debate-phase timeout must not lock a tool out of later plan review. **How to apply:** use the `dialectic_*_available` shadow flags inside Step 2a.5 and the `judge_*_available` shadow flags inside the judge re-probe; never touch the top-level flags.

4. **NEVER pass `--caller-env` or `--write-health` to `session-setup.sh` when `SESSION_ENV_PATH` is empty.** **Why:** standalone `/design` invocations have no parent `/implement` to consume the session-env or health artifacts. **How to apply:** branch on `SESSION_ENV_PATH` non-empty in Step 0; omit both flags when standalone.

5. **NEVER call `collect-agent-results.sh` with zero positional arguments.** **Why:** it exits 1 with "at least one output file is required". This is the zero-externals failure mode when every external slot has fallen back to a Claude subagent. **How to apply:** guard each collector call with an explicit check that at least one external slot was launched; the dialectic zero-externals guardrail (Step 2a.5 step 5) and the Step 3 collector both require this.

6. **NEVER conflate the two timeout families.** **Why:** sketch-phase timeouts (sketches are shorter) differ from plan-review + dialectic timeouts (longer, deeper reasoning). **How to apply:** use `timeout: 1260000` (Bash tool) / `--timeout 1260` (collector) / `--timeout 1200` (reviewer script) for sketch-phase launches and sketch collection; use `timeout: 1860000` / `--timeout 1860` / `--timeout 1800` for plan-review launches, dialectic debaters, and dialectic judges.

7. **NEVER emit step breadcrumbs when `SESSION_ENV_PATH` is non-empty.** **Why:** nested `/design` runs under `/implement`, whose parent-visible transcript must obey the artifact-only return contract. **How to apply:** write human-readable content to `$DESIGN_TMPDIR` artifacts, export the Step 5 design manifest, and emit only file-backed artifact paths plus the manifest machine footer.

<!-- step:0 — Session Setup -->
## Step 0 — Session Setup

Print: `> **🔶 /design 0: setup**`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 0 — session setup" || true
```

Define `branch_info_supplied=true` only when the caller passed valid `--branch-info` containing all 4 keys: `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`, and `CURRENT_BRANCH`. `SESSION_ENV_PATH` being non-empty is not a nesting signal by itself; `--session-env` is an exposed argument and can be passed manually.

If `branch_info_supplied=true` (trusted caller-supplied branch state, normally from `/implement`), use the parsed `--branch-info` values for `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, and `USER_PREFIX`. The four key values are accepted as-is and not cross-checked against the working tree (see the `--branch-info` "Sharp edge" note in `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md`). `/implement` is presumed to have already run the entry gate, so `session-entry-gate.sh` below will emit `SKIP_BRANCH_CHECK=true`.

If `branch_info_supplied=false` (standalone, regardless of `SESSION_ENV_PATH`), check the current branch before setup:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check
```

Parse `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, and `USER_PREFIX` from stdout.

Run the shared entry gate helper using the parsed branch facts. Its contract lives at `${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.md`.

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh \
  --mode design \
  --current-branch "$CURRENT_BRANCH" \
  --is-main "$IS_MAIN" \
  --is-user-branch "$IS_USER_BRANCH" \
  --user-prefix "$USER_PREFIX" \
  --branch-info-supplied "$branch_info_supplied"
```

Parse `ENTRY_GATE` and `SKIP_BRANCH_CHECK` from this script's stdout in isolation. Do not concatenate it with `create-branch.sh --check` output for a single `eval`. On non-zero exit, print the raw `GATE_ERROR=...` line first, then print the normalized internal-contract message and abort:

**⚠ /design: internal Step 0 contract violation in session-entry-gate.sh. Aborting.**

Do NOT print the clean-main banner for `GATE_ERROR`; that banner is reserved for `session-setup.sh` `PREFLIGHT_ERROR`.

If `SKIP_BRANCH_CHECK=true`, run setup with `--skip-branch-check`:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-design --skip-branch-check --skip-repo-check --check-reviewers [--caller-env "$SESSION_ENV_PATH"] [--skip-codex-probe] [--skip-cursor-probe] [--write-health "${SESSION_ENV_PATH}.health"]
```

If `SKIP_BRANCH_CHECK=false`, run setup without `--skip-branch-check`; `preflight.sh` runs in default mode and enforces clean `main` plus fetch/rebase before design work begins:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-design --skip-repo-check --check-reviewers [--caller-env "$SESSION_ENV_PATH"] [--skip-codex-probe] [--skip-cursor-probe] [--write-health "${SESSION_ENV_PATH}.health"]
```

Only include `--caller-env "$SESSION_ENV_PATH"` and `--write-health "${SESSION_ENV_PATH}.health"` if `SESSION_ENV_PATH` is non-empty. This Anti-pattern #4 predicate is orthogonal to `branch_info_supplied`: session-env controls parent health I/O; branch-info controls whether `/design` trusts `/implement`'s already-gated branch state. If `SESSION_ENV_PATH` provides `CODEX_HEALTHY=false` or `CURSOR_HEALTHY=false`, the script auto-sets the corresponding `--skip-codex-probe` / `--skip-cursor-probe` flag — you do not need to pass these explicitly when using `--caller-env`.

If the script exits non-zero, always print the raw `PREFLIGHT_ERROR=...` line first. Then print the normalized skill-level message and abort:

**⚠ /design requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run (the branch naming convention is the explicit opt-in to continue from current state); (c) commit or stash uncommitted changes on `main` first.**

Parse the output for `SESSION_TMPDIR`, `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`. Set `DESIGN_TMPDIR` = `SESSION_TMPDIR`. Substitute the actual path in every command below.

Set mental flags `codex_available` and `cursor_available` based on the output:
- If `CODEX_AVAILABLE=false`: `codex_available=false`. Print: `**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**`
- Else if `CODEX_HEALTHY=false`: `codex_available=false`. Print: `**⚠ Codex installed but not responding (health check failed). Using Claude replacement.**`
- Else: `codex_available=true`
- Same logic for Cursor.

The `--write-health` flag writes the health status file for cross-skill propagation. It will be updated by `collect-agent-results.sh --write-health` during runtime if any reviewer times out.

**Execution-issues logging for nested runs**: When `SESSION_ENV_PATH` is non-empty, the parent log is `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`. Any failing Bash tool, external reviewer launch, external reviewer collector status not equal to `OK`, or Agent-tool fallback failure must append the full captured stdout/stderr or returned text verbatim through `${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh` under `External Reviewer Issues` (or `Warnings` for diagram generation/sanitizer failures). Capture into a `$DESIGN_TMPDIR/*-failure.log` file first; include `${OUTPUT}.diag` sidecar content for reviewer collector failures. Do not summarize or truncate these captures.

<!-- step:0 tail — Run-Depth Router -->

After `session-setup.sh` returns and `DESIGN_TMPDIR` is confirmed, compute run parameters once and write them to `$DESIGN_TMPDIR/run-params.json`:

1. If `--design-classification <value>` was supplied AND `branch_info_supplied=true`, accept the forwarded value (`TRIVIAL_DOC_ONLY`, `SIMPLE`, or `HARD`) without re-classifying. Set `design_classification_source=caller-forwarded`.
2. Otherwise, write the feature text to `$DESIGN_TMPDIR/feature-description.txt` and classify through the ACTION driver. Set `design_classification_source=router-pre-design` for `write-run-params.sh`; the richer `CLASSIFICATION_SOURCE=deterministic|cursor-validated|cursor-fallback` value from `classify-issue.sh` is diagnostic stdout only and is not written to `run-params.json`.

```bash
printf '%s\n' "$FEATURE_DESCRIPTION" > "$DESIGN_TMPDIR/feature-description.txt"
printf 'ACTION=CLASSIFY ARGS=--feature-description %s\n' "$DESIGN_TMPDIR/feature-description.txt" \
  | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
```

Parse `CLASSIFICATION=<value>` and `CLASSIFICATION_REASON=<text>` from the driver output. If the driver exits non-zero or emits no valid classification, default to `HARD` with reason `classification failed`.
3. `TRIVIAL_DOC_ONLY` is allowed only when the codebase scan confirms the change is documentation/prose-only and no runtime files, scripts, hooks, generated artifacts, or security behavior need edits. If the scan cannot confirm that, default to `SIMPLE`.
4. Derive `sketch_budget`: if `full_mode=true`, use `4`; else if `quick_mode=true`, use `min(classification_budget, 2)` — where `classification_budget` is derived in the next step (so `TRIVIAL_DOC_ONLY -> 0`, `SIMPLE -> 2`, `HARD -> 4`; the min preserves the 0-budget path, not just caps non-trivial tasks); else use `classification_budget` directly.
5. Derive `review_budget`: `quick` when `quick_mode=true`, otherwise `full`.
6. Derive `workflow_path`: `SIMPLE` for `TRIVIAL_DOC_ONLY` or `SIMPLE`, otherwise `HARD`.

Write the file using the shared helper:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/write-run-params.sh \
  --classification "$design_classification" \
  --reason "$design_classification_reason" \
  --source "$design_classification_source" \
  --sketch-budget "$sketch_budget" \
  --review-budget "$review_budget" \
  --workflow-path "$workflow_path" \
  --output "$DESIGN_TMPDIR/run-params.json"
```

If the helper exits non-zero, print `**⚠ 0: router — run-params write failed; defaulting to HARD sketch budget.**`, set in-memory defaults `design_classification=HARD`, `sketch_budget=4`, `review_budget=full`, `workflow_path=HARD`, and continue. Consumers treat missing or schema-invalid `run-params.json` the same way.

<!-- step:1 — Create Branch -->

Print: `> **🔶 /design 1: branch**`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 1 — branch" || true
```

### 1a — Check current branch state

**If `branch_info_supplied=true`** (via `--branch-info`): Use the values parsed from the flag (`CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`). Skip the `create-branch.sh --check` call.

**Otherwise** (standalone invocation or validation failed): Use the values parsed from Step 0's standalone `create-branch.sh --check` call. If Step 0 did not capture those values for any reason, run the `create-branch.sh` script in check mode before proceeding:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check
```

Parse the output for `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, and `USER_PREFIX`.

### 1b — Decide action

**Decision logic** (using the script output):
- If `IS_MAIN=true`: Derive a short kebab-case branch name from the feature description (e.g., "add user auth" → `<USER_PREFIX>/add-user-auth`). Keep it under 50 characters. Then create it:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --branch <USER_PREFIX>/<branch-name>
  ```

- If `IS_USER_BRANCH=true`: Verify the branch name (`CURRENT_BRANCH`) aligns with the requested feature. If it appears unrelated (different feature name, unrelated commits), print a warning: `**⚠ Current branch '<branch-name>' may not match the requested feature. Creating a new branch from main.**` and create a new branch as above. Otherwise, skip branch creation. Print: `> **🔶 /design 1: branch — using existing: <branch-name>**`

- Otherwise (non-main, non-user branch): Print a warning: `**⚠ Currently on branch '<branch-name>' which doesn't match the expected '<USER_PREFIX>/*' pattern. Creating a new branch from main.**` Then derive a name and create as above.

<!-- step:1c — Clarifying Questions -->

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 1c — questions" || true
```

Print: `> **🔶 /design 1c: questions**`

**If `auto_mode=true`**: Print `⏩ 1c: questions — skipped (auto mode) (<elapsed>)` and proceed to Step 1d.

**If `auto_mode=false`**: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/discussion-rounds.md` completely. Execute the Step 1c body in that file. **Do NOT load `discussion-rounds.md` when `auto_mode=true`** — the short-circuit above exits first.

<!-- step:1d — Design Discussion (Round 1) -->

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 1d — discussion r1" || true
```

Print: `> **🔶 /design 1d: discussion r1**`

**If `auto_mode=true`**: Print `⏩ 1d: discussion r1 — skipped (auto mode) (<elapsed>)` and proceed to Step 2a.

**If `auto_mode=false`**: Execute the Step 1d body in `${CLAUDE_PLUGIN_ROOT}/skills/design/references/discussion-rounds.md`. If already loaded at Step 1c, no need to re-load; otherwise **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/discussion-rounds.md` completely.

<!-- step:2a — Collaborative Approach Sketches -->
## Step 2a — Collaborative Approach Sketches

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 2a — sketches" || true
```

Before branching, read `$DESIGN_TMPDIR/run-params.json` and parse `sketch_budget`. Valid values are `0`, `2`, and `4`. If the file is absent or schema-invalid, default to `sketch_budget=4`. `review_budget` is consumed later by Step 3. Do not re-classify here; Step 0 owns router judgment.

**IMPORTANT: The collaborative sketch phase MUST run with the configured `sketch_budget` — 4 in full mode, 2 in quick/simple mode, or 0 only for codebase-scan-confirmed `TRIVIAL_DOC_ONLY` (using Claude replacements when external tools are unavailable on non-zero budgets). Never abbreviate a non-zero sketch budget regardless of how simple or obvious the feature appears. The sketch synthesis is required architectural input for the implementation plan — skipping it outside the explicit zero-sketch carve-out causes anchoring bias where a single perspective locks in the direction before alternatives are considered.**

A diverge-then-converge phase where multiple agents independently produce short architectural sketches before writing the full plan. This surfaces different perspectives early — when they can still influence architectural direction — rather than waiting for review when the plan is already anchored.

### Zero-sketch mode (`sketch_budget=0`) — no sketch agents

This path is allowed only when Step 0 classified `TRIVIAL_DOC_ONLY` after a codebase scan. Launch no external agents and no Claude fallback agents. Write sentinel artifacts:

```bash
printf '%s\n' 'NO_SKETCHES_CLASSIFIED_TRIVIAL' > "$DESIGN_TMPDIR/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' > "$DESIGN_TMPDIR/contested-decisions.md"
: > "$DESIGN_TMPDIR/dialectic-resolutions.md"
```

Skip Step 2a.5 and proceed directly to Step 2b. Do NOT call `collect-agent-results.sh`.

### Regular mode (`sketch_budget=4`) — 4 sketch agents

The 4 sketch agents are **2 Cursor + 2 Codex**, with per-slot Claude fallback when an external tool is unavailable:

1. **Cursor — Architecture/Standards** — or **Claude (Architecture/Standards)** fallback.
2. **Cursor — Edge-cases/Failure-modes** — or **Claude (Edge-cases/Failure-modes)** fallback.
3. **Codex — Innovation/Exploration** — or **Claude (Innovation/Exploration)** fallback.
4. **Codex — Pragmatism/Safety** — or **Claude (Pragmatism/Safety)** fallback.

When the assigned external is unavailable, the slot's Claude fallback uses the same personality prompt; the configured 4-agent shape is preserved.

### Quick/simple mode (`sketch_budget=2`) — 2 sketch agents

1. **Cursor — Generic** — or **Claude (Generic)** fallback: a broad-scope sketch without personality specialization.
2. **Codex — Generic** — or **Claude (Generic)** fallback: same generic prompt as Cursor-Generic.

### Heavy phase dispatch (regular and quick mode)

Print `> **🔶 /design 2a: sketches**`.

**Subagent heavy phase**: If `subagent_mode=true` (i.e., `--subagent` was passed) AND `quick_mode=false`, invoke a single Agent-tool subagent (subagent_type: `general-purpose`) for the heavy non-interactive phase before entering 2a.2. The subagent MUST read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/heavy-worker.md`, receive `DESIGN_TMPDIR`, `IMPLEMENT_TMPDIR`, `SESSION_ENV_PATH`, `FEATURE_DESCRIPTION`, `quick_mode`, `auto_mode`, `$DESIGN_TMPDIR/run-params.json`, branch info, and reviewer health flags as explicit data, and write raw artifacts to `$DESIGN_TMPDIR/`. The subagent returns a terse KV block whose first line is `DESIGN_HEAVY=complete` (optionally followed by `DESIGN_SUMMARY_FILE=<path>`) or a single failure line `DESIGN_HEAVY=failed REASON=<short-token>`; it does not write the manifest and does not return plan/reviewer/tally prose.

Immediately after the Agent tool returns, parse the heavy-worker status line. Before following the success path, fail closed if the worker omitted a valid status line or returned success without the required artifacts. The gate has two tiers, drawn from two distinct normative sources: **Tier 1 (non-empty)** for substantive artifacts the `heavy-worker.md` "Artifact Contract" mandates as non-empty regardless of manifest export; **Tier 2 (must-exist)** for may-be-empty artifacts that `skills/design/scripts/write-design-manifest.sh` requires on disk for manifest export (`copy_required_may_be_empty` calls in that script). On the nested+`auto_mode=true` path, parent Step 4 (which creates missing empty files) is skipped, so Tier 2 is the load-bearing existence check before manifest export at Step 5; Tier 1 is the heavy-worker contract check independent of manifest export.

```bash
if [[ "${DESIGN_HEAVY:-}" != "complete" && "${DESIGN_HEAVY:-}" != "failed" ]]; then
  DESIGN_HEAVY=failed
  REASON=worker-yielded-without-artifacts
elif [[ "${DESIGN_HEAVY:-}" == "complete" ]] && {
  [[ ! -s "$DESIGN_TMPDIR/plan.txt" ]] ||
  [[ ! -s "$DESIGN_TMPDIR/diff-lines.txt" ]] ||
  [[ ! -s "$DESIGN_TMPDIR/approach-synthesis.txt" ]] ||
  [[ ! -s "$DESIGN_TMPDIR/voting-tally.md" ]] ||
  [[ ! -f "$DESIGN_TMPDIR/contested-decisions.md" ]] ||
  [[ ! -f "$DESIGN_TMPDIR/oos.md" ]] ||
  [[ ! -f "$DESIGN_TMPDIR/rejected-findings.md" ]] ||
  [[ ! -f "$DESIGN_TMPDIR/accepted-plan-findings.md" ]]
}; then
  DESIGN_HEAVY=failed
  REASON=worker-yielded-without-artifacts
fi
```

Tier 1 (non-empty `-s` checks) pins the substantive artifacts mandated as non-empty by `heavy-worker.md` "Artifact Contract"; this tier is independent of manifest export and includes `approach-synthesis.txt`, which `write-design-manifest.sh` does not stage. `diff-lines.txt` is included because `/implement` Step 1 reads it from `design-export/` for the `diff_lines < 30` coder carve-out. Tier 2 (existence `-f` checks) pins may-be-empty manifest-required artifacts (`contested-decisions.md`, `oos.md`, `rejected-findings.md`, `accepted-plan-findings.md`) that `write-design-manifest.sh` stages via `copy_required_may_be_empty`. Two artifacts are intentionally NOT in the gate: `dialectic-resolutions.md` (`heavy-worker.md` "Artifact Contract" requires it as an empty file when dialectic does not run, but `dialectic-protocol.md` allows absence on the `NO_CONTESTED_DECISIONS` short-circuit and the zero-externals guardrail — adding `-f` would false-positive on those legitimate paths until the two normative sources are reconciled, which is out of scope for this gate) and `architecture-diagram.md` (optional; `auto_mode=true` only). A failure from this gate routes through the normal `DESIGN_HEAVY=failed` branch below.

On `DESIGN_HEAVY=complete`:
- Parse `DESIGN_SUMMARY_FILE` from the worker's return KV block as a routing signal only. For security, ignore the returned path value if it differs from the fixed path `$DESIGN_TMPDIR/design-summary.json`.
- Validate the fixed summary path if present: it must be a non-symlink regular file, size ≤2 KB, `jq . "$DESIGN_TMPDIR/design-summary.json"` must parse, and `.schema_version == 1`. On validation failure or absence, fall back to the existing full-file reads and artifact gates silently.
- **If `SESSION_ENV_PATH` is non-empty (nested under /implement)**: use valid `design-summary.json` fields for lightweight routing/status decisions, including accepted/rejected plan-review counts when a compact status line is needed; do not read or print bulky artifact bodies. If `auto_mode=false` proceed directly to Step 3.5; if `auto_mode=true` proceed directly to Step 5 because the worker ran Step 3b and Step 4. (Parent /implement reads the manifest written at Step 5.)
- **If `SESSION_ENV_PATH` is empty (standalone /design --subagent — NEW capability)**: read and print `$DESIGN_TMPDIR/plan.txt` under `## Implementation Plan`, `$DESIGN_TMPDIR/voting-tally.md` under `## Voting Tally and Reviewer Competition Scoreboard`, `$DESIGN_TMPDIR/accepted-plan-findings.md` under `## Plan Review Findings (Voted In)` (skip header if file is empty or missing), `$DESIGN_TMPDIR/oos.md` under `## Out-of-Scope Observations` (skip header if file is empty or missing), and — when `auto_mode=true` AND `$DESIGN_TMPDIR/architecture-diagram.md` exists and is non-empty — `$DESIGN_TMPDIR/architecture-diagram.md` under `## Architecture Diagram` with the mermaid fence (when `auto_mode=true` AND the file is missing/empty, print `**⚠ Architecture diagram unavailable (rejected by sanitizer).**` if the session's Warnings section contains a `mermaid sanitizer rejected` entry; otherwise print `**⚠ Architecture diagram unavailable (Step 3b generation failed in subagent).**`). When `auto_mode=true`, also read `$DESIGN_TMPDIR/rejected-findings.md`: if non-empty, print it under `## Unimplemented Plan Review Suggestions`; if empty or missing, print `## Plan Review — All Suggestions Implemented` (matches Step 4's standalone output). Then if `auto_mode=false` proceed to Step 3.5 (Discussion Round 2 still runs interactively against the displayed artifacts); if `auto_mode=true` proceed to Step 5 (cleanup). This replay matches the inline standalone output that today's empty-`SESSION_ENV_PATH` path produces, so the user sees the deliverables that `cleanup-tmpdir.sh` would otherwise delete.

On `DESIGN_HEAVY=failed`:
- **If `SESSION_ENV_PATH` is non-empty (nested)**: write the failure reason to `$DESIGN_TMPDIR/manifest-failure.md`, emit no inline warning, proceed to Step 5 for cleanup/export checks (Step 5 sets `MANIFEST_EXPORT_OK=false`, skips `cleanup-tmpdir.sh`, preserves `$DESIGN_TMPDIR`), and do not run the inline heavy steps. **Recovery**: the parent `/implement` Step 1 reads the manifest after `/design` returns; on missing/failed manifest it sets `STALL_TRACKING=true` and bails to Step 18 cleanup. To retry transient subagent failures (network blip, model timeout), the operator re-runs the same `/implement` invocation — Step 0.5 sentinel idempotency reuses the already-created tracking issue, and `/design` runs fresh.
- **If `SESSION_ENV_PATH` is empty (standalone)**: print `**⚠ 2a: sketches — heavy worker subagent failed: $REASON. Preserving $DESIGN_TMPDIR for inspection.**`, set the mental flag `STANDALONE_HEAVY_FAILED=true`, skip the inline heavy steps, and proceed to Step 5. Step 5 sees `STANDALONE_HEAVY_FAILED=true` and skips `cleanup-tmpdir.sh`, preserving `$DESIGN_TMPDIR` so the operator can inspect partial artifacts. (No parent /implement consumer; no manifest needed for standalone.)

If `subagent_mode=false` (or `quick_mode=true`), proceed to 2a.2 and run the inline flow below. (`SESSION_ENV_PATH` continues to govern nested I/O semantics — verbosity suppression, manifest export, OOS routing — orthogonally to dispatch mode.)

### 2a.2 — Launch Sketches in Parallel

If `sketch_budget=0`, perform the Zero-sketch mode sentinel writes above and proceed directly to Step 2b.

**Regular mode**: when `sketch_budget=4`, 4 sketch agents run in parallel: 2 Cursor slots (Architecture/Standards, Edge-cases/Failure-modes) + 2 Codex slots (Innovation/Exploration, Pragmatism/Safety), with per-slot Claude Agent-tool fallback when an external tool is unavailable so the 4-agent count is preserved.

**Quick/simple mode**: when `sketch_budget=2`, 2 sketch agents run in parallel: 1 Cursor-Generic + 1 Codex-Generic, with per-slot Claude Agent-tool fallback so the 2-agent count is preserved.

**MANDATORY — READ ENTIRE FILE (load FIRST)**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sketch-prompts.md` completely. It defines `ARCH_PROMPT`, `EDGE_PROMPT`, `INNOVATION_PROMPT`, `PRAGMATIC_PROMPT`, and `GENERIC_PROMPT` — the four personality-prompt bodies and the quick-mode generic prompt, substituted into the launch shell blocks via the corresponding `<…>` token names.

**MANDATORY — READ ENTIRE FILE (load SECOND, after sketch-prompts.md)**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sketch-launch.md` completely. It contains the byte-preserved launch shell blocks for the 4 regular-mode external slots (2 Cursor + 2 Codex) and the 2 quick-mode slots (1 Cursor-Generic + 1 Codex-Generic), the spawn-order rule, the per-slot `run_in_background: true` / `timeout: 1260000` requirements, and the per-slot Claude fallback notes.

Execute the launches per `sketch-launch.md` — all external and fallback launches issued in a single message, Cursor slots first, then Codex slots, then any Claude fallbacks.

### 2a.3 — Wait and Validate Sketches

Collect and validate external sketch outputs using the shared collection script. Pass the output paths for whichever external slots were actually launched (omit any slot where the tool was unavailable and a Claude subagent fallback is returning via Agent tool instead).

If `sketch_budget=0`, skip this section entirely. Do NOT call `collect-agent-results.sh`.

**Regular mode** (4 external output files when both tools available):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1260 \
  "$DESIGN_TMPDIR/cursor-sketch-arch-output.txt" \
  "$DESIGN_TMPDIR/cursor-sketch-edge-output.txt" \
  "$DESIGN_TMPDIR/codex-sketch-innovation-output.txt" \
  "$DESIGN_TMPDIR/codex-sketch-pragmatic-output.txt"
```

**Quick mode** (2 external output files when both tools available; `sketch_budget=2`):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1260 \
  "$DESIGN_TMPDIR/cursor-sketch-generic-output.txt" \
  "$DESIGN_TMPDIR/codex-sketch-generic-output.txt"
```

Use `timeout: 1260000` on the Bash tool call. **Do NOT** set `run_in_background: true` — this call must block. Only include output paths for slots that were actually launched as external reviewers — omit any slot whose tool was unavailable (its fallback comes back via the Agent tool).

Note: This is a separate `collect-agent-results.sh` call from the one in Step 3. Both are permitted because they operate on completely distinct output file sets (`*-sketch-*-output.txt` vs `*-plan-output.txt`).

Parse the structured output for each reviewer's `STATUS`, `REVIEWER_FILE`, and `HEALTHY`. For sketches, a valid output is non-empty and contains substantive architectural content (at least a paragraph). If a reviewer's `STATUS` is not `OK`, follow the **Runtime Timeout Fallback** procedure in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md` (set `*_available=false` for all subsequent steps).

For every non-`OK` sketch collector result, compose `$DESIGN_TMPDIR/sketch-collector-<reviewer>.failure.log` with the structured collector block, the full `REVIEWER_FILE` content if present, and the full `${REVIEWER_FILE}.diag` content if present. When `SESSION_ENV_PATH` is non-empty, append that file with `${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh --log "$(dirname "$SESSION_ENV_PATH")/execution-issues.md" --site "design Step 2a.3" --tool "collect-agent-results.sh <tool> <status>" --exit-code <EXIT_CODE-or-1> --category "External Reviewer Issues" --output-file "$failure_log" --redact || true`.

After this collection boundary, consult any `${OUTPUT}.dirty-tree` launcher sidecars for launched Cursor/Codex outputs, then run `${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint`. If a sidecar or checkpoint reports `STATUS=dirty` or `STATUS=unknown`, write `$DESIGN_TMPDIR/dirty-tree-detected.env` with `STATUS`, `STAGE=sketch-collection`, and `RECOVERY_REQUIRED=true`, then fire the dirty-tree recovery `AskUserQuestion` regardless of `auto_mode`. Use a `$DESIGN_TMPDIR/.dirty-tree-prompted-sketch-collection` flag so one logical boundary prompts once.

### 2a.4 — Synthesis

Read all sketches (or their Claude fallbacks if an external tool was unavailable). Produce a synthesis that:

1. Identifies where the approaches **agree** (likely the majority)
2. Identifies where they **diverge** and makes a reasoned call on each contested point with justification
3. Notes which ideas from each sketch are being incorporated into the full plan

**Regular mode only** (`sketch_budget=4`, personality-specific highlights — skip these when `sketch_budget=2`):

4. Highlights any **Architecture/Standards** concerns that should be addressed in the plan
5. Highlights any **Pragmatism/Safety** warnings about regression risk or unnecessary complexity
6. Surfaces any **Edge-case/Failure-mode** risks that should be addressed in the plan's Failure modes section
7. Notes any **Innovation/Exploration** alternatives worth preserving as options even when not chosen

**Quick mode** (`sketch_budget=2`): attribute sketches by tool (Cursor-Generic vs Codex-Generic). Skip personality-specific highlight bullets 4-7 above. Use generic agreement/divergence analysis only.

8. Lists contested decisions as a structured markdown list in `$DESIGN_TMPDIR/contested-decisions.md`. Use this schema:

   ```markdown
   ### DECISION_1: <short title>
   - **Chosen**: <the synthesis choice>
   - **Alternative**: <the strongest alternative>
   - **Tension**: <why this is contested — which sketches diverged and why>
   - **Impact**: High/Medium/Low
   - **Affected files**: <comma-separated list of files/modules impacted by this decision>
   ```

   List decisions in priority order: High impact first, then by degree of sketch disagreement (more agents on different sides = higher priority), then by order of appearance in the synthesis. If no sketches diverged (all agents agreed on all points), write exactly `NO_CONTESTED_DECISIONS` as the entire file content.

Write the synthesis to `$DESIGN_TMPDIR/approach-synthesis.txt` so it can be referenced by Step 2b. If `SESSION_ENV_PATH` is empty, also print it under an `## Approach Synthesis` header. If `SESSION_ENV_PATH` is non-empty, print nothing for this save and continue; the Step 5 manifest is the parent-visible handoff.

### 2a.5 — Dialectic Resolution of Contested Decisions

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 2a.5 — dialectic" || true
```

Print: `> **🔶 /design 2a.5: dialectic**`

If `sketch_budget=0`, print `⏩ 2a.5: dialectic — skipped (trivial doc-only) (<elapsed>)` and proceed directly to Step 2b. Do NOT load `dialectic-execution.md`.

Read `$DESIGN_TMPDIR/contested-decisions.md`. If the file contains only `NO_CONTESTED_DECISIONS` (ignoring leading/trailing whitespace and newlines), print `⏩ 2a.5: dialectic — no contested decisions (<elapsed>)` and IMMEDIATELY proceed to Step 2b — do NOT halt after the skip breadcrumb.

**Intentional divergence from the repo-wide replacement-first fallback architecture (debate phase only)**. The **debate** phase (steps 1-9 below) deliberately diverges from the "Voter Composition" rule in `${CLAUDE_PLUGIN_ROOT}/skills/shared/voting-protocol.md` and from the Cursor/Codex fallback rules in the "Step 3 — Plan Review" section below: when an assigned debater tool is unavailable, the bucket is **skipped entirely** — Claude subagents are NEVER substituted into the dialectic **debate** path. Likewise, the "Runtime Timeout Fallback" procedure in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md` flips orchestrator-wide `*_available` for all subsequent session steps; in this phase, runtime failures affect ONLY this phase's bookkeeping and never mutate the orchestrator-wide flags. Do NOT "fix" this carve-out back to global-flip + Claude-replacement behavior for debaters — see GitHub issue #98 for the rationale.

This divergence applies **only to debate execution**, not to **judge adjudication**. The post-debate judge panel (see `${CLAUDE_PLUGIN_ROOT}/skills/shared/dialectic-protocol.md`) uses the repo-wide **replacement-first** pattern: when Cursor or Codex is unavailable for judging, a Claude Code Reviewer subagent replaces that slot so the panel always remains at 3 judges. Judges merely adjudicate between pre-authored defenses; the "no Claude substitution" rule is specific to adversarial debate where model-specific writing style could encode tool identity.

Otherwise, read `$DESIGN_TMPDIR/approach-synthesis.txt` — this provides `{SYNTHESIS_TEXT}` for the prompt templates below. Then apply the following protocol:

1. **Cap = `min(5, |contested-decisions|)`** — select that many decisions from the file (they are already in priority order from Step 2a.4).

2. **Initialize dialectic-scoped shadow flags** at the top of this step:
   - `dialectic_codex_available = codex_available` (snapshot at entry)
   - `dialectic_cursor_available = cursor_available` (snapshot at entry)
   The orchestrator-wide `codex_available` / `cursor_available` flags are NEVER mutated during this step. This preserves Step 3's plan-review panel integrity by construction (Option B).

3. **Deterministic per-decision bucket assignment** (1-based indexing):
   - Decision 1, 3, 5 → **Cursor** bucket (uses `dialectic_cursor_available`).
   - Decision 2, 4 → **Codex** bucket (uses `dialectic_codex_available`).
   - Both thesis and antithesis for a single decision use the same tool (bucket homogeneity).

4. **Per-bucket pre-launch availability check**. For each selected decision, check the assigned tool's `dialectic_*_available` flag:
   - If `false`: print `**⚠ <Tool> unavailable — dialectic skipped for bucket <N> decisions (indices: <comma-list>). Step 2a.4 synthesis decisions stand.**`, skip that decision, and continue. Do NOT fall back to a Claude Agent-tool subagent. Do NOT reassign the decision to the surviving tool. Do NOT abort this step.
   - If `true`: queue both the thesis and antithesis launch for that decision.

5. **Zero-externals guardrail**. If after iterating all selected decisions, zero buckets are queued, print no further launches, do NOT call `collect-agent-results.sh` at all, skip the judge phase entirely. The `dialectic-resolutions.md` file IS still written — it contains only `Disposition: bucket-skipped` entries (one per selected decision) plus any `Disposition: over-cap` entries for decisions ranked outside the top-5 cap — so Step 2b and Step 3.5 parse a uniform schema regardless of dialectic outcome. On this path, follow the second `Do NOT load` variant below.

**MANDATORY — READ ENTIRE FILE before rendering debate prompts (step 6)**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/dialectic-execution.md` completely. It contains the byte-preserved execution choreography: per-decision prompt rendering, parallel debater launch, collection, the eligibility gate (Dispositions), the debate quorum gate, the dialectic-local judge-panel re-probe, ballot construction, judge launch, tally, and the `Write dialectic-resolutions.md` sub-step. The first directive inside that file is a nested MANDATORY pointing to `references/dialectic-debate.md` — the template-body file that holds the Thesis/Antithesis prompt substitution placeholders (`{FEATURE_DESCRIPTION}`, `{SYNTHESIS_TEXT}`, `{DECISION_BLOCK}`, `{CHOSEN}`, `{ALTERNATIVE}`, `{TENSION}`, `{AFFECTED_FILES}` plus the `<debater_synthesis>` / `<debater_decision>` reference-block wrappers).

**Do NOT load `dialectic-execution.md` when `contested-decisions.md` contains only `NO_CONTESTED_DECISIONS`** — the short-circuit print at the top of Step 2a.5 exits before reaching this point, so the reference file is naturally never loaded on the no-contest path.

**Do NOT load `dialectic-execution.md` when the zero-externals guardrail fired (zero buckets queued in step 5 above)** — instead, jump directly to the final sub-step of `dialectic-execution.md` conceptually (emit only `bucket-skipped` / `over-cap` entries into `dialectic-resolutions.md`) without loading the full execution procedure. The dialectic-resolutions schema for these entries is documented in the **Write `$DESIGN_TMPDIR/dialectic-resolutions.md`** section of `dialectic-execution.md`; if the orchestrator already has the schema in context from a prior run, skip the load entirely. Otherwise, a one-time load of `dialectic-execution.md` is acceptable but the debate-execution mechanics inside it MUST NOT fire (no debaters, no judges, no ballot).

Execute steps 6 through final dialectic resolution writing as documented in `${CLAUDE_PLUGIN_ROOT}/skills/design/references/dialectic-execution.md` (loaded via the MANDATORY directive above). That file is the single normative source for dialectic-execution mechanics. The final `Write $DESIGN_TMPDIR/dialectic-resolutions.md` sub-step (including the per-disposition field rules) lives inside that reference; print the `## Dialectic Resolutions` header at the end.

After each dialectic collection boundary (debate results and judge results), follow the dirty-tree probe contract in `references/heavy-worker.digest.md`: consult launcher sidecars, run `check-mid-run-dirty-tree.sh --mode checkpoint`, and ask for recovery on dirty/unknown regardless of `auto_mode`, deduped by `$DESIGN_TMPDIR/.dirty-tree-prompted-<boundary>`.

<!-- step:2b — Design the Implementation Plan -->

Print: `> **🔶 /design 2b: full plan**`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 2b — plan" || true
```

Before writing any code, create a concrete implementation plan. Research the codebase (read relevant files, grep for patterns, understand existing architecture). See CLAUDE.md for project-specific development references and conventions.

Read `$DESIGN_TMPDIR/approach-synthesis.txt` from Step 2a and incorporate the synthesis into the plan. The synthesis should inform architectural decisions, file selection, and tradeoff resolutions. If it contains exactly `NO_SKETCHES_CLASSIFIED_TRIVIAL`, treat that as a sentinel that no sketches ran because the router confirmed trivial doc-only scope; write the plan from direct codebase/doc inspection instead of fabricating sketch agreement.

Also read `$DESIGN_TMPDIR/discussion-round1.md` if it exists and is non-empty. Incorporate the scope boundaries and hard constraints established during the design discussion into the plan — these define what is in-scope, what must not break, and what the user explicitly does not want.

Also read `$DESIGN_TMPDIR/dialectic-resolutions.md` if it exists and is non-empty. Parse the structured fields defined in `${CLAUDE_PLUGIN_ROOT}/skills/shared/dialectic-protocol.md` (Resolution, Disposition, Vote tally, Thesis summary, Antithesis summary, Why field). **Branch on `Disposition`**:

- **`Disposition: voted`**: the plan **must** follow the `Resolution` direction and explicitly note how the antithesis concern (from `Antithesis summary`) was addressed, referencing the `Why thesis prevails` / `Why antithesis prevails` justification. These resolutions are binding for Step 2b — do not override them.
- **`Disposition: fallback-to-synthesis`**: the synthesis decision stands (Resolution is the synthesis choice = `CHOSEN`). Note the `Why fallback` reason briefly (judge panel tie, quorum failure, etc.) but do NOT fabricate antithesis-engagement prose — no antithesis was heard with sufficient rigor to engage.
- **`Disposition: bucket-skipped`**: the synthesis decision stands. Note that debate was skipped (`Why skipped` reason) but do NOT fabricate antithesis-engagement prose — no debate occurred.
- **`Disposition: over-cap`**: the synthesis decision stands. Note that this decision was outside the dialectic cap (`Why over-cap` reason) but do NOT fabricate antithesis-engagement prose.

(Note: Step 3 plan review may subsequently revise the plan based on accepted review findings, which supersede dialectic resolutions.)

Produce a plan that includes:

- **Files to modify/create**: List each file with a brief description of what changes.
- **Approach**: Describe the implementation strategy, key decisions, and any trade-offs.
- **Edge cases**: Note important input/boundary conditions and how they'll be handled.
- **Failure modes** (for non-trivial changes): The 3 most likely architectural/systemic failure paths, earliest warning signals, and simplest mitigations. May be omitted for purely cosmetic or documentation-only changes.
- **Testing strategy**: What tests will be added or modified.
- **Diff size estimate**: Estimate the total diff size in changed lines for the planned implementation. Append a final line `diff_lines: <N>` to `$DESIGN_TMPDIR/plan.txt`, where `<N>` is a non-negative integer. This estimate drives `/implement` Step 1's `diff_lines < 30` Claude inline carve-out; use best judgment, but do not omit the line.

Write the plan to `$DESIGN_TMPDIR/plan.txt` with basename exactly `plan.txt`. If `SESSION_ENV_PATH` is empty, print the plan to the user under a `## Implementation Plan` header so reviewers can see it. If `SESSION_ENV_PATH` is non-empty, print nothing for this save; `/implement` reads the exported plan file through the Step 5 manifest. The plan is an intermediate deliverable — IMMEDIATELY continue to Step 3 (Plan Review) after saving/printing. Do NOT halt, summarize, or treat the plan as the end of the design.

Immediately after saving `plan.txt`, emit the mechanical plan-validation ACTION. This writes `$DESIGN_TMPDIR/diff-lines.txt` atomically and fails closed if the final `diff_lines: <N>` line is missing or malformed:

```bash
printf '%s\n' 'ACTION=EMIT_PLAN' \
  | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
```

If the driver exits non-zero or emits `EMIT_PLAN_STATUS=missing-diff-lines`, treat it as a hard Step 2b failure and repair `$DESIGN_TMPDIR/plan.txt` before proceeding to Step 3.

> **Continue to Step 3 IMMEDIATELY.** The implementation plan is an intermediate design artifact — plan review, optional discussion, diagram generation, rejected-findings reporting, and cleanup still must run. → shared/subskill-invocation.md#step-boundary

<!-- step:3 — Plan Review -->

Print: `> **🔶 /design 3: plan review**`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 3 — plan review" || true
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 1 — design Step 3 plan review" || true
```

Read `review_budget` from `$DESIGN_TMPDIR/run-params.json`. Valid values are `quick` and `full`; if absent or invalid, derive the fallback from `quick_mode` (`quick` when true, otherwise `full`).

**If `review_budget=quick`**: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/plan-review-quick.md` completely. It defines the quick-mode plan-review procedure (self-review checklist, output file requirements, acceptance policy). After executing the procedure, proceed to Step 3.5 if `auto_mode=false`, or Step 3b if `auto_mode=true`.

**If `review_budget=full`**:

**IMPORTANT: Plan review MUST ALWAYS run with all 10 reviewers (5 Cursor: Arch, Edge, Innovation, Pragmatic, Requirements + 5 Codex: Arch, Edge, Innovation, Pragmatic, Requirements). Never skip or abbreviate this step regardless of how straightforward the plan appears — even when all sketch agents agreed, the plan is short, or the change seems trivial. Reviewers validate against the actual codebase state, catching issues that sketch-phase reasoning alone cannot detect. When Cursor is unavailable, each Cursor archetype slot falls back to Codex; when Codex is unavailable, each Codex archetype slot falls back to Cursor; when both are unavailable, each falls back to a Claude subagent.**

**MANDATORY — READ ENTIRE FILE before launching reviewers**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/plan-review.md` completely. The reference is the normative source for the reviewer-prompt content and post-launch procedures: the byte-preserved Competition notice blockquote (appended to EACH reviewer prompt), the external prompt renderer contract, the voter-1 prompt, the `dispatch-plan-voters.sh` Voter 2/3 launch contract, the ballot file handling paragraph, the Collecting External Reviewer Results procedure (10 reviewers: 5 Cursor archetypes (Arch, Edge, Innovation, Pragmatic, Requirements) + 5 Codex archetypes (Arch, Edge, Innovation, Pragmatic, Requirements), all external), the Voting Panel launch-order + threshold + Competition scoring rules, the Finalize Plan Review 4-step procedure plus OOS artifact write rule, the Track Rejected Plan Review Findings rule, and the accepted `FINDING_N` template, accepted `oos-accepted-design.md` format, and rejected-findings template. Step 3 control flow that remains inline in SKILL.md below (not in plan-review.md): the 10-reviewer "MUST ALWAYS run" IMPORTANT banner, the overall parallel-launch + spawn-order rule, `### External Reviewer Setup` (writing `$DESIGN_TMPDIR/plan.txt` + the focus-area enum summary line), and the external reviewer launch Bash blocks (5 Cursor archetypes + 5 Codex archetypes) which must stay inline because CI greps SKILL.md for focus-area enum anchor comments before each renderer call. Renderer details live in `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.md`; harness coverage lives in `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-plan-review-prompt.sh` and `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-plan-review-prompt.md`. The Competition notice must be in context before any reviewer launch below — reading this file now guarantees that.

Launch **all 10 reviewers in parallel** (in a single message). When Cursor is unavailable, each Cursor archetype slot falls back to Codex; when Codex is unavailable, each Codex archetype slot falls back to Cursor; when both are unavailable, each archetype slot falls back to a Claude subagent. **Spawn order matters for parallelism** — launch the slowest reviewers first: 5 Cursor archetypes (Arch, Edge, Innovation, Pragmatic, Requirements), then 5 Codex archetypes (Arch, Edge, Innovation, Pragmatic, Requirements). Each reviewer receives the plan text and the feature description. Each must **only report findings** — never edit files.

### External Reviewer Setup (if `codex_available` or `cursor_available`)

Before launching external reviewers, verify the implementation plan exists at `$DESIGN_TMPDIR/plan.txt` so Codex and Cursor can read it. Step 2b owns writing this file.

Each reviewer walks five focus areas: code-quality / risk-integration / correctness / architecture / security.

### Cursor Archetype Reviewers (5 slots)

Launch 5 Cursor archetype plan reviewers **first** in the parallel message (Arch, Edge, Innovation, Pragmatic, Requirements — they take the longest). Each archetype reviews the plan from its specialized perspective. Each Cursor reviewer has full repo access. **Fallback chain per slot**: Cursor → Codex → Claude subagent (subagent_type: `larch:code-reviewer`, model: `"sonnet"` with the archetype personality prepended).

**Cursor — Architecture/Standards** (if `cursor_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_arch_prompt_file="$DESIGN_TMPDIR/render-plan-arch.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype arch --vendor cursor --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_arch_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
  --output "$DESIGN_TMPDIR/cursor-plan-arch-output.txt" \
  --timeout 1800 --timing-task-kind cursor-plan-arch \
  --prompt-file "$_arch_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Cursor — Edge-cases/Failure-modes** (if `cursor_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_edge_prompt_file="$DESIGN_TMPDIR/render-plan-edge.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype edge --vendor cursor --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_edge_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
  --output "$DESIGN_TMPDIR/cursor-plan-edge-output.txt" \
  --timeout 1800 --timing-task-kind cursor-plan-edge \
  --prompt-file "$_edge_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Cursor — Innovation/Exploration** (if `cursor_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_cursor_innovation_prompt_file="$DESIGN_TMPDIR/render-plan-cursor-innovation.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype innovation --vendor cursor --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_cursor_innovation_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
  --output "$DESIGN_TMPDIR/cursor-plan-innovation-output.txt" \
  --timeout 1800 --timing-task-kind cursor-plan-innovation \
  --prompt-file "$_cursor_innovation_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Cursor — Pragmatism/Safety** (if `cursor_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_cursor_pragmatic_prompt_file="$DESIGN_TMPDIR/render-plan-cursor-pragmatic.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype pragmatic --vendor cursor --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_cursor_pragmatic_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
  --output "$DESIGN_TMPDIR/cursor-plan-pragmatic-output.txt" \
  --timeout 1800 --timing-task-kind cursor-plan-pragmatic \
  --prompt-file "$_cursor_pragmatic_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Cursor — Requirements/Completeness** (if `cursor_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_cursor_requirements_prompt_file="$DESIGN_TMPDIR/render-plan-cursor-requirements.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype requirements --vendor cursor --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_cursor_requirements_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
  --output "$DESIGN_TMPDIR/cursor-plan-requirements-output.txt" \
  --timeout 1800 --timing-task-kind cursor-plan-requirements \
  --prompt-file "$_cursor_requirements_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Cursor archetype fallback** (per slot, if `cursor_available` is false): For each Cursor archetype slot where Cursor is unavailable, try Codex first (if `codex_available`). Render the same archetype with `render-plan-review-prompt.sh --archetype <arch|edge|innovation|pragmatic|requirements> --vendor codex`, write it to an explicit temp prompt file, then launch via `launch-review.sh --tool codex --prompt-file` with distinct per-archetype output paths: `$DESIGN_TMPDIR/codex-fallback-cursor-plan-arch-output.txt`, `$DESIGN_TMPDIR/codex-fallback-cursor-plan-edge-output.txt`, `$DESIGN_TMPDIR/codex-fallback-cursor-plan-innovation-output.txt`, `$DESIGN_TMPDIR/codex-fallback-cursor-plan-pragmatic-output.txt`, `$DESIGN_TMPDIR/codex-fallback-cursor-plan-requirements-output.txt`. If both Cursor and Codex are unavailable for a slot, launch a Claude subagent fallback (subagent_type: `larch:code-reviewer`, model: `"sonnet"`) using the reviewer-templates.md path in `plan-review.md`.

### Codex Archetype Reviewers (5 slots)

Launch 5 Codex archetype plan reviewers **second** in the parallel message (Arch, Edge, Innovation, Pragmatic, Requirements, after Cursor). Each archetype reviews the plan from its specialized perspective. Each Codex reviewer has full repo access. **Fallback chain per slot**: Codex → Cursor → Claude subagent (subagent_type: `larch:code-reviewer`, model: `"sonnet"` with the archetype personality prepended).

**Codex — Architecture/Standards** (if `codex_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_codex_arch_prompt_file="$DESIGN_TMPDIR/render-plan-codex-arch.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype arch --vendor codex --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_codex_arch_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex \
  --output "$DESIGN_TMPDIR/codex-primary-plan-arch-output.txt" \
  --timeout 1800 --timing-task-kind codex-plan-arch \
  --prompt-file "$_codex_arch_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Codex — Edge-cases/Failure-modes** (if `codex_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_codex_edge_prompt_file="$DESIGN_TMPDIR/render-plan-codex-edge.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype edge --vendor codex --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_codex_edge_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex \
  --output "$DESIGN_TMPDIR/codex-primary-plan-edge-output.txt" \
  --timeout 1800 --timing-task-kind codex-plan-edge \
  --prompt-file "$_codex_edge_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Codex — Innovation/Exploration** (if `codex_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_innovation_prompt_file="$DESIGN_TMPDIR/render-plan-innovation.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype innovation --vendor codex --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_innovation_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex \
  --output "$DESIGN_TMPDIR/codex-primary-plan-innovation-output.txt" \
  --timeout 1800 --timing-task-kind codex-plan-innovation \
  --prompt-file "$_innovation_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Codex — Pragmatism/Safety** (if `codex_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_pragmatic_prompt_file="$DESIGN_TMPDIR/render-plan-pragmatic.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype pragmatic --vendor codex --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_pragmatic_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex \
  --output "$DESIGN_TMPDIR/codex-primary-plan-pragmatic-output.txt" \
  --timeout 1800 --timing-task-kind codex-plan-pragmatic \
  --prompt-file "$_pragmatic_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Codex — Requirements/Completeness** (if `codex_available`):

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_codex_requirements_prompt_file="$DESIGN_TMPDIR/render-plan-codex-requirements.prompt"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype requirements --vendor codex --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_codex_requirements_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex \
  --output "$DESIGN_TMPDIR/codex-primary-plan-requirements-output.txt" \
  --timeout 1800 --timing-task-kind codex-plan-requirements \
  --prompt-file "$_codex_requirements_prompt_file"
```

Use `run_in_background: true` and `timeout: 1860000` on the Bash tool call.

**Codex archetype fallback** (per slot, if `codex_available` is false): For each Codex archetype slot where Codex is unavailable, try Cursor first (if `cursor_available`). Render the same archetype with `render-plan-review-prompt.sh --archetype <arch|edge|innovation|pragmatic|requirements> --vendor cursor`, write it to an explicit temp prompt file, then launch via `launch-review.sh --tool cursor --prompt-file` with distinct per-archetype output paths: `$DESIGN_TMPDIR/cursor-fallback-codex-plan-arch-output.txt`, `$DESIGN_TMPDIR/cursor-fallback-codex-plan-edge-output.txt`, `$DESIGN_TMPDIR/cursor-fallback-codex-plan-innovation-output.txt`, `$DESIGN_TMPDIR/cursor-fallback-codex-plan-pragmatic-output.txt`, `$DESIGN_TMPDIR/cursor-fallback-codex-plan-requirements-output.txt`. If both Codex and Cursor are unavailable for a slot, launch a Claude subagent fallback (subagent_type: `larch:code-reviewer`, model: `"sonnet"`) using the reviewer-templates.md path in `plan-review.md`.

### Collecting, Voting, Finalize, Track Rejected

Follow `plan-review.md` (loaded via the MANDATORY at the top of Step 3) for: Collecting External Reviewer Results (`collect-agent-results.sh` for all launched external reviewers (up to 10 archetype slots), dedup in-scope and OOS separately), Voting Panel launch-order through `dispatch-plan-voters.sh` + threshold + Competition scoring, writing the ballot file and explicit voter output files, Finalize Plan Review (accepted findings revise plan, write accepted OOS to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md` when `SESSION_ENV_PATH` is non-empty, print non-accepted OOS under `## Out-of-Scope Observations` only when `SESSION_ENV_PATH` is empty), and Track Rejected Plan Review Findings (in-scope only). Accepted OOS Descriptions should include affected repo-relative file paths and line ranges when applicable; `/implement` Step 9a.1 serializes same-file OOS issues unless the exposed ranges are parseable and non-overlapping.

After `dispatch-plan-voters.sh` returns Voter 2/3 output paths and the local Voter 1 ballot path is available, emit the tally ACTION with explicit files. Use the canonical ballot path `$DESIGN_TMPDIR/ballot.txt` and the voter output paths emitted by `dispatch-plan-voters.sh` (`VOTER_1_PATH` for the Claude Voter 1 output, `VOTER_2_PATH`, `VOTER_3_PATH`). This script writes `$DESIGN_TMPDIR/voting-tally.md`, `$DESIGN_TMPDIR/accepted-plan-findings.md`, `$DESIGN_TMPDIR/rejected-findings.md`, `$DESIGN_TMPDIR/oos.md`, and `$DESIGN_TMPDIR/oos-accepted-design.md` using the design-local parser for `### FINDING_N:` and `### OOS_N:` blocks. When `SESSION_ENV_PATH` is non-empty, accepted non-security OOS is also written to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md`:

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" \
printf 'ACTION=TALLY ARGS=--ballot-file %s --voter-files %s %s %s --session-env-path %s\n' \
  "$DESIGN_TMPDIR/ballot.txt" \
  "$VOTER_1_PATH" \
  "$VOTER_2_PATH" \
  "$VOTER_3_PATH" \
  "$SESSION_ENV_PATH" \
  | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
```

If accepted findings revise `$DESIGN_TMPDIR/plan.txt`, immediately re-run plan emission so `diff-lines.txt` reflects the final plan:

```bash
printf '%s\n' 'ACTION=EMIT_PLAN' \
  | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
```

If the second `EMIT_PLAN` fails, repair the revised plan before continuing.

After the plan-review collection boundary, consult launcher `${OUTPUT}.dirty-tree` sidecars, run `check-mid-run-dirty-tree.sh --mode checkpoint`, and ask for recovery on dirty/unknown regardless of `auto_mode`, deduped by `$DESIGN_TMPDIR/.dirty-tree-prompted-plan-review`.

If **all reviewers** report no in-scope issues and no out-of-scope observations, skip voting and proceed to Step 3.5 if `auto_mode=false`, or Step 3b if `auto_mode=true`.

> **Continue to Step 3.5 or Step 3b IMMEDIATELY.** The plan-review result is not terminal — follow the `auto_mode` branch into discussion or diagram generation.

<!-- step:3.5 — Design Discussion (Round 2) -->

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 3.5 — discussion r2" || true
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 1 — design Step 3.5 discussion r2" || true
```

Print: `> **🔶 /design 3.5: discussion r2**`

**If `auto_mode=true`**: Print `⏩ 3.5: discussion r2 — skipped (auto mode) (<elapsed>)` and proceed to Step 3b. **Do NOT load `discussion-rounds.md` when `auto_mode=true`.**

**If `auto_mode=false`**: Execute the Step 3.5 body in `${CLAUDE_PLUGIN_ROOT}/skills/design/references/discussion-rounds.md`. If already loaded at Step 1c, no need to re-load; otherwise **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/discussion-rounds.md` completely. The body defines Inputs, Behavior (still-contested criteria including close 2-1 voted, fallback-to-synthesis, bucket-skipped, over-cap), Short-circuit, Output schema, Cap, and Terse-answer rules.

<!-- step:3b — Architecture Diagram -->

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 3b — arch diagram" || true
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 1 — design Step 3b arch diagram" || true
```

Print: `> **🔶 /design 3b: arch diagram**`

**This step runs on most paths through Step 3** — whether voting produced revisions, rejected all findings, or was skipped entirely because all reviewers reported no issues. It executes before Step 4, with one exception: non-architectural plans emit a placeholder and skip generation (see below).

Before generating the diagram, classify the plan type by reading `$DESIGN_TMPDIR/plan.txt`. The plan is **non-architectural** when ALL files to be modified are exclusively: documentation files (`.md`, `CHANGELOG`, `docs/**`), configuration files (`.json`, `.yaml`, `.yml`, `.tsv`), or plain text (`.txt`) — with no new behavioral components, public APIs, or cross-skill contracts introduced. Apply a **conservative classifier** — SKILL.md files, `.sh` scripts, and `.py` scripts count as potentially architectural regardless of change size; when uncertain, generate the diagram rather than skip.

If the plan is non-architectural: do NOT write `$DESIGN_TMPDIR/architecture-diagram.md`. When `SESSION_ENV_PATH` is empty, print `⏩ 3b: arch diagram status=skip reason=no-architectural-change elapsed=<elapsed>`. When `SESSION_ENV_PATH` is non-empty, print nothing. Then IMMEDIATELY continue to Step 4. Leaving `architecture-diagram.md` absent ensures `write-design-manifest.sh` omits `ARCHITECTURE_DIAGRAM_FILE` from the manifest so consumers render `"Architecture diagram not available."` rather than a plain-text placeholder.

**Otherwise** (plan is architectural): generate a mermaid Architecture Diagram that represents the high-level system/component structure of the feature based on the finalized implementation plan (revised or original). The diagram should focus on **modules, boundaries, and their relationships** — not runtime behavior or code flow.

Choose the most appropriate mermaid diagram type for the feature (e.g., `graph TD`, `flowchart`, `C4Context`, `classDiagram`, etc.). The diagram type is flexible — pick whatever best communicates the architecture.

Diagram contents must obey `${CLAUDE_PLUGIN_ROOT}/skills/shared/mermaid-safe-content.md` to avoid sanitizer rejection.

Write the diagram to `$DESIGN_TMPDIR/architecture-diagram.candidate.md` first. The candidate file includes the `## Architecture Diagram` heading and mermaid fence. Validate it before promotion:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
"${CLAUDE_PLUGIN_ROOT}/scripts/sanitize-mermaid-fragment.sh" \
  --input "$DESIGN_TMPDIR/architecture-diagram.candidate.md" \
  --from-md \
  --warnings-step "3b"
```

On `STATUS=ok`, rename the candidate to `$DESIGN_TMPDIR/architecture-diagram.md`. If `SESSION_ENV_PATH` is empty, also print the promoted diagram under a `## Architecture Diagram` header with a mermaid code fence:

```
## Architecture Diagram

```mermaid
<diagram content>
```
```

**If diagram generation and sanitizer validation succeed**, continue to Step 4; the Step 5 manifest carries the artifact path when `SESSION_ENV_PATH` is non-empty.

**If the sanitizer returns `STATUS=rejected` or exits 2**, do NOT promote the candidate. Delete `$DESIGN_TMPDIR/architecture-diagram.candidate.md`. When `SESSION_ENV_PATH` is empty, print `**⚠ 3b: architecture diagram — rejected by mermaid sanitizer (REASON_TOKEN=<token>); proceeding without diagram.**`. When `SESSION_ENV_PATH` is non-empty, emit no inline warning; capture the sanitizer's full stdout/stderr to `$DESIGN_TMPDIR/architecture-diagram-sanitizer.failure.log` and append it under `### Warnings` in `$(dirname "$SESSION_ENV_PATH")/execution-issues.md` via `${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh --site "design Step 3b" --tool "sanitize-mermaid-fragment.sh architecture" --exit-code <exit-code-or-2> --category Warnings --output-file "$DESIGN_TMPDIR/architecture-diagram-sanitizer.failure.log" --redact || true`. Then continue to Step 4.

**If diagram generation fails** (e.g., the feature is too abstract to diagram meaningfully), print `**⚠ 3b: arch diagram — generation failed, proceeding without diagram (<elapsed>)**` only when `SESSION_ENV_PATH` is empty. When `SESSION_ENV_PATH` is non-empty, emit no inline warning and append the full generation failure capture to `$(dirname "$SESSION_ENV_PATH")/execution-issues.md` with `append-tool-failure.sh` under `Warnings`. Then IMMEDIATELY continue to Step 4.

> **Continue to Step 4 IMMEDIATELY.** The architecture diagram branch is not terminal — rejected-findings reporting and cleanup still must run.

<!-- step:4 — Rejected Plan Review Findings Report -->

Print: `> **🔶 /design 4: rejected findings**`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 4 — rejected findings" || true
```

Print any rejected plan review findings:

1. Emit `ACTION=FINALIZE` to ensure `$DESIGN_TMPDIR/rejected-findings.md`, `$DESIGN_TMPDIR/accepted-plan-findings.md`, and `$DESIGN_TMPDIR/oos.md` exist and to validate non-empty manifest-required artifacts before Step 5 export:
   ```bash
   printf '%s\n' 'ACTION=FINALIZE' \
     | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
   ```
   If this exits non-zero, repair the missing artifact before Step 5.
2. Check if `$DESIGN_TMPDIR/rejected-findings.md` exists and is non-empty.
3. If it has content and `SESSION_ENV_PATH` is empty, print it under a `## Unimplemented Plan Review Suggestions` header, formatted clearly with the reviewer name, the suggestion, and the reason for each.
4. If it has content and `SESSION_ENV_PATH` is non-empty, print nothing; the Step 5 manifest carries the rejected-findings artifact path.
5. If `$DESIGN_TMPDIR/rejected-findings.md` is empty (it always exists after item 1), continue.

After printing rejected findings (or the "all implemented" message), IMMEDIATELY continue to Step 5 — do NOT halt or treat this as the end of the design.

> **Continue to Step 5 IMMEDIATELY.** Rejected-findings output is not terminal — cleanup and manifest export still must run.

<!-- step:5 — Cleanup and Final Warnings -->

Print: `> **🔶 /design 5: cleanup**`

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 5 — cleanup" || true
```

### 5a — Update Health Status File

Health status file updates are now handled automatically by `collect-agent-results.sh --write-health` during reviewer collection (Steps 2a.3 and 3). No additional cleanup-time write is needed unless a reviewer was marked unhealthy outside of a `collect-agent-results.sh` call (e.g., via a manual timeout detection). If `SESSION_ENV_PATH` is non-empty and any reviewer was marked unhealthy during this session that was NOT already written by `collect-agent-results.sh`, re-write the health status file at `${SESSION_ENV_PATH}.health` with the final health state before cleanup.

### 5b — Remove Temp Directory

If `SESSION_ENV_PATH` is non-empty, export design artifacts before cleanup:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/write-design-manifest.sh --design-tmpdir "$DESIGN_TMPDIR" --implement-tmpdir "$(dirname "$SESSION_ENV_PATH")"
```

Parse `MANIFEST_WRITTEN=<path>` from stdout and set the mental flag `MANIFEST_EXPORT_OK=true` if the command exited 0 AND the manifest file exists AND is non-empty. Otherwise set `MANIFEST_EXPORT_OK=false`; when `SESSION_ENV_PATH` is empty, print `**⚠ 5: cleanup — design manifest export failed. Preserving $DESIGN_TMPDIR for inspection.**`; when `SESSION_ENV_PATH` is non-empty, emit no inline warning because the missing/failed manifest is the parent-visible machine signal. SKIP the `cleanup-tmpdir.sh` step below entirely so the parent /implement (or operator) can inspect the partial artifacts. If `SESSION_ENV_PATH` is empty, skip this manifest write and treat `MANIFEST_EXPORT_OK` as `true` for cleanup-gating purposes (standalone `/design` preserves visible inline output, has no parent consumer, and always cleans up on the normal path).

**Manifest helper contracts** (per `${CLAUDE_PLUGIN_ROOT}/.claude/rules/script-md-siblings.md`):
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh` — ACTION dispatcher for scriptable `/design` mechanics. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/classify-issue.sh` — deterministic plus Cursor-validated run-depth classifier used by the `ACTION=CLASSIFY` path. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/classify-issue.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/emit-plan.sh` — fail-closed `plan.txt` / `diff-lines.txt` validator used by the `ACTION=EMIT_PLAN` path. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/emit-plan.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/tally-plan-review.sh` — design-local vote tally and scoreboard renderer used by the `ACTION=TALLY` path. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/tally-plan-review.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/finalize-plan.sh` — final design artifact validator used by the `ACTION=FINALIZE` path. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/finalize-plan.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/write-design-manifest.sh` — atomic writer invoked above; it also exports `diff-lines.txt` so `/implement` can route on `diff_lines < 30` after `$DESIGN_TMPDIR` cleanup. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/write-design-manifest.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/read-design-manifest.sh` — consumer-side reader/verifier invoked from `skills/implement/SKILL.md` Step 1 after `/design` returns. Producer/reader colocation under `skills/design/scripts/` is intentional (plan-review FINDING_12 vote: keep colocated, do not relocate to `skills/implement/scripts/`). Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/read-design-manifest.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-design-manifest.sh` — regression harness for both writer and reader (atomicity, missing-required-artifact rejection, KV grammar, source/eval injection rejection, path-traversal rejection, symlink rejection, control-character rejection, malformed-key rejection). Wired into `make lint` via the `test-design-manifest` Makefile target. Sibling contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-design-manifest.md`.

Remove the session temp directory and all files within it. Run `cleanup-tmpdir.sh` only when `MANIFEST_EXPORT_OK=true` AND `STANDALONE_HEAVY_FAILED` is unset or `false`; otherwise skip cleanup so `$DESIGN_TMPDIR` is preserved for inspection. `STANDALONE_HEAVY_FAILED=true` is set by the Step 2a `Subagent heavy phase` failure branch when `SESSION_ENV_PATH` is empty (standalone `/design --subagent` failed); `MANIFEST_EXPORT_OK=false` is set by Step 5b's writer-invocation failure (nested `/implement` path):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$SESSION_ENV_PATH" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-tmpdir.sh --dir "$DESIGN_TMPDIR"
```

**Repeat any external reviewer warnings** from earlier steps (Step 0 reviewer-availability checks via `session-setup.sh`, Step 2a sketch-phase failures/timeouts, Step 3 runtime failures, or Step 3b diagram generation failure) so they are visible at the end of the workflow. For example:
- `**⚠ Codex not available: <reason>**`
- `**⚠ Cursor review failed: <reason>**`
- `**⚠ Cursor sketch timed out / produced empty output**`
- `**⚠ Codex sketch timed out / produced empty output**`
- `**⚠ 3b: arch diagram — generation failed, proceeding without diagram (<elapsed>)**`

Do NOT write any farewell message such as "Design complete", "Returning to the /implement orchestrator", "Handing back control", or any other prose that signals the skill is done — those are halts in disguise that make the Skill tool appear to return a completed response and prompt the parent session to end its turn without invoking the mandatory `post-design-boundary.sh` Bash wrapper.
