### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: agents/_implementer-base.md:47-48,136,197
- **Concern**: python/larch/rendering/_rendering_generators.py:_implementer_text() depends on exact base splice strings not listed in the plan immutable contract. Scenario: Prose tightening can change TOOL_COMMIT_STDERR, the checklist TOOL_MODIFIED_HISTORY sentence, or guard #2 so it no longer matches ^2\. \*\*NEVER `git add`.*$; Codex then keeps Cursor-specific guard #2 text and wrong stderr path tokens while generate --check still passes
- **Proposed resolution**: Add an explicit byte-stable list in Approach step 3 and Edge cases: TOOL_COMMIT_STDERR, TOOL_MODIFIED_HISTORY, the exact checklist sentence Codex .replace() removes, and guard #2/#8 line prefixes the Codex re.sub and Cursor strip regexes anchor; verify with generate codex-implementer/cursor-implementer --check plus launcher tests

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/rendering/test_rendering.py:128-135
- **Concern**: Plan omits test-pinned scout prose substring optional best-effort. Scenario: Compressing SCOUT_MANIFEST_PATH lines in agents/_implementer-base.md or _rendering_generators.py intro can remove that phrase; py-test fails after an otherwise successful compression pass
- **Proposed resolution**: Add optional best-effort to the immutable prose list (or cite test_generated_implementers_include_scout_sidecar in Testing strategy / Failure modes)

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: agents/_implementer-base.md:47,136,197
- **Concern**: Generator hook tokens `TOOL_MODIFIED_HISTORY` and `TOOL_COMMIT_STDERR` are absent from the byte-stable preserve list. Scenario: `_implementer_text()` in `python/larch/rendering/_rendering_generators.py` does string substitution on those literals (cursor replaces them; codex also removes the checklist sentence containing `TOOL_MODIFIED_HISTORY`). Prose tightening that drops or rephrases them yields generated prompts with the wrong bail token name, wrong commit-stderr filename, or a codex prompt that still carries cursor-only checklist text
- **Proposed resolution**: Add `TOOL_MODIFIED_HISTORY` and `TOOL_COMMIT_STDERR` to the immutable token list in Approach step 3 and the `_implementer-base.md` byte-stable bullets; keep the exact checklist sentence `. `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself.` until generator logic changes

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/_rendering_generators.py:303,328
- **Concern**: Plan allows compressing Codex/Cursor intro prose but does not pin the `optional best-effort` substring. Scenario: `python/tests/rendering/test_rendering.py::test_generated_implementers_include_scout_sidecar` asserts that phrase in both generated implementer texts; removing it from the intro bullets during compression fails `make py-test` acceptance even when manifest/scout JSON blocks stay intact
- **Proposed resolution**: When tightening intro bullets in `_implementer_text()`, keep the substring `optional best-effort` (or explicitly add updating that test to the plan if the wording is intentionally changed)

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agents/_implementer-base.md:47,197
- **Concern**: python/larch/rendering/_rendering_generators.py applies silent codex/cursor transforms on shared base prose. Scenario: Plan freezes generator regex/replace logic but only generically says preserve hard guards and path tokens. `_implementer_text()` still does exact `.replace()` on `. `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself.` and regex rewrite of hard guard #2 (`^2\. \*\*NEVER `git add`.*$`). Prose tightening on those lines can fail transforms while `generate --check` passes, leaving codex-implementer.md with Cursor-specific hard guard #2 (`Cursor runs unsandboxed` / `TOOL_MODIFIED_HISTORY`) and wrong sandbox guidance
- **Proposed resolution**: Add explicit byte-stable hooks to Approach step 3 / UPDATED `_implementer-base.md`: keep hard guard #2 opening through the first `git commit` backticks regex-matchable; keep the checklist substring ending with `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself.` After regeneration, grep `agents/codex-implementer.md` must not contain `Cursor runs unsandboxed` or bare `TOOL_MODIFIED_HISTORY`, and must contain `workspace-write`

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/_rendering_generators.py:307,334
- **Concern**: Kind-specific intro prose encodes vendor-only commit guards not duplicated in `_implementer-base.md`. Scenario: Step 4 allows compressing Codex/Cursor header prose. Codex-only `workspace-write` sandbox semantics and Cursor-only `HEAD == BASELINE_SHA` / `cursor-modified-history` warnings live only in `_implementer_text()` headers. No harness asserts those strings; aggressive intro compression can drop them while generation checks still pass, weakening Step 2 implementer behavior
- **Proposed resolution**: In step 4 byte-stable list, require retaining codex `workspace-write` / `.git/` prohibition and cursor `HEAD == BASELINE_SHA` plus `cursor-modified-history` warnings. Add post-regen greps in Testing strategy for those literals in the generated agent files 1. **risk-integration** (`agents/_implementer-base.md:47,197`, `python/larch/rendering/_rendering_generators.py:310-311`): Shared-base compression can silently break codex-specific generation. The plan correctly forbids editing generator regex/replace logic, but it does not document the base-side anchors those transforms depend on. A prose-only pass that rewords hard guard #2 or the bailed-status checklist bullet can leave `generate --check` green while `codex-implementer.md` still carries Cursor-oriented commit guidance. 2. **correctness** (`python/larch/rendering/_rendering_generators.py:307,334`): Vendor-specific commit semantics live only in generated headers, not in `_implementer-base.md`. The plan authorizes intro compression without naming these header-only guardrails, and there is no test coverage for `workspace-write`, `BASELINE_SHA`, or `cursor-modified-history` in the generated prompts. That is a real silent-regression path on the Step 2 Codex/Cursor execution surface. [OUT_OF_SCOPE] **architecture** (`python/tests/rendering/test_rendering.py:128-135`): Consider a small rendering test that asserts codex/cursor generator invariants (transform success plus header guard strings). Real hardening gap, but not required for this density pass to ship; existing `--check` plus targeted greps are the minimum-change mitigation.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-Prompt Contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: agents/_implementer-base.md:47,136,197; python/larch/rendering/_rendering_generators.py:310-312
- **Concern**: The byte-stable list omits `_implementer_text()` replace/regex hooks in the shared base.. Scenario: Codex generation does `re.sub(r"^2\. \*\*NEVER `git add`.*$", ...)` on guard 2 and `.replace("TOOL_COMMIT_STDERR", ...)` / `.replace(". `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself.", ".")`. Cursor globally replaces `TOOL_MODIFIED_HISTORY` and `TOOL_COMMIT_STDERR`. Wrapping guard 2 across lines, rewording the checklist sentence, or dropping those literals lets cursor-only guard 2 prose leak into `agents/codex-implementer.md`, or leaves unreplaced `TOOL_COMMIT_STDERR` while the dispatcher writes `${tool_tag}-commit-stderr.txt` per `python/larch/implement/dispatch_step2.py:603`. `generate --check` can still pass after a full regen.
- **Proposed resolution**: Add explicit byte-stable hooks to Approach step 3 / `### UPDATED: agents/_implementer-base.md`: guard 2 stays one line matching `^2\. \*\*NEVER `git add``; keep literal `TOOL_COMMIT_STDERR`; keep the checklist sentence `` `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself. `` verbatim. After regen, verify codex guard 2 has no Cursor-only sandbox wording. ### 1. [correctness] `agents/_implementer-base.md:47,136,197`; `python/larch/rendering/_rendering_generators.py:310-312` **Concern:** The plan’s byte-stable inventory covers JSON/jq blocks, status strings, bail tokens, and the PLR0911 pin, but not the substring/line-shape contracts that `_implementer_text()` applies when building Codex/Cursor prompts. **Scenario:** Prose compression that reflows hard guard 2, rephrases the manifest-checklist `TOOL_MODIFIED_HISTORY` line, or renames the `TOOL_COMMIT_STDERR` placeholder will not fail manifest/jq harnesses, yet regenerated `agents/codex-implementer.md` can retain cursor-biased guard 2 text or wrong commit-stderr filenames relative to the dispatcher’s `${tool_tag}-commit-stderr.txt` contract. **Suggested revision:** Extend the plan’s immutable-surface list with those generator hooks and a post-regen codex guard-2 sanity check (no Cursor-only sandbox prose).
