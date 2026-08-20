# Complete Umbrella Recovery

Use the same command to start or recover a managed umbrella:

```text
/complete-umbrella <umbrella-issue-N>
```

Do not remove `[IMPLEMENTING]` from a leaf by hand. The command checks for a
durable run pointer before it starts a new run. Recovery keeps the original
session tmpdir, including every `complete-umbrella-leaf-<N>/` handoff file.

## Sleep and offline behavior

A sleeping laptop may leave the whole-loop bgjob and its leaf child alive. A
lost Claude session does not own the only recovery state. The pointer under
`~/.cache/larch/sessions/` records the repository, umbrella, tmpdir, current
leaf and step, transient-attempt count, and bgjob step.

After the laptop wakes, run `/complete-umbrella <N>` once. The resume owner:

- rebinds a live bgjob wait lease to the current session and returns to the
  same wait;
- consumes an identity-bound durable child result through the existing retry
  or failure route;
- ignores the immediately prior transient result after its next-attempt
  checkpoint has already been persisted, so a wake cannot consume one retry
  twice;
- resets an open leaf's stale `[IMPLEMENTING]` prefix when no live job remains,
  then selects it again without replacing its handoff root.

An offline wake can still make the GitHub validation or title reset fail. Wait
until connectivity returns, then run the same command again. Recovery does not
loosen remote read-back or mutation checks.

## Fail-closed cases

Recovery stops without choosing a candidate when it finds multiple matching
pointers, a missing tmpdir, a repository mismatch, malformed pointer state, or
an unsafe path. Keep the pointer and tmpdir intact while investigating.

The normal success path removes the pointer after the parent closes. A
terminal hard failure removes it only after lifecycle diagnostics are written.
Session cleanup treats a valid complete-umbrella pointer as an active tmpdir
reference, so age cleanup does not discard recoverable handoffs.

## Harness false-denies

Recovery assumes the verified runtime entrypoint can run. On Cursor Agent
sessions that also load a production-telemetry plugin with Bash-wide PreToolUse
guards (notably `smarts` pagerduty, hyperdx, changes, and log-evidence guards),
the Shell tool may reject legitimate
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh complete-umbrella …` and `bgjob …`
commands before execution. The reject text often names PagerDuty, log-provider,
HyperDX, or packaged-reader policy even though the argv never touches those
surfaces. That is a coexistence false-deny, not recoverable umbrella state.

When the harness blocks `start`, `run-leaves` / `bgjob start`, `clear-pointer`,
or `finish`, stop. Repair or upgrade the co-installed Bash-wide guards, or run
`/complete-umbrella` in a session without those guards. Do not hand-edit
lifecycle titles, invent an alternate shell entrypoint, or rephrase the driver
as `gh`, curl, or wget. The skill retries an identical blocked driver at most
once through the harness approval API when present, then hard-fails with this
diagnosis.

## Diagnostic helper

The skill calls the Rust helper through the verified runtime entrypoint. A
maintainer can inspect the same route directly from the target repository:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" complete-umbrella resume \
  --repository OWNER/REPO \
  --issue N \
  --claude-pid "$PPID" \
  --operator-invoked
```

`RESUME_ACTION=wait` means re-enter the documented `bgjob wait` command.
`RESUME_ACTION=reselect` means launch the same whole-loop step against the
returned `COMPLETE_UMBRELLA_TMPDIR`. `needs-design` and `failed` remain terminal
for that invocation and follow the ordinary diagnostic cleanup path.
