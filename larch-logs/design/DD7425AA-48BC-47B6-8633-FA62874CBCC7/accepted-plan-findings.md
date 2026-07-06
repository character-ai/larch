### FINDING_1: Present-but-empty architectural docs must still reach reviewers
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Review-time architectural knowledge should not collapse a present file with zero parsed entries into the same empty output as an absent file, or the reviewer block, no-parsed-entries cue, and cache-key contribution disappear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate inclusion on reader `status=present` (not parsed-body non-emptiness), emit explicit no-parsed-entries cues, and update rendering tests so present+empty-parsed includes the tiered block instead of matching absent behavior.


### FINDING_2: Codex resume launches drop architectural guidance
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Resume launches should carry the architectural-knowledge section and read-order instructions, not only the first-launch static body, or Codex retries lose the acknowledgment context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin in `_ci_launcher.py` that the architectural-knowledge block is appended on every `_implement_prompt()` return, including Codex resume (`codex_session` set), and extend `test_external_dispatch.py` with a resume-path assertion.


### FINDING_4: Launch-time knowledge snapshot can go stale
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The launcher/dispatcher handshake should make the launch-time architectural-knowledge snapshot authoritative when present, otherwise a file that appears after launch can trigger a false missing-ack bailout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Always write or replace `step2-architectural-knowledge.env` before external launch with `ARCHITECTURAL_KNOWLEDGE_REQUIRED=true|false`; make dispatch treat a well-formed snapshot as authoritative and fall back to the live predicate only when the snapshot is absent or malformed.


### FINDING_5: Ack gating happens too late on schema-invalid completions
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Architectural acknowledgment should be required before schema-invalid complete manifests can route into manifest-invalid recovery, or a required ack can be skipped entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Run the shared `_require_architectural_acknowledgment` check for `status=complete` and `status=needs_qa` whenever the launch-time snapshot or `architectural_knowledge_required(repo_root)` says knowledge was required, before `_complete_schema_valid` failure can route into `_emit_manifest_invalid_or_recover`. On missing or empty acknowledgment, call `st.emit_bailed("architectural-acknowledgment-missing")` directly. Add a dispatch test where knowledge is required, the manifest is schema-invalid, acknowledgment is absent, and stdout must show `REASON=architectural-acknowledgment-missing` with no `RECOVERY_FROM=`.


### FINDING_6: Architectural knowledge needs untrusted-envelope framing
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: External coder prompts should wrap parsed architectural knowledge in the same untrusted content-block envelope used for reviewer feeds, so repo text cannot masquerade as higher-priority instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Require `_implement_prompt()` (every launch, including Q/A resume) to append parsed present-file content only through the same untrusted block helper/tags used on the reviewer path, plus one-line untrusted-evidence framing in `agents/_implementer-base.md`; keep invalid/absent fail-closed gating unchanged.


