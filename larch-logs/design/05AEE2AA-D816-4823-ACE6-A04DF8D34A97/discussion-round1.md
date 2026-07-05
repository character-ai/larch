## Decision 1: Unified severity naming (top tier)
- **Question**: What to name the top tier of the unified 3-level severity scale (the tier that gates OOS filing via HIGH_SEVERITIES and marks stop-ship in-scope findings)?
- **Resolution**: `major` > `minor` > `nit`. `JudgeSeverity` becomes `{major, minor, nit}` (drop `blocker`, `uncertain`). `HIGH_SEVERITIES` becomes `{major}`. `major` absorbs old `blocker`; `nit` absorbs old `latent`/`trivial`.
- **Source**: user

## Decision 2: Emit-cut scope (binding constraint from issue)
- **Question**: Does the reviewer emit-cut (major/minor only, never nit) and the mechanical nit-filter apply to in-scope findings or OOS only?
- **Resolution**: BOTH in-scope and OOS reviewer output (issue point 2 + point 3 are explicit). Reviewers never emit `nit`; a mechanical pre-aggregator filter deterministically drops any `nit` that slips through, for both scopes.
- **Source**: codebase/issue (converged)

## Decision 3: OOS file gate (binding constraint from issue)
- **Question**: What is the OOS filing gate?
- **Resolution**: File an OOS item only if (a) the panel accepts it at the active voting tier (keep existing degraded thresholds 1/1, 1+/2, 2+/3) AND (b) a strict majority of YES voters rate it `major`. Not a hard 2+ floor. Accepted-but-`minor`, rejected, and neutral OOS are logged/flushed, never filed. In-scope filing/points are unchanged in gate logic (only the severity vocabulary changes).
- **Source**: codebase/issue (converged)

## Decision 4: Report visibility + audit retention (binding constraint from issue)
- **Question**: What happens to rejected/logged OOS in the human report, and to mechanically-dropped nits?
- **Resolution**: Stop rendering the `## Rejected OOS audit` section in the human summary (only filed OOS appears). KEEP all underlying audit data (`round-*/oos.md`, classification TSV) for `/fluff-analysis`, `/rejected-analysis`, `/voter-calibration`. Mechanically-dropped nits are silent to the report but retain an audit lineage (`oos-dropped-before-vote.md`).
- **Source**: codebase/issue (converged)

## Decision 5: Reconciliation with #6028 (hard constraint)
- **Question**: How does the silent nit-drop reconcile with #6028 ("OOS-dropped real findings have no filing path"), which is CLOSED/DONE?
- **Resolution**: #6028's fix routed all OOS candidates through voting+filing (removed pre-vote drops; retired `oos-dropped-before-vote.md` producers). #6421 re-introduces a NARROW pre-vote drop for `nit` only, with the source-drop-is-unrecoverable tradeoff explicitly accepted for token savings. The major/minor filing path #6028 established must NOT regress — only nits are cut at source.
- **Source**: user-accepted tradeoff (issue) + codebase
