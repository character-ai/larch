## Decision 1: Retirement scope — full retirement, author at compose time
- **Question**: Fully retire the staged-assessment / fingerprint-pin / drop-notice machinery and author the assessment fresh at Step 8 compose time, or make the minimal cross-rebase-pin fix?
- **Resolution**: Full retirement. Author the architectural-guideline assessment at Step 8 compose time, after the last Step 8b rebase, when HEAD and the shipped diff are stable. Remove the staged-assessment write, the diff-fingerprint pin, and the "HEAD drifted" drop notice. The 6 prior CLOSED attempts (#5337, #5675, #5969, #6059, #6106, #6114) were all minimal pin-patches that kept recurring; removing the drift window entirely is the durable fix.
- **Source**: user

## Decision 2: Durable committed copy — in scope
- **Question**: Also (re)write a durable/committed copy of the assessment from the same stable-HEAD compose step, or defer committed-copy auditability to the separate issue in the series?
- **Resolution**: In scope. Persist a durable copy of the assessment from the same stable-HEAD compose step so it survives in committed logs, not only the PR body. Author once against the final diff and write both the PR-body note and the durable copy from that single stable-HEAD point.
- **Source**: user

## Hard constraints (from issue acceptance criteria)
- **Question**: What must hold for the fix to be accepted?
- **Resolution**: (1) On a normal `--merge` run whose Step 8b rebases onto a moved `origin/main`, the shipped PR body contains a real assessment (clean note or deviation list), never the "dropped because HEAD drifted" notice. (2) A genuine deviation authored during the run reaches the PR body. (3) Extend the #6114 rebase test to assert the note survives a rebase where the base moved (not only the unchanged-feature-diff case), exercising the real Step 7a→Step 8 path rather than helper units. (4) Drop rate re-measured to ~0% (post-merge operator validation, not a code deliverable).
- **Source**: user / codebase
