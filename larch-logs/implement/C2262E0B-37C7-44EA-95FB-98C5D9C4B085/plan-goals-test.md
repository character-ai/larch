## Goal
Combine root-cause prompt restructure (Part A) with per-side cross-tool waterfall retry (Part B) in /design dialectic to prevent quorum truncation.

## Implementation Plan
## Plan

Combine a root-cause prompt fix (Part A) with a per-side cross-tool waterfall retry (Part B). Both ship together. The waterfall is the safety net for any residual quality failure; the prompt restructure reduces how often that net is needed.

### Part A — Restructure debate prompts to lead with explicit OUTPUT FORMAT

Rewrite both thesis and antithesis templates in `skills/design/references/dialectic-debate.md` so:

1. The first content block after the role sentence is an **OUTPUT FORMAT** section showing the exact required structure:

   ```
   OUTPUT FORMAT — produce EXACTLY this structure, in this order, with no other top-level prose:

   <steelman>
   [1-2 full sentences: the strongest version of the opposing case. Do not straw-man.]
   </steelman>
   <claim>
   [Your position in one full sentence.]
   </claim>
   <evidence>
   [At least one concrete file:line citation obtained via Read/Grep/Glob; ≥1 full sentence of substantive content.]
   </evidence>
   <strongest_concession>
   [The best opposing point, acknowledged honestly; ≥1 full sentence.]
   </strongest_concession>
   <counter_to_opposition>
   [Refute the concession directly; do not restate your claim; ≥1 full sentence.]
   </counter_to_opposition>
   <risk_if_wrong>
   [What breaks if your position loses; ≥1 full sentence.]
   </risk_if_wrong>
   RECOMMEND: THESIS
   ```
   (Antithesis template uses `RECOMMEND: ANTI_THESIS`.)

2. **Promote steelman to a 6th required tag** (`<steelman>`) at the top of the structured block. This converts the failure mode "produce steelman then stop" into "produce 6 tags or none" — the model treats the steelman as part of the structured deliverable, not a prelude that can substitute for it.

3. Add a **SELF-CHECK BEFORE FINISHING** directive immediately after the OUTPUT FORMAT block:

   ```
   SELF-CHECK BEFORE STOPPING (verify in order):
   1. Did you emit all 6 tags: <steelman>, <claim>, <evidence>, <strongest_concession>, <counter_to_opposition>, <risk_if_wrong>?
   2. Did you write `RECOMMEND: THESIS` (or `RECOMMEND: ANTI_THESIS`) as a standalone final line?
   3. Is your prose outside the tags under the 250-word cap?
   If any answer is "no", complete the missing parts BEFORE stopping.
   ```

4. Move the existing content rules (250-word cap, anti-patterns list, proportionality lens for antithesis, reader clause) below OUTPUT FORMAT and SELF-CHECK under a `## Content rules` header so they remain authoritative but no longer compete for first-position attention.

5. Keep the reference blocks `<debater_synthesis>` and `<debater_decision>` at the end (their position is fine; they're reference material).

### Part B — Per-side cross-tool waterfall retry

#### B.1 — Change original launch assignment from bucket-homogeneity to per-side cross-tool

Today, `skills/design/references/dialectic-execution.md` step 3 assigns both sides of a decision to the same tool (bucket homogeneity: odd N → Cursor for both sides; even N → Codex for both sides). Replace this with per-side assignment:

- **Decision N odd**: thesis = Cursor, antithesis = Codex.
- **Decision N even**: thesis = Codex, antithesis = Cursor.

This rotation alternates per decision (mirrors the existing position-order rotation in `skills/shared/dialectic-protocol.md` "Position-order rotation" section) and guarantees that, in normal conditions, each decision is debated by two different external tools.

**Degraded mode** (one external unavailable at launch time): assign both sides to the available external. The waterfall retry (B.3) then falls directly to Claude when one of those sides fails.

**Zero-externals mode**: existing guardrail (Step 2a.5 step 5) still fires; no debate occurs.

#### B.2 — Retry trigger covers ALL quorum failures (recoverable + no_output)

A side enters the waterfall whenever the existing quorum gate would classify the decision as `fallback-to-synthesis` for that side, regardless of reason. Reasons: `no_output` (collector `STATUS != OK`), `missing_tag`, `bad_recommend`, `missing_citation`, `role_mismatch`, `substantive_empty`. The orchestrator no longer immediately classifies the decision — it queues the failing side for retry.

#### B.3 — Per-side waterfall order

For each failing side, the retry tool sequence is:

- Thesis originally Cursor → 1st retry **Codex** → 2nd retry **Claude**.
- Thesis originally Codex → 1st retry **Cursor** → 2nd retry **Claude**.
- Antithesis originally Codex → 1st retry **Cursor** → 2nd retry **Claude**.
- Antithesis originally Cursor → 1st retry **Codex** → 2nd retry **Claude**.

Generalized: the 1st retry uses the OTHER external tool; the 2nd retry uses Claude (final fallback). Maximum 2 retries per side, max 3 launches per side (original + 2 retries). If a retry succeeds the quality gate, the side is considered passed and proceeds to the judge ballot with that retry's output.

**Parallel execution.** When both sides need a 1st retry, both launches go out in the same Bash message (per-side parallelism). Same for 2nd retries. The waterfall itself is sequential per side (1st retry must collect before 2nd is decided) but parallel across sides.

**Pre-launch presence re-check.** Immediately before each retry wave, run `scripts/check-reviewers.sh` and refresh dialectic-local presence flags (`dialectic_codex_available`, `dialectic_cursor_available`). A tool that was unavailable at original launch may be available now, and vice versa. Do NOT mutate orchestrator-wide `codex_available` / `cursor_available` (Step 3 plan-review uses those).

**Skip retry slot when target unavailable.** If the 1st-retry target (other external) is unavailable at retry time, skip directly to 2nd retry (Claude). If Claude (the 2nd retry) is somehow unavailable (Agent tool not present), the side cannot be recovered — proceed to final classification.

#### B.4 — Output file naming and timing-task-kind literals

Output paths follow a deterministic per-tool / per-side / per-attempt pattern so the collector's basename heuristic correctly attributes results:

- Original launch: `$DESIGN_TMPDIR/debate-<n>-<tool>-<side>.txt` (existing pattern, unchanged).
- 1st retry: `$DESIGN_TMPDIR/debate-<n>-<retry-tool>-<side>-retry1.txt`.
- 2nd retry (Claude): `$DESIGN_TMPDIR/debate-<n>-claude-<side>-retry2.txt`.

New timing-task-kind literals to register in `scripts/lib-timing-kinds.sh` `TIMING_TASK_KINDS_ALLOWED`:

- `cursor-debate-thesis-retry1`, `cursor-debate-antithesis-retry1`
- `codex-debate-thesis-retry1`, `codex-debate-antithesis-retry1`
- `claude-debate-thesis-retry2`, `claude-debate-antithesis-retry2`

#### B.5 — Corrective-prompt rendering

Create `scripts/render-debate-retry-prompt.sh`. Reads the ORIGINAL prompt file (the one the failed launch was pointed at) and produces a NEW prompt file that includes:

1. An explicit failure-mode summary at the top: "Your previous response had the following structural issues: \<list\>". The list is built from the quorum-failure reason tokens (`missing_tag: <which tags>`, `bad_recommend: <what was wrong>`, `missing_citation`, `role_mismatch: emitted <X> but role is <Y>`, `substantive_empty: tag bodies too short`, `no_output: previous launch produced no output`).
2. A direct instruction: "Respond AGAIN to the task. Emit all 6 required tags and the `RECOMMEND:` line. Do not truncate."
3. The full ORIGINAL prompt body verbatim below the directives (so the model has identical task context).
4. For Claude (2nd retry only): also append "Do not self-identify your underlying model in your output" to mitigate attribution leak (see "Failure modes" below).

The CLI surface:

```
scripts/render-debate-retry-prompt.sh \
  --original-prompt-file <path> \
  --previous-output-file <path> \
  --failure-reason <token>[,<token>...] \
  --retry-tool codex|cursor|claude \
  --output <path>
```

Stdout: machine-parseable KV lines (`RENDERED=true`, `OUTPUT_FILE=<path>`).

Sibling: `scripts/render-debate-retry-prompt.md` (per `.claude/rules/script-md-siblings.md`).

#### B.6 — Updated final classification

After the waterfall settles:

- Both sides pass at any attempt (original or retry): `Disposition: voted` candidate; proceeds to judge ballot. The successful output (whether original or retry) is what feeds the ballot Defense block.
- One or both sides fail after all retries: `Disposition: fallback-to-synthesis`, `Why fallback`: `<original failure reason> [waterfall exhausted: <retry1=tool/result, retry2=tool/result>]`.

The dialectic-resolutions.md schema gains an optional `Waterfall trace` field on fallback-to-synthesis entries (one line, e.g., `cursor=missing_tag → codex=ok-but-still-missing_tag → claude=ok`). Voted entries do NOT include the trace.

### Part C — Documentation and contract updates

1. **`skills/shared/dialectic-protocol.md`**:
   - Rewrite the "Position-order rotation" section to note that tool assignment is per-side (not per-bucket).
   - Add a new section "Per-side waterfall retry" under the Disposition Enum that documents B.1–B.6.
   - Add Claude waterfall exception to "Judge Panel Composition" (Claude is permitted as the FINAL waterfall slot for debaters; the GH#98 rule still forbids Claude as PRIMARY or 1st-retry debater).
   - Update Disposition table to note that `voted` may use retry outputs, and `fallback-to-synthesis` reason may carry a `[waterfall exhausted: …]` suffix.
   - Update the eligibility gate paragraph to require 6 tags including `<steelman>`.

2. **`skills/design/SKILL.md`** Anti-patterns NEVER #2: change the absolute "NEVER substitute a Claude subagent into a dialectic debate bucket" to a tighter rule with an explicit exception. New text body:

   ```
   2. **NEVER substitute Claude into a dialectic debate as the PRIMARY or 1ST-RETRY debater.** **Why:** the debate path uses externals (Cursor/Codex) because model-specific writing style could encode tool identity into adversarial arguments; see GitHub issue #98. **How to apply:** the original launch and the 1st-retry launch in the per-side waterfall both target external tools only. **Exception:** Claude IS permitted as the 2nd-retry (FINAL) waterfall step for a side that has already failed with both externals — this trades a small attribution-leak risk for the chance to actually hear the antithesis instead of always defaulting to synthesis. The judge-panel path remains under the repo-wide replacement-first pattern (Claude permitted as a panel slot per `dialectic-protocol.md`).
   ```

3. **`skills/design/references/dialectic-execution.md`**:
   - Step 3 (bucket assignment): replace with per-side assignment (B.1).
   - After step 8 (collect): insert step 8b (waterfall retry choreography) covering B.2–B.6.
   - Step 9 (per-bucket runtime failure handling): retitle to "Per-side failure queuing" — failures no longer immediately classify; they enter the waterfall queue.
   - Update the "Eligibility gate (Dispositions)" section: `fallback-to-synthesis` now means "failed after full waterfall."
   - Update the "Write `$DESIGN_TMPDIR/dialectic-resolutions.md`" sub-section: add the optional `Waterfall trace` field for fallback-to-synthesis entries.

4. **`skills/design/SKILL.md`** Step 2a.5 inline body (the bucket-assignment summary block under the "Deterministic per-decision bucket assignment" bullet): change the two "Decision 1, 3, 5 → Cursor bucket" / "Decision 2, 4 → Codex bucket" lines plus the "bucket homogeneity" line to point at the new per-side assignment in `dialectic-execution.md` (Cursor/Codex alternation per side per decision).

### Part D — Helpers

Create:

- `scripts/render-debate-retry-prompt.sh` (per B.5).
- `scripts/render-debate-retry-prompt.md` (sibling doc).

### Part E — Tests

Create:

- `scripts/test-render-debate-retry-prompt.sh` covering each failure-reason token, each retry-tool target, original-prompt verbatim preservation, output-file naming, and CLI flag validation. Wire into `Makefile` next to similar `test-*.sh` targets.
- `scripts/test-render-debate-retry-prompt.md` (sibling doc).

Extend an existing structural test (most likely `scripts/test-design-structure.sh` — read its current assertions before editing) to assert:

- `dialectic-execution.md` contains the literal token `waterfall` in step 8b and per-side assignment language in step 3.
- `dialectic-protocol.md` contains a "Per-side waterfall retry" section header.
- `SKILL.md` NEVER #2 contains the literal token `2nd-retry` (or equivalent pinned phrase establishing the Claude exception).
- The 6 new `TIMING_TASK_KINDS_ALLOWED` entries from B.4 exist in `scripts/lib-timing-kinds.sh`.

If no existing design-structure test exists or it does not cover these areas, create a new harness `skills/design/scripts/test-dialectic-waterfall-contract.sh` + sibling `.md`.

Run `make lint`, `make lint-bash32`, and the new harnesses to confirm clean.

### Files to modify

- `skills/design/references/dialectic-debate.md` — Restructure both prompt templates per Part A (lead with OUTPUT FORMAT, promote steelman to 6th tag, add SELF-CHECK directive, move existing rules under `## Content rules`).
- `skills/design/references/dialectic-execution.md` — Per-side tool assignment in step 3; new step 8b (waterfall retry); updated step 9; updated Eligibility gate and resolution-writing sections; reference `render-debate-retry-prompt.sh`.
- `skills/shared/dialectic-protocol.md` — Document per-side assignment, waterfall retry section, Claude waterfall exception, optional `Waterfall trace` resolution field. Update eligibility gate to recognize 6 tags including `<steelman>`.
- `skills/design/SKILL.md` — Update NEVER #2 with the 2nd-retry-Claude exception; update Step 2a.5 inline bucket-assignment summary to point at per-side assignment.
- `scripts/lib-timing-kinds.sh` — Add 6 new timing-task-kind literals from B.4.
- `Makefile` — Register `test-render-debate-retry-prompt` target (and `test-dialectic-waterfall-contract` if created).

### Files to create

- `scripts/render-debate-retry-prompt.sh` — Corrective-prompt renderer per B.5.
- `scripts/render-debate-retry-prompt.md` — Sibling doc.
- `scripts/test-render-debate-retry-prompt.sh` — Unit harness.
- `scripts/test-render-debate-retry-prompt.md` — Sibling doc.
- (Conditional, see Part E) `skills/design/scripts/test-dialectic-waterfall-contract.sh` + sibling `.md`.

### Implementation steps (numbered, ordered)

1. **`render-debate-retry-prompt.sh`** + harness + sibling docs. Self-contained; can be developed and tested in isolation. Verify with `make lint-bash32` and the new harness.
2. **`scripts/lib-timing-kinds.sh`**: add the 6 new entries.
3. **`skills/design/references/dialectic-debate.md`**: restructure both templates per Part A. Single file; bytes-only diff. Verify by re-rendering one template with sample substitutions and eyeballing the rendered prompt file.
4. **`skills/shared/dialectic-protocol.md`**: update eligibility gate to expect 6 tags (add `<steelman>`); add per-side assignment + waterfall + Claude exception sections.
5. **`skills/design/references/dialectic-execution.md`**: update step 3 (per-side assignment); insert step 8b (waterfall choreography); update step 9; update Eligibility gate and resolution-writing sections.
6. **`skills/design/SKILL.md`**: update NEVER #2 with the exception; update Step 2a.5 inline bucket-assignment summary.
7. **Structural test extension** (`scripts/test-design-structure.sh` if it exists, otherwise new `skills/design/scripts/test-dialectic-waterfall-contract.sh`): pin the new contract language and timing-task-kind entries.
8. **`Makefile`**: register new test targets.
9. **Final**: `make lint`, `make lint-bash32`, `bash scripts/relevant-checks.sh`. Confirm clean.

### Edge cases

- **One external unavailable at original launch**: both sides launched with the available external (degraded original assignment). 1st retry waterfall target = the unavailable tool — if presence re-check shows it back online, retry with it; otherwise skip directly to Claude (2nd retry).
- **Both externals unavailable at original launch**: existing Step 2a.5 step 5 zero-externals guardrail still fires; no debate occurs; no waterfall.
- **Pre-launch presence re-check shows a tool is back online**: use it for the retry. Conversely, an external that was available at original launch but is gone at retry time → skip that retry tier.
- **One side succeeds (original or retry), other side exhausts waterfall**: decision falls back to synthesis. The successful side's defense is preserved in `dialectic-resolutions.md` under the appropriate `<Thesis|Antithesis> summary` field; the failed side's summary is `(no defense — waterfall exhausted)`.
- **Retry succeeds quorum gate but Claude self-identifies in output**: the corrective prompt for retry-tool=claude includes "Do not self-identify your underlying model"; attribution stripping at ballot-construction time provides a second layer of defense. If self-identification slips through, the judge can downweight on style — accepted residual risk per the GH#98 exception language in NEVER #2.
- **Same-decision concurrent retries hit serial-lock**: `launch-review.sh` already uses `external_serial_lock_acquire` for external launches. Retries launched in a single Bash message contend for the same lock; the existing lock handles this. No new serialization required.
- **Bash 3.2 portability** for `render-debate-retry-prompt.sh`: use newline-delimited temp files instead of associative arrays; `case` statements instead of parameter case conversion; `>>file 2>&1` instead of `&>>file`. Run `make lint-bash32`.
- **Existing run logs with prior bucket-homogeneity outputs**: this change is forward-only; existing `larch-logs/design/<RUN_ID>/` artifacts retain their original naming. The retry naming pattern (`*-retry1.txt`, `*-retry2.txt`) is additive.
- **Step 3 plan review unaffected**: orchestrator-wide `codex_available` / `cursor_available` flags remain untouched by the dialectic waterfall (only `dialectic_*_available` shadows are mutated). Preserve the Option B snapshot pattern.

### Failure modes

The 3 most likely architectural/systemic failure paths.

1. **Claude attribution leak in 2nd-retry output**.
   - **Earliest warning signal**: the ballot inadvertently contains `Claude` / `Anthropic` / `Sonnet` tokens after attribution stripping. Today the protocol greps for `Cursor` / `Codex` / `Claude` tokens at ballot-construction time but stripping is asymmetric to defense bodies.
   - **Simplest mitigation**: extend the ballot-construction attribution-strip to scrub `Claude`, `Anthropic`, `Sonnet`, `Opus`, `Haiku` substrings (case-insensitive) from defense bodies. Add the corrective prompt instruction "Do not self-identify your underlying model" for Claude retries (B.5 step 4). Add a test assertion that `dialectic-ballot.txt` contains none of these substrings after a Claude-retry path.

2. **Waterfall extends real wall time past `/design` operator expectations**.
   - **Earliest warning signal**: a `/design --hard` run that historically took ~30 minutes for dialectic suddenly takes 90+ minutes because multiple decisions exhaust the waterfall.
   - **Simplest mitigation**: emit a breadcrumb per retry wave (`⏩ 2a.5: waterfall retry 1 — <N> sides retrying`) so operators see live progress. Cap each retry timeout at the existing 1800s budget — do NOT increase per-launch budget (the gain is reliability across retries, not longer single calls). Document the new worst-case in `dialectic-protocol.md`.

3. **`render-debate-retry-prompt.sh` produces an over-long prompt that itself gets truncated by Cursor**.
   - **Earliest warning signal**: 1st-retry outputs ALSO truncate after the steelman, identical failure shape.
   - **Simplest mitigation**: the corrective prompt MUST place the failure-mode summary and "respond AGAIN" directive at the TOP, followed by the original task body. The original task body now starts with the new OUTPUT FORMAT block (Part A), so the structured-output requirement is up-front regardless of total prompt length. Add a harness assertion that the rendered retry prompt has the OUTPUT FORMAT block within the first N characters (e.g., first 2000) — pin the structural invariant.

### Testing strategy

Tests added/modified:

- **New unit harness** `scripts/test-render-debate-retry-prompt.sh`:
  - Covers each failure-reason token (`missing_tag`, `bad_recommend`, `missing_citation`, `role_mismatch`, `substantive_empty`, `no_output`) and combinations.
  - Covers each retry-tool target (`codex`, `cursor`, `claude`).
  - Asserts: original prompt body is preserved verbatim; failure summary lists the right reasons; Claude branch appends the "do not self-identify" instruction.
  - Asserts: output-file naming respects the per-tool / per-side / per-attempt convention.
- **New or extended structural test** (`scripts/test-design-structure.sh` extension or `skills/design/scripts/test-dialectic-waterfall-contract.sh`):
  - `dialectic-execution.md` contains `waterfall` token in step 8b and per-side assignment language in step 3.
  - `dialectic-protocol.md` contains a "Per-side waterfall retry" section header.
  - `dialectic-protocol.md` eligibility gate lists 6 required tags including `<steelman>`.
  - `dialectic-debate.md` contains the literal token `OUTPUT FORMAT` as a section header and `SELF-CHECK BEFORE STOPPING` as a directive header.
  - `SKILL.md` NEVER #2 contains the literal token `2nd-retry` (or pinned phrase establishing the Claude exception).
  - `scripts/lib-timing-kinds.sh` `TIMING_TASK_KINDS_ALLOWED` contains all 6 new entries.
- **`make lint`** and **`make lint-bash32`** continue to pass.
- **`bash scripts/relevant-checks.sh`** continues to pass.

Manual smoke test (operator-driven, post-merge):

- Run `/design --hard <feature-issue>` on a feature with at least one contested decision; confirm dialectic resolutions show no `fallback-to-synthesis` when both externals are responsive. If a truncation can be synthetically forced (e.g., very short cap), confirm the waterfall retry kicks in and the resolution comes back as `voted`.

### Breaking changes

- **Contract change in `dialectic-protocol.md`**: eligibility gate now requires 6 tags including `<steelman>`. No external consumer parses defense bodies; the only in-tree consumers (`/design` Step 2b plan generation and Step 3.5 still-contested matching) read the resolution schema's Disposition/summary fields, not the tag set — both compatible.
- **NEVER #2 in `SKILL.md`** changes from absolute to permitting Claude as the 2nd-retry waterfall slot. This is a deliberate relaxation; the original GH#98 rationale (no Claude in adversarial debate) is preserved for PRIMARY and 1st-retry slots.
- **Per-side launch assignment** replaces bucket homogeneity. Existing structural assertions on bucket-homogeneity (search `test-design-structure.sh` and any other `test-*.sh` that asserts bucket-homogeneity wording) must be updated in the same PR. Existing run-log artifacts retain their original naming (forward-only).

No external public APIs change. Operator-visible: dialectic runs may take longer when retries fire; resolutions for `voted` Dispositions now occasionally cite a retry output instead of an original one, but the schema is unchanged.

## Acceptance

- `skills/design/references/dialectic-debate.md` contains an `OUTPUT FORMAT` block as the first major content section in both thesis and antithesis templates, listing 6 tags (`<steelman>` + the existing 5) and a final `RECOMMEND:` line, followed by a `SELF-CHECK BEFORE STOPPING` directive.
- `skills/design/references/dialectic-execution.md` step 3 specifies per-side tool assignment (thesis vs antithesis use different externals by default; rotation alternates per decision N).
- `skills/design/references/dialectic-execution.md` contains a step 8b "Per-side waterfall retry" section that documents the Cursor↔Codex→Claude waterfall, parallel-across-sides execution, presence re-check before each retry wave, and corrective-prompt invocation.
- `skills/shared/dialectic-protocol.md` contains a "Per-side waterfall retry" section and the eligibility gate enumerates 6 tags including `<steelman>`.
- `skills/design/SKILL.md` NEVER #2 carries the Claude-as-2nd-retry exception clause; the bucket-homogeneity language is removed or replaced with per-side language.
- `scripts/render-debate-retry-prompt.sh` exists, is executable, accepts the documented CLI surface, and is covered by `scripts/test-render-debate-retry-prompt.sh`.
- `scripts/lib-timing-kinds.sh` `TIMING_TASK_KINDS_ALLOWED` contains the 6 new entries.
- `Makefile` registers `test-render-debate-retry-prompt` (and any new structural-contract test) under the appropriate aggregate targets.
- `make lint`, `make lint-bash32`, `bash scripts/relevant-checks.sh`, and all touched/new `test-*.sh` harnesses exit 0.
- No regression in `make lint` or in existing `scripts/test-design-*` harnesses.

diff_lines: 700

## Test plan
(no test plan section in plan-file)
