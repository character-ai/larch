## Plan

# Implementation Plan — Issue #2673: Voter prompt YES↔EXONERATE clarification

## Files to modify

1. **`skills/design/references/plan-review.md`** — "Voter prompts" section (the two voter prompt strings, currently at the Voter 1 bullet and the shared Codex/Cursor/Claude-replacement paragraph).
   - In the Voter 1 (Claude Code Reviewer subagent) prompt string, **replace the single sentence** `When voting, also consider proportionality: vote EXONERATE (not YES) if the finding's concern is legitimate but the proposed change would introduce more complexity than the issue warrants.` with the multi-paragraph YES↔EXONERATE framing from the issue body (verbatim).
   - In the shared Voter 2/3 (Codex / Cursor / Claude replacement) prompt string, **replace the single sentence** with the same multi-paragraph framing.
   - The leading instruction prose ("You are a senior code reviewer..." / "You are a senior engineer...") is preserved as-is. Only the proportionality sentence is replaced.

2. **`scripts/dispatch-plan-voters.sh`** — `make_prompt_file()` (the per-tool prompt-emit function).
   - **Replace the single `printf` line** that currently emits `Vote EXONERATE, not YES, if the concern is legitimate but the proposed change would introduce more complexity than the issue warrants.` with a sequence of `printf '%s\n'` lines (or one `printf '%s\n' "$VAR"` with a quoted multi-line variable) that emits the multi-paragraph YES↔EXONERATE framing verbatim.
   - The rest of `make_prompt_file()` (output format directives, "Verify silently", "Output ONLY vote lines") is unchanged.
   - `make_plan_voter_retry_prompt_file()` is unchanged — it concatenates `PLAN_VOTER_PARSE_RATE_RETRY_PREFIX` with the primary prompt body, so the new framing is automatically included in retry prompts.

3. **`skills/design/references/plan-review-quick.md`** — "Procedure" section.
   - **Augment** the acceptance-guidance line `Accept when the concern is clear and unambiguous. Reject nits and speculative concerns. Mark valid but out-of-scope items as OOS.` with a condensed restatement of the YES↔EXONERATE framing applied to single-reviewer inline review.
   - Quick mode has no separate voter panel; the same proportionality logic governs Claude's inline accept/reject decisions. Keep this section terse — the canonical anchor phrase `When in doubt between YES and EXONERATE, prefer EXONERATE` is included for searchability, but the multi-paragraph block from the issue body is NOT pasted in full (quick mode acceptance is not a vote; it is a self-review). Roughly 5-8 lines added.

4. **`scripts/test-dispatch-plan-voters.sh`** — additive assertion.
   - Immediately after the existing `grep -Fq 'OOS_N:' "$TMP/healthy/codex-plan-voter-prompt.txt"` assertion (and the parallel cursor one), add a new `grep -Fq 'When in doubt between YES and EXONERATE, prefer EXONERATE'` assertion against the same two prompt files. This pins the canonical anchor phrase in the rendered prompt.

## Approach

The user picked "verbatim" wording — the multi-paragraph block from the issue body is dropped into `plan-review.md` (twice — Voter 1 and shared Voter 2/3) and `dispatch-plan-voters.sh` (once) without rewording. `plan-review-quick.md` gets a condensed adaptation because quick mode does not have a voter panel.

The multi-paragraph block from the issue body:

```
The YES ↔ EXONERATE boundary requires careful judgment. Both votes accept that the finding is correct and the concern is real. The difference is whether the proposed plan revision is worth shipping in THIS PR:

- Vote YES when: the finding is correct AND the proposed plan revision (or any equivalent revision the implementer would write) materially improves the plan's clarity, completeness, or correctness, AND the revision's complexity is proportionate to the issue's severity. A YES vote is a commitment to revise the plan.

- Vote EXONERATE when: the finding is correct AND the concern is real, BUT one of:
  - The proposed plan revision adds disproportionate complexity for the issue's severity (e.g., a 5-line clarification fix for a 1-line nit; a new mechanism for a one-off edge case).
  - The finding is correct but the plan would already address it implicitly (e.g., reviewer says "missing X" but X is covered by an obvious extension of an already-named contract).
  - The finding is correct but better addressed in a follow-up PR (out-of-PR scope creep).
  - The concern is forward-looking / speculative; valid but not pressing for this PR's correctness.

When in doubt between YES and EXONERATE, prefer EXONERATE. A YES vote should feel like "yes, the plan WILL be worse without this revision." An EXONERATE vote feels like "yes, this is a real concern, but I would not insist on it during a senior code review."

(The YES ↔ NO and NO ↔ EXONERATE boundaries are unchanged: NO means the finding is wrong / a false positive / based on a misreading.)
```

For `dispatch-plan-voters.sh`, store the block in a single-quoted variable inside `make_prompt_file()` and emit with `printf '%s\n' "$framing"`. This keeps the source readable and avoids per-line `printf` escaping. (Pattern is shell-3.2-safe; identical to how `PLAN_VOTER_PARSE_RATE_RETRY_PREFIX` is already declared in the same script.)

## Edge cases

- **Markdown code-span hygiene (`.claude/rules/markdown-no-space-in-code-span.md`)**: the multi-paragraph block contains backticks only around `YES`, `NO`, `EXONERATE`, and quoted-prose markers — none with leading/trailing whitespace. No MD038 risk.
- **`printf` quoting**: the prose contains parentheses, slashes, hyphens, and quoted phrases — all safe inside a single-quoted Bash variable. No `%` characters appear in the prose that would interact with `printf` format strings.
- **Newlines**: the proposed wording uses single-newline paragraph breaks. Use `printf '%s\n' "$framing"` (with newlines embedded in the variable) rather than per-paragraph `printf` calls — easier to keep in sync with the markdown source of truth.
- **Bash 3.2 portability**: no `${var^^}` / namerefs / mapfile introduced. Same `printf` style as elsewhere in the file.
- **Retry prompt inheritance**: `make_plan_voter_retry_prompt_file()` reads the primary prompt file via `cat` and prefixes the retry header — no edit needed there; new framing inherits automatically.
- **Plan-review.md prose duplication**: the Voter 1 and Voter 2/3 prompt strings each contain the full multi-paragraph block. They are intentionally duplicated (each prompt is a self-contained instruction handed to a different agent). A future refactor could extract to a shared template; out-of-scope for this PR.
- **Test stub interference**: the harness uses stub binaries that emit fixed output regardless of prompt content. The new assertion inspects the prompt **file** on disk (which is always written by `make_prompt_file`), independent of how the stub agent responds. No stub change needed.

## Failure modes

1. **Prose drift between the three text locations** (`plan-review.md` Voter 1 / Voter 2/3 / `dispatch-plan-voters.sh` / `plan-review-quick.md`). Once verbatim is established, an edit to one location can silently diverge from the others.
   - **Earliest warning**: a future `/design` run where one voter slot exhibits noticeably different acceptance behavior from another would be the first observable signal.
   - **Mitigation**: the new harness assertion catches drift in `dispatch-plan-voters.sh`. For the markdown files, the canonical phrase `When in doubt between YES and EXONERATE, prefer EXONERATE` could be grep-pinned in a future structural test (deferred to follow-up issue per user "verbatim" decision).

2. **Voter behavior over-corrects toward EXONERATE**, dropping acceptance rates below useful thresholds.
   - **Earliest warning**: next 2-3 `/design` runs show acceptance rates noticeably below the pre-change baseline. `voting-tally.md` and `accepted-plan-findings.md` per run are the diagnostic surfaces.
   - **Mitigation**: revert is a four-file restore. The change is prose-only; rollback is trivial.

3. **`printf` format mishap during multi-paragraph emit** corrupts the rendered prompt and silently degrades the voter prompt.
   - **Earliest warning**: the new harness assertion fails — `grep -Fq 'When in doubt between YES and EXONERATE, prefer EXONERATE'` will not match a corrupted render.
   - **Mitigation**: store the block in a single-quoted variable assignment and emit with `printf '%s\n' "$var"`. This is the same pattern as `PLAN_VOTER_PARSE_RATE_RETRY_PREFIX` already in the script.

## Testing strategy

- **`bash scripts/test-dispatch-plan-voters.sh`** — must pass with the new assertion present. Existing assertions (waterfall wiring, paths-file, healthy/retry/substantive-fail modes) unaffected.
- **`make lint`** — exercises pre-commit hooks repo-wide (markdownlint, shellcheck, bash32 portability, foreground markers, etc.).
- **`bash scripts/test-design-structure.sh`** — confirms no byte-preserved anchors in plan-review.md were disrupted. Pre-PR grep confirmed no structural assertions reference the Voter 1/2/3 prompt prose, so the change is structure-test-safe.
- **`bash scripts/relevant-checks.sh`** — repo-wide pre-commit smoke for the touched paths.

No new test file is created. The single additive assertion is added inline to the existing `test-dispatch-plan-voters.sh` harness.

diff_lines: 50

## Acceptance

- `skills/design/references/plan-review.md` Voter prompts section: both Voter 1 (Claude Code Reviewer subagent) and the shared Voter 2/3 (Codex / Cursor / Claude-replacement) prompt strings contain the multi-paragraph YES↔EXONERATE framing (verbatim from issue #2673) in place of the single-line proportionality sentence.
- `scripts/dispatch-plan-voters.sh` `make_prompt_file()`: the per-tool prompt file contains the multi-paragraph YES↔EXONERATE framing (verbatim), emitted via a single-quoted variable + `printf '%s\n' "$var"` pattern that mirrors the existing `PLAN_VOTER_PARSE_RATE_RETRY_PREFIX` declaration.
- `skills/design/references/plan-review-quick.md` Procedure section: the acceptance-guidance prose is augmented with a condensed YES↔EXONERATE framing that includes the canonical anchor phrase `When in doubt between YES and EXONERATE, prefer EXONERATE`.
- `scripts/test-dispatch-plan-voters.sh`: an additive `grep -Fq 'When in doubt between YES and EXONERATE, prefer EXONERATE'` assertion runs against the rendered codex and cursor prompt files in the `healthy` stub mode; existing waterfall / paths-file / retry / substantive-fail assertions remain passing.
- `bash scripts/test-dispatch-plan-voters.sh` passes.
- `make lint` passes (markdownlint, shellcheck, bash32, foreground markers).
- `bash scripts/test-design-structure.sh` passes.
- No change to vote tally logic, voter selection, panel composition, the 2-of-3 acceptance threshold, voter weight engineering, or code-review voter prompts in `scripts/dispatch-code-voters.sh`.

diff_lines: 50
