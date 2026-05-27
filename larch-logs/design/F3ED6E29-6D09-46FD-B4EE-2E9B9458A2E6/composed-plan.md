## Plan

Augment every `/design` prompt that produces user-facing text so the text is born in three styles at once: Strunk & White, dyslexia-friendly, and brief. One shared preamble file is the only source of truth. A pre-commit lint asserts every amendment site references that preamble. Each external-agent prompt path has an explicit `<READABILITY_STYLE>` expansion contract. No new pipeline step. No post-hoc rewriter.

## Files to modify/create

### NEW: `skills/design/references/readability-style.md`

Holds the canonical style preamble.

- Names the three style axes: Strunk & White (active voice, omit needless words), dyslexia-friendly (short sentences, simpler vocabulary, more bullets/headings), and brevity (shorter is better — overall artifact length minimized).
- Defines the precision-contract carve-outs: fenced code blocks, backticked tokens, file paths, identifiers, flag names, the `### NEW|UPDATED|REWRITTEN:` plan grammar, and the trailing `diff_lines: <N>` line stay byte-stable.
- Names the precedence order when axes conflict: **code references > meaning > brevity > dyslexia-friendly chunking > Strunk & White micro-rewrites**.
- Declares the literal substitution token `<READABILITY_STYLE>` that external-agent prompt files MUST embed.
- Adds 3–5 short before/after examples so agents see what compliant output looks like.
- Target size: 60–80 lines. Self-applies the same style.

### NEW: `scripts/lint-readability-preamble.sh`

Pre-commit lint script that asserts every amendment site references the preamble.

- Reads a hard-coded amendment-site manifest as an array of `path:variant` rows where `variant` is one of `external-prompt` or `orchestrator-inline`.
- The manifest is the **explicit allowlist** of real amendment sites only. It explicitly excludes the preamble file `skills/design/references/readability-style.md`, the lint script `scripts/lint-readability-preamble.sh`, its sibling `scripts/lint-readability-preamble.md`, and the test harness `scripts/test-lint-readability-preamble.sh` so the lint cannot false-pass by matching its own contract prose.
- For each manifest row, applies the anchored-line check matching the row's `variant`:
  - `external-prompt`: a line matching the anchored pattern `^Style requirements: \`<READABILITY_STYLE>\`\.$` must exist in the file.
  - `orchestrator-inline`: a line-start anchored pattern matching `^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: \`skills/design/references/readability-style\.md\`\.\*\*$` must exist in the file (the directive text after "before" is free-form, the trailing path token and surrounding bold markers are anchored).
- Exits 0 when every manifest row is satisfied. Exits non-zero with one offending row per stderr line on failure: `<path>: missing <variant> readability-style directive`.
- Bash 3.2 portable per `BASH_AUTHORING.md` §3.
- Sibling `scripts/lint-readability-preamble.md` documents the contract, the two anchored line patterns, and the manifest grammar.

### NEW: `scripts/test-lint-readability-preamble.sh`

Offline regression harness for the lint.

- Builds three fixture directories under `mktemp -d`: one fully compliant (token present in external-prompt fixture file; MANDATORY directive present in orchestrator-inline fixture file); one **external-prompt non-compliant** (external-prompt fixture missing the `<READABILITY_STYLE>` line, orchestrator-inline file still compliant); one **orchestrator-inline non-compliant** (orchestrator-inline fixture missing the MANDATORY directive, external-prompt file still compliant).
- Invokes the lint against each fixture; asserts exit 0 on the compliant fixture; asserts non-zero exit on each non-compliant fixture and verifies the offending path is named in the lint's stderr (`<path>: missing <variant> readability-style directive`).
- Wired into the Makefile via the new target and assigned to a `test-harnesses-N` shard (see Makefile section below).

### NEW: `scripts/lint-readability-preamble.md`

Sibling-contract documentation for the lint per `.claude/rules/script-md-siblings.md`.

- Documents the two anchored line patterns and the manifest grammar.
- Notes the explicit exclusion of the preamble file, the lint scripts, and the test harness from the manifest.
- Cross-links to `skills/design/references/readability-style.md`.

### UPDATED: `.pre-commit-config.yaml`

Adds a local hook so the lint runs on every commit, not only via `make lint`.

- New `repos:` entry with `repo: local`, `hooks:` containing `id: lint-readability-preamble`, `name: lint readability preamble references`, `entry: bash scripts/lint-readability-preamble.sh`, `language: system`, `pass_filenames: false`, `always_run: true`.
- This is the FINDING_3 fix: normal enforcement paths (pre-commit, `scripts/relevant-checks.sh`, `make lint-only`) now invoke the lint without depending on the umbrella `make lint` target.

### UPDATED: `skills/design/SKILL.md`

Adds MANDATORY read directives at the remaining orchestrator-inline writing sites in this file (the Step 1d.5 synthesis amendment moves to `references/brainstorm.md` per FINDING_5).

- Step 1d.7 outline body — already lives in `references/design-outline.md`; SKILL.md just routes there. No SKILL.md edit needed for 1d.7.
- Step 2b plan-drafting prose — insert MANDATORY directive just before the `## Files to modify/create` schema notes.
- Step 3b architecture-diagram prose — insert directive just before the mermaid generation instructions (covers any prose around the diagram).
- Step 4 rejected-findings printout prose — insert directive just before the `## Unimplemented Plan Review Suggestions` header instruction.
- Step 5c `composed-plan.md` composition prose — insert directive just before item 1 "Compose `composed-plan.md`".
- Add a one-line cross-link in the Anti-patterns section noting the style preamble as the single source of style truth.

Each directive is the exact anchored form: `**MANDATORY — READ ENTIRE FILE before <composition step name>: \`skills/design/references/readability-style.md\`.**`

### UPDATED: `skills/design/references/design-outline.md`

Adds the MANDATORY read directive at the orchestrator-inline outline composition site.

- Insert before the `## Outline schema` section the exact anchored line: `**MANDATORY — READ ENTIRE FILE before composing the outline: \`skills/design/references/readability-style.md\`.**`

### UPDATED: `skills/design/references/brainstorm.md`

Adds the MANDATORY read directive for the in-session brainstorm synthesis (FINDING_5 — moved from SKILL.md). Also adds the assembly-side expansion contract for the three brainstorm slot prompts (FINDING_2, FINDING_6).

- Insert the MANDATORY directive immediately before `## Synthesis → brainstorm.md`: `**MANDATORY — READ ENTIRE FILE before composing the synthesis and any free-form discussion-loop response: \`skills/design/references/readability-style.md\`.**`
- Add an assembly-side expansion section (anchor heading "Style preamble expansion") that instructs the orchestrator: "Before launching each external slot (Cursor framing, Codex scope) and before composing the always-Claude pragmatic slot, read `skills/design/references/readability-style.md` once and substitute every literal `<READABILITY_STYLE>` token in the assembled prompt with the full preamble contents. The pragmatic slot is parent-session but receives the same substitution so all three slots see identical style guidance."
- File is added to the lint manifest as an `orchestrator-inline` site.

### UPDATED: `skills/design/references/brainstorm-prompts.md`

Embeds the `<READABILITY_STYLE>` substitution token in each of the three slot prompt bodies.

- `<BRAINSTORM_FRAMING_PROMPT>` gains a final anchored line: `Style requirements: \`<READABILITY_STYLE>\`.`
- `<BRAINSTORM_SCOPE_PROMPT>` gains the same anchored line.
- `<BRAINSTORM_PRAGMATIC_PROMPT>` gains the same anchored line (uniform handling per FINDING_6; expansion happens at assembly per the `brainstorm.md` update above).
- Updates `skills/design/scripts/test-brainstorm-prompts.sh` to add three assertions, one per slot, that the exact anchored line is present.

### UPDATED: `skills/design/references/sketch-prompts.md`

Embeds `<READABILITY_STYLE>` in the four real personality sketch prompts (FINDING_11 drops `GENERIC_PROMPT`).

- `ARCH_PROMPT`, `EDGE_PROMPT`, `INNOVATION_PROMPT`, and `PRAGMATIC_PROMPT` each gain a final anchored line: `Style requirements: \`<READABILITY_STYLE>\`.`
- `GENERIC_PROMPT` is **not** amended. It is the SIMPLE-quick path's prompt; SIMPLE tier already skips sketches entirely under the no-sketch carve-out, and amending an unused prompt would be scope creep beyond the minimum-change lane.

### UPDATED: `skills/design/references/sketch-launch.md`

Adds the assembly-side `<READABILITY_STYLE>` expansion contract for sketch prompts (FINDING_2). HARD-tier only.

- Insert in the per-slot prompt assembly description: "Before launching, read `skills/design/references/readability-style.md` once and substitute every literal `<READABILITY_STYLE>` token in the assembled prompt body with the full preamble contents."
- File is added to the lint manifest as an `orchestrator-inline` site (covers the orchestrator-inline expansion directive).

### UPDATED: `skills/design/references/dialectic-debate.md`

Embeds `<READABILITY_STYLE>` in the Thesis and Antithesis template bodies (HARD-tier).

- Each template body gains a final anchored line `Style requirements: \`<READABILITY_STYLE>\`.` before its closing reference-block wrapper.

### UPDATED: `skills/design/references/dialectic-execution.md`

Adds the assembly-side `<READABILITY_STYLE>` expansion contract for dialectic prompts (FINDING_2). HARD-tier only.

- Insert in the per-decision prompt rendering step (step 2 in that file): "Before launching each debater, read `skills/design/references/readability-style.md` once and substitute every literal `<READABILITY_STYLE>` token in the rendered prompt body with the full preamble contents."
- File is added to the lint manifest as an `orchestrator-inline` site.

### UPDATED: `skills/design/references/plan-review.md`

Embeds the `<READABILITY_STYLE>` token in the reviewer prompt body and the OOS-Description guidance.

- Reviewer prompt body gains a final anchored line `Style requirements for finding text and OOS Descriptions: \`<READABILITY_STYLE>\`.`
- Existing reviewer-finding schema and OOS schema are untouched; only the prose-style instruction changes.
- This is the **documentation** surface; the **runtime** prompt emitter is amended below in `render-plan-review-prompt.sh` (FINDING_1).

### UPDATED: `skills/design/scripts/render-plan-review-prompt.sh`

Adds runtime substitution so emitted plan-review prompts carry the expanded readability preamble (FINDING_1).

- Read `skills/design/references/readability-style.md` once at script start.
- Substitute every occurrence of the literal token `<READABILITY_STYLE>` in the rendered prompt body with the full preamble contents before writing the final prompt file.
- The substitution runs after all existing token substitutions (plan text, feature context, focus area, etc.) and before the heredoc closes.
- If the preamble file is missing or empty, fall back to emitting the prompt without substitution and write a single warning line to stderr (consistent with Round-1 fail-quiet posture: denser-text-is-still-correct-text).

### UPDATED: `skills/design/scripts/test-plan-review-prompt.sh`

Pins the FINDING_1 runtime substitution.

- Assert that the rendered prompt contains a meaningful excerpt of the preamble content (e.g., the literal string `Strunk & White` and the literal string `code references > meaning > brevity`).
- Assert that the rendered prompt contains **no** literal `<READABILITY_STYLE>` token (proving substitution actually happened).
- The harness uses an isolated fixture preamble file plus a fixture prompt template, not the real preamble, so the harness stays hermetic.

### UPDATED: `skills/design/references/approval-gates.md`

Adds the MANDATORY read directive covering Gate A, Gate B, and Gate C operator-facing prose (FINDING_4).

- Insert a single file-level MANDATORY directive near the top of the file, immediately after the `# Approval Gates Reference` header: `**MANDATORY — READ ENTIRE FILE before composing Gate A discussion prose, Gate B findings presentation and apply-all rewrite, or Gate C approval prose: \`skills/design/references/readability-style.md\`.**`
- A single file-level directive covers all three gate sections; the lint checks for that exact line.
- File is added to the lint manifest as an `orchestrator-inline` site.

### UPDATED: `skills/design/references/discussion-rounds.md`

Adds the MANDATORY read directive at the top of each round body (Step 1c, Step 1d, post-plan Round 2 sub-round).

- Insert a single file-level MANDATORY directive near the top of the file, immediately after the `# Discussion Rounds Reference` header: `**MANDATORY — READ ENTIRE FILE before composing Step 1c clarifying questions, Step 1d discussion-round writes, or the post-plan Round 2 sub-round body: \`skills/design/references/readability-style.md\`.**`
- File is added to the lint manifest as an `orchestrator-inline` site.

### UPDATED: `Makefile`

Wires the new lint and its harness into the existing `lint` umbrella and assigns the harness to a test-harnesses shard.

- New `.PHONY` entries for `lint-readability-preamble` and `test-lint-readability-preamble`.
- New target `lint-readability-preamble` invoking `bash scripts/lint-readability-preamble.sh`.
- New target `test-lint-readability-preamble` invoking `bash scripts/test-lint-readability-preamble.sh`.
- Add `lint-readability-preamble` as a dependency of the master `lint` target.
- Assign `test-lint-readability-preamble` to **one** existing `test-harnesses-N` shard (place it in `test-harnesses-5` alongside the other `test-` design lints, or whichever shard the implementer's `make harness-shards-coverage` audit indicates is least full). Do **not** add it as a direct dependency of `lint` — the test-harnesses shards already roll up under `make lint`.

## Approach

Single canonical preamble file. Every prompt that generates user-facing text either includes the substitution token `<READABILITY_STYLE>` (external-agent prompts that get rendered to files) or carries a MANDATORY directive to read `readability-style.md` (orchestrator-inline composition sites). Two patterns:

- **Pattern A — external prompts** (`brainstorm-prompts.md`, `sketch-prompts.md`, `dialectic-debate.md`, `plan-review.md`): each prompt body embeds the literal token `<READABILITY_STYLE>`. Expansion is contracted at the assembly point (`brainstorm.md`, `sketch-launch.md`, `dialectic-execution.md`) or in the rendering script (`render-plan-review-prompt.sh`). The orchestrator or the script reads `readability-style.md` once and substitutes the token before launching the agent.
- **Pattern B — orchestrator-inline writing** (`SKILL.md` step bodies, `design-outline.md`, `approval-gates.md`, `discussion-rounds.md`, `brainstorm.md` synthesis): each amendment site carries a MANDATORY READ directive. The orchestrator reads `readability-style.md` before composing the user-facing text.

The lint enforces the contract per-site using an anchored-line regex per variant. The manifest is an explicit allowlist of real amendment sites — the preamble file, lint scripts, and test harness are excluded so the lint cannot false-pass against its own contract prose.

The preamble's precedence rule resolves the apparent tension between dyslexia-friendly chunking (may add bytes) and brevity (fewer bytes). Order: code references > meaning > brevity > dyslexia-friendly chunking > Strunk & White micro-rewrites.

No new step in the pipeline. No `ACTION` in `design-driver.sh`. No helper that mutates `plan.txt`. No runtime validator on output. No fall-back logic, because the failure mode of "agent ignored style" still produces correct text — just denser.

## Edge cases

- A new prompt file added in the future without preamble reference triggers the lint via the manifest. The manifest is the contract; new prompt sites must opt in.
- An agent prompt rendered via a helper script (e.g., `render-plan-review-prompt.sh`) does the read+substitute inside the script (FINDING_1). Other assembly paths put the read+substitute in the assembly reference doc (`brainstorm.md`, `sketch-launch.md`, `dialectic-execution.md`) and rely on the orchestrator to honor the directive.
- The `<BRAINSTORM_PRAGMATIC_PROMPT>` is a parent-session prompt rather than an external one, but it carries the same token and the same substitution contract per FINDING_6 — uniform handling.
- Re-running `/design` on the same issue re-applies the same amended prompts and produces the same readable output (within LLM nondeterminism). No "already-simplified" footgun.
- `GENERIC_PROMPT` in `sketch-prompts.md` is intentionally NOT amended (FINDING_11). It is the SIMPLE-quick path's generic prompt and the SIMPLE tier already skips sketches under the no-sketch carve-out; amending an unused prompt would exceed the minimum-change lane.

## Failure modes

1. **Agent ignores style guidance.** Output is denser than target but still correct. No automated detector; mitigation is reader complaint. Acceptable for v1 per Round-1 fail-quiet posture.
2. **Preamble drifts from amendment sites.** A contributor edits one prompt's style guidance inline instead of updating the central preamble. The lint catches removal of the anchored line / directive but not silent additions. Mitigation: code review + the lint's explicit manifest.
3. **Runtime substitution misses a path.** A new external-agent prompt path is added later without amending its assembly site to substitute `<READABILITY_STYLE>` — agents receive a literal token. Mitigation: the lint's manifest requires every prompt-rendering surface to be registered as an `orchestrator-inline` site documenting the substitution contract; the `test-plan-review-prompt.sh` pattern (assert rendered prompt contains no literal token) should be replicated for any future renderer-style prompt path. For brainstorm/sketch/dialectic assembly (orchestrator-inline), the orchestrator is trusted to follow the directive; no runtime guard.

## Testing strategy

- `scripts/test-lint-readability-preamble.sh` covers the lint with one compliant + two variant-specific non-compliant fixtures (FINDING_10). Each non-compliant case asserts both the exit code and the offending path in stderr.
- `make lint` runs the new `lint-readability-preamble` target via the existing umbrella.
- `pre-commit run --all-files` runs the lint via the new `.pre-commit-config.yaml` entry (FINDING_3).
- `scripts/test-plan-review-prompt.sh` is extended to assert the rendered prompt contains preamble content and no literal `<READABILITY_STYLE>` token (FINDING_1).
- `scripts/test-brainstorm-prompts.sh` is extended to assert each brainstorm slot body contains the exact anchored `Style requirements: \`<READABILITY_STYLE>\`.` line.
- Existing `scripts/test-design-structure.sh` continues to pass because step boundaries, sentinels, and file outputs are unchanged.
- Manual smoke: invoke `/design --simple <small issue>` post-merge and confirm `plan.txt`, `brainstorm.md`, `design-outline.md`, and `composed-plan.md` exhibit shorter sentences, more bullets, simpler vocabulary than baseline runs in `larch-logs/design/`.

## Acceptance

The change is complete when all of the following hold simultaneously on the implementation PR:

1. `skills/design/references/readability-style.md` exists, is non-empty, names all three style axes (Strunk & White, dyslexia-friendly, brevity), names the precedence ordering `code references > meaning > brevity > dyslexia-friendly chunking > Strunk & White micro-rewrites`, and declares the literal `<READABILITY_STYLE>` substitution token.
2. `scripts/lint-readability-preamble.sh` exists, is executable, is Bash 3.2 portable, and carries a sibling `scripts/lint-readability-preamble.md` contract doc.
3. The lint manifest inside `scripts/lint-readability-preamble.sh` is an explicit allowlist of real amendment sites. It does NOT list `skills/design/references/readability-style.md`, `scripts/lint-readability-preamble.sh`, `scripts/lint-readability-preamble.md`, or `scripts/test-lint-readability-preamble.sh`.
4. Every amendment site listed in the manifest passes its variant's anchored line check on the implementation PR:
   - `external-prompt` sites contain a line exactly matching `^Style requirements: \`<READABILITY_STYLE>\`\.$` (or the plan-review variant `^Style requirements for finding text and OOS Descriptions: \`<READABILITY_STYLE>\`\.$`).
   - `orchestrator-inline` sites contain a line exactly matching `^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: \`skills/design/references/readability-style\.md\`\.\*\*$`.
5. `bash scripts/lint-readability-preamble.sh` exits 0 on a clean checkout of the implementation PR.
6. `bash scripts/test-lint-readability-preamble.sh` exits 0 and covers three fixtures: one compliant, one external-prompt-non-compliant, one orchestrator-inline-non-compliant. The harness asserts the offending path in stderr for each non-compliant case.
7. `.pre-commit-config.yaml` contains a local hook with `id: lint-readability-preamble`, `entry: bash scripts/lint-readability-preamble.sh`, `language: system`, `pass_filenames: false`, `always_run: true`.
8. `make lint-readability-preamble` and `make test-lint-readability-preamble` exist as targets; `make lint` includes `lint-readability-preamble` in its dependencies; `test-lint-readability-preamble` is assigned to one `test-harnesses-N` shard and not directly to the `lint` target.
9. `skills/design/scripts/render-plan-review-prompt.sh` reads `readability-style.md` and substitutes every `<READABILITY_STYLE>` token in its rendered prompt; the rendered prompt contains no literal token.
10. `bash scripts/test-plan-review-prompt.sh` asserts the rendered prompt contains preamble content (`Strunk & White` and `code references > meaning > brevity`) and no literal `<READABILITY_STYLE>` token. `bash scripts/test-brainstorm-prompts.sh` asserts each of the three brainstorm slot bodies contains the exact `Style requirements: \`<READABILITY_STYLE>\`.` line.
11. `GENERIC_PROMPT` in `skills/design/references/sketch-prompts.md` is NOT amended (FINDING_11).
12. All pre-existing test harnesses continue to pass: `make lint`, `pre-commit run --all-files`, and each `test-harnesses-N` shard.

diff_lines: 420
