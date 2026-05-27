## Decision 1: Target artifact and human-facing surfaces
- **Question**: Which plan artifact does the new simplification step target?
- **Resolution**: BOTH the GitHub-published `larch:plan` body AND the in-chat plan display shown to humans. One canonical simplified plan flows to every human-facing surface. The reviewer panel (Step 3), Gate B/C, and `/implement` therefore also see the simplified plan, because they read the same `plan.txt` (chat displays) or the same `larch:plan` block (`/implement`).
- **Source**: user (Step 1c Q1)

## Decision 2: Style scope
- **Question**: What does "simplify" mean for this step?
- **Resolution**: Both Strunk & White prose discipline (concise, active voice, omit needless words) AND dyslexia-friendly accessibility scaffolding (short sentences <20 words, simpler vocabulary, more bullets/headings, no dense paragraphs).
- **Source**: user (Step 1c Q2)

## Decision 3: Activation
- **Question**: When should this new step run?
- **Resolution**: Always-on, new mandatory step in `/design`. No flag, no tier gate. Runs on every `/design` invocation.
- **Source**: user (Step 1c Q3)

## Decision 4: Failure mode
- **Question**: If the rewriter fails (LLM timeout, malformed output, suspicious content drift), how should `/design` respond?
- **Resolution**: Fall back to the original plan and append a `Warnings` entry to `execution-issues.md`. Simplification is a UX layer, never a correctness gate; `/design` MUST NOT block on rewriter failure.
- **Source**: user (Step 1d Q1)

## Decision 5: Precision contract
- **Question**: What is the rewriter allowed to drop or change?
- **Resolution**: Preserve every fact and code reference verbatim. File paths, function names, line numbers, flag names, command names, configuration keys, identifiers, and fenced code blocks stay byte-identical. Only prose between code references may be rewritten. This protects `/implement` (which reads the simplified plan via the `larch:plan` block) from precision loss.
- **Source**: user (Step 1d Q2)

## Decision 6: Scope discipline
- **Question**: Is the simplification step strictly scoped to the design plan, or does it also rewrite adjacent artifacts?
- **Resolution**: Plan + OOS issue bodies. Targets: (a) `plan.txt` and the derived `composed-plan.md` / `larch:plan` body, AND (b) the Description fields of accepted-OOS items before `/larch:issue` files them at Step 5b. Out of scope: reviewer feature-context (`feature-description.txt`), design-log publish bundle README, `/research` reports, the pre-plan-write issue body, dialectic prompts, sketch prompts, brainstorm prompts.
- **Source**: user (Step 1d Q3)

## Inferred hard constraints (NOT user-asked; load-bearing for the brainstorm panel)
- `plan-block-write.sh` contract must keep working: the simplified `composed-plan.md` must still parse as a valid `larch:plan` block (Plan + Acceptance + trailing `diff_lines: <N>` line).
- `redact-secrets.sh` is applied AFTER simplification (Step 5c sequence stays: compose → simplify → redact → write).
- The `## Files to modify/create` section's `### NEW:` / `### UPDATED:` / `### REWRITTEN:` subsection grammar must be preserved verbatim — `scout-plan-archetypes-wrapper.sh` and `check-plan-size.sh` parse this with a strict regex.
- The trailing `diff_lines: <N>` line must be preserved verbatim.
- Fenced code blocks (` ```bash ... ``` `, ` ```sh ... ``` `, ` ```python ... ``` `, etc.) must be byte-identical, especially because the plan-command validator (`validate-plan-commands.sh`) executes Tier 2/3 against fenced commands.
- Backticked code-reference tokens (file paths, flag names, function names) must be byte-identical.
- The simplification step must not introduce shell metacharacters or markdown that would break `plan-block-write.sh` (e.g., literal `<!-- larch:plan -->` markers).
- The step must remain idempotent: re-running `/design` on the same plan produces the same simplified output (within LLM nondeterminism), and the rewriter consuming an already-simplified plan must not degrade it further.
