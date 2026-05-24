## Goal
Insert semantic dedup-sweep instruction at three Gate B spots in skills/design/references/approval-gates.md so the design orchestrator sweeps and removes duplicate lines from plan.txt after applying voted-in suggestions.

## Implementation Plan
## Plan

### Summary

After the orchestrator revises `$DESIGN_TMPDIR/plan.txt` in Gate B (Apply all or Go through each), instruct it to perform a semantic duplicate-content sweep on the revised plan using its own LLM judgment (not deterministic pattern matching), remove any duplicate lines, and print a one-line breadcrumb reporting the number of duplicate lines removed. The sweep runs strictly **inside Gate B** (Step 3.5), after revision and before `ACTION=EMIT_PLAN`; it does **not** apply to Step 2b initial plan writes, Step 1e Gate A "Discuss more" sub-round plan revisions, or any other plan-emit path.

### Approach

Documentation-only instruction edit in `skills/design/references/approval-gates.md`. Both Gate B paths that call the Write tool to revise `plan.txt` (Apply all on line 86; Go through each on line 87 and the after-iteration revise on line 100) get an inline instruction inserted between "write the revised plan via the Write tool" and "then re-emit `ACTION=EMIT_PLAN`". The user explicitly chose **LLM reasoning over deterministic pattern matching** for the match rule — so no new script, regex, or sort/uniq pipeline is introduced.

### Files to modify

#### UPDATED: `skills/design/references/approval-gates.md`

Insert the dedup-sweep instruction at three spots inside the Gate B section:

1. **Apply all branch** (~line 86): after "write the revised plan via the Write tool (full file replacement, preserving `diff_lines: <N>`)" and before "then re-emit `ACTION=EMIT_PLAN`".
2. **Go through each — batch revise step** (~line 87): after "revise `plan.txt` to incorporate only the applied subset" and before "re-emit `ACTION=EMIT_PLAN`".
3. **One-by-one iteration completion** (~line 100): after "the orchestrator revises `plan.txt` per the applied set only" and before "writes the per-finding outcomes back ...".

Canonical inserted instruction wording (applied at all three spots, parameterized only by surrounding tense):

> Before re-emitting `ACTION=EMIT_PLAN`, perform a duplicate-content sweep on the freshly revised `plan.txt`: re-read the file, use your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once — not just byte-identical text). Preserve intentional repetition where the same content appears in distinct context sections (e.g., a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section. Rewrite `plan.txt` via the Write tool with duplicates removed. Then print exactly one breadcrumb of the shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (use `0` when none were found — the breadcrumb always fires so operators see the sweep ran). Only after the breadcrumb proceed to `ACTION=EMIT_PLAN`.

For the "One-by-one iteration completion" spot, the order is: revise plan.txt → dedup sweep → breadcrumb → write per-finding outcomes back to the artifact files.

### Edge cases

- **Zero duplicates** — breadcrumb still fires with `<N>` = `0` so operators always see the sweep ran.
- **Trivial repetition is not a duplicate** — blank lines, code-fence delimiters, lone bullet markers handled by agent judgment.
- **Lines whose wording is similar but meaning differs** — must NOT be removed; instruction emphasizes "semantically duplicate" (same meaning).
- **Distinct-context repetition** — preserved when the same content appears in distinct context sections (e.g., a constraint reinforced in both Approach and Edge cases).
- **`diff_lines: <N>` trailer** — preserved by the agent; the subsequent `ACTION=EMIT_PLAN` regenerates it. Accidental removal fails closed with `EMIT_PLAN_STATUS=missing-diff-lines`.
- **Single-finding apply set** — sweep still runs unconditionally; breadcrumb fires with `0`.
- **Zero-findings short-circuit** — no revision occurs, so sweep does NOT run.
- **Gate B(c) "Switch to discussion mode"** — no revision occurs, so sweep does NOT run.

### Failure modes

- **Over-removal of intentional repetition** — mitigated by the distinct-context carve-out in the instruction wording; visible to operators via the breadcrumb's `<N>` count.
- **Under-removal (misses true duplicates)** — least harmful; plan still works, slightly verbose. No mitigation needed.
- **Breadcrumb forgotten** — instruction emphasizes "the breadcrumb always fires"; relies on prose discipline (consistent with the rest of `approval-gates.md`).

### Testing strategy

Documentation-only change. No new tests added.

- Existing tests preserved: `scripts/test-design-structure.sh` (no new headings, only inline prose).
- Manual verification on the next `/design --simple` or `/design --hard` run that exercises Gate B's Apply path: confirm the breadcrumb appears in chat output and `<N>` is a non-negative integer.
- No lint impact: no fenced shell blocks, no foreground-required script calls, no new flags — `make lint`, `make lint-foreground-markers`, and `make lint-bash32` are unaffected.

## Acceptance

- `skills/design/references/approval-gates.md` contains the canonical dedup-sweep instruction text (or a byte-equivalent paraphrase that preserves the four contract points: re-read freshly revised `plan.txt`, semantic LLM judgment with distinct-context carve-out, rewrite via Write tool, breadcrumb of shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt`) at all three identified Gate B spots (Apply all branch ~line 86; Go through each batch revise ~line 87; one-by-one iteration completion ~line 100). The instruction must appear textually between the revise step and the `ACTION=EMIT_PLAN` re-emit step at each spot.
- The instruction text emphasizes **semantic LLM judgment** rather than deterministic pattern matching, regex, sort/uniq, or any new script.
- The instruction text includes the distinct-context-repetition carve-out: "Preserve intentional repetition where the same content appears in distinct context sections ... only remove duplicates that are truly redundant within or across the same section."
- The breadcrumb is specified to fire **unconditionally** after every Gate B revision, even when `<N>` is `0` — the instruction text reinforces "the breadcrumb always fires so operators see the sweep ran".
- The sweep is scoped **strictly to Gate B** — the instruction is NOT added to Step 2b initial plan writes, Step 1e Gate A discussion sub-round plan revisions, or any other `ACTION=EMIT_PLAN` caller.
- No script, validator, lint rule, harness, or `.tsv` registry is changed by this PR.
- `scripts/test-design-structure.sh` passes unchanged (no new Gate B headings; the inserted prose lives inside existing bullet paragraphs).
- `make lint` passes (no fenced shell blocks added → `make lint-foreground-markers` unaffected; no Bash 4 idioms introduced → `make lint-bash32` unaffected).

diff_lines: 25

## Test plan
(no test plan section in plan-file)
