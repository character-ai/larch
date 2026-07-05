### OOS_1: [OUT_OF_SCOPE] Third local copy of normalize will drift
- **Description**: [OUT_OF_SCOPE] Third local copy of normalize will drift. Scenario: `execution_issues.normalize_body_for_hash` and `run_log_batch._normalize_body_for_hash` already differ. Copying either into `architectural_guidelines.py` adds a third variant.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Route append through implement-run launcher
- **Description**: [OUT_OF_SCOPE] Route append through implement-run launcher. Scenario: The write-compose fence uses `implement-run-$PPID.sh`; the planned append fence calls `python3` directly. Launcher adds pause/rehydration consistency.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/references/architectural-guidelines-present.md
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Use run_logs file lock on md write
- **Description**: [OUT_OF_SCOPE] Use run_logs file lock on md write. Scenario: `run_log_batch._append_execution_issue` acquires a lock; the helper plans direct writes.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/core/architectural_guidelines.py
- **Phase**: design



### OOS_4: Route append-deviation-note through implement-run launcher like write-compose
- **Description**: Route append-deviation-note through implement-run launcher like write-compose. Scenario: Prompt-side direct python3 cli.py bypasses the launcher used for other Step 8 fences; parity with pause/rehydration is nicer but a tmpdir-only append has no demonstrated failure on the genuine-deviation path
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/architectural-guidelines-present.md
- **Phase**: design



### OOS_5: Route append-deviation-note through implement-run-$PPID.sh like write-compose
- **Description**: Route append-deviation-note through implement-run-$PPID.sh like write-compose. Scenario: The write-compose fence uses the launcher for pause/rehydration; the planned helper uses bare python3. Consistency only; no stated requirement and prior round rejected this. ## Findings ### 1. [correctness] `python/larch/core/architectural_guidelines.py` — ndjson dedup contract The plan’s secondary ndjson guard compares `sha256(normalize_body_for_hash(note))` to existing `source_sha256` strings. Ship-time flushing in `python/larch/report/run_log_flush.py` dedupes with `_redact_batch_payload`, `run_log_batch._normalize_body_for_hash`, and `exec_issue_detail.structured_body_dedupe_keys` (covered by `test_execution_issues_batch_dedupes_repeated_warning_events` in `python/tests/report/test_run_logs.py`). Those paths differ from `execution_issues.normalize_body_for_hash` on the raw note file. After a pre-push refresh, ndjson can already contain the guideline under a different `source_sha256` than the note-only hash, so the helper returns `ok`, re-appends to md, and a later refresh can commit duplicate guideline rows. Acceptance criterion 2 stays at risk. **Suggested revision:** Reuse the flush dedup contract: redact the formatted entry, compute Warnings body keys, and compare against `_existing_execution_issue_keys` from the run batch before any md write. ### 2. [correctness] `python/larch/core/architectural_guidelines.py` — md Warnings dedup granularity Scanning the entire `### Warnings` section for one hash does not match how flush splits content (`_execution_issue_chunks`) or how duplicates appear in logs such as `larch-logs/implement/9694D21F-505C-4782-80D5-33126E3533DE/execution-issues.ndjson`. When other Warnings bullets share the section, section-level hashing misses an identical guideline line. **Suggested revision:** Dedup per chunk using the same body-key logic as flush, against both existing md Warnings bullets and the ndjson batch. ### 3. [completeness] `skills/implement/references/architectural-guidelines-present.md` — entry shape The present reference still says to append under Warnings but does not pin how draft markdown maps to md lines. Dedup hashes and body keys depend on that shape. **Suggested revision:** Add one normative entry format in the deviation-path contract and implement the helper to emit that text before dedup. ### [OUT_OF_SCOPE] Launcher routing for the new fence Prior round rejected routing `append-deviation-note` through `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh"`. The plan’s direct `python3 … cli.py` call matches other small helpers; no new evidence that pause/rehydration requires launcher wrapping for this read-only append.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/architectural-guidelines-present.md
- **Phase**: design



