## Plan

### Approach

Treat this as a **documentation + lint** change, not an orchestration refactor. The skill prose already contains scattered "Do NOT set `run_in_background: true`" warnings at specific sites; this work establishes the single normative rule, makes the per-site markers uniform, adds a CI-enforced lint, and revises a small set of canonical operator-facing docs so future drift fails fast.

Execution sequence:
1. Establish the rule (BASH_AUTHORING.md §4 + AGENTS.md cross-reference + `docs/linting.md` row + `.pre-commit-config.yaml` header reconciliation).
2. Build the linter (`scripts/lint-foreground-markers.sh` + sibling `.md` + harness + harness sibling `.md` + Makefile target + `test-harnesses-N` shard wiring + `agent-lint.toml` exclusion + pre-commit local hook entry).
3. Run the linter against the current tree, capture the full list of failing sites (the lint output IS the authoritative checklist), and apply canonical markers at each. Existing bespoke ⚠ banners are preserved; the canonical leader is added as the first paragraph line (leading-line match).
4. Verify `make lint`, `make test-harnesses-${shard}` for the chosen shard, `make lint-only` (pre-commit hooks), and Family A regression spot-check all pass.

### Canonical marker literals (pinned byte-for-byte)

**Banner** (must appear as the leading prose line of a paragraph within the 20 markdown lines IMMEDIATELY BEFORE the opening fence; strip leading `> ` blockquote prefix before match):

```
**⚠ Foreground required — do NOT set `run_in_background: true`.**
```

**Inline comment** (must appear on at least one of the 5 source lines IMMEDIATELY BEFORE the line containing the denylisted basename token, INSIDE the same fence):

```
# Foreground required: see BASH_AUTHORING.md §4
```

Linter matches the banner phrase verbatim after stripping one-level `> ` blockquote prefix; no other normalization. Matches the comment via a Bash 3.2-compatible substring scan that requires the literal `# Foreground required: see BASH_AUTHORING.md §4` on a comment line (`^#` after leading whitespace) preceding the basename anchor.

### Detection algorithm

For each `.md` file in scope:

1. Walk markdown line-by-line. Track fenced shell blocks: enter on a line matching `^```\s*(bash|sh|shell)\s*$`; exit on a closing `^```\s*$`.
2. Within each fence, identify **invocation anchor lines** — non-comment lines (`^\s*[^#\s]`) whose textual content contains any denylisted basename token via these match positions:
   - Leading shell word: `^\s*(bash\s+)?(["']?)(\S*\/)?BASENAME\b`
   - Assignment-wrapped command substitution: `=\$\(["']?(\S*\/)?BASENAME\b`
   - Env-prefixed invocation: `^\s*(\w+=\S+\s+)+(bash\s+)?(["']?)(\S*\/)?BASENAME\b`
   - `if`/`while` test: `\b(if|while|until|elif)\s+(["']?)(\S*\/)?BASENAME\b`
   - Quoted path expansion: `"\$\{?CLAUDE_PLUGIN_ROOT\}?/\S*\/BASENAME\b`
   The match operates on the full line text; a wrapped invocation with `\` continuations matches on the line that physically contains the basename token.
3. For each anchor, assert BOTH: banner within 20 lines immediately BEFORE the fence (strip `> `), AND inline comment within 5 source lines immediately BEFORE the anchor line, inside the same fence.
4. On any failure, emit `FILE:ANCHOR_LINE: missing <banner|comment> for <BASENAME>` and exit 1.

**Parse-only safety**: extraction is string-based (`awk` / `while IFS= read -r`); the linter NEVER `eval`s, `source`s, `bash -c`s, or otherwise executes fence content. Explicit code comment near the fence-parse loop states this invariant. Harness fixture includes a deliberate side-effecting command and asserts no execution.

### Files to modify / create

**Created**:
- `scripts/lint-foreground-markers.sh` — denylist (basenames at top of script as newline-delimited heredoc) + fence parser implementing the detection algorithm. Bash 3.2-portable. Scans `skills/**/SKILL.md`, `skills/**/references/*.md`, `skills/shared/*.md`, `.claude/skills/*/SKILL.md`, `.claude/rules/*.md`. Exit codes: 0 = pass, 1 = violations, 2 = usage/internal error. Mirrors `scripts/lint-bash32.sh` invocation shape.
- `scripts/lint-foreground-markers.md` — sibling contract per `.claude/rules/script-md-siblings.md`.
- `scripts/test-lint-foreground-markers.sh` — 16 fixtures covering positive baseline, missing banner, missing comment, multi-Family-B fence, Family A pass-through, prose-only mention, indented fence, heredoc, commented-out invocation, bespoke ⚠ paragraph, command-substitution assignment, env-prefixed invocation, if-test form, blockquoted banner, multi-line `\`-continued invocation, parse-only safety.
- `scripts/test-lint-foreground-markers.md` — sibling stub.

**Modified**:
- `BASH_AUTHORING.md` — new §4 "Foreground Default for Blocking Script Calls" (rule + WHY + Family A and Monitor-tailed exceptions + worked examples).
- `AGENTS.md` — one-line "Conventions" cross-reference near the existing `ScheduleWakeup` / "Don't spawn a Monitor or Bash `run_in_background` polling loop" rules.
- `docs/linting.md` — catalog row for `lint-foreground` / `test-lint-foreground-markers` mirroring the `lint-bash32` row.
- `Makefile` — `lint-foreground:` target + `test-lint-foreground-markers:` target + append to `.PHONY` and to one existing `test-harnesses-N:` prerequisite line (mirror `test-lint-bash32` shard placement).
- `.pre-commit-config.yaml` — `local` hook for `scripts/lint-foreground-markers.sh` (`always_run: true, pass_filenames: false`); header comment reconciled with reality (CI `lint` job runs `make lint-only`, not `make lint`).
- `agent-lint.toml` — add `scripts/lint-foreground-markers.{sh,md}` and `scripts/test-lint-foreground-markers.{sh,md}` to the existing Makefile-only exclusion block.
- `.claude/rules/timing-task-kind-allowlist.md` — fix stale `(28g)` reference (OOS_2).
- `skills/implement/SKILL.md` — markers at `ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh` invocation sites. Existing bespoke ⚠ blockquote at `ship-pr.sh` gets the canonical phrase prepended.
- `skills/implement/references/rebase-rebump-subprocedure.md` — markers at `ci-wait.sh` site.
- `skills/design/SKILL.md` — markers at `collect-agent-results.sh` and the command-substitution `dispatch-with-waterfall.sh` site.
- `skills/design/references/plan-review.md` — markers at command-substitution `dispatch-plan-voters.sh` site.
- `skills/design/references/dialectic-execution.md` — markers at both `collect-agent-results.sh` boundaries.
- `skills/shared/external-reviewers.md`, `skills/shared/voting-protocol.md`, `skills/shared/dialectic-protocol.md` — markers at every `collect-agent-results.sh` site.
- `skills/research/references/research-phase.md`, `skills/research/references/validation-phase.md` — markers at `collect-agent-results.sh` sites.
- `skills/review/references/heavy-worker.md` — markers only if a fenced invocation exists (lint scans fences only).
- `skills/review-and-fix/SKILL.md` — markers per the FENCED criterion only; prose-only `review-and-fix.sh` instructions are intentionally out of scope.
- Any `.claude/skills/*/SKILL.md` and `.claude/rules/*.md` surfaced by the linter (initial grep showed zero hits; in scope for future drift).

### Edge cases

- Bespoke long banners: leading-line match — canonical phrase prepended; existing prose preserved below.
- Multi-Family-B fence: one banner above the fence + one inline comment per anchor line inside the fence.
- Prose-only basename mentions: not flagged (lint scans fences only).
- Commented-out invocations: not flagged (anchor scanner requires non-comment line).
- Family A allowlist: not enforced (out of scope). Family A basenames simply aren't on the denylist.
- `review-and-fix.sh` prose-only invocation: not flagged (acceptance is "every FENCED Family B invocation").
- Bash 3.2 portability covered by `lint-bash32`.

### Failure modes

1. **Denylist drift on script rename/split** — mitigation: one-time landing audit of `scripts/*.sh` and `skills/*/scripts/*.sh` against the denylist; denylist is single source of truth referenced from the sibling `.md`.
2. **Linter false-positives on unusual fence shapes** — mitigation: harness covers heredoc / indented / unusual-language-tag fences; relax detector toward false negatives over forcing contorted marker placement; document carve-outs in `scripts/lint-foreground-markers.md`.
3. **Marker insertion accidentally re-flows surrounding prose, breaking other lints** — mitigation: use `Edit` (precise old/new strings) rather than `Write` (full-file replacement); run `make lint` after each batch of marker insertions; never touch the same line as a load-bearing structure-test anchor (use the harness's actual `grep -Fq` contract strings as the real structure-test anchors when validating).

### Testing strategy

- **Unit/harness**: `scripts/test-lint-foreground-markers.sh` (via `make test-lint-foreground-markers` and `make test-harnesses-${SHARD}`) covers 16 fixtures.
- **Family A regression spot-check**: harness includes a `family_a_unchanged` test that grep-counts `run_in_background: true` across a fixed Family A file set (`skills/design/references/sketch-launch.md`, `skills/design/references/dialectic-execution.md`, `skills/shared/voting-protocol.md`, `skills/shared/dialectic-protocol.md`); baseline established at landing; fails if any count decreases.
- **Regression**: `make lint`, `agent-lint`, `markdownlint`, existing structure tests all green.
- **CI enforcement**: pre-commit `local` hook (`always_run: true, pass_filenames: false`) gates PRs through the CI `lint` job (`make lint-only`); `test-harnesses-N` shard gates PRs through the harness matrix job. Both paths catch drift.
- **End-to-end**: post-audit `make lint-foreground` exit 0; deliberate violation produces clear `FILE:LINE: missing <banner|comment> for <BASENAME>` message; revert.

## Acceptance

- `BASH_AUTHORING.md` gains §4 "Foreground Default for Blocking Script Calls" with: (a) the rule, (b) the WHY (real-time visibility of `lib-quiet.sh` FD-3 breadcrumbs and FD 1/2 output, turn-boundary safety per `skills/implement/SKILL.md` NEVER #16 / issue #2454), (c) the exception list (Family A parallel agent launches awaited by a single foreground collector; scripts explicitly designed for `Monitor`-based tailing).
- `AGENTS.md` "Conventions" cross-references §4 in one line.
- Every **FENCED** Family B invocation in `skills/**/SKILL.md`, `skills/**/references/*.md`, `skills/shared/*.md`, `.claude/skills/*/SKILL.md`, and `.claude/rules/*.md` has BOTH the canonical ⚠ banner (within 20 markdown lines immediately before the fence; `> ` blockquote prefix stripped before match) AND the `# Foreground required: see BASH_AUTHORING.md §4` comment (within 5 source lines immediately before each anchor line, inside the same fence). Prose-only basename mentions are out of scope by acceptance language.
- Lint target `lint-foreground` and harness target `test-lint-foreground-markers` exist; both are wired into `Makefile` + `.PHONY` + exactly one `test-harnesses-N` shard + a `.pre-commit-config.yaml` `local` hook + the `agent-lint.toml` Makefile-only exclusion block + a `docs/linting.md` catalog row.
- `make lint`, `make lint-only`, `make test-harnesses-${shard}` for the chosen shard, and the Family A regression spot-check all regression-clean against the updated tree.
- Stale `(28g)` reference in `.claude/rules/timing-task-kind-allowlist.md` resolved (OOS_2).
- `.pre-commit-config.yaml` header comment reconciled with actual CI behavior (OOS_4).

diff_lines: 600
