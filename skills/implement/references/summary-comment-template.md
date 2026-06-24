# Summary Comment Template

**Consumer**: script-owned `/implement` tracking-issue publication surfaces that post slim marker-keyed comments via `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary`.

**Contract**: Tracking issue comments use one marker per comment:

```text
<!-- larch:metadata v1 runid=<R> -->
<!-- larch:diagrams v1 -->
<!-- larch:plan v1 runid=<R> -->
<!-- larch:final-summary v1 runid=<R> -->
```

`larch:diagrams` is the only marker that intentionally omits `runid=`. It is
issue-scoped rather than run-scoped, jointly written by `/design` (Architecture)
and `/implement` (Code Flow). All other markers remain run-scoped.

The `larch:final-summary` body is rich markdown produced by
`python/cli.py render run-summary`: it opens with a `## /…` header and bullet lines,
including optional `- Emergency: true` when `/implement --emergency` was
requested, then emits the `<!-- larch:run-summary v=1 -->` sentinel **before** any optional
note lines from `--note-lines-file` (sentinel is the last line of the
standardized block, not the first line of the file).
`/implement` and `/design` share the same `larch:final-summary` marker family; the
`runid=` segment disambiguates concurrent runs on one tracking issue.
`/implement` uses this renderer for the committed
`final-summary.md` projection and the GitHub upsert payload (`summary-final.md` for implement; `python/cli.py design render-final-summary` owns the `/design` gather + upsert path).

Large runtime payloads are not embedded in these comments. They are written to
`larch-logs/<skill>/<run-id>/` by `python/cli.py run-log` and committed at the
terminal log-flush step. **Exception**: `larch:diagrams` embeds diagram bodies
directly in the shared issue comment; diagrams are not written as a larch-log
batch. `/design` owns the Architecture section and `/implement` owns the Code
Flow section.

The `larch:metadata` body may include `Emergency: true` when the run was started
with `/implement --emergency`; the line is omitted when false.

**When to load**: orchestrator prompt-side composition does not load this reference on normal runs. Load it when editing script-owned tracking-issue publication surfaces: `post-tracking-issue.sh`, `python/cli.py execution-issues refresh` (the Step 8+ `execution-issues refresh` fence), and `python/cli.py final-report write` / Step 16-17 final-report paths.
