### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Unreadable bundles and `NEEDS_DEEP` do not agree
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-evidence-gate
- **Severity**: major
- **Concern**: The triage prompt asks for `NEEDS_DEEP` output on unreadable bundles, but ingest rejects rows that do not match a bundle-derived `evidence_token`. That means unreadable issues never record cleanly and can keep looping until someone works around the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Omit unreadable issues from JSONL or add a token-free unreadable ingest path documented in both agent and SKILL.
  - From dyn-dyn-evidence-gate: Either require a successful bundle Read (valid token) before any verdict including `NEEDS_DEEP`, or add a separate ingest schema for tokenless unreadable-bundle rows that never sets `triage_evidence_verified` and cannot drive cache skip, deep queue, or report verdicts.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: `evidence_token` parsing can be spoofed by newline injection
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-evidence-gate
- **Severity**: major
- **Concern**: Untrusted issue text can inject or shadow the bundle’s `evidence_token` line, and first-match parsing accepts the spoofed value. A crafted title/body with embedded line breaks can therefore make ingest validate against attacker-chosen text instead of the coordinator’s token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-evidence-gate: Write the coordinator token on line 1 of every bundle (before any untrusted title/body), or normalize title/header fields to strip `\n`/`\r` and reject embedded `evidence_token:` substrings before assembly; optionally restrict parsing to a fixed line index or signed/HMAC token format that untrusted fields cannot forge.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Deep ingest needs a verification-bit regression test
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no regression test that proves a deep ingest leaves `triage_evidence_verified` set on an already verified issue. Without that coverage, a future change could accidentally clear the bit and re-enable unverified triage routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add deep ingest fixture asserting triage_evidence_verified stays True after ingest


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Verified triage is skipped from deep routing under `--refresh`
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Stage 2 reruns ledger compute with `--refresh` after triage ingest, which makes the completion check report false and causes the deep-candidate selector to ignore newly ingested verified triage rows. Fresh verified triage needs to remain usable for deep routing even when refresh is used to skip stale completion caches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

