### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:482-501
- **Concern**: Plan keeps manifest-outside-orchestrator expecting exit 2 while production path now treats that fixture as snapshotted carryover. Scenario: Identical setup to proposed work_carryover_orchestrator (pre-dispatch dirty other.txt, coder only touches src/main.py): snapshot at review-and-fix.sh:1235-1237 + unchanged other.txt is excluded from manifest and skipped by the guard, so the case should exit 0 with CODER_STATUS=applied, not 2 — make test-review-and-fix fails after the fix
- **Proposed resolution**: Repurpose manifest-outside-orchestrator to assert genuine outside-manifest fail-closed (e.g. clean other.txt at dispatch and a TEST_AGENT_BEHAVIOR stub that dirties a tracked path not present in coder-stage-paths.txt, or break the carryover snapshot so other.txt is dirty but not carryover); drop the Testing strategy claim that this case stays unchanged

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:482-501
- **Concern**: Testing strategy keeps manifest-outside-orchestrator expecting exit 2 but the fix makes that fixture succeed. Scenario: That orchestrator pre-dirties other.txt before dispatch so it is snapshotted as carryover; with round_dir passed the guard skips it and scoped commits only src/main.py — identical to planned carryover-orchestrator (test B) so make test-review-and-fix fails or duplicates a passing case
- **Proposed resolution**: Repurpose manifest-outside-orchestrator (e.g. custom stub also mutates other.txt so diff ≠ snapshot, or add a non-snapshotted dirty path) to keep an integration fail-closed case; drop the “unchanged manifest-outside-orchestrator” line from the testing strategy

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:63-82 (planned round_has_non_carryover_tracked_residue)
- **Concern**: Post-commit residue uses porcelain path=${line:3} while the pre-commit guard uses capture_round_tracked_paths. Scenario: Rename or quoted paths (e.g. R/old -> new) can be mis-parsed or missed by grep -Fxq against the manifest while still appearing in git diff — follow-up/skip behavior diverges from the guard
- **Proposed resolution**: Accept as #3272 out-of-scope only if documented; otherwise align extraction with capture_round_tracked_paths for residue checks or document rename/space paths as unsupported

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:564-577
- **Concern**: Proposed `round_has_non_carryover_tracked_residue` skips every manifest-listed path (`grep -Fxq "$path" "$manifest" && continue`) but post-commit follow-up must still run for dirty manifest paths (e.g. pre-commit hook re-touch). Scenario: After a scoped primary commit, hook residue on `src/main.py` stays tracked-dirty and is listed in `coder-stage-paths.txt`; the helper returns 1, so lines 564–577 skip follow-up and line 574 never fails—regresses `round-hook-residue` / `round-persistent-hook-residue` while the plan claims hook behavior is preserved
- **Proposed resolution**: Remove the manifest `grep` skip from the post-commit helper; warn-and-continue only for `path_is_pre_coder_carryover`. Prefer walking `capture_round_tracked_paths` (same source as the pre-commit guard) instead of porcelain `${line:3}`. Update `review-and-fix.md` residue text to match

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:482-501
- **Concern**: Testing strategy keeps manifest-outside-orchestrator expecting exit 2 and CODER_STATUS=failed, but the proposed guard passes round_dir and snapshots other.txt at review-and-fix.sh:1235-1237 before dispatch — the same carryover setup as new case B. Scenario: make test-review-and-fix fails after implementation even when production behavior is correct; implementer may chase a spurious regression
- **Proposed resolution**: Repurpose manifest-outside-orchestrator to expect exit 0, CODER_STATUS=applied, round commit on src/main.py only, and carryover warning (or delete it as redundant with carryover-orchestrator). Update the Testing strategy bullet that says this case stays unchanged. Keep fail-closed coverage via unchanged single-arg manifest-outside-guard plus extracted negative control (snapshot deleted / path mutated)
