## Goal
Refactor AGENTS.md below 11000 chars via empirical cross-agent validation (Branch A extraction or Branch B trim)

## Implementation Plan
## Plan


## Files to modify/create

**Always modified**:
- `AGENTS.md` — current size 11997 chars. Target ≤ 11000.

**Created conditionally (Branch A only — see Approach)**:
- `CONVENTIONS.md` (root, new) — extracted content from AGENTS.md's `## Conventions` section.

**Ephemeral (created in `$IMPLEMENT_TMPDIR` during Phase 1, not committed)**:
- `$IMPLEMENT_TMPDIR/include-test/<workspace>/AGENTS.md` — fixture A
- `$IMPLEMENT_TMPDIR/include-test/<workspace>/INCLUDED.md` — fixture B
- `$IMPLEMENT_TMPDIR/include-test/results.md` — per-agent transcripts (targeted + control prompts) + branch decision

## Approach

This refactor combines Approach 1 (extract `## Conventions` to a separate file) AND Approach 2 (trim duplicated prose) from the issue body, but extraction is **conditional on empirical cross-agent validation**. AGENTS.md is consumed natively by Claude (via `CLAUDE.md @AGENTS.md`), Codex (via repo-root sandbox per `scripts/launch-codex-implement.md`), Cursor (via repo-root workspace), and Gemini (via `GEMINI.md` containing `@./AGENTS.md`). Any include syntax inside AGENTS.md must work for all four agent runtimes that consume it as project instructions.

### Phase 1 — Empirical validation of cross-agent include semantics

Build sample fixtures in `$IMPLEMENT_TMPDIR/include-test/workspace/`:

- `AGENTS.md` (fixture A) — short file containing exactly one hypothesized include line plus a sentence: `The complete set of project conventions lives in INCLUDED.md (imported below).` followed by `@./INCLUDED.md`. (Use the same `@./` syntax that `GEMINI.md` uses today since that is the most likely-supported form.)
- `INCLUDED.md` (fixture B) — short file containing a unique fact: `Project alias is SCARLET-FOX-9412. This token appears only in INCLUDED.md.` and nothing else of interest.

Spawn three external subprocesses, each pointed at the fixture workspace. For each agent, issue **TWO prompts** in succession:

- **Targeted prompt**: `What is the project alias? Answer with the token only; do not read any additional files.`
- **Control prompt**: `List every distinct piece of factual content you have from your project instructions, one bullet per line. Do not read any additional files.`

Per-agent invocation:

- **Claude**: `claude -p --add-dir "$WS" "<prompt>"` (working dir `$WS`)
- **Codex**: `(cd "$WS" && codex exec --skip-git-repo-check "<prompt>")` — codex reads `AGENTS.md` from CWD by convention
- **Cursor**: `cursor-agent --print --mode ask --workspace "$WS" --trust "<prompt>"`

Each call has a per-call timeout (e.g., 300s); stdout/stderr captured to `results.md` with sections per agent and per prompt.

Decision rule (Branch A taken only when BOTH conditions hold for ALL THREE agents):

- **(a)** Targeted prompt returns `SCARLET-FOX-9412`.
- **(b)** Control prompt returns at least one bullet that surfaces content unique to `INCLUDED.md` — specifically the project-alias sentence or a clear paraphrase of it.

If any agent fails either condition → **Branch B (trim only)**. Do not attempt alternate syntaxes; the user's caveat is that the include must work without per-agent tricks. The control prompt is mandatory in the decision rule, not just a debugging aid — it guards against false positives from hallucination, prompt-completion, or session leakage.

The "do not read any additional files" clause in both prompts prevents the agent from helpfully reading INCLUDED.md as a follow-up tool action; we are testing **automatic** loading of the included file (which is what AGENTS.md needs to rely on), not the agent's ability to follow a prose pointer with a tool call.

### Phase 2A — Branch A (extraction works for all agents)

1. Create `CONVENTIONS.md` at repo root containing the `## Conventions` section content from AGENTS.md (currently ~5346 bytes — by far the largest section). Use a top-level `# Conventions` header and the existing bullet list verbatim — no semantic edits in this step.
2. In `AGENTS.md`, replace the entire `## Conventions` section (lines 48-60 in the current file) with a tiny two-line block:
   ```
   ## Conventions

   See `CONVENTIONS.md` (imported below).
   @./CONVENTIONS.md
   ```
3. If AGENTS.md is still > 11000 chars after step 2, apply trim-pass (see Phase 2B) to the remaining sections.

Note: no CLAUDE.md edit is needed. Phase 1 only takes Branch A when all three agents — including Claude — auto-load `INCLUDED.md` via `@./INCLUDED.md` inside the fixture AGENTS.md. The same mechanism resolves `@./CONVENTIONS.md` in the real AGENTS.md, so adding an additional `@./CONVENTIONS.md` import line to CLAUDE.md would be redundant.

### Phase 2B — Branch B (extraction does not work for some agent)

Pure trim-only pass on AGENTS.md. Target sections:

1. **The three oversized NEVER bullets** in `## Conventions` (current ~4100 chars total):
   - "Don't spawn a Monitor or a Bash `run_in_background` polling loop..." (line 56, ~1700 chars)
   - "NEVER improvise ScheduleWakeup outside skill-script direction" (line 59, ~1300 chars)
   - "NEVER write `$IMPLEMENT_TMPDIR/session-env.sh` from prompt-side..." (line 60, ~1100 chars)

   Each of these already cites a canonical SKILL.md location for its rationale (the "Why" / past incident). Trim each bullet to: rule statement + one-line "see <SKILL.md NEVER #N> for rationale" pointer. Expected savings: ~3000 chars.

2. **Canonical sources list trim** — drop redundant trailing descriptions for entries whose filename is already self-descriptive (e.g., `docs/installation-and-setup.md`, `docs/voting-process.md` need no further inline description). Expected savings: ~500 chars.

This is sufficient to bring AGENTS.md below 11000 chars even without extraction.

### Phase 3 — Validation (both branches)

1. `wc -c AGENTS.md` — must be ≤ 11000.
2. `bash scripts/relevant-checks.sh` — must pass (this exercises all relevant pre-commit hooks including agent-lint, markdownlint, lint-mermaid-fences, lint-literal-counts, etc.).
3. `make test-design-structure test-implement-structure` (and any other harness found by `grep -rln 'AGENTS\.md' scripts/test-*.sh`) — must pass.
4. **Branch A only**: spawn one Claude subprocess on the real (post-refactor) AGENTS.md and ask a sample Conventions question; confirm the answer reflects content that lives in CONVENTIONS.md after extraction.
5. Manual diff review: confirm no semantic content was dropped — only re-organized or de-duplicated.

## Edge cases

- **AGENTS.md still over 11000 chars after Branch A step 2** → apply Phase 2B trim to the residual sections.
- **Empirical test agent returns ambiguous answer** ("I don't have that token") → treat as a "did not auto-load" result; force Branch B. Do not retry with cleverer prompting — the contract is that auto-load works without orchestration.
- **Control prompt returns the token but no paraphrase of the project-alias sentence** (agent returned token via hallucination) → condition (b) fails → Branch B.
- **Structure tests grep AGENTS.md for specific section headers** → before extracting, `grep -rln 'AGENTS\.md\|## Conventions' scripts/ .github/ agent-lint.toml`. If anchors would break, either keep those exact headers in AGENTS.md or update the matching test (the latter is OUT of scope for this trivial refactor — prefer keeping headers).
- **`GEMINI.md` references `@./AGENTS.md`** — extraction doesn't touch AGENTS.md's filename or top-level structure, so this remains valid.
- **An agent CLI requires a workspace flag in a different form** (e.g., Codex doesn't auto-discover AGENTS.md from CWD) → adjust the per-agent invocation in Phase 1 only after consulting that CLI's `--help`; do not give up on the agent silently.

## Failure modes

1. **Phase 1 control prompt itself fails to elicit factual enumeration** — an agent might respond with a generic refusal or a paraphrase that doesn't list INCLUDED.md content distinctly, even if it DID auto-load the file. Earliest signal: the targeted prompt returns the token but the control prompt returns only AGENTS.md content. Mitigation: log the full transcript to `results.md` and have the implementer scan for any reference to "SCARLET-FOX" or "project alias" in the control output, not just a bullet match. Use a tolerant string search rather than strict bullet-format matching.

2. **Anchor break in CI / structure tests** — `scripts/test-*-structure.sh`, `agent-lint.toml`, or a hooks/workflow file may grep for a section name now extracted out. Earliest signal: `bash scripts/relevant-checks.sh` fails on a structure test or agent-lint. Mitigation: do the pre-check grep before extraction (listed in Edge cases) and preserve any matched anchor in AGENTS.md (e.g., keep the `## Conventions` header in AGENTS.md with the import line directly below it — exactly the Branch A step 2 form above). If a deeper anchor (e.g., a specific bullet) is grepped, escalate to OOS and don't extract that bullet.

3. **Cross-agent ABI drift after the empirical test settles** — Phase 1 finds the include works today, but a future Codex/Cursor release changes behavior. This is a latent risk that this refactor cannot fully prevent. Mitigation: include a one-line note in CONVENTIONS.md (or a short comment in AGENTS.md) indicating that the import is auto-load-dependent and that if any future agent fails to surface CONVENTIONS.md content, the refactor should be reversed to in-line form. The empirical test fixtures are ephemeral (lost after Phase 1), so the validation is a point-in-time snapshot rather than a continuous guard.

## Testing strategy

- **Pre-refactor baseline**: capture `wc -c AGENTS.md` (= 11997 today), `bash scripts/relevant-checks.sh` exit code (= 0 today).
- **Phase 1 evidence**: `$IMPLEMENT_TMPDIR/include-test/results.md` captures per-agent stdout/stderr for both targeted and control prompts, and the chosen branch decision in a header line (`BRANCH=A` or `BRANCH=B`).
- **Phase 2 incremental check**: after each edit, `wc -c AGENTS.md` to track progress toward ≤ 11000.
- **Phase 3 final**: `bash scripts/relevant-checks.sh` exit 0; `make test-design-structure` exit 0; `make test-implement-structure` exit 0. For Branch A only, a single Claude subprocess sanity check confirming Conventions content is reachable through the refactored AGENTS.md.
- No new test files are added by this refactor — it relies on existing harnesses.



## Acceptance

- `wc -c AGENTS.md` returns a value ≤ 11000 after the refactor.
- `bash scripts/relevant-checks.sh` exits 0 on the refactored tree.
- `make test-design-structure` and `make test-implement-structure` (plus any other harness that greps `AGENTS.md`) exit 0.
- AGENTS.md content semantics are preserved — no factual changes to existing guidance, only re-organization and (Branch B) de-duplication.
- Phase 1 empirical test results recorded in `$IMPLEMENT_TMPDIR/include-test/results.md` with a `BRANCH=A` or `BRANCH=B` header line and per-agent transcripts for both targeted and control prompts.
- If Branch A taken: `CONVENTIONS.md` exists at repo root; AGENTS.md's `## Conventions` section retains its header plus an `@./CONVENTIONS.md` import line and a one-line prose pointer. No CLAUDE.md edit.
- If Branch B taken: AGENTS.md trimmed to ≤ 11000 chars via the three oversized NEVER bullets and Canonical sources list trim, with semantic content preserved by reference to the SKILL.md anchors each bullet already cites.

diff_lines: 150

## Test plan
(no test plan section in plan-file)
