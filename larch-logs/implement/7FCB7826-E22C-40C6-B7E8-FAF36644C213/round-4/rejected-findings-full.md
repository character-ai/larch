### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Makefile — unrelated harnesses share `test-harnesses-16` shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unrelated harnesses share the `test-harnesses-16` shard. A shard failure does not isolate design-publish vs upgrade-larch. Optional shard split for clearer CI signal.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: SKILL.md Step 5c — `FINAL_SUMMARY_PATH` not confined to `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The orchestrator verbatim-emits `FINAL_SUMMARY_PATH` from parsed result env without confining it to `DESIGN_TMPDIR` or rejecting symlinks. A same-UID attacker (or buggy tool) could replace `.design-publish-result.env` with `FINAL_SUMMARY_PATH=/etc/passwd` or point `final-summary.md` at a symlink; Step 5c item 5 reads and emits that file verbatim into operator chat, leaking host content. Resolve the path under canonical `DESIGN_TMPDIR`; refuse symlinks and paths outside the tmpdir prefix before Read/cat.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: SKILL.md Step 5c — parsed `WARN=` replayed verbatim without sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 5c replays parsed `WARN=` values verbatim to top chat without sanitization. A tampered `.design-publish-result.env` containing `WARN=Run rm -rf …` or exfiltration instructions could be shown as trusted operator guidance and steer the orchestrator off the skill script. Replay only driver-known `WARN` templates, or parse `WARN` via `phase_driver_read_result_env` with newline rejection and length caps.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: design-publish.sh — duplicated phase-driver boilerplate without shared library
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Argv validation, `validate_repo`, `parse_kv_from_output`, and `write_result_env_and_emit` duplicate sibling driver patterns without a shared library. Future drivers may copy the same block again, increasing drift across `design-route`, `design-init-runparams`, and `design-publish`. Defer until a fourth driver; then factor shared validators/KV parsing into `lib-phase-driver.sh`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: design-publish.sh — whitespace-only `--session-id` rejected with exit 2
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Whitespace-only `--session-id` is rejected with exit 2 beyond the plan newline/CR rule. If the orchestrator passes `--session-id` with only spaces, the driver exits 2 (config error) instead of following empty-`SESSION_ID` branches. Remove whitespace-only rejection or document it as intentional hardening.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

