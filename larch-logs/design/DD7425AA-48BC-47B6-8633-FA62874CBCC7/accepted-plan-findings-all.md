### FINDING_1: Acknowledgment can bypass recovery
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Prompt Contract Architect
- **Severity**: major
- **Concern**: Missing `architectural_acknowledgment` can still fall through recovery or pass the `needs_qa` path, so a complete or early-exit manifest can ship without the required proof of acknowledgment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: The plan routes missing acknowledgment through _complete_schema_valid / manifest-schema-invalid. Today that path calls _emit_manifest_invalid_or_recover, which can emit STATUS=claude_fallback with RECOVERY_FROM=manifest-schema-invalid and commit the external implementer's tree without any acknowledgment. That defeats the issue's hard verification requirement. Keep structural schema in _complete_schema_valid. After it passes, when architectural_knowledge_required is true, validate architectural_acknowledgment separately and call st.emit_bailed with a dedicated token (e.g. architectural-acknowledgment-missing). Do not route acknowledgment failures through _emit_manifest_invalid_or_recover. Apply the same direct-bail path for needs_qa when knowledge was required.
  - From Cursor-Pragmatic: In a repo with valid architectural knowledge present, an external coder returns `status=complete` with edits but omits `architectural_acknowledgment`. Validation fails inside `_complete_schema_valid`, recovery preserves the tree, and the run continues with no recorded acknowledgment. Add a separate `_require_architectural_acknowledgment(...)` helper (sanitize only). In `dispatch_step2.py`, call it for `status=complete` and `status=needs_qa` when readers mark knowledge required, and on failure return `st.emit_bailed(...)` directly. Do not route acknowledgment misses through `_emit_manifest_invalid_or_recover`.
  - From Cursor-Requirements: In dispatch_step2.py, after needs_qa question validation and before emitting STATUS=needs_qa, call the shared acknowledgment helper from dispatch_manifest.py whenever architectural knowledge was required. Fail with manifest-schema-invalid (or the same recovery path as complete) on empty/missing field; keep status=bailed exempt.
  - From Cursor-dyn-Prompt Contract Architect: Add a separate acknowledgment gate that calls st.emit_bailed("manifest-schema-invalid") (no recovery) for complete and needs_qa when architectural knowledge was required. Do not fold this check into _complete_schema_valid unless _manifest_invalid_bail_reason hard-bails all complete-schema defects. Extend test_implement_dispatch.py to assert RECOVERY_FROM is absent on missing-ack failures.


### FINDING_2: Shared architectural-knowledge predicate missing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Prompt Contract Architect, Codex-dyn-Prompt Contract Architect
- **Severity**: major
- **Concern**: The launcher and validator do not share one authoritative `architectural_knowledge_required` contract, so prompt injection, tmpdir state, and manifest validation can disagree about whether acknowledgment is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a shared helper in python/larch/core/architectural_guidelines.py (e.g. architectural_knowledge_required(repo_root)) with the same present/invalid/absent rules as prompt assembly. Call it from _ci_launcher.py when building the prompt and from dispatch_step2.py when validating manifests. Optionally persist KNOWLEDGE_REQUIRED=true to $IMPLEMENT_TMPDIR/step2-architectural-knowledge.env for tests, but treat the shared reader as authoritative.
  - From Cursor-Innovation: Write $IMPLEMENT_TMPDIR/step2-architectural-knowledge.env (or equivalent) once before the first launch with ARCHITECTURAL_KNOWLEDGE_REQUIRED and optional parsed snapshot hashes; have _ci_launcher read it for prompt assembly and dispatch_step2/dispatch_manifest read the same file for complete and needs_qa acknowledgment gating.
  - From Cursor-Requirements: Add one shared helper (for example architectural_knowledge_required(repo_root) -> bool plus optional parsed-entry metadata) used by _ci_launcher prompt assembly and dispatch_step2 validation, or write/read a single $IMPLEMENT_TMPDIR/step2-architectural-knowledge.env at launch and consume it at validation. Document the rule: required iff at least one knowledge file read returns status=present, including present-but-zero-parsed-entries cases from the plan edge cases.
  - From Cursor-dyn-Prompt Contract Architect: Add architectural_knowledge_required(repo_root) (or equivalent) in python/larch/core/architectural_guidelines.py, true when either reader returns present (including zero parsed I-* or G-* entries per Edge cases). Use it in _ci_launcher prompt injection and dispatch_step2 acknowledgment validation. Cover with test_external_dispatch.py and test_implement_dispatch.py.
  - From Codex-dyn-Prompt Contract Architect: No shared architectural_knowledge_required producer/consumer contract. Scenario: The plan threads a launcher-only flag into validation but names no shared helper or tmpdir marker. Prompt assembly runs in _ci_launcher._implement_prompt (agents/_ci_launcher.py:535-560); validation runs later in dispatch_step2.py. Divergent present/empty/invalid rules would gate the prompt differently than the manifest check. Add architectural_knowledge_required(repo_root) (or equivalent) in python/larch/core/architectural_guidelines.py, true when either reader returns present (including zero parsed I-* or G-* entries per Edge cases). Use it in _ci_launcher prompt injection and dispatch_step2 acknowledgment validation. Cover with test_external_dispatch.py and test_implement_dispatch.py.


### FINDING_4: Prompt growth needs closure-baseline regen
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The planned prompt-text edits will ratchet skill-closure-growth, but the closure-baseline artifact is not updated, so lint/CI can fail even when the feature code is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add ### UPDATED: python/skill-closure-baseline.json and regenerate it with python3 python/cli.py lint skill-closure-growth --write when the prompt growth is intentional.
  - From Codex-Innovation: Add python/skill-closure-baseline.json as MAY_UPDATE or firm when the ratchet grows, and include python3 python/cli.py lint skill-closure-growth or the relevant regen/check path in validation.


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


