## Goal
Implement issue #4782: [IMPLEMENTING] [port-drift] [BUG] design log-publish tail: restore dropped GitHub-redundant-snapshot exclusions and secret-rotation warning.

## Implementation Plan
## Summary

Two low-severity omissions left by the #3681 design publish/log-publish port (one of them a tail of the #4766 filter restoration): the committed design-log filter does not exclude GitHub-redundant snapshot files, and the publish path no longer surfaces the operator "rotate the exposed credential" warning. Found by the post-#4766 migration-wave audit.

## Root cause and evidence

- **GitHub-redundant snapshots not excluded.** `python/design_log_publish_flow.py::_publish_excluded` (the restored port of the old `design_artifact_excluded`) does not list `issue-body.txt`, `issue.json`, `architecture-diagram.md`, or `panel-manifest.ndjson`. The old bash filter excluded these (Phase 3d / #3721 and #3929) because they duplicate the GitHub issue body and the `larch:diagrams` comment. They are NOT the ambiguous human-readable duplicates the #4766 fix deliberately chose to keep (`findings.md`, `voting-tally.md`, `round-meta.json`), so they appear to be an unaddressed remainder. Impact: a few KB of redundant files per committed design run (avg ~1.5-4.8 KB each), far below the raw-carrier bloat #4766 fixed.
- **Secret-rotation warning dropped.** The recovered `design-publish.sh` parsed `SECRET_SCRUB_VIOLATIONS=` from the log-publish output and emitted the "a credential was almost certainly exposed; ROTATE it now" operator warning. The Python publish path ignores it. The scrubbing itself still happens (no secret leak), but the operator is no longer told to rotate.

## Affected files

- `python/design_log_publish_flow.py` (`_publish_excluded` exclusion lists; `SECRET_SCRUB_VIOLATIONS` surfacing).
- `python/design_publish.py` (whichever publish tail consumes the log-publish KV output).
- `python/test_design_log_publish_flow.py` / `python/test_design_publish.py`.

## Suggested fix

Add `issue-body.txt`, `issue.json`, `architecture-diagram.md`, and `panel-manifest.ndjson` to the design log-publish exclusion set (top-level only if needed to avoid touching curated subtree copies), and re-surface `SECRET_SCRUB_VIOLATIONS` as an operator-facing rotate warning on the publish path. Add tests for both.

## Related

Tail of #4766 (the design-log filter restoration that fixed the ~40x committed-log bloat); this covers the small residual exclusions that fix deliberately deferred, plus the operator rotate-warning. Same publish surface as the architecture-diagram-upsert regression.

## Test plan
(no test plan section in plan-file)
