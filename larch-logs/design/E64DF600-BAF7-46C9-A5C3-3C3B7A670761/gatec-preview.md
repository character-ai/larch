## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Extend the existing Step 8 note and outcome contracts in place. Keep inline assessment authoring and dispatch unchanged.

1. Define shared note-state and outcome-reason constants.
2. Classify a changed path as clearly out of scope only when it is under `larch-logs/` or is a Markdown file under `docs/`; inspect both sides of renames.
3. Store separate authored-input and covered-input fingerprints. Preserve `DIFF_FINGERPRINT` for compatibility.
4. On HEAD drift, determine whether coverage can advance by diffing the durable prior `HEAD_SHA` against the current HEAD, not by replaying the base diff or diffing from an input fingerprint. Advance only after every incremental path is clearly out of scope, then re-materialize the complete base-to-current-HEAD diff and atomically refresh its snapshot, covered identity, and `HEAD_SHA`.
5. Add deterministic-clean and unavailable note materialization paths with explicit `NOTE_STATE`.
6. Validate live inputs before consuming or advancing persisted state, including when recorded `HEAD_SHA` matches. Treat Git errors, malformed paths, stale or missing identities, symlinks, and non-regular files as unsafe.
7. Map note states to existing schema-version-1 outcomes. Preserve blocking invariant violations when later assessment input is unavailable.
8. Extend the owning outcome validators in `architectural_guidelines.py`, then document the additive metadata and outcome semantics.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add canonical `Final` constants for:
  - `NOTE_STATE_AUTHORED`
  - `NOTE_STATE_DETERMINISTIC_CLEAN`
  - `NOTE_STATE_UNAVAILABLE`
  - `REASON_DETERMINISTIC_CLEAN`
  - `REASON_UNAVAILABLE`
- Build any note-state token set from these constants so writers and validators share one source.
- Do not add new outcome `assessment_kind` values or change unrelated wire tokens.

### UPDATED: python/larch/core/architectural_guidelines.py

- Add a conservative `_path_out_of_scope(path)` classifier.
  - Accept only normalized repo-relative paths under `larch-logs/`.
  - Accept only `.md` files recursively under `docs/`.
  - Treat root Markdown, code, knowledge files, empty paths, absolute paths, traversal-like paths, malformed Git output, and all other paths as intersecting.
- Replace the log-only HEAD-change rule with a shared incremental path check that uses the classifier for both guideline and invariant notes.
  - Use the `HEAD_SHA` persisted with the currently covered input as the old revision.
  - On HEAD drift, run a rename-safe incremental command equivalent to `git diff --no-renames --name-only -z <stored HEAD_SHA>..<current HEAD>`.
  - Do not diff from the base reference, an authored fingerprint, a covered fingerprint, or a previously materialized full diff when deciding which paths are newly introduced by drift.
  - Classify every returned path, including both delete and add paths produced by rename suppression.
  - Return a safe result only when Git succeeds, reports at least one unambiguous path, and every path is clearly out of scope.
  - Treat Git launch errors, nonzero exits, undecodable or ambiguous output, empty results, an invalid stored or current revision, and invalid NUL-delimited path records as unsafe.
- Extend durable note metadata with:
  - `NOTE_STATE`
  - `AUTHORED_DIFF_FINGERPRINT`
  - `COVERED_DIFF_FINGERPRINT`
- Keep `DIFF_FINGERPRINT` readable and writable as the prior-format compatibility field.
  - For old metadata, interpret a valid non-empty `DIFF_FINGERPRINT` as both authored and covered identity.
  - Treat a missing `NOTE_STATE` on a valid old note as `authored`.
  - Treat missing or empty required identities as unconsumable rather than implicitly clean.
- Update guideline and invariant note writers to preserve distinct identities.
  - Authored notes pin the authoring input and initial covered input to the same validated full-diff fingerprint, snapshot, and `HEAD_SHA`.
  - Deterministic-clean notes record the validated full input as both authored and covered identity while retaining their distinct note state.
  - Later safe increments update only the covered fingerprint, full-diff snapshot metadata, and recorded `HEAD_SHA`.
  - Never rewrite the authored fingerprint during mechanical coverage advancement.
- Add focused helpers for deterministic-clean and unavailable notes.
  - Write regular durable artifacts through the existing atomic helpers.
  - Record the correct `NOTE_STATE`, fingerprints where a validated input exists, base reference, status, and assessment kind.
  - Use deterministic fixed prose rather than model-authored assessment text.
  - Ensure unavailable artifacts represent failed or unsafe assessment input without claiming deterministic cleanliness.
  - Do not synthesize a covered identity or snapshot for unavailable input that could not be fully materialized and validated.
- Add a shared incremental coverage advancement helper for guideline and invariant artifacts.
  - Resolve persisted identities with the explicit prior-format fallback before attempting advancement.
  - Require a valid persisted `HEAD_SHA`, base reference, covered fingerprint, and snapshot record for an artifact that is eligible for reuse.
  - Validate that the persisted snapshot is a regular file, its bytes produce the persisted covered fingerprint, and it still represents the stored base-to-stored-HEAD input before treating the prior state as advanceable.
  - Resolve the current HEAD and, only when it differs from the stored `HEAD_SHA`, run the rename-safe incremental path check from `<stored HEAD_SHA>` to `<current HEAD>`.
  - After every incremental path passes the narrow out-of-scope classifier, re-materialize the **complete** implementation diff from the persisted base reference to the current HEAD.
  - Validate the new materialized diff, compute its full-diff fingerprint, and refresh the durable snapshot contents and `DIFF_SNAPSHOT` metadata from that complete current input.
  - Set `COVERED_DIFF_FINGERPRINT` to the newly materialized full base-to-current-HEAD fingerprint; do not derive it from the incremental path list and do not retain the former fingerprint after snapshot replacement.
  - Atomically persist the refreshed snapshot reference or contents, covered fingerprint, compatibility `DIFF_FINGERPRINT` where applicable, current coverage metadata, and current `HEAD_SHA` only after the complete validation succeeds.
  - Keep `AUTHORED_DIFF_FINGERPRINT` unchanged during this transaction.
  - Leave durable state unchanged and require assessment when an increment intersects scope or cannot be proven safe.
- Wire incremental advancement into `note_consumable`, `invariant_note_consumable`, and any shared compose precheck path that determines whether an existing note may be reused.
  - Do not return consumable solely because `HEAD_SHA` matches.
  - Resolve and require a non-empty covered identity, validate the corresponding full live base-to-HEAD input and snapshot, and run the covered-fingerprint freshness check before returning consumable.
  - On HEAD drift, attempt safe coverage advancement before declaring the note stale or requiring assessment.
  - After successful advancement, re-read or validate the persisted metadata, refreshed snapshot, and full current materialized input; compare the live full-diff fingerprint with `COVERED_DIFF_FINGERPRINT` before returning consumable.
  - On an intersecting, malformed, failed, or unprovable increment, leave the note and snapshot unchanged and return the existing reassessment-required result.
- Update note consumption and fingerprint-staleness checks to compare the live complete base-to-current-HEAD input with `COVERED_DIFF_FINGERPRINT`.
  - Reject mismatched or missing required covered identities.
  - Require an authored identity for new-format authored records and apply the explicit valid-prior-format fallback for legacy records.
  - Do not silently accept stale authored or covered results.
- Validate every materialization input at use time.
  - Reject symlinks, directories, missing files, and other non-regular inputs.
  - Reject a snapshot whose content fingerprint does not match its declared covered fingerprint.
  - Reject a snapshot or materialized full diff that does not match the declared base and HEAD identities.
  - Reject HEAD or base identity drift before persisting or consuming the result.
- Extend `validate_guideline_ship_outcome_record` and `validate_invariant_ship_outcome_record`, which own schema-version-1 outcome validation.
  - Accept the existing authored combinations unchanged.
  - Accept `clean` with reason `deterministic-clean` and the existing clean assessment kind.
  - Accept the existing non-violation fallback status with reason `unavailable` and an empty assessment kind.
  - Reject `unavailable` paired with a violation status or non-empty assessment kind.
  - Reject `deterministic-clean` paired with deviation or violation statuses, or a non-clean assessment kind.
  - Continue rejecting unknown reasons, inconsistent assessment kinds, malformed statuses, and invalid outcome combinations.
- Apply the same state, identity, advancement, snapshot-refresh, and validation rules to guideline and invariant artifacts through shared helpers where practical.
- Keep `prepare_compose_assessment`, `prepare_invariant_compose_assessment`, and their current callers on the existing inline route.

### UPDATED: python/larch/implement/ship_guidelines.py

- Add `REASON_DETERMINISTIC_CLEAN` and `REASON_UNAVAILABLE` to the guideline and invariant reason-token sets using the config constants.
- Read `NOTE_STATE` from durable metadata when producing gate results.
- Classify schema-version-1 outcomes without adding fields or new `assessment_kind` values:
  - `authored`: preserve existing clean, pinned deviation, and violation behavior.
  - `deterministic-clean`: emit `clean` with reason `deterministic-clean` and the existing clean assessment kind.
  - `unavailable`: emit the existing non-violation fallback outcome with reason `unavailable` and an empty assessment kind.
- Make invariant classification precedence explicit.
  - A valid authored violation remains `violation`.
  - An unavailable state by itself is never a violation.
  - An unavailable refresh or fallback must not overwrite or downgrade an already valid violation result.
- Leave schema-version-1 record-combination validation in `python/larch/core/architectural_guidelines.py`; this module supplies classification and reason-token inputs to those validators.
- Keep Step 8 route behavior unchanged. Do not add bgjob dispatch expectations.

### UPDATED: python/tests/core/test_architectural_guidelines.py

- Add table-driven path-classification coverage for:
  - nested and top-level `larch-logs/` paths;
  - nested and top-level Markdown files under `docs/`;
  - non-Markdown files under `docs/`;
  - root Markdown and architecture knowledge files;
  - code paths, ambiguous paths, absolute paths, traversal-like paths, and empty input.
- Extend incremental HEAD-change tests to prove:
  - docs-only Markdown and log-only increments are safe;
  - the incremental Git comparison is from the persisted `HEAD_SHA` to current HEAD, not from the base reference or a materialized full diff;
  - mixed safe and intersecting paths require reassessment;
  - a code or knowledge-file rename into `docs/**/*.md` or `larch-logs/**` is treated as intersecting because both old and new paths are checked;
  - Git errors, nonzero exits, malformed output, invalid NUL-delimited records, invalid revisions, and empty output fail closed.
- Test consumption-integrated coverage advancement for both guideline and invariant notes.
  - A safe docs-only or log-only HEAD advance re-materializes the full base-to-current-HEAD diff, atomically updates the snapshot and `DIFF_SNAPSHOT`, updates `COVERED_DIFF_FINGERPRINT` and `HEAD_SHA`, then remains consumable without reassessment.
  - Assert that the refreshed snapshot bytes fingerprint to the new covered identity and match the live full base-to-current-HEAD materialization.
  - A chained sequence of assessed input, docs-only advance, then log-only advance preserves the authored fingerprint while advancing only the covered fingerprint, snapshot, and HEAD identity.
  - Assert the second advance compares the first advance's persisted `HEAD_SHA` to the new current HEAD, and that the covered fingerprint reflects the complete accumulated base-to-current-HEAD diff rather than only the second increment.
  - An intersecting or failed advance changes neither identity, snapshot, `DIFF_SNAPSHOT`, nor `HEAD_SHA` and requires reassessment.
  - Shared compose precheck callers observe the same reuse result rather than bypassing advancement.
- Test authored and covered fingerprint separation.
  - Initial authored writes set both identities.
  - Deterministic-clean writes set valid initial identities with the deterministic-clean state.
  - Safe advancement changes only covered identity and the associated full-diff snapshot metadata.
  - Intersecting or failed advancement changes neither identity nor snapshot state.
- Test fail-closed consumption checks even when `HEAD_SHA` matches.
  - Missing or empty covered identity is unconsumable.
  - Missing required authored identity in new-format authored metadata is unconsumable.
  - A missing, symlinked, directory, malformed, or fingerprint-mismatched persisted snapshot is unconsumable.
  - Valid prior-format metadata with a non-empty `DIFF_FINGERPRINT` resolves both identities and remains readable.
  - Stale old notes and old notes without sufficient identity require reassessment.
- Test stale-input rejection for mismatched HEAD, base, snapshot content, authored fingerprint, and covered fingerprint.
- Test rejection of missing, symlinked, directory, and other non-regular materialization inputs.
- Add deterministic-clean and unavailable note tests for both guideline and invariant artifacts.
- Add validator tests for `validate_guideline_ship_outcome_record` and `validate_invariant_ship_outcome_record`.
  - Accept deterministic-clean clean outcomes and unavailable non-violation outcomes.
  - Preserve all prior valid schema-version-1 records.
  - Reject unavailable violations, unavailable non-empty assessment kinds, and deterministic-clean deviation or violation combinations.
- Preserve existing tests for inline compose materialization and staged-note compatibility.

### UPDATED: python/tests/implement/test_ship.py

- Test guideline outcome classification for authored, deterministic-clean, and unavailable states under schema version `1`.
- Test invariant outcome classification for the same states.
- Verify unavailable produces no violation classification and uses an empty assessment kind.
- Verify a valid invariant violation takes precedence over an unavailable fallback and cannot be erased.
- Keep classification-facing validator integration coverage for:
  - accepted new reason combinations;
  - prior valid outcome records;
  - rejection of unavailable paired with violation;
  - rejection of deterministic-clean paired with deviation or violation;
  - unknown state, reason, and assessment-kind combinations.
- Keep Step 8 route assertions unchanged. Do not add bgjob dispatch expectations.

### UPDATED: docs/run-logs.md

- Document `authored`, `deterministic-clean`, and `unavailable` note states.
- Explain the difference between authored-input and covered-input fingerprints.
- State that coverage advancement compares the stored covered `HEAD_SHA` with current HEAD, then advances only across proven `larch-logs/**` or `docs/**/*.md` increments, with rename-safe path inspection that cannot omit a source path.
- Explain that a successful safe increment refreshes the complete base-to-current-HEAD materialized diff, snapshot metadata, covered fingerprint, and HEAD identity together, while preserving the authored fingerprint.
- Document that consumption validates identities and materialized inputs even when the recorded HEAD matches the current HEAD.
- Document fail-closed stale-input, snapshot-mismatch, and unsafe-materialization behavior.
- Explain prior metadata compatibility and when reassessment is required.
- Clarify that unavailable is non-violating and cannot replace a recorded invariant violation.

### UPDATED: docs/run-log-batches.md

- Extend the schema-version-1 outcome documentation with the `deterministic-clean` and `unavailable` reason tokens.
- Record the valid outcome, reason, and `assessment_kind` combinations for guidelines and invariants.
- State that the schema remains version `1` and historical records remain valid.
- Document that unavailable must use the existing non-violation fallback with an empty assessment kind.
- Note invariant precedence: violations stay blocking, while unavailable remains a non-violation fallback.

## Edge cases

- A diff contains both `docs/guide.md` and a code path. Treat the increment as intersecting.
- A code or knowledge file is renamed into `docs/guide.md` or `larch-logs/run.md`. Treat the increment as intersecting because the old path is also examined.
- A path is `README.md`, `ARCHITECTURAL_GUIDELINES.md`, or `ARCHITECTURAL_INVARIANTS.md`. Treat it as intersecting.
- A path is under `docs/` but does not end in `.md`. Treat it as intersecting.
- Git returns no paths for distinct stored and current HEAD revisions. Do not infer safety.
- The stored `HEAD_SHA` is invalid, missing, or no longer resolvable. Do not infer safety or compute an incremental diff from base instead; require reassessment.
- A safe incremental path list is followed by a failure to materialize, validate, fingerprint, or atomically persist the complete current base-to-HEAD diff. Leave the prior artifact unchanged and require reassessment.
- The note sidecar is old but internally valid. Derive both identities from its non-empty `DIFF_FINGERPRINT`.
- The old sidecar lacks enough identity to prove freshness. Require reassessment.
- A current-HEAD note lacks a required covered fingerprint or aligned regular snapshot. Do not consume it.
- The durable note is readable but its metadata, snapshot, or fingerprint is stale. Do not consume it.
- A deterministic-clean note later gains an intersecting increment. Require authored assessment.
- An unavailable state follows an existing invariant violation. Preserve the violation.
- Artifact paths change type or become symlinks between checks. Revalidate at use time and fail closed.

## Failure modes

- Over-broad classification could skip a required architectural assessment. Keep the allowlist narrow, use rename-safe diff enumeration from stored HEAD to current HEAD, and table-test ambiguous paths.
- Comparing the incremental path check from base instead of stored HEAD could treat pre-assessment scope changes as new drift or misclassify the once-per-run reuse boundary. Require the persisted `HEAD_SHA` range explicitly.
- Updating the authored fingerprint during incremental advancement could falsely claim model coverage. Assert identity separation in tests.
- Updating only `COVERED_DIFF_FINGERPRINT` after safe drift while retaining the old snapshot could leave consumption internally inconsistent. Re-materialize the full current diff and atomically refresh snapshot, snapshot metadata, covered fingerprint, and HEAD identity.
- Leaving advancement disconnected from consumption would force unnecessary reassessment after safe commits. Exercise consumable and compose-precheck integration paths.
- A HEAD-match shortcut, stale snapshot, or empty fingerprint could accept unproven coverage. Require resolved identities and live validation on every consumption path.
- Strict new readers could invalidate historical runs. Centralize prior-format fallback and test legacy fixtures.
- Tolerant outcome handling could downgrade a blocking invariant violation. Encode and test violation precedence.
- A failed Git or file read could be mistaken for clean input. Map uncertainty to intersecting or unavailable, never deterministic-clean.
- Partial metadata or snapshot writes could leave inconsistent identities. Use the existing atomic write helpers and validate the complete refreshed record before consumption.

## Testing strategy

- Run the changed core test module:
  - `python3 -m pytest python/tests/core/test_architectural_guidelines.py`
- Run the changed ship test module:
  - `python3 -m pytest python/tests/implement/test_ship.py`
- Run lint and type checks only for the changed Python files, using the targets documented in `docs/linting.md`.
- Run documentation lint for `docs/run-logs.md` and `docs/run-log-batches.md`.
- Confirm no test or production change touches `dispatch_step18.py` or alters the current Step 8 dispatch and inline authoring path.

difficulty: HARD
diff_lines: 735
