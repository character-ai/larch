## Goal
Implement issue #6920: [IMPLEMENTING] Drop the following bread-crumbs/report log lines.

## Implementation Plan
## Plan

## Approach

Limit the quiet-authoring change to the Step 5b.5 architecture-diagram sequence.

Suppress only Claude-authored chat narration that announces diagram composition, safe-content reading, candidate writing, validation, or a free-form transition recap. Preserve required `🔶` breadcrumbs, bounded `⚠ 5b.5` **generation-failure-only** warnings, structured outputs, and the required anti-halt blockquote that continues to Step 5c.

Do not add a Step 5b.5 sanitizer pre-check. Step 5c remains the sole authority for sanitization, promotion, skip-marker creation, sanitizer-rejection logging, and candidate cleanup. Keep Claude Code harness-rendered tool lines outside the prompt contract.

## Files to modify/create

### UPDATED: skills/design/SKILL.md

- Add a Step 5b.5-specific quiet-authoring rule for `DIAGRAM_REQUIRED=true`.
- Require direct candidate authoring without Claude-authored lead-ins, safe-content-reading narration, candidate-content descriptions, sanitizer-validation narration, validity recaps, or free-form transition recaps.
- Clarify that Claude Code harness-rendered tool-use lines, such as `Write(...)`, `Wrote N lines`, and shell-command counts, are not controlled by this prompt contract.
- Preserve the required `> **Continue to Step 5c IMMEDIATELY.**` anti-halt blockquote and all existing required breadcrumbs, generation-failure warnings, and Step 2b structured plan output.
- Explicitly prohibit Step 5b.5 from invoking `python3 python/cli.py mermaid sanitize`, `design-step3b-sanitize.sh`, or another sanitizer command before Step 5c.
- Narrow the applicable execution-issues exception so Step 5b.5 may report only bounded diagram-generation failures. Reserve sanitizer-rejection warnings and execution-issue logging for Step 5c publish handling.

### UPDATED: skills/design/references/finalize-step5.md

- Mirror the Step 5b.5-specific quiet-authoring contract in the normative diagram-composition section.
- Forbid Claude-authored prose that announces Mermaid composition, safe-content reading, candidate writing, sanitizer checking, successful validation, or a free-form continuation recap.
- Preserve the existing candidate format, bounded generation-failure warning, optional local generation-failure capture, and the required Step 5c anti-halt continuation.
- Require Step 5b.5 to write the candidate silently and continue directly to Step 5c without a sanitizer pre-check.
- Explicitly forbid `python/cli.py mermaid sanitize`, `design-step3b-sanitize.sh`, pre-Step-5c candidate promotion or rejection, sentinel or diagram-artifact writes, candidate moves or deletion, and `**⚠ 5b.5:` sanitizer warnings.
- Reaffirm that Step 5c alone sanitizes, promotes, skips, logs sanitizer rejection, and writes Step-5c-owned artifacts.

### UPDATED: scripts/test-design-structure.sh

- Add structural assertions for the Step 5b.5-only quiet-authoring contract and the distinction between suppressible Claude-authored prose and uncontrollable harness-rendered tool-use lines.
- Pin preservation of the required `> **Continue to Step 5c IMMEDIATELY.**` anti-halt blockquote while rejecting free-form Step 5b.5 transition recaps.
- Add negative assertions that Step 5b.5 does not invoke `python3 python/cli.py mermaid sanitize`, `design-step3b-sanitize.sh`, or another sanitizer path before Step 5c.
- Add negative assertions that Step 5b.5 does not write `.completed/step-5b.5`, `architecture-diagram.md`, or `architecture-diagram.skipped`, or move or delete the candidate before Step 5c.
- Pin the narrowed execution-issues wording so Step 5b.5 permits generation-failure reporting only and cannot regain sanitizer-rejection warning or logging authority.
- Keep existing assertions for candidate secrecy, Step 5c sanitizer ownership, and immediate continuation.

## Edge cases

- Continue to emit required `🔶` breadcrumbs and bounded `⚠ 5b.5` diagram-generation-failure warnings.
- Preserve the Step 5b.5 anti-halt blockquote to Step 5c. It is required control-flow output, not a forbidden free-form recap.
- Do not suppress the Step 2b `## Implementation Plan` output, voting results, summaries, required operator prompts, or other existing structured output.
- Do not treat ordinary Claude Code tool-use rendering as a prompt-contract failure.
- Step 5b.5 does not validate, sanitize, revise, promote, reject, move, or delete the candidate. Step 5c receives the candidate unchanged and remains authoritative for all publish decisions.

## Failure modes

- Broadening the rule beyond Step 5b.5 could change unrelated `/design` authoring behavior.
- Overbroad quiet-authoring wording could suppress required breadcrumbs, bounded generation-failure warnings, or the anti-halt continuation blockquote.
- Leaving the global execution-issues exception broad could reauthorize Step 5b.5 sanitizer-rejection warnings or pre-Step-5c logging.
- Allowing a Step 5b.5 sanitizer invocation could produce uncontrolled harness noise, wrong-flag probes, or preempt Step 5c’s authoritative publish path.
- Unpinned prompt text could reintroduce narration or pre-Step-5c sanitizer behavior during later refactors.

## Testing strategy

- Run `make test-design-structure`.
- Run the documented lint targets applicable to the changed Markdown and shell surfaces.
- Inspect the final Step 5b.5 prompt text to confirm it distinguishes Claude-authored narration from Claude Code harness output.
- Confirm Step 5b.5 writes the candidate silently, emits only required breadcrumbs or generation-failure warnings plus the anti-halt blockquote, and continues directly to Step 5c.
- Confirm Step 5b.5 contains no sanitizer invocation and that Step 5c remains the sole sanitizer, promote/skip, sanitizer-warning, and cleanup authority.
- Confirm no Bash fences, scripts, Python behavior, sanitizer behavior, or machine-consumed wire grammar changed.

## Acceptance

- Run `make test-design-structure`.
- Run the documented lint targets applicable to the changed Markdown and shell surfaces.
- Inspect the final Step 5b.5 prompt text to confirm it distinguishes Claude-authored narration from Claude Code harness output.
- Confirm Step 5b.5 writes the candidate silently, emits only required breadcrumbs or generation-failure warnings plus the anti-halt blockquote, and continues directly to Step 5c.
- Confirm Step 5b.5 contains no sanitizer invocation and that Step 5c remains the sole sanitizer, promote/skip, sanitizer-warning, and cleanup authority.
- Confirm no Bash fences, scripts, Python behavior, sanitizer behavior, or machine-consumed wire grammar changed.

diff_added: 30
diff_deleted: 4
mechanical_churn: false
diff_lines: 34

## Test plan
(no test plan section in plan-file)
