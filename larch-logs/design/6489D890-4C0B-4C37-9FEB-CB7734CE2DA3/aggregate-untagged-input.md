### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:21-48
- **Concern**: The plan adds `--urgent` parsing in the Contract and `--title-prefix` in Step 5 but does not require stripping leading `--urgent` tokens before Step 1 security triage or the empty-description gate.. Scenario: `/bug --urgent SQL injection in auth` still runs Step 1 security triage on raw `$ARGUMENTS` (flag text first). `/bug --urgent` alone can fail the empty check for the wrong reason or skip investigation of the real description. Item 4 acceptance breaks.
- **Proposed resolution**: Add an early argv-normalization step (before Step 1): strip all leading `--urgent` tokens, bind `BUG_DESCRIPTION`, run Step 1 empty check and security triage on `BUG_DESCRIPTION`, use it in Steps 3-4, and pass `--title-prefix` only in Step 5.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/pr_body.py:16-30
- **Concern**: The plan says to reuse `oos_filer._FILED_URL_LINE_RE` for Item 1 JSON parsing. That couples run-summary rendering to the OOS filing module via a private regex.. Scenario: Implementers may `import oos_filer` from `pr_body.py`, widening the dependency surface and inviting drift if filing grammar changes independently.
- **Proposed resolution**: [SCOPE-REDUCTION] Duplicate the filed-URL line regex inline in `pr_body.py` (or lift one shared compiled pattern to `config.py`) instead of importing `oos_filer` private symbols.

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-7a.md:18-27
- **Concern**: Plan adds DIAGRAM_REASON KV emission in python/step_7a.py but does not list the Step 7a stdout contract doc in Files to modify/create. Scenario: Downstream readers of step-7a.md (orchestrator probes, harness authors) will not see the new key; contract drift is likely on the next Step 7a touch
- **Proposed resolution**: Add ### UPDATED: skills/implement/scripts/step-7a.md with a DIAGRAM_REASON row (empty on skip/ok; enriched generation-failed rc=<N> tail=<capped-redacted> on failure) and note it is emitted on both normal and rebase-checkpoint early-return tails

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:21-29
- **Concern**: Item 4 plan documents `--urgent` parsing in the Contract and Step 5 `/issue` call but does not require Steps 1-4 to use description-after-flag-stripping. Scenario: `/bug --urgent token leak` still treats raw `$ARGUMENTS` as the bug text in Steps 1-4: investigation greps `--urgent`, **Original report** can include the flag, and `/bug --urgent` alone may pass Step 1 empty-check because `--urgent` is non-empty before stripping
- **Proposed resolution**: Bind a stripped description once (Step 1 or a new parse step before validation) and state explicitly that Steps 1-4, title derivation, and Step 5 all use that value; run the empty-description guard only after removing leading `--urgent` token(s)
