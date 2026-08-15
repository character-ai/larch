#[path = "support/parity.rs"]
mod parity_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
    process::{Command, Output},
    time::{Duration, SystemTime},
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use larch_core::{ClassifyTextInput, classify_text, shell_quote};
use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};
use sha2::{Digest as _, Sha256};
use tempfile::TempDir;

#[derive(Clone, Copy)]
struct CleanInstallCase {
    id: &'static str,
    domain: &'static str,
    verb: &'static str,
}

impl CleanInstallCase {
    const fn new(id: &'static str, domain: &'static str, verb: &'static str) -> Self {
        Self { id, domain, verb }
    }

    /// Exit status a clean dispatch of this case produces.
    ///
    /// A verb whose only offline-deterministic invocation is a refusal still
    /// proves the dispatch reached it; the case pins that refusal's code rather
    /// than reaching the network or mutating a repository to reach `0`.
    fn expected_exit(self) -> i32 {
        match self.id {
            // `issue state` refuses its own missing-value line. Neither
            // `parse-input` nor `fetch-issue-details` has a `--help` action, so
            // the clean-install token reads as an unknown option and each
            // refuses too. The other two issue-input verbs accept that token and
            // exit 0: `allocate-candidates` prints its usage, and `list-issues`
            // reports its fail-open envelope.
            // `issue state` refuses its own missing-value line, and neither
            // `create-one` nor `write-sentinel` has a `--help` action, so the
            // clean-install token reads as an unknown option there too.
            "clean-install-issue-add-blocked-by"
            | "clean-install-issue-add-sub-issue"
            | "clean-install-alias-generate"
            | "clean-install-alias-resolve-target"
            | "clean-install-issue-create-one"
            | "clean-install-issue-fetch-issue-details"
            | "clean-install-issue-parse-input"
            | "clean-install-issue-state"
            | "clean-install-issue-write-sentinel"
            // The six tracking-issue verbs declare no `--help` action either,
            // so the clean-install token reads as an unrecognized argument and
            // each refuses with the `argparse` usage exit code.
            | "clean-install-tracking-issue-append-comment"
            | "clean-install-tracking-issue-create-issue"
            | "clean-install-tracking-issue-mark-false-positive"
            | "clean-install-tracking-issue-read"
            | "clean-install-tracking-issue-rename"
            | "clean-install-tracking-issue-upsert-summary"
            // `oos file-conflict-deps` parses its own option line and reports
            // its own usage exit rather than the `argparse` one.
            | "clean-install-oos-file-conflict-deps"
            // Pacific timestamp treats every argument, including `--help`, as
            // its legacy unexpected-argument refusal. `local-cleanup` keeps
            // its historical raw compatibility parser, so the same token is a
            // deterministic usage refusal that proves verified dispatch.
            | "clean-install-audit-runs-pacific-timestamp"
            | "clean-install-session-local-cleanup" => 1,
            "clean-install-admission-preflight" => 3,
            "clean-install-token-measure-cache-efficiency"
            | "clean-install-token-measure-checks-digest-savings"
            | "clean-install-token-measure-panel-cost"
            | "clean-install-token-measure-realized-cost"
            | "clean-install-token-measure-references-heatmap" => 4,
            "clean-install-session-check-live-mutation-auth" => 5,
            // Neither `/block-issue` verb has a `--help` action either, so the
            // clean-install token reads as an unknown flag and each refuses
            // with its own usage exit code, which is the same `2` the terminal
            // snapshot reports for its missing session directory, the three
            // title verbs and four untrusted verbs report for the token they
            // cannot use, and each write verb reports for its missing required
            // option.
            "clean-install-block-issue-add-blocked-by"
            | "clean-install-block-issue-remove-blocked-by"
            | "clean-install-issue-insert-signal-marker"
            | "clean-install-issue-title-archival-jq"
            | "clean-install-issue-title-eligibility"
            | "clean-install-named-block-write"
            | "clean-install-plan-block-read"
            | "clean-install-plan-block-write"
            | "clean-install-run-log-prepare-terminal-snapshot"
            | "clean-install-untrusted-file-block"
            | "clean-install-triage-apply"
            | "clean-install-triage-inspect"
            | "clean-install-triage-probe"
            | "clean-install-untrusted-redact-stream"
            | "clean-install-untrusted-xml-escape-attr"
            // Neither final-report verb declares a `--help` action either, so
            // the clean-install token reads as an unrecognized argument and each
            // refuses for its missing `--implement-tmpdir`.
            | "clean-install-final-report-step18b"
            | "clean-install-final-report-write"
            // None of the four execution-issue verbs declares a `--help`
            // action, so the clean-install token reads as an unrecognized
            // argument and each refuses with the same usage exit code.
            | "clean-install-execution-issues-append"
            | "clean-install-execution-issues-flush"
            | "clean-install-execution-issues-flush-safety-net"
            | "clean-install-execution-issues-refresh"
            // No `oos` verb declares a `--help` action either: the two hand
            // rolled option lines report their own usage exit `1`, and the
            // three `argparse`-shaped ones refuse the token with `2`.
            | "clean-install-oos-materialize-manifest"
            | "clean-install-oos-issue-cap"
            | "clean-install-oos-disposition-gate"
            | "clean-install-oos-disposition-checkpoint"
            | "clean-install-oos-file"
            // The combine-issues compatibility verbs receive the fixture's
            // `--help` token as a raw argument, so their argparse boundary
            // proves dispatch by refusing it with the standard usage code.
            | "clean-install-combine-issues-apply"
            | "clean-install-combine-issues-close-eligible"
            | "clean-install-combine-issues-close-sources"
            | "clean-install-combine-issues-close-stale"
            | "clean-install-combine-issues-fetch"
            | "clean-install-combine-issues-fetch-deps"
            | "clean-install-combine-issues-list-open"
            | "clean-install-combine-issues-plan-audit"
            | "clean-install-combine-issues-plan-inherited"
            | "clean-install-combine-issues-prose-audit"
            // `generate` keeps its raw compatibility boundary, so `--help`
            // proves that the verified wrapper reaches each selector while the
            // selector rejects its unsupported extra argument.
            | "clean-install-generate-check"
            | "clean-install-generate-code-reviewer-agent"
            | "clean-install-generate-pre-rendered-reviewer-prompts"
            | "clean-install-generate-reviewer-code-robustness-agent"
            | "clean-install-generate-reviewer-plan-fidelity-agent"
            | "clean-install-generate-reviewer-security-structure-tests-agent"
            | "clean-install-voting-code-review-classification-header"
            | "clean-install-voting-compose-tally-record"
            | "clean-install-voting-findings-classification-header"
            | "clean-install-voting-degraded-warning"
            | "clean-install-voting-voter-status-block"
            | "clean-install-voting-write-tally" => 2,
            // Every umbrella verb owns a real help action, so the default
            // clean-install `--help` probe succeeds.
            _ => 0,
        }
    }

    fn arguments(self) -> &'static [&'static str] {
        if let Some(arguments) = phase_detail_clean_install_arguments(self.id) {
            return arguments;
        }
        if let Some(arguments) = admission_clean_install_arguments(self.id) {
            return arguments;
        }
        match self.id {
            "clean-install-kv-get" => &["--key", "MISSING", "--default", "clean-install"],
            "clean-install-session-read-key" => &[
                "--file",
                "/larch-clean-install-read-key-missing",
                "--key",
                "KEY",
                "--default",
                "clean-install",
            ],
            "clean-install-session-read-keys" => &[
                "--file",
                "/larch-clean-install-read-keys-missing",
                "--key",
                "KEY=clean-install",
            ],
            "clean-install-session-cleanup-tmpdir" => {
                &["--dir", "/tmp/larch-clean-install-session-missing"]
            }
            "clean-install-session-setup" => &[
                "--prefix",
                "clean-install",
                "--skip-preflight",
                "--skip-repo-check",
            ],
            // `require-plugin-root` rejects every argument, and the three
            // progress stdin readers see an empty payload, so all four dispatch
            // with no arguments at all.
            "clean-install-session-require-plugin-root"
            | "clean-install-progress-statusline"
            | "clean-install-progress-session-reset"
            | "clean-install-progress-install-statusline" => &[],
            "clean-install-session-resolve-implement-tmpdir" => {
                &["--cwd", "/larch-clean-install-clone-missing"]
            }
            "clean-install-session-validate-design-tmpdir" => {
                &["/tmp/larch-clean-install-design-tmpdir-missing"]
            }
            id if id.starts_with("clean-install-run-log-") => run_log_arguments(id),
            id if id.starts_with("clean-install-timing-") => timing_arguments(id),
            id if id.starts_with("clean-install-token-") => token_arguments(id),
            "clean-install-progress-activate" | "clean-install-progress-deactivate" => &[
                "--repo-root",
                "/larch-clean-install-clone-missing",
                "--run-id",
                "clean-install",
            ],
            "clean-install-progress-cleanup" => &["--retention-days", "7"],
            "clean-install-progress-clear" => {
                &["--repo-root", "/larch-clean-install-clone-missing"]
            }
            "clean-install-progress-note" => &[
                "--repo-root",
                "/larch-clean-install-clone-missing",
                "--skill",
                "clean",
                "--step",
                "install",
                "dispatch",
            ],
            // Every writer below runs against the fixture's seeded session
            // directory, so a clean install proves the whole route, not just
            // the argument rejection in front of it.
            "clean-install-session-write-env" => &[
                "--output",
                "%SESSION%/session-env.sh",
                "--repo-unavailable",
                "false",
            ],
            "clean-install-session-write-id" => &["--output", "%SESSION%/session-id"],
            "clean-install-session-write-design-env" => &[
                "--output",
                "%SESSION%/source-env.sh",
                "--design-tmpdir",
                "%SESSION%",
                "--session-id",
                "clean-install",
            ],
            "clean-install-session-write-implement-env" => &[
                "--claude-pid",
                "4242",
                "--implement-tmpdir",
                "%SESSION%",
                "--cwd",
                "%SESSION%",
            ],
            "clean-install-session-clear-implement-pointer" => &["--claude-pid", "4242"],
            "clean-install-session-persist-run-flags" => {
                &["--implement-tmpdir", "%SESSION%", "--no-issues", "false"]
            }
            "clean-install-session-restore-finalize-state" => &["--implement-tmpdir", "%SESSION%"],
            "clean-install-session-write-run-params" => &["--output", "%SESSION%/run-params.json"],
            "clean-install-session-resolve-trusted-design-env" => &[
                "--session-env-path",
                "%HOME%/.cache/larch/sessions/current-design-env-4242.sh",
                "--claude-pid",
                "4242",
            ],
            _ => &["--help"],
        }
    }
}

/// Arguments for the `/implement` admission, gate, and blocker verbs.
///
/// A free helper for the same reason `phase_detail_clean_install_arguments` is
/// one: it keeps `arguments` inside the per-function line cap.
fn admission_clean_install_arguments(id: &str) -> Option<&'static [&'static str]> {
    match id {
        "clean-install-admission-preflight" => Some(&["--larch-clean-install-probe"]),
        "clean-install-session-check-live-mutation-auth" => Some(&[
            "--context-file",
            "/larch-clean-install-context-missing",
            "--run-id",
            "clean-install",
            "--trusted-root",
            "/larch-clean-install-root-missing",
        ]),
        "clean-install-session-entry-gate" => Some(&[
            "--mode",
            "implement",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "clean-install",
        ]),
        // `all-open` needs no arguments to reach its empty-result path.
        "clean-install-blocker-all-open" => Some(&[]),
        // Neither issue verb has a `--help` action. `state` proves dispatch
        // through its argument refusal, and `info` through the empty value it
        // reports for a field it does not serve; neither reaches the network.
        "clean-install-issue-state" => Some(&["--issue"]),
        "clean-install-issue-info" => Some(&["--issue", "1", "--field", "title"]),
        // `content-block` and `scope-paths` print their `argparse` help and
        // exit `0`; `strip-body` routes its help through the diagnostic writer
        // and also exits `0`. The rest refuse the clean-install token, so each
        // is given the exact line that proves dispatch without a GitHub read.
        "clean-install-issue-insert-signal-marker"
        | "clean-install-issue-title-archival-jq"
        | "clean-install-issue-title-eligibility"
        | "clean-install-untrusted-redact-stream"
        | "clean-install-untrusted-xml-escape-attr" => Some(&["--clean-install"]),
        "clean-install-untrusted-file-block" => Some(&["clean-install"]),
        "clean-install-named-block-write" | "clean-install-plan-block-write" => Some(&["--delete"]),
        "clean-install-plan-block-read" => Some(&["--issue", "1"]),
        _ => None,
    }
}

fn phase_detail_clean_install_arguments(id: &str) -> Option<&'static [&'static str]> {
    match id {
        "clean-install-progress-render-phase-detail" => Some(&[
            "--rounds-root",
            "/larch-clean-install-rounds-missing",
            "--no-gantt",
        ]),
        "clean-install-progress-write-design-round-meta"
        | "clean-install-progress-write-implement-round-meta" => {
            Some(&["--round-dir", "/larch-clean-install-round-missing"])
        }
        _ => None,
    }
}

/// Argument sets for every Rust-owned `timing` clean-install case.
///
/// A clean install names no session temporary directory, so every verb resolves
/// no ledger: each case proves the whole dispatch route and still writes nothing.
#[rustfmt::skip]
fn timing_arguments(id: &str) -> &'static [&'static str] {
    match id {
        "clean-install-timing-mark" => &["clean-install"],
        "clean-install-timing-report" => &["--summary"],
        "clean-install-timing-record-round" => &[
            "--skill", "implement", "--step", "clean-install", "--round", "1",
            "--start-s", "0", "--end-s", "1", "--accepted", "0", "--rejected", "0",
        ],
        "clean-install-timing-record-vendor-task" => &[
            "--vendor", "codex", "--task-kind", "codex-review",
            "--start-s", "0", "--end-s", "1", "--output", "clean-install.log",
        ],
        "clean-install-timing-harness-mark" => &["--label", "clean-install", "--", "/usr/bin/true"],
        _ => &[],
    }
}

/// Argument sets for every Rust-owned `token` clean-install case.
///
/// A clean install names no session temporary directory, so recording verbs
/// resolve no ledger and still succeed after proving the dispatch route.
#[rustfmt::skip]
fn token_arguments(id: &str) -> &'static [&'static str] {
    match id {
        "clean-install-token-mark" => &["clean-install"],
        "clean-install-token-record-vendor" => &[
            "codex", "input=1", "output=0", "cache_read=0", "cache_create=0", "total=1", "raw=clean-install",
        ],
        "clean-install-token-record-vendor-sidecar" => &["--input", "/larch-clean-install-token-sidecar-missing"],
        "clean-install-token-append-record" => &[
            "--tmpdir", "/tmp", "--input", "/larch-clean-install-token-sidecar-missing",
        ],
        "clean-install-token-lane-write" => &[
            "--dir", "/tmp", "--phase", "research", "--lane", "clean-install",
            "--tool", "claude", "--total-tokens", "1",
        ],
        "clean-install-token-lane-report" => &["--dir", "/tmp"],
        // dump and any unknown id prove dispatch with zero args.
        _ => &[],
    }
}

/// Argument sets for every Rust-owned `run-log` clean-install case.
///
/// The entry-write verbs run against the fixture's seeded session inputs, so a
/// clean install proves each whole route rather than only the argument
/// rejection in front of it. Split out of `CleanInstallCase::arguments` so that
/// matcher stays readable.
#[rustfmt::skip]
fn run_log_arguments(id: &str) -> &'static [&'static str] {
    match id {
        "clean-install-run-log-manifest" => &[
            "--log-root", "manifest-logs", "--skill", "clean",
            "--run-id", "clean-install", "--field", "steps_ran.install=true",
        ],
        "clean-install-run-log-validate-run-id" => &["--run-id", "clean-install"],
        "clean-install-run-log-init" => &[
            "--log-root", "%SESSION%/larch-logs", "--skill", "clean",
            "--run-id", "clean-install",
        ],
        "clean-install-run-log-write" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--batch",
            "review-context",
            "--input-file",
            "%SESSION%/payload.md",
        ],
        "clean-install-run-log-write-round" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--round",
            "1",
            "--source-dir",
            "%SESSION%/round-src",
        ],
        "clean-install-run-log-append" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--batch",
            "execution-issues",
            "--record-file",
            "%SESSION%/record.ndjson",
        ],
        "clean-install-run-log-exists" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--batch",
            "run-statistics",
        ],
        "clean-install-run-log-append-entry" => &[
            "--log",
            "%SESSION%/execution-issues.md",
            "--category",
            "Warnings",
            "--entry",
            "clean-install",
        ],
        "clean-install-run-log-append-failure" => &[
            "--log",
            "%SESSION%/execution-issues.md",
            "--site",
            "clean",
            "--tool",
            "install",
            "--exit-code",
            "0",
            "--category",
            "Warnings",
            "--output-file",
            "%SESSION%/payload.md",
        ],
        "clean-install-run-log-verify-completeness" => &["%SESSION%/verify-run"],
        "clean-install-run-log-publish-breadcrumbs" => &[
            "--source-dir",
            "%SESSION%/breadcrumbs",
            "--dest-dir",
            "%SESSION%/larch-logs/clean/clean-install/breadcrumbs",
        ],
        "clean-install-run-log-checkpoint" => &[],
        "clean-install-run-log-capture-transcript" => &[
            "--log-root", "%SESSION%/larch-logs", "--skill", "implement",
            "--run-id", "clean-install", "--source-file", "%SESSION%/missing-source.env",
        ],
        "clean-install-run-log-refresh" => &["--implement-tmpdir", "%SESSION%"],
        "clean-install-run-log-prepare-terminal-snapshot" => &[
            "--implement-tmpdir", "/larch-clean-install-session-missing",
            "--run-id", "clean-install",
        ],
        _ => &["--help"],
    }
}

#[rustfmt::skip]
const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[
    CleanInstallCase::new("clean-install-admission-fork-env", "admission", "fork-env"),
    CleanInstallCase::new("clean-install-admission-gate", "admission", "gate"),
    CleanInstallCase::new(
        "clean-install-admission-preflight",
        "admission",
        "preflight",
    ),
    CleanInstallCase::new("clean-install-alias-generate", "alias", "generate"),
    CleanInstallCase::new(
        "clean-install-alias-resolve-target",
        "alias",
        "resolve-target",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-bugs-ledger",
        "analyze-bugs",
        "ledger",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-bugs-prefetch",
        "analyze-bugs",
        "prefetch",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-bugs-report",
        "analyze-bugs",
        "report",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-bugs-runtime",
        "analyze-bugs",
        "runtime",
    ),
    CleanInstallCase::new(
        "clean-install-rejected-analysis-ingest-verdict",
        "rejected-analysis",
        "ingest-verdict",
    ),
    CleanInstallCase::new(
        "clean-install-rejected-analysis-prepare",
        "rejected-analysis",
        "prepare",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-check-proposals",
        "learn-from-bugs",
        "check-proposals",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-coverage-index",
        "learn-from-bugs",
        "coverage-index",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-filing-deps",
        "learn-from-bugs",
        "filing-deps",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-prepare",
        "learn-from-bugs",
        "prepare",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-read-state",
        "learn-from-bugs",
        "read-state",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-resolve-zones",
        "learn-from-bugs",
        "resolve-zones",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-state-publish",
        "learn-from-bugs",
        "state-publish",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-validate-report",
        "learn-from-bugs",
        "validate-report",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-verify-origin",
        "learn-from-bugs",
        "verify-origin",
    ),
    CleanInstallCase::new(
        "clean-install-learn-from-bugs-write-state",
        "learn-from-bugs",
        "write-state",
    ),
    CleanInstallCase::new(
        "clean-install-validate-merged-ingest-finder",
        "validate-merged",
        "ingest-finder",
    ),
    CleanInstallCase::new(
        "clean-install-validate-merged-ingest-refuter",
        "validate-merged",
        "ingest-refuter",
    ),
    CleanInstallCase::new(
        "clean-install-validate-merged-prepare",
        "validate-merged",
        "prepare",
    ),
    CleanInstallCase::new(
        "clean-install-validate-merged-report",
        "validate-merged",
        "report",
    ),
    CleanInstallCase::new(
        "clean-install-validate-merged-write-state",
        "validate-merged",
        "write-state",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-issues-analyze",
        "analyze-issues",
        "analyze",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-issues-fetch",
        "analyze-issues",
        "fetch",
    ),
    CleanInstallCase::new(
        "clean-install-analyze-issues-run",
        "analyze-issues",
        "run",
    ),
    CleanInstallCase::new(
        "clean-install-audit-runs-bugs-backlog-nudge",
        "audit-runs",
        "bugs-backlog-nudge",
    ),
    CleanInstallCase::new(
        "clean-install-audit-runs-close-priors",
        "audit-runs",
        "close-priors",
    ),
    CleanInstallCase::new("clean-install-audit-runs-compute-counters", "audit-runs", "compute-counters"),
    CleanInstallCase::new("clean-install-audit-runs-map-runs", "audit-runs", "map-runs"),
    CleanInstallCase::new("clean-install-audit-runs-pacific-timestamp", "audit-runs", "pacific-timestamp"),
    CleanInstallCase::new("clean-install-audit-runs-preflight", "audit-runs", "preflight"),
    CleanInstallCase::new("clean-install-audit-runs-resolve-prs", "audit-runs", "resolve-prs"),
    CleanInstallCase::new("clean-install-audit-runs-scan-run", "audit-runs", "scan-run"),
    CleanInstallCase::new("clean-install-audit-runs-title", "audit-runs", "title"),
    CleanInstallCase::new(
        "clean-install-audit-runs-title-match",
        "audit-runs",
        "title-match",
    ),
    CleanInstallCase::new("clean-install-blocker-all-open", "blocker", "all-open"),
    CleanInstallCase::new("clean-install-bootstrap-invoke", "bootstrap", "invoke"),
    CleanInstallCase::new(
        "clean-install-bootstrap-parse-routing",
        "bootstrap",
        "parse-routing",
    ),
    CleanInstallCase::new(
        "clean-install-bootstrap-resolve-non-interactive",
        "bootstrap",
        "resolve-non-interactive",
    ),
    CleanInstallCase::new("clean-install-cleanup-run", "cleanup", "run"),
    CleanInstallCase::new("clean-install-combine-issues-apply", "combine-issues", "apply"),
    CleanInstallCase::new(
        "clean-install-combine-issues-close-eligible",
        "combine-issues",
        "close-eligible",
    ),
    CleanInstallCase::new(
        "clean-install-combine-issues-close-sources",
        "combine-issues",
        "close-sources",
    ),
    CleanInstallCase::new(
        "clean-install-combine-issues-close-stale",
        "combine-issues",
        "close-stale",
    ),
    CleanInstallCase::new("clean-install-combine-issues-fetch", "combine-issues", "fetch"),
    CleanInstallCase::new(
        "clean-install-combine-issues-fetch-deps",
        "combine-issues",
        "fetch-deps",
    ),
    CleanInstallCase::new(
        "clean-install-combine-issues-list-open",
        "combine-issues",
        "list-open",
    ),
    CleanInstallCase::new(
        "clean-install-combine-issues-plan-audit",
        "combine-issues",
        "plan-audit",
    ),
    CleanInstallCase::new(
        "clean-install-combine-issues-plan-inherited",
        "combine-issues",
        "plan-inherited",
    ),
    CleanInstallCase::new(
        "clean-install-combine-issues-prose-audit",
        "combine-issues",
        "prose-audit",
    ),
    CleanInstallCase::new("clean-install-deps-apply", "deps", "apply"),
    CleanInstallCase::new("clean-install-deps-explicit-refs", "deps", "explicit-refs"),
    CleanInstallCase::new("clean-install-deps-fetch", "deps", "fetch"),
    CleanInstallCase::new("clean-install-deps-plan", "deps", "plan"),
    CleanInstallCase::new("clean-install-deps-resolve-repo", "deps", "resolve-repo"),
    CleanInstallCase::new("clean-install-deps-write-proposals", "deps", "write-proposals"),
    CleanInstallCase::new("clean-install-generate-check", "generate", "check"),
    CleanInstallCase::new(
        "clean-install-generate-code-reviewer-agent",
        "generate",
        "code-reviewer-agent",
    ),
    CleanInstallCase::new(
        "clean-install-generate-pre-rendered-reviewer-prompts",
        "generate",
        "pre-rendered-reviewer-prompts",
    ),
    CleanInstallCase::new(
        "clean-install-generate-reviewer-code-robustness-agent",
        "generate",
        "reviewer-code-robustness-agent",
    ),
    CleanInstallCase::new(
        "clean-install-generate-reviewer-plan-fidelity-agent",
        "generate",
        "reviewer-plan-fidelity-agent",
    ),
    CleanInstallCase::new(
        "clean-install-generate-reviewer-security-structure-tests-agent",
        "generate",
        "reviewer-security-structure-tests-agent",
    ),
    CleanInstallCase::new(
        "clean-install-block-issue-add-blocked-by",
        "block-issue",
        "add-blocked-by",
    ),
    CleanInstallCase::new(
        "clean-install-block-issue-remove-blocked-by",
        "block-issue",
        "remove-blocked-by",
    ),
    CleanInstallCase::new(
        "clean-install-issue-add-blocked-by",
        "issue",
        "add-blocked-by",
    ),
    CleanInstallCase::new("clean-install-issue-add-sub-issue", "issue", "add-sub-issue"),
    CleanInstallCase::new(
        "clean-install-issue-allocate-candidates",
        "issue",
        "allocate-candidates",
    ),
    CleanInstallCase::new(
        "clean-install-issue-cleanup-failed",
        "issue",
        "cleanup-failed",
    ),
    CleanInstallCase::new("clean-install-issue-create-one", "issue", "create-one"),
    CleanInstallCase::new(
        "clean-install-issue-fetch-issue-details",
        "issue",
        "fetch-issue-details",
    ),
    CleanInstallCase::new("clean-install-issue-info", "issue", "info"),
    CleanInstallCase::new(
        "clean-install-issue-insert-signal-marker",
        "issue",
        "insert-signal-marker",
    ),
    CleanInstallCase::new(
        "clean-install-issue-title-archival-jq",
        "issue",
        "title-archival-jq",
    ),
    CleanInstallCase::new(
        "clean-install-issue-title-eligibility",
        "issue",
        "title-eligibility",
    ),
    CleanInstallCase::new("clean-install-named-block-write", "named-block", "write"),
    CleanInstallCase::new("clean-install-plan-scope-paths", "plan", "scope-paths"),
    CleanInstallCase::new(
        "clean-install-plan-review-panel-dispatch",
        "plan-review",
        "panel-dispatch",
    ),
    CleanInstallCase::new(
        "clean-install-plan-review-voter-dispatch",
        "plan-review",
        "voter-dispatch",
    ),
    CleanInstallCase::new("clean-install-plan-review-emit", "plan-review", "emit"),
    CleanInstallCase::new("clean-install-plan-review-emit-rejected", "plan-review", "emit-rejected"),
    CleanInstallCase::new("clean-install-plan-review-filter-gate-b-skipped", "plan-review", "filter-gate-b-skipped"),
    CleanInstallCase::new("clean-install-plan-review-gate-b-counts", "plan-review", "gate-b-counts"),
    CleanInstallCase::new("clean-install-plan-review-gate-b-dedup", "plan-review", "gate-b-dedup"),
    CleanInstallCase::new("clean-install-plan-review-gate-b-finding-line", "plan-review", "gate-b-finding-line"),
    CleanInstallCase::new("clean-install-plan-review-persist-accepted-audit", "plan-review", "persist-accepted-audit"),
    CleanInstallCase::new("clean-install-plan-review-snapshot-pre-review", "plan-review", "snapshot-pre-review"),
    CleanInstallCase::new("clean-install-plan-review-tally", "plan-review", "tally"),
    CleanInstallCase::new("clean-install-status-check", "status", "check"),
    CleanInstallCase::new("clean-install-plan-block-read", "plan-block", "read"),
    CleanInstallCase::new(
        "clean-install-plan-block-strip-body",
        "plan-block",
        "strip-body",
    ),
    CleanInstallCase::new("clean-install-plan-block-write", "plan-block", "write"),
    CleanInstallCase::new(
        "clean-install-tracking-issue-append-comment",
        "tracking-issue",
        "append-comment",
    ),
    CleanInstallCase::new(
        "clean-install-tracking-issue-create-issue",
        "tracking-issue",
        "create-issue",
    ),
    CleanInstallCase::new(
        "clean-install-tracking-issue-mark-false-positive",
        "tracking-issue",
        "mark-false-positive",
    ),
    CleanInstallCase::new("clean-install-tracking-issue-read", "tracking-issue", "read"),
    CleanInstallCase::new(
        "clean-install-tracking-issue-rename",
        "tracking-issue",
        "rename",
    ),
    CleanInstallCase::new(
        "clean-install-tracking-issue-upsert-summary",
        "tracking-issue",
        "upsert-summary",
    ),
    CleanInstallCase::new("clean-install-triage-apply", "triage", "apply"),
    CleanInstallCase::new("clean-install-triage-inspect", "triage", "inspect"),
    CleanInstallCase::new("clean-install-triage-probe", "triage", "probe"),
    CleanInstallCase::new(
        "clean-install-umbrella-mark-in-flight",
        "umbrella",
        "mark-in-flight",
    ),
    CleanInstallCase::new(
        "clean-install-umbrella-persist-proposal",
        "umbrella",
        "persist-proposal",
    ),
    CleanInstallCase::new("clean-install-umbrella-prepare", "umbrella", "prepare"),
    CleanInstallCase::new(
        "clean-install-umbrella-reconcile-in-flight",
        "umbrella",
        "reconcile-in-flight",
    ),
    CleanInstallCase::new(
        "clean-install-umbrella-record-resolved",
        "umbrella",
        "record-resolved",
    ),
    CleanInstallCase::new("clean-install-umbrella-mutate", "umbrella", "mutate"),
    CleanInstallCase::new("clean-install-umbrella-verify", "umbrella", "verify"),
    CleanInstallCase::new(
        "clean-install-umbrella-verify-completion",
        "umbrella",
        "verify-completion",
    ),
    CleanInstallCase::new(
        "clean-install-untrusted-content-block",
        "untrusted",
        "content-block",
    ),
    CleanInstallCase::new(
        "clean-install-untrusted-file-block",
        "untrusted",
        "file-block",
    ),
    CleanInstallCase::new(
        "clean-install-untrusted-redact-stream",
        "untrusted",
        "redact-stream",
    ),
    CleanInstallCase::new(
        "clean-install-untrusted-xml-escape-attr",
        "untrusted",
        "xml-escape-attr",
    ),
    CleanInstallCase::new("clean-install-issue-list-issues", "issue", "list-issues"),
    CleanInstallCase::new(
        "clean-install-issue-migration-audit",
        "issue",
        "migration-audit",
    ),
    CleanInstallCase::new("clean-install-issue-parse-input", "issue", "parse-input"),
    CleanInstallCase::new("clean-install-issue-state", "issue", "state"),
    CleanInstallCase::new(
        "clean-install-issue-write-sentinel",
        "issue",
        "write-sentinel",
    ),
    CleanInstallCase::new(
        "clean-install-session-check-live-mutation-auth",
        "session",
        "check-live-mutation-auth",
    ),
    CleanInstallCase::new("clean-install-session-entry-gate", "session", "entry-gate"),
    CleanInstallCase::new(
        "clean-install-agent-classify-diff",
        "agent",
        "classify-diff",
    ),
    CleanInstallCase::new(
        "clean-install-agent-check-reviewers",
        "agent",
        "check-reviewers",
    ),
    CleanInstallCase::new(
        "clean-install-agent-compose-collector-failure-log",
        "agent",
        "compose-collector-failure-log",
    ),
    CleanInstallCase::new(
        "clean-install-agent-cursor-auth-preflight",
        "agent",
        "cursor-auth-preflight",
    ),
    CleanInstallCase::new(
        "clean-install-agent-cursor-wrap-prompt",
        "agent",
        "cursor-wrap-prompt",
    ),
    CleanInstallCase::new(
        "clean-install-agent-degraded-tools-gate",
        "agent",
        "degraded-tools-gate",
    ),
    CleanInstallCase::new(
        "clean-install-agent-external-tool-registry",
        "agent",
        "external-tool-registry",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-review",
        "agent",
        "launch-review",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-ci",
        "agent",
        "launch-codex-ci",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-cursor-ci",
        "agent",
        "launch-cursor-ci",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-ci",
        "agent",
        "launch-claude-ci",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-implement",
        "agent",
        "launch-codex-implement",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-cursor-implement",
        "agent",
        "launch-cursor-implement",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-lint-fix",
        "agent",
        "launch-claude-lint-fix",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-review-fix",
        "agent",
        "launch-claude-review-fix",
    ),
    CleanInstallCase::new(
        "clean-install-agent-collect-results",
        "agent",
        "collect-results",
    ),
    CleanInstallCase::new(
        "clean-install-agent-dispatch-waterfall",
        "agent",
        "dispatch-waterfall",
    ),
    CleanInstallCase::new(
        "clean-install-agent-dispatch-voters",
        "agent",
        "dispatch-voters",
    ),
    CleanInstallCase::new("clean-install-agent-model-args", "agent", "model-args"),
    CleanInstallCase::new(
        "clean-install-agent-read-claude-model",
        "agent",
        "read-claude-model",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-review",
        "agent",
        "launch-claude-review",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-subprocess",
        "agent",
        "launch-claude-subprocess",
    ),
    CleanInstallCase::new(
        "clean-install-agent-resolve-model-pins",
        "agent",
        "resolve-model-pins",
    ),
    CleanInstallCase::new(
        "clean-install-execution-issues-append",
        "execution-issues",
        "append",
    ),
    CleanInstallCase::new(
        "clean-install-execution-issues-flush",
        "execution-issues",
        "flush",
    ),
    CleanInstallCase::new(
        "clean-install-execution-issues-flush-safety-net",
        "execution-issues",
        "flush-safety-net",
    ),
    CleanInstallCase::new(
        "clean-install-execution-issues-refresh",
        "execution-issues",
        "refresh",
    ),
    CleanInstallCase::new(
        "clean-install-oos-materialize-manifest",
        "oos",
        "materialize-manifest",
    ),
    CleanInstallCase::new("clean-install-oos-issue-cap", "oos", "issue-cap"),
    CleanInstallCase::new(
        "clean-install-oos-file-conflict-deps",
        "oos",
        "file-conflict-deps",
    ),
    CleanInstallCase::new(
        "clean-install-oos-disposition-gate",
        "oos",
        "disposition-gate",
    ),
    CleanInstallCase::new(
        "clean-install-oos-disposition-checkpoint",
        "oos",
        "disposition-checkpoint",
    ),
    CleanInstallCase::new("clean-install-oos-file", "oos", "file"),
    CleanInstallCase::new(
        "clean-install-external-defaults-docs",
        "external-defaults",
        "docs",
    ),
    CleanInstallCase::new(
        "clean-install-external-defaults-resolve-vendor",
        "external-defaults",
        "resolve-vendor",
    ),
    CleanInstallCase::new(
        "clean-install-external-defaults-role",
        "external-defaults",
        "role",
    ),
    CleanInstallCase::new(
        "clean-install-slack-issue-announce",
        "slack",
        "issue-announce",
    ),
    CleanInstallCase::new(
        "clean-install-agent-gather-branch-context",
        "agent",
        "gather-branch-context",
    ),
    CleanInstallCase::new(
        "clean-install-review-gather-context",
        "review",
        "gather-context",
    ),
    CleanInstallCase::new(
        "clean-install-review-dispatch-panel",
        "review",
        "dispatch-panel",
    ),
    CleanInstallCase::new(
        "clean-install-review-collect-findings",
        "review",
        "collect-findings",
    ),
    CleanInstallCase::new(
        "clean-install-review-check-reviewer-failure-threshold",
        "review",
        "check-reviewer-failure-threshold",
    ),
    CleanInstallCase::new(
        "clean-install-review-aggregate-findings",
        "review",
        "aggregate-findings",
    ),
    CleanInstallCase::new(
        "clean-install-review-prune-nit-findings",
        "review",
        "prune-nit-findings",
    ),
    CleanInstallCase::new(
        "clean-install-review-reviewer-prune",
        "review",
        "reviewer-prune",
    ),
    CleanInstallCase::new(
        "clean-install-review-emit-tally",
        "review",
        "emit-tally",
    ),
    CleanInstallCase::new(
        "clean-install-review-log-phase",
        "review",
        "log-phase",
    ),
    CleanInstallCase::new(
        "clean-install-review-tally-code-votes",
        "review",
        "tally-code-votes",
    ),
    CleanInstallCase::new(
        "clean-install-agent-parse-codex-usage",
        "agent",
        "parse-codex-usage",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-drafter",
        "agent",
        "launch-claude-drafter",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-drafter",
        "agent",
        "launch-codex-drafter",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-exec",
        "agent",
        "launch-codex-exec",
    ),
    CleanInstallCase::new(
        "clean-install-agent-run-negotiation-round",
        "agent",
        "run-negotiation-round",
    ),
    CleanInstallCase::new(
        "clean-install-agent-run-external-agent",
        "agent",
        "run-external-agent",
    ),
    CleanInstallCase::new(
        "clean-install-agent-wait-reviewers",
        "agent",
        "wait-reviewers",
    ),
    CleanInstallCase::new("clean-install-lint-gitleaks", "lint", "gitleaks"),
    CleanInstallCase::new("clean-install-bgjob-adapt", "bgjob", "adapt"),
    CleanInstallCase::new("clean-install-bgjob-reap", "bgjob", "reap"),
    CleanInstallCase::new("clean-install-bgjob-start", "bgjob", "start"),
    CleanInstallCase::new("clean-install-bgjob-status", "bgjob", "status"),
    CleanInstallCase::new("clean-install-bgjob-wait", "bgjob", "wait"),
    CleanInstallCase::new("clean-install-kv-get", "kv", "get"),
    CleanInstallCase::new(
        "clean-install-session-cleanup-tmpdir",
        "session",
        "cleanup-tmpdir",
    ),
    CleanInstallCase::new(
        "clean-install-session-local-cleanup",
        "session",
        "local-cleanup",
    ),
    CleanInstallCase::new("clean-install-session-setup", "session", "setup"),
    CleanInstallCase::new("clean-install-session-read-key", "session", "read-key"),
    CleanInstallCase::new("clean-install-session-read-keys", "session", "read-keys"),
    CleanInstallCase::new(
        "clean-install-session-kill-background-processes",
        "session",
        "kill-background-processes",
    ),
    CleanInstallCase::new(
        "clean-install-session-require-plugin-root",
        "session",
        "require-plugin-root",
    ),
    CleanInstallCase::new(
        "clean-install-session-resolve-implement-tmpdir",
        "session",
        "resolve-implement-tmpdir",
    ),
    CleanInstallCase::new(
        "clean-install-session-validate-design-tmpdir",
        "session",
        "validate-design-tmpdir",
    ),
    CleanInstallCase::new("clean-install-session-write-env", "session", "write-env"),
    CleanInstallCase::new("clean-install-session-write-id", "session", "write-id"),
    CleanInstallCase::new(
        "clean-install-session-write-design-env",
        "session",
        "write-design-env",
    ),
    CleanInstallCase::new(
        "clean-install-session-write-implement-env",
        "session",
        "write-implement-env",
    ),
    CleanInstallCase::new(
        "clean-install-session-clear-implement-pointer",
        "session",
        "clear-implement-pointer",
    ),
    CleanInstallCase::new(
        "clean-install-session-persist-run-flags",
        "session",
        "persist-run-flags",
    ),
    CleanInstallCase::new(
        "clean-install-session-write-run-params",
        "session",
        "write-run-params",
    ),
    CleanInstallCase::new(
        "clean-install-session-restore-finalize-state",
        "session",
        "restore-finalize-state",
    ),
    CleanInstallCase::new(
        "clean-install-session-resolve-trusted-design-env",
        "session",
        "resolve-trusted-design-env",
    ),
    CleanInstallCase::new("clean-install-ci-timing-harness", "ci-timing", "harness"),
    CleanInstallCase::new("clean-install-ci-timing-jobs", "ci-timing", "jobs"),
    CleanInstallCase::new(
        "clean-install-ci-timing-merge-group-source",
        "ci-timing",
        "merge-group-source",
    ),
    CleanInstallCase::new("clean-install-ci-timing-pytest", "ci-timing", "pytest"),
    CleanInstallCase::new("clean-install-ci-gitleaks-base", "ci", "gitleaks-base"),
    CleanInstallCase::new("clean-install-ci-rust-select", "ci", "rust-select"),
    CleanInstallCase::new(
        "clean-install-ci-rust-select-summary",
        "ci",
        "rust-select-summary",
    ),
    CleanInstallCase::new("clean-install-rebalance-tests-run", "rebalance-tests", "run"),
    CleanInstallCase::new(
        "clean-install-report-tokens-analyze",
        "report-tokens",
        "analyze",
    ),
    CleanInstallCase::new("clean-install-repo-size", "repo", "size"),
    CleanInstallCase::new("clean-install-research-banner", "research", "banner"),
    CleanInstallCase::new(
        "clean-install-research-render-findings-batch",
        "research",
        "render-findings-batch",
    ),
    CleanInstallCase::new("clean-install-research-run-planner", "research", "run-planner"),
    CleanInstallCase::new(
        "clean-install-research-validate-citations",
        "research",
        "validate-citations",
    ),
    CleanInstallCase::new("clean-install-eval-research", "eval", "research"),
    CleanInstallCase::new(
        "clean-install-eval-validate-research-output",
        "eval",
        "validate-research-output",
    ),
    CleanInstallCase::new(
        "clean-install-residual-bash-paths",
        "residual-bash",
        "paths",
    ),
    CleanInstallCase::new("clean-install-final-report-write", "final-report", "write"),
    CleanInstallCase::new(
        "clean-install-final-report-step18b",
        "final-report",
        "step18b",
    ),
    CleanInstallCase::new("clean-install-timing-dump", "timing", "dump"),
    CleanInstallCase::new(
        "clean-install-timing-harness-mark",
        "timing",
        "harness-mark",
    ),
    CleanInstallCase::new("clean-install-timing-mark", "timing", "mark"),
    CleanInstallCase::new("clean-install-timing-record-round", "timing", "record-round"),
    CleanInstallCase::new(
        "clean-install-timing-record-vendor-task",
        "timing",
        "record-vendor-task",
    ),
    CleanInstallCase::new("clean-install-timing-report", "timing", "report"),
    CleanInstallCase::new("clean-install-timing-task-kinds", "timing", "task-kinds"),
    CleanInstallCase::new(
        "clean-install-timing-telemetry-mark",
        "timing",
        "telemetry-mark",
    ),
    CleanInstallCase::new("clean-install-token-append-record", "token", "append-record"),
    CleanInstallCase::new("clean-install-token-dump", "token", "dump"),
    CleanInstallCase::new("clean-install-token-lane-report", "token", "lane-report"),
    CleanInstallCase::new("clean-install-token-lane-write", "token", "lane-write"),
    CleanInstallCase::new("clean-install-token-mark", "token", "mark"),
    CleanInstallCase::new(
        "clean-install-token-measure-cache-efficiency",
        "token",
        "measure-cache-efficiency",
    ),
    CleanInstallCase::new(
        "clean-install-token-measure-checks-digest-savings",
        "token",
        "measure-checks-digest-savings",
    ),
    CleanInstallCase::new(
        "clean-install-token-measure-md-cost",
        "token",
        "measure-md-cost",
    ),
    CleanInstallCase::new(
        "clean-install-token-measure-ngram-duplication",
        "token",
        "measure-ngram-duplication",
    ),
    CleanInstallCase::new(
        "clean-install-token-measure-panel-cost",
        "token",
        "measure-panel-cost",
    ),
    CleanInstallCase::new(
        "clean-install-token-measure-realized-cost",
        "token",
        "measure-realized-cost",
    ),
    CleanInstallCase::new(
        "clean-install-token-measure-references-heatmap",
        "token",
        "measure-references-heatmap",
    ),
    CleanInstallCase::new("clean-install-token-record-vendor", "token", "record-vendor"),
    CleanInstallCase::new(
        "clean-install-token-record-vendor-sidecar",
        "token",
        "record-vendor-sidecar",
    ),
    CleanInstallCase::new("clean-install-test-shard-pack", "test-shard", "pack"),
    CleanInstallCase::new(
        "clean-install-test-shard-read-makefile",
        "test-shard",
        "read-makefile",
    ),
    CleanInstallCase::new(
        "clean-install-test-shard-write-makefile",
        "test-shard",
        "write-makefile",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-baseline",
        "dirty-tree",
        "baseline",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-checkpoint",
        "dirty-tree",
        "checkpoint",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-scope-check",
        "dirty-tree",
        "scope-check",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-scope-marker",
        "dirty-tree",
        "scope-marker",
    ),
    CleanInstallCase::new(
        "clean-install-gh-agnix-ensure-label",
        "gh",
        "agnix-ensure-label",
    ),
    CleanInstallCase::new("clean-install-gh-agnix-issue", "gh", "agnix-issue"),
    CleanInstallCase::new("clean-install-gh-remote-repo", "gh", "remote-repo"),
    CleanInstallCase::new("clean-install-gh-resolve-repo", "gh", "resolve-repo"),
    CleanInstallCase::new("clean-install-gh-run-logs", "gh", "run-logs"),
    CleanInstallCase::new("clean-install-gh-workflow-path", "gh", "workflow-path"),
    CleanInstallCase::new("clean-install-git-amend-add", "git", "amend-add"),
    CleanInstallCase::new("clean-install-git-branch-info", "git", "branch-info"),
    CleanInstallCase::new(
        "clean-install-git-check-main-sync",
        "git",
        "check-main-sync",
    ),
    CleanInstallCase::new(
        "clean-install-git-check-phantom-dirty",
        "git",
        "check-phantom-dirty",
    ),
    CleanInstallCase::new(
        "clean-install-git-check-remote-branch",
        "git",
        "check-remote-branch",
    ),
    CleanInstallCase::new("clean-install-git-checkout-ours", "git", "checkout-ours"),
    CleanInstallCase::new("clean-install-git-clean-tree", "git", "clean-tree"),
    CleanInstallCase::new("clean-install-git-commit", "git", "commit"),
    CleanInstallCase::new("clean-install-git-conflict-files", "git", "conflict-files"),
    CleanInstallCase::new("clean-install-git-count-commits", "git", "count-commits"),
    CleanInstallCase::new("clean-install-git-current-branch", "git", "current-branch"),
    CleanInstallCase::new("clean-install-git-phantom-probe", "git", "phantom-probe"),
    CleanInstallCase::new("clean-install-git-rebase-abort", "git", "rebase-abort"),
    CleanInstallCase::new("clean-install-git-rebase-skip", "git", "rebase-skip"),
    CleanInstallCase::new("clean-install-git-show-stage", "git", "show-stage"),
    CleanInstallCase::new(
        "clean-install-git-snapshot-untracked",
        "git",
        "snapshot-untracked",
    ),
    CleanInstallCase::new("clean-install-git-stage", "git", "stage"),
    CleanInstallCase::new(
        "clean-install-git-sync-local-main",
        "git",
        "sync-local-main",
    ),
    CleanInstallCase::new(
        "clean-install-hook-anti-read-poll",
        "hook",
        "anti-read-poll",
    ),
    CleanInstallCase::new(
        "clean-install-plugin-read-version",
        "plugin",
        "read-version",
    ),
    CleanInstallCase::new("clean-install-object-store-gcs", "object-store", "gcs"),
    CleanInstallCase::new("clean-install-push-branch", "push", "branch"),
    CleanInstallCase::new(
        "clean-install-push-checkpoint-probe",
        "push",
        "checkpoint-probe",
    ),
    CleanInstallCase::new("clean-install-push-force", "push", "force"),
    CleanInstallCase::new("clean-install-push-rebase", "push", "rebase"),
    CleanInstallCase::new(
        "clean-install-release-asset-candidate",
        "release",
        "asset-candidate",
    ),
    CleanInstallCase::new(
        "clean-install-release-classify-bump",
        "release",
        "classify-bump",
    ),
    CleanInstallCase::new(
        "clean-install-release-collect-assets",
        "release",
        "collect-assets",
    ),
    CleanInstallCase::new(
        "clean-install-release-package-asset",
        "release",
        "package-asset",
    ),
    CleanInstallCase::new(
        "clean-install-release-plugin-runtime",
        "release",
        "plugin-runtime",
    ),
    CleanInstallCase::new("clean-install-release-prepare", "release", "prepare"),
    CleanInstallCase::new(
        "clean-install-release-set-version",
        "release",
        "set-version",
    ),
    CleanInstallCase::new(
        "clean-install-release-validate-assets",
        "release",
        "validate-assets",
    ),
    CleanInstallCase::new("clean-install-run-log-archive", "run-log", "archive"),
    CleanInstallCase::new("clean-install-run-log-manifest", "run-log", "manifest"),
    CleanInstallCase::new("clean-install-run-log-publish", "run-log", "publish"),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-cancel",
        "run-log",
        "lifecycle-cancel",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-early-return",
        "run-log",
        "lifecycle-early-return",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-failure",
        "run-log",
        "lifecycle-failure",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-finalize",
        "run-log",
        "lifecycle-finalize",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-start",
        "run-log",
        "lifecycle-start",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-materialize",
        "run-log",
        "materialize",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-cleanup-implement-logs",
        "run-log",
        "cleanup-implement-logs",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-migrate-layout",
        "run-log",
        "migrate-layout",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-retro-fix-cursor",
        "run-log",
        "retro-fix-cursor",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-retro-v3-sweep",
        "run-log",
        "retro-v3-sweep",
    ),
    CleanInstallCase::new("clean-install-run-log-sync", "run-log", "sync"),
    CleanInstallCase::new(
        "clean-install-run-log-validate-run-id",
        "run-log",
        "validate-run-id",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-chat-print",
        "stall-recovery",
        "chat-print",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-clear-stall",
        "stall-recovery",
        "clear-stall",
    ),
    CleanInstallCase::new("clean-install-stall-recovery-classify", "stall-recovery", "classify"),
    CleanInstallCase::new("clean-install-stall-recovery-init-attempts", "stall-recovery", "init-attempts"),
    CleanInstallCase::new("clean-install-stall-recovery-normalize-file-failure-report-env", "stall-recovery", "normalize-file-failure-report-env"),
    CleanInstallCase::new("clean-install-stall-recovery-normalize-issue-env", "stall-recovery", "normalize-issue-env"),
    CleanInstallCase::new("clean-install-stall-recovery-normalize-outcome", "stall-recovery", "normalize-outcome"),
    CleanInstallCase::new("clean-install-stall-recovery-record-attempt", "stall-recovery", "record-attempt"),
    CleanInstallCase::new("clean-install-stall-recovery-record-escalation", "stall-recovery", "record-escalation"),
    CleanInstallCase::new("clean-install-stall-recovery-retry-policy", "stall-recovery", "retry-policy"),
    CleanInstallCase::new(
        "clean-install-stall-recovery-compose-report",
        "stall-recovery",
        "compose-report",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-dedup-tier-a-report",
        "stall-recovery",
        "dedup-tier-a-report",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-is-larch-dev-clone",
        "stall-recovery",
        "is-larch-dev-clone",
    ),
    CleanInstallCase::new("clean-install-stall-recovery-lint", "stall-recovery", "lint"),
    CleanInstallCase::new(
        "clean-install-stall-recovery-populate-sensitive-corpus",
        "stall-recovery",
        "populate-sensitive-corpus",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-seed-terminal-state",
        "stall-recovery",
        "seed-terminal-state",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-validate-terminal-state",
        "stall-recovery",
        "validate-terminal-state",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-validate-tier-b-public-file",
        "stall-recovery",
        "validate-tier-b-public-file",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-validate-token",
        "stall-recovery",
        "validate-token",
    ),
    CleanInstallCase::new("clean-install-run-log-init", "run-log", "init"),
    CleanInstallCase::new("clean-install-run-log-write", "run-log", "write"),
    CleanInstallCase::new(
        "clean-install-run-log-write-round",
        "run-log",
        "write-round",
    ),
    CleanInstallCase::new("clean-install-run-log-append", "run-log", "append"),
    CleanInstallCase::new("clean-install-run-log-exists", "run-log", "exists"),
    CleanInstallCase::new(
        "clean-install-run-log-append-entry",
        "run-log",
        "append-entry",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-append-failure",
        "run-log",
        "append-failure",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-verify-completeness",
        "run-log",
        "verify-completeness",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-publish-breadcrumbs",
        "run-log",
        "publish-breadcrumbs",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-capture-transcript",
        "run-log",
        "capture-transcript",
    ),
    CleanInstallCase::new("clean-install-run-log-checkpoint", "run-log", "checkpoint"),
    CleanInstallCase::new(
        "clean-install-run-log-prepare-terminal-snapshot",
        "run-log",
        "prepare-terminal-snapshot",
    ),
    CleanInstallCase::new("clean-install-run-log-refresh", "run-log", "refresh"),
    CleanInstallCase::new(
        "clean-install-run-log-render-session-transcript",
        "run-log",
        "render-session-transcript",
    ),
    CleanInstallCase::new("clean-install-progress-activate", "progress", "activate"),
    CleanInstallCase::new("clean-install-progress-cleanup", "progress", "cleanup"),
    CleanInstallCase::new("clean-install-progress-clear", "progress", "clear"),
    CleanInstallCase::new(
        "clean-install-progress-deactivate",
        "progress",
        "deactivate",
    ),
    CleanInstallCase::new(
        "clean-install-progress-install-statusline",
        "progress",
        "install-statusline",
    ),
    CleanInstallCase::new("clean-install-progress-note", "progress", "note"),
    CleanInstallCase::new(
        "clean-install-progress-render-phase-detail",
        "progress",
        "render-phase-detail",
    ),
    CleanInstallCase::new(
        "clean-install-progress-session-reset",
        "progress",
        "session-reset",
    ),
    CleanInstallCase::new(
        "clean-install-progress-statusline",
        "progress",
        "statusline",
    ),
    CleanInstallCase::new(
        "clean-install-progress-write-design-round-meta",
        "progress",
        "write-design-round-meta",
    ),
    CleanInstallCase::new(
        "clean-install-progress-write-implement-round-meta",
        "progress",
        "write-implement-round-meta",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-storage-preflight",
        "run-log",
        "storage-preflight",
    ),
    CleanInstallCase::new(
        "clean-install-upgrade-larch-release-step7-root",
        "upgrade-larch",
        "release-step7-root",
    ),
    CleanInstallCase::new("clean-install-upgrade-larch-run", "upgrade-larch", "run"),
    CleanInstallCase::new(
        "clean-install-upgrade-larch-sparse-dirs",
        "upgrade-larch",
        "sparse-dirs",
    ),
    CleanInstallCase::new(
        "clean-install-verify-skill-called",
        "verify",
        "skill-called",
    ),
    CleanInstallCase::new(
        "clean-install-voting-code-review-classification-header",
        "voting",
        "code-review-classification-header",
    ),
    CleanInstallCase::new(
        "clean-install-voting-findings-classification-header",
        "voting",
        "findings-classification-header",
    ),
    CleanInstallCase::new(
        "clean-install-calibration-replay-rebuild-ballot",
        "calibration-replay",
        "rebuild-ballot",
    ),
    CleanInstallCase::new(
        "clean-install-calibration-replay-run-replay",
        "calibration-replay",
        "run-replay",
    ),
    CleanInstallCase::new(
        "clean-install-calibration-replay-validate-manifest",
        "calibration-replay",
        "validate-manifest",
    ),
    CleanInstallCase::new(
        "clean-install-voter-calibration-snapshot",
        "voter-calibration",
        "snapshot",
    ),
    CleanInstallCase::new(
        "clean-install-voting-compose-tally-record",
        "voting",
        "compose-tally-record",
    ),
    CleanInstallCase::new(
        "clean-install-voting-degraded-warning",
        "voting",
        "degraded-warning",
    ),
    CleanInstallCase::new(
        "clean-install-voting-effective-judges",
        "voting",
        "effective-judges",
    ),
    CleanInstallCase::new(
        "clean-install-voting-parse-rate-check",
        "voting",
        "parse-rate-check",
    ),
    CleanInstallCase::new(
        "clean-install-voting-parse-rate-retry",
        "voting",
        "parse-rate-retry",
    ),
    CleanInstallCase::new(
        "clean-install-voting-scoreboard",
        "voting",
        "scoreboard",
    ),
    CleanInstallCase::new(
        "clean-install-voting-tally-vote",
        "voting",
        "tally-vote",
    ),
    CleanInstallCase::new(
        "clean-install-voting-voter-status-block",
        "voting",
        "voter-status-block",
    ),
    CleanInstallCase::new(
        "clean-install-voting-write-tally",
        "voting",
        "write-tally",
    ),
];

#[test]
fn release_publication_commands_are_exposed_by_the_rust_binary() {
    for command in ["finish", "promote", "promote-latest"] {
        let output = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["release", command, "--help"])
            .output()
            .unwrap_or_else(|error| panic!("launch release {command}: {error}"));

        assert!(
            output.status.success(),
            "release {command} --help failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            String::from_utf8_lossy(&output.stdout)
                .contains(&format!("Usage: larch release {command}")),
            "release {command} did not enter the Rust CLI"
        );
    }
}

#[test]
fn representative_python_and_rust_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let compiled_rust_fixture = compile_rust_fixture(&fixture_directory);
    let rust_fixture = compiled_rust_fixture.path().join("reference-command");
    let python_fixture = fixture_directory.join("reference_command.py");
    let golden_directory = fixture_directory.join("goldens");

    let cases = [
        ParityCase {
            name: "clean",
            python: Program::new(&python)
                .args([path_text(&python_fixture), "clean", "{sandbox}"])
                .env("FIXTURE_TIMESTAMP", "2026-07-18T20:00:00.123Z"),
            rust: Program::new(&rust_fixture)
                .args(["clean", "{sandbox}"])
                .env("FIXTURE_TIMESTAMP", "2026-07-18T20:00:01Z"),
            seed_files: vec![SeedFile::text("input/seed.txt", "fixture\n")],
            side_effect_records: vec![PathBuf::from("effects.ndjson")],
            normalization: vec![
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        },
        ParityCase {
            name: "usage-error",
            python: Program::new(&python).args([path_text(&python_fixture)]),
            rust: Program::new(&rust_fixture),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "malformed-input",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "malformed",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["malformed", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "environmental-failure",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "environment",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["environment", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "service-isolation",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "isolation",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["isolation", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        },
    ];

    for case in cases {
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct SessionKvFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    stdin: Option<&'static [u8]>,
    seed: Option<(&'static str, &'static str)>,
    normalize_root: bool,
}

impl SessionKvFixture {
    fn build(self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let rust_command = match self.command {
            "kv-get" => ["kv", "get"],
            "read-key" => ["session", "read-key"],
            "read-keys" => ["session", "read-keys"],
            command => panic!("unknown session parity command: {command}"),
        };
        let mut python = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.command))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust = Program::new(rust).args(
            rust_command
                .into_iter()
                .chain(self.arguments.iter().copied()),
        );
        if let Some(input) = self.stdin {
            python = python.stdin(input);
            rust = rust.stdin(input);
        }
        ParityCase {
            name: self.name,
            python,
            rust,
            seed_files: self
                .seed
                .map(|(path, contents)| SeedFile::text(path, contents))
                .into_iter()
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self
                .normalize_root
                .then_some(NormalizationRule::SandboxRoot)
                .into_iter()
                .collect(),
        }
    }
}

#[test]
fn session_kv_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("session_kv_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");
    let cases = [
        SessionKvFixture {
            name: "kv-stdin-bytes",
            command: "kv-get",
            arguments: &["--key", "KEY", "--match", "last-non-empty"],
            stdin: Some(b"KEY=first\nKEY=\xff\nKEY=\n"),
            seed: None,
            normalize_root: false,
        },
        SessionKvFixture {
            name: "kv-file-cr-strip",
            command: "kv-get",
            arguments: &[
                "--file",
                "{sandbox}/values.env",
                "--key",
                "KEY",
                "--match",
                "last",
                "--cr-strip",
                "strip",
            ],
            stdin: None,
            seed: Some(("values.env", "KEY=first\r\nKEY=\rvalue\r\r\n")),
            normalize_root: false,
        },
        SessionKvFixture {
            name: "kv-usage-error",
            command: "kv-get",
            arguments: &[],
            stdin: None,
            seed: None,
            normalize_root: false,
        },
        SessionKvFixture {
            name: "session-read-key-first",
            command: "read-key",
            arguments: &["--file", "{sandbox}/session.env", "--key", "KEY"],
            stdin: None,
            seed: Some(("session.env", "IGNORED=value\u{85}KEY=first\nKEY=last\n")),
            normalize_root: false,
        },
        SessionKvFixture {
            name: "session-read-key-cr-error",
            command: "read-key",
            arguments: &[
                "--file",
                "{sandbox}/session.env",
                "--key",
                "KEY",
                "--default",
                "fallback",
            ],
            stdin: None,
            seed: Some(("session.env", "KEY=value\r\n")),
            normalize_root: true,
        },
        SessionKvFixture {
            name: "session-read-keys",
            command: "read-keys",
            arguments: &[
                "--file",
                "{sandbox}/session.env",
                "--key",
                "A",
                "--key",
                "B=default",
                "--key",
                "MISSING=fallback",
            ],
            stdin: None,
            seed: Some(("session.env", "A=first\nA=last\nB=\n")),
            normalize_root: false,
        },
    ];

    for fixture in cases {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[cfg(unix)]
#[test]
fn bgjob_commands_have_frozen_black_box_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("bgjob_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");
    let completed_result = "BGJOB_RC=0\nBGJOB_ELAPSED_S=7\nSTEP=demo\n";
    let cases = vec![
        ParityCase {
            name: "bgjob-start-missing-command",
            python: Program::new(&python).args([path_text(&python_fixture), "start"]),
            rust: Program::new(&rust).args(["bgjob", "start"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "bgjob-wait-completed-envelope",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "wait",
                "--step",
                "demo",
                "--tmpdir",
                "{sandbox}/session",
                "--max-wait-s",
                "0",
            ]),
            rust: Program::new(&rust).args([
                "bgjob",
                "wait",
                "--step",
                "demo",
                "--tmpdir",
                "{sandbox}/session",
                "--max-wait-s",
                "0",
            ]),
            seed_files: vec![SeedFile::text(
                "session/bgjob/demo.result.env",
                completed_result,
            )],
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "bgjob-status-empty-registry",
            python: Program::new(&python).args([path_text(&python_fixture), "status"]),
            rust: Program::new(&rust).args(["bgjob", "status"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "bgjob-reap-empty-registry",
            python: Program::new(&python).args([path_text(&python_fixture), "reap"]),
            rust: Program::new(&rust).args(["bgjob", "reap"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "bgjob-adapt-missing-command",
            python: Program::new(&python).args([path_text(&python_fixture), "adapt"]),
            rust: Program::new(&rust).args(["bgjob", "adapt"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
    ];

    for case in cases {
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct StallRecoveryFixture {
    name: &'static str,
    verb: &'static str,
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
    environment: &'static [(&'static str, &'static str)],
}

impl StallRecoveryFixture {
    const fn new(
        name: &'static str,
        verb: &'static str,
        arguments: &'static [&'static str],
        seeds: &'static [(&'static str, &'static str)],
    ) -> Self {
        Self {
            name,
            verb,
            arguments,
            seeds,
            environment: &[],
        }
    }

    const fn with_environment(
        mut self,
        environment: &'static [(&'static str, &'static str)],
    ) -> Self {
        self.environment = environment;
        self
    }

    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.verb))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust = Program::new(rust).args(
            ["stall-recovery", self.verb]
                .into_iter()
                .chain(self.arguments.iter().copied()),
        );
        for (key, value) in self.environment {
            python = python.env(key, value);
            rust = rust.env(key, value);
        }
        ParityCase {
            name: self.name,
            python,
            rust,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        }
    }
}

const STALL_TERMINAL: &str = "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=approved\nSTALL_STEP=8a\nPHASE=ship-pr\nSITE=ship-pr\nTRIGGER=main-agent-required\nBAIL_REASON=review-required\nEXIT_CODE=4\nFAILURE_DETAIL_LOG=\nSOURCE_SCRIPT=ship-pr\n";
const STALL_TERMINAL_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--primary-state-file",
    "{sandbox}/terminal.env",
];
const STALL_GENERIC_CURRENT: &str = "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=approved\nSTALL_STEP=publish\nPHASE=publish\nSITE=design-publish\nTRIGGER=publish-tail-failed\nBAIL_REASON=failed-publish-tail\nEXIT_CODE=5\nFAILURE_DETAIL_LOG=\nSOURCE_SCRIPT=design-publish\nPUBLISH_ATTEMPT_ID=attempt-123\nPUBLISH_RC_SOURCE=returned\nPLAN_WRITE_OK=true\nPUBLISH_OK=false\nLATEST_PHASE=publish\n";
const STALL_GENERIC_FALLBACK: &str = "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=approved\nSTALL_STEP=step2b\nPHASE=postplan\nSITE=gate-b\nTRIGGER=failed\nBAIL_REASON=operator-action\nEXIT_CODE=4\nFAILURE_DETAIL_LOG=\nSOURCE_SCRIPT=split-path\n";
const STALL_GENERIC_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--primary-state-file",
    "{sandbox}/terminal.env",
    "--profile",
    "generic",
    "--artifact-prefix",
    "design-failure",
];
const STALL_ABANDONED_REGISTRY: &str = "STEP=implement-step3-checks\nRUN_ID=parity-run\nTMPDIR=.\nLOG_DIR=.\nCLONE_PATH=.\nSTART_EPOCH=0\nBUDGET_S=600\nSTDOUT_LOG=dead.stdout.log\nSTDERR_LOG=dead.stderr.log\nRESULT_ENV=bgjob/dead.result.env\nDAEMON_PID=999999\nDAEMON_PGID=999999\nDAEMON_START_TIME=dead\nDAEMON_BIRTH_IDENTITY=\nDAEMON_COMMAND=dead\nDAEMON_EXPECTED=\nCHILD_PID=999998\nCHILD_PGID=999998\nCHILD_START_TIME=dead\nCHILD_BIRTH_IDENTITY=\nCHILD_COMMAND=dead\nCHILD_EXPECTED=\nCHILD_ALLOW_COMMAND_TRANSITION=true\n";
const STALL_ABANDONED_ENVIRONMENT: &[(&str, &str)] =
    &[("LARCH_BGJOB_REGISTRY_ROOT", "{sandbox}/registry")];
const STALL_PUBLIC_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--public-file",
    "{sandbox}/public.md",
    "--sensitive-corpus-file",
    "{sandbox}/stall-recovery-sensitive-corpus.env",
];
const STALL_DEV_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--working-tree-root",
    "{sandbox}",
];
const STALL_REPORT_ENVIRONMENT: &[(&str, &str)] = &[
    ("CLAUDE_PROJECT_DIR", "{sandbox}"),
    ("LARCH_STALL_RECOVERY_DRY_RUN", "1"),
];
const STALL_DRY_RUN_ENVIRONMENT: &[(&str, &str)] = &[("LARCH_STALL_RECOVERY_DRY_RUN", "1")];
const STALL_REPORT_COMPOSE_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--surface",
    "issue-input",
    "--report-kind",
    "terminal-failure",
];
const STALL_REPORT_COMPOSE_SEEDS: &[(&str, &str)] = &[
    ("skills/implement/SKILL.md", "fixture\n"),
    (
        "stall-recovery-classification.env",
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nBAIL_REASON=review-required\nRESUME_HINT=none\nEXIT_CODE=1\n",
    ),
    (
        "stall-recovery-attempts.env",
        "version=1\nattempt_count=0\n",
    ),
    (
        "stall-recovery-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe title\n\nProse.\n",
    ),
    ("session-env.sh", "LARCH_RUN_ID=run-1\nBRANCH_NAME=topic\n"),
];
const STALL_REPORT_CORPUS_ARGS: &[&str] = &["--implement-tmpdir", "{sandbox}"];
const STALL_REPORT_CORPUS_SEEDS: &[(&str, &str)] = &[
    ("stall-recovery-sensitive-corpus.env", "existing-token\n"),
    (
        "stall-recovery-classification.env",
        "FAILURE_CLASS=lint-failure\nSTALL_STEP=5\n",
    ),
    (
        "plan.txt",
        "https://client.example.test/private\nexample raw line\n",
    ),
];
const STALL_REPORT_CHAT_SEEDS: &[(&str, &str)] = &[
    (
        "stall-recovery-classification.env",
        "FAILURE_CLASS=lint-failure\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
    ),
    (
        "stall-recovery-attempts.env",
        "version=1\nattempt_count=0\n",
    ),
    (
        "stall-recovery-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe title\n\nProse.\n",
    ),
    (
        "stall-recovery-sensitive-corpus.env",
        "client-secret-value\n",
    ),
    (
        "stall-recovery-bounded-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe summary\n\nclient-secret-value\n",
    ),
];
#[rustfmt::skip]
const STALL_RECOVERY_CASES: &[StallRecoveryFixture] = &[
    StallRecoveryFixture::new(
        "stall-token-generic",
        "validate-token",
        &[
            "--profile",
            "generic",
            "--token-kind",
            "step",
            "--value",
            "step2b",
        ],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-token-raw-rejected",
        "validate-token",
        &["--token", "bad value"],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-token-implement-bail",
        "validate-token",
        &["--token-kind", "bail", "--token", "review-required"],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-terminal-valid",
        "validate-terminal-state",
        STALL_TERMINAL_ARGS,
        &[("terminal.env", STALL_TERMINAL)],
    ),
    StallRecoveryFixture::new(
        "stall-terminal-partial",
        "validate-terminal-state",
        STALL_TERMINAL_ARGS,
        &[(
            "terminal.env",
            "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\n",
        )],
    ),
    StallRecoveryFixture::new(
        "stall-seed-fresh",
        "seed-terminal-state",
        &["--implement-tmpdir", "{sandbox}"],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-seed-rewrite",
        "seed-terminal-state",
        &[
            "--implement-tmpdir",
            "{sandbox}",
            "--stall-step",
            "8a",
            "--phase",
            "ci-initial",
        ],
        &[("ship-pr-state.sh", "KEEP=yes\nSTALL_STEP=9\nPHASE=merge\n")],
    ),
    StallRecoveryFixture::new(
        "stall-clear",
        "clear-stall",
        &["--implement-tmpdir", "{sandbox}"],
        &[(
            "ship-pr-state.sh",
            "KEEP=yes\nSTALL_TRACKING=true\nSTALL_STEP=8\n",
        )],
    ),
    StallRecoveryFixture::new(
        "stall-public-valid",
        "validate-tier-b-public-file",
        STALL_PUBLIC_ARGS,
        &[
            ("public.md", "Sanitized report\n"),
            ("stall-recovery-sensitive-corpus.env", "secret-value\n"),
        ],
    ),
    StallRecoveryFixture::new(
        "stall-public-sensitive",
        "validate-tier-b-public-file",
        STALL_PUBLIC_ARGS,
        &[
            ("public.md", "Found secret-value\n"),
            ("stall-recovery-sensitive-corpus.env", "secret-value\n"),
        ],
    ),
    StallRecoveryFixture::new(
        "stall-dev-clone",
        "is-larch-dev-clone",
        STALL_DEV_ARGS,
        &[("skills/implement/SKILL.md", "fixture\n")],
    ),
    StallRecoveryFixture::new(
        "stall-dev-clone-forked",
        "is-larch-dev-clone",
        STALL_DEV_ARGS,
        &[
            ("skills/implement/SKILL.md", "fixture\n"),
            ("ship-pr-state.sh", "FORKED_TARGET=true\n"),
        ],
    ),
    StallRecoveryFixture::new(
        "stall-report-compose-tier-a",
        "compose-report",
        STALL_REPORT_COMPOSE_ARGS,
        STALL_REPORT_COMPOSE_SEEDS,
    )
    .with_environment(STALL_REPORT_ENVIRONMENT),
    StallRecoveryFixture::new(
        "stall-report-populate-sensitive-corpus",
        "populate-sensitive-corpus",
        STALL_REPORT_CORPUS_ARGS,
        STALL_REPORT_CORPUS_SEEDS,
    ),
    StallRecoveryFixture::new(
        "stall-report-chat-sensitive",
        "chat-print",
        STALL_REPORT_CORPUS_ARGS,
        STALL_REPORT_CHAT_SEEDS,
    ),
    StallRecoveryFixture::new(
        "stall-report-dedup-dry-run",
        "dedup-tier-a-report",
        STALL_REPORT_CORPUS_ARGS,
        &[],
    )
    .with_environment(STALL_DRY_RUN_ENVIRONMENT),
    StallRecoveryFixture::new("stall-classify-checks-signal", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env", "--bail-reason", "checks-child-failed", "--stall-step", "3", "--exit-code", "-15"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nPHASE=checks\n")]),
    StallRecoveryFixture::new("stall-classify-no-stall", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env"], &[]),
    StallRecoveryFixture::new("stall-classify-abandoned-checks", "classify", &["--implement-tmpdir", "{sandbox}"], &[("session-env.sh", "LARCH_RUN_ID=parity-run\n"), ("bgjob/.keep", ""), ("registry/parity-run-implement-step3-checks.env", STALL_ABANDONED_REGISTRY)])
        .with_environment(STALL_ABANDONED_ENVIRONMENT),
    StallRecoveryFixture::new("stall-classify-ordinary-text", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nSTALL_STEP=2\nPHASE=implementation\nBAIL_REASON=manifest-missing\nDETAIL=pytest failed\n")]),
    StallRecoveryFixture::new("stall-classify-postmerge-failure", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nSTALL_STEP=postmerge-flush\nPHASE=postmerge\nMERGE_RESULT=merged\nBAIL_REASON=redaction-failed\nEXIT_CODE=4\n")]),
    StallRecoveryFixture::new("stall-classify-postmerge-expected", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nSTALL_STEP=postmerge-flush\nPHASE=postmerge\nMERGE_RESULT=merged\nBAIL_REASON=preterminal-outcome\nEXIT_CODE=4\n")]),
    StallRecoveryFixture::new("stall-classify-resume-hint", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nSTALL_STEP=2\nPHASE=implementation\nBAIL_REASON=manifest-missing\n")]),
    StallRecoveryFixture::new("stall-classify-same-cause-repeat", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/stall-recovery-attempts.env"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nSTALL_STEP=2\nPHASE=implementation\nBAIL_REASON=manifest-missing\nDETAIL=pytest failed\n"), ("stall-recovery-attempts.env", "version=1\nattempt_count=1\nattempt.1.signature=8dbffb4b3b2ca6235a138773299358b72f8d75f46f1380895e82f222aa53f049\n")]),
    StallRecoveryFixture::new("stall-classify-generic-current-publish", "classify", STALL_GENERIC_ARGS, &[("terminal.env", STALL_GENERIC_CURRENT)]),
    StallRecoveryFixture::new("stall-classify-generic-fallback", "classify", STALL_GENERIC_ARGS, &[("terminal.env", STALL_GENERIC_FALLBACK)]),
    StallRecoveryFixture::new("stall-init-attempts", "init-attempts", &["--implement-tmpdir", "{sandbox}"], &[]),
    StallRecoveryFixture::new("stall-record-attempt", "record-attempt", &["--implement-tmpdir", "{sandbox}", "--class", "test-failure", "--signature", "sig-1", "--resume-hint", "step2-impl"], &[("stall-recovery-attempts.env", "version=1\r\ncreated_utc=2026-01-01T00:00:00+00:00\r\n")]),
    StallRecoveryFixture::new("stall-retry-policy", "retry-policy", &["--class", "transient-infra"], &[]),
    StallRecoveryFixture::new("stall-normalize-outcome", "normalize-outcome", &["--implement-tmpdir", "{sandbox}"], &[("ship-pr-state.sh", "STALL_TRACKING=false\nMERGE_RESULT=merged\nPR_NUMBER=42\n")]),
    StallRecoveryFixture::new("stall-normalize-issue", "normalize-issue-env", &["--implement-tmpdir", "{sandbox}", "--issue-stdout-file", "{sandbox}/issue.out", "--issue-exit-code", "0"], &[("issue.out", "ISSUES_FAILED=0\nISSUE_1_NUMBER=42\nISSUE_1_URL=https://github.com/o/r/issues/42\n")]),
    StallRecoveryFixture::new("stall-normalize-file-report", "normalize-file-failure-report-env", &["--implement-tmpdir", "{sandbox}", "--file-failure-report-env", "{sandbox}/file.env"], &[("file.env", "FILE_FAILURE_REPORT_STATUS=filed\nFILE_FAILURE_REPORT_URL=https://github.com/o/r/issues/42\n")]),
    StallRecoveryFixture::new("stall-record-escalation", "record-escalation", &["--implement-tmpdir", "{sandbox}", "--site", "step2", "--trigger", "step2-impl", "--step", "2", "--phase", "implementation", "--dispatcher", "codex", "--exit-code", "1"], &[]),
];

#[test]
#[rustfmt::skip]
fn every_text_classifier_branch_matches_the_frozen_python_table() {
    let python = find_executable("python3");
    let fixture = fixture_directory().join("stall_recovery_reference.py");
    for line in include_str!("../../../fixtures/rust-parity/stall-classifier-cases.tsv").lines().skip(1) {
        let [name, text, bail, step, detail, exit, implement] = line.split('\t').collect::<Vec<_>>().try_into().expect("seven columns");
        let detail = detail == "true";
        let implement = implement == "true";
        let output = Command::new(&python)
            .args([path_text(&fixture), "classify-text", "--text", text, "--bail", bail, "--step", step,
                "--detail-valid", if detail { "true" } else { "false" }, "--exit-code", exit,
                "--implement", if implement { "true" } else { "false" }])
            .output().expect("run frozen classifier");
        assert!(output.status.success(), "Python classifier failed for {name}");
        let result = classify_text(ClassifyTextInput { text, bail, step, detail_log_valid: detail, exit_code: exit, implement });
        let expected = format!("FAILURE_CLASS={}\nCLASSIFIED_HINT={}\nPATTERN={}\n", result.failure_class, result.resume_hint, result.pattern);
        assert_eq!(String::from_utf8(output.stdout).expect("UTF-8"), expected, "classifier parity case {name}");
    }
}

#[test]
fn stall_recovery_commands_and_outer_classifier_branches_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("stall_recovery_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");
    for fixture in STALL_RECOVERY_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct SessionLifecycleFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    environment: &'static [(&'static str, &'static str)],
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl SessionLifecycleFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.command))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust_program = Program::new(rust).args(
            ["session", self.command]
                .into_iter()
                .chain(self.arguments.iter().copied()),
        );
        for (key, value) in self.environment {
            python_program = python_program.env(key, value);
            rust_program = rust_program.env(key, value);
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self.normalization.to_vec(),
        }
    }
}

/// Environment shared by every lifecycle case that needs an expanded plugin root.
const PLUGIN_ROOT_ENVIRONMENT: &[(&str, &str)] = &[("CLAUDE_PLUGIN_ROOT", "{sandbox}")];
const SANDBOX_ONLY: &[NormalizationRule] = &[NormalizationRule::SandboxRoot];
const CLEANUP_NORMALIZATION: &[NormalizationRule] = &[
    NormalizationRule::SandboxRoot,
    NormalizationRule::Rfc3339Utc,
    NormalizationRule::ProcessIdentity,
];
/// One implement session bound to the clone and identity the match case queries.
const IMPLEMENT_KEEPALIVE: &str = "CLONE_PATH=/clone/for/parity\nSESSION_ID=S1\n";
/// A sibling session in the same root bound to a different identity.
const OTHER_KEEPALIVE: &str = "CLONE_PATH=/clone/for/parity\nSESSION_ID=S2\n";

const SESSION_LIFECYCLE_CASES: &[SessionLifecycleFixture] = &[
    SessionLifecycleFixture {
        name: "session-require-plugin-root-expanded",
        command: "require-plugin-root",
        arguments: &[],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-require-plugin-root-empty",
        command: "require-plugin-root",
        arguments: &[],
        environment: &[("CLAUDE_PLUGIN_ROOT", "")],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-require-plugin-root-unexpanded",
        command: "require-plugin-root",
        arguments: &[],
        environment: &[("CLAUDE_PLUGIN_ROOT", "${CLAUDE_PLUGIN_ROOT}")],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-require-plugin-root-unrecognized",
        command: "require-plugin-root",
        arguments: &["--bogus"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-missing-path",
        command: "validate-design-tmpdir",
        arguments: &[],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-allowed",
        command: "validate-design-tmpdir",
        arguments: &["{sandbox}/.tmp/claude-design-parity"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[(".tmp/claude-design-parity/.keep", "")],
        normalization: SANDBOX_ONLY,
    },
    // Not a sandbox path: every platform's temporary root is itself allowlisted,
    // on Linux through `/tmp` and on macOS through `TMPDIR`. `/usr` is a real
    // directory on both, so the rejected path resolves to itself either way.
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-outside-allowlist",
        command: "validate-design-tmpdir",
        arguments: &["/usr/larch-parity-not-a-session"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-relative",
        command: "validate-design-tmpdir",
        arguments: &["relative/design"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-dot-segment",
        command: "validate-design-tmpdir",
        arguments: &["{sandbox}/.tmp/../escape"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-unrecognized",
        command: "validate-design-tmpdir",
        arguments: &["--bogus"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-missing-output",
        command: "write-id",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-unrecognized",
        command: "write-id",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-outside-allowed-root",
        command: "write-id",
        arguments: &["--output", "/larch-parity-not-a-session/session-id"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-preserves-existing-identity",
        command: "write-id",
        arguments: &["--output", "{sandbox}/.tmp/claude-design-parity/session-id"],
        environment: &[],
        seeds: &[(".tmp/claude-design-parity/session-id", "PRESERVED\n")],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-missing-dir",
        command: "cleanup-tmpdir",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-outside-allowed-root",
        command: "cleanup-tmpdir",
        arguments: &["--dir", "/larch-parity-not-a-session"],
        environment: &[],
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-unrecognized",
        command: "cleanup-tmpdir",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-removes-session",
        command: "cleanup-tmpdir",
        arguments: &["--dir", "{sandbox}/.tmp/claude-design-parity"],
        environment: &[],
        seeds: &[
            (".tmp/claude-design-parity/nested/artifact.txt", "payload\n"),
            (".tmp/claude-design-parity/session-id", "ID\n"),
        ],
        normalization: CLEANUP_NORMALIZATION,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-cache-sessions-root",
        command: "cleanup-tmpdir",
        arguments: &[
            "--dir",
            "{sandbox}/xdg/larch/sessions/claude-implement-cache",
        ],
        environment: &[("XDG_CACHE_HOME", "{sandbox}/xdg")],
        seeds: &[(
            "xdg/larch/sessions/claude-implement-cache/artifact.txt",
            "payload\n",
        )],
        normalization: CLEANUP_NORMALIZATION,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-missing-target",
        command: "cleanup-tmpdir",
        arguments: &["--dir", "{sandbox}/.tmp/claude-design-absent"],
        environment: &[],
        seeds: &[],
        normalization: CLEANUP_NORMALIZATION,
    },
    SessionLifecycleFixture {
        name: "session-resolve-implement-tmpdir-no-match",
        command: "resolve-implement-tmpdir",
        arguments: &["--cwd", "/clone/without/session"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-resolve-implement-tmpdir-session-bound",
        command: "resolve-implement-tmpdir",
        arguments: &["--cwd", "/clone/for/parity"],
        environment: &[("LARCH_TOKEN_SESSION_ID", "S1")],
        seeds: &[
            (
                ".home/.cache/larch/sessions/claude-implement-alpha/design-export/manifest.env",
                "MANIFEST=1\n",
            ),
            (
                ".home/.cache/larch/sessions/claude-implement-alpha/.larch-keepalive",
                IMPLEMENT_KEEPALIVE,
            ),
            (
                ".home/.cache/larch/sessions/claude-implement-beta/review-round-summary.md",
                "# round\n",
            ),
            (
                ".home/.cache/larch/sessions/claude-implement-beta/.larch-keepalive",
                OTHER_KEEPALIVE,
            ),
        ],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-resolve-implement-tmpdir-unrecognized",
        command: "resolve-implement-tmpdir",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
];

/// One `progress` verb compared against the frozen Python reference.
///
/// Every case pins `--repo-root` to a path that cannot exist, so the clone hash
/// and therefore every seeded and asserted cache path stay sandbox independent.
struct ProgressFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    stdin: Option<&'static str>,
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl ProgressFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python)
            .args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.command))
                    .chain(self.arguments.iter().copied()),
            )
            .env("LARCH_TEST_CACHE_HOME", PROGRESS_CACHE_HOME);
        let mut rust_program = Program::new(rust)
            .args(
                ["progress", self.command]
                    .into_iter()
                    .chain(self.arguments.iter().copied()),
            )
            .env("LARCH_TEST_CACHE_HOME", PROGRESS_CACHE_HOME);
        if let Some(input) = self.stdin {
            python_program = python_program.stdin(input.as_bytes());
            rust_program = rust_program.stdin(input.as_bytes());
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self.normalization.to_vec(),
        }
    }
}

const PROGRESS_CACHE_HOME: &str = "{sandbox}/cache";
/// A clone path that cannot exist, so its hash is identical in every sandbox.
const PROGRESS_CLONE: &str = "/larch-parity-clone";
/// `sha256("/larch-parity-clone")[:16]`, the clone directory both owners derive.
const PROGRESS_CLONE_DIR: &str = "cache/larch/progress/d8b96cde3cb3f56e";
const PROGRESS_POINTER: &str = "cache/larch/progress/d8b96cde3cb3f56e/current";
const PROGRESS_LOG: &str = "cache/larch/progress/d8b96cde3cb3f56e/run-1/breadcrumbs.log";
const PROGRESS_ACTIVE_SEED: &[(&str, &str)] = &[
    (PROGRESS_POINTER, "run-1\n"),
    (PROGRESS_LOG, "[design 1] first\n[implement 5] second\n"),
];
const STAMP_ONLY: &[NormalizationRule] = &[NormalizationRule::StatuslineStamp];
const STARTUP_PAYLOAD: &str =
    r#"{"workspace": {"current_dir": "/larch-parity-clone"}, "source": "startup"}"#;
const RESUME_PAYLOAD: &str =
    r#"{"workspace": {"current_dir": "/larch-parity-clone"}, "source": "resume"}"#;
const STATUSLINE_PAYLOAD: &str = r#"{"workspace": {"current_dir": "/larch-parity-clone"}}"#;

const PROGRESS_CASES: &[ProgressFixture] = &[
    ProgressFixture {
        name: "progress-activate",
        command: "activate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "run-1"],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-activate-missing-run-id",
        command: "activate",
        arguments: &["--repo-root", PROGRESS_CLONE],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-activate-reserved-run-id",
        command: "activate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "current"],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-active-run",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--skill",
            "implement",
            "--step",
            "5",
            "code",
            "review",
            "started",
        ],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-rejects-a-url",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--skill",
            "implement",
            "--step",
            "5",
            "see",
            "https://example.invalid/pr",
        ],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-missing-skill",
        command: "note",
        arguments: &["--repo-root", PROGRESS_CLONE, "--step", "5", "text"],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-explicit-run",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--run-id",
            "run-2",
            "--skill",
            "design",
            "--step",
            "3",
            "other",
            "run",
        ],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-without-an-active-pointer",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--skill",
            "design",
            "--step",
            "3",
            "no",
            "pointer",
        ],
        stdin: None,
        seeds: &[(PROGRESS_LOG, "[design 1] first\n")],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-deactivate-wrong-owner",
        command: "deactivate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "run-2"],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-deactivate-owner",
        command: "deactivate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "run-1"],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-clear",
        command: "clear",
        arguments: &["--repo-root", PROGRESS_CLONE],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-clear-without-state",
        command: "clear",
        arguments: &["--repo-root", PROGRESS_CLONE],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-active",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: STAMP_ONLY,
    },
    ProgressFixture {
        name: "progress-statusline-torn-log",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[
            (PROGRESS_POINTER, "run-1\n"),
            (
                PROGRESS_LOG,
                "[design 1] first\n[implement 5] partial without a newline",
            ),
        ],
        normalization: STAMP_ONLY,
    },
    ProgressFixture {
        name: "progress-statusline-non-breadcrumb-log",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[
            (PROGRESS_POINTER, "run-1\n"),
            (PROGRESS_LOG, "garbage without a marker\n"),
        ],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-missing-state",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-torn-pointer",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[
            (PROGRESS_POINTER, "run"),
            (PROGRESS_LOG, "[design 1] first\n"),
        ],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-empty-payload",
        command: "statusline",
        arguments: &[],
        stdin: Some(""),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-session-reset-startup",
        command: "session-reset",
        arguments: &[],
        stdin: Some(STARTUP_PAYLOAD),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-session-reset-resume",
        command: "session-reset",
        arguments: &[],
        stdin: Some(RESUME_PAYLOAD),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
];

#[test]
fn progress_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("progress_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in PROGRESS_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct PhaseDetailFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
    environment: &'static [(&'static str, &'static str)],
}

impl PhaseDetailFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path, python_path: &str) -> ParityCase {
        let python = self.environment.iter().fold(
            Program::new(python)
                .args(
                    std::iter::once(path_text(fixture))
                        .chain(std::iter::once(self.command))
                        .chain(self.arguments.iter().copied()),
                )
                .env("PYTHONPATH", python_path),
            |program, (key, value)| program.env(key, value),
        );
        let rust = self.environment.iter().fold(
            Program::new(rust).args(
                ["progress", self.command]
                    .into_iter()
                    .chain(self.arguments.iter().copied()),
            ),
            |program, (key, value)| program.env(key, value),
        );
        ParityCase {
            name: self.name,
            python,
            rust,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const PHASE_DETAIL_CASES: &[PhaseDetailFixture] = &[
    PhaseDetailFixture {
        name: "progress-phase-detail-missing-rounds-root",
        command: "render-phase-detail",
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-no-gantt-explicit-value",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/rounds", "--no-gantt=unexpected"],
        seeds: &[("rounds/.keep", "")],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-help",
        command: "render-phase-detail",
        arguments: &["--help"],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-design-round-meta-missing-round-dir",
        command: "write-design-round-meta",
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta-help",
        command: "write-implement-round-meta",
        arguments: &["--help"],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-no-rounds",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/rounds", "--no-gantt"],
        seeds: &[("rounds/.keep", "")],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-rendered-round",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/rounds",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--findings-file",
            "{sandbox}/findings.jsonl",
            "--no-gantt",
        ],
        seeds: &[
            (
                "rounds/round-1/round-meta.json",
                "{\n  \"tally\": {\"ACCEPTED_COUNT\": \"2\", \"REJECTED_COUNT\": \"1\", \"EXONERATED_COUNT\": \"0\", \"NEUTRAL_COUNT\": \"1\", \"OOS_PROPOSED_COUNT\": \"1\", \"OOS_ACCEPTED_COUNT\": \"1\", \"OOS_REJECTED_COUNT\": \"0\"},\n  \"summary\": {\"panel\": {\"total_slot_count\": 3}},\n  \"collector\": \"TOOL=codex\\nSTATUS=FAILED\\nREVIEWER_FILE=codex-specialist-arch-output.txt\"\n}\n",
            ),
            (
                "rounds/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"codex-specialist-arch-output.txt\"}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t-\timplement\t-\t1\t100\t200\nv1\tvendor\t-\t-\t-\tcodex\tcodex-review\t110\t190\t-\tcodex-specialist-arch-output.txt\t-\tcomplete\n",
            ),
            (
                "findings.jsonl",
                "{\"outcome\":\"accepted\",\"reviewer_slots\":[\"codex-specialist-arch-output.txt\"]}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-top-n-zero",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/rounds",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--findings-file",
            "{sandbox}/findings.jsonl",
            "--top-n",
            "0",
            "--no-gantt",
        ],
        seeds: &[
            (
                "rounds/round-1/round-meta.json",
                "{\n  \"tally\": {\"ACCEPTED_COUNT\": \"2\", \"REJECTED_COUNT\": \"1\", \"EXONERATED_COUNT\": \"0\", \"NEUTRAL_COUNT\": \"1\", \"OOS_PROPOSED_COUNT\": \"1\", \"OOS_ACCEPTED_COUNT\": \"1\", \"OOS_REJECTED_COUNT\": \"0\"},\n  \"summary\": {\"panel\": {\"total_slot_count\": 3}},\n  \"collector\": \"TOOL=codex\\nSTATUS=FAILED\\nREVIEWER_FILE=codex-specialist-arch-output.txt\"\n}\n",
            ),
            (
                "rounds/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"codex-specialist-arch-output.txt\"}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t-\timplement\t-\t1\t100\t200\nv1\tvendor\t-\t-\t-\tcodex\tcodex-review\t110\t190\t-\tcodex-specialist-arch-output.txt\t-\tcomplete\n",
            ),
            (
                "findings.jsonl",
                "{\"outcome\":\"accepted\",\"reviewer_slots\":[\"codex-specialist-arch-output.txt\"]}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-design-round-meta",
        command: "write-design-round-meta",
        arguments: &["--round-dir", "{sandbox}/design/plan-review/round-1"],
        seeds: &[
            (
                "design/plan-review/round-1/voting-tally.md",
                "## Findings\n| FINDING_1 | detail | accepted |\n| OOS_1 | detail | rejected |\n",
            ),
            (
                "design/plan-review/round-1/plan-review-slots.ndjson",
                "{\"slot\":\"cursor-plan-arch\",\"tool\":\"cursor\",\"output\":\"cursor-plan-arch-output.txt\",\"vendor\":\"cursor\"}\n",
            ),
            (
                "design/plan-review/round-1/revise/revise.env",
                "REVISE_STATUS=clean\nREVISE_TIER=major\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta",
        command: "write-implement-round-meta",
        arguments: &["--round-dir", "{sandbox}/review/round-1"],
        seeds: &[
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\tvoting_result\tscope\tv1_vote\tv1_severity\nFINDING_1\taccepted\tin_scope\tYES\tmajor\nOOS_1\taccepted\toos\tYES\tmajor\n",
            ),
            (
                "review/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"codex-specialist-arch-output.txt\"}\n",
            ),
            ("review/round-1/prune-nit.env", "PRUNED_COUNT=1\n"),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-classification-bonus-and-fallback",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/plan-review",
            "--skill",
            "design",
            "--no-gantt",
        ],
        seeds: &[
            (
                "plan-review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"4\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"1\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":3}}}\n",
            ),
            (
                "plan-review/round-1/plan-review-prune-label-map.tsv",
                "slot\thuman_label\nplan-requirements\tCursor-Pragmatic\nplan-architecture\tCodex-Arch\n",
            ),
            (
                "plan-review/round-1/findings-classification.tsv",
                "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_severity\tscope\nFINDING_SOLE\tSolo-Reviewer\taccepted\tYES\tminor\tin_scope\nFINDING_MULTI\tMulti-A, Multi-B\taccepted\tYES\tminor\tin_scope\nFINDING_WHITESPACE\tCursor-Pragmatic Codex-Arch\taccepted\tYES\tminor\tin_scope\nFINDING_PARTIAL\tCursor-Pragmatic trailing-text\taccepted\tYES\tminor\tin_scope\nOOS_1\tOos-Reviewer\taccepted\tYES\tmajor\toos\n",
            ),
        ],
        environment: &[("LARCH_UNIQUE_FINDER_BONUS", "0.25")],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-attribution-historical-shapes",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/plan-review",
            "--skill",
            "design",
            "--no-gantt",
        ],
        seeds: &[
            (
                "plan-review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"3\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "plan-review/round-1/plan-review-prune-label-map.tsv",
                "slot\thuman_label\nknown\tKnown\n",
            ),
            (
                "plan-review/round-1/findings-classification.tsv",
                "finding_id\tfinding_reviewers\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nFINDING_1\t\tcodex-specialist-ignored-output.txt\taccepted\tYES\tminor\tin_scope\nFINDING_2\tKnown Known\tignored\taccepted\tYES\tminor\tin_scope\nFINDING_3\tUnknown Reviewer\tignored\taccepted\tYES\tminor\tin_scope\n",
            ),
            (
                "plan-review/round-1/review.output-files.dropped-slots",
                "dyn-custom-codex\tcodex\ttransport-failed\n",
            ),
        ],
        environment: &[("LARCH_UNIQUE_FINDER_BONUS", "0.25")],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-attempts-and-token-costs",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--token-ledger",
            "{sandbox}/tokens.jsonl",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"1\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t1782345600\timplement\t-\t1\t1782345600\t1782345610\t10\t0\t0\t0\t1\nv1\tround\t1782345620\timplement\t-\t1\t1782345620\t1782345640\t20\t0\t0\t0\t2\nv1\tvendor\t1782345608\timplement\t-\tcodex\tcodex-review\t1782345602\t1782345608\t6\tcodex-specialist-arch-output.txt\t0\tcomplete\nv1\tvendor\t1782345638\timplement\t-\tcursor\tcursor-review\t1782345622\t1782345638\t16\tcursor-specialist-edge-output.txt\t0\tsignal\n",
            ),
            (
                "tokens.jsonl",
                "{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.6-terra\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:05Z\"}\n{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.6-luna\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:06Z\"}\n{\"type\":\"vendor\",\"vendor\":\"cursor\",\"model\":\"cursor-grok-4.6-high\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:07Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-sonnet-4-6\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:08Z\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-gantt-hostile-width",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"1\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t-\timplement\t-\t1\t100\t200\nv1\tvendor\t-\t-\t-\tcursor\tcursor-review\t110\t190\t80\tcursor-specialist-very-long-review-focus-name-for-layout-output-retry.txt\t-\tcomplete\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-security-oos-zero-artifact",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/review", "--no-gantt"],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"1\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nOOS_1\tarch.txt\taccepted\tYES\tmajor\toos\n",
            ),
            (
                "review/round-1/findings-oos.md",
                "### OOS_1: [OUT_OF_SCOPE] [security] private item\n- **Focus area**: security\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-security-oos-id-boundary",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/review", "--no-gantt"],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"1\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nOOS_1\tarch.txt\taccepted\tYES\tminor\toos\n",
            ),
            (
                "review/round-1/findings-oos.md",
                "### OOS_10: [OUT_OF_SCOPE] [security] unrelated item\n- **Focus area**: security\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-security-oos-unclosed-fence",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/review", "--no-gantt"],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"1\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nOOS_1\tarch.txt\taccepted\tYES\tmajor\toos\n",
            ),
            (
                "review/round-1/findings-oos.md",
                "### OOS_1: [OUT_OF_SCOPE] unclosed fenced field\n```\nfocus-area=security\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-token-rate-overrides",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--token-ledger",
            "{sandbox}/tokens.jsonl",
            "--no-gantt",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t1782345600\timplement\t-\t1\t1782345600\t1782345610\t10\t0\t0\t0\t-\n",
            ),
            (
                "tokens.jsonl",
                "{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.6-sol\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:05Z\"}\n{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.4-mini\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:06Z\"}\n{\"type\":\"vendor\",\"vendor\":\"cursor\",\"model\":\"composer-2.5\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:07Z\"}\n{\"type\":\"vendor\",\"vendor\":\"cursor\",\"model\":\"cursor-grok-4.6-high\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:08Z\"}\n",
            ),
        ],
        environment: &[
            ("LARCH_CODEX_INPUT_RATE_PER_M", "bad"),
            ("LARCH_RATE_CODEX_INPUT", "8.25"),
            ("LARCH_RATE_CODEX_CACHE_READ", "0.90"),
            ("LARCH_RATE_CODEX_MINI_INPUT", "1.75"),
            ("LARCH_RATE_CODEX_MINI_CACHE_READ", "0.20"),
            ("LARCH_RATE_CURSOR_INPUT", "3.25"),
            ("LARCH_RATE_CURSOR_CACHE_READ", "0.80"),
            ("LARCH_CURSOR_GROK_INPUT_RATE_PER_M", "7.25"),
            ("LARCH_CURSOR_GROK_CACHE_READ_RATE_PER_M", "0.70"),
        ],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-claude-sub-model-buckets",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--token-ledger",
            "{sandbox}/tokens.jsonl",
            "--no-gantt",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t1782345600\timplement\t-\t1\t1782345600\t1782345610\t10\t0\t0\t0\t-\n",
            ),
            (
                "tokens.jsonl",
                "{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-sonnet-4-6\",\"input\":1000000,\"cache_create\":1000000,\"ts\":\"2026-06-25T00:00:05Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-haiku-4-5\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:06Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-fable-5\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:07Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-sonnet-4-6[1m]\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:08Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"raw\":\"claude_review\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:09Z\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-partial-and-historical-rounds",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/rounds", "--no-gantt"],
        seeds: &[
            ("rounds/round-0/round-meta.json", "{}\n"),
            ("rounds/round-01/round-meta.json", "{}\n"),
            ("rounds/round-1/inflight.txt", "still running\n"),
            ("rounds/round-2/round-meta.json", "{not valid JSON\n"),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-design-round-meta-security-and-collector",
        command: "write-design-round-meta",
        arguments: &["--round-dir", "{sandbox}/design/plan-review/round-1"],
        seeds: &[
            (
                "design/plan-review/round-1/voting-tally.md",
                "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n| OOS_1 | accepted |\n",
            ),
            (
                "design/plan-review/round-1/findings-oos.md",
                "### OOS_1: security item\nfocus-area=security\n",
            ),
            (
                "design/plan-review/round-1/plan-review-slots.ndjson",
                "{\"slot\":\"cursor-plan-requirements\",\"tool\":\"cursor\",\"output\":\"cursor-plan-requirements-output.txt\",\"vendor\":\"cursor\",\"resolved_model\":\"cursor-model\",\"focus_area\":\"rêview 😀\"}\n",
            ),
            (
                "design/plan-review/round-1/round-summary.env",
                "COLLECT_FAILURE_COUNT=1\n",
            ),
            (
                "design/collector-results.env",
                "REVIEWER_FILE=ok-output.txt\nTOOL=cursor\nSTATUS=OK\n\nREVIEWER_FILE=cursor-plan-requirements-output.txt\nTOOL=cursor\nSTATUS=FAILED\n",
            ),
            (
                "design/plan-review/round-1/revise/revise.env",
                "REVISE_STATUS=ok-fallback\nREVISE_TIER=primary\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta-canonical-and-difficulty",
        command: "write-implement-round-meta",
        arguments: &["--round-dir", "{sandbox}/review/round-1"],
        seeds: &[
            (
                "review/round-1/voting-tally.md",
                "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n| FINDING_2 | rejected |\n| FINDING_3 | rejected |\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nFINDING_1\tarch.txt\taccepted\tYES\tminor\tin_scope\nFINDING_2\tarch.txt\trejected\tNO\tminor\tin_scope\nFINDING_3\tarch.txt\trejected\tNO\tminor\toos\nOOS_1\tarch.txt\taccepted\tYES\tminor\toos\n",
            ),
            (
                "review/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"arch.txt\"}\n",
            ),
            ("review/round-1/review-tally.env", "OOS_ACCEPTED_COUNT=2\n"),
            ("review/round-1/prune-nit.env", "PRUNED_COUNT=1\n"),
            (
                "review/round-1/difficulty-rating.json",
                "{\"panel_tier\":\"HARD\",\"applied_tier\":\"HARD\",\"round_cap\":3,\"codex_model_role\":\"default\",\"override_source\":\"operator\",\"audit_evaluated\":true,\"audit_upgrade\":\"true\",\"escalated_round\":true,\"escalations\":[{\"round\":2,\"from_tier\":\"MODERATE\",\"to_tier\":\"HARD\"}]}\n",
            ),
            (
                "review/round-1/scout-difficulty-rating.raw.json",
                "{\"predicted_tier\":\"TRIVIAL\",\"confidence\":\"low\",\"rationale\":\"unclear small diff\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta-relative-path",
        command: "write-implement-round-meta",
        arguments: &["--round-dir", "round"],
        seeds: &[
            (
                "round/voting-tally.md",
                "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n",
            ),
            (
                "round/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"arch.txt\"}\n",
            ),
            (
                "round/scout-difficulty-rating.raw.json",
                "{\"predicted_tier\":\"TRIVIAL\",\"confidence\":\"low\",\"rationale\":\"small scope\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-output-file",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/rounds",
            "--no-gantt",
            "--output",
            "{sandbox}/output/review-detail.md",
        ],
        seeds: &[("rounds/.keep", ""), ("output/.keep", "")],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-output-file-relative-path",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "rounds",
            "--no-gantt",
            "--output",
            "output/review-detail.md",
        ],
        seeds: &[("rounds/.keep", ""), ("output/.keep", "")],
        environment: &[],
    },
];

#[test]
fn phase_detail_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("progress_phase_detail_reference.py");
    let python_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../python")
        .canonicalize()
        .expect("python source path")
        .to_string_lossy()
        .into_owned();
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in PHASE_DETAIL_CASES {
        let case = fixture.build(&python, &python_fixture, &rust, &python_path);
        let golden = golden_directory.join(format!("{}.golden.json", fixture.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[cfg(unix)]
#[test]
fn phase_detail_public_artifacts_keep_the_legacy_writer_mode() {
    let sandbox = TempDir::new().expect("sandbox");
    let round = sandbox.path().join("round");
    fs::create_dir(&round).expect("round directory");
    let binary = env!("CARGO_BIN_EXE_larch");

    let metadata = Command::new(binary)
        .args([
            "progress",
            "write-implement-round-meta",
            "--round-dir",
            round.to_str().expect("round path"),
        ])
        .status()
        .expect("write metadata");
    assert!(metadata.success());

    let rounds = sandbox.path().join("rounds");
    fs::create_dir(&rounds).expect("rounds directory");
    let output = sandbox.path().join("phase-detail.md");
    let rendered = Command::new(binary)
        .args([
            "progress",
            "render-phase-detail",
            "--rounds-root",
            rounds.to_str().expect("rounds path"),
            "--no-gantt",
            "--output",
            output.to_str().expect("output path"),
        ])
        .status()
        .expect("write phase detail");
    assert!(rendered.success());

    for artifact in [round.join("round-meta.json"), output] {
        let mode = fs::metadata(&artifact)
            .expect("artifact metadata")
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o644, "{}", artifact.display());
    }
}

struct RenderingFixture {
    name: &'static str,
    domain: &'static str,
    verb: &'static str,
    arguments: &'static [&'static str],
    stdin: Option<&'static str>,
    seeds: &'static [(&'static str, &'static str)],
}

impl RenderingFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python).args(
            [path_text(fixture).to_owned(), self.verb.to_owned()]
                .into_iter()
                .chain(self.arguments.iter().map(|value| (*value).to_owned())),
        );
        let mut rust_program = Program::new(rust).args(
            [self.domain.to_owned(), self.verb.to_owned()]
                .into_iter()
                .chain(self.arguments.iter().map(|value| (*value).to_owned())),
        );
        if let Some(input) = self.stdin {
            python_program = python_program.stdin(input.as_bytes());
            rust_program = rust_program.stdin(input.as_bytes());
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const GANTT_ROWS_TSV: &str =
    "codex-arch\t10\t95\ncursor-edge\t0\t120\nclaude-security-specialist\t40\t60\n";
const GROWTH_TSV: &str = "key\tlabel\t2026-01\t2026-02\t2026-03\nA\tBug\t1\t5\t9\nB\tTask\t0\t2\t12\nCD\tChore\t3\t3\t3\n";
const GANTT_ROWS_SEED: &[(&str, &str)] = &[("rows.tsv", GANTT_ROWS_TSV)];

const RENDERING_CASES: &[RenderingFixture] = &[
    RenderingFixture {
        name: "gantt-render-help",
        domain: "gantt",
        verb: "render",
        arguments: &["--help"],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "gantt-render-missing-required",
        domain: "gantt",
        verb: "render",
        arguments: &[],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "gantt-render-surplus-argument-after-required",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "120",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
            "surplus",
        ],
        stdin: None,
        seeds: GANTT_ROWS_SEED,
    },
    RenderingFixture {
        name: "gantt-render-invalid-int",
        domain: "gantt",
        verb: "render",
        arguments: &["--width", "wide"],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "gantt-render-help-after-invalid-int",
        domain: "gantt",
        verb: "render",
        arguments: &["--width", "wide", "--help"],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "gantt-render-invalid-int-before-missing-value",
        domain: "gantt",
        verb: "render",
        arguments: &["--width", "wide", "--window-start-s"],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "gantt-render-help-after-valid-int",
        domain: "gantt",
        verb: "render",
        arguments: &["--width", "12", "--help"],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "gantt-render-nonpositive-width",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "120",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
            "--width",
            "0",
        ],
        stdin: None,
        seeds: GANTT_ROWS_SEED,
    },
    RenderingFixture {
        name: "gantt-render-default-width",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "120",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
        ],
        stdin: None,
        seeds: GANTT_ROWS_SEED,
    },
    RenderingFixture {
        name: "gantt-render-explicit-narrow-width",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "-30",
            "--window-end-s",
            "120",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
            "--width",
            "13",
        ],
        stdin: None,
        seeds: GANTT_ROWS_SEED,
    },
    RenderingFixture {
        name: "gantt-render-no-overlapping-row",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "500",
            "--window-end-s",
            "600",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
        ],
        stdin: None,
        seeds: GANTT_ROWS_SEED,
    },
    RenderingFixture {
        name: "gantt-render-empty-rows",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "60",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
        ],
        stdin: None,
        seeds: &[("rows.tsv", "")],
    },
    RenderingFixture {
        name: "gantt-render-malformed-column-count",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "60",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
        ],
        stdin: None,
        seeds: &[("rows.tsv", "only\ttwo\n")],
    },
    RenderingFixture {
        name: "gantt-render-malformed-bounds",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "60",
            "--rows-tsv",
            "{sandbox}/rows.tsv",
        ],
        stdin: None,
        seeds: &[("rows.tsv", "label\tstart\t9\n")],
    },
    RenderingFixture {
        name: "gantt-render-unreadable-rows",
        domain: "gantt",
        verb: "render",
        arguments: &[
            "--window-start-s",
            "0",
            "--window-end-s",
            "60",
            "--rows-tsv",
            "{sandbox}/absent.tsv",
        ],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "analyze-issues-render-chart-help",
        domain: "analyze-issues",
        verb: "render-chart",
        arguments: &["--help"],
        stdin: None,
        seeds: &[],
    },
    RenderingFixture {
        name: "analyze-issues-render-chart-file",
        domain: "analyze-issues",
        verb: "render-chart",
        arguments: &["{sandbox}/growth.tsv"],
        stdin: None,
        seeds: &[("growth.tsv", GROWTH_TSV)],
    },
    RenderingFixture {
        name: "analyze-issues-render-chart-stdin",
        domain: "analyze-issues",
        verb: "render-chart",
        arguments: &[],
        stdin: Some(GROWTH_TSV),
        seeds: &[],
    },
    RenderingFixture {
        name: "analyze-issues-render-chart-empty-stdin",
        domain: "analyze-issues",
        verb: "render-chart",
        arguments: &[],
        stdin: Some(""),
        seeds: &[],
    },
    RenderingFixture {
        name: "analyze-issues-render-chart-blank-and-short-rows",
        domain: "analyze-issues",
        verb: "render-chart",
        arguments: &[],
        stdin: Some("key\tlabel\tb1\tb2\n\n   \nAB\tBug\t1\t\nshort\trow\nB\tTask\t\t7\n"),
        seeds: &[],
    },
    RenderingFixture {
        name: "analyze-issues-render-chart-surplus-argument",
        domain: "analyze-issues",
        verb: "render-chart",
        arguments: &["{sandbox}/growth.tsv", "surplus"],
        stdin: None,
        seeds: &[("growth.tsv", GROWTH_TSV)],
    },
];

#[test]
fn rendering_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("rendering_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in RENDERING_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", fixture.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn the_parity_clone_hash_is_pinned_to_its_path() {
    assert!(
        PROGRESS_CLONE_DIR.ends_with(&larch_core::progress_clone_digest(PROGRESS_CLONE)),
        "the pinned parity clone directory no longer matches its clone hash"
    );
    assert!(!Path::new(PROGRESS_CLONE).exists());
}

struct SessionEnvFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    environment: &'static [(&'static str, &'static str)],
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl SessionEnvFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        // Session writer targets seeded directly under the fixture root are
        // valid temporary-session paths. Pin TMPDIR to that root so macOS and
        // Linux exercise the same allowlist boundary.
        let mut python_program = Program::new(python)
            .args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.command))
                    .chain(self.arguments.iter().copied()),
            )
            .env("TMPDIR", "{sandbox}");
        let mut rust_program = Program::new(rust)
            .args(
                ["session", self.command]
                    .into_iter()
                    .chain(self.arguments.iter().copied()),
            )
            .env("TMPDIR", "{sandbox}");
        for (key, value) in self.environment {
            python_program = python_program.env(key, value);
            rust_program = rust_program.env(key, value);
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self.normalization.to_vec(),
        }
    }
}

/// A seeded session directory whose name never matches the tmpdir redaction rules.
const WRITER_SESSION: &str = "writer-session/.keep";
/// One prior `/implement` session-env the overwrite cases must not lose.
const PRIOR_SESSION_ENV: &str = "REPO=prior/repo\n";
/// A durable ship-pr state with no bail reason, so no run-log delegation runs.
const SHIP_PR_STATE: &str = concat!(
    "# comment\n",
    "BRANCH_NAME=feature/x\n",
    "PR_NUMBER=42\n",
    "PR_TITLE=Some title with spaces\n",
    "PR_URL=https://example.invalid/pr/42\n",
    "ISSUE_NUMBER=8058\n",
    "REPO=character-ai/larch\n",
    "MERGE=true\n",
    "RUN_ID=run-abc\n",
    "NOT_A_KEY\n",
);
/// A prior finalize state whose stall tracking outranks the durable state.
const PRIOR_FINALIZE_STATE: &str =
    "STALL_TRACKING=true\nSTALL_STEP=Step 5\nEXPECTED_SESSION_ID=sid-1\n";
/// A prior design env the refresh path recovers values from.
const PRIOR_DESIGN_ENV: &str = concat!(
    "#!/usr/bin/env bash\n",
    "export REPO_ROOT=/prior/root\n",
    "export LARCH_RUN_ID=prior-run\n",
    "export CODEX_BINARY_FOUND=true\n",
    "export LARCH_LIVE_MUTATION_OK=true\n",
);
const PLUGIN_ROOT_SANDBOX: &[(&str, &str)] = &[("CLAUDE_PLUGIN_ROOT", "{sandbox}")];

const SESSION_ENV_CASES: &[SessionEnvFixture] = &[
    SessionEnvFixture {
        name: "session-write-env-missing-arguments",
        command: "write-env",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-unrecognized",
        command: "write-env",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    // A missing required flag outranks an unexpanded plugin root, so the two
    // must not be reordered when the flag validations are grouped.
    SessionEnvFixture {
        name: "session-write-env-missing-repo-unavailable-outranks-plugin-root",
        command: "write-env",
        arguments: &["--output", "{sandbox}/writer-session/session-env.sh"],
        environment: &[("CLAUDE_PLUGIN_ROOT", "${CLAUDE_PLUGIN_ROOT}")],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-invalid-plugin-root",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
        ],
        environment: &[("CLAUDE_PLUGIN_ROOT", "${CLAUDE_PLUGIN_ROOT}")],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-dev-null",
        command: "write-env",
        arguments: &["--output", "/dev/null", "--repo-unavailable", "false"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-invalid-boolean",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
            "--auto-mode",
            "maybe",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-outside-allowed-root",
        command: "write-env",
        arguments: &[
            "--output",
            "/larch-parity-not-a-session/session-env.sh",
            "--repo-unavailable",
            "false",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-full",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo",
            "character-ai/larch",
            "--repo-root",
            "/repo/root",
            "--repo-unavailable",
            "false",
            "--claude-binary-found",
            "true",
            "--codex-binary-found",
            "false",
            "--cursor-binary-found",
            "true",
            "--auto-mode",
            "true",
            "--forked-target",
            "true",
            "--timing-ledger",
            "/tmp/ledger.tsv",
            "--token-session-id",
            "abc.123",
            "--claude-source-file",
            "/tmp/claude-source.env",
            "--prev-implement-tmpdir",
            "/tmp/prev",
            "--dynamic-archetypes",
            "1",
            "--run-id",
            "run-9",
            "--live-mutation-ok",
            "true",
        ],
        environment: PLUGIN_ROOT_SANDBOX,
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-write-env-plugin-root-only",
        command: "write-env",
        arguments: &[
            "--plugin-root-only",
            "--output",
            "{sandbox}/writer-session/plugin-root.env",
            "--value",
            "/opt/larch",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-write-env-rejects-and-keeps-prior",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
            "--run-id",
            "bad/id",
        ],
        environment: &[],
        seeds: &[
            (WRITER_SESSION, ""),
            ("writer-session/session-env.sh", PRIOR_SESSION_ENV),
        ],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-design-env-missing-arguments",
        command: "write-design-env",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-design-env-invalid-repo",
        command: "write-design-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/source-env.sh",
            "--design-tmpdir",
            "{sandbox}/writer-session",
            "--session-id",
            "sid.1",
            "--repo",
            "/bad",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    // Not a sandbox path: every platform's temporary root is itself allowlisted,
    // on Linux through `/tmp` and on macOS through `TMPDIR`. `/usr` is a real
    // directory on both, so the rejected path resolves to itself either way.
    SessionEnvFixture {
        name: "session-write-design-env-outside-allowlist",
        command: "write-design-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/source-env.sh",
            "--design-tmpdir",
            "/usr",
            "--session-id",
            "sid.1",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-design-env-requires-plugin-root-with-pid",
        command: "write-design-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/source-env.sh",
            "--design-tmpdir",
            "{sandbox}/writer-session",
            "--session-id",
            "sid.1",
            "--claude-pid",
            "4242",
        ],
        environment: &[],
        seeds: &[
            (WRITER_SESSION, ""),
            ("writer-session/source-env.sh", PRIOR_DESIGN_ENV),
        ],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-implement-env-invalid-pid",
        command: "write-implement-env",
        arguments: &["--claude-pid", "0", "--cwd", "/"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-implement-env-publishes-pointer",
        command: "write-implement-env",
        arguments: &[
            "--claude-pid",
            "4242",
            "--implement-tmpdir",
            "{sandbox}/writer-session",
            "--cwd",
            "/",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-clear-implement-pointer-invalid-pid",
        command: "clear-implement-pointer",
        arguments: &["--claude-pid", "abc"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-clear-implement-pointer-removes-pointer",
        command: "clear-implement-pointer",
        arguments: &["--claude-pid", "4242"],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/current-implement-env-4242.sh",
            "IMPLEMENT_TMPDIR=/tmp/writer-session\n",
        )],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-unrecognized",
        command: "persist-run-flags",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-missing-directory",
        command: "persist-run-flags",
        arguments: &["--implement-tmpdir", "{sandbox}/absent-session"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-invalid-boolean",
        command: "persist-run-flags",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-full",
        command: "persist-run-flags",
        arguments: &[
            "--implement-tmpdir",
            "{sandbox}/writer-session",
            "--quick-mode",
            "true",
            "--no-issues",
            "false",
            "--force-requested",
            "true",
            "--self-review-requested",
            "false",
            "--self-implement-requested",
            "true",
            "--difficulty-override",
            "MODERATE",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-unrecognized",
        command: "write-run-params",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-relative-output",
        command: "write-run-params",
        arguments: &["--output", "relative.json"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-invalid-difficulty",
        command: "write-run-params",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/run-params.json",
            "--difficulty",
            "NOPE",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-missing-directory",
        command: "write-run-params",
        arguments: &["--output", "{sandbox}/absent-session/run-params.json"],
        environment: &[],
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-write-run-params-full",
        command: "write-run-params",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/run-params.json",
            "--partition-requested",
            "true",
            "--brainstorm-requested",
            "false",
            "--approve-requested",
            "true",
            "--skip-approve-requested",
            "false",
            "--difficulty",
            "HARD",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-missing-state-file",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-outside-allowed-root",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "/usr"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-fresh",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[("writer-session/ship-pr-state.sh", SHIP_PR_STATE)],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-keeps-stall-tracking",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[
            ("writer-session/ship-pr-state.sh", SHIP_PR_STATE),
            ("writer-session/finalize-state.sh", PRIOR_FINALIZE_STATE),
        ],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-resolve-trusted-design-env-missing-required",
        command: "resolve-trusted-design-env",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-resolve-trusted-design-env-invalid-pid",
        command: "resolve-trusted-design-env",
        arguments: &[
            "--session-env-path",
            "{sandbox}/absent.sh",
            "--claude-pid",
            "0",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-resolve-trusted-design-env-no-pointer",
        command: "resolve-trusted-design-env",
        arguments: &[
            "--session-env-path",
            "{sandbox}/absent.sh",
            "--claude-pid",
            "4242",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
];

#[test]
fn session_env_writer_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("session_env_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in SESSION_ENV_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

/// One admission or gate case, addressed by its reference sub-verb and its
/// real `DOMAIN VERB` selector.
struct AdmissionFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    environment: &'static [(&'static str, &'static str)],
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl AdmissionFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.reference))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust_program = Program::new(rust).args(
            self.selector
                .iter()
                .copied()
                .chain(self.arguments.iter().copied()),
        );
        for (key, value) in self.environment {
            python_program = python_program.env(key, value);
            rust_program = rust_program.env(key, value);
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self.normalization.to_vec(),
        }
    }
}

/// A session context file whose authorization key and run id both match.
const MUTATION_CONTEXT: &str = "export LARCH_LIVE_MUTATION_OK='true'\nLARCH_RUN_ID=\"run1\"\n";
const ADMISSION_CASES: &[AdmissionFixture] = &[
    AdmissionFixture {
        name: "session-entry-gate-strict",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode",
            "implement",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-design-branch-info-continues",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode",
            "design",
            "--current-branch",
            "feature",
            "--is-main",
            "false",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
            "--branch-info-supplied",
            "true",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-invalid-mode",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode",
            "review",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-inline-spelling-reads-as-missing",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode=implement",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-unknown-argument",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-missing-value",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &["--mode"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-authorized",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1",
        ],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-run-id-mismatch",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            "--run-id",
            "run2",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1",
        ],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-non-session-root-name",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/not-a-session/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/not-a-session",
        ],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/not-a-session/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-root-outside-allowlist",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "/usr/claude-implement-parity/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "/usr/claude-implement-parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-test-deny",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1",
        ],
        environment: &[("LARCH_ISSUE_MUTATION_DENY", "true")],
        seeds: &[(
            ".home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-missing-required",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &["--run-id", "run1"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-help",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--help"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-help-consumed-as-issue-value",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "-h"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-help-after-issue",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "5", "--help"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-missing-issue",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-non-positive-issue",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "0"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-unresolvable-repo",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "8059"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-preflight-unknown-option",
        reference: "admission-preflight",
        selector: &["admission", "preflight"],
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-preflight-stray-positional",
        reference: "admission-preflight",
        selector: &["admission", "preflight"],
        arguments: &["--skip-branch-check", "extra"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-preflight-not-on-main",
        reference: "admission-preflight",
        selector: &["admission", "preflight"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-help",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &["--help"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-help-consumed-as-tmpdir-value",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &["--tmpdir", "-h"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-unrecognized",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-missing-upstream",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "blocker-all-open-no-issue",
        reference: "blocker-all-open",
        selector: &["blocker", "all-open"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "blocker-all-open-trailing-issue-flag",
        reference: "blocker-all-open",
        selector: &["blocker", "all-open"],
        arguments: &["--repo", "o/r", "--issue"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
];

#[test]
fn admission_and_gate_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("admission_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ADMISSION_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

/// One issue-query case, addressed by its reference sub-verb and its real
/// `DOMAIN VERB` selector.
struct IssueQueryFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
}

impl IssueQueryFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        ParityCase {
            name: self.name,
            python: Program::new(python).args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.reference))
                    .chain(self.arguments.iter().copied()),
            ),
            rust: Program::new(rust).args(
                self.selector
                    .iter()
                    .copied()
                    .chain(self.arguments.iter().copied()),
            ),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        }
    }
}

/// Every case stops before a GitHub client is built. The sandbox has no `gh`,
/// no `git`, and no network, so repository resolution is absent and the reads
/// these verbs would otherwise perform never start.
const ISSUE_QUERY_CASES: &[IssueQueryFixture] = &[
    IssueQueryFixture {
        name: "issue-state-missing-issue",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &[],
    },
    IssueQueryFixture {
        name: "issue-state-non-numeric-issue",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "12a"],
    },
    IssueQueryFixture {
        name: "issue-state-unknown-flag",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--bogus"],
    },
    // The scanner matches exact spellings only, so the inline form is unknown
    // rather than an `--issue` assignment.
    IssueQueryFixture {
        name: "issue-state-inline-spelling-reads-as-unknown",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue=42"],
    },
    IssueQueryFixture {
        name: "issue-state-trailing-issue-flag",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue"],
    },
    // A transposed line must not read `--repo` as the issue number.
    IssueQueryFixture {
        name: "issue-state-option-shaped-issue-value",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "--repo", "o/r"],
    },
    IssueQueryFixture {
        name: "issue-state-trailing-repo-flag",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "42", "--repo"],
    },
    IssueQueryFixture {
        name: "issue-state-unresolvable-repo",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "8167"],
    },
    IssueQueryFixture {
        name: "issue-info-trailing-field-flag",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field"],
    },
    IssueQueryFixture {
        name: "issue-info-unsupported-field",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field", "title"],
    },
    // An unrecognized token suppresses the read without stopping the scan.
    IssueQueryFixture {
        name: "issue-info-unknown-token",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["noise", "--issue", "7", "--field", "state"],
    },
    IssueQueryFixture {
        name: "issue-info-missing-issue",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--field", "state"],
    },
    IssueQueryFixture {
        name: "issue-info-unresolvable-repo",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field", "state"],
    },
    // An explicit repository still reaches an unreachable API, and this verb
    // reports that the same way it reports every other refusal.
    IssueQueryFixture {
        name: "issue-info-unreachable-explicit-repo",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field", "url", "--repo", "o/r"],
    },
    IssueQueryFixture {
        name: "issue-context-help",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--help"],
    },
    // `--help` after a value-taking option is that option's value, not help.
    IssueQueryFixture {
        name: "issue-context-help-consumed-as-issue-value",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "--help"],
    },
    IssueQueryFixture {
        name: "issue-context-trailing-issue-flag",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue"],
    },
    IssueQueryFixture {
        name: "issue-context-unknown-token",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--bogus", "x"],
    },
    IssueQueryFixture {
        name: "issue-context-missing-tmpdir",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "7", "--repo", "o/r"],
    },
    IssueQueryFixture {
        name: "issue-context-non-positive-issue",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "0", "--repo", "o/r", "--tmpdir", "{sandbox}/ctx"],
    },
    IssueQueryFixture {
        name: "issue-context-invalid-repo",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "7", "--repo", "bad", "--tmpdir", "{sandbox}/ctx"],
    },
];

#[test]
fn issue_query_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("issue_query_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ISSUE_QUERY_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

/// One issue-input case, addressed by its reference sub-verb and its real
/// `DOMAIN VERB` selector.
///
/// `parse-input` and `allocate-candidates` run end to end here, so their cases
/// compare the materialized body files as well as the contract streams.
struct IssueInputFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    stdin: &'static str,
    seeds: &'static [(&'static str, &'static str)],
}

impl IssueInputFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.reference))
                .chain(self.arguments.iter().copied()),
        );
        let rust_program = Program::new(rust).args(
            self.selector
                .iter()
                .copied()
                .chain(self.arguments.iter().copied()),
        );
        ParityCase {
            name: self.name,
            python: python_program.stdin(self.stdin.as_bytes()),
            rust: rust_program.stdin(self.stdin.as_bytes()),
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

/// The batch file every `parse-input` case parses. It exercises the OOS block,
/// the ambiguous heading that splits an item, the generic fallback, a balanced
/// fence whose payload heading is not a boundary, and a title with no body.
const BATCH_INPUT: &str = concat!(
    "### OOS_1: first\n",
    "- **Description**: body\n",
    "### Ambiguous\n",
    "pending body\n",
    "### OOS_2: second\n",
    "- **Concern**: concern body\n",
    "- **Reviewer(s)**: cursor-edge-cases, cursor-testing\n",
    "- **Vote tally**: YES=1\n",
    "- **Phase**: review\n",
    "### Generic item\n",
    "Intro line.\n",
    "```markdown\n",
    "### Payload heading inside a fence\n",
    "- **Description**: fenced field-looking line stays body\n",
    "```\n",
    "Trailing line.\n",
    "### title only\n",
);

// #8455: two inner generic boundaries and one EOF-final item must materialize
// byte-identical bodies.
const GENERIC_BOUNDARY_INPUT: &str = concat!(
    "### First generic item\n",
    "shared body\n",
    "\n",
    "### Inner generic item\n",
    "shared body\n",
    "\n",
    "### Final generic item\n",
    "shared body",
);

const ISSUE_INPUT_CASES: &[IssueInputFixture] = &[
    IssueInputFixture {
        name: "issue-parse-input-batch-file",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &[
            "--input-file",
            "{sandbox}/batch.md",
            "--output-dir",
            "{sandbox}/bodies",
        ],
        stdin: "",
        seeds: &[("batch.md", BATCH_INPUT)],
    },
    IssueInputFixture {
        name: "issue-parse-input-generic-boundaries",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &[
            "--input-file",
            "{sandbox}/generic-boundaries.md",
            "--output-dir",
            "{sandbox}/bodies",
        ],
        stdin: "",
        seeds: &[("generic-boundaries.md", GENERIC_BOUNDARY_INPUT)],
    },
    IssueInputFixture {
        name: "issue-parse-input-empty-file",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &[
            "--input-file",
            "{sandbox}/empty.md",
            "--output-dir",
            "{sandbox}/bodies",
        ],
        stdin: "",
        seeds: &[("empty.md", "")],
    },
    IssueInputFixture {
        name: "issue-parse-input-missing-input",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &[
            "--input-file",
            "{sandbox}/absent.md",
            "--output-dir",
            "{sandbox}/bodies",
        ],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-parse-input-missing-output-dir",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &["--input-file", "{sandbox}/batch.md"],
        stdin: "",
        seeds: &[("batch.md", BATCH_INPUT)],
    },
    IssueInputFixture {
        name: "issue-parse-input-no-arguments",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-parse-input-unknown-option",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &["--bogus", "x"],
        stdin: "",
        seeds: &[],
    },
    // A value-taking option that ends the line reads as an unknown option.
    IssueInputFixture {
        name: "issue-parse-input-trailing-input-flag",
        reference: "issue-parse-input",
        selector: &["issue", "parse-input"],
        arguments: &["--input-file"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-allocate-candidates-floor-and-spillover",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--total-items", "3"],
        stdin: concat!(
            "CAND 1 10 dup high\n",
            "CAND 1 11 dep medium\n",
            "CAND 2 10 dup low\n",
            "CAND 2 12 both high\n",
            "CAND 3 13 dup\n",
            "CAND 3 14 weird medium\n",
        ),
        seeds: &[],
    },
    // Every defensive drop reports its own reason, in row order.
    IssueInputFixture {
        name: "issue-allocate-candidates-malformed-rows",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--total-items", "2"],
        stdin: concat!(
            "noise\n",
            "CAND 1 10\n",
            "CAND x 10 dup\n",
            "CAND 9 10 dup\n",
            "CAND 1 0 dup\n",
            "CAND 1 abc dup\n",
        ),
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-allocate-candidates-over-cap-warns",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--total-items", "31"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-allocate-candidates-zero-items-ignores-stdin",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--total-items", "0"],
        stdin: "CAND 1 100 dup high\n",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-allocate-candidates-help",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--help"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-allocate-candidates-non-numeric-total",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--total-items", "x"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-allocate-candidates-unknown-option",
        reference: "issue-allocate-candidates",
        selector: &["issue", "allocate-candidates"],
        arguments: &["--bogus"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-list-issues-unresolvable-repo",
        reference: "issue-list-issues",
        selector: &["issue", "list-issues"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    // An explicit repository still reaches a client that cannot be built.
    IssueInputFixture {
        name: "issue-list-issues-unreachable-explicit-repo",
        reference: "issue-list-issues",
        selector: &["issue", "list-issues"],
        arguments: &["--repo", "o/r", "--closed-window-days", "30"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-list-issues-non-numeric-window",
        reference: "issue-list-issues",
        selector: &["issue", "list-issues"],
        arguments: &["--closed-window-days", "x"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-list-issues-unknown-option",
        reference: "issue-list-issues",
        selector: &["issue", "list-issues"],
        arguments: &["--bogus", "x"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-list-issues-trailing-repo-flag",
        reference: "issue-list-issues",
        selector: &["issue", "list-issues"],
        arguments: &["--repo"],
        stdin: "",
        seeds: &[],
    },
    // The corpus envelope is written even when every fetch fails, and a
    // non-numeric identifier is skipped before any read is attempted.
    IssueInputFixture {
        name: "issue-fetch-issue-details-every-read-refused",
        reference: "issue-fetch-issue-details",
        selector: &["issue", "fetch-issue-details"],
        arguments: &[
            "--numbers",
            "9,abc,,10",
            "--output",
            "{sandbox}/candidates.md",
            "--repo",
            "o/r",
        ],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-fetch-issue-details-missing-output",
        reference: "issue-fetch-issue-details",
        selector: &["issue", "fetch-issue-details"],
        arguments: &["--numbers", "9"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-fetch-issue-details-non-numeric-bound",
        reference: "issue-fetch-issue-details",
        selector: &["issue", "fetch-issue-details"],
        arguments: &[
            "--numbers",
            "9",
            "--output",
            "{sandbox}/candidates.md",
            "--max-comments",
            "x",
        ],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-fetch-issue-details-unknown-option",
        reference: "issue-fetch-issue-details",
        selector: &["issue", "fetch-issue-details"],
        arguments: &["--bogus", "x"],
        stdin: "",
        seeds: &[],
    },
    IssueInputFixture {
        name: "issue-fetch-issue-details-trailing-numbers-flag",
        reference: "issue-fetch-issue-details",
        selector: &["issue", "fetch-issue-details"],
        arguments: &["--numbers"],
        stdin: "",
        seeds: &[],
    },
];

/// One issue-creation case, addressed by its reference sub-verb and its real
/// `DOMAIN VERB` selector.
///
/// `write-sentinel` runs end to end here, so its cases compare the published
/// sentinel as well as the contract streams.
struct IssueCreateFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
    environment: &'static [(&'static str, &'static str)],
}

impl IssueCreateFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.reference))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust_program = Program::new(rust).args(
            self.selector
                .iter()
                .copied()
                .chain(self.arguments.iter().copied()),
        );
        for (key, value) in self.environment {
            python_program = python_program.env(key, value);
            rust_program = rust_program.env(key, value);
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        }
    }
}

/// Every GitHub-backed case stops before a client is built: `create-one` at
/// its authorization gate or at repository resolution, `cleanup-failed` at
/// repository resolution. The sandbox has no `gh`, no `git`, and no network.
const ISSUE_CREATE_CASES: &[IssueCreateFixture] = &[
    IssueCreateFixture {
        name: "issue-create-one-no-arguments",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-create-one-unknown-option",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &["--bogus", "x"],
        seeds: &[],
        environment: &[],
    },
    // A value-taking option that ends the line names itself, unlike the
    // input-pipeline scanners that report it as an unknown option.
    IssueCreateFixture {
        name: "issue-create-one-trailing-title-flag",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &["--title"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-create-one-dry-run",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &[
            "--title",
            "[oos] already tagged",
            "--title-prefix",
            "[OOS]",
            "--label",
            "one",
            "--label",
            "two",
            "--dry-run",
        ],
        seeds: &[],
        environment: &[],
    },
    // A dry run reads no body file, so a path that does not exist is not a
    // refusal on this path.
    IssueCreateFixture {
        name: "issue-create-one-dry-run-ignores-the-body-file",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &[
            "--title",
            "Fix",
            "--body-file",
            "{sandbox}/absent.md",
            "--dry-run",
        ],
        seeds: &[],
        environment: &[],
    },
    // Outbound redaction scrubs secrets and leaves operator paths alone.
    IssueCreateFixture {
        name: "issue-create-one-dry-run-redacts-a-secret-title",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &[
            "--title",
            "leak ghp_abcdefghijklmnopqrstuvwxyz0123456789 in /Users/operator/clone",
            "--dry-run",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-create-one-missing-body-file",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &["--title", "Fix", "--body-file", "{sandbox}/absent.md"],
        seeds: &[],
        environment: &[],
    },
    // The gate refuses before any repository is resolved or contacted.
    IssueCreateFixture {
        name: "issue-create-one-unauthorized",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &["--title", "Fix", "--body-file", "{sandbox}/body.md"],
        seeds: &[("body.md", "## Out-of-Scope Observation\nbody\n")],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-create-one-test-denied",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &["--title", "Fix", "--operator-invoked"],
        seeds: &[],
        environment: &[("LARCH_ISSUE_MUTATION_DENY", "true")],
    },
    // An operator-invoked create passes the gate and stops at resolution.
    IssueCreateFixture {
        name: "issue-create-one-unresolvable-repo",
        reference: "issue-create-one",
        selector: &["issue", "create-one"],
        arguments: &["--title", "Fix", "--operator-invoked"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-writes-the-receipt",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "{sandbox}/run/issue.sentinel",
            "--issues-created",
            "2",
            "--issues-deduplicated",
            "1",
            "--issues-failed",
            "0",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-dry-run",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "{sandbox}/issue.sentinel",
            "--issues-created",
            "2",
            "--issues-deduplicated",
            "1",
            "--issues-failed",
            "0",
            "--dry-run",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-unknown-argument",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &["--bogus"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-trailing-path-flag",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &["--path"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-empty-path-value",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &["--path", ""],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-missing-counters",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "{sandbox}/issue.sentinel",
            "--issues-created",
            "1",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-relative-path",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "issue.sentinel",
            "--issues-created",
            "0",
            "--issues-deduplicated",
            "0",
            "--issues-failed",
            "0",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-parent-segment",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "{sandbox}/../issue.sentinel",
            "--issues-created",
            "0",
            "--issues-deduplicated",
            "0",
            "--issues-failed",
            "0",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-write-sentinel-non-numeric-counter",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "{sandbox}/issue.sentinel",
            "--issues-created",
            "x",
            "--issues-deduplicated",
            "0",
            "--issues-failed",
            "0",
        ],
        seeds: &[],
        environment: &[],
    },
    // A run with failures is a successful non-write, not a refusal.
    IssueCreateFixture {
        name: "issue-write-sentinel-failures-block-the-write",
        reference: "issue-write-sentinel",
        selector: &["issue", "write-sentinel"],
        arguments: &[
            "--path",
            "{sandbox}/issue.sentinel",
            "--issues-created",
            "1",
            "--issues-deduplicated",
            "0",
            "--issues-failed",
            "2",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-cleanup-failed-no-arguments",
        reference: "issue-cleanup-failed",
        selector: &["issue", "cleanup-failed"],
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-cleanup-failed-non-numeric-issue",
        reference: "issue-cleanup-failed",
        selector: &["issue", "cleanup-failed"],
        arguments: &["--issue-number", "12a"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-cleanup-failed-unknown-option",
        reference: "issue-cleanup-failed",
        selector: &["issue", "cleanup-failed"],
        arguments: &["--bogus"],
        seeds: &[],
        environment: &[],
    },
    // The issue read before the unusable token still names the subject.
    IssueCreateFixture {
        name: "issue-cleanup-failed-trailing-repo-flag",
        reference: "issue-cleanup-failed",
        selector: &["issue", "cleanup-failed"],
        arguments: &["--issue-number", "42", "--repo"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-cleanup-failed-unresolvable-repo",
        reference: "issue-cleanup-failed",
        selector: &["issue", "cleanup-failed"],
        arguments: &["--issue-number", "42"],
        seeds: &[],
        environment: &[],
    },
];

/// Every case stops before a GitHub client is built: the two `issue` verbs at
/// their scanner, their numeric validation, their authorization gate, or at
/// repository resolution, and the two `/block-issue` verbs at their scanner or
/// at the same resolution. The sandbox has no `gh`, no `git`, and no network.
const ISSUE_DEPENDENCY_CASES: &[IssueCreateFixture] = &[
    IssueCreateFixture {
        name: "issue-add-blocked-by-no-arguments",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-blocked-by-unknown-option",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &["--bogus", "x"],
        seeds: &[],
        environment: &[],
    },
    // A value-taking option that ends the line reads as an unknown option.
    IssueCreateFixture {
        name: "issue-add-blocked-by-trailing-repo-flag",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &["--client-issue", "1", "--blocker-issue", "2", "--repo"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-blocked-by-missing-blocker",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &["--client-issue", "1"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-blocked-by-non-positive-issue",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &[
            "--client-issue",
            "0",
            "--blocker-issue",
            "2",
            "--operator-invoked",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-blocked-by-non-numeric-blocker-id",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &[
            "--client-issue",
            "1",
            "--blocker-issue",
            "2",
            "--blocker-id",
            "x",
            "--operator-invoked",
        ],
        seeds: &[],
        environment: &[],
    },
    // The gate refuses before the repository is resolved or contacted.
    IssueCreateFixture {
        name: "issue-add-blocked-by-unauthorized",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &[
            "--client-issue",
            "1",
            "--blocker-issue",
            "2",
            "--repo",
            "o/r",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-blocked-by-test-denied",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &[
            "--client-issue",
            "1",
            "--blocker-issue",
            "2",
            "--repo",
            "o/r",
        ],
        seeds: &[],
        environment: &[("LARCH_ISSUE_MUTATION_DENY", "true")],
    },
    IssueCreateFixture {
        name: "issue-add-blocked-by-unresolvable-repo",
        reference: "issue-add-blocked-by",
        selector: &["issue", "add-blocked-by"],
        arguments: &[
            "--client-issue",
            "1",
            "--blocker-issue",
            "2",
            "--operator-invoked",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-sub-issue-no-arguments",
        reference: "issue-add-sub-issue",
        selector: &["issue", "add-sub-issue"],
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    // Each verb reads only its own option names; the other pair is unknown.
    IssueCreateFixture {
        name: "issue-add-sub-issue-foreign-option",
        reference: "issue-add-sub-issue",
        selector: &["issue", "add-sub-issue"],
        arguments: &["--client-issue", "1"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-sub-issue-non-positive-issue",
        reference: "issue-add-sub-issue",
        selector: &["issue", "add-sub-issue"],
        arguments: &[
            "--parent-issue",
            "1",
            "--child-issue",
            "0",
            "--operator-invoked",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-sub-issue-unauthorized",
        reference: "issue-add-sub-issue",
        selector: &["issue", "add-sub-issue"],
        arguments: &["--parent-issue", "1", "--child-issue", "2", "--repo", "o/r"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "issue-add-sub-issue-unresolvable-repo",
        reference: "issue-add-sub-issue",
        selector: &["issue", "add-sub-issue"],
        arguments: &[
            "--parent-issue",
            "1",
            "--child-issue",
            "2",
            "--operator-invoked",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-no-arguments",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-unknown-flag",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &["--bogus"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-empty-repo-value",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &["1", "2", "--repo", ""],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-non-positive-issue",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &["0", "2", "--operator-invoked"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-requires-operator",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &["1", "2"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-invalid-timestamp",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &[
            "1",
            "2",
            "--operator-invoked",
            "--triage-controlled",
            "--expected-updated-at",
            "yesterday",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-timestamp-without-triage",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &[
            "1",
            "2",
            "--operator-invoked",
            "--expected-updated-at",
            "2026-08-07T01:02:03Z",
        ],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-invalid-repo-slug",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &["1", "2", "--operator-invoked", "--repo", "not-a-slug"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-add-blocked-by-unresolvable-repo",
        reference: "block-issue-add-blocked-by",
        selector: &["block-issue", "add-blocked-by"],
        arguments: &["1", "2", "--operator-invoked"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-remove-blocked-by-usage",
        reference: "block-issue-remove-blocked-by",
        selector: &["block-issue", "remove-blocked-by"],
        arguments: &["1"],
        seeds: &[],
        environment: &[],
    },
    IssueCreateFixture {
        name: "block-issue-remove-blocked-by-unresolvable-repo",
        reference: "block-issue-remove-blocked-by",
        selector: &["block-issue", "remove-blocked-by"],
        arguments: &["1", "2", "--operator-invoked"],
        seeds: &[],
        environment: &[],
    },
];

/// One `/triage` parity case.
///
/// Every verb here is a scanner in front of an effect the sandbox cannot
/// perform, so a case carries only its argument line and the seed tree it runs
/// against.
struct TriageFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
}

impl TriageFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.reference))
                .chain(self.arguments.iter().copied()),
        );
        let rust_program = Program::new(rust).args(
            self.selector
                .iter()
                .copied()
                .chain(self.arguments.iter().copied()),
        );
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

/// The sandbox has no `git`, no `gh`, no network, and a working directory that
/// is not a repository, so every case here stops at its scanner or at the first
/// effect it cannot perform.
#[rustfmt::skip]
const TRIAGE_CASES: &[TriageFixture] = &[
    TriageFixture {
        name: "triage-inspect-no-origin-remote",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &[],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-escaping-evidence-path",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--path", "../secrets.env"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-option-shaped-evidence-path",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--path=-rf"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-backslash-evidence-path",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--path", "a\\b"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-empty-evidence-path",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--path", ""],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-zero-max-bytes",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--max-bytes", "0"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-max-bytes-above-cap",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--max-bytes", "65537"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-non-integer-max-bytes",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--max-bytes", "many"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-missing-repo-root",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--repo-root", "no-such-directory"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-help",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--help"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-inspect-unrecognized",
        reference: "triage-inspect",
        selector: &["triage", "inspect"],
        arguments: &["--bogus"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-absent-git",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "git-version"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-absent-codex",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "codex-model-readonly", "--arg", "gpt-5.1"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-unknown-name",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "curl"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-shell-syntax-argument",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "codex-model-readonly", "--arg", "gpt;id"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-repeated-argument",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "codex-model-readonly", "--arg", "a", "--arg", "b"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-argument-on-versionless-probe",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "git-version", "--arg", "x"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-zero-max-bytes",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "git-version", "--max-bytes", "0"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-max-bytes-above-cap",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--name", "git-version", "--max-bytes", "16385"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-missing-name",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &[],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-probe-help",
        reference: "triage-probe",
        selector: &["triage", "probe"],
        arguments: &["--help"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-inconclusive-short-circuit",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "inconclusive",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "/tmp",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-unauthorized-makes-no-request",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "/tmp",
            "--body-file", "body.md",
        ],
        seeds: &[("body.md", "diagnosis\n")],
    },
    TriageFixture {
        name: "triage-apply-non-utc-timestamp",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12 10:00:00", "--triage-root", "/tmp",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-non-positive-issue",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "0", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "/tmp",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-malformed-repository",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "/tmp",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-uncanonical-session-root",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        // The sandbox is created directly inside the canonical temporary root,
        // so it proves the name half of the confinement without depending on
        // whether the platform's `/tmp` is itself a symlink.
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "{sandbox}",
            "--body-file", "{sandbox}/body.md", "--operator-invoked",
        ],
        seeds: &[("body.md", "diagnosis\n")],
    },
    TriageFixture {
        name: "triage-apply-relative-session-root",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "workdir",
            "--body-file", "body.md", "--operator-invoked",
        ],
        seeds: &[("body.md", "diagnosis\n")],
    },
    TriageFixture {
        name: "triage-apply-close-session-root-confinement",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        // A close verdict takes the same confinement as a `valid` one, ahead of
        // the artifact it would otherwise select.
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "already-fixed",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "{sandbox}",
            "--operator-invoked",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-absent-session-root",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z",
            "--triage-root", "/larch-triage-root-missing",
            "--body-file", "{sandbox}/body.md", "--operator-invoked",
        ],
        seeds: &[("body.md", "diagnosis\n")],
    },
    TriageFixture {
        name: "triage-apply-invalid-verdict-choice",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "7", "--repo", "owner/repo", "--verdict", "maybe",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "/tmp",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-missing-required-arguments",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &["--repo", "owner/repo"],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-non-integer-issue",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &[
            "seven", "--repo", "owner/repo", "--verdict", "valid",
            "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root", "/tmp",
        ],
        seeds: &[],
    },
    TriageFixture {
        name: "triage-apply-help",
        reference: "triage-apply",
        selector: &["triage", "apply"],
        arguments: &["--help"],
        seeds: &[],
    },
];

/// One `issue_wire` parity case.
///
/// The wire verbs read stdin as often as they read a file, and several publish
/// a caller-named artifact, so this fixture carries both a stdin payload and
/// the seed tree the case runs against.
struct IssueWireFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    stdin: &'static str,
    seeds: &'static [(&'static str, &'static str)],
}

impl IssueWireFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let python_program = Program::new(python)
            .args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.reference))
                    .chain(self.arguments.iter().copied()),
            )
            .stdin(self.stdin.as_bytes());
        let rust_program = Program::new(rust)
            .args(
                self.selector
                    .iter()
                    .copied()
                    .chain(self.arguments.iter().copied()),
            )
            .stdin(self.stdin.as_bytes());
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const PLAN_SEED: &str = concat!(
    "## Plan\n",
    "### UPDATED: `outside.txt`\n",
    "## Files to modify/create\n",
    "### MAY_UPDATE: `docs/optional.md`\n",
    "### UPDATED: `a/b.py`, `c/d.md`\n",
    "### REWRITTEN: skills/design/scripts/x.sh (legacy)\n",
    "## UPDATED [README.md]\n",
    "## Acceptance\n",
);
const FENCED_PLAN_SEED: &str = concat!(
    "```md\n",
    "## Files to modify/create\n",
    "### UPDATED: hidden.py\n",
    "```\n",
    "prose only\n",
);
const PLAN_BODY_SEED: &str = concat!(
    "intro\n",
    "<!-- larch:plan:start -->\n",
    "### NEW: `x.rs`\n",
    "diff_lines: 7\n",
    "<!-- larch:plan:end -->\n",
    "tail\n",
);
const BROKEN_BODY_SEED: &str = "<!-- larch:plan:start -->\nwork\n";
const SECRET_SEED: &str = "token ghp_abcdefghijklmnopqrstuvwxyz0123456789 <tag> & \"q\"\n";
const PLAN_BODY_WITH_MARKUP: &str =
    "<!-- larch:plan:start -->\n### NEW: `a.rs`\ndiff_lines: 3\n<!-- larch:plan:end -->\n";

/// The three GitHub-backed verbs stop at repository resolution: the sandbox has
/// no `gh`, no `git`, and no network, so every case here is offline.
#[rustfmt::skip]
const ISSUE_WIRE_CASES: &[IssueWireFixture] = &[
    IssueWireFixture {
        name: "untrusted-xml-escape-attr-stdin",
        reference: "untrusted-xml-escape-attr",
        selector: &["untrusted", "xml-escape-attr"],
        arguments: &[],
        stdin: "a<b>&\"c\"'d\n",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-xml-escape-attr-unknown-option",
        reference: "untrusted-xml-escape-attr",
        selector: &["untrusted", "xml-escape-attr"],
        arguments: &["x"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-redact-stream-secret",
        reference: "untrusted-redact-stream",
        selector: &["untrusted", "redact-stream"],
        arguments: &[],
        stdin: "ghp_abcdefghijklmnopqrstuvwxyz0123456789 <b>&\n",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-redact-stream-empty",
        reference: "untrusted-redact-stream",
        selector: &["untrusted", "redact-stream"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-file-block-redacts-and-escapes",
        reference: "untrusted-file-block",
        selector: &["untrusted", "file-block"],
        arguments: &["evidence", "secret.txt"],
        stdin: "",
        seeds: &[("secret.txt", SECRET_SEED)],
    },
    IssueWireFixture {
        name: "untrusted-file-block-usage",
        reference: "untrusted-file-block",
        selector: &["untrusted", "file-block"],
        arguments: &["only-one"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-content-block-text",
        reference: "untrusted-content-block",
        selector: &["untrusted", "content-block"],
        arguments: &["evidence", "--text", "a<b>&"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-content-block-stdin",
        reference: "untrusted-content-block",
        selector: &["untrusted", "content-block"],
        arguments: &["evidence"],
        stdin: "piped <x>&\n",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-content-block-help",
        reference: "untrusted-content-block",
        selector: &["untrusted", "content-block"],
        arguments: &["--help"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-content-block-unrecognized",
        reference: "untrusted-content-block",
        selector: &["untrusted", "content-block"],
        arguments: &["a", "b"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "untrusted-content-block-missing-tag",
        reference: "untrusted-content-block",
        selector: &["untrusted", "content-block"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-eligibility-lifecycle",
        reference: "issue-title-eligibility",
        selector: &["issue", "title-eligibility"],
        arguments: &["--title", "  [dOnE] fix"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-eligibility-archival-report",
        reference: "issue-title-eligibility",
        selector: &["issue", "title-eligibility"],
        arguments: &["--title=[Analysis Report] x"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-eligibility-brainstorm",
        reference: "issue-title-eligibility",
        selector: &["issue", "title-eligibility"],
        arguments: &["--title", "Brainstorm-mode"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-eligibility-leading-hyphen",
        reference: "issue-title-eligibility",
        selector: &["issue", "title-eligibility"],
        arguments: &["--title", "-starts-with-hyphen"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-eligibility-unknown-option",
        reference: "issue-title-eligibility",
        selector: &["issue", "title-eligibility"],
        arguments: &["--bogus"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-eligibility-missing-title",
        reference: "issue-title-eligibility",
        selector: &["issue", "title-eligibility"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-archival-jq-filter",
        reference: "issue-title-archival-jq",
        selector: &["issue", "title-archival-jq"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-title-archival-jq-unknown-option",
        reference: "issue-title-archival-jq",
        selector: &["issue", "title-archival-jq"],
        arguments: &["x"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-insert-signal-marker-after-lifecycle",
        reference: "issue-insert-signal-marker",
        selector: &["issue", "insert-signal-marker"],
        arguments: &["--title", "[Debated] Mixed case", "--marker", "FALSE-POSITIVE"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-insert-signal-marker-idempotent",
        reference: "issue-insert-signal-marker",
        selector: &["issue", "insert-signal-marker"],
        arguments: &["--title=[DONE] [OOS] x", "--marker=OOS"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "issue-insert-signal-marker-missing-marker",
        reference: "issue-insert-signal-marker",
        selector: &["issue", "insert-signal-marker"],
        arguments: &["--title", "x"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-scope-paths-section-bounded",
        reference: "plan-scope-paths",
        selector: &["plan", "scope-paths"],
        arguments: &["--plan-file", "plan.md"],
        stdin: "",
        seeds: &[("plan.md", PLAN_SEED)],
    },
    IssueWireFixture {
        name: "plan-scope-paths-fenced-fallback-nul",
        reference: "plan-scope-paths",
        selector: &["plan", "scope-paths"],
        arguments: &["--plan-file", "fenced.md", "-z"],
        stdin: "",
        seeds: &[("fenced.md", FENCED_PLAN_SEED)],
    },
    IssueWireFixture {
        name: "plan-scope-paths-missing-file",
        reference: "plan-scope-paths",
        selector: &["plan", "scope-paths"],
        arguments: &["--plan-file", "absent.md"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-scope-paths-missing-option",
        reference: "plan-scope-paths",
        selector: &["plan", "scope-paths"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-scope-paths-help",
        reference: "plan-scope-paths",
        selector: &["plan", "scope-paths"],
        arguments: &["--help"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-strip-body-file",
        reference: "plan-block-strip-body",
        selector: &["plan-block", "strip-body"],
        arguments: &["--file", "body.md"],
        stdin: "",
        seeds: &[("body.md", PLAN_BODY_SEED)],
    },
    IssueWireFixture {
        name: "plan-block-strip-body-malformed",
        reference: "plan-block-strip-body",
        selector: &["plan-block", "strip-body"],
        arguments: &["--file", "broken.md"],
        stdin: "",
        seeds: &[("broken.md", BROKEN_BODY_SEED)],
    },
    IssueWireFixture {
        name: "plan-block-strip-body-stdin",
        reference: "plan-block-strip-body",
        selector: &["plan-block", "strip-body"],
        arguments: &[],
        stdin: PLAN_BODY_SEED,
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-strip-body-output-file",
        reference: "plan-block-strip-body",
        selector: &["plan-block", "strip-body"],
        arguments: &["--file", "body.md", "--output", "stripped.md"],
        stdin: "",
        seeds: &[("body.md", PLAN_BODY_SEED)],
    },
    IssueWireFixture {
        name: "plan-block-strip-body-malformed-output-file",
        reference: "plan-block-strip-body",
        selector: &["plan-block", "strip-body"],
        arguments: &["--file", "broken.md", "--output", "stripped.md"],
        stdin: "",
        seeds: &[("broken.md", BROKEN_BODY_SEED)],
    },
    IssueWireFixture {
        name: "plan-block-strip-body-unrecognized",
        reference: "plan-block-strip-body",
        selector: &["plan-block", "strip-body"],
        arguments: &["--bogus"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-read-invalid-issue",
        reference: "plan-block-read",
        selector: &["plan-block", "read"],
        arguments: &["--issue", "0", "--output", "plan.txt"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-read-missing-output",
        reference: "plan-block-read",
        selector: &["plan-block", "read"],
        arguments: &["--issue", "1"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-read-unresolvable-repo",
        reference: "plan-block-read",
        selector: &["plan-block", "read"],
        arguments: &["--issue", "8171", "--output", "plan.txt"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-malformed-marker",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &["--marker", "Bad", "--issue", "1"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-unsupported-marker",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &["--marker", "bad", "--issue", "1"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-usage-without-content",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &["--marker", "plan", "--issue", "1"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-mutually-exclusive",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &["--marker", "plan", "--issue", "1", "--delete", "--content-file", "x"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-missing-content-file",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &["--marker", "plan", "--issue", "1", "--content-file", "absent.md"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-required-arguments",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "named-block-write-unresolvable-repo",
        reference: "named-block-write",
        selector: &["named-block", "write"],
        arguments: &["--marker", "plan", "--issue", "8171", "--content-file", "plan-block.md"],
        stdin: "",
        seeds: &[("plan-block.md", PLAN_BODY_WITH_MARKUP)],
    },
    IssueWireFixture {
        name: "plan-block-write-usage-without-content",
        reference: "plan-block-write",
        selector: &["plan-block", "write"],
        arguments: &["--issue", "1"],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-write-required-arguments",
        reference: "plan-block-write",
        selector: &["plan-block", "write"],
        arguments: &[],
        stdin: "",
        seeds: &[],
    },
    IssueWireFixture {
        name: "plan-block-write-invalid-issue",
        reference: "plan-block-write",
        selector: &["plan-block", "write"],
        arguments: &["--issue", "0", "--delete"],
        stdin: "",
        seeds: &[],
    },
];

/// One `/umbrella` parity case.
///
/// Four of the five verbs never leave the filesystem, so a case carries its
/// argument line and the seed tree it runs against; the harness compares the
/// published artifacts as well as the contract stream.
struct UmbrellaFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
}

impl UmbrellaFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.reference))
                .chain(self.arguments.iter().copied()),
        );
        let rust_program = Program::new(rust).args(
            self.selector
                .iter()
                .copied()
                .chain(self.arguments.iter().copied()),
        );
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

/// SHA-256 of `[LEAF OF 12] One` and its exact body.
const LEAF_ONE: &str = "9f098c3c884e445fe3249c20b4393b3eec2fc76da7a888ca928f90294109ca9d";
/// SHA-256 of `[LEAF OF 12] Two` and its exact body.
const LEAF_TWO: &str = "15ec5048c213762b103ea765030abdf57afc581af7ca42b58a245f68850360bf";

/// One durable record: leaf one in flight, leaf two still pending.
const RECORD: &str = concat!(
    r#"{"common_context":"context","dependency_edges":[],"#,
    r#""expected_updated_at":"2026-07-26T00:00:00Z","leaves":["#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst.","#,
    r#""identity":"9f098c3c884e445fe3249c20b4393b3eec2fc76da7a888ca928f90294109ca9d","#,
    r#""issue_id":"","number":"","state":"in-flight","title":"[LEAF OF 12] One","url":""},"#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nSecond.","#,
    r#""identity":"15ec5048c213762b103ea765030abdf57afc581af7ca42b58a245f68850360bf","#,
    r#""issue_id":"","number":"","state":"pending","title":"[LEAF OF 12] Two","url":""}],"#,
    r#""prepared_deps_sha256":"","prepared_input_sha256":"","repository":"owner/repo","#,
    r#""umbrella":"12","version":1}"#,
    "\n"
);

/// The same record with leaf one already bound to an issue.
const RECORD_RESOLVED: &str = concat!(
    r#"{"common_context":"context","dependency_edges":[],"#,
    r#""expected_updated_at":"2026-07-26T00:00:00Z","leaves":["#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst.","#,
    r#""identity":"9f098c3c884e445fe3249c20b4393b3eec2fc76da7a888ca928f90294109ca9d","#,
    r#""issue_id":"99","number":"34","state":"resolved","title":"[LEAF OF 12] One","#,
    r#""url":"https://example.test/issues/34"},"#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nSecond.","#,
    r#""identity":"15ec5048c213762b103ea765030abdf57afc581af7ca42b58a245f68850360bf","#,
    r#""issue_id":"","number":"","state":"pending","title":"[LEAF OF 12] Two","url":""}],"#,
    r#""prepared_deps_sha256":"","prepared_input_sha256":"","repository":"owner/repo","#,
    r#""umbrella":"12","version":1}"#,
    "\n"
);

/// The same record with leaf one's identity rewritten.
const RECORD_TAMPERED: &str = concat!(
    r#"{"common_context":"context","dependency_edges":[],"#,
    r#""expected_updated_at":"2026-07-26T00:00:00Z","leaves":["#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst.","#,
    r#""identity":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","#,
    r#""issue_id":"","number":"","state":"in-flight","title":"[LEAF OF 12] One","url":""}],"#,
    r#""prepared_deps_sha256":"","prepared_input_sha256":"","repository":"owner/repo","#,
    r#""umbrella":"12","version":1}"#,
    "\n"
);

/// One candidate row carrying leaf one's exact title and body.
const CANDIDATE_ONE_ROW: &str = concat!(
    r#"[{"number":34,"url":"https://example.test/issues/34","id":99,"#,
    r#""title":"[LEAF OF 12] One","#,
    r#""body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst."}]"#,
    "\n"
);

/// The same row twice, so no single remote issue carries the leaf.
const CANDIDATE_TWO_ROWS: &str = concat!(
    r#"[{"number":34,"url":"https://example.test/issues/34","id":99,"#,
    r#""title":"[LEAF OF 12] One","#,
    r#""body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst."},"#,
    r#"{"number":35,"url":"https://example.test/issues/35","id":100,"#,
    r#""title":"[LEAF OF 12] One","#,
    r#""body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst."}]"#,
    "\n"
);

/// The managed source snapshot a prepared partition is approved against.
const PREPARED_SNAPSHOT: &str = concat!(
    r#"{"repository": "owner/repo", "number": "12", "title": "[DESIGNING] Split", "#,
    r#""body": "Shared context.", "state": "OPEN", "updated_at": "2026-08-03T00:00:00Z"}"#,
    "\n"
);

/// The exact parent-approved batch two leaves are read from.
const PREPARED_INPUT: &str = "### One\n\nFirst body.\n\n### Two\n\nSecond body.\n";

/// The nine paths a prepared-partition invocation names, in scanner order.
const PREPARED_ARGUMENTS: &[&str] = &[
    "--snapshot",
    "{sandbox}/snapshot.json",
    "--prepared-root",
    "{sandbox}",
    "--prepared-input",
    "{sandbox}/input.txt",
    "--prepared-deps",
    "{sandbox}/deps.tsv",
    "--completion-sentinel",
    "{sandbox}/complete.sentinel",
    "--output-root",
    "{sandbox}",
    "--output",
    "{sandbox}/proposal.json",
    "--issue-input-output",
    "{sandbox}/issue-input.txt",
    "--deps-output",
    "{sandbox}/prepared-deps.tsv",
];

/// The sandbox has no `gh`, no credential, and no network, so `prepare` stops
/// at its scanner or at the identity check that precedes the first request.
/// Every other verb runs end to end against the seeded record.
#[rustfmt::skip]
const UMBRELLA_CASES: &[UmbrellaFixture] = &[
    UmbrellaFixture {
        name: "umbrella-prepare-missing-arguments",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repo", "owner/repo"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-prepare-unknown-flag",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repository", "owner/repo"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-prepare-valueless-flag",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repo"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-prepare-repeated-flag",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repo", "owner/repo", "--repo", "other/repo", "--issue", "12", "--output", "{sandbox}/s.json"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-prepare-non-boolean-managed-partition",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repo", "owner/repo", "--issue", "12", "--output", "{sandbox}/s.json", "--managed-partition", "maybe"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-prepare-malformed-repository",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repo", "owner", "--issue", "12", "--output", "{sandbox}/s.json"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-prepare-non-positive-issue",
        reference: "umbrella-prepare",
        selector: &["umbrella", "prepare"],
        arguments: &["--repo", "owner/repo", "--issue", "0", "--output", "{sandbox}/s.json"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-missing-arguments",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &[],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-mixed-modes",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &["--proposal", "record.json", "--output", "out.json", "--output-root", "{sandbox}"],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-partial-prepared-group",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &["--snapshot", "{sandbox}/snapshot.json", "--output-root", "{sandbox}"],
        seeds: &[("snapshot.json", PREPARED_SNAPSHOT)],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-round-trip",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &["--proposal", "record.json", "--output", "published.json"],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-tampered-identity",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &["--proposal", "record.json", "--output", "published.json"],
        seeds: &[("record.json", RECORD_TAMPERED)],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-absent-record",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &["--proposal", "absent.json", "--output", "published.json"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-persist-proposal-malformed-record",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &["--proposal", "record.json", "--output", "published.json"],
        seeds: &[("record.json", "{\"umbrella\": 12}\n")],
    },
    UmbrellaFixture {
        name: "umbrella-mark-in-flight-missing-arguments",
        reference: "umbrella-mark-in-flight",
        selector: &["umbrella", "mark-in-flight"],
        arguments: &["--proposal", "record.json"],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-mark-in-flight-records-state",
        reference: "umbrella-mark-in-flight",
        selector: &["umbrella", "mark-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_TWO],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-mark-in-flight-unknown-identity",
        reference: "umbrella-mark-in-flight",
        selector: &["umbrella", "mark-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", "absent"],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-mark-in-flight-already-resolved",
        reference: "umbrella-mark-in-flight",
        selector: &["umbrella", "mark-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE],
        seeds: &[("record.json", RECORD_RESOLVED)],
    },
    UmbrellaFixture {
        name: "umbrella-record-resolved-missing-arguments",
        reference: "umbrella-record-resolved",
        selector: &["umbrella", "record-resolved"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE, "--number", "34"],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-record-resolved-binds-one-issue",
        reference: "umbrella-record-resolved",
        selector: &["umbrella", "record-resolved"],
        arguments: &[
            "--proposal", "record.json", "--identity", LEAF_ONE,
            "--number", "34", "--url", "https://example.test/issues/34", "--issue-id", "99",
        ],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-record-resolved-non-positive-number",
        reference: "umbrella-record-resolved",
        selector: &["umbrella", "record-resolved"],
        arguments: &[
            "--proposal", "record.json", "--identity", LEAF_ONE,
            "--number", "0", "--url", "https://example.test/issues/34",
        ],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-record-resolved-unknown-identity",
        reference: "umbrella-record-resolved",
        selector: &["umbrella", "record-resolved"],
        arguments: &[
            "--proposal", "record.json", "--identity", "absent",
            "--number", "34", "--url", "https://example.test/issues/34",
        ],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-reconcile-missing-arguments",
        reference: "umbrella-reconcile-in-flight",
        selector: &["umbrella", "reconcile-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-reconcile-binds-a-single-match",
        reference: "umbrella-reconcile-in-flight",
        selector: &["umbrella", "reconcile-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE, "--candidates", "candidates.json"],
        seeds: &[("record.json", RECORD), ("candidates.json", CANDIDATE_ONE_ROW)],
    },
    UmbrellaFixture {
        name: "umbrella-reconcile-duplicate-matches",
        reference: "umbrella-reconcile-in-flight",
        selector: &["umbrella", "reconcile-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE, "--candidates", "candidates.json"],
        seeds: &[("record.json", RECORD), ("candidates.json", CANDIDATE_TWO_ROWS)],
    },
    UmbrellaFixture {
        name: "umbrella-reconcile-pending-leaf",
        reference: "umbrella-reconcile-in-flight",
        selector: &["umbrella", "reconcile-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_TWO, "--candidates", "candidates.json"],
        seeds: &[("record.json", RECORD), ("candidates.json", CANDIDATE_ONE_ROW)],
    },
    UmbrellaFixture {
        name: "umbrella-reconcile-absent-candidates",
        reference: "umbrella-reconcile-in-flight",
        selector: &["umbrella", "reconcile-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE, "--candidates", "absent.json"],
        seeds: &[("record.json", RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-reconcile-non-array-candidates",
        reference: "umbrella-reconcile-in-flight",
        selector: &["umbrella", "reconcile-in-flight"],
        arguments: &["--proposal", "record.json", "--identity", LEAF_ONE, "--candidates", "candidates.json"],
        seeds: &[("record.json", RECORD), ("candidates.json", "{}\n")],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-publishes-three-artifacts",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-stale-sentinel",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
            ("complete.sentinel", "GRAPH_VERIFIED=true\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-unmanaged-snapshot",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", "{\"repository\": \"owner/repo\", \"number\": \"12\", \"title\": \"Regular issue\", \"body\": \"Shared.\", \"state\": \"OPEN\", \"updated_at\": \"2026-08-03T00:00:00Z\"}\n"),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-non-positive-number",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", "{\"repository\": \"owner/repo\", \"number\": \"0\", \"title\": \"[DESIGNING] Split\", \"body\": \"Shared.\", \"state\": \"OPEN\", \"updated_at\": \"2026-08-03T00:00:00Z\"}\n"),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-closed-snapshot",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", "{\"repository\": \"owner/repo\", \"number\": \"12\", \"title\": \"[DESIGNING] Split\", \"body\": \"Shared.\", \"state\": \"CLOSED\", \"updated_at\": \"2026-08-03T00:00:00Z\"}\n"),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-malformed-snapshot",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", "[]\n"),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-absent-snapshot",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-dependency-cycle",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n2\t1\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-out-of-range-edge",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t3\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-single-leaf",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", "### One\n\nOnly body.\n"),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-leaf-titled-item",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: PREPARED_ARGUMENTS,
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", "### One\n\nFirst.\n\n### [LEAF OF 9] Two\n\nSecond.\n"),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-relative-path",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &[
            "--snapshot", "snapshot.json",
            "--prepared-root", "{sandbox}",
            "--prepared-input", "{sandbox}/input.txt",
            "--prepared-deps", "{sandbox}/deps.tsv",
            "--completion-sentinel", "{sandbox}/complete.sentinel",
            "--output-root", "{sandbox}",
            "--output", "{sandbox}/proposal.json",
            "--issue-input-output", "{sandbox}/issue-input.txt",
            "--deps-output", "{sandbox}/prepared-deps.tsv",
        ],
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-prepared-partition-escaping-input",
        reference: "umbrella-persist-proposal",
        selector: &["umbrella", "persist-proposal"],
        arguments: &[
            "--snapshot", "{sandbox}/snapshot.json",
            "--prepared-root", "{sandbox}/parent",
            "--prepared-input", "{sandbox}/input.txt",
            "--prepared-deps", "{sandbox}/parent/deps.tsv",
            "--completion-sentinel", "{sandbox}/parent/complete.sentinel",
            "--output-root", "{sandbox}",
            "--output", "{sandbox}/proposal.json",
            "--issue-input-output", "{sandbox}/issue-input.txt",
            "--deps-output", "{sandbox}/prepared-deps.tsv",
        ],
        seeds: &[
            ("snapshot.json", PREPARED_SNAPSHOT),
            ("input.txt", PREPARED_INPUT),
            ("parent/deps.tsv", ""),
        ],
    },
];

/// The prepared record after both leaves were bound to their issues.
const RESOLVED_RECORD: &str = concat!(
    r#"{"common_context":"Shared context.","dependency_edges":[{"blocked":"#,
    r#""91c8ac2b09259690bdcebe4afd7ab76f27d050cbf59f65bf891fa9633516d33c","blocker":"#,
    r#""8d0da119b1326b1d588637958269d8902ab475ef5a8521a848977daf3b42c364"}],"#,
    r#""expected_updated_at":"2026-08-03T00:00:00Z","leaves":["#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst body.","#,
    r#""identity":"8d0da119b1326b1d588637958269d8902ab475ef5a8521a848977daf3b42c364","#,
    r#""issue_id":"90","number":"21","state":"resolved","title":"[LEAF OF 12] One","#,
    r#""url":"https://example.test/issues/21"},"#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nSecond body.","#,
    r#""identity":"91c8ac2b09259690bdcebe4afd7ab76f27d050cbf59f65bf891fa9633516d33c","#,
    r#""issue_id":"91","number":"22","state":"resolved","title":"[LEAF OF 12] Two","#,
    r#""url":"https://example.test/issues/22"}],"#,
    r#""prepared_deps_sha256":"0c944e60f2140df3aaa1c17f7e4ed1e3699bcf647cf9e38623180ff5e86ac971","#,
    r#""prepared_input_sha256":"ee3b6085286d69d3db1335a83442a017180cab8a5cef2948d1186c2a4e085c00","#,
    r#""repository":"owner/repo","umbrella":"12","version":1}"#,
    "\n"
);

/// The same record with its second leaf still waiting to be filed.
const PENDING_RECORD: &str = concat!(
    r#"{"common_context":"Shared context.","dependency_edges":[{"blocked":"#,
    r#""91c8ac2b09259690bdcebe4afd7ab76f27d050cbf59f65bf891fa9633516d33c","blocker":"#,
    r#""8d0da119b1326b1d588637958269d8902ab475ef5a8521a848977daf3b42c364"}],"#,
    r#""expected_updated_at":"2026-08-03T00:00:00Z","leaves":["#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nFirst body.","#,
    r#""identity":"8d0da119b1326b1d588637958269d8902ab475ef5a8521a848977daf3b42c364","#,
    r#""issue_id":"90","number":"21","state":"resolved","title":"[LEAF OF 12] One","#,
    r#""url":"https://example.test/issues/21"},"#,
    r#"{"body":"This is a leaf of umbrella #12. Read the umbrella in full before acting.\n\nSecond body.","#,
    r#""identity":"91c8ac2b09259690bdcebe4afd7ab76f27d050cbf59f65bf891fa9633516d33c","#,
    r#""issue_id":"","number":"","state":"pending","title":"[LEAF OF 12] Two","url":""}],"#,
    r#""prepared_deps_sha256":"0c944e60f2140df3aaa1c17f7e4ed1e3699bcf647cf9e38623180ff5e86ac971","#,
    r#""prepared_input_sha256":"ee3b6085286d69d3db1335a83442a017180cab8a5cef2948d1186c2a4e085c00","#,
    r#""repository":"owner/repo","umbrella":"12","version":1}"#,
    "\n"
);

/// The two live issues that exactly carry the recorded leaves.
const RESOLVED_LEAVES: &str = concat!(
    r#"[{"number": 21, "title": "[LEAF OF 12] One", "body": "This is a leaf of umbrella #12. "#,
    r#"Read the umbrella in full before acting.\n\nFirst body."}, "#,
    r#"{"number": 22, "title": "[LEAF OF 12] Two", "body": "This is a leaf of umbrella #12. "#,
    r#"Read the umbrella in full before acting.\n\nSecond body."}]"#,
    "\n"
);

/// The same rows with one live title edited away from its recorded leaf.
const DRIFTED_LEAVES: &str = concat!(
    r#"[{"number": 21, "title": "[LEAF OF 12] Renamed", "body": "This is a leaf of umbrella #12. "#,
    r#"Read the umbrella in full before acting.\n\nFirst body."}, "#,
    r#"{"number": 22, "title": "[LEAF OF 12] Two", "body": "This is a leaf of umbrella #12. "#,
    r#"Read the umbrella in full before acting.\n\nSecond body."}]"#,
    "\n"
);

/// The exact completion sentinel the prepared partition above authorizes.
const VALID_SENTINEL: &str = concat!(
    "UMBRELLA_SENTINEL_VERSION=2\nREPOSITORY=owner/repo\nUMBRELLA_NUMBER=12\n",
    "PREPARED_INPUT_SHA256=ee3b6085286d69d3db1335a83442a017180cab8a5cef2948d1186c2a4e085c00\n",
    "PREPARED_DEPS_SHA256=0c944e60f2140df3aaa1c17f7e4ed1e3699bcf647cf9e38623180ff5e86ac971\n",
    "PREPARED_GRAPH_SHA256=5a3a565074e99ebcc5715804373065855f81e10ba1c1a2745ef3febdec9f607b\n",
    "GRAPH_VERIFIED=true\n"
);

/// The same rows with the graph digest rewritten to a value nothing produces.
const STALE_SENTINEL: &str = concat!(
    "UMBRELLA_SENTINEL_VERSION=2\nREPOSITORY=owner/repo\nUMBRELLA_NUMBER=12\n",
    "PREPARED_INPUT_SHA256=ee3b6085286d69d3db1335a83442a017180cab8a5cef2948d1186c2a4e085c00\n",
    "PREPARED_DEPS_SHA256=0c944e60f2140df3aaa1c17f7e4ed1e3699bcf647cf9e38623180ff5e86ac971\n",
    "PREPARED_GRAPH_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
    "GRAPH_VERIFIED=true\n"
);

/// The final umbrella body, carrying the record a resumed run reads.
const FINAL_UMBRELLA_BODY: &str = "Shared context.\n\n<!-- larch:umbrella-proposal -->\n";

/// The six flags `verify` names when it must publish the sentinel too.
const VERIFY_ARGUMENTS: &[&str] = &[
    "--proposal",
    "{sandbox}/record.json",
    "--leaves",
    "{sandbox}/leaves.json",
    "--sentinel-file",
    "{sandbox}/complete.sentinel",
    "--sentinel-root",
    "{sandbox}",
    "--prepared-input",
    "{sandbox}/input.txt",
    "--prepared-deps",
    "{sandbox}/deps.tsv",
];

/// The six flags `verify-completion` names, in scanner order.
const COMPLETION_ARGUMENTS: &[&str] = &[
    "--sentinel-file",
    "{sandbox}/complete.sentinel",
    "--sentinel-root",
    "{sandbox}",
    "--prepared-input",
    "{sandbox}/input.txt",
    "--prepared-deps",
    "{sandbox}/deps.tsv",
    "--repo",
    "owner/repo",
    "--issue",
    "12",
];

/// The five flags `mutate` names for the managed conversion path.
const MUTATE_ARGUMENTS: &[&str] = &[
    "--repo",
    "owner/repo",
    "--issue",
    "12",
    "--title",
    "[UMBRELLA] Split",
    "--body-file",
    "{sandbox}/body.md",
];

/// The seed tree a completed run leaves behind: record, rows, and partition.
const COMPLETION_SEEDS: &[(&str, &str)] = &[
    ("record.json", RESOLVED_RECORD),
    ("leaves.json", RESOLVED_LEAVES),
    ("input.txt", PREPARED_INPUT),
    ("deps.tsv", "1\t2\n"),
];

/// `mutate` writes one GitHub issue, and the sandbox has no `gh`, no
/// credential, and no network, so its cases stop at the scanner, the body it
/// cannot read, or the umbrella contract that body fails. `verify` and
/// `verify-completion` never leave the filesystem, so their cases run end to
/// end and the harness compares the published sentinel byte for byte.
#[rustfmt::skip]
const UMBRELLA_COMPLETION_CASES: &[UmbrellaFixture] = &[
    UmbrellaFixture {
        name: "umbrella-mutate-missing-arguments",
        reference: "umbrella-mutate",
        selector: &["umbrella", "mutate"],
        arguments: &["--repo", "owner/repo"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-mutate-non-boolean-managed-partition",
        reference: "umbrella-mutate",
        selector: &["umbrella", "mutate"],
        arguments: &[
            "--repo", "owner/repo", "--issue", "12", "--title", "[UMBRELLA] Split",
            "--body-file", "{sandbox}/body.md", "--managed-partition", "maybe",
        ],
        seeds: &[("body.md", FINAL_UMBRELLA_BODY)],
    },
    UmbrellaFixture {
        name: "umbrella-mutate-absent-body",
        reference: "umbrella-mutate",
        selector: &["umbrella", "mutate"],
        arguments: MUTATE_ARGUMENTS,
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-mutate-title-without-prefix",
        reference: "umbrella-mutate",
        selector: &["umbrella", "mutate"],
        arguments: &[
            "--repo", "owner/repo", "--issue", "12", "--title", "[DESIGNING] Split",
            "--body-file", "{sandbox}/body.md",
        ],
        seeds: &[("body.md", FINAL_UMBRELLA_BODY)],
    },
    UmbrellaFixture {
        name: "umbrella-mutate-body-without-record",
        reference: "umbrella-mutate",
        selector: &["umbrella", "mutate"],
        arguments: MUTATE_ARGUMENTS,
        seeds: &[("body.md", "Shared context.\n")],
    },
    UmbrellaFixture {
        name: "umbrella-verify-missing-arguments",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: &["--proposal", "{sandbox}/record.json"],
        seeds: &[("record.json", RESOLVED_RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-verify-partial-completion-group",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: &[
            "--proposal", "{sandbox}/record.json", "--leaves", "{sandbox}/leaves.json",
            "--sentinel-file", "{sandbox}/complete.sentinel",
        ],
        seeds: COMPLETION_SEEDS,
    },
    UmbrellaFixture {
        name: "umbrella-verify-proves-the-graph-alone",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: &[
            "--proposal", "{sandbox}/record.json", "--leaves", "{sandbox}/leaves.json",
        ],
        seeds: COMPLETION_SEEDS,
    },
    UmbrellaFixture {
        name: "umbrella-verify-publishes-the-sentinel",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: VERIFY_ARGUMENTS,
        seeds: COMPLETION_SEEDS,
    },
    UmbrellaFixture {
        name: "umbrella-verify-unresolved-leaf",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: VERIFY_ARGUMENTS,
        seeds: &[
            ("record.json", PENDING_RECORD),
            ("leaves.json", RESOLVED_LEAVES),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-drifted-leaf-title",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: VERIFY_ARGUMENTS,
        seeds: &[
            ("record.json", RESOLVED_RECORD),
            ("leaves.json", DRIFTED_LEAVES),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-absent-leaves",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: &[
            "--proposal", "{sandbox}/record.json", "--leaves", "{sandbox}/absent.json",
        ],
        seeds: &[("record.json", RESOLVED_RECORD)],
    },
    UmbrellaFixture {
        name: "umbrella-verify-non-array-leaves",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: &[
            "--proposal", "{sandbox}/record.json", "--leaves", "{sandbox}/leaves.json",
        ],
        seeds: &[("record.json", RESOLVED_RECORD), ("leaves.json", "{}\n")],
    },
    UmbrellaFixture {
        name: "umbrella-verify-stale-prepared-partition",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: VERIFY_ARGUMENTS,
        seeds: &[
            ("record.json", RESOLVED_RECORD),
            ("leaves.json", RESOLVED_LEAVES),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", ""),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-absent-sentinel-root",
        reference: "umbrella-verify",
        selector: &["umbrella", "verify"],
        arguments: &[
            "--proposal", "{sandbox}/record.json", "--leaves", "{sandbox}/leaves.json",
            "--sentinel-file", "{sandbox}/absent/complete.sentinel",
            "--sentinel-root", "{sandbox}/absent",
            "--prepared-input", "{sandbox}/absent/input.txt",
            "--prepared-deps", "{sandbox}/absent/deps.tsv",
        ],
        seeds: COMPLETION_SEEDS,
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-missing-arguments",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: &["--repo", "owner/repo", "--issue", "12"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-unknown-flag",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: &["--repository", "owner/repo"],
        seeds: &[],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-proves-the-sentinel",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: COMPLETION_ARGUMENTS,
        seeds: &[
            ("complete.sentinel", VALID_SENTINEL),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-stale-sentinel",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: COMPLETION_ARGUMENTS,
        seeds: &[
            ("complete.sentinel", STALE_SENTINEL),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-truncated-sentinel",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: COMPLETION_ARGUMENTS,
        seeds: &[
            ("complete.sentinel", "GRAPH_VERIFIED=true\n"),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-carriage-return",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: COMPLETION_ARGUMENTS,
        seeds: &[
            ("complete.sentinel", "UMBRELLA_SENTINEL_VERSION=2\r\nGRAPH_VERIFIED=true\n"),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-absent-sentinel",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: COMPLETION_ARGUMENTS,
        seeds: &[("input.txt", PREPARED_INPUT), ("deps.tsv", "1\t2\n")],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-non-positive-issue",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: &[
            "--sentinel-file", "{sandbox}/complete.sentinel", "--sentinel-root", "{sandbox}",
            "--prepared-input", "{sandbox}/input.txt", "--prepared-deps", "{sandbox}/deps.tsv",
            "--repo", "owner/repo", "--issue", "0",
        ],
        seeds: &[
            ("complete.sentinel", VALID_SENTINEL),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
    UmbrellaFixture {
        name: "umbrella-verify-completion-malformed-repository",
        reference: "umbrella-verify-completion",
        selector: &["umbrella", "verify-completion"],
        arguments: &[
            "--sentinel-file", "{sandbox}/complete.sentinel", "--sentinel-root", "{sandbox}",
            "--prepared-input", "{sandbox}/input.txt", "--prepared-deps", "{sandbox}/deps.tsv",
            "--repo", "owner", "--issue", "12",
        ],
        seeds: &[
            ("complete.sentinel", VALID_SENTINEL),
            ("input.txt", PREPARED_INPUT),
            ("deps.tsv", "1\t2\n"),
        ],
    },
];

#[test]
fn umbrella_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("umbrella_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in UMBRELLA_CASES.iter().chain(UMBRELLA_COMPLETION_CASES) {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn triage_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("triage_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in TRIAGE_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn issue_wire_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("issue_wire_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ISSUE_WIRE_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn issue_dependency_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("issue_dependency_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ISSUE_DEPENDENCY_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn issue_create_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("issue_create_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ISSUE_CREATE_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn issue_input_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("issue_input_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ISSUE_INPUT_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn session_lifecycle_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("session_lifecycle_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in SESSION_LIFECYCLE_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

const REJECTED_ANALYSIS_CANDIDATES: &str = r#"[
  {
    "candidate_id": "C1",
    "finding_hash": "finding-hash",
    "concern_hash": "concern-hash",
    "prompt_path": "work/verify-C1.md",
    "finding": {
      "finding_hash": "finding-hash",
      "concern_hash": "concern-hash",
      "source_skill": "implement",
      "run_id": "RUN-1",
      "round_num": "1",
      "canonical_finding_id": "FINDING_1",
      "synthetic_id": "REJ_CR1_1",
      "reviewer_slots": ["cursor-specialist"],
      "dissenting_slots": ["cursor"],
      "file_path": "python/foo.py",
      "line_hint": "12",
      "concern": "Missing required check",
      "prose_body": "Finding one",
      "classification_row": {},
      "vote_split": {
        "yes_votes": 1,
        "no_votes": 2,
        "yes_slots": ["cursor"],
        "no_slots": ["codex", "claude"],
        "high_severity": true
      },
      "started_at": "2026-08-14T12:00:00Z",
      "demoted_later_touched": false
    }
  }
]"#;

struct RejectedAnalysisIngestFixture {
    name: &'static str,
    candidate_id: &'static str,
    launcher_exit: &'static str,
    output: Option<&'static str>,
    dirty_sidecar: Option<&'static str>,
}

impl RejectedAnalysisIngestFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let arguments = [
            "--work-dir",
            "{sandbox}/work",
            "--candidate-id",
            self.candidate_id,
            "--output",
            "{sandbox}/work/verdict.txt",
            "--launcher-exit",
            self.launcher_exit,
        ];
        let mut seeds = vec![SeedFile::text(
            "work/candidates.json",
            REJECTED_ANALYSIS_CANDIDATES,
        )];
        if let Some(output) = self.output {
            seeds.push(SeedFile::text("work/verdict.txt", output));
        }
        if let Some(dirty_sidecar) = self.dirty_sidecar {
            seeds.push(SeedFile::text("work/verdict.txt.dirty-tree", dirty_sidecar));
        }
        ParityCase {
            name: self.name,
            python: Program::new(python).args(
                std::iter::once(path_text(fixture).to_owned())
                    .chain(std::iter::once("ingest-verdict".to_owned()))
                    .chain(arguments.into_iter().map(str::to_owned)),
            ),
            rust: Program::new(rust).args(
                ["rejected-analysis", "ingest-verdict"]
                    .into_iter()
                    .map(str::to_owned)
                    .chain(arguments.into_iter().map(str::to_owned)),
            ),
            seed_files: seeds,
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const REJECTED_ANALYSIS_INGEST_CASES: &[RejectedAnalysisIngestFixture] = &[
    RejectedAnalysisIngestFixture {
        name: "rejected-analysis-ingest-confirmed",
        candidate_id: "C1",
        launcher_exit: "0",
        output: Some(
            "{\"status\": \"confirmed\", \"current_location\": \"python/foo.py:13\", \"evidence\": \"Current code still omits the check.\"}",
        ),
        dirty_sidecar: Some("STATUS=clean\n"),
    },
    RejectedAnalysisIngestFixture {
        name: "rejected-analysis-ingest-launch-failed",
        candidate_id: "C1",
        launcher_exit: "1",
        output: None,
        dirty_sidecar: None,
    },
    RejectedAnalysisIngestFixture {
        name: "rejected-analysis-ingest-dirty-tree",
        candidate_id: "C1",
        launcher_exit: "0",
        output: Some("{}"),
        dirty_sidecar: Some("STATUS=dirty\n"),
    },
    RejectedAnalysisIngestFixture {
        name: "rejected-analysis-ingest-unknown-candidate",
        candidate_id: "C2",
        launcher_exit: "1",
        output: None,
        dirty_sidecar: None,
    },
];

#[test]
fn rejected_analysis_ingestion_has_reviewed_black_box_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("rejected_analysis_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in REJECTED_ANALYSIS_INGEST_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", fixture.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct RejectedAnalysisPrepareFixture {
    name: &'static str,
    arguments: &'static [&'static str],
}

impl RejectedAnalysisPrepareFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        ParityCase {
            name: self.name,
            python: Program::new(python).args(
                std::iter::once(path_text(fixture).to_owned())
                    .chain(std::iter::once("prepare".to_owned()))
                    .chain(self.arguments.iter().map(|argument| (*argument).to_owned())),
            ),
            rust: Program::new(rust).args(
                ["rejected-analysis", "prepare"]
                    .into_iter()
                    .map(str::to_owned)
                    .chain(self.arguments.iter().map(|argument| (*argument).to_owned())),
            ),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const REJECTED_ANALYSIS_PREPARE_CASES: &[RejectedAnalysisPrepareFixture] = &[
    RejectedAnalysisPrepareFixture {
        name: "rejected-analysis-prepare-missing-days",
        arguments: &[],
    },
    RejectedAnalysisPrepareFixture {
        name: "rejected-analysis-prepare-missing-days-value",
        arguments: &["--days"],
    },
    RejectedAnalysisPrepareFixture {
        name: "rejected-analysis-prepare-help",
        arguments: &["--help"],
    },
    RejectedAnalysisPrepareFixture {
        name: "rejected-analysis-prepare-invalid-days",
        arguments: &["--days", "nope"],
    },
    RejectedAnalysisPrepareFixture {
        name: "rejected-analysis-prepare-repository-preflight",
        arguments: &["--days", "7", "--log-root", "{sandbox}/logs"],
    },
    RejectedAnalysisPrepareFixture {
        name: "rejected-analysis-prepare-preflight-precedes-bounds",
        arguments: &[
            "--days",
            "0",
            "--verify-cap",
            "-1",
            "--log-root",
            "{sandbox}/logs",
        ],
    },
];

struct RejectedAnalysisDiagnosticFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
}

impl RejectedAnalysisDiagnosticFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        ParityCase {
            name: self.name,
            python: Program::new(python).args(
                std::iter::once(path_text(fixture).to_owned())
                    .chain(std::iter::once(self.command.to_owned()))
                    .chain(self.arguments.iter().map(|argument| (*argument).to_owned())),
            ),
            rust: Program::new(rust).args(
                ["rejected-analysis", self.command]
                    .into_iter()
                    .map(str::to_owned)
                    .chain(self.arguments.iter().map(|argument| (*argument).to_owned())),
            ),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const REJECTED_ANALYSIS_DIAGNOSTIC_CASES: &[RejectedAnalysisDiagnosticFixture] =
    &[RejectedAnalysisDiagnosticFixture {
        name: "rejected-analysis-ingest-invalid-launcher-exit",
        command: "ingest-verdict",
        arguments: &[
            "--work-dir",
            "x",
            "--candidate-id",
            "C1",
            "--output",
            "verdict.json",
            "--launcher-exit",
            "nope",
        ],
    }];

#[test]
fn rejected_analysis_preparation_has_reviewed_black_box_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("rejected_analysis_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in REJECTED_ANALYSIS_PREPARE_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", fixture.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn rejected_analysis_diagnostics_have_reviewed_black_box_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("rejected_analysis_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in REJECTED_ANALYSIS_DIAGNOSTIC_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", fixture.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn hung_command_fails_at_the_case_boundary() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let compiled_rust_fixture = compile_rust_fixture(&fixture_directory);
    let case = ParityCase {
        name: "timeout",
        python: Program::new(&python)
            .args(["-c", "import time; time.sleep(2)"])
            .timeout(Duration::from_millis(50)),
        rust: Program::new(compiled_rust_fixture.path().join("reference-command")),
        seed_files: Vec::new(),
        side_effect_records: Vec::new(),
        normalization: Vec::new(),
    };

    let error = assert_case(&case, Path::new("unused.golden.json"))
        .expect_err("hung command should fail the harness");

    assert!(error.contains("timed out after 50ms"));
}

const CLEAN_INSTALL_PARTITION_COUNT: usize = 4;

#[test]
fn rust_owned_selector_matrix_partition_0_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(0);
}

#[test]
fn rust_owned_selector_matrix_partition_1_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(1);
}

#[test]
fn rust_owned_selector_matrix_partition_2_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(2);
}

#[test]
fn rust_owned_selector_matrix_partition_3_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(3);
}

fn assert_clean_install_partition(partition: usize) {
    let fixture = clean_install_fixture();
    for (index, case) in CLEAN_INSTALL_CASES.iter().copied().enumerate() {
        if index % CLEAN_INSTALL_PARTITION_COUNT != partition {
            continue;
        }
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, case, None);
        assert_eq!(
            output.status.code(),
            Some(case.expected_exit()),
            "{} failed: {}",
            case.id,
            String::from_utf8_lossy(&output.stderr)
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        let lines: Vec<&str> = events.lines().collect();
        let expected_dispatch = clean_install_dispatch(&fixture, case);
        assert_eq!(lines.first(), Some(&"--version"), "{}", case.id);
        assert_eq!(lines.get(1), Some(&"bootstrap self-check"), "{}", case.id);
        assert_eq!(
            lines.get(2),
            Some(&expected_dispatch.as_str()),
            "{}",
            case.id
        );
        assert_eq!(lines.len(), 3, "{}", case.id);
        assert!(!fixture.root.join("bin/larch").exists(), "{}", case.id);
    }
}

#[test]
fn clean_install_validation_failures_precede_selector_dispatch() {
    let fixture = clean_install_fixture();
    let case = CLEAN_INSTALL_CASES[0];
    for failure in ["version", "target", "bootstrap"] {
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, case, Some(failure));
        assert!(
            !output.status.success(),
            "{failure} unexpectedly dispatched"
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        assert!(
            !events
                .lines()
                .any(|line| line == clean_install_dispatch(&fixture, case)),
            "{failure} reached selector dispatch"
        );
    }
}

/// Pin the public Rust-owned bootstrap envelope on both paths. The verified
/// wrapper supplies deterministic session setup without a Python continuation.
#[cfg(unix)]
#[test]
fn bootstrap_invoke_stdout_is_pinned_for_fresh_and_resume_paths() {
    let fixture = clean_install_fixture();
    let source_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical source root");
    fs::remove_dir_all(fixture.root.join("python")).expect("remove seeded Python contract");
    // The installed plugin still provides independently owned Python telemetry
    // verbs.  The assertion below proves Step 0 itself does not require the
    // retired continuation module.
    std::os::unix::fs::symlink(source_root.join("python"), fixture.root.join("python"))
        .expect("link independently owned Python runtime");
    assert!(
        !fixture
            .root
            .join("python/larch/state/bootstrap.py")
            .exists(),
        "clean-install bootstrap fixture must not need the retired Python continuation"
    );
    let bin = fixture.root.join("bin");
    fs::create_dir_all(&bin).expect("create fixture binary directory");
    let fixture_binary = bin.join("larch");
    fs::copy(&fixture.binary, &fixture_binary).expect("copy fixture binary");
    let mut permissions = fs::metadata(&fixture_binary)
        .expect("read fixture binary metadata")
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&fixture_binary, permissions).expect("make fixture binary executable");

    let bootstrap_session = fixture.root.join("bootstrap-session");
    let fresh = run_bootstrap_invoke(&fixture, &bootstrap_session, "initial");
    assert!(
        fresh.status.success(),
        "fresh bootstrap failed: {}",
        String::from_utf8_lossy(&fresh.stderr)
    );
    let routing_target = bootstrap_session.join("routing-target.env");
    fs::write(&routing_target, "prior\n").expect("write routing target");
    let routing_file = bootstrap_session.join("bootstrap-routing.env");
    fs::remove_file(&routing_file).expect("remove fresh routing envelope");
    std::os::unix::fs::symlink(&routing_target, &routing_file).expect("symlink routing envelope");
    let resume = run_bootstrap_invoke(&fixture, &bootstrap_session, "resume");
    assert!(
        resume.status.success(),
        "resume bootstrap failed: {}",
        String::from_utf8_lossy(&resume.stderr)
    );
    assert!(
        String::from_utf8_lossy(&resume.stderr)
            .contains("refusing to overwrite symlinked bootstrap-routing.env"),
        "resume must retain a hostile routing-file target: {:?}",
        String::from_utf8_lossy(&resume.stderr)
    );
    assert_eq!(
        fs::read_to_string(&routing_target).expect("read routing target"),
        "prior\n"
    );
    let token_ledger = fs::read_dir(&bootstrap_session)
        .expect("read bootstrap session")
        .flatten()
        .map(|entry| entry.path())
        .find(|path| {
            path.file_name()
                .is_some_and(|name| name.to_string_lossy().starts_with("larch-tokens-"))
        })
        .expect("Step 0 bootstrap token ledger");
    let token_rows = fs::read_to_string(token_ledger).expect("read Step 0 token ledger");
    assert!(
        token_rows.contains(r#""step":"Step 0 \u2014 preflight""#),
        "bootstrap must mark the preflight token boundary; rows: {token_rows:?}"
    );

    let expected = concat!(
        "IMPLEMENT_TMPDIR={SESSION}\n",
        "STALL_TRACKING=false\n",
        "REPO_UNAVAILABLE=true\n",
        "DEFERRED=true\n",
        "REPO_ROOT={REPO_ROOT}\n",
        "CODEX_BINARY_FOUND=false\n",
        "CURSOR_BINARY_FOUND=false\n",
        "codex_available=false\n",
        "cursor_available=false\n",
        "RUN_ID=bootstrap-session\n",
        "SELF_REVIEW_REQUESTED=true\n",
        "SELF_IMPLEMENT_REQUESTED=true\n",
        "BOOTSTRAP_NEXT=cleanup\n",
    );
    let normalize = |output: &[u8]| {
        String::from_utf8_lossy(output)
            .replace(&bootstrap_session.display().to_string(), "{SESSION}")
            .replace(
                &fixture.root.join("nested-repo").display().to_string(),
                "{REPO_ROOT}",
            )
    };
    assert_eq!(normalize(&fresh.stdout), expected);
    assert_eq!(normalize(&resume.stdout), expected);
}

/// Exercise the native continuation's successful plan, coder, and routing
/// path through the verified clean-install entrypoint.  The fixture is a
/// forked target so it does not mutate a real tracking issue or branch.
#[cfg(unix)]
#[test]
fn bootstrap_invoke_clean_install_runs_native_plan_coder_and_tail() {
    let fixture = clean_install_fixture();
    let source_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical source root");
    fs::remove_dir_all(fixture.root.join("python")).expect("remove seeded Python contract");
    std::os::unix::fs::symlink(source_root.join("python"), fixture.root.join("python"))
        .expect("link independently owned Python runtime");
    assert!(
        !fixture
            .root
            .join("python/larch/state/bootstrap.py")
            .exists(),
        "clean-install continuation must not need the retired Python owner"
    );
    let bin = fixture.root.join("bin");
    fs::create_dir_all(&bin).expect("create fixture binary directory");
    let fixture_binary = bin.join("larch");
    fs::copy(&fixture.binary, &fixture_binary).expect("copy fixture binary");
    let mut permissions = fs::metadata(&fixture_binary)
        .expect("read fixture binary metadata")
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&fixture_binary, permissions).expect("make fixture binary executable");

    let session = fixture.root.join("bootstrap-full-session");
    fs::create_dir_all(&session).expect("create bootstrap session");
    fs::write(session.join(".bootstrap-test-repo-available"), "")
        .expect("mark bootstrap fixture repository available");
    let preflight = fixture.root.join("bootstrap-full-preflight");
    fs::create_dir_all(&preflight).expect("create preflight directory");
    fs::write(
        preflight.join("plan-from-issue.txt"),
        concat!(
            "## Implementation Plan\n",
            "Move the continuation into Rust.\n\n",
            "## Test Plan\n",
            "- Exercise the public bootstrap command.\n\n",
            "review_status: approved\n",
            "rounds_completed: 1\n",
            "difficulty: MODERATE\n",
            "diff_lines: 1\n",
        ),
    )
    .expect("write preflight plan");

    let output = run_bootstrap_forked_invoke(&fixture, &session, &preflight);
    assert!(
        output.status.success(),
        "full bootstrap failed: {}\nevents: {}",
        String::from_utf8_lossy(&output.stderr),
        fs::read_to_string(&fixture.events).unwrap_or_default(),
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    for expected in [
        format!("IMPLEMENT_TMPDIR={}", session.display()),
        format!("PLAN_FILE={}", session.join("plan.txt").display()),
        "ISSUE_NUMBER=8358".to_owned(),
        "REPO=character-ai/larch".to_owned(),
        "REPO_UNAVAILABLE=false".to_owned(),
        "DEFERRED=true".to_owned(),
        "coder=claude".to_owned(),
        "ROUTE=continue".to_owned(),
        "CHECKPOINT_NEXT=continue".to_owned(),
        "REBASE_RC=0".to_owned(),
        "BOOTSTRAP_NEXT=step2".to_owned(),
    ] {
        assert!(
            stdout.contains(&format!("{expected}\n")),
            "stdout: {stdout}"
        );
    }
    assert_eq!(
        fs::read_to_string(session.join("plan.txt")).expect("read materialized plan"),
        concat!(
            "## Implementation Plan\n",
            "Move the continuation into Rust.\n\n",
            "## Test Plan\n",
            "- Exercise the public bootstrap command.\n\n",
            "diff_lines: 1\n",
        )
    );
    assert_eq!(
        fs::read_to_string(session.join("feature-description.txt"))
            .expect("read materialized feature description"),
        "Issue 8358 title\n\nIssue 8358 body"
    );
    assert_eq!(
        fs::read_to_string(session.join("bootstrap-routing.env"))
            .expect("read durable routing envelope"),
        stdout
    );
}

/// Exercise the non-forked Step 0 transaction through a local repository and
/// verified-entrypoint fixture. This covers the adoption, lease, branch, and
/// post-admission paths without contacting GitHub.
#[cfg(unix)]
#[test]
fn bootstrap_invoke_tracking_path_adopts_issue_and_activates_lease() {
    let tracking = tracking_bootstrap_fixture();
    let output =
        invoke_tracking_bootstrap(&tracking, "tracking-run-8358", "true", "true", None, false);

    assert!(
        output.status.success(),
        "tracking bootstrap failed: {}",
        String::from_utf8_lossy(&output.stderr),
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    for expected in [
        "ISSUE_NUMBER=8358",
        "RUN_ID=tracking-run-8358",
        "BRANCH_ACTION=created",
        "coder=claude",
        "ROUTE=continue",
        "BOOTSTRAP_NEXT=step2",
    ] {
        assert!(stdout.contains(expected), "stdout: {stdout}");
    }
    let branch = git_output(&tracking.repository, &["branch", "--show-current"]);
    assert_ne!(branch, "main");
    assert!(
        branch.starts_with("test-user/issue-8358-title-8358"),
        "{branch}"
    );
    assert_eq!(
        fs::read_to_string(tracking.session.join("parent-issue.md"))
            .expect("read tracking sentinel"),
        "ISSUE_NUMBER=8358\nRUN_ID=tracking-run-8358\nADOPTED=true\n"
    );
}

/// A closed issue is not adopted or mutated, but still gets a durable cleanup
/// route for the caller.
#[cfg(unix)]
#[test]
fn bootstrap_invoke_tracking_path_stops_for_closed_issue() {
    let tracking = tracking_bootstrap_fixture();
    fs::write(tracking.session.join(".bootstrap-test-issue-closed"), "")
        .expect("mark fixture issue closed");

    let output =
        invoke_tracking_bootstrap(&tracking, "closed-run-8358", "true", "true", None, false);

    assert!(
        output.status.success(),
        "closed tracking bootstrap failed: {}",
        String::from_utf8_lossy(&output.stderr),
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("IMPLEMENT_BAIL_REASON=adopted-issue-closed\n"),
        "stdout: {stdout}"
    );
    assert!(
        stdout.contains("BOOTSTRAP_NEXT=cleanup\n"),
        "stdout: {stdout}"
    );
    assert!(!tracking.session.join("parent-issue.md").exists());
}

/// The native continuation must stop with the documented failure when neither
/// external coder can pass the refreshed health gate.
#[cfg(unix)]
#[test]
fn bootstrap_invoke_tracking_path_stops_when_external_coders_are_unavailable() {
    let tracking = tracking_bootstrap_fixture();
    let output =
        invoke_tracking_bootstrap(&tracking, "degraded-run-8358", "true", "false", None, true);

    let stderr = String::from_utf8_lossy(&output.stderr);
    assert_eq!(
        output.status.code(),
        Some(2),
        "stdout: {}\nstderr: {stderr}",
        String::from_utf8_lossy(&output.stdout)
    );
    assert!(
        stderr.contains("STEP_FAILED=degraded-both-down-hard-fail"),
        "stderr: {stderr}"
    );
    assert!(
        stderr.contains("both Codex and Cursor are unavailable after health probes"),
        "stderr: {stderr}"
    );
}

#[cfg(unix)]
struct TrackingBootstrapFixture {
    fixture: CleanInstallFixture,
    repository: PathBuf,
    session: PathBuf,
    preflight: PathBuf,
    fake_bin: PathBuf,
}

#[cfg(unix)]
fn tracking_bootstrap_fixture() -> TrackingBootstrapFixture {
    let fixture = clean_install_fixture();
    let source_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical source root");
    fs::remove_dir_all(fixture.root.join("python")).expect("remove seeded Python contract");
    std::os::unix::fs::symlink(source_root.join("python"), fixture.root.join("python"))
        .expect("link Python runtime for the bounded governance seam");

    let session = fixture.root.join("bootstrap-tracking-session");
    fs::create_dir_all(&session).expect("create tracking session");
    fs::write(session.join(".bootstrap-test-repo-available"), "")
        .expect("mark bootstrap fixture repository available");
    fs::write(session.join(".bootstrap-test-tracking"), "")
        .expect("enable tracking fixture responses");

    let repository = create_bootstrap_tracking_repository(&fixture.root);
    let base_sha = git_output(&repository, &["rev-parse", "HEAD"]);
    let issue_body = tracking_issue_body(&base_sha);
    fs::write(session.join("fixture-issue-body.md"), &issue_body)
        .expect("write post-admission issue body");

    let preflight = fixture.root.join("bootstrap-tracking-preflight");
    fs::create_dir_all(&preflight).expect("create tracking preflight");
    fs::write(
        preflight.join("plan-from-issue.txt"),
        concat!(
            "## Implementation Plan\n",
            "Exercise the tracking transaction.\n\n",
            "## Test Plan\n",
            "- Run the native Step 0 path.\n\n",
            "review_status: approved\n",
            "rounds_completed: 1\n",
            "difficulty: MODERATE\n",
            "diff_lines: 1\n",
        ),
    )
    .expect("write tracking preflight plan");
    fs::write(
        preflight.join("issue.json"),
        serde_json::to_string(&serde_json::json!({
            "updatedAt": "2026-08-10T00:00:00Z",
            "body": issue_body,
            "title": "Issue 8358 title",
            "labels": [],
        }))
        .expect("serialize issue snapshot"),
    )
    .expect("write issue snapshot");

    let fake_bin = fixture.root.join("tracking-bin");
    fs::create_dir_all(&fake_bin).expect("create fake gh directory");
    let fake_gh = fake_bin.join("gh");
    write_test_executable(
        &fake_gh,
        concat!(
            "#!/bin/sh\n",
            "set -eu\n",
            "case \"${1:-}:${2:-}\" in\n",
            "  api:*dependencies/blocked_by) printf '%s\\n' '[]' ;;\n",
            "  *) printf 'unexpected gh invocation: %s\\n' \"$*\" >&2; exit 64 ;;\n",
            "esac\n",
        ),
    );
    let python = Command::new("python3")
        .args(["-c", "import sys; print(sys.executable)"])
        .output()
        .expect("resolve host Python interpreter");
    assert!(
        python.status.success(),
        "could not resolve host Python interpreter: {}",
        String::from_utf8_lossy(&python.stderr)
    );
    let python = String::from_utf8(python.stdout)
        .expect("host Python path is UTF-8")
        .trim()
        .to_owned();
    write_test_executable(
        &fake_bin.join("python3"),
        &format!("#!/bin/sh\nexec {} \"$@\"\n", shell_quote(&python)),
    );

    TrackingBootstrapFixture {
        fixture,
        repository,
        session,
        preflight,
        fake_bin,
    }
}

#[cfg(unix)]
#[allow(clippy::too_many_arguments)]
fn invoke_tracking_bootstrap(
    tracking: &TrackingBootstrapFixture,
    run_id: &str,
    self_review_requested: &str,
    self_implement_requested: &str,
    coder: Option<&str>,
    isolate_external_coders: bool,
) -> Output {
    let inherited_path = if isolate_external_coders {
        std::ffi::OsString::from("/usr/bin:/bin")
    } else {
        env::var_os("PATH").expect("test process should have PATH")
    };
    let path = env::join_paths(
        std::iter::once(tracking.fake_bin.clone()).chain(env::split_paths(&inherited_path)),
    )
    .expect("join fixture PATH");
    let mut command = Command::new(tracking.fixture.root.join("scripts/larch.sh"));
    command
        .args([
            "bootstrap",
            "invoke",
            "--mode",
            "initial",
            "--issue-number",
            "8358",
            "--run-id",
        ])
        .arg(run_id)
        .args(["--preflight-tmpdir"])
        .arg(path_text(&tracking.preflight))
        .args([
            "--self-review-requested",
            self_review_requested,
            "--self-implement-requested",
            self_implement_requested,
            "--difficulty",
            "HARD",
        ]);
    if let Some(coder) = coder {
        command.args(["--coder", coder]);
    }
    command
        .current_dir(&tracking.repository)
        .env("HOME", &tracking.fixture.home)
        .env("TMPDIR", &tracking.fixture.session)
        .env("CLAUDE_PLUGIN_ROOT", &tracking.fixture.root)
        .env("LARCH_BINARY", &tracking.fixture.wrapper)
        .env("IMPLEMENT_TMPDIR", &tracking.session)
        .env("LARCH_CLAUDE_PID", "4242")
        .env("REPO_ROOT", &tracking.repository)
        .env("CLAUDE_PROJECT_DIR", &tracking.repository)
        .env("PATH", path)
        .env("LARCH_TEST_CACHE_HOME", &tracking.fixture.root)
        .env("LARCH_STATUSLINE_DISABLE", "1");
    command.output().expect("run tracking bootstrap invoke")
}

#[cfg(unix)]
fn write_test_executable(path: &Path, contents: &str) {
    fs::write(path, contents).expect("write test executable");
    let mut permissions = fs::metadata(path)
        .expect("read test executable metadata")
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(path, permissions).expect("make test executable");
}

#[cfg(unix)]
fn create_bootstrap_tracking_repository(root: &Path) -> PathBuf {
    let origin = root.join("bootstrap-tracking-origin.git");
    let repository = root.join("bootstrap-tracking-repository");
    git_success(root, &["init", "--bare", path_text(&origin)]);
    git_success(
        root,
        &["init", "--initial-branch=main", path_text(&repository)],
    );
    git_success(
        &repository,
        &["config", "user.email", "test@example.invalid"],
    );
    git_success(&repository, &["config", "user.name", "Test User"]);
    fs::write(repository.join("README.md"), "tracking fixture\n").expect("write tracked fixture");
    git_success(&repository, &["add", "README.md"]);
    git_success(&repository, &["commit", "-m", "initial"]);
    git_success(
        &repository,
        &["remote", "add", "origin", path_text(&origin)],
    );
    git_success(&repository, &["push", "--set-upstream", "origin", "main"]);
    git_success(&repository, &["fetch", "origin", "main"]);
    repository
}

#[cfg(unix)]
fn git_success(directory: &Path, arguments: &[&str]) {
    let output = Command::new("git")
        .arg("-C")
        .arg(directory)
        .args(arguments)
        .output()
        .expect("launch git fixture command");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        arguments,
        String::from_utf8_lossy(&output.stderr)
    );
}

#[cfg(unix)]
fn git_output(directory: &Path, arguments: &[&str]) -> String {
    let output = Command::new("git")
        .arg("-C")
        .arg(directory)
        .args(arguments)
        .output()
        .expect("launch git fixture query");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        arguments,
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout)
        .expect("git output should be UTF-8")
        .trim()
        .to_owned()
}

#[cfg(unix)]
fn tracking_issue_body(base_sha: &str) -> String {
    let plan = "## Plan\nNo shared owner changes.\n";
    let plan_sha = format!("{:x}", Sha256::digest(plan.as_bytes()));
    let empty_sha = format!("{:x}", Sha256::digest(b""));
    format!(
        "<!-- larch:plan:start -->\n{plan}<!-- larch:plan:end -->\n<!-- larch:plan-receipt v1 plan_sha256={plan_sha} base_sha={base_sha} blockers_sha256={empty_sha} owners_sha256={empty_sha} -->\n"
    )
}

/// The public command must preserve the live session named by its environment,
/// even when the age gate would otherwise remove it from the cache root.
#[cfg(unix)]
#[test]
fn cleanup_run_preserves_live_session_directory() {
    let fixture = clean_install_fixture();
    let live = fixture.home.join(".cache/larch/sessions/live-session");
    fs::create_dir_all(&live).expect("create live session");
    let old = SystemTime::now()
        .checked_sub(Duration::from_secs(2 * 86_400))
        .expect("old timestamp");
    fs::File::open(&live)
        .expect("open live session")
        .set_times(fs::FileTimes::new().set_modified(old))
        .expect("age live session");

    let output = Command::new("/bin/bash")
        .arg(fixture.root.join("scripts/larch.sh"))
        .args(["cleanup", "run"])
        .env("HOME", &fixture.home)
        .env_remove("XDG_CACHE_HOME")
        .env("TMPDIR", &fixture.session)
        .env("IMPLEMENT_TMPDIR", &live)
        .env("LARCH_CLEANUP_RETENTION_DAYS", "1")
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        .env("CLEAN_INSTALL_FAILURE", "")
        .output()
        .expect("run cleanup");

    assert!(output.status.success(), "{output:?}");
    assert!(live.is_dir(), "cleanup removed a live session");
    assert!(String::from_utf8_lossy(&output.stdout).contains("CACHE_REMOVED=0"));
}

#[cfg(unix)]
#[allow(clippy::literal_string_with_formatting_args)]
#[test]
fn status_check_preserves_the_health_envelope() {
    let fixture = clean_install_fixture();
    let entrypoint = fixture.root.join("scripts/larch.sh");
    fs::write(
        &entrypoint,
        r#"#!/bin/sh
case "${1:-}:${2:-}" in
  agent:check-reviewers)
    printf '%s\n' 'CODEX_BINARY_FOUND=true' 'CURSOR_BINARY_FOUND=true' 'CODEX_PRESENT=false' 'CURSOR_PRESENT=true' 'CODEX_PROBE_DETAIL=update Codex'
    ;;
  agent:degraded-tools-gate)
    printf '%s\n' 'CODEX_STATE=probe-failed' 'CURSOR_STATE=ok' 'DEGRADED=true'
    ;;
  agent:resolve-model-pins)
    printf '%s\n' 'CURSOR_MODEL_PINS=unknown-id' 'CURSOR_MODEL_PIN_DETAIL=CURSOR_MODEL=missing' 'CODEX_MODEL_PINS=skipped' 'CODEX_MODEL_PIN_DETAIL=vendor probe not ok'
    ;;
  *) exit 1 ;;
esac
"#,
    )
    .expect("write fake larch entrypoint");
    let mut permissions = fs::metadata(&entrypoint)
        .expect("read entrypoint permissions")
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&entrypoint, permissions).expect("make entrypoint executable");

    let output = Command::new(&fixture.binary)
        .args(["status", "check"])
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .output()
        .expect("run status");

    assert!(output.status.success(), "{output:?}");
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        format!(
            concat!(
                "LARCH_PLUGIN_VERSION={}\n",
                "CODEX_BINARY_FOUND=true\n",
                "CURSOR_BINARY_FOUND=true\n",
                "CODEX_PRESENT=false\n",
                "CURSOR_PRESENT=true\n",
                "CODEX_STATE=probe-failed\n",
                "CURSOR_STATE=ok\n",
                "DEGRADED=true\n",
                "CODEX_PROBE_DETAIL=update Codex\n",
                "CURSOR_MODEL_PINS=unknown-id\n",
                "CURSOR_MODEL_PIN_DETAIL=CURSOR_MODEL=missing\n",
                "CODEX_MODEL_PINS=skipped\n",
                "CODEX_MODEL_PIN_DETAIL=vendor probe not ok\n",
            ),
            env!("CARGO_PKG_VERSION"),
        )
    );
}

#[cfg(unix)]
fn run_bootstrap_invoke(
    fixture: &CleanInstallFixture,
    session: &Path,
    mode: &str,
) -> std::process::Output {
    let session_hint = fixture.root.join(".bootstrap-test-session");
    fs::write(&session_hint, format!("{}\n", session.display()))
        .expect("write bootstrap session hint");
    let repo_root = if mode == "resume" {
        fixture.root.join("unexpected-resume-root")
    } else {
        fixture.root.join("nested-repo")
    };
    let mut command = Command::new("/bin/bash");
    command
        .arg(fixture.root.join("scripts/larch.sh"))
        .args([
            "bootstrap",
            "invoke",
            "--mode",
            mode,
            "--self-review-requested",
            "true",
            "--self-implement-requested",
            "true",
        ])
        .env("HOME", &fixture.home)
        .env("TMPDIR", &fixture.session)
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        .env("CLEAN_INSTALL_FAILURE", "")
        .env("LARCH_CLAUDE_PID", "4242")
        .env("LARCH_TEST_CACHE_HOME", &fixture.root)
        .env("XDG_CACHE_HOME", fixture.root.join("nested-cache"))
        .env("REPO_ROOT", repo_root)
        .env("LARCH_STATUSLINE_DISABLE", "1")
        .env("CLAUDE_PLUGIN_OPTION_CODEX_EFFORT", "medium")
        .env("CLAUDE_PLUGIN_OPTION_CODEX_MODEL", "plugin-codex")
        .env("CLAUDE_PLUGIN_OPTION_CURSOR_MODEL", "plugin-cursor")
        .env("LARCH_CODEX_EFFORT", "high")
        .env("LARCH_CODEX_FIX_MODEL", "fix-codex")
        .env("LARCH_CODEX_MODEL", "impl-codex")
        .env("LARCH_CODEX_REVIEW_MODEL", "review-codex")
        .env("LARCH_CODEX_VOTE_MODEL", "vote-codex")
        .env("LARCH_CURSOR_MODEL", "cursor-model")
        .env("LARCH_EXTERNAL_AUTH_RETRIES", "2")
        .env("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "17")
        .env("LARCH_PROBE_NEGATIVE_TTL_SECONDS", "3")
        .env("LARCH_PROBE_RETRIES", "4")
        .env("LARCH_PROBE_TIMEOUT_RETRIES", "5")
        .env("LARCH_PROBE_TIMEOUT_SECONDS", "6")
        .env("LARCH_PROBE_TTL_SECONDS", "7")
        .env("IMPLEMENT_TMPDIR", session);
    let output = command.output().expect("run bootstrap invoke");
    fs::remove_file(session_hint).expect("remove bootstrap session hint");
    output
}

#[cfg(unix)]
fn run_bootstrap_forked_invoke(
    fixture: &CleanInstallFixture,
    session: &Path,
    preflight: &Path,
) -> std::process::Output {
    let repo_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical test repository root");
    Command::new("/bin/bash")
        .arg(fixture.root.join("scripts/larch.sh"))
        .args([
            "bootstrap",
            "invoke",
            "--mode",
            "initial",
            "--issue-number",
            "8358",
            "--forked-target",
            "true",
            "--upstream-repo",
            "character-ai/larch",
            "--preflight-tmpdir",
            &preflight.display().to_string(),
            "--self-review-requested",
            "true",
            "--self-implement-requested",
            "true",
        ])
        .current_dir(&fixture.root)
        .env("HOME", &fixture.home)
        .env("TMPDIR", &fixture.session)
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("CLAUDE_PROJECT_DIR", repo_root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        .env("CLEAN_INSTALL_FAILURE", "")
        .env("BOOTSTRAP_TEST_SESSION", session)
        .env("IMPLEMENT_TMPDIR", session)
        .env("LARCH_CLAUDE_PID", "4242")
        .env("LARCH_TEST_CACHE_HOME", &fixture.root)
        .output()
        .expect("run forked bootstrap invoke")
}

/// Argument placeholder each clean-install case expands to the seeded session.
const CLEAN_INSTALL_SESSION_TOKEN: &str = "%SESSION%";
/// Argument placeholder each clean-install case expands to the isolated home.
const CLEAN_INSTALL_HOME_TOKEN: &str = "%HOME%";

struct CleanInstallFixture {
    _temporary: TempDir,
    root: PathBuf,
    /// Isolated home, so a verb that publishes a PID-keyed pointer stays contained.
    home: PathBuf,
    /// Seeded session directory every writer verb targets.
    session: PathBuf,
    wrapper: PathBuf,
    events: PathBuf,
    binary: PathBuf,
}

#[allow(clippy::literal_string_with_formatting_args, clippy::too_many_lines)]
fn clean_install_fixture() -> CleanInstallFixture {
    let temporary = tempfile::tempdir().expect("clean-install tempdir");
    let temporary_root = fs::canonicalize(temporary.path()).expect("canonical clean-install root");
    let root = temporary_root.join("plugin");
    let scripts = root.join("scripts");
    let manifest_directory = root.join(".claude-plugin");
    fs::create_dir_all(&scripts).expect("create clean-install scripts directory");
    fs::create_dir_all(&manifest_directory).expect("create clean-install manifest directory");
    fs::copy(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../scripts/larch.sh"),
        scripts.join("larch.sh"),
    )
    .expect("copy verified bootstrap script");
    #[cfg(unix)]
    {
        let script = scripts.join("larch.sh");
        let mut permissions = fs::metadata(&script)
            .expect("read clean-install script metadata")
            .permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(script, permissions).expect("make clean-install script executable");
    }
    fs::write(
        manifest_directory.join("plugin.json"),
        format!(
            "{{\n  \"name\": \"larch\",\n  \"version\": \"{}\"\n}}\n",
            env!("CARGO_PKG_VERSION")
        ),
    )
    .expect("write clean-install plugin manifest");
    seed_clean_install_stall_recovery_contract(&root);
    let wrapper = temporary_root.join("verified-larch");
    let wrapper_source = r#"#!/bin/sh
set -eu
if [ -n "${CLEAN_INSTALL_EVENTS:-}" ]; then
  printf '%s\n' "$*" >> "$CLEAN_INSTALL_EVENTS"
fi
bootstrap_session=${BOOTSTRAP_TEST_SESSION:-${IMPLEMENT_TMPDIR:-}}
if [ -z "$bootstrap_session" ] \
  && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] \
  && [ -r "$CLAUDE_PLUGIN_ROOT/.bootstrap-test-session" ]; then
  IFS= read -r bootstrap_session < "$CLAUDE_PLUGIN_ROOT/.bootstrap-test-session"
fi
bootstrap_repo_available=false
if [ "${BOOTSTRAP_TEST_REPO_AVAILABLE:-}" = true ] \
  || { [ -n "$bootstrap_session" ] && [ -f "$bootstrap_session/.bootstrap-test-repo-available" ]; }; then
  bootstrap_repo_available=true
fi
bootstrap_tracking=false
if [ -n "$bootstrap_session" ] && [ -f "$bootstrap_session/.bootstrap-test-tracking" ]; then
  bootstrap_tracking=true
fi
if [ -n "$bootstrap_session" ]; then
  case "${1:-}:${2:-}" in
    git:current-branch)
      printf '%s\n' 'BRANCH=bootstrap-parity'
      exit 0
      ;;
    session:setup)
      if [ "$bootstrap_repo_available" != true ]; then
        [ "${LARCH_CLAUDE_PID:-}" = 4242 ] || exit 78
        [ "${XDG_CACHE_HOME:-}" = "$CLAUDE_PLUGIN_ROOT/nested-cache" ] || exit 78
        [ "${REPO_ROOT:-}" = "$CLAUDE_PLUGIN_ROOT/nested-repo" ] || exit 78
        [ "${LARCH_STATUSLINE_DISABLE:-}" = 1 ] || exit 78
        [ "${CLAUDE_PLUGIN_OPTION_CODEX_EFFORT:-}" = medium ] || exit 78
        [ "${CLAUDE_PLUGIN_OPTION_CODEX_MODEL:-}" = plugin-codex ] || exit 78
        [ "${CLAUDE_PLUGIN_OPTION_CURSOR_MODEL:-}" = plugin-cursor ] || exit 78
        [ "${LARCH_CODEX_EFFORT:-}" = high ] || exit 78
        [ "${LARCH_CODEX_FIX_MODEL:-}" = fix-codex ] || exit 78
        [ "${LARCH_CODEX_MODEL:-}" = impl-codex ] || exit 78
        [ "${LARCH_CODEX_REVIEW_MODEL:-}" = review-codex ] || exit 78
        [ "${LARCH_CODEX_VOTE_MODEL:-}" = vote-codex ] || exit 78
        [ "${LARCH_CURSOR_MODEL:-}" = cursor-model ] || exit 78
        [ "${LARCH_EXTERNAL_AUTH_RETRIES:-}" = 2 ] || exit 78
        [ "${LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT:-}" = 17 ] || exit 78
        [ "${LARCH_PROBE_NEGATIVE_TTL_SECONDS:-}" = 3 ] || exit 78
        [ "${LARCH_PROBE_RETRIES:-}" = 4 ] || exit 78
        [ "${LARCH_PROBE_TIMEOUT_RETRIES:-}" = 5 ] || exit 78
        [ "${LARCH_PROBE_TIMEOUT_SECONDS:-}" = 6 ] || exit 78
        [ "${LARCH_PROBE_TTL_SECONDS:-}" = 7 ] || exit 78
      fi
      mkdir -p "$bootstrap_session"
      printf '%s\n' 'bootstrap-session' > "$bootstrap_session/session-id"
      if [ "$bootstrap_repo_available" = true ]; then
        printf '%s\n' \
          "SESSION_TMPDIR=$bootstrap_session" \
          'SESSION_ID=bootstrap-session' \
          'REPO=character-ai/larch' \
          'REPO_UNAVAILABLE=false' \
          'CLAUDE_BINARY_FOUND=false' \
          'CODEX_BINARY_FOUND=false' \
          'CURSOR_BINARY_FOUND=false'
      else
        printf '%s\n' \
          "SESSION_TMPDIR=$bootstrap_session" \
          'SESSION_ID=bootstrap-session' \
          'REPO=' \
          'REPO_UNAVAILABLE=true' \
          'CLAUDE_BINARY_FOUND=false' \
          'CODEX_BINARY_FOUND=false' \
          'CURSOR_BINARY_FOUND=false'
      fi
      exit 0
      ;;
    issue:context)
      if [ "$bootstrap_repo_available" = true ]; then
        printf '%s' 'Issue 8358 title' > "$bootstrap_session/upstream-issue-title.txt"
        printf '%s' 'Issue 8358 body' > "$bootstrap_session/upstream-issue-body.txt"
        printf '%s\n' \
          "TITLE_FILE=$bootstrap_session/upstream-issue-title.txt" \
          "BODY_FILE=$bootstrap_session/upstream-issue-body.txt"
        exit 0
      fi
      ;;
    issue:state)
      if [ "$bootstrap_tracking" = true ]; then
        if [ -f "$bootstrap_session/.bootstrap-test-issue-closed" ]; then
          printf '%s\n' 'STATE=CLOSED' 'IS_PR=false'
        else
          printf '%s\n' 'STATE=OPEN' 'IS_PR=false'
        fi
        exit 0
      fi
      ;;
    dirty-tree:checkpoint)
      if [ "$bootstrap_repo_available" = true ]; then
        printf '%s\n' 'STATUS=clean'
        exit 0
      fi
      ;;
    push:checkpoint-probe)
      if [ "$bootstrap_repo_available" = true ]; then
        printf '%s\n' 'ROUTE=continue' 'CHECKPOINT_NEXT=continue' 'REBASE_OUTCOME=clean'
        exit 0
      fi
      ;;
    session:persist-run-flags)
      if [ "$bootstrap_tracking" = true ]; then
        printf '%s\n' 'DIFFICULTY_OVERRIDE=HARD' > "$bootstrap_session/run-flags.sh"
        exit 0
      fi
      ;;
    tracking-issue:rename)
      if [ "$bootstrap_tracking" = true ]; then
        exit 0
      fi
      ;;
    tracking-issue:read)
      if [ "$bootstrap_tracking" = true ]; then
        body_out=''
        shift 2
        while [ "$#" -gt 0 ]; do
          if [ "$1" = '--body-out' ]; then
            body_out="${2:-}"
            break
          fi
          shift
        done
        [ -n "$body_out" ] && [ -f "$body_out" ] && [ -f "$bootstrap_session/fixture-issue-body.md" ] || exit 64
        cp "$bootstrap_session/fixture-issue-body.md" "$body_out"
        exit 0
      fi
      ;;
    progress:install-statusline)
      if [ "$bootstrap_tracking" = true ]; then
        exit 0
      fi
      ;;
    run-log:init|run-log:write|run-log:append-failure|run-log:append-entry|run-log:manifest|tracking-issue:upsert-summary)
      if [ "$bootstrap_repo_available" = true ]; then
        exit 0
      fi
      ;;
  esac
fi
case "${CLEAN_INSTALL_FAILURE:-}" in
  version)
    if [ "$1" = --version ]; then printf '%s\n' 'larch 0.0.0'; exit 0; fi
    ;;
  target)
    if [ "$1" = bootstrap ]; then
      if [ "$2" = self-check ]; then
        "$REAL_LARCH" "$@" | sed 's/"target":"[^"]*"/"target":"wrong-target"/'
        exit "$?"
      fi
    fi
    ;;
  bootstrap)
    if [ "$1" = bootstrap ]; then
      if [ "$2" = self-check ]; then exit 9; fi
    fi
    ;;
esac
if [ -n "${REAL_LARCH:-}" ]; then
  real_larch=$REAL_LARCH
else
  real_larch=__REAL_LARCH__
fi
exec "$real_larch" "$@"
"#;
    let real_larch = shell_quote(path_text(Path::new(env!("CARGO_BIN_EXE_larch"))));
    fs::write(
        &wrapper,
        wrapper_source.replace("__REAL_LARCH__", &real_larch),
    )
    .expect("write verified binary wrapper");
    #[cfg(unix)]
    {
        let mut permissions = fs::metadata(&wrapper)
            .expect("read wrapper metadata")
            .permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&wrapper, permissions).expect("make wrapper executable");
    }
    let home = temporary_root.join("home");
    let session = temporary_root.join("session");
    let sessions_cache = home.join(".cache/larch/sessions");
    fs::create_dir_all(&sessions_cache).expect("create clean-install home");
    fs::create_dir_all(&session).expect("create clean-install session directory");
    // `restore-finalize-state` reports a missing durable state file as a warning
    // exit, so the seeded state is what lets a clean dispatch complete.
    fs::write(
        session.join("ship-pr-state.sh"),
        "BRANCH_NAME=clean-install\n",
    )
    .expect("seed clean-install ship-pr state");
    // `resolve-trusted-design-env` resolves an existing pointer or exits 1, so the
    // seeded link and target are what let a clean dispatch complete.
    fs::write(
        session.join("design-env.sh"),
        format!(
            "DESIGN_TMPDIR={}\nexport SESSION_ID=clean-install\n",
            session.display()
        ),
    )
    .expect("seed clean-install design env");
    #[cfg(unix)]
    std::os::unix::fs::symlink(
        session.join("design-env.sh"),
        sessions_cache.join("current-design-env-4242.sh"),
    )
    .expect("seed clean-install design pointer");
    seed_clean_install_run_log_inputs(&root, &session);
    CleanInstallFixture {
        events: temporary_root.join("events.log"),
        binary: PathBuf::from(env!("CARGO_BIN_EXE_larch")),
        _temporary: temporary,
        root,
        home,
        session,
        wrapper,
    }
}

/// Copy the contract that the installed Rust-owned lint command reads.
fn seed_clean_install_stall_recovery_contract(root: &Path) {
    let projection = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../plugin");
    for relative in [
        "python/stall-recovery-report.md",
        "python/stall-recovery-report-allowlists.tsv",
    ] {
        let destination = root.join(relative);
        fs::create_dir_all(
            destination
                .parent()
                .expect("stall-recovery contract parent"),
        )
        .expect("create stall-recovery contract parent");
        fs::copy(projection.join(relative), destination).expect("copy stall-recovery contract");
    }
}

/// Seed the payloads, quiet log, round source, run directory, and required-files
/// manifest the `run-log` entry-write and breadcrumb verbs read on a clean install.
fn seed_clean_install_run_log_inputs(root: &Path, session: &Path) {
    fs::write(session.join("payload.md"), "clean-install payload\n")
        .expect("seed clean-install batch payload");
    fs::write(
        session.join("larch-quiet-clean-install.sh-1.log"),
        "clean-install breadcrumb\n",
    )
    .expect("seed clean-install quiet log");
    fs::write(session.join("record.ndjson"), "{\"clean\":\"install\"}\n")
        .expect("seed clean-install append record");
    let round_source = session.join("round-src");
    fs::create_dir_all(&round_source).expect("create clean-install round source");
    fs::write(round_source.join("coder-prompt.md"), "prompt\n")
        .expect("seed clean-install round artifact");
    let run_directory = session.join("verify-run");
    fs::create_dir_all(&run_directory).expect("create clean-install verify run directory");
    fs::write(
        run_directory.join("manifest.json"),
        "{\"schema_version\":2,\"status\":\"merged\",\"run_id\":\"clean-install\",\"steps_ran\":{}}\n",
    )
    .expect("seed clean-install verify manifest");
    let documents = root.join("docs");
    fs::create_dir_all(&documents).expect("create clean-install docs directory");
    fs::write(
        documents.join("run-logs-required-files.tsv"),
        "relative_path\tcondition\nmanifest.json\talways\n",
    )
    .expect("seed clean-install required-files manifest");
}

/// Expand one case's static arguments against the fixture's seeded session.
fn clean_install_arguments(fixture: &CleanInstallFixture, case: CleanInstallCase) -> Vec<String> {
    let session = fixture.session.to_string_lossy().into_owned();
    let home = fixture.home.to_string_lossy().into_owned();
    case.arguments()
        .iter()
        .map(|argument| {
            argument
                .replace(CLEAN_INSTALL_SESSION_TOKEN, &session)
                .replace(CLEAN_INSTALL_HOME_TOKEN, &home)
        })
        .collect()
}

/// Render the argv line the verified bootstrap wrapper records for one case.
///
/// An argument-free verb records only its domain and verb, with no trailing
/// separator, because the wrapper logs the shell's joined argument list.
fn clean_install_dispatch(fixture: &CleanInstallFixture, case: CleanInstallCase) -> String {
    std::iter::once(case.domain.to_owned())
        .chain(std::iter::once(case.verb.to_owned()))
        .chain(clean_install_arguments(fixture, case))
        .collect::<Vec<_>>()
        .join(" ")
}

fn run_clean_install_case(
    fixture: &CleanInstallFixture,
    case: CleanInstallCase,
    failure: Option<&str>,
) -> std::process::Output {
    let manifest_root = if case.id == "clean-install-run-log-manifest" {
        let path = fixture
            .root
            .join("manifest-logs/clean/clean-install/manifest.json");
        fs::create_dir_all(path.parent().expect("manifest parent"))
            .expect("create clean-install manifest parent");
        fs::write(
            &path,
            "{\"schema_version\":2,\"status\":\"partial\",\"run_id\":\"clean-install\",\"steps_ran\":{}}\n",
        )
        .expect("write clean-install manifest");
        Some(fixture.root.as_path())
    } else {
        None
    };
    let mut command = Command::new("/bin/bash");
    command
        .arg(fixture.root.join("scripts/larch.sh"))
        .args([case.domain, case.verb])
        .args(clean_install_arguments(fixture, case))
        .env("HOME", &fixture.home)
        .env("TMPDIR", &fixture.session)
        .env_remove("XDG_CACHE_HOME")
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        // Progress verbs write clone-scoped cache state; confine it to the fixture.
        .env("LARCH_TEST_CACHE_HOME", &fixture.root)
        .env("CLEAN_INSTALL_FAILURE", failure.unwrap_or_default());
    if let Some(root) = manifest_root {
        command.env("IMPLEMENT_TMPDIR", root);
    }
    command.output().expect("run clean-install selector")
}

#[test]
fn execution_issue_append_matches_the_frozen_python_behavior() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let reference = fixture_directory.join("execution_issues_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");
    let cases = [
        (
            "execution-issues-append-category-keyed",
            "Tool Failures",
            "- same",
            "",
            vec![SeedFile::text(
                "execution-issues.md",
                "### Warnings\n\n- same\n",
            )],
        ),
        (
            "execution-issues-append-chunked-durable-dedupe",
            "Warnings",
            "- first\n- second\n- third",
            "execution-issues.ndjson",
            vec![
                SeedFile::text("execution-issues.md", "### Warnings\n\n- first\n"),
                SeedFile::text(
                    "execution-issues.ndjson",
                    concat!(
                        "malformed\n",
                        "{\"body\":\"- third\\n\",\"category\":\"Warnings\"}\n"
                    ),
                ),
            ],
        ),
        (
            "execution-issues-append-duplicate",
            "Warnings",
            "- same",
            "",
            vec![SeedFile::text(
                "execution-issues.md",
                "### Warnings\n\n- same\n",
            )],
        ),
    ];
    for (name, category, entry, batch, seed_files) in cases {
        let mut common = vec![
            "--log".to_owned(),
            "{sandbox}/execution-issues.md".to_owned(),
            "--category".to_owned(),
            category.to_owned(),
            "--entry".to_owned(),
            entry.to_owned(),
        ];
        if !batch.is_empty() {
            common.extend([
                "--existing-batch".to_owned(),
                format!("{{sandbox}}/{batch}"),
            ]);
        }
        let case = ParityCase {
            name,
            python: Program::new(&python)
                .args(std::iter::once(path_text(&reference).to_owned()).chain(common.clone())),
            rust: Program::new(&rust).args(
                ["execution-issues".to_owned(), "append".to_owned()]
                    .into_iter()
                    .chain(common),
            ),
            seed_files,
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        };
        let golden = golden_directory.join(format!("{name}.golden.json"));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

fn fixture_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../fixtures/rust-parity")
}

fn compile_rust_fixture(fixture_directory: &Path) -> TempDir {
    let output = tempfile::tempdir().expect("compiled Rust fixture tempdir");
    let executable = output.path().join("reference-command");
    let rustc = env::var_os("RUSTC").map_or_else(|| find_executable("rustc"), PathBuf::from);
    let status = Command::new(&rustc)
        .args(["--edition=2024", "-o"])
        .arg(&executable)
        .arg(fixture_directory.join("reference_command.rs"))
        .status()
        .unwrap_or_else(|error| panic!("launch {}: {error}", rustc.display()));
    assert!(status.success(), "Rust parity fixture failed to compile");
    output
}

fn find_executable(name: &str) -> PathBuf {
    let path = env::var_os("PATH").expect("test process should have PATH");
    env::split_paths(&path)
        .map(|directory| {
            if directory.is_absolute() {
                directory.join(name)
            } else {
                env::current_dir()
                    .expect("test process should have a current directory")
                    .join(directory)
                    .join(name)
            }
        })
        .find(|candidate| candidate.is_file())
        .unwrap_or_else(|| panic!("required executable not found on PATH: {name}"))
}

fn path_text(path: &Path) -> &str {
    path.to_str().expect("fixture path should be UTF-8")
}

// ---------------------------------------------------------------------------
// eval validate-research-output / eval research (leaf #8500)
// ---------------------------------------------------------------------------

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("repo root")
        .to_path_buf()
}

fn eval_command(arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(arguments)
        .output()
        .expect("run eval command")
}

fn exit_code(output: &Output) -> i32 {
    output.status.code().expect("exit code")
}

#[test]
fn eval_validate_research_output_exit_code_matrix() {
    let dir = TempDir::new().expect("tempdir");

    // Missing file -> 4.
    let missing = dir.path().join("nope.md");
    let output = eval_command(&[
        "eval",
        "validate-research-output",
        missing.to_str().expect("path"),
    ]);
    assert_eq!(exit_code(&output), 4, "missing file must exit 4");

    // Thin body -> 2.
    let thin = dir.path().join("thin.md");
    fs::write(&thin, "one two three\n").expect("write");
    assert_eq!(
        exit_code(&eval_command(&[
            "eval",
            "validate-research-output",
            thin.to_str().expect("path"),
        ])),
        2,
    );

    let body: String = std::iter::repeat_n("word", 250)
        .collect::<Vec<_>>()
        .join(" ");

    // Enough words, no provenance -> 3.
    let no_prov = dir.path().join("noprov.md");
    fs::write(&no_prov, format!("{body}\n")).expect("write");
    assert_eq!(
        exit_code(&eval_command(&[
            "eval",
            "validate-research-output",
            no_prov.to_str().expect("path"),
        ])),
        3,
    );

    // Provenance present -> 0.
    let with_prov = dir.path().join("prov.md");
    fs::write(&with_prov, format!("{body} https://example.com/x\n")).expect("write");
    assert_eq!(
        exit_code(&eval_command(&[
            "eval",
            "validate-research-output",
            with_prov.to_str().expect("path"),
        ])),
        0,
    );

    // Structured reviewer mode -> exit 5 when nothing normalizes.
    let junk = dir.path().join("junk.md");
    fs::write(&junk, "not structured at all\n").expect("write");
    assert_eq!(
        exit_code(&eval_command(&[
            "eval",
            "validate-research-output",
            "--structured-reviewer-mode",
            junk.to_str().expect("path"),
        ])),
        5,
    );

    // -h prints usage and exits 0.
    let help = eval_command(&["eval", "validate-research-output", "-h"]);
    assert_eq!(exit_code(&help), 0);
    assert!(String::from_utf8_lossy(&help.stdout).contains("Usage: validate-research-output"));
}

#[test]
fn eval_validate_research_output_validation_mode_accepts_sentinel() {
    let dir = TempDir::new().expect("tempdir");
    let sentinel = dir.path().join("s.md");
    fs::write(&sentinel, "NO_ISSUES_FOUND\n").expect("write");
    assert_eq!(
        exit_code(&eval_command(&[
            "eval",
            "validate-research-output",
            "--validation-mode",
            sentinel.to_str().expect("path"),
        ])),
        0,
    );
}

#[test]
fn eval_validate_research_output_writes_normalized_wire_file() {
    let dir = TempDir::new().expect("tempdir");
    let reviewer = dir.path().join("reviewer.tsv");
    let header = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix";
    fs::write(
        &reviewer,
        format!("{header}\n1\tin_scope\tMAJOR\tcompleteness\tsrc/a.rs:1\twhat\tscenario\tfix\n"),
    )
    .expect("write");
    let wire = dir.path().join("out.tsv");
    let output = eval_command(&[
        "eval",
        "validate-research-output",
        "--structured-reviewer-mode",
        "--write-structured",
        wire.to_str().expect("path"),
        reviewer.to_str().expect("path"),
    ]);
    assert_eq!(exit_code(&output), 0);
    // Column 1 normalizes to "1", severity lowercases, focus canonicalizes.
    assert_eq!(
        fs::read_to_string(&wire).expect("wire"),
        format!("{header}\n1\tin_scope\tmajor\tcode-quality\tsrc/a.rs:1\twhat\tscenario\tfix\n"),
    );
}

#[test]
fn eval_research_smoke_test_reports_pass() {
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["eval", "research", "--smoke-test"])
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .output()
        .expect("run eval research");
    assert_eq!(
        exit_code(&output),
        0,
        "smoke test stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stdout).contains("smoke test PASS"),
        "stdout: {}",
        String::from_utf8_lossy(&output.stdout)
    );
}

#[test]
fn eval_research_rejects_bad_timeout() {
    let output = eval_command(&["eval", "research", "--timeout", "0"]);
    assert_eq!(exit_code(&output), 2);
}

#[test]
fn eval_research_help_exits_zero() {
    let output = eval_command(&["eval", "research", "--help"]);
    assert_eq!(exit_code(&output), 0);
    assert!(String::from_utf8_lossy(&output.stdout).contains("Usage: eval research"));
}

#[test]
fn eval_research_missing_claude_reports_exit_three() {
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["eval", "research"])
        .env("PATH", "")
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .output()
        .expect("run eval research");
    assert_eq!(exit_code(&output), 3);
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("required tool missing: claude"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}
