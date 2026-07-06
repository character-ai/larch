### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:815-827
- **Concern**: Tiered reviewer sections must not skip present files with zero parsed entries. Scenario: The plan requires present-but-empty `ARCHITECTURAL_INVARIANTS.md` / `ARCHITECTURAL_GUIDELINES.md` to count as knowledge (`architectural_knowledge_required=true`), inject a no-parsed-entries cue, and require coder acknowledgment. Today `_architectural_guidelines_review_section()` returns "" when `status=present` but `content.strip()` is empty, and tests pin that noop. Replacing the helper without changing the gate drops reviewer context and cache keys for the exact edge case the plan calls out.
- **Proposed resolution**: Gate inclusion on reader `status=present` (not parsed-body non-emptiness), emit explicit no-parsed-entries cues, and update rendering tests so present+empty-parsed includes the tiered block instead of matching absent behavior.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_ci_launcher.py:507-560
- **Concern**: Codex resume launches omit the static implementer body. Scenario: Codex `needs_qa` resumes build `_implement_prompt()` with `static=""` and only the resume block plus path parameters. If the new architectural-knowledge section is appended only with the first-launch static body, resume invocations lose read-order, scope, and acknowledgment instructions while the launch-time snapshot still requires `architectural_acknowledgment` on the next `complete` or `needs_qa` manifest.
- **Proposed resolution**: Pin in `_ci_launcher.py` that the architectural-knowledge block is appended on every `_implement_prompt()` return, including Codex resume (`codex_session` set), and extend `test_external_dispatch.py` with a resume-path assertion.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: agents/_implementer-base.md:94-132
- **Concern**: Implementer self-validation omits `needs_qa` acknowledgment rules. Scenario: The plan adds `architectural_acknowledgment` for `status=complete` and `status=needs_qa` when knowledge is present, but `_implementer-base.md` jq self-validation only structurally checks `needs_qa.questions`. External coders can emit a first `needs_qa` manifest without acknowledgment and only fail at dispatcher bail.
- **Proposed resolution**: Add conditional jq (or an equally explicit pre-rename check) for both `complete` and `needs_qa` branches when the launcher included the architectural-knowledge section, and extend the required-fields table accordingly.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_ci_launcher.py:535-559
- **Concern**: Launch-time architectural knowledge snapshot only records the true state. Scenario: No architecture file is present at launch, so the coder receives no architectural section and no acknowledgment requirement. If a valid knowledge file appears before manifest validation, `dispatch_step2.py` has no false snapshot and falls back to the live predicate, then emits `architectural-acknowledgment-missing` for a manifest that could not have known to include the field.
- **Proposed resolution**: Always write or replace `step2-architectural-knowledge.env` before external launch with `ARCHITECTURAL_KNOWLEDGE_REQUIRED=true|false`; make dispatch treat a well-formed snapshot as authoritative and fall back to the live predicate only when the snapshot is absent or malformed.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_step2.py
- **Concern**: Incomplete FINDING_1 fix: acknowledgment gate runs only after structural validation passes. Scenario: The plan gates `architectural_acknowledgment` on `_complete_schema_valid` succeeding first. A `status=complete` manifest that is schema-invalid for any other reason still enters `_emit_manifest_invalid_or_recover`, can emit `STATUS=claude_fallback` with `RECOVERY_FROM=manifest-schema-invalid`, and commit the external coder tree with no acknowledgment when knowledge was required.
- **Proposed resolution**: Run the shared `_require_architectural_acknowledgment` check for `status=complete` and `status=needs_qa` whenever the launch-time snapshot or `architectural_knowledge_required(repo_root)` says knowledge was required, before `_complete_schema_valid` failure can route into `_emit_manifest_invalid_or_recover`. On missing or empty acknowledgment, call `st.emit_bailed("architectural-acknowledgment-missing")` directly. Add a dispatch test where knowledge is required, the manifest is schema-invalid, acknowledgment is absent, and stdout must show `REASON=architectural-acknowledgment-missing` with no `RECOVERY_FROM=`.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/agents/_ci_launcher.py:535-560
- **Concern**: External coder prompt assembly omits the untrusted content-block envelope for architectural knowledge. Scenario: Codex Step 2 user prompts are built only from `_implement_prompt()` parameters (agent body goes to `instructions.md`; `static` is empty whenever `codex_session` is set). The plan lists read-order bullets and constraint language for `_ci_launcher.py` but does not require wrapping reader output in `issue_wire.emit_untrusted_content_block` with distinct `architectural_invariants` / `architectural_guidelines` tags, unlike the planned reviewer change in `rendering.py` and unlike `architectural-guidelines read`. Repo-local file text can then read as higher-priority instructions and compete with AGENTS.md/skills/plan scope.
- **Proposed resolution**: Require `_implement_prompt()` (every launch, including Q/A resume) to append parsed present-file content only through the same untrusted block helper/tags used on the reviewer path, plus one-line untrusted-evidence framing in `agents/_implementer-base.md`; keep invalid/absent fail-closed gating unchanged.



