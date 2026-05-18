### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/test-cache-key-runtime-audit.sh:80-94`, `scripts/test-cache-key-runtime-audit.sh:179-188` — The new mutation fixtures model the second attachment as a later linear child of the first assistant, so `prefix_records()` sees it as an appended stable-prefix record, not a mutation at an established prefix position. Concrete failing scenario: the tool-result fixture produces records `[sys1, usr1/result-A]` then `[sys1, usr1/result-A, usr2/result-B]`, and `classify_change()` returns `EXPECTED-GROWTH`, while the harness asserts `BASELINE,CACHE-INVALIDATING`; the image fixture has the same shape. Suggested fix: make the “mutation” fixtures branch from the same parent position, like the existing `write_cache_invalidating_fixture()` does, or change these two assertions to `EXPECTED-GROWTH` and add separate branched attachment-mutation cases.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-cache-key-runtime-audit.sh:80-94`, `scripts/test-cache-key-runtime-audit.sh:179-188` — The new mutation fixtures model the second attachment as a later linear child of the first assistant, so `prefix_records()` sees it as an appended stable-prefix record, not a mutation at an established prefix position. Concrete failing scenario: the tool-result fixture produces records `[sys1, usr1/result-A]` then `[sys1, usr1/result-A, usr2/result-B]`, and `classify_change()` returns `EXPECTED-GROWTH`, while the harness asserts `BASELINE,CACHE-INVALIDATING`; the image fixture has the same shape. Suggested fix: make the “mutation” fixtures branch from the same parent position, like the existing `write_cache_invalidating_fixture()` does, or change these two assertions to `EXPECTED-GROWTH` and add separate branched attachment-mutation cases.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## correctness: scripts/test-cache-key-runtime-audit.sh:99-195

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] write_attachment_stable_fixture omits planned second identical tool_result turn Plan §4 requires two turns with same tool_result content for EXPECTED-GROWTH; fixture uses plain-text usr2 so coverage and pass message imply a scenario the plan did not describe Use two tool_result user turns with identical JSON per plan, or revise plan and comments to match the implemented user:initial extension case
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## security: scripts/cache-key-runtime-audit.py:103-129 scripts/cache-key-runtime-audit.py:333-341

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Full tool_result JSON in prefix digest and diffs Audit output or saved reports may embed secrets from tool outputs Document sensitivity add redaction or gate verbose serialization
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** (`risk-integration`) — [larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/manifest.json](larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/manifest.json): The branch adds a committed implement run directory with `status: "in-progress"`, plus [larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-goals-test.md](larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-goals-test.md) and [larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-review-tally.json](larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-review-tally.json). This is unrelated to the audit-script behavior under review, increases noise and size on every clone, and risks violating the repo’s own run-log hygiene expectations (operators and reviewers must reason about whether this tree is intentional). **Scenario:** PR merges with a stray in-progress run; future tooling or humans treat `larch-logs/` as authoritative and get confused by duplicate plan text and non-final manifests. **Suggested fix:** Drop these paths from the PR (or replace with a single finalized artifact only if a tracking issue explicitly requires committing this run, following `docs/run-logs.md`).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`) — [larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/manifest.json](larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/manifest.json): The branch adds a committed implement run directory with `status: "in-progress"`, plus [larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-goals-test.md](larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-goals-test.md) and [larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-review-tally.json](larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-review-tally.json). This is unrelated to the audit-script behavior under review, increases noise and size on every clone, and risks violating the repo’s own run-log hygiene expectations (operators and reviewers must reason about whether this tree is intentional). **Scenario:** PR merges with a stray in-progress run; future tooling or humans treat `larch-logs/` as authoritative and get confused by duplicate plan text and non-final manifests. **Suggested fix:** Drop these paths from the PR (or replace with a single finalized artifact only if a tracking issue explicitly requires committing this run, following `docs/run-logs.md`).
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## code-quality: larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated implement run artifacts (manifest, plan-goals-test, tally) committed alongside the audit fix. PR noise, possible policy/process mismatch, harder review and merge conflict risk on larch-logs. Remove run-log artifacts from the PR or replace with intentionally scoped committed logs per repo contract.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `security` `scripts/cache-key-runtime-audit.py:145` and `scripts/cache-key-runtime-audit.py:296-309` — The new redaction invariant does not hold for dict-shaped non-text content blocks: `_is_attachment_bearing()` only recognizes list content, and `content_to_text()` returns a dict’s `"text"` field before checking `type`. Concrete scenario: a transcript entry like `{"type":"user","message":{"content":{"type":"file","text":"SECRET"}}}` can be included as `user:initial` and render `SECRET` in the audit report, despite `SECURITY.md` saying raw attachment bodies are no longer reproduced. Fix by handling dict content in `_is_attachment_bearing()` and checking `block_type not in ("", "text")` before returning `"text"` in the dict branch.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/cache-key-runtime-audit.py:145` and `scripts/cache-key-runtime-audit.py:296-309` — The new redaction invariant does not hold for dict-shaped non-text content blocks: `_is_attachment_bearing()` only recognizes list content, and `content_to_text()` returns a dict’s `"text"` field before checking `type`. Concrete scenario: a transcript entry like `{"type":"user","message":{"content":{"type":"file","text":"SECRET"}}}` can be included as `user:initial` and render `SECRET` in the audit report, despite `SECURITY.md` saying raw attachment bodies are no longer reproduced. Fix by handling dict content in `_is_attachment_bearing()` and checking `block_type not in ("", "text")` before returning `"text"` in the dict branch.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## correctness: implementation plan Files to Modify (1-4) vs branch diff

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch modifies SECURITY.md and adds larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/* not listed in the plan's four-file surface Plan-to-implementation traceability breaks; merged tree carries implement run artifacts alongside the audit fix Remove unintended run-log files from the PR or extend the written plan; document SECURITY.md if intentional
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: scripts/cache-key-runtime-audit.py:312-337

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] user:attachment does not set included_initial so a later plain user in the same chain can be mislabeled user:initial Chain system then tool_result user then assistant then plain user then assistant: plain user is recorded as user:initial; later edits to that plain text can yield CACHE-INVALIDATING even if runtime cache treats only the true opener plus attachments as stable Tighten user:initial eligibility or mark initial slot consumed after first included user prefix record; add regression for attachment-then-text chain
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## risk-integration: larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/manifest.json;larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-goals-test.md;larch-logs/implement/C5B28F06-C105-4ECC-B99A-59C3023BFB0E/plan-review-tally.json

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Committed in-progress implement run artifacts and embedded plan text not listed in the attachment-fix plan Feature PR carries unrelated larch-logs session state (in-progress manifest, full plan copy), increasing noise and risking policy mismatch with how implement logs should land Remove these files from the branch unless run-log policy explicitly requires them
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Nit** (`risk-integration`) — [scripts/test-cache-key-runtime-audit.sh](scripts/test-cache-key-runtime-audit.sh) (~175–189): New checks only compare `classification_sequence` from `audit_run`; they do not assert anything about rendered report text (e.g. presence of `payload_sha256` / absence of raw attachment bodies) despite [SECURITY.md](SECURITY.md) and [scripts/cache-key-runtime-audit.md](scripts/cache-key-runtime-audit.md) documenting redacted reporting. **Scenario:** A future change could route classification through summarized digests but accidentally restore raw bodies in `PrefixRecord.render` / diff output without failing this harness. **Suggested fix:** Extend `run_audit` assertions for one attachment fixture to grep for `payload_sha256` and against a distinctive raw secret string placed in fixture content.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Nit** (`risk-integration`) — [scripts/test-cache-key-runtime-audit.sh](scripts/test-cache-key-runtime-audit.sh) (~175–189): New checks only compare `classification_sequence` from `audit_run`; they do not assert anything about rendered report text (e.g. presence of `payload_sha256` / absence of raw attachment bodies) despite [SECURITY.md](SECURITY.md) and [scripts/cache-key-runtime-audit.md](scripts/cache-key-runtime-audit.md) documenting redacted reporting. **Scenario:** A future change could route classification through summarized digests but accidentally restore raw bodies in `PrefixRecord.render` / diff output without failing this harness. **Suggested fix:** Extend `run_audit` assertions for one attachment fixture to grep for `payload_sha256` and against a distinctive raw secret string placed in fixture content.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Nit** `code-quality` `scripts/test-cache-key-runtime-audit.sh:75-196` — The feature explicitly names `tool_use`, but the new fixtures cover `tool_result`, image mutation, and stable `tool_result` only. Add a `tool_use` fixture so future regressions in that named block type cannot pass unnoticed.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/test-cache-key-runtime-audit.sh:75-196` — The feature explicitly names `tool_use`, but the new fixtures cover `tool_result`, image mutation, and stable `tool_result` only. Add a `tool_use` fixture so future regressions in that named block type cannot pass unnoticed.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `scripts/cache-key-runtime-audit.py:326` — `prefix_records()` still ignores top-level transcript entries with `type:"attachment"`, even though committed transcripts use those for prompt-bearing material like `deferred_tools_delta`, `skill_listing`, and `command_permissions` (`larch-logs/implement/14EA567C-39FB-439D-9962-BC343E074002/session-transcript.jsonl:5-7`). Concrete failing scenario: two assistant requests branching from the same parent with `command_permissions` changing from `["Read"]` to `["Read","Edit"]` produce records containing only `system:init`, so the second turn classifies as `EXPECTED-GROWTH` instead of `CACHE-INVALIDATING`. Include `entry.entry_type == "attachment"` records in the stable prefix, serialize/redact `raw["attachment"]` through the same summary path, and add a branched top-level attachment mutation fixture.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/cache-key-runtime-audit.py:326` — `prefix_records()` still ignores top-level transcript entries with `type:"attachment"`, even though committed transcripts use those for prompt-bearing material like `deferred_tools_delta`, `skill_listing`, and `command_permissions` (`larch-logs/implement/14EA567C-39FB-439D-9962-BC343E074002/session-transcript.jsonl:5-7`). Concrete failing scenario: two assistant requests branching from the same parent with `command_permissions` changing from `["Read"]` to `["Read","Edit"]` produce records containing only `system:init`, so the second turn classifies as `EXPECTED-GROWTH` instead of `CACHE-INVALIDATING`. Include `entry.entry_type == "attachment"` records in the stable prefix, serialize/redact `raw["attachment"]` through the same summary path, and add a branched top-level attachment mutation fixture.
- **Suggested revision**: Address the concern above.

