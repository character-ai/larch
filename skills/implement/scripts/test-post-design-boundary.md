# skills/implement/scripts/test-post-design-boundary.sh — contract

`test-post-design-boundary.sh` is the skill-local integration harness for `skills/implement/scripts/post-design-boundary.sh`. It owns wrapper-only behavior; `scripts/test-implement-post-design-boundary.sh` owns the repo-root SKILL.md and reader-pin assertions.

Covered cases:
- Successful synthesized manifest: wrapper exits 0, re-emits `MANIFEST_OK=true`, captures `BRANCH=boundary-test` from a temporary git repo, emits `POST_DESIGN_BOUNDARY_OK=true`, writes `.boundary-gate-passed`, and ends with the default `➡️` imperative breadcrumb. Re-running the wrapper is idempotent.
- Missing manifest and invalid tmpdir: wrapper exits 0 with `MANIFEST_FAILED=true`, suppresses `POST_DESIGN_BOUNDARY_OK=true`, suppresses the imperative breadcrumb, and does not write `.boundary-gate-passed`.
- Boundary sentinel write failure: read-only tmpdir permissions force `ERROR=boundary-gate-sentinel-write-failed` with no success markers.
- Anchored reader-output parsing: an `IMPLEMENT_TMPDIR` path component containing `MANIFEST_FAILED=true` does not affect success classification when the reader emits anchored `MANIFEST_OK=true`.
- Health sidecar behavior: monotonic degradation rewrites session-env while preserving `SLACK_OK`, `SLACK_MISSING`, `REPO`, and `REPO_UNAVAILABLE`; absent sidecar is a no-op with no warnings; malformed booleans warn and preserve prior values; `write-session-env.sh` failure warns and remains non-fatal.
- Branch capture: named branch emits `BRANCH=boundary-test`; persistent detached HEAD failure emits `MANIFEST_FAILED=true ERROR=branch-capture-failed` after retry and suppresses success output.
- Design-only mode emits the design-only `➡️` variant.
- Control-character path injection is rejected with `ERROR=invalid-tmpdir`.
- PostToolUse hook integration: synthetic `Skill` stdin for `design` resolves the cwd-bound tmpdir, reads `.design-only`, emits `hookSpecificOutput.additionalContext`, and the decoded context is byte-identical to direct wrapper stdout including trailing newline. Non-design Skill calls and no matching tmpdir emit empty stdout.
- Stop hook integration: synthetic Stop stdin blocks only when `manifest.env` exists and neither `.boundary-gate-passed` nor `.run-cleaned-up` exists; `.boundary-gate-passed`, `.run-cleaned-up`, absent manifest, and `stop_hook_active=true` all allow stop with empty stdout. Concurrent-session fixtures prove `cwd` binds to the matching `.larch-keepalive` `CLONE_PATH` and fails open when no candidate matches.
- Executable-bit assertions cover the wrapper and both hook entry points.

The harness synthesizes design manifests using the real `skills/design/scripts/read-design-manifest.sh` contract and uses real temporary git repositories for branch behavior. The `write-session-env.sh` auxiliary-failure case uses a temporary plugin-root shim for only that helper while symlinking the real manifest reader and branch helper.

Edit-in-sync: update this file with `post-design-boundary.sh`, `post-design-boundary.md`, `hook-post-design.sh`, `hook-stop-fail-close.sh`, `lib-resolve-implement-tmpdir.sh`, `scripts/test-implement-post-design-boundary.sh`, and `skills/implement/SKILL.md` whenever wrapper stdout, health propagation, hook resolution, branch capture, or boundary sequencing changes. Wired into `make lint` through the `test-post-design-boundary` target; the existing `test-implement-post-design-boundary` target depends on it so both ownership layers run together.
