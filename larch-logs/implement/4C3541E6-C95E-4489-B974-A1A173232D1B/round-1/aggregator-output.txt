Aggregating the supplied reviewer slots into merged findings. No file writes or mutating commands (read-only). Treating duplicate commit-title entries across `cursor-specialist-structure-output.txt` and `cursor-specialist-security-output.txt` as one behavioral cluster each; merging substantive overlap for `06df1786`, quick-mode EXONERATE wording, doc-vs-dispatcher formatting, and single-anchor harness coverage; keeping dyn-test coverage gaps as separate architecture findings.

---

### FINDING_1: `467605f3` — chore(larch-logs): flush implement run 4C3541E6-…
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Both reviewers surface the same commit-title-style item (`467605f3` — chore(larch-logs): flush implement run 4C3541E6-…) with no additional behavioral detail beyond the title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: `8c167678` — Sync plan-review Panel summary with YES/EXONERATE voter framing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Duplicate surfacing of the same commit-title item (`8c167678` — Sync plan-review Panel summary with YES/EXONERATE voter framing) without distinct sub-concerns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: `93ad9cbf` — chore(larch-logs): flush implement run 1BB00F8E-…
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Duplicate surfacing of the same commit-title item (`93ad9cbf` — chore(larch-logs): flush implement run 1BB00F8E-…) without distinct sub-concerns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_4: `666e60fe` — Clarify plan-review YES versus EXONERATE voter framing (#2673)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Duplicate surfacing of the same commit-title item (`666e60fe` — Clarify plan-review YES versus EXONERATE voter framing (#2673)) without distinct sub-concerns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: `06df1786` — chore(larch-logs): flush design run A7995B2E-… (#2684) — substantive diff vs security lens
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Same change set (`06df1786`), described in two lenses: (a) structure: `scripts/dispatch-plan-voters.sh` adds `plan_voter_yes_exonerate_framing` and emits it with `printf '%s\n'` after the existing opener; `scripts/test-dispatch-plan-voters.sh` greps an anchor on healthy Codex and Cursor prompt files; `plan-review-quick.md` adds a condensed accept/reject paragraph with the canonical anchor; `plan-review.md` replaces a one-line proportionality note with fenced `text` blocks for Voter 1 and Voter 2/3 and tightens the Panel summary bullet; large `larch-logs/` trees exist on the branch diff but are called intentionally out of scope for that review lens. (b) security: `dispatch-plan-voters.sh` replaces one static `printf` with a `local` variable and `printf '%s\n' "$plan_voter_yes_exonerate_framing"` to avoid `printf` format-string pitfalls (prose has no `%` sequences); ballot path emission remains `printf '... %s\n' "$BALLOT_FILE"` with unchanged trust boundary; no new `eval`, untrusted-driven subshell command construction, or credential handling in the shown hunks; doc changes reframe voter instructions without changing tally math, dispatcher wiring, or external tool invocation patterns in the shown diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: Quick-mode EXONERATE-like judgment vs reject / OOS labeling (`skills/design/references/plan-review-quick.md:21`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Quick-mode guidance maps EXONERATE-like judgment to rejected or OOS without clearly distinguishing exonerate from false-positive reject; downstream readers may treat rejected-findings as false positives while the intent is valid-but-not-actionable (EXONERATE analog), or mis-compare quick-mode rejected-findings to full-mode EXONERATE tallies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Clarify in-doc how exonerate-equivalent concerns should be labeled or filed relative to rejected vs OOS artifacts.
  - From cursor-specialist-edge-cases-output.txt: Add a sentence defining reject as non-actionable on the plan not incorrect and steer some cases to OOS.

### FINDING_7: Markdown fenced voter prose vs shell-emitted prompts (`plan-review.md` ~73–112 vs `scripts/dispatch-plan-voters.sh` ~46–61)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Fenced voter prose in markdown is indented relative to list nesting while shell-emitted prompts are flush-left with different bullet indentation; maintainers comparing doc vs `codex-plan-voter-prompt.txt` may see false drift or edit non-canonical copy despite a verbatim-prose goal (formatting / risk-integration mismatch, not necessarily runtime breakage).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Dedent markdown fences or document that whitespace is not part of the canonical prompt.
  - From cursor-specialist-edge-cases-output.txt: Strip leading indentation in fences or declare dispatcher output canonical for Voter 2/3.

### FINDING_8: Harness only pins one anchor line in rendered prompts (`scripts/test-dispatch-plan-voters.sh:151-152`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The harness only greps the anchor sentence on healthy Codex/Cursor prompt files; loss or truncation of the multi-paragraph YES/EXONERATE framing in `dispatch-plan-voters.sh` could slip through if the anchor line stays intact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a second grep for another distinctive line from the framing block, or a small golden-file substring check in a follow-up.
  - From cursor-specialist-edge-cases-output.txt: Add an optional second grep for another distinctive sentence from the framing block.

### FINDING_9: Quick-mode vocabulary — “this PR’s correctness” (`skills/design/references/plan-review-quick.md:21`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Quick-mode design doc uses “this PR’s correctness”; minor vocabulary mismatch may nudge implementers toward a code-review mental model on a design-only path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rephrase to “this change” or “this design step” (keep the anchor phrase).

### FINDING_10: Panel summary references YES/EXONERATE framing beyond plan subsection list (`skills/design/references/plan-review.md:1166-1171`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Panel summary paragraph updated to reference YES/EXONERATE voter framing though the implementation plan only listed Voter prompts subsection edits; cherry-pick or partial revert could leave summary wording inconsistent with voter prompts if someone splits commits without this hunk; treat as intentional doc sync; optionally document in plan for strict traceability; no functional fix needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Retry prompt composition path lacks anchor assertion in harness (`scripts/test-dispatch-plan-voters.sh:63-65,151-174` vs `scripts/dispatch-plan-voters.sh:84-86`)
- **Reviewer(s)**: dyn-test-coverage-gaps-output.txt
- **Severity**: latent
- **Concern**: New anchor `grep -Fq` checks only healthy primary artifacts `codex-plan-voter-prompt.txt` and `cursor-plan-voter-prompt.txt` (`scripts/test-dispatch-plan-voters.sh:151-152`), while the absent-tools path already inspects `claude-plan-voter-prompt-retry.txt` for the retry header (`scripts/test-dispatch-plan-voters.sh:64`) and the `retry-waterfall` block exercises parse-rate retry without opening any `*-plan-voter-prompt-retry.txt` for the anchor (`scripts/test-dispatch-plan-voters.sh:159-174`). That leaves the retry prompt composition path unguarded even though `make_plan_voter_retry_prompt_file` is supposed to embed the full primary body after the prefix (`scripts/dispatch-plan-voters.sh:84-86`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-gaps-output.txt: **Suggested fix:** After line 64, assert the anchor in `$TMP/absent/claude-plan-voter-prompt-retry.txt`, and after the retry-waterfall section assert it in `$TMP/retry-waterfall/codex-plan-voter-prompt-retry.txt` (created when voter-2’s first pass is narrative-only), so regressions that drop `cat "$src_prompt_file"` or point `orig_prompt` at the wrong file fail the harness.

### FINDING_12: Claude Voter 1 prose lives only in `plan-review.md` with no automated parity pin (`plan-review.md:71-110` vs `scripts/test-design-structure.sh:223-233`)
- **Reviewer(s)**: dyn-test-coverage-gaps-output.txt
- **Severity**: latent
- **Concern**: Voter 1’s instructions live only in `plan-review.md` (duplicate blocks around the anchor at `skills/design/references/plan-review.md:86` and `skills/design/references/plan-review.md:109`), orchestrated via Step 3’s mandatory read of that reference (`skills/design/SKILL.md` per grep context), not via `make_prompt_file` in `scripts/dispatch-plan-voters.sh`. `scripts/test-design-structure.sh` pins other `plan-review.md` contracts (`scripts/test-design-structure.sh:223-229` region) but not this voter prose, so the branch’s stated goal of keeping tool voters and the normative reference aligned has no automated parity check on the Claude Voter 1 surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-gaps-output.txt: **Suggested fix:** Add a small structural `grep -Fq` (or count) in `scripts/test-design-structure.sh` against `plan-review.md` for the canonical anchor so Voter 1 / shared reference drift is caught alongside the dispatch-script pin.

---

**Notes (process):** No input finding used the `[OUT_OF_SCOPE]` first-line tag, so no `### OOS_N:` blocks. `FINDING_8` merges two slots whose suggested revisions were not word-for-word identical, so they remain separate bullets. Because this output contains `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this file.
