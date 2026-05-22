# Sub-skill Invocation Conventions

Canonical style guide for larch skills that delegate to other skills via the `Skill` tool. Cited throughout by `/create-skill`'s scaffold and by `AGENTS.md`. When you author a new skill that invokes another skill, follow the patterns below. When you change a convention here, update the cited source-example skills in the same PR (or file a follow-up issue) so the examples stay in sync with the rules.

## Two invocation patterns

Every larch skill that invokes another skill uses exactly one of two first-class shapes. Pick the one that matches your intent.

### Pattern A — Pure delegator (bulleted)

Used when the parent skill mostly forwards to a child with preset flags or light argument assembly. Appears in `skills/im/SKILL.md § Behavior` and `skills/create-skill/SKILL.md § Step 3 — Delegate to /im`. Canonical form:

```
Invoke the Skill tool:
- Try skill: "implement" first (bare name). If no skill matches, try skill: "larch:implement" (fully-qualified plugin name).
- args: --merge $ARGUMENTS
```

Keep the block together. The bare-name-first rule is important — see `## Bare-name-then-fully-qualified fallback` below.

Note: `/create-skill` forwards to `/im` (not directly to `/implement`); `/im` in turn forwards to `/implement --merge` per its own Pattern A definition. The chained delegation gives `/create-skill` auto-merge semantics while keeping each hop as a minimal pure forwarder.

### Pattern B — Stateful orchestrator (inline)

Used when the parent runs setup, exports `SESSION_ENV_PATH` for the child session merge, invokes the child, and then parses structured output to continue. Appears in `skills/fix-issue/SKILL.md § Step 5 — Execute` (parent step heading + explicit "Invoke `/implement` via the Skill tool" line + positional issue tail) and in `skills/implement/SKILL.md` (nested `/design`, `/review`, `/bump-version` calls). Canonical form:

```
Invoke `/implement` via the Skill tool:

- `/implement --merge [--no-admin-fallback if no_admin_fallback] [--no-logs-commit if no_logs_commit] [--coder=<value> if coder set] [--forked if forked_mode] [--draft if draft_mode] [--no-dynamic-archetypes|--dynamic-archetypes N when set] [--run-id <ID> if set] $ISSUE_NUMBER`
```

Export `SESSION_ENV_PATH="$FIX_ISSUE_TMPDIR/session-env.sh"` in the environment before the Skill tool call when the parent owns a caller session-env file — `/implement` Step 0 merges from `SESSION_ENV_PATH` via `session-setup.sh --caller-env` when set; do **not** pass removed `--session-env` argv.

The step heading + explicit Skill-tool line + scannable args shape makes the invocation impossible to miss. Do **not** collapse Pattern B into a single paragraph — see `## Avoid conditional phrasing for sub-skill invocations` below.

`scripts/lint-skill-invocations.py` mechanically enforces line-local co-location: every direct-invocation line that says ``Invoke `/<name>`'' (with optional `the` and a bounded `**bold-span**`) must also contain `via the Skill tool` on the same line.

## allowed-tools narrowing heuristic

Set `allowed-tools` to the minimum needed by the parent skill itself — never mirror the child skill's broader tool set. Three tiers cover every larch skill:

| Tier | `allowed-tools` | Example (with stable anchor) |
|---|---|---|
| Pure delegator | `Skill` | `skills/im/SKILL.md` frontmatter (allowed-tools line) — forwards only |
| Delegator that validates first | `Bash, Skill` | `skills/create-skill/SKILL.md` frontmatter — runs validation scripts before delegating |
| Hybrid orchestrator | `Skill` plus whatever the parent needs | `skills/implement/SKILL.md`, `skills/fix-issue/SKILL.md`, `skills/review/SKILL.md`, `skills/alias/SKILL.md`, `skills/research/SKILL.md` — parent runs setup, file I/O, git ops, and in `/alias`'s case a post-delegation sentinel-file verification. |

`allowed-tools: Skill` alone is **neither necessary nor sufficient** to classify a skill as a pure delegator — some delegators need `Bash` for input validation. Conversely, a skill with `Skill` in its allowed list is not automatically a delegator; hybrid orchestrators include `Skill` as one tool among many.

When in doubt, start narrow and widen only for tools the parent actually uses. If your skill adds `Skill` to `allowed-tools`, also confirm the frontmatter includes every other tool your parent invokes (Bash, Read, Edit, Glob, Grep, etc.). Omitting a needed tool produces silent runtime denials — not error messages — so the narrowing heuristic must be paired with a concrete accounting of parent tool usage.

## Post-invocation verification

**Scope**: this rule applies to **orchestrators that continue execution based on a child skill's side effects** — e.g., a parent that reads the child's output to decide the next step. Pure forwarders (`/im`, `/block-issue`, `/create-skill`, `/simplify-skill`, `/compress-skill`) are exempt — once they delegate, they do nothing further, so there is nothing to verify.

For every mandatory sub-skill call inside an orchestrator's step, pair the call with a **mechanical check that the parent cannot satisfy without the child's side effects**. The check must read the filesystem, parse stdout, or compare counters — never rely on the child's prose acknowledgement. If the child silently skipped or internally bailed, the check must notice.

Canonical examples:

- **Commit-count delta around `/bump-version`** — the orchestrator captures a pre-count, invokes the skill, then compares with a post-count:

  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/check-bump-version.sh --mode pre
  # Parse HAS_BUMP, COMMITS_BEFORE, STATUS from stdout.
  # Invoke /bump-version via the Skill tool.
  ${CLAUDE_PLUGIN_ROOT}/scripts/check-bump-version.sh --mode post --before-count "$COMMITS_BEFORE"
  # Parse VERIFIED, COMMITS_AFTER, EXPECTED, STATUS.
  # STATUS ∈ {ok, missing_main_ref, git_error}. MUST check STATUS=ok before trusting
  # the COMMITS_* counts — a non-ok STATUS means the count is 0-by-coercion, not
  # a legitimate "0 commits ahead" result (#172). --mode post already forces
  # VERIFIED=false when STATUS != ok, independent of the numeric comparison.
  ```

  See `skills/implement/SKILL.md § Step 8+ — Ship PR State Machine` for the full recipe. `--mode post` **requires** `--before-count $COMMITS_BEFORE` — calling `--mode post` without it errors out at the script level.

- **Parsed stdout machine value after `/issue`** — the orchestrator reads `ISSUES_CREATED=<N>` / `ISSUES_FAILED=<N>` / per-issue `ISSUE_N_NUMBER`/`ISSUE_N_URL` lines from `/issue`'s stdout. Without those parsed values, the parent cannot file the created issue links into the PR body. See `skills/implement/SKILL.md § Step 8+ — Ship PR State Machine` (the OOS pipeline runs as a checkpoint inside the ship-pr orchestration).

- **Sentinel file** — nested `/design` exports the full file-backed bundle (plan, plan-review tally, OOS, rejected findings, accepted-plan findings, optional architecture diagram) through `$IMPLEMENT_TMPDIR/design-export/manifest.env`. `/implement` Step 1 reads that manifest (or notices its absence / `MANIFEST_FAILED=true`) to hydrate `PLAN_FILE`, `PLAN_REVIEW_TALLY_FILE`, `CONTESTED_CRITERIA_FILE`, `OOS_FILE`, `REJECTED_FINDINGS_FILE`, `ACCEPTED_PLAN_FINDINGS_FILE`, and `ARCHITECTURE_DIAGRAM_FILE` — the manifest is the single file-backed handoff for the entire exported design bundle, not just one path. See `skills/design/scripts/{read,write}-design-manifest.md` for the schema.

- **Sentinel file (defense in depth) — `/research` → `/issue`** — when `/research` invokes `/issue` to file findings as GitHub issues, `/issue` writes a small KV sentinel at `$RESEARCH_TMPDIR/issue-completed.sentinel` (path supplied by `/research` via `/issue`'s narrow `--sentinel-file <path>` flag — NOT `--session-env`). `/research` runs the canonical `${CLAUDE_PLUGIN_ROOT}/scripts/verify-skill-called.sh --sentinel-file "$RESEARCH_TMPDIR/issue-completed.sentinel"` post-return and aborts on `VERIFIED=false`. Defense-in-depth precedence: **stdout parsing of `ISSUES_*` (the immediately-prior bullet) is the primary post-`/issue` mechanical check** for any caller; this sentinel-file gate is `/research`-specific defense-in-depth on top of stdout parsing, not a replacement. Both apply for `/research`. The sentinel proves *execution* (gate: `ISSUES_FAILED=0 AND !dry_run`), not creation count — the all-dedup outcome (`ISSUES_CREATED=0`, `ISSUES_DEDUPLICATED>=1`, `ISSUES_FAILED=0`) writes the sentinel and continues normally. See `skills/research/SKILL.md § Filing findings as issues` for the numbered procedure and `skills/issue/SKILL.md § Sentinel file (post-success)` for `/issue`'s side of the contract.

If you cannot name a concrete mechanical check, the call is not actually mandatory — reclassify it as Pattern A (pure delegation) or restructure so the child's side effect is observable.

See `## Anti-halt continuation reminder` below — the two sections govern the same call-site boundary from complementary directions (verification asks "did the child run?"; anti-halt asks "did the parent continue?").

<a id="anti-halt"></a>
## Anti-halt continuation reminder

**Scope**: this rule applies to the same orchestrator set as `## Post-invocation verification` above — stateful orchestrators (`/fix-issue`, `/implement`, `/review`, `/alias`, `/research`) that run additional steps after a child `Skill` tool call returns. Pure forwarders (`/im`, `/create-skill`, `/simplify-skill`, `/compress-skill`) are exempt — once they delegate, they do nothing further. The two sections are complementary: `## Post-invocation verification` asks **"did the child run?"**; this section asks **"did the parent continue?"** Both failure modes are distinct and real (see GitHub issue #177 for the originating report).

**The rule**: after every child `Skill` tool call (`/design`, `/review`, `/bump-version`, `/issue`, `/implement`) returns AND after every `Bash` tool call that completes a numbered step or sub-step, including `run-relevant-checks-captured.sh`, the main agent MUST immediately continue with the parent skill's NEXT step. The child's cleanup / summary output and helper stdout are NOT end-of-turn. Visible outputs (plans, diagrams, voting tallies, skip breadcrumbs, PR URLs, helper KEY=VALUE envelopes) are intermediate artifacts, NOT stopping points. Likewise, a summary, handoff, status recap, or "returning to parent" turn-ending message is a halt in disguise, not a valid continuation. In long sessions where the child produces many tokens (e.g., `/design` with 3 reviewers + voting easily produces 15k+ tokens), the main agent's attention can drift to the child's local "mission accomplished" framing and lose the parent orchestration frame. A short, standardized banner at the top of every orchestrator plus short per-call-site micro-reminders reinforce the rule where attention is most at risk.

**Carve-out (critical)**: the rule is strictly subordinate to any explicit non-sequential control-flow directive in the parent skill — including `skip to Step N`, `bail to cleanup`, `jump back to Step Na`, `loop back to Step 3a`, `fall through to 12c`, `break out of the loop`, or any other explicit redirect. A normal numerically-sequential `proceed to Step N+1` directive is the default continuation path that anti-halt reinforces — NOT an exception.

**Loop-internal carve-out**: when an orchestrator's step explicitly loops (a hypothetical Skill-tool call inside a loop body), the "next step" of the parent IS the loop-continuation directive, not the first textually-following section header. Use the loop-aware micro-reminder variant at loop-internal child-Skill call sites.

**Generic relevant-checks clause**: every direct `/relevant-checks` Skill invocation and every `run-relevant-checks-captured.sh` helper call anywhere in an orchestrator SKILL.md is covered by this rule. The parent must resume after the check returns — whether that means advancing to the next numbered step, re-running validation after a fix, or committing the fixed files.

### Canonical banner (top of each orchestrator SKILL.md, after the title body, before `## Progress Reporting`)

````markdown
**Anti-halt continuation reminder.** After every child `Skill` tool call (e.g., `/design`, `/review`, `/bump-version`, `/issue`, `/implement`) returns AND after every numbered-step `Bash` helper call, including `run-relevant-checks-captured.sh`, IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on the child's cleanup output or helper stdout, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. The rule is strictly subordinate to any explicit non-sequential control-flow directive in THIS file (e.g., `skip to Step N`, `bail to cleanup`, `jump back`, `loop back`, `fall through`, `break out`). A normal sequential `proceed to Step N+1` instruction is the default continuation this rule reinforces, NOT an exception. Every relevant-checks helper call anywhere in this file is covered by this rule. → shared/subskill-invocation.md#anti-halt
````

The substring `**Anti-halt continuation reminder.**` is a contract token asserted by `${CLAUDE_PLUGIN_ROOT}/scripts/test-anti-halt-banners.sh`.

### Canonical micro-reminder (per Skill-tool call site — branch-specific placement)

Place the micro-reminder **inside the specific branch that actually invokes the child** — not at the top of a step whose body may skip the invocation on some branches (e.g., `/implement` Step 1 both-externals-down skips `/design`; Step 8 `HAS_BUMP=false` skips `/bump-version`). The reminder belongs next to the real Skill-tool call, inside the branch that emits it.

Standard variant:

````markdown
> **Continue after child returns.** When the child Skill returns, execute the NEXT step of this skill — do NOT end the turn, and do NOT write a summary, handoff, or "returning to parent" message. → shared/subskill-invocation.md#anti-halt
````

Loop-aware variant (for loop-internal Skill-tool call sites in orchestrators with explicit loop bodies):

````markdown
> **Continue after child returns (loop-internal).** When the child Skill returns, continue the loop per the parent's explicit loop-back directive — do NOT exit the loop unless the exit condition fires, and do NOT write a summary, handoff, or "returning to parent" message. → shared/subskill-invocation.md#anti-halt
````

The substring `Continue after child returns` is a contract token asserted by `${CLAUDE_PLUGIN_ROOT}/scripts/test-anti-halt-banners.sh` (matches both the standard and loop-internal variants).

### Scope list

The banner MUST appear in these orchestrator SKILL.md files:

- `skills/fix-issue/SKILL.md`
- `skills/implement/SKILL.md`
- `skills/review/SKILL.md`
- `skills/alias/SKILL.md`
- `skills/research/SKILL.md`

The banner MUST NOT appear in pure-delegator SKILL.md files:

- `skills/im/SKILL.md`
- `skills/block-issue/SKILL.md`
- `skills/create-skill/SKILL.md`
- `skills/simplify-skill/SKILL.md`
- `skills/compress-skill/SKILL.md`

Both presence and absence are enforced by `${CLAUDE_PLUGIN_ROOT}/scripts/test-anti-halt-banners.sh`, wired into `make lint` via the `test-anti-halt` target.

<a id="step-boundary"></a>
## Step-boundary anti-halt

**Scope**: this rule covers numbered-step boundaries where the parent skill has just completed a step or sub-step and the next action is another numbered step, not a child `Skill` return. It is especially important after skip breadcrumbs, status footers, and terminal-sounding helper output where there is no immediately adjacent Skill-tool micro-reminder to re-anchor continuation.

**Canonical form**: use a two-line blockquote at the specific boundary:

````markdown
> **Continue to Step N IMMEDIATELY.** <One-sentence reason this boundary is not terminal and what remains.>
````

This is deliberately separate from the `Continue after child returns` micro-reminder above. The micro-reminder fires at Skill-tool call sites; the step-boundary reminder fires between numbered steps, including Bash-only or prose-only tails. Use the step-boundary form sparingly at halt-prone boundaries and include a pointer to this section on the first such reminder in each SKILL.md so future edits can find the single source of truth.

## Session-env handoff

2. The parent passes `--session-env "$PARENT_TMPDIR/session-env.sh"` to the child.
3. The child reads the file via `${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh ... --caller-env "$SESSION_ENV_PATH"`.

Canonical producers and consumers in the live tree:

- `skills/fix-issue/SKILL.md § Step 1 — Setup` writes `$FIX_ISSUE_TMPDIR/session-env.sh` and passes it to `/implement` (Step 0 acquires the `IN PROGRESS` comment lock and applies the `[IN PROGRESS]` title prefix before the tmpdir / session-env exist).
- `skills/implement/SKILL.md § Step 0 — Session Setup` accepts `--session-env` from its parent and propagates a fresh `$IMPLEMENT_TMPDIR/session-env.sh` to `/design` and `/review` via `--session-env` on each invocation. It also writes `PREV_IMPLEMENT_TMPDIR=$IMPLEMENT_TMPDIR` so a future `/implement` session can copy the previous session's `larch-logs` subtree into its fresh tmpdir, and `LARCH_CLAUDE_PLUGIN_ROOT` so later Bash blocks can recover `${CLAUDE_PLUGIN_ROOT}` without sourcing the file.
- The same `/implement` handoff may also carry `LARCH_DYNAMIC_ARCHETYPES_MAX=<0..8>` when the parent operator selected `--dynamic-archetypes <N>` or `--no-dynamic-archetypes`; nested review launchers should preserve that validated key through `session-setup.sh --caller-env` / `--write-session-env` so Step 5 can replay the chosen cap.
- `skills/design/SKILL.md § Step 0 — Session Setup` and `skills/review/SKILL.md § Step 0 — Session Setup` both accept `--session-env` as an `--caller-env` forward; their Bash blocks also read `LARCH_CLAUDE_PLUGIN_ROOT` directly from that file when `${CLAUDE_PLUGIN_ROOT}` needs rehydration before helper invocation.

<a id="artifact-only-return"></a>
## Artifact-only return contract (nested mode)

When `SESSION_ENV_PATH` is non-empty, a child skill is running in nested mode under a parent orchestrator such as `/implement`. In this mode, child skills emit ONLY:

- a terminal machine footer made of a structured heading plus `KEY=VALUE` lines; and
- artifact file paths needed by the parent to read human-facing content.

All human-readable content must be file-backed. Step breadcrumbs, round summaries, voting tallies, reviewer scoreboards, implementation plans, architecture diagrams, rejected-finding prose, explanatory prose, and status narration are forbidden in parent-visible output when nested. If the parent needs any of that content, the child writes it to an artifact and the parent reads the artifact on demand.

Canonical examples:

- `/design` writes plan, tally, OOS, rejected-finding, accepted-finding, and optional architecture-diagram artifacts, then exports the design manifest for `/implement`.
- `/review --diff` writes `$REVIEW_TMPDIR/review-round-summary.md` before Step 4 returns. When nested, Step 4 copies it to `$(dirname "$SESSION_ENV_PATH")/review-round-summary.md`, suppresses inline prose, and emits only the `### review-result` KV footer plus that artifact path; `/implement` reads the stable parent-tmpdir summary file for its `code-review-tally` log batch.

Standalone invocations (`SESSION_ENV_PATH` empty) preserve their normal visible prose and artifact replay behavior.

### Security — never `source` a session-env file

**Do NOT `source` `session-env.sh`.** Parse it line-by-line with `KEY=VALUE` matching. The file crosses a trust boundary (written by one skill, consumed by another), so `source` would execute arbitrary shell if any line contained `$(...)`, backticks, or command substitution. The canonical safe-parse pattern lives in `${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh` (the `--caller-env` reader).

When your skill consumes a session-env file, always route through `session-setup.sh --caller-env` rather than ad-hoc `while read` loops so the safe-parse invariant is centralized.

### Health sidecar

## Subagent execution topology

`--session-env` and `--subagent` address orthogonal concerns. Forward both when a parent orchestrator delegates heavy work to `/design`.

- **`--subagent` — execution topology.** Runs `/design`'s heavy non-interactive phase (adaptive sketches → plan → plan review → optional architecture diagram) inside an isolated Agent-tool subagent. The subagent reads `$DESIGN_TMPDIR/run-params.json`, writes raw artifacts to `$DESIGN_TMPDIR/`, and returns terse status; the parent's transcript stays small. Without `--subagent`, the heavy phase runs in `/design`'s own in-turn context — richer transcript, higher token cost in the parent. See `skills/design/SKILL.md § Step 2a — Collaborative Approach Sketches` (Subagent heavy phase).

The two flags are independent: `--session-env` shapes what crosses the call boundary; `--subagent` shapes where heavy work executes. Verbosity suppression remains gated on `SESSION_ENV_PATH` regardless of dispatch mode.

### Normative pattern for nested orchestrators

When an orchestrator (e.g. `/implement`) delegates heavy planning to `/design`, forward both flags. `/implement` controls the `--subagent` decision through its own `--inline` flag:

- Default (`inline_mode=false`): `/implement` appends `--subagent` to its Step 1 `/design` invocation. The heavy phase runs in an isolated subagent; only terse breadcrumbs reach the parent.
- `--inline` (`inline_mode=true`): `/implement` omits `--subagent`. The heavy phase runs in `/design`'s in-turn context; the full reviewer transcript is visible at higher token cost.

`--inline` controls execution topology only — verbosity suppression in the child is unchanged because `SESSION_ENV_PATH` remains non-empty under both settings. See `skills/implement/SKILL.md § Step 1 — Ensure Design Plan Exists` (canonical invocation order) and the `--inline` flag definition at the top of that file.

`--quick`, `--full`, and caller-forwarded classification interact with `--subagent` along these paths:

- **`/implement`** always invokes `/design` on the Skill path unless the both-externals-down inline-plan branch applies; the `--inline` vs `--subagent` distinction matters for that `/design` invocation.
- **`/design`** still runs the sketch and plan-review flow, but `--subagent` is ignored: `/design`'s Step 2a heavy-subagent branch is gated on `subagent_mode=true AND quick_mode=false`, so quick mode falls back to the inline path.
- **`/design --full`** forces `sketch_budget=4`. When combined with `--quick`, the sketch budget stays full while plan review remains quick.
- **`/implement`** passes `--design-classification HARD` on the canonical `/design` argument list (simplicity-based pre-design routing was removed). `/design` trusts that value only with complete `--branch-info`; standalone invocations classify locally and write `design_classification_source=router-pre-design`.

## Avoid conditional phrasing for sub-skill invocations

The worst shape, and the one that gets skipped most often, is a single-line conditional paragraph that buries the Skill-tool invocation:

> If the classification is HARD, call `/implement --auto --merge --session-env $TMPDIR/session-env.sh <description>`; otherwise call `/implement --auto --merge --session-env $TMPDIR/session-env.sh <description>` (same invocation — do not branch on a pre-design "SIMPLE" guess).

Prose conditionals bury the invocation and reliably slip past the executing model — especially mid-run. Rewrite as an explicit numbered sub-step whose center is the `Skill` tool call (or as Pattern B's heading + variant bullets shape), so the Skill-tool call is the visual center of the step.

<a id="bare-name-fallback"></a>
## Bare-name-then-fully-qualified fallback

Skill resolution from a consumer repo differs from resolution inside the larch plugin repo itself. In a consumer repo with the plugin installed, `"implement"` resolves correctly — but in a repo where the plugin is installed under a different namespace, the bare name may miss. Always use the two-step fallback:

- **First**: try the bare name — `"implement"`, `"design"`, `"review"`.
- **Second** (only if no skill matched): try the fully-qualified name — `"larch:implement"`, `"larch:design"`, `"larch:review"`.

Never start with the fully-qualified name — it couples the caller to the plugin namespace and breaks in repos that install the plugin under a different name. The alias generator at `${CLAUDE_PLUGIN_ROOT}/skills/alias/scripts/generate-alias.sh` emits this fallback automatically for every alias — see the generated `## Behavior` section inside the `HEREDOC_BODY` block (lines 72-86) of that script; follow the same shape when authoring an invocation by hand.

## Agent-type qualified-name-first fallback

Agent resolution differs from skill resolution. Plugin-defined agents (e.g., `agents/code-reviewer.md`) are namespaced at runtime as `<plugin-name>:<agent-name>` — the bare name does **not** resolve. This is the opposite of the skill-name pattern, where bare names resolve first.

- **First**: try the fully-qualified name — `"larch:code-reviewer"`.
- **Second** (only if not found): try the bare name — `"code-reviewer"`.

All `subagent_type` references in larch skills use the qualified name `larch:code-reviewer`. If a consumer installs the plugin under a different namespace, the bare-name fallback activates.

---

## Cross-references

- `AGENTS.md § Canonical sources` — lists this file as a canonical source (update triggers live at the bottom of this file).
- `skills/shared/progress-reporting.md` — adjacent contract for step-progress formatting.
- `skills/shared/reviewer-templates.md` — canonical source for the Code Reviewer archetype (parallel shared-doc pattern).

## Update triggers

This file is the canonical source for sub-skill invocation conventions (Pattern A bulleted vs Pattern B inline, `allowed-tools` narrowing heuristic, post-invocation verification for orchestrators, anti-halt continuation reminder for orchestrators (closes #177), `session-env` handoff and safe-parse rule, artifact-only return contract for nested child skills, subagent execution topology and the dual-flag (`--session-env` + `--subagent`) handoff for nested orchestrators (closes #1039), anti-conditional-phrasing for Skill-tool calls, bare-name-then-fully-qualified fallback, agent-type qualified-name-first fallback). Runtime surface (ships to consumers under `skills/`). No generated artifact — update directly. Update trigger: when a cited source-example skill (`/im`, `/alias`, `/create-skill`, `/fix-issue`, `/implement`, `/review`) changes its invocation pattern, artifact-only nested return behavior, or its anti-halt banner/micro-reminder, update the corresponding example in the guide in the same PR. Additional trigger: when `/design` (`skills/design/SKILL.md` or `skills/design/references/heavy-worker.md`) changes `--subagent`, `--quick`, `--session-env`, manifest export, or nested verbosity behavior, update the `## Subagent execution topology` section in the same PR. `skills/create-skill/scripts/render-skill-md.sh` emits a `## Sub-skill Invocation` reminder block referencing this file into every scaffolded skill; `skills/create-skill/scripts/test-render-skill-md.sh` is the regression harness guarding that emission (wired into `make lint` via the `test-render-skill` target). `scripts/test-anti-halt-banners.sh` is the paired regression harness for the anti-halt banner and micro-reminder — it asserts banner presence in the five orchestrator SKILL.md files (`/fix-issue`, `/implement`, `/review`, `/alias`, `/research`), absence in the five pure-delegator SKILL.md files (`/im`, `/block-issue`, `/create-skill`, `/simplify-skill`, `/compress-skill`), and micro-reminder presence in each of the orchestrators. `/alias` is classified as an orchestrator because its Step 4 runs a sentinel-file verification after `/implement` returns. `/research` is classified as an orchestrator because it may invoke `/issue` via the Skill tool and continue to its report/cleanup steps. Wired into `make lint` via the `test-anti-halt` target.
