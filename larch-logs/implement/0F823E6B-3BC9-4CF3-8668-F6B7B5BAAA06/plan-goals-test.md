## Goal
Unify OOS voter-prompt builders into a shared helper and add explicit problem-vs-solution judging clause

## Implementation Plan
## Plan

Unify the two hand-written voter-prompt builders (`scripts/dispatch-plan-voters.sh::make_prompt_file()` and `scripts/dispatch-code-voters.sh::make_voter_prompt_file()`) into a single shared helper that emits the full voter-prompt body to stdout, parameterized by skill-specific deltas. Add an explicit, emphatic OOS problem-vs-solution clause. Backport the canonical OOS clause text to `skills/shared/voting-protocol.md` and inline it into the `main-agent-vote-required` (MAV) prose in `skills/design/SKILL.md`, `skills/implement/SKILL.md`, and the /design Voter 1 instruction in `skills/design/references/plan-review.md`. Add a documentation note in `skills/review/SKILL.md` explaining /review's MAV adjudication delegation.

### NEW files

1. `skills/shared/scripts/render-voter-prompt.sh` (~170 LOC) — canonical voter-prompt renderer. Bash 3.2-compatible, `set -euo pipefail`. **Does NOT call `larch_quiet_init`** (stdout IS the payload; lib-quiet's stdout redirection would silently empty the rendered prompt). Leading comment block documents this divergence. **Must land with executable mode** (`chmod +x`). Required flags:
   - `--ballot-file PATH`
   - `--panel-role STRING` (free-form; callers pass hardcoded trusted strings)
   - `--id-grammar finding-oos|finding-only` — controls both the OOS_N example block AND the wording of the OOS-specific clause (grammar-conditional).
   - `--verification-context plan|diff-plan` — `plan` preserves the existing "may silently inspect the plan or referenced repo files" allowance.

   Output (stdout) structure, byte-preserved from current dispatcher prose where possible:

   Common body (always emitted):
   ```
   You are a {PANEL_ROLE}.
   Vote EXONERATE rather than YES when the concern is legitimate but the proposed change introduces more complexity than it warrants.
   Do NOT vote NO solely because you dislike or distrust the proposed fix — fix proposals are informational; the coder decides the exact change. Vote NO only when the stated problem is not real or not worth raising.
   ```

   Then the grammar-conditional OOS clause:
   - `finding-only`: `For items prefixed with ``[OUT_OF_SCOPE]``: vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy.`
   - `finding-oos`: `For ``OOS_N:`` items in plan review (or items prefixed with ``[OUT_OF_SCOPE]`` in code review): vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy.`

   Then:
   ```
   Do NOT modify files. Do NOT commit. Do NOT push.

   Read the ballot from this path: {BALLOT_FILE}
   ```

   Then verification-context branch:
   - `plan` (/design): `**Verify silently** — do not produce narrative output, reasoning explanations, or status updates before, between, or after the vote lines. You may read the ballot file and silently inspect the plan or referenced repo files for verification, but do not invoke planning/status tools.`
   - `diff-plan` (/review): `Use the ballot path and any provided diff/plan context files to verify the ballot claims before voting.\n**Verify silently** — do not produce narrative output, reasoning explanations, or status updates before, between, or after the vote lines. You may read the ballot file and any provided diff/plan context files for verification, but do not invoke planning/status tools or any other tools beyond those file reads.`

   Then vote-line schema (`FINDING_N: YES|NO -- reason|EXONERATE -- reason`), appended with `OOS_N:` example block for `finding-oos` only, then the "Output ONLY vote lines" closer.

   Exit codes: `0` on success; `2` on argument error.

2. `skills/shared/scripts/render-voter-prompt.md` (~100 LOC) — sibling doc per `.claude/rules/script-md-siblings.md`. Sections: Purpose, Primary callers, Flags, Output contract, **lib-quiet divergence** (explicit "does NOT call larch_quiet_init"), **executable mode invariant**, Harness, **Edit-in-sync rules**: canonical OOS clause appears in **five logical locations** (two helper grammar variants + four doc/SKILL.md verbatim copies); edits must propagate. The drift-guard mechanically verifies copies 2-5 against a hard-coded canonical string.

3. `scripts/test-render-voter-prompt.sh` (~200 LOC) — six cases:
   - `case_finding_only` — assert finding-only OOS clause variant, NO OOS_N substring, FINDING_N example present, diff-plan verification sentence present.
   - `case_finding_oos` — assert OOS_N example present, finding-oos OOS clause variant, plan-context verification sentence including the "may silently inspect the plan or referenced repo files" allowance.
   - `case_canonical_text_drift_guard` — hard-coded canonical-body string greps **four** doc/SKILL.md locations: `voting-protocol.md`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/design/references/plan-review.md`.
   - `case_executable_bit` — asserts `[ -x render-voter-prompt.sh ]`.
   - `case_lib_quiet_isolation` — invokes with `LARCH_QUIET_ACTIVE=1`; asserts rendered prompt is non-empty.
   - `case_argument_validation` — exit code 2 on missing/invalid flags.

4. `scripts/test-render-voter-prompt.md` (~50 LOC) — sibling doc; documents all six cases, the 4-location drift-guard contract, lib-quiet and executable-bit invariants.

### MODIFIED files

5. `scripts/dispatch-plan-voters.sh` — `make_prompt_file()` body (lines 42-63) replaced with helper call: `--id-grammar finding-oos --verification-context plan --panel-role "senior engineer on a voting panel deciding which proposed plan modifications should be accepted"`. `make_plan_voter_retry_prompt_file()` unchanged.

6. `scripts/dispatch-code-voters.sh` — `make_voter_prompt_file()` body (lines 51-72) replaced with helper call: `--id-grammar finding-only --verification-context diff-plan --panel-role "scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted"`. `make_voter_retry_prompt_file()` unchanged.

7. `scripts/test-dispatch-plan-voters.sh` — TWO changes: (a) `PLUGIN_ROOT_STUB` augmentation around lines 71-76 to copy/symlink `skills/shared/scripts/render-voter-prompt.sh` (with executable bit preserved) into the stub root, since dispatchers now resolve the helper from `$PLUGIN_ROOT`. (b) Composed-prompt assertion that the dispatcher-generated prompt contains the canonical OOS clause (finding-oos variant), the general fix-informational rule, and both FINDING_N + OOS_N example lines.

8. `scripts/test-dispatch-code-voters.sh` — parallel changes: (a) `PLUGIN_ROOT_STUB` augmentation. (b) Composed-prompt assertion: canonical OOS clause (finding-only variant), general fix-informational rule, FINDING_N example present, **NO `OOS_N` substring anywhere** (confirms grammar-conditional clause is applied).

9. `scripts/dispatch-plan-voters.md` — document that prompt rendering is delegated to the shared helper.

10. `scripts/dispatch-code-voters.md` — parallel update.

11. `scripts/test-dispatch-plan-voters.md` — document the new harness assertions and `PLUGIN_ROOT_STUB` extension.

12. `scripts/test-dispatch-code-voters.md` — parallel update.

13. `skills/shared/voting-protocol.md` — replace the existing "For items prefixed with `[OUT_OF_SCOPE]`" paragraph (~line 93). Important: line 93 is INSIDE a fenced Voter Prompt Template. Move the HTML drift comment to Markdown prose **adjacent to** (not inside) the fenced block. Two structural changes: (a) above the fence, add a Markdown paragraph containing the canonical OOS clause verbatim (finding-only variant — lowest-common-denominator), preceded by an HTML comment naming `render-voter-prompt.sh` as runtime authority and listing the four drift-guarded copies. (b) Inside the fenced template, replace the existing OOS sentence with a grammar-conditional placeholder so readers see the structural shape.

14. `skills/design/SKILL.md` Step 3 MAV paragraph (~line 598) — inject the canonical OOS clause (finding-oos variant) inline, prefixed with one sentence of context. Existing "same proportionality rubric as the voting panel" framing remains for FINDING_N items.

15. `skills/implement/SKILL.md` Step 5 MAV paragraph (~line 1238) — inject the canonical OOS clause (finding-only variant) inline. One-line note that the clause applies to FINDING items with the `[OUT_OF_SCOPE]` prefix.

16. `skills/design/references/plan-review.md` (~+25 LOC at lines 69-75) — embed the canonical OOS clauses (finding-oos variant) in the Voter 1 prompt template so the /design Claude subagent voter receives the same judging rubric as Voters 2/3. Drift guard extends to this file.

17. `skills/review/SKILL.md` (~+5 LOC) — brief documentation note that /review's `REVIEW_CORE_STATUS=main-agent-vote-required` adjudication is **always delegated to the caller** (currently /implement Step 5). Documents current behavior so future maintainers do not duplicate the rubric in /review's own SKILL.md.

18. `agent-lint.toml` (~+2 LOC) — add `scripts/test-render-voter-prompt.sh` to the dead-script exclusion list at the same location as `scripts/test-dispatch-plan-voters.sh` (~lines 668-673).

19. `docs/linting.md` (~+2 LOC) — add a row to the public linting target table (~lines 40-44) for `make test-render-voter-prompt` alongside `test-dispatch-plan-voters`.

20. `Makefile` (~+4 LOC) — three additions: (a) `test-render-voter-prompt` to the `.PHONY:` list. (b) Target rule after `test-dispatch-plan-voters`. (c) Add to one `test-harnesses-N` shard (shard 13 or 14; new harness is fast).

### Failure modes

1. **Drift between canonical OOS clause copies** (helper × 2 grammar variants + 4 doc/SKILL.md verbatim copies = 6 logical locations). Earliest warning: `case_canonical_text_drift_guard` fails CI. Mitigation: drift-guard hard-codes the shared canonical-body string and greps all 4 doc/SKILL.md locations; `render-voter-prompt.md` documents edit-in-sync rules.

2. **Retry-prompt rendering regression** — plan explicitly leaves `make_*_retry_prompt_file()` UNCHANGED. Existing retry harnesses act as regression guards.

3. **Voter-behavior shift from prompt-text normalization** — mitigation: byte-preserve existing prose where possible; intentional content changes are additions (general rule for /design, grammar-conditional OOS clause for both), not rewrites.

## Acceptance

- The shared helper at `skills/shared/scripts/render-voter-prompt.sh` exists, is executable (`-x`), emits the full voter-prompt body to stdout for both `--id-grammar finding-oos` and `--id-grammar finding-only` modes.
- The helper does NOT call `larch_quiet_init` (otherwise its stdout would be redirected to the quiet log); leading comment + harness case pin this invariant.
- Both `scripts/dispatch-plan-voters.sh::make_prompt_file()` and `scripts/dispatch-code-voters.sh::make_voter_prompt_file()` invoke the helper with the documented flags and write the rendered body to a prompt file; their generated prompts contain the canonical OOS clause and the general fix-informational rule.
- The canonical OOS clause appears in `skills/shared/voting-protocol.md`, `skills/design/SKILL.md` Step 3 MAV, `skills/implement/SKILL.md` Step 5 MAV, and `skills/design/references/plan-review.md` (Voter 1 instruction); `scripts/test-render-voter-prompt.sh::case_canonical_text_drift_guard` greps all four.
- `scripts/test-render-voter-prompt.sh` exists with all six cases (`case_finding_only`, `case_finding_oos`, `case_canonical_text_drift_guard`, `case_executable_bit`, `case_lib_quiet_isolation`, `case_argument_validation`); registered in Makefile (`.PHONY` + target rule + one shard) and excluded in `agent-lint.toml`; documented in `docs/linting.md`.
- `scripts/test-dispatch-plan-voters.sh` and `scripts/test-dispatch-code-voters.sh` augment their `PLUGIN_ROOT_STUB` to include the new helper and assert the composed dispatcher prompts contain the unified text (finding-oos and finding-only variants respectively); test-dispatch-code-voters.sh additionally asserts NO `OOS_N` substring appears (grammar-conditional clause confirmed applied).
- Sibling .md docs for the four modified scripts (`dispatch-plan-voters.md`, `dispatch-code-voters.md`, `test-dispatch-plan-voters.md`, `test-dispatch-code-voters.md`) are updated to reflect the helper delegation.
- `skills/review/SKILL.md` includes a one-paragraph note documenting that /review's MAV adjudication is always delegated to /implement Step 5.
- `scripts/test-prompt-template-invariants.sh:134-137` continues to pass unchanged (the /design plan voter still has the plan/repo inspection allowance).
- `make lint` (including `make lint-bash32`) is green; CI workflows pass.

diff_lines: 693

## Test plan
(no test plan section in plan-file)
