## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Capture one sanitized diagnostic at the assessment boundary. Reuse it across the unavailable receipt, outcome sidecar, ship handoff, and operator prompt.

Keep `DETAIL=invariants,guidelines` unchanged for routing. Add `ASSESSMENT_UNAVAILABLE_DETAIL` as an additive handoff field.

Register the shared sanitizer through `python/cli.py` so the Step 8 Bash adapter invokes supported Python-owned redaction logic.

Capture child stderr in the Step 8 adapter. Install fail-closed cleanup immediately when its raw-stderr file is created, then redact, flatten, and bound it before writing `ASSESSMENT_CHILD_DETAIL` to the merge-result envelope. Never persist raw stderr.

## Files to modify/create

### UPDATED: python/larch/implement/architectural_assessment.py

- Compute `_safe_detail()` once in `_persist_unavailable`.
- Pass that safe value through `_write_outcome` into the existing gate-result `detail` field.
- Write the same value to the unavailable receipt.
- Keep successful assessment outcomes unchanged.
- Expose or reuse a Python-owned sanitizer entry point suitable for CLI use, including redaction, tmpdir replacement, control-character flattening, and bounded output.

### UPDATED: python/larch/cli.py

- Register an `architectural-assessment sanitize-detail` command, or equivalent scoped subcommand, that invokes the shared sanitizer.
- Accept diagnostic input through a documented non-argument transport that does not expose raw stderr in process arguments.
- Emit exactly one sanitized, newline-free diagnostic value on stdout and no additional stdout rows.
- Return nonzero on invalid invocation so the Step 8 adapter can fail closed without forwarding raw input.

### UPDATED: python/larch/implement/ship_guidelines.py

- Add a narrow reader that accepts unavailable diagnostic detail only from a regular, valid outcome sidecar.
- Require `reason=unavailable`, matching kind, `head_sha`, and `base_ref`.
- Keep prior outcome shapes with missing or empty `detail` valid.
- Populate unavailable gate results with the validated detail before the gate rewrites the sidecar.

### UPDATED: python/larch/implement/ship.py

- Preserve validated unavailable detail while refreshing invariant and guideline outcome sidecars.
- Keep `needs_user_reason=architectural-assessment-unavailable`.
- Keep `ShipResult.detail` as the existing canonical kind list.
- Do not change violation, genuine dropped-outcome, or reassessment routing.

### UPDATED: python/larch/implement/dispatch_ship.py

- For `architectural-assessment-unavailable`, read the current validated outcome sidecars for the listed kinds.
- Add a bounded, single-line `ASSESSMENT_UNAVAILABLE_DETAIL` to `.ship-route-exit-handoff.env`.
- Label per-kind diagnostics when they differ. Avoid duplicate text when both kinds share one failure.
- Preserve `DETAIL` and `DETAIL_FILE` semantics for all existing consumers.
- Omit the new field when an older or invalid outcome has no trustworthy diagnostic.

### UPDATED: skills/implement/scripts/step-8-assessment.sh

- Capture the child command’s stderr in a safe raw file under `$IMPLEMENT_TMPDIR`.
- Immediately install a trap or equivalent cleanup mechanism after creating that file, covering normal completion, malformed child output, sanitizer failure, merge-result write failure, shell error exits, signals, and interruption paths.
- Ensure cleanup removes the raw file before every adapter exit and does not mask the adapter’s intended terminal status.
- Sanitize the raw file only through `python3 python/cli.py architectural-assessment sanitize-detail`.
- Forward only the successful bounded result as `ASSESSMENT_CHILD_DETAIL` in merge and terminal result envelopes.
- Preserve the value across fail-closed and retry handling where it describes the terminal attempt.
- Keep the current stdout grammar and success validation intact.

### UPDATED: skills/implement/scripts/test-step-8-assessment.sh

- Cover child stderr capture, merge-result forwarding, retry replacement, and fail-closed preservation.
- Assert cleanup removes raw-stderr files after successful execution, malformed output, sanitizer failure, merge-write failure, and interrupted/error exit paths.
- Assert secrets, tmpdir paths, newlines, and overlong input cannot escape through `ASSESSMENT_CHILD_DETAIL`.
- Assert normal successful runs retain their existing required KVs.

### UPDATED: skills/implement/scripts/step-8-assessment.md

- Document the optional `ASSESSMENT_CHILD_DETAIL` field and its redacted, bounded contract.
- Document the supported `python3 python/cli.py architectural-assessment sanitize-detail` invocation and its single-line stdout contract.
- State that raw child stderr is never a merge-result value or committed artifact, and is removed on all adapter exit paths.

### UPDATED: skills/implement/SKILL.md

- Make the unavailable operator-bail prompt read `ASSESSMENT_UNAVAILABLE_DETAIL`.
- Show the diagnostic with the affected kind list so the operator can choose retry, investigation, or manual continuation.
- Remove the stale instruction to surface an unavailable receipt from the committed run log.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

- Add `ASSESSMENT_UNAVAILABLE_DETAIL` to the operator-bail handoff contract.
- Require the prompt to surface it only for `architectural-assessment-unavailable`.
- Preserve compatibility when historical outcomes lack detail.

### UPDATED: docs/run-logs.md

- Clarify that unavailable invariant and guideline outcomes carry a redacted diagnostic in `detail`.
- Note that historical outcome files may have an empty detail field.

### UPDATED: python/tests/implement/test_architectural_assessment.py

- Verify `_persist_unavailable` writes the same sanitized diagnostic to receipt and outcome.
- Cover empty stdout, nonzero launcher stderr, secret redaction, tmpdir replacement, newline flattening, and truncation.
- Confirm receipt behavior remains unchanged.

### UPDATED: python/tests/implement/test_ship.py

- Verify valid unavailable details survive gate reload and outcome refresh.
- Cover both assessment kinds.
- Reject stale HEAD/base, malformed, wrong-reason, symlinked, and non-regular sidecars as diagnostic sources.
- Confirm the existing reason token, kind-list detail, violation priority, and genuine dropped-outcome behavior remain stable.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Verify route-exit preserves `DETAIL=invariants,guidelines` and adds `ASSESSMENT_UNAVAILABLE_DETAIL`.
- Cover one kind, two distinct diagnostics, duplicate diagnostics, legacy empty detail, and hostile multiline input.
- Confirm unrelated operator-bail reasons do not gain the new field.

### UPDATED: python/tests/test_cli.py

- Verify the registered sanitizer command reaches the shared sanitizer.
- Assert its stdout is one newline-free sanitized value with no additional protocol output.
- Cover invalid invocation and sanitizer failure behavior without exposing raw diagnostic input.

## Edge cases

- Both kinds may fail for the same launcher error.
- One kind may have a valid diagnostic while the other has an old or invalid outcome.
- Historical outcomes may omit or empty `detail`.
- A stale outcome may describe a prior HEAD or base.
- Diagnostics may contain secrets, tmpdir paths, control characters, or newlines.
- Child stderr may be empty even when the coordinator records an unavailable result.
- The adapter may exit after raw-stderr creation but before sanitization or merge-result publication.

## Failure modes

- Fail closed rather than trusting a stale or malformed outcome sidecar.
- Do not replace the canonical kind list with diagnostic prose.
- Do not let stderr forge extra `KEY=value` rows.
- Do not commit raw stderr or unsanitized exceptions.
- Remove raw stderr on every adapter exit path, including sanitizer and envelope-write failures.
- Do not turn missing legacy detail into a new ship failure.

## Testing strategy

Run only changed-file checks:

- `python3 -m pytest python/tests/implement/test_architectural_assessment.py`
- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/test_cli.py`
- `bash skills/implement/scripts/test-step-8-assessment.sh`
- Relevant Python lint and type checks for the changed Python modules.
- Relevant Bash, Bash 3.2, and shellcheck targets for `step-8-assessment.sh` and its harness.
- Markdown lint for the changed skill and documentation files.

Confidence: high. The existing outcome and routing paths provide the handoff points; the revision makes the Bash-to-Python sanitizer contract explicit and closes raw-stderr cleanup on all exit paths.

difficulty: HARD
diff_lines: 410
