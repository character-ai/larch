# Summary Comment Template

**Consumer**: `skills/implement/SKILL.md` — when posting slim marker-keyed tracking-issue comments via `scripts/tracking-issue-summary.sh`.

**Contract**: Tracking issue comments use one marker per comment:

```text
<!-- larch:metadata v1 runid=<R> -->
<!-- larch:diagrams v1 runid=<R> -->
<!-- larch:plan v1 runid=<R> -->
<!-- larch:token-report v1 runid=<R> -->
<!-- larch:final-summary v1 runid=<R> -->
```

Large runtime payloads are not embedded in these comments. They are written to
`larch-logs/<skill>/<run-id>/` by `scripts/larch-log.sh` and committed at the
terminal log-flush step.

**When to load**: when editing `/implement` tracking-issue publication steps (Steps 0.5, 1, 9a.1, 11, 18).
