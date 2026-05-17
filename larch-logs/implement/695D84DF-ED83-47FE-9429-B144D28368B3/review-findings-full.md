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

### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/run-step1-plan-log.sh:63`, `scripts/run-step5-review.sh:68`, `skills/implement/SKILL.md:142`, `skills/implement/SKILL.md:493-506` — The new Step 1 and Step 5 launchers derive `RUN_ID` from `$IMPLEMENT_TMPDIR/session-id`, but `/implement` already supports canonical run IDs that differ from that file: `--run-id <ID>` and Branch 1 resume via `parent-issue.md`. Concrete scenario: `/implement --run-id custom-run ...` initializes manifest/metadata under `larch-logs/implement/custom-run/`, but `run-step1-plan-log.sh` writes `plan-goals-test` and `run-step5-review.sh` passes review logging under the generated session id instead, so tracking summaries point at missing/incomplete committed run logs. Fix by persisting the canonical `RUN_ID` into session-env or deriving it from the existing manifest/sentinel first, with `session-id` only as fallback; add launcher harness cases where `RUN_ID != session-id`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/run-step1-plan-log.sh:63`, `scripts/run-step5-review.sh:68`, `skills/implement/SKILL.md:142`, `skills/implement/SKILL.md:493-506` — The new Step 1 and Step 5 launchers derive `RUN_ID` from `$IMPLEMENT_TMPDIR/session-id`, but `/implement` already supports canonical run IDs that differ from that file: `--run-id <ID>` and Branch 1 resume via `parent-issue.md`. Concrete scenario: `/implement --run-id custom-run ...` initializes manifest/metadata under `larch-logs/implement/custom-run/`, but `run-step1-plan-log.sh` writes `plan-goals-test` and `run-step5-review.sh` passes review logging under the generated session id instead, so tracking summaries point at missing/incomplete committed run logs. Fix by persisting the canonical `RUN_ID` into session-env or deriving it from the existing manifest/sentinel first, with `session-id` only as fallback; add launcher harness cases where `RUN_ID != session-id`. Commits reviewed: `1826b48`, `eced74d`, `130f673`, `f5b73e7`, `ae30c1b`, `5a72590`, `6ec51ba`.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## code-quality: scripts/test-run-step5-review.sh

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness omits several argv/reject branches compared to launcher-argv-test-coverage spirit. Regression holes for bad ROUND_NUM or malformed session-env booleans/workflow. Extend assertions for exit-2 paths and invalid env combinations.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## code-quality: skills/review-and-fix/scripts/review-and-fix.md:50

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sibling contract claims round-1 token/timing ledger marks inside review-and-fix.sh but the shell file contains no ledger invocations after the diff. Readers and future edits assume marks live in review-and-fix.sh while SKILL.md pre-loop Bash performs Step 5 marks; double-mark or missing-mark regressions become easy. Align review-and-fix.md with the real mark site (SKILL preamble only) or restore marks in review-and-fix.sh to match the doc.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: scripts/run-relevant-checks-captured.md:13

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Still claims Step 5 marks are owned by review-and-fix.sh Conflicts with SKILL Step 5 preamble and updated review-and-fix.sh behavior Reword invariant to name the real marking site
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: scripts/run-relevant-checks-captured.sh:116-122 and skills/implement/SKILL.md:1269-1270,1457-1458

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Duplicate token-ledger mark for Step 3 and Step 6 on /implement path (SKILL block then run-relevant-checks-captured case step3/step6). Token budget windows reset twice in a row; check-step-token-budget can undercount prior-phase vendor spend and miss or delay cap_hit before expensive steps. Keep one authoritative mark site: remove token-ledger from helper and mark in ship-pr only where needed, or remove token lines from SKILL Step 3/6 and rely on helper.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1360-1398

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5 gates still reference round_cap but bash no longer assigns it Orchestrator cannot evaluate round_num vs cap mechanically; cap log line may be wrong Add session-env-derived round_cap binding or rewrite gates to use POST_PLAN_WORKFLOW_PATH literals
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1360-1398

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 5 gate prose still compares round_num to round_cap after removing the Bash that exported round_cap from quick_mode. Bash snippets copied from the SKILL that still use [ "$round_num" -lt "$round_cap" ] see an empty round_cap and mis-evaluate loop termination vs caps. Add a short shell binding for round_cap from POST_PLAN_WORKFLOW_PATH or stop using shell variables in those gates.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## correctness: skills/review-and-fix/scripts/review-and-fix.md:30-41; scripts/run-relevant-checks-captured.md:13; skills/review-and-fix/scripts/review-and-fix.sh:554-563

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Sibling docs claim Step 5 ledger marks inside review-and-fix.sh; code removed timing mark block without replacement in hunk Future maintainer deletes SKILL preamble marks thinking script owns them Align docs with mark ownership or restore script-side marks
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: skills/review-and-fix/scripts/review-and-fix.md:50-51

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Contract documents round-1 token/timing marks inside review-and-fix.sh but script has no such invocations Readers assume child performs Step 5 ledger marks; code path does not, risking wrong refactors or dropped telemetry Update contract to match SKILL/parent ownership or restore marks in script if still required
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## risk-integration: .claude/rules/launcher-argv-test-coverage.md + scripts/test-run-step5-review.sh + scripts/test-run-step1-plan-log.sh + skills/implement/scripts/test-run-step2-dispatch.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harnesses omit most reject paths and validation branches required by launcher-argv rule Regressions in new argv validation or session-env parsing ship without CI signal Add per-branch assertions with exit 2 and pinned stderr
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## risk-integration: scripts/run-relevant-checks-captured.md:13

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Invariant still attributes Step 5 ledger marks solely to review-and-fix.sh. SKILL.md now emits Step 5 token/timing marks before run-step5-review.sh; operators may add duplicate marks trying to satisfy this stale contract. Rewrite the bullet to state SKILL-owned marks (or whichever component is authoritative after the launcher split).
- **Suggested revision**: Address the concern above.

