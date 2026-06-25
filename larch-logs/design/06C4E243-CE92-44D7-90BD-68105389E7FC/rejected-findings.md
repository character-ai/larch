### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:33-34,42
- **Concern**: RESUME_BACKREF_LITERAL trailing period mismatches SKILL.md example. Scenario: The plan SKILL.md example ends with `...first-time Step 3 review fence above.` but the harness constant omits the final period. If implementer copies the SKILL example, the full-line `grep -qF` back-reference pin fails and `make lint` breaks even when prose is otherwise correct.
- **Proposed resolution**: Pin one canonical string in both places: drop the period from the SKILL example or add it to `RESUME_BACKREF_LITERAL`, and state they must match byte-for-byte. **Finding 1** (correctness, in_scope): `plan.txt:33-34` vs `plan.txt:42` — the resume back-reference example in `skills/design/SKILL.md` ends with a period; `RESUME_BACKREF_LITERAL` in `scripts/test-implement-anti-polling-rule.sh` does not. The harness full-string pin will fail if implementers follow the SKILL example verbatim. Fix: declare one canonical literal and require byte-identical use in both files. **Prior accepted findings (resume harness retarget):** The current plan now lists all six resume-locus removals (237–241, 269–293) and replacement back-reference pins. That prior accepted gap looks addressed; no re-raise. **Rejected / OOS ledger items:** Not re-raised (verbosity Post-notification harness pins, `progress-reporting.md`, blanket `test-implement-anti-polling-rule.md` line 33 invariant) — no materially new evidence beyond what round 2 already judged.

