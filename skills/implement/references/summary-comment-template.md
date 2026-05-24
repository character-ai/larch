# Summary Comment Template

**Consumer**: `skills/implement/SKILL.md` — when posting slim marker-keyed tracking-issue comments via `scripts/tracking-issue-summary.sh`.

**Contract**: Tracking issue comments use one marker per comment:

```text
<!-- larch:metadata v1 runid=<R> -->
<!-- larch:diagrams v1 runid=<R> -->
<!-- larch:plan v1 runid=<R> -->
<!-- larch:final-summary v1 runid=<R> -->
```

The `larch:final-summary` body is rich markdown produced by
`scripts/render-run-summary.sh`: it opens with a `## /…` header and bullet lines,
then emits the `<!-- larch:run-summary v=1 -->` sentinel **before** any optional
note lines from `--note-lines-file` (sentinel is the last line of the
standardized block, not the first line of the file).
`/implement` and `/design` share the same `larch:final-summary` marker family; the
`runid=` segment disambiguates concurrent runs on one tracking issue.
`/implement` uses this renderer for the committed
`final-summary.md` projection and the GitHub upsert payload (`summary-final.md` for implement; `skills/design/scripts/render-final-summary.sh` owns the `/design` gather + upsert path).

Large runtime payloads are not embedded in these comments. They are written to
`larch-logs/<skill>/<run-id>/` by `scripts/larch-log.sh` and committed at the
terminal log-flush step. **Exception**: `larch:diagrams` embeds diagram bodies
directly (Architecture + Code Flow); diagrams are not written as a larch-log
batch.

**When to load**: when editing `/implement` tracking-issue publication steps (Step 0 tracking + plan materialization tail, 9a.1, 11, 18).
