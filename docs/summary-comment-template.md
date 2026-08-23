# Summary Comment Template Contributor Notes

**Purpose**: Contributor documentation for `/implement` tracking-issue publication surfaces that post slim marker-keyed comments through the shared Rust tracking owner.

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

The `/implement` `larch:final-summary` body is rich markdown produced by Rust
`final-report write`; it opens with a `## /…` header and bullet lines, including
optional `- Force: true` when `/implement --force` was requested, then emits
the `<!-- larch:run-summary v=1 -->` sentinel **before** any optional note
lines from `--note-lines-file` (sentinel is the last line of the standardized
block, not the first line of the file). The #7680 Rust `render run-summary`
command remains a bounded `/design` payload renderer, not an `/implement`
final-report owner.
`/implement` and `/design` share the same `larch:final-summary` marker family; the
`runid=` segment disambiguates concurrent runs on one tracking issue.
`/implement` uses Rust `final-report write` for the published `final-summary.md`
projection and the GitHub upsert payload (`summary-final.md` for implement;
`scripts/larch.sh design render-final-summary` owns the `/design` gather + upsert
path).

Large runtime payloads are not embedded in these comments. Rust `run-log`
commands stage them under `larch-logs/<skill>/<run-id>/`, then the Rust
lifecycle publishes one terminal archive. **Exception**: `larch:diagrams` embeds diagram bodies
directly in the shared issue comment; diagrams are not written as a larch-log
batch. `/design` owns the Architecture section and `/implement` owns the Code
Flow section.

The `larch:metadata` body may include `Force: true` when the run was started
with `/implement --force`; the line is omitted when false. Rust
`tracking post-issue` composes the private `summary-metadata.md` wire file and
calls the marker-keyed upsert owner in process. `post-tracking-issue.sh` is only
a verified-entrypoint compatibility delegate.

**Edit when**: Update this docs page when changing tracking-issue publication surfaces: `scripts/larch.sh tracking post-issue`, `scripts/larch.sh execution-issues refresh` (the Step 8+ `execution-issues refresh` fence), and `scripts/larch.sh final-report write` / Step 16-17 final-report paths. This page is not a runtime `/implement` reference.
