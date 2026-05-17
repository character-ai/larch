### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `skills/design/scripts/tally-plan-review.sh:151-160`, `skills/implement/SKILL.md:1039`, `scripts/write-tally.sh:20-22`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/design/scripts/tally-plan-review.sh:151-160`, `skills/implement/SKILL.md:1039`, `scripts/write-tally.sh:20-22`      The new HARD-path `plan-review-tally` flush writes real `accepted_count` / `rejected_count`, but `/implement` Step 1 still rewrites the same replace-mode `plan-review-tally` batch later without passing counts, so `write-tally.sh` defaults them back to `0`. Concrete scenario: a HARD plan review with 1 accepted and 1 rejected finding first flushes `accepted_count=1,rejected_count=1`, then Step 1 overwrites the final committed `plan-review-tally.json` with `0,0`. Fix by either skipping the parent Step 1 rewrite when `/design` already flushed the HARD tally, or updating Step 1 to derive and pass the actual `--accepted`, `--rejected`, and `--rounds` values.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1159

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Prose says invoke step2-implement.sh directly. Mismatches actual run-step2-dispatch.sh call site. Update wording to the launcher/dispatcher layering.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1382-1384

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Re-review and bulk-skip gates still instruct invoking review-and-fix.sh directly. Orchestrator may reconstruct a long argv from prose, reintroducing paraphrase risk the launchers were meant to remove. Point gates at run-step5-review.sh with the same two-flag pattern as the main loop.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:42

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NEVER #4 still claims direct review-and-fix.sh invocation. Contradicts Step 5 launcher narrative; confuses operators. Update NEVER text to run-step5-review.sh derivation.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: Makefile:27-51

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Shard-10 comment claims test-ship-pr but shard-10 rule omits it Future resharding mistakes break CI balance assumptions Match comment to test-harnesses-10 deps or move test-ship-pr
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## correctness: skills/design/scripts/tally-plan-review.sh:149-160

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Parent plan-review-tally flush always passes write-tally --mode hard. SIMPLE/quick parent runs record plan-review-tally batches as hard mode, contradicting SKILL Step 1 mode rules. Derive simple|hard from parent session-env POST_PLAN_WORKFLOW_PATH (or skip flush until known).
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1116-1122

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2 token-ledger mark removed from orchestrator; only external launchers mark now. Runs with coder=claude or cursor→claude_fallback never hit launch-codex/cursor, so the Step 2 token-ledger JSONL mark disappears vs main, breaking token-window assumptions and undercounting those sessions. Restore mark on orchestrator for non-external paths or emit once from step2-implement.sh before claude early exits without double-marking Codex/Cursor.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1159

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 2 prose still says invoke step2-implement.sh Orchestrator follows prose and bypasses run-step2-dispatch.sh, restoring long argv from SKILL Change prose to name run-step2-dispatch.sh as the foreground entrypoint
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## correctness: skills/review-and-fix/scripts/review-and-fix.sh:574-576 and skills/implement/SKILL.md:1334-1335

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Duplicate token-ledger mark Step 5 on round 1: SKILL preamble plus new run_implement_round call. /implement Step 5 round 1 emits two identical token-ledger marks for one review phase, skewing per-step token accounting. Keep a single mark site (remove one of the two calls).
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## risk-integration: .claude/rules/launcher-argv-test-coverage.md paths front-matter

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New launchers/harnesses not listed in canonical paths array Argv edits may ship without harness parity nudge Update paths list to include new launcher + test paths
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## risk-integration: .claude/rules/launcher-argv-test-coverage.md:4-6

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] paths frontmatter omits new Step 1/2/5 launchers and harnesses Contributors may not realize argv or message-text edits require harness updates per the repo rule Extend paths (and narrative) to include run-step1-plan-log run-step5-review run-step2-dispatch and their test-run-step* harnesses
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:1382-1384

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 5 re-review and bulk-skip prose names review-and-fix.sh instead of run-step5-review.sh On rare re-review or bulk-skip paths the orchestrator may hand-construct a divergent multi-flag review-and-fix argv instead of the launcher-derived argv pinned by tests Reword to require run-step5-review.sh with the same two flags as the main loop or add an explicit Bash snippet
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## security: skills/implement/SKILL.md:266-269

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unvalidated orchestrator value written into session-env via printf can embed extra lines if auto_mode contains newlines Attacker-influenced or buggy auto_mode injects additional KEY=value lines into session-env.sh after write-session-env output, altering downstream parsing order for keys not already present or confusing tooling that treats the file as line-oriented config Append LARCH_AUTO_MODE only through a validated helper (reject non true|false and reject multiline) or add write-session-env.sh support for vetted key updates
- **Suggested revision**: Address the concern above.

