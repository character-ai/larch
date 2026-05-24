### OOS_1: Add harness assertion for canonical YES↔EXONERATE phrase in rendered voter prompt
- **Description**: The parent design log (run 6B5851D9-) for issue #2678 described a harness assertion that would grep `When in doubt between YES and EXONERATE, prefer EXONERATE` against the rendered codex/cursor voter prompt files in the `healthy` stub-mode block of `scripts/test-dispatch-plan-voters.sh`. The current source-level structural check in `scripts/test-design-structure.sh` (this PR) verifies the canonical phrase appears in `skills/shared/scripts/render-voter-prompt.sh` source, but does not verify that the rendered output of `scripts/dispatch-plan-voters.sh make_prompt_file()` actually contains the phrase in the produced `$DESIGN_TMPDIR/{codex,cursor}-plan-voter-prompt.txt` files. A second additive assertion in the `healthy` block of `scripts/test-dispatch-plan-voters.sh` (around line 152 — alongside the existing `grep -Fq 'OOS_N:' "$TMP/healthy/codex-plan-voter-prompt.txt"` assertion) would close this rendered-output gap and is a small follow-up.
- **Reviewer**: Claude (quick mode)
- **Vote tally**: N/A — quick-mode self-review
- **Phase**: design

