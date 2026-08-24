# Vendor-agent diagnostics boundary

This document records the current saved, logged, and flushed guarantees for
vendor-agent failures. It supersedes the mixed Python/Rust launch inventory
originally assembled for #3713.

## Ownership

All larch-owned Claude, Codex, and Cursor binary launches are Rust-owned and
enter through `scripts/larch.sh`. `larch-core` owns typed vendor requests,
artifact-path families, diagnostic ordering, budgets, and redaction.
`larch-adapters` is the sole owner of subprocess and diagnostic filesystem
effects. `larch-cli` composes launchers, failure records, and run-log batches.
There is no Python agent launcher, carrier library, or fallback.

`ExternalProcessRunner` is the process port. Its production implementation,
`TokioProcessRunner` in `crates/larch-adapters/src/process.rs`, accepts only
closed vendor programs, clears the ambient environment, applies typed
credential overrides, bounds output, and owns timeout and cancellation. On
Unix, it terminates the process group with SIGTERM, escalates to SIGKILL, and
reaps the direct child so descendants cannot outlive the launch.

## Diagnostic guarantees

- **Saved**: the generic external-agent launcher composes a bounded, redacted
  `<output>.failure-diag` before it publishes `<output>.done`. Other launcher
  families reuse the same compositor at their terminal failure boundary. Retry
  stream history is rolled into the ordered source family, and a later success
  removes a stale failure carrier.
- **Logged**: failure records resolve the best available carrier and use a
  non-empty fallback when no diagnostic bytes were captured. Operator-visible
  stderr tails are independently line- and byte-bounded and redacted.
- **Flushed**: implementation failures append private per-launch parts below
  `vendor-failure-diagnostics.parts`; terminal snapshot preparation sorts and
  replaces the `vendor-failure-diagnostics` run-log batch. Design publication
  stages composed carriers while excluding raw streams and retry history.

Raw `*.sidecar`, `*.diag`, `*.events.jsonl`, `*.stderr`, and history artifacts
remain private session evidence. Publication uses only the composed, redacted
carrier or the canonical batch. See
[Artifacts, Redaction, and Publication](security/artifacts-redaction-and-publication.md)
for retention and egress rules.

## Runtime inventory

| Surface | Rust owners | Boundary evidence |
|---|---|---|
| Generic vendor launch and sentinel publication | `crates/larch-cli/src/external_agent.rs` | Builds a typed request, calls `TokioProcessRunner`, composes failure diagnostics, then writes `.done`. |
| Reviewer and collector lifecycle | `crates/larch-cli/src/agent_review.rs`, `collector_commands.rs`, and `review_dispatch_commands.rs` | Review retries preserve stream history, resolve carriers, and append durable diagnostic parts. |
| Claude subprocesses, implementers, and CI fixers | `crates/larch-cli/src/claude_commands.rs`, `implement_launcher_commands.rs`, and `ci_launcher_commands.rs` | All variants reuse the process port and shared launcher-failure envelope. |
| Drafters, Codex exec, and negotiation rounds | `crates/larch-cli/src/drafter_commands.rs` | Typed vendor argv, credential overlays, session handles, and failure carriers are composed in Rust. |
| Voters, waterfalls, review fixers, scouts, and lint fixers | `crates/larch-cli/src/voter_dispatch_commands.rs`, `waterfall_commands.rs`, `review_and_fix_commands.rs`, `scout_commands.rs`, and `checks_lint_fix_commands.rs` | Dispatchers select approved launcher commands; they do not spawn vendor binaries directly. |
| Diagnostic policy and artifact paths | `crates/larch-core/src/vendor_diagnostics.rs` | Owns source ordering, redaction, truncation, stderr-tail limits, and artifact suffixes. |
| Diagnostic reads and private writes | `crates/larch-adapters/src/vendor_diagnostics.rs` | Uses confined reads and mode-`0600` atomic writes for carriers and tails. |
| Durable implementation batch and publication | `crates/larch-cli/src/launcher_support.rs` and `run_log_flush_commands.rs` | Appends bounded parts, sorts them, and replaces the canonical run-log batch. |

## Verification

`agent-python-free` pins the completed #7678 command ledger and rejects restored
Python launch surfaces or runtime callers. `codex-exec-auth` rejects raw Codex
dispatch outside the authenticated launcher. `subprocess-via-runner` rejects a
second production Rust process owner. Focused Rust tests cover process-group
termination, credential inheritance, diagnostic composition and bounds,
launcher artifacts, retries, collector behavior, and run-log flushing.
