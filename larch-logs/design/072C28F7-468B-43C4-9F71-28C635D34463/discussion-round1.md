## Decision 1: Scope of hardening layers to mirror
- **Question**: Which of the 5 plan-review hardening layers should the render-cache block adopt?
- **Resolution**: Layers (c) tree-wide `find -type l` reject and (d) per-file `[[ -L $f ]]` recheck before staging only. No filename allowlist — render-cache content is variable-schema (cached prompt outputs).
- **Source**: user

## Decision 2: Test coverage scope
- **Question**: How should test coverage expand for the new render-cache hardening?
- **Resolution**: Add 3 test cases mirroring plan-review: render-cache root symlink, render-cache mid-tree symlink, render-cache symlink race (find→stage window). Reuse the existing `make_find_symlink_race_stub` helper.
- **Source**: user

## Decision 3: Error contract for new reject paths
- **Question**: Should the new failure paths use the same `larch_err` + `emit_publish_result false` + `exit 0` pattern as plan-review?
- **Resolution**: Yes — symmetry with plan-review is the explicit ask in the issue body.
- **Source**: codebase (scripts/design-log-publish.sh lines 305-310, 336-340 establish the canonical reject pattern)

## Decision 4: Backward compatibility — happy-path test
- **Question**: Must the existing happy-path render-cache test (test-design-log-publish.sh line 197+, creates `render-cache/nested/c.txt` with no symlinks) keep passing?
- **Resolution**: Yes. The hardening only rejects symlinks, not regular nested files. Existing happy-path coverage continues to pass.
- **Source**: codebase (no symlinks in happy-path test fixture)

## Decision 5: Backward compatibility — suffix denylist
- **Question**: Must the existing suffix denylist (`.sidecar`, `.events.jsonl`) keep working for render-cache?
- **Resolution**: Yes — handled by `design_publish_stage_file` independently of the staging-walk guards being added.
- **Source**: codebase (test-design-log-publish.sh lines 215-216, 248-249)
