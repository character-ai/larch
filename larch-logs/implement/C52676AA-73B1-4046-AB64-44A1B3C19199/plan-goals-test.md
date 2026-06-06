## Goal
Implement issue #3592: [IMPLEMENTING] [BUG] (URGENT) lint-fix cap skips final re-verify; stall signature too coarse\n\nTwo cooperating defects that turned a recoverable Step 5 situation into a terminal `[STALLED]` run (run `3876DC27-D694-4C99-B942-61A52A2554D7`, issue #3547):.

## Implementation Plan
Two cooperating defects that turned a recoverable Step 5 situation into a terminal `[STALLED]` run (run `3876DC27-D694-4C99-B942-61A52A2554D7`, issue #3547):

**(a) Step 5 lint-fix attempt cap fires before the final applied fix is verified.**
`skills/review-and-fix/scripts/review-implement-step5-loop.sh` (post-round checks loop): on `STEP5_LINT_STATUS=applied` the loop increments `lint_attempts` and, when `lint_attempts >= lint_max`, emits `STEP5_REVIEW_STATUS=stall` / `lint-fix-attempt-cap` **without re-running the checks helper on that final applied fix**. The Nth repair (already committed by `lint-fix-loop.sh`) is never verified, so a tree that would have gone green is declared stalled. Observed empirically: in rounds 3 and 4 the stranded repair sets were complete and correct — `scripts/test-check-contains-pins.sh` passed unmodified on direct re-run, and the round-3 residue (quiet-env unset guard, `.gitleaks.toml` / `agent-lint.toml` registrations) was committed verbatim during recovery. Suggested: re-run the captured checks after the final `applied` attempt before declaring the cap, or count verify-failures rather than applies.

**(b) Stall signature has no failure-evidence component, collapsing distinct failures into `same-cause-repeat`.**
`skills/implement/scripts/stall-recovery-report.sh` `cmd_classify`: `signature=$(printf ... "class=..." "hint=..." "step=..." "phase=..." "bail=..." | hash_text)`. Any two stalls with the same class/hint/step/phase/bail hash identically regardless of which check actually failed. In the incident, three genuinely different failures (quiet-env harness assertion, an unsatisfiable local python gate, `test-check-contains-pins` pin drift) all produced the same signature, so the second recovery dispatch classified `same-cause-repeat`, burned the 2-attempt cap, and the run went terminal `[STALLED]` even though each failure was individually fixable. Suggested: mix a bounded, sanitized failure-evidence digest into the signature — e.g. the first failing make target / hook id extracted from the **redacted** checks log — keeping the existing allowlist discipline per `SECURITY.md`.

**Related, not covering**: #3563 / PR #3581 improved stall-report fields (exit code, bail-reason surfacing); open #3579 covers missing bail-reason enum tokens. Neither addresses the cap-before-verify ordering or signature granularity.

## Test plan
(no test plan section in plan-file)
