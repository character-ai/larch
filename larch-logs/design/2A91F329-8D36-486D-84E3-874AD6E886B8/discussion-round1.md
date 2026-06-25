## Decision 1: Target surface
- **Question**: Which SKILL.md surface(s) does this relocation cover?
- **Resolution**: Both `skills/implement/SKILL.md` and `skills/design/SKILL.md`. `/implement` is the primary lever; `/design` Steps 5/5b/5c bodies are also in scope.
- **Source**: user

## Decision 2: Relocation strategy (turn-cost rule)
- **Question**: How aggressive should body relocation be given a new on-entry Read costs one turn?
- **Resolution**: Two clean targets only. (a) Fold body into steps that ALREADY do a MANDATORY READ on entry (zero new turns). (b) Relocate the latest steps (e.g. `/implement` Step 18, Step 8+) into new on-entry references (one new turn there; body absent for most of the run). Do not blanket-relocate mid-run steps that lack an existing on-entry Read.
- **Source**: user

## Decision 3: Sequencing dependency
- **Question**: Must this land after #5273 and #5276?
- **Resolution**: Both #5273 and #5276 are CLOSED `[DONE]`. The sequencing constraint is satisfied; work may proceed now.
- **Source**: codebase (gh issue view)

## Decision 4: KEEP-safe invariants (must not change)
- **Question**: What must stay inline so step-sequence awareness is preserved?
- **Resolution**: The step skeleton (`<!-- step:N -->` markers and headers), step-to-step transitions, and the anti-halt "Critical boundary" / "Continue to Step N IMMEDIATELY" callouts stay inline. Only late/large step BODY detail moves to references.
- **Source**: issue body (KEEP-safe)

## Decision 5: Hard constraints discovered (must not break)
- **Question**: What CI / lint / test invariants gate this change?
- **Resolution**:
  - `scripts/test-implement-fence-shape.sh` pins `EXPECTED_OLD`/`EXPECTED_NEW` bash-fence counts in `/implement` SKILL.md. Relocating any step body that contains a ```bash fence shifts the count and requires updating that test (run `make test-implement-fence-shape`). Listed as `### UPDATED:` when fences move.
  - `.claude/rules/skill-editing-trace.md` governs SKILL.md edits and names the fence harness explicitly.
  - agent-lint S030 pins certain literal script paths inside SKILL.md; those pinned literal paths must be retained inline (do not relocate the S030-pinned path tokens).
  - New/changed reference `.md` files must satisfy markdownlint (MD038 no inner-whitespace code spans, MD001 heading increments) and `make lint` / `make py-lint` / `make py-test`.
- **Source**: codebase (test-implement-fence-shape.sh, .claude/rules/, readability-style.md)

## Decision 6: Behavior preservation (non-goal: behavior change)
- **Question**: May step behavior or sequencing change?
- **Resolution**: No. This is a token-cost / readability relocation only. The orchestrator must reach and execute the same steps in the same order with the same wrapper calls. Relocation is byte-faithful where it preserves contract tokens; only prose location changes.
- **Source**: issue body
