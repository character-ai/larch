### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `scripts/lint-fix-loop.sh:150`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/lint-fix-loop.sh:150`      `scripts/lint-fix-loop.sh:150-160` treats any dirty tree after the coder runs as lint-fix output and commits it with `Apply /relevant-checks fixes (...)`, but Step 3 can run while the Claude-fallback implementation is still uncommitted (`skills/implement/SKILL.md:1258-1301`), and Step 6 can run before Step 7’s review-fix commit (`skills/implement/SKILL.md:1464-1508`). Concrete scenario: Claude fallback edits files, Step 3 checks fail, the lint helper changes one file, then `git add -A` commits both the original implementation and lint fix under the checks-fix message; Step 4 then has no implementation diff left or fails on “nothing to commit.” Fix by making Step 3/Step 6 site-aware: either do not commit from `lint-fix-loop.sh` when downstream commit steps own the dirty tree, or capture a clean baseline and only commit when the pre-dispatch tree was clean.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## code-quality: scripts/test-implement-structure.sh:38-39

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Attribution grep matches any substring user has (case-insensitive). Innocent SKILL or contract prose like end user has access can fail the structural test as a false positive. Use word boundaries or a tighter multi-word forbidden phrase list aligned to the original hallucination pattern.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: scripts/lint-fix-loop.md:27-32 vs scripts/lint-fix-loop.sh:108-122

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Contract step order for empty log vs missing coders disagrees with script Empty redacted log with no external coders returns no-changes from code but contract ordering suggests main-agent-required may apply, confusing implementers debugging session-env. Reorder contract bullets or script logic so documented behavior matches emitted KVs.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1258-1267,skills/implement/SKILL.md:~1464-1527

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 3/6 check-failure prose drops explicit until-clean outer loop after lint-fix-loop; applied/no-changes only mandate a single checks re-run. After LINT_FIX_STATUS=applied the orchestrator re-runs run-relevant-checks-captured.sh once; checks still return STATUS=fail (partial external fix). The updated text does not say to repeat lint-fix-loop/main-agent repair until RELEVANT_CHECKS_OK=true unlike the replaced until-clean instruction. Restore an explicit repeat-until-clean (or until failed stall) sentence around the STATUS=fail and LINT_FIX_STATUS branches.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1363-1368

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 5 post-checks prose requires resolving lint failures without lint-fix-loop while forbidding main-agent Edit/Write. After review fixes, run-relevant-checks-captured fails; doc gives no external lint-fix dispatch and bans main-agent fixes, leaving no consistent repair path. Add step5 lint-fix-loop (or explicit exception + mechanical external path) aligned with Steps 3/6.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/lint-fix-loop.sh:137`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/lint-fix-loop.sh:137`      `scripts/lint-fix-loop.sh:137-160` dispatches a full-auto external coder and then stages all changes without the submodule scrub/revert guard used by review fixes (`skills/review-and-fix/scripts/review-and-fix.sh:179-213`). Concrete scenario: a checks log points at a checked-out submodule path, the coder edits it or `.gitmodules` despite the prompt-only prohibition at `scripts/lint-fix-loop.sh:47`, and the helper either commits `.gitmodules`/gitlink changes or stalls after leaving the submodule dirty. Add mechanical submodule discovery plus post-dispatch revert/refusal before `git add -A`, matching the review-and-fix guardrail.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: scripts/lint-fix-loop.sh:143-147

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dispatch-failure exit omits FAILURE_REASON despite contract. Stall to Step 18 loses machine-readable reason without reading wrapper logs. Emit FAILURE_REASON on the failed dispatch branch.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## risk-integration: scripts/lint-fix-loop.sh:159

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] git add -A stages the entire working tree before commit. Unrelated local edits get swept into the automated lint-fix commit with wrong scope and blame. Stage only externally touched paths or diff against a pre-run snapshot.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## risk-integration: scripts/lint-fix-loop.sh:159-161 scripts/git-commit.sh:30-91

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Lint-fix commits use git-commit.sh default Co-Authored-By Claude Code. Codex/Cursor did the edits but git history shows Claude Code co-authorship, contradicting explicit external-coder attribution goals. Use --no-trailer or tool-specific Co-Authored-By for the active CODER_TOOL.
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:1368

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 5 post-review-fixes checks prose omits lint-fix-loop.sh while Steps 3/6 use it; prose is resolve+re-invoke only. When --site step5-review-fixes fails with external Codex/Cursor available the orchestrator no longer gets the same delegated repair path as Step 6; main-agent must infer repair without the LINT_FIX_STATUS contract. Mirror Step 3/6: pass REDACTED_LOG_FILE through scripts/lint-fix-loop.sh --site step5 (or equivalent) and gate on LINT_FIX_STATUS; or explicitly document why Step 5 must differ.
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## security: scripts/lint-fix-loop.sh:52-59

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Fixed Markdown fence around inlined checks log allows fence breakout if the log contains closing ``` lines. Tool or linter output includes a fence terminator; following log bytes are interpreted as instructions by Codex/Cursor despite the preamble. Use an unpredictable fence token, encode the log (e.g. base64), or sanitize lines equal to ``` before embedding.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## architecture: skills/implement/SKILL.md:1368

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Step 5 checks-failure prose does not reference lint-fix-loop.sh or LINT_FIX_STATUS unlike Steps 3 and 6. Operators expect uniform external-coder repair for all check failures; Step 5 stays vague (“resolve”) and may under-use Codex/Cursor. Align Step 5 with the lint-fix-loop contract or state explicitly that Step 5 is main-agent-only by design.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/lint-fix-loop.sh:233`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/lint-fix-loop.sh:233`      `lint-fix-loop.sh` does not snapshot or verify `HEAD` around the external coder dispatch (`scripts/lint-fix-loop.sh:233-263`), even though the “Do NOT commit” rule is only prompt text. Concrete failing scenario: Cursor ignores the prompt, edits a file, runs `git add -A && git commit -m fix`, exits 0, and leaves the working tree clean; the helper then emits `LINT_FIX_STATUS=no-changes` with no `LINT_FIX_COMMIT_SHA`, bypassing the helper-owned commit path at `scripts/lint-fix-loop.sh:266-272` and any forbidden-path detection based on working-tree diffs. Add a `baseline_head=$(git rev-parse HEAD)` before dispatch and fail closed if `HEAD` changes afterward, plus a behavioral test with a stub external agent that commits.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## risk-integration: scripts/lint-fix-loop.md:58-66 vs skills/implement/SKILL.md:1368

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Generic contract routes failed to Step 18 while Step 5 routes the same status to Step 16. Downstream automation reading only lint-fix-loop.md follows the wrong stall/cleanup rail for Step 5 failures. Qualify routing per --site in the contract or duplicate the Step 16 vs Step 18 language from SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## risk-integration: scripts/lint-fix-loop.sh:267-271

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] git add before git-commit.sh with no rollback on commit failure leaves the index partially staged. A hook rejects git-commit.sh after staging; STALL_TRACKING flow leaves operators with ambiguous staged state. Reset staged paths (or restore index) before fail_status, or use an atomic commit path that cannot leave half-staged state.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: scripts/test-implement-structure.sh:38-40

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Attribution regression test omits review-and-fix.sh. Reintroducing forbidden user-facing phrasing in shell breadcrumbs bypasses CI while docs stay clean. Include skills/review-and-fix/scripts/review-and-fix.sh (and any other narration hosts) in the grep set.
- **Suggested revision**: Address the concern above.

