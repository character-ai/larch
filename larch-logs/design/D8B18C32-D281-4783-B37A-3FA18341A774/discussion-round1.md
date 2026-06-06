## Decision 1: Fix approach
- **Question**: Which fix should the plan target for the `bug-body` → `/larch:issue --input-file` heading mismatch (0 items parsed)?
- **Resolution**: Wire the existing, already-tested `issue-input-file` subcommand into `skills/implement/references/stall-recovery.md` step 4. After `bug-body` produces the body, call `stall-recovery-report.sh issue-input-file --classification-file <class> --body-file <bug-body output>` to synthesize the `### [Bug] /implement stall: <class> at <step>` heading, then pass THAT file to `/larch:issue --input-file`. Do NOT modify `bug-body`'s body composition (`compose_body_content` / `cmd_bug_body_like`); leave the consumer-repo "Action required" chat-print path byte-unchanged.
- **Source**: user

## Decision 2: Hardening scope (in-scope vs out-of-scope)
- **Question**: Should the fix also harden the *silent* no-op in `/issue --input-file` (0-item case), or stay minimal?
- **Resolution**: Stay minimal (SIMPLE-tier). **In-scope**: (a) the step-4 wiring change in `stall-recovery.md`; (b) a regression test pin in `test-stall-recovery-report.sh` asserting the generated input file parses to `ITEMS_TOTAL=1` under `skills/issue/scripts/parse-input.sh`. **Out-of-scope**: any change to `skills/issue/scripts/parse-input.sh` or `/issue --input-file` 0-item behavior (would expand blast radius into the shared `/issue` parser and risks overlap with in-flight #3550 / #3547 — pursue separately as a blocked-by issue if desired).
- **Source**: user

## Hard constraints / must-not-break
- `bug-body` and `bug-comment` output bodies, and the consumer-repo/`--forked` verbatim chat-print path, must remain unchanged.
- `issue-input-file` is already covered by `test-stall-recovery-report.sh` Case 18 (dry-run) and the allowlist TSV; the wiring change must keep `DRY_RUN_DECISION` handling intact (dry-run still skips GitHub).
- First-detection filing only fires when `attempt_count==0` and `FAILURE_CLASS` is non-terminal; the wiring change must not alter that gate.
